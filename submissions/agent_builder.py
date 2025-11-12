import io
import os
import zipfile
import hashlib
import tempfile
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
        
        # .dockerignore wird hinzugefügt, falls der User keins drin hat
        # .dockerignore hinzufügen (falls der User keins mitliefert)
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

    