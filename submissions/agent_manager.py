import docker

LABEL_NS = "org.gameai"
LABEL_KIND = f"{LABEL_NS}.kind"
LABEL_OWNER_ID = f"{LABEL_NS}.owner_id"
LABEL_AGENT_ID = f"{LABEL_NS}.agent_id"
LABEL_MATCH_ID = f"{LABEL_NS}.match_id"

KIND_IMAGE_AGENT = "agent"
KIND_CONTAINER_AGENT = "agent-container"

class ManagementError(Exception):
    pass

def _client() -> docker.DockerClient:
    return docker.from_env()

# ---------------------------------------------------------------------------
# Image management
# ---------------------------------------------------------------------------

def list_agent_images(owner_id: str | None = None) -> list[dict]:
    """Return metadata for all agent images. Can filter by owner_id."""
    client = _client()
    images = client.images.list()
    result: list[dict] = []

    for img in images:
        attrs = img.attrs or {}
        cfg = attrs.get("Config", {})
        labels: dict = cfg.get("Labels") or {}

        if labels.get(LABEL_KIND) != KIND_IMAGE_AGENT:
            continue

        if owner_id is not None and labels.get(LABEL_OWNER_ID) != owner_id:
            continue

        result.append({
            "image_id": img.id,
            "tags": img.tags or [],
            "owner_id": labels.get(LABEL_OWNER_ID),
            "created_at": labels.get(f"{LABEL_NS}.created_at"),
            "content_sha256": labels.get(f"{LABEL_NS}.content_sha256"),
            "size": attrs.get("Size"),
        })

    return result

def delete_agent_image(image_ref: str, force: bool = False) -> None:
    """Delete a single agent image."""
    client = _client()
    try:
        client.images.remove(image=image_ref, force=force, noprune=False)
    except docker.errors.ImageNotFound:
        raise ManagementError(f"Image not found: {image_ref}")
    except Exception as e:
        raise ManagementError(f"Failed to delete image {image_ref}: {e}")
    
def delete_images_for_owner(owner_id: str, force: bool = False) -> int:
    """Delete all agent images for a given owner. Returns count."""
    client = _client()
    images = list_agent_images(owner_id)
    count = 0

    for item in images:
        image_id = item["image_id"]
        try:
            client.images.remove(image=image_id, force=force, noprune=False)
            count += 1
        except docker.errors.ImageNotFound:
            continue
        except Exception as e:
            raise ManagementError(f"Failed to delete image {image_id}: {e}")

    return count

# ---------------------------------------------------------------------------
# Container management (for matches)
# ---------------------------------------------------------------------------

def list_agent_containers(
    match_id: str | None = None,
    owner_id: str | None = None,
    agent_id: str | None = None,
    include_exited: bool = False,
) -> list[dict]:
    """List running or exited agent containers used in matches."""
    client = _client()

    label_filters: list[str] = [f"{LABEL_KIND}={KIND_CONTAINER_AGENT}"]

    if match_id is not None:
        label_filters.append(f"{LABEL_MATCH_ID}={match_id}")

    if owner_id is not None:
        label_filters.append(f"{LABEL_OWNER_ID}={owner_id}")

    if agent_id is not None:
        label_filters.append(f"{LABEL_AGENT_ID}={agent_id}")

    containers = client.containers.list(
        all=include_exited,
        filters={"label": label_filters},
    )

    result: list[dict] = []

    for c in containers:
        attrs = c.attrs or {}
        cfg = attrs.get("Config", {})
        labels = cfg.get("Labels") or {}
        state = attrs.get("State") or {}

        result.append({
            "container_id": c.id,
            "name": c.name,
            "image": cfg.get("Image"),
            "status": c.status,
            "state": state,
            "labels": labels,
            "created": attrs.get("Created"),
        })

    return result


def get_container_logs(container_id: str, tail: int = 1000) -> str:
    """Return combined stdout/stderr logs for a container."""
    client = _client()
    try:
        container = client.containers.get(container_id)
        raw = container.logs(stdout=True, stderr=True, tail=tail)
    except docker.errors.NotFound:
        raise ManagementError(f"Container not found: {container_id}")
    except Exception as e:
        raise ManagementError(f"Failed to read logs: {e}")

    return raw.decode(errors="replace")


def stop_agent_container(container_id: str, timeout: int | None = None) -> None:
    """Stop a running agent container."""
    client = _client()
    try:
        container = client.containers.get(container_id)
        if timeout is not None:
            container.stop(timeout=timeout)
        else:
            container.stop()
    except docker.errors.NotFound:
        raise ManagementError(f"Container not found: {container_id}")
    except Exception as e:
        raise ManagementError(f"Failed to stop container {container_id}: {e}")


def delete_agent_container(container_id: str, force: bool = False) -> None:
    """Remove an agent container."""
    client = _client()
    try:
        container = client.containers.get(container_id)
        container.remove(force=force)
    except docker.errors.NotFound:
        raise ManagementError(f"Container not found: {container_id}")
    except Exception as e:
        raise ManagementError(f"Failed to delete container {container_id}: {e}")


def get_container_stats(container_id: str) -> dict:
    """Return a CPU/memory usage snapshot for a container."""
    client = _client()
    try:
        container = client.containers.get(container_id)
        stats = container.stats(stream=False)
    except docker.errors.NotFound:
        raise ManagementError(f"Container not found: {container_id}")
    except Exception as e:
        raise ManagementError(f"Failed to read stats: {e}")

    mem = stats.get("memory_stats", {})
    mem_usage = mem.get("usage")
    mem_limit = mem.get("limit")

    cpu_stats = stats.get("cpu_stats", {})
    precpu_stats = stats.get("precpu_stats", {})

    cpu_delta = (
        cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
    )
    system_delta = (
        cpu_stats.get("system_cpu_usage", 0)
        - precpu_stats.get("system_cpu_usage", 0)
    )

    cpus = cpu_stats.get("online_cpus")
    if isinstance(cpus, list):
        cpus = len(cpus)

    if system_delta > 0 and cpu_delta > 0 and cpus:
        cpu_percent = (cpu_delta / system_delta) * cpus * 100.0
    else:
        cpu_percent = 0.0

    return {
        "memory_usage": mem_usage,
        "memory_limit": mem_limit,
        "cpu_percent": cpu_percent,
    }