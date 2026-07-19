import asyncio
import hashlib
import io
import logging
import os
import re
import shutil
import stat
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import docker
import yaml

from lib.agent_runner import _build_docker_run_kwargs
from lib.backend_api import BackendAPI

logger = logging.getLogger(__name__)

DEFAULT_DOCKERIGNORE_PATH = Path(__file__).parent / "default_dockerignore"
SECURE_SETTINGS_PATH = Path(__file__).parent.parent / "secure_default_settings.yaml"

# ZIP entry path components must match this charset.
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# Syntax-check program. Agent filename passed via AGENT_FILE env var.
_SYNTAX_CHECK_PROGRAM = (
    "import os; _f = os.environ['AGENT_FILE']; "
    "compile(open(_f, 'rb').read(), _f, 'exec')"
)

# Defaults applied when a key is missing from secure_default_settings.yaml.
_DEFAULT_BUILD_LIMITS: dict = {
    "max_archive_bytes": 50 * 1024 * 1024,
    "max_uncompressed_bytes": 256 * 1024 * 1024,
    "max_file_count": 2000,
    "max_nesting_depth": 16,
    "build_timeout_seconds": 300,
    "syntax_check_timeout_seconds": 30,
    "build_network_mode": "none",
}


class BuildError(Exception):
    pass


def _load_secure_settings() -> dict:
    if not SECURE_SETTINGS_PATH.exists():
        logger.warning("secure_default_settings.yaml not found; using built-in defaults")
        return {}
    return yaml.safe_load(SECURE_SETTINGS_PATH.read_text(encoding="utf-8")) or {}


def _load_build_limits(settings: dict | None = None) -> dict:
    settings = settings if settings is not None else _load_secure_settings()
    limits = dict(_DEFAULT_BUILD_LIMITS)
    limits.update(settings.get("build_limits") or {})
    return limits


def _validate_member_name(name: str, max_depth: int) -> None:
    """Reject ZIP entry names with unsafe characters or excessive nesting (H-4, H-8)."""
    components = [c for c in name.replace("\\", "/").split("/") if c not in ("", ".")]
    if len(components) > max_depth:
        raise BuildError(f"ZIP entry nesting too deep (>{max_depth}): {name}")
    for component in components:
        if component == "..":
            raise BuildError(f"Illegal Path in ZIP: {name}")
        if not _SAFE_NAME_RE.match(component):
            raise BuildError(f"Illegal characters in ZIP entry name: {name!r}")


def _safe_extract_zip(zip_bytes: bytes, dst: Path, limits: dict | None = None) -> None:
    limits = limits if limits is not None else _load_build_limits()
    dst = dst.resolve()

    if len(zip_bytes) > limits["max_archive_bytes"]:
        raise BuildError(
            f"ZIP archive too large: {len(zip_bytes)} bytes (max {limits['max_archive_bytes']})"
        )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        infos = zf.infolist()
        if len(infos) > limits["max_file_count"]:
            raise BuildError(f"ZIP has too many entries: {len(infos)} (max {limits['max_file_count']})")

        total_uncompressed = 0
        for m in infos:
            # Reject symlinks and other special files. Only inspect the file-type
            # field when it is actually set; zipfile.writestr stores plain perms
            # (e.g. 0o600) with no S_IFMT bits, which must be treated as regular.
            fmt = stat.S_IFMT(m.external_attr >> 16)
            if fmt == stat.S_IFLNK:
                raise BuildError(f"ZIP entry is a symlink, which is not allowed: {m.filename}")
            if fmt not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise BuildError(f"ZIP entry is a special file, which is not allowed: {m.filename}")

            _validate_member_name(m.filename, limits["max_nesting_depth"])

            total_uncompressed += m.file_size
            if total_uncompressed > limits["max_uncompressed_bytes"]:
                raise BuildError(
                    f"ZIP uncompressed size exceeds limit of {limits['max_uncompressed_bytes']} bytes"
                )

            # Robust containment: the resolved target must stay within dst (replaces
            # the weak str.startswith prefix check that mis-handled sibling prefixes).
            p = (dst / m.filename).resolve()
            if p != dst and not p.is_relative_to(dst):
                raise BuildError(f"Illegal Path in ZIP: {m.filename}")

        zf.extractall(dst)


