import hashlib
import io
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import docker

logger = logging.getLogger(__name__)

DEFAULT_DOCKERIGNORE_PATH = Path(__file__).parent / "default_dockerignore"


class BuildError(Exception):
    pass


def _safe_extract_zip(zip_bytes: bytes, dst: Path) -> None:
    dst = dst.resolve()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for m in zf.infolist():
            p = (dst / m.filename).resolve()
            # will trigger when one tries to escape from the zip by trying to access
            # folders higher up
            if not str(p).startswith(str(dst)):
                raise BuildError(f"Illegal Path in ZIP: {m.filename}")
        zf.extractall(dst)


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
            "No agent entry file found. Expected 'agent.py' or a file ending with '_agent.py'."
        )

    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        raise BuildError(f"Multiple agent entry files found: {names}. Provide exactly one file.")

    return candidates[0].name


def build_from_zip(
    zip_bytes: bytes, owner_id: str, repo_prefix: str = "agent", base_label_ns: str = "org.gameai"
) -> dict:
    """Uses orchestration/Dockerfile to build a Docker image from the ZIP contents."""
    client = docker.from_env()
    project_root = Path(__file__).resolve().parent.parent  # orchestration/

    build_local_base = os.environ.get("BUILD_LOCAL_BASE_IMAGE", "False").lower() in ("true", "1", "yes")

    if build_local_base:
        base_image = "agent-base:latest"

        logger.info("BUILD_LOCAL_BASE_IMAGE is enabled. Building base image locally...")
        dockerfile_base_path = project_root / "Dockerfile.base"
        if not dockerfile_base_path.exists():
            raise BuildError(f"{dockerfile_base_path} not found.")

        gamelib_src = project_root.parent / "gamelib"
        use_local_gamelib = gamelib_src.exists()

        try:
            if not use_local_gamelib:
                client.images.build(
                    path=str(project_root),
                    dockerfile=str(dockerfile_base_path),
                    tag=base_image,
                    rm=True,
                )
            else:
                logger.info("Local gamelib found, injecting into base image build context...")
                with tempfile.TemporaryDirectory(prefix="base-build-context-") as td:
                    build_ctx = Path(td)

                    # Copy context files, preserving timestamps for Docker cache
                    shutil.copy2(dockerfile_base_path, build_ctx / "Dockerfile.base")
                    shutil.copy2(project_root / "base_requirements.txt", build_ctx / "base_requirements.txt")

                    # Copy gamelib source
                    shutil.copytree(gamelib_src, build_ctx / "gamelib")

                    # Inject local package installation into the builder stage of Dockerfile
                    df_lines = (build_ctx / "Dockerfile.base").read_text().splitlines()
                    new_df = []
                    injected = False
                    for line in df_lines:
                        if not injected and (line.startswith("# Stage 2") or (line.startswith("FROM") and "builder" not in line)):
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
                        rm=True,
                    )

            logger.info(f"Successfully built local base image: {base_image}")
        except Exception as e:
            raise BuildError(f"Failed to build local base image: {e}")
    else:
        base_image = "ghcr.io/ai-club-aachen/game-ai-platform/agent-base:latest"

        # Pull the latest base image to ensure we are up to date
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

    with tempfile.TemporaryDirectory(prefix="agent-build-") as td:
        ctx = Path(td)
        _safe_extract_zip(zip_bytes, ctx)

        entry_file = _find_agent_entry(ctx)

        # copy base_requirements into the build-directory
        global_reqs = project_root / "base_requirements.txt"
        if global_reqs.exists():
            shutil.copy(global_reqs, ctx / "base_requirements.txt")

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

        image, _ = client.images.build(
            path=str(ctx),
            dockerfile=str(dockerfile_path),
            tag=full_tag,
            labels=labels,
            rm=True,
            pull=False,
            buildargs={"AGENT_FILE": entry_file},
            network_mode="default",  # allow this for the build, but not for the containers later
        )

        try:
            client.containers.run(
                image.id,
                command=["python", "-c", f"with open('{entry_file}', 'rb') as f: compile(f.read(), '{entry_file}', 'exec')"],
                remove=True
            )
        except docker.errors.ContainerError as e:
            err_msg = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else str(e.stderr)
            try:
                client.images.remove(image.id, force=True)
            except Exception:
                pass
            raise BuildError(f"Agent code has syntax errors:\n{err_msg}")
        except docker.errors.APIError as e:
            try:
                client.images.remove(image.id, force=True)
            except Exception:
                pass
            raise BuildError(f"Failed to verify agent code: {e}")

    return {
        "image_id": image.id,
        "tag": full_tag,
        "labels": labels,
        "size": image.attrs.get("Size"),
    }


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
