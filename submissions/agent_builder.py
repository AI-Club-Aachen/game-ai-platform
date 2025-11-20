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
            # passiert, wenn man versucht aus der zip auszubrechen, also in folder drüber gehen will
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

def build_from_zip(zip_bytes: bytes, owner_id: str,
                   repo_prefix: str="agent", base_label_ns: str="org.aiclub") -> dict:
    """Verwendet submissions/Dockerfile, baut Image aus ZIP-Inhalt."""
    client = docker.from_env()
    project_root = Path(__file__).resolve().parent # submissions/
    dockerfile_path = project_root / "Dockerfile"

    if not dockerfile_path.exists():
        raise BuildError("submissions/Dockerfile nicht gefunden.")
    
    with tempfile.TemporaryDirectory(prefix="agent-build-") as td:
        ctx = Path(td)
        _safe_extract_zip(zip_bytes, ctx)

        # kleiner check
        if not (ctx / "agent.py").exists():
            raise BuildError("agent.py fehlt in der ZIP.")
        
        # agent_requirements ins build-directory kopieren
        global_reqs = project_root / "agent_requirements.txt"
        if global_reqs.exists():
            shutil.copy(global_reqs, ctx / "agent_requirements.txt")

        # .dockerignore wird hinzugefügt, falls der User keins drin hat
        di = ctx / ".dockerignore"
        if not di.exists():
            if DEFAULT_DOCKERIGNORE_PATH.exists():
                di.write_text(DEFAULT_DOCKERIGNORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

        # deterministischer Tag + Label
        sha = _content_hash(ctx)
        tag = f"{repo_prefix}-{sha[:8]}"
        labels = {
            f"{base_label_ns}.owner_id": str(owner_id),
            f"{base_label_ns}.content_sha256": sha,
            f"{base_label_ns}.created_at": datetime.now(timezone.utc).isoformat(),
            f"{base_label_ns}.kind": "agent"
        }   

        image, _ = client.images.build(
            path=str(ctx),
            dockerfile=str(dockerfile_path),
            tag=tag,
            labels=labels,
            rm=True,
            pull=False,
            network_mode="default" # Build darf Netz haben, nur die runtime später nicht
        )
    return {
        "image_id": image.id,
        "tag": tag,
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