def _build_image_with_timeout(
    client: "docker.DockerClient",
    *,
    path: str,
    dockerfile: str,
    tag: str,
    labels: dict,
    buildargs: dict,
    network_mode: str,
    timeout: float,
):
    """Stream a docker build with a wall-clock deadline (M-8/H-7).

    Consuming the low-level build stream lets us stop waiting once the deadline
    passes instead of blocking indefinitely on a stalling submission.
    """
    deadline = time.monotonic() + timeout
    resp = client.api.build(
        path=path,
        dockerfile=dockerfile,
        tag=tag,
        labels=labels,
        rm=True,
        pull=False,
        nocache=True,
        buildargs=buildargs,
        network_mode=network_mode,
        decode=True,
    )
    for chunk in resp:
        if time.monotonic() > deadline:
            raise BuildError(f"Image build exceeded timeout of {timeout}s")
        if isinstance(chunk, dict) and chunk.get("error"):
            raise BuildError(chunk["error"])
    # Resolve by tag — robust across classic builder and BuildKit output formats.
    return client.images.get(tag)


def _content_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted([p for p in root.rglob("*") if p.is_file()]):
        h.update(p.relative_to(root).as_posix().encode())
        with p.open("rb") as f:
            while b := f.read(1 << 14):
                h.update(b)
    return h.hexdigest()


def _find_agent_entry(ctx: Path) -> str:
    """
    Find the agent entry file in the build directory.
    Accepted patterns:
      - agent.py
      - *_agent.py

    Returns the filename of the entry point.
    """
    candidates = [
        p
        for p in ctx.iterdir()
        if p.is_file() and (p.name == "agent.py" or p.name.endswith("_agent.py"))
    ]

    if not candidates:
        raise BuildError(
            "No agent entry file found. Expected 'agent.py' or a file ending with '_agent.py' "
            "at the root of the ZIP file or inside a single top-level folder. "
            "Please check your ZIP file structure to ensure the agent file is not nested too deeply."
        )

    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        raise BuildError(f"Multiple agent entry files found: {names}. Provide exactly one file.")

    entry_name = candidates[0].name
    # Reject filenames outside safe charset.
    if not _SAFE_NAME_RE.match(entry_name):
        raise BuildError(f"Illegal characters in agent entry filename: {entry_name!r}")

    return entry_name


def get_base_image_name(requirements_file: str, build_local_base: bool) -> str:
    """
    Derives the Docker base image tag/repository name based on the requirements file name.

    Examples:
      - 'base_requirements.txt' -> 'agent-base:latest' (local) / 'ghcr.io/.../agent-base:latest' (remote)
      - 'torch_requirements.txt' -> 'agent-base-torch:latest' (local) / 'ghcr.io/.../agent-base-torch:latest' (remote)
      - 'custom_requirements.txt' -> 'agent-base-custom:latest' (local) / 'ghcr.io/.../agent-base-custom:latest' (remote)
    """
    file_name = Path(requirements_file).name
    if file_name.endswith("_requirements.txt"):
        suffix = file_name[:-17]
    elif file_name.endswith(".txt"):
        suffix = file_name[:-4]
    else:
        suffix = file_name

    if suffix in ("base", "requirements", ""):
        suffix = "base"

    if build_local_base:
        if suffix == "base":
            return "agent-base:latest"
        return f"agent-base-{suffix}:latest"
    else:
        if suffix == "base":
            env_var = "AGENT_BASE_IMAGE"
            default_image = "ghcr.io/ai-club-aachen/game-ai-platform/agent-base:latest"
        else:
            env_var = f"AGENT_BASE_IMAGE_{suffix.upper()}"
            default_image = f"ghcr.io/ai-club-aachen/game-ai-platform/agent-base-{suffix}:latest"
        return os.environ.get(env_var, default_image)


