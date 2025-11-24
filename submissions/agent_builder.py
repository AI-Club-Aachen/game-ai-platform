import io
import zipfile
import hashlib
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

import docker

DEFAULT_DOCKERIGNORE_PATH = Path(__file__).parent / "default_dockerignore"

class BuildError(Exception): pass

def _safe_extract_zip(zip_bytes: bytes, dst: Path) -> None:
    dst = dst.resolve()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for m in zf.infolist():
            p = (dst / m.filename).resolve()
            # will trigger when one tries to escape from the zip by trying to access folders higher up
            if not str(p).startswith(str(dst)):
                raise BuildError(f"Illegal Path in ZIP: {m.filename}")
        zf.extractall(dst)

def _content_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted([p for p in root.rglob("*") if p.is_file()]):
        h.update(p.relative_to(root).as_posix().encode())
        with p.open("rb") as f:
            while (b := f.read(1 << 14)):
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
        p for p in ctx.iterdir() if p.is_file() and (p.name == "agent.py" or p.name.endswith("_agent.py"))
    ]

    if not candidates:
        raise BuildError(
            "No agent entry file found. Expected 'agent.py' or a file ending with '_agent.py'."
        )
    
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        raise BuildError(
            f"Multiple agent entry files found: {names}. "
            "Provide exactly one file."
        )

    return candidates[0].name


def build_from_zip(zip_bytes: bytes, owner_id: str,
                   repo_prefix: str="agent", base_label_ns: str="org.aiclub") -> dict:
    """Uses submissions/Dockerfile to build a Docker image from the ZIP contents."""
    client = docker.from_env()
    project_root = Path(__file__).resolve().parent # submissions/
    dockerfile_path = project_root / "Dockerfile.agent"

    if not dockerfile_path.exists():
        raise BuildError("submissions/Dockerfile nicht gefunden.")
    
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
                di.write_text(DEFAULT_DOCKERIGNORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

        # deterministic tag + label
        sha = _content_hash(ctx)
        base_tag = f"{repo_prefix}-{sha[:8]}"
        full_tag = f"{base_tag}:latest"
        labels = {
            f"{base_label_ns}.owner_id": str(owner_id),
            f"{base_label_ns}.content_sha256": sha,
            f"{base_label_ns}.created_at": datetime.now(timezone.utc).isoformat(),
            f"{base_label_ns}.kind": "agent"
        }   

        image, _ = client.images.build(
            path=str(ctx),
            dockerfile=str(dockerfile_path),
            tag=full_tag,
            labels=labels,
            rm=True,
            pull=False,
            buildargs={"AGENT_FILE": entry_file},
            network_mode="default" # allow this for the build, but not for the containers later
        )
    return {
        "image_id": image.id,
        "tag":  full_tag,
        "labels": labels,
        "size": image.attrs.get("Size")
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
