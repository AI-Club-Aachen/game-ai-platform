import time

import docker
import pytest
from submissions.agent_builder import build_from_zip
from submissions.agent_manager import (
    delete_agent_container,
    delete_agent_image,
    delete_images_for_owner,
    get_container_logs,
    get_container_stats,
    list_agent_containers,
    list_agent_images,
    stop_agent_container,
)
from submissions.agent_runner import start_agent_container


@pytest.fixture
def test_image(create_zip, track_images):
    """Creates a test image and returns its tag. Cleans up after."""
    zip_bytes = create_zip({"agent.py": "print('hello')", "requirements.txt": ""})
    result = build_from_zip(zip_bytes, owner_id="manager_test")
    tag = result["tag"]
    track_images(result["image_id"])
    yield tag
    try:
        delete_agent_image(tag, force=True)
    except Exception:
        pass


@pytest.fixture
def test_container(test_image):
    """Creates a test container and returns its ID. Cleans up after."""
    res = start_agent_container(test_image, match_id="m1", agent_id="a1", owner_id="manager_test")
    cid = res["container_id"]

    yield cid

    try:
        delete_agent_container(cid, force=True)
    except Exception:
        pass


def test_list_agent_images(test_image):
    """Test listing agent images with filtering by owner."""
    images = list_agent_images(owner_id="manager_test")
    assert len(images) >= 1
    found = False
    for img in images:
        if img["owner_id"] == "manager_test":
            # Check if our specific test image tag is present in this image's tags
            if test_image in img["tags"]:
                found = True
            assert "image_id" in img
            assert "created_at" in img
    assert found


def test_delete_agent_image(create_zip, track_images):
    """Test deleting a specific agent image."""
    zip_bytes = create_zip({"agent.py": "print('hello')", "requirements.txt": ""})
    result = build_from_zip(zip_bytes, owner_id="delete_test")
    tag = result["tag"]
    track_images(result["image_id"])

    delete_agent_image(tag)

    client = docker.from_env()
    with pytest.raises(docker.errors.ImageNotFound):
        client.images.get(tag)


def test_delete_images_for_owner(create_zip, track_images):
    """Test deleting all images for a given owner."""
    zip1 = create_zip({"agent.py": "print(1)"})
    zip2 = create_zip({"agent.py": "print(2)"})

    res1 = build_from_zip(zip1, owner_id="bulk_delete_owner")
    res2 = build_from_zip(zip2, owner_id="bulk_delete_owner")
    track_images(res1["image_id"])
    track_images(res2["image_id"])

    count = delete_images_for_owner("bulk_delete_owner", force=True)
    assert count == 2

    images = list_agent_images(owner_id="bulk_delete_owner")
    assert len(images) == 0


def test_list_agent_containers(test_container):
    """Test listing agent containers with filtering."""
    containers = list_agent_containers(owner_id="manager_test", include_exited=True)
    assert len(containers) >= 1
    ids = [c["container_id"] for c in containers]
    assert test_container in ids


def test_get_container_logs(test_container):
    """Test retrieving container logs."""
    time.sleep(1)
    logs = get_container_logs(test_container)
    assert isinstance(logs, str)


def test_stop_agent_container(create_zip, track_images):
    """Test stopping a running agent container."""
    zip_bytes = create_zip({"agent.py": "import time; time.sleep(10); print('done')"})
    res = build_from_zip(zip_bytes, owner_id="stopper")
    tag = res["tag"]
    track_images(res["image_id"])

    start_res = start_agent_container(tag, match_id="m2", agent_id="a2", owner_id="stopper")
    cid = start_res["container_id"]

    try:
        stop_agent_container(cid)

        client = docker.from_env()
        c = client.containers.get(cid)
        assert c.status in ["exited", "stopped"]
    finally:
        delete_agent_container(cid, force=True)


def test_get_container_stats(test_container):
    """Test retrieving container stats."""
    stats = get_container_stats(test_container)
    assert "memory_usage" in stats
    assert "memory_limit" in stats
    assert "cpu_percent" in stats


def test_stats_on_running_container(create_zip, track_images):
    """Test retrieving CPU and memory stats from a running container."""
    zip_bytes = create_zip({"agent.py": "import time; time.sleep(5)"})
    res = build_from_zip(zip_bytes, owner_id="stats_test")
    tag = res["tag"]
    track_images(res["image_id"])

    start_res = start_agent_container(tag, match_id="m3", agent_id="a3", owner_id="stats_test")
    cid = start_res["container_id"]

    try:
        stats = get_container_stats(cid)
        assert "memory_usage" in stats
        assert "cpu_percent" in stats
    finally:
        delete_agent_container(cid, force=True)