def build_from_zip(
    zip_bytes: bytes,
    owner_id: str,
    repo_prefix: str = "agent",
    base_label_ns: str = "org.gameai",
    requirements_file: str = "base_requirements.txt",
) -> dict:
    """Uses orchestration/Dockerfile to build a Docker image from the ZIP contents."""
    client = docker.from_env()
    project_root = Path(__file__).resolve().parent.parent  # orchestration/

    build_local_base = os.environ.get("BUILD_LOCAL_BASE_IMAGE", "False").lower() in ("true", "1", "yes")

    base_image = get_base_image_name(requirements_file, build_local_base)

    if build_local_base:
        logger.info(f"BUILD_LOCAL_BASE_IMAGE is enabled. Building base image {base_image} locally...")

        reg_user = os.environ.get("DOCKER_REGISTRY_USER")
        reg_pass = os.environ.get("DOCKER_REGISTRY_PASSWORD")
        if reg_user and reg_pass:
            logger.info("Logging into dhi.io registry...")
            client.login(username=reg_user, password=reg_pass, registry="dhi.io")
        else:
            logger.warning("DOCKER_REGISTRY_USER or DOCKER_REGISTRY_PASSWORD not set. "
                           "Skipping registry login, which may cause pull failures "
                           "if the base image is not available locally.")

        dockerfile_base_path = project_root / "Dockerfile.base"
        if not dockerfile_base_path.exists():
            raise BuildError(f"{dockerfile_base_path} not found.")

        gamelib_src = project_root.parent / "gamelib"
        use_local_gamelib = os.getenv("USE_LOCAL_GAMELIB", "false").lower() == "true" and gamelib_src.exists()

        try:
            if not use_local_gamelib:
                client.images.build(
                    path=str(project_root),
                    dockerfile=str(dockerfile_base_path),
                    tag=base_image,
                    buildargs={"REQUIREMENTS_FILE": requirements_file},
                    rm=True,
                    nocache=True,
                )
            else:
                logger.info("Local gamelib found, injecting into base image build context...")
                with tempfile.TemporaryDirectory(prefix="base-build-context-") as td:
                    build_ctx = Path(td)

                    # Copy context files, preserving timestamps for Docker cache
                    shutil.copy2(dockerfile_base_path, build_ctx / "Dockerfile.base")

                    req_path = build_ctx / requirements_file
                    shutil.copy2(project_root / requirements_file, req_path)

                    # Remove PyPI aica-gamelib dependency to force using the local copy
                    req_lines = [line for line in req_path.read_text().splitlines()
                                 if not line.startswith("aica-gamelib")]
                    req_path.write_text("\n".join(req_lines))

                    # Copy gamelib source ignoring build artifacts/virtualenvs
                    shutil.copytree(
                        gamelib_src,
                        build_ctx / "gamelib",
                        ignore=shutil.ignore_patterns(
                            '.venv', '__pycache__', '.pytest_cache', '*.pyc', '.git', '*.egg-info')
                    )

                    # Inject local package installation into the builder stage of Dockerfile
                    df_lines = (build_ctx / "Dockerfile.base").read_text().splitlines()
                    new_df = []
                    injected = False
                    for line in df_lines:
                        if not injected and (line.startswith("# Stage 2") or (line.startswith("FROM") and "builder" not in line)):  # noqa: E501
                            new_df.append("COPY gamelib /gamelib_local")
                            new_df.append("RUN pip install --no-cache-dir --prefix=/install /gamelib_local")
                            injected = True
                        new_df.append(line)

                    if not injected:
                        new_df.append("COPY gamelib /gamelib_local")
                        new_df.append("RUN pip install --no-cache-dir --prefix=/install /gamelib_local")

                    (build_ctx / "Dockerfile.base").write_text("\n".join(new_df))

                    client.images.build(
                        path=str(build_ctx),
                        dockerfile="Dockerfile.base",
                        tag=base_image,
                        buildargs={"REQUIREMENTS_FILE": requirements_file},
                        rm=True,
                        nocache=True,
                    )

            logger.info(f"Successfully built local base image: {base_image}")
        except Exception as e:
            raise BuildError(f"Failed to build local base image: {e}")
    else:
        # Pull the base image to ensure we are up to date
        try:
            logger.info(f"Pulling base image: {base_image}...")
            client.images.pull(base_image)
        except docker.errors.APIError as e:
            logger.warning(f"Failed to pull base image {base_image}: {e}")
            logger.info("Proceeding with local image if available...")

    if build_local_base:
        dockerfile_path = project_root / "Dockerfile.agent.local"
    else:
        dockerfile_path = project_root / "Dockerfile.agent"

    if not dockerfile_path.exists():
        raise BuildError(str(Path(__file__).resolve().parent.parent) + f"/{dockerfile_path.name} not found.")

    secure_settings = _load_secure_settings()
    build_limits = _load_build_limits(secure_settings)

    with tempfile.TemporaryDirectory(prefix="agent-build-") as td:
        ctx = Path(td)
        _safe_extract_zip(zip_bytes, ctx, build_limits)

        # Flatten directory if the user zipped a folder instead of its contents
        top_level_items = [p for p in ctx.iterdir() if p.name not in ("__MACOSX", ".DS_Store")]
        if len(top_level_items) == 1 and top_level_items[0].is_dir():
            inner_dir = top_level_items[0]
            for item in inner_dir.iterdir():
                shutil.move(str(item), str(ctx / item.name))
            shutil.rmtree(str(inner_dir), ignore_errors=True)

        entry_file = _find_agent_entry(ctx)

        # copy requirements into the build-directory
        global_reqs = project_root / requirements_file
        if global_reqs.exists():
            shutil.copy(global_reqs, ctx / requirements_file)

        # add .dockerignore, if the user does not provide one
        di = ctx / ".dockerignore"
        if not di.exists():
            if DEFAULT_DOCKERIGNORE_PATH.exists():
                di.write_text(
                    DEFAULT_DOCKERIGNORE_PATH.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )

        sha = _content_hash(ctx)
        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        base_tag = f"{repo_prefix}-{sha[:8]}-{ts_str}"
        full_tag = f"{base_tag}:latest"
        labels = {
            f"{base_label_ns}.owner_id": str(owner_id),
            f"{base_label_ns}.content_sha256": sha,
            f"{base_label_ns}.created_at": datetime.now(timezone.utc).isoformat(),
            f"{base_label_ns}.kind": "agent",
        }

        # Build with no network (egress disabled) and wall-clock timeout.
        image = _build_image_with_timeout(
            client,
            path=str(ctx),
            dockerfile=str(dockerfile_path),
            tag=full_tag,
            labels=labels,
            buildargs={"AGENT_FILE": entry_file, "BASE_IMAGE": base_image},
            network_mode=str(build_limits["build_network_mode"]),
            timeout=float(build_limits["build_timeout_seconds"]),
        )

        # Post-build syntax check with hardened container settings.
        run_kwargs = _build_docker_run_kwargs(secure_settings)
        syntax_timeout = float(build_limits["syntax_check_timeout_seconds"])
        try:
            container = client.containers.run(
                image.id,
                command=["python", "-c", _SYNTAX_CHECK_PROGRAM],
                environment={"AGENT_FILE": entry_file},
                detach=True,
                **run_kwargs,
            )
        except docker.errors.APIError as e:
            try:
                client.images.remove(image.id, force=True)
            except Exception:
                pass
            raise BuildError(f"Failed to verify agent code: {e}")

        try:
            try:
                result = container.wait(timeout=syntax_timeout)
            except Exception as e:
                try:
                    container.kill()
                except Exception:
                    pass
                try:
                    client.images.remove(image.id, force=True)
                except Exception:
                    pass
                raise BuildError(f"Agent syntax check timed out after {syntax_timeout}s: {e}")

            exit_code = result.get("StatusCode")
            if exit_code != 0:
                err_msg = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                try:
                    client.images.remove(image.id, force=True)
                except Exception:
                    pass
                raise BuildError(f"Agent code has syntax errors:\n{err_msg}")
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass

        # Reclaim dangling layers from builds.
        try:
            client.images.prune(filters={"dangling": True})
        except Exception as e:
            logger.debug(f"Dangling image prune failed (non-fatal): {e}")

    return {
        "image_id": image.id,
        "tag": full_tag,
        "labels": labels,
        "size": image.attrs.get("Size"),
    }


