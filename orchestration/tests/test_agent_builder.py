import io
import zipfile

import docker
import pytest

from lib.agent_builder import (
    _DEFAULT_BUILD_LIMITS,
    BuildError,
    _safe_extract_zip,
    build_from_zip,
)


def test_builder_success_valid_zip(docker_client, create_zip, track_images):
    """Test building from a standard valid zip file."""
    zip_bytes = create_zip({"agent.py": "print('hello')", "requirements.txt": ""})
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])

    assert result["image_id"]
    assert result["tag"].startswith("agent-")
    assert result["labels"]["org.gameai.owner_id"] == "test_owner"

    img = docker_client.images.get(result["image_id"])
    assert img


def test_builder_success_different_name(docker_client, create_zip, track_images):
    """Test building where agent file has a different name ending in _agent.py."""
    zip_bytes = create_zip({"my_agent.py": "print('hello')", "requirements.txt": ""})
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])
    assert result["image_id"]


def test_builder_success_with_dockerignore(docker_client, create_zip, track_images):
    """Test building a zip that includes a .dockerignore file."""
    zip_bytes = create_zip(
        {
            "agent.py": "print('test')",
            ".dockerignore": "ignored_file.txt",
            "ignored_file.txt": "should be ignored",
        }
    )
    result = build_from_zip(zip_bytes, owner_id="test_owner")
    track_images(result["image_id"])

    client = docker.from_env()
    container = client.containers.create(result["image_id"])
    try:
        # try to get the file from the container
        # get_archive returns a stream of the tar archive
        container.get_archive("ignored_file.txt")
        pytest.fail("ignored_file.txt should not exist in the image")
    except docker.errors.NotFound:
        # This is expected if the file was correctly ignored
        pass
    finally:
        container.remove()


def test_builder_fails_no_agent_file(create_zip):
    """Test failure when no agent.py or *_agent.py is present."""
    zip_bytes = create_zip({"readme.txt": "hello"})
    with pytest.raises(BuildError, match="No agent entry file found"):
        build_from_zip(zip_bytes, owner_id="fail_test")


def test_builder_fails_multiple_agents(create_zip):
    """Test failure when multiple agent files are present."""
    zip_bytes = create_zip({"agent.py": "print('a')", "my_agent.py": "print('b')"})
    with pytest.raises(BuildError, match="Multiple agent entry files found"):
        build_from_zip(zip_bytes, owner_id="fail_test")


def test_builder_fails_illegal_path(create_zip):
    """Test failure when zip contains illegal paths (Zip Slip)."""
    import io
    import zipfile

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("../evil.py", "print('evil')")

    with pytest.raises(BuildError, match="Illegal Path in ZIP"):
        build_from_zip(bio.getvalue(), owner_id="fail_test")


def test_builder_succeeds_single_nested_folder(docker_client, create_zip, track_images):
    """Test that if the zip contains a single root folder, it gets flattened and the agent is found."""
    zip_bytes = create_zip({"subfolder/": "", "subfolder/agent.py": "print('nested')"})
    res = build_from_zip(zip_bytes, owner_id="success_test")
    track_images(res["image_id"])
    assert "image_id" in res


def test_builder_fails_multiple_nested_agent_not_found(create_zip):
    """Test that an agent deep in a subdirectory is NOT found if there are multiple root folders."""
    zip_bytes = create_zip({
        "subfolder/": "",
        "subfolder/agent.py": "print('nested')",
        "another_folder/": "",
        "another_folder/file.txt": "abc"
    })
    with pytest.raises(BuildError, match="No agent entry file found"):
        build_from_zip(zip_bytes, owner_id="fail_test")


# ---------------------------------------------------------------------------
# Extraction-hardening regression tests.
# ---------------------------------------------------------------------------


def _zip_with(entries: dict[str, bytes | str]) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        for name, content in entries.items():
            z.writestr(name, content)
    return bio.getvalue()


def test_safe_extract_rejects_command_injection_filename(tmp_path):
    """Injection payloads in ZIP entry names are rejected at extraction."""
    malicious = "evil'); __import__('os').system('echo pwned')#_agent.py"
    zip_bytes = _zip_with({malicious: "print('x')"})

    with pytest.raises(BuildError, match="Illegal characters"):
        _safe_extract_zip(zip_bytes, tmp_path)

    # Nothing should have been written to disk.
    assert not any(tmp_path.iterdir())


def test_safe_extract_rejects_too_many_files(tmp_path):
    """Archives exceeding entry count cap are rejected."""
    limits = {**_DEFAULT_BUILD_LIMITS, "max_file_count": 3}
    zip_bytes = _zip_with({f"file_{i}.txt": "x" for i in range(10)})

    with pytest.raises(BuildError, match="too many entries"):
        _safe_extract_zip(zip_bytes, tmp_path, limits)


def test_safe_extract_rejects_zip_bomb_uncompressed(tmp_path):
    """Archives exceeding uncompressed size cap are rejected."""
    limits = {**_DEFAULT_BUILD_LIMITS, "max_uncompressed_bytes": 1024}
    # Highly compressible payload: small on disk, large uncompressed.
    zip_bytes = _zip_with({"agent.py": b"0" * (64 * 1024)})

    with pytest.raises(BuildError, match="uncompressed size"):
        _safe_extract_zip(zip_bytes, tmp_path, limits)


def test_safe_extract_rejects_symlink_entry(tmp_path):
    """Symlink entries are rejected."""
    import stat as stat_mod

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        info = zipfile.ZipInfo("link_agent.py")
        info.external_attr = (stat_mod.S_IFLNK | 0o777) << 16
        z.writestr(info, "/etc/passwd")

    with pytest.raises(BuildError, match="symlink"):
        _safe_extract_zip(bio.getvalue(), tmp_path)


def test_safe_extract_accepts_normal_archive(tmp_path):
    """Happy path: a standard agent ZIP (incl. a subfolder) extracts cleanly."""
    zip_bytes = _zip_with(
        {
            "agent.py": "print('hello')",
            "requirements.txt": "",
            "helpers/util.py": "x = 1",
        }
    )
    _safe_extract_zip(zip_bytes, tmp_path)
    assert (tmp_path / "agent.py").exists()
    assert (tmp_path / "helpers" / "util.py").exists()


def test_builder_prevents_tag_collision(docker_client, create_zip, track_images):
    """
    Test that building the same zip twice (even with different owners)
    results in two DIFFERENT tags and NO dangling images.
    """
    zip_bytes = create_zip({"agent.py": "print('hello')", "requirements.txt": ""})

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
