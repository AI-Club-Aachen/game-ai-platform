import pytest
import docker
from submissions.agent_builder import build_from_zip, BuildError


def test_builder_success_valid_zip(docker_client, create_zip, track_images):
    """Test building from a standard valid zip file."""
    zip_bytes = create_zip({
        "agent.py": "print('hello')",
        "requirements.txt": ""
    })
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])

    assert result["image_id"]
    assert result["tag"].startswith("agent-")
    assert result["labels"]["org.gameai.owner_id"] == "test_owner"
    
    img = docker_client.images.get(result["image_id"])
    assert img


def test_builder_success_different_name(docker_client, create_zip, track_images):
    """Test building where agent file has a different name ending in _agent.py."""
    zip_bytes = create_zip({
        "my_agent.py": "print('hello')",
        "requirements.txt": ""
    })
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])
    assert result["image_id"]


def test_builder_success_with_dockerignore(docker_client, create_zip, track_images):
    """Test building a zip that includes a .dockerignore file."""
    zip_bytes = create_zip({
        "agent.py": "print('test')",
        ".dockerignore": "ignored_file.txt",
        "ignored_file.txt": "should be ignored"
    })
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


def test_builder_fails_nested_agent_not_found(create_zip):
    """Test that an agent in a subdirectory is NOT found."""
    zip_bytes = create_zip({
        "subfolder/": "",
        "subfolder/agent.py": "print('nested')"
    })
    with pytest.raises(BuildError, match="No agent entry file found"):
        build_from_zip(zip_bytes, owner_id="fail_test")


def test_builder_prevents_tag_collision(docker_client, create_zip, track_images):
    """
    Test that building the same zip twice (even with different owners)
    results in two DIFFERENT tags and NO dangling images.
    """
    zip_bytes = create_zip({
        "agent.py": "print('hello')",
        "requirements.txt": ""
    })
    
    # Build 1
    res1 = build_from_zip(zip_bytes, owner_id="owner_A")
    track_images(res1["image_id"])
    
    # Build 2
    res2 = build_from_zip(zip_bytes, owner_id="owner_B")
    track_images(res2["image_id"])
    
    # Check that we have 2 different images
    assert res1["image_id"] != res2["image_id"]
    
    # Check that we have 2 different tags
    assert res1["tag"] != res2["tag"]
    
    # Verify both tags still exist (neither was stolen)
    img1 = docker_client.images.get(res1["tag"])
    img2 = docker_client.images.get(res2["tag"])
    
    assert img1.id == res1["image_id"]
    assert img2.id == res2["image_id"]