async def build_images_for_agents(agent_ids: list[str], api: BackendAPI) -> list[str]:
    """
    Used by match runner worker to build images for agents.
    This is needed when the agent builder cleans up images after building.

    Args:
        agent_ids: List of agent UUIDs to build images for
        api: BackendAPI instance for fetching agent and submission data

    Returns:
        List of Docker image tags in the same order as agent_ids

    Raises:
        BuildError: If any agent lacks an active submission, submission cannot be fetched,
                   or image building fails
    """
    image_tags = []

    for agent_id in agent_ids:
        logger.info(f"Building image for agent {agent_id}")

        try:
            # Get agent to find its active submission
            agent = await api.get_agent(agent_id)
            submission_id = agent.get("active_submission_id")
            arena_id = agent.get("arena_id")

            if not submission_id:
                raise BuildError(f"Agent {agent_id} does not have an active submission")

            # Fetch the arena to check for packages
            packages = "numpy"
            if arena_id:
                try:
                    arena = await api.get_arena(str(arena_id))
                    packages = arena.get("packages", "numpy")
                except Exception as ae:
                    logger.warning(f"Failed to fetch arena {arena_id} details, falling back to 'numpy': {ae}")

            requirements_file = "torch_requirements.txt" if packages == "torch" else "base_requirements.txt"

            # Get submission to find the user_id
            submission = await api.get_submission(submission_id)
            user_id = submission.get("user_id")

            # Download the zip file from backend API
            zip_bytes = await api.download_submission(submission_id)
            logger.debug(f"Downloaded ZIP file for agent {agent_id}: {len(zip_bytes)} bytes")

            # Build the image
            logger.info(f"Building Docker image for agent {agent_id} (submission {submission_id})")
            result = await asyncio.to_thread(
                build_from_zip,
                zip_bytes=zip_bytes,
                owner_id=str(user_id),
                requirements_file=requirements_file,
            )

            image_tag = result["tag"]
            logger.info(f"Successfully built image for agent {agent_id}: {image_tag}")
            image_tags.append(image_tag)

        except Exception as e:
            logger.error(f"Failed to build image for agent {agent_id}: {e}")
            raise BuildError(f"Failed to build image for agent {agent_id}: {e}") from e

    return image_tags


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Build an agent image from a ZIP file.")
    parser.add_argument("zip_path", help="Path to the agent ZIP.")
    parser.add_argument("--owner", default="localtest", help="Owner ID label.")
    args = parser.parse_args()

    zip_file = Path(args.zip_path)
    if not zip_file.exists():
        print("ZIP not found:", zip_file)
        exit(1)

    data = zip_file.read_bytes()

    try:
        result = build_from_zip(data, owner_id=args.owner)
        print("Build completed.")
        print("Image ID:", result["image_id"])
        print("Tag:", result["tag"])
        print("Size:", result["size"])
    except Exception as e:
        print("Build failed:", e)
        exit(1)
