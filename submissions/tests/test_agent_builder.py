import pytest
import docker
from submissions.agent_builder import build_from_zip, BuildError


def test_builder_success_valid_zip(docker_client, load_zip, track_images):
    """Test building from a standard valid zip file."""
    zip_bytes = load_zip("valid_agent.zip")
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])

    assert result["image_id"]
    assert result["tag"].startswith("agent-")
    assert result["labels"]["org.gameai.owner_id"] == "test_owner"
    
    img = docker_client.images.get(result["image_id"])
    assert img


def test_builder_success_different_name(docker_client, load_zip, track_images):
    """Test building where agent file has a different name ending in _agent.py."""
    zip_bytes = load_zip("different_agent_name.zip")
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])
    assert result["image_id"]


def test_builder_success_with_dockerignore(docker_client, load_zip, track_images):
    """Test building a zip that includes a .dockerignore file."""
    zip_bytes = load_zip("dockerignore_agent.zip")
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])
    
    client = docker.from_env()
    try:
        client.containers.run(
            result["image_id"], 
            "ls ignored_file.txt", 
            remove=True
        )
        pytest.fail("ignored_file.txt should not exist in the image")
    except docker.errors.ContainerError:
        pass


def test_builder_fails_no_agent_file(create_zip):
    """Test failure when no agent.py or *_agent.py is present."""
    zip_bytes = create_zip({"readme.txt": "hello"})
    with pytest.raises(BuildError, match="No agent entry file found"):
        build_from_zip(zip_bytes, owner_id="fail_test")


def test_builder_fails_multiple_agents(create_zip):
    """Test failure when multiple agent files are present."""
    zip_bytes = create_zip({
        "agent.py": "print('a')",
        "my_agent.py": "print('b')"
    })
    with pytest.raises(BuildError, match="Multiple agent entry files found"):
        build_from_zip(zip_bytes, owner_id="fail_test")


def test_builder_fails_illegal_path(create_zip):
    """Test failure when zip contains illegal paths (Zip Slip)."""
    import zipfile
    import io
    
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("../evil.py", "print('evil')")
    
    with pytest.raises(BuildError, match="Illegal Path in ZIP"):
        build_from_zip(bio.getvalue(), owner_id="fail_test")


def test_builder_fails_nested_agent_not_found(load_zip):
    """Test that an agent in a subdirectory is NOT found."""
    zip_bytes = load_zip("nested_agent.zip")
    with pytest.raises(BuildError, match="No agent entry file found"):
        build_from_zip(zip_bytes, owner_id="fail_test")