from pathlib import Path
import pytest
import docker
import zipfile
from docker.errors import DockerException

@pytest.fixture
def docker_client():
    """Ensure Docker is available for tests."""
    try:
        client = docker.from_env()
        client.ping()
    except DockerException:
        pytest.skip("Docker daemon not available.")
    return client

@pytest.fixture
def create_zip(tmp_path):
    """
    Factory fixture to create a zip file with given content.
    content: dict mapping filename to content (str or bytes).
    """
    def _create(content: dict[str, str | bytes]) -> bytes:
        zip_path = tmp_path / "temp_agent.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            for filename, file_content in content.items():
                # Handle directories if filename ends with /
                if filename.endswith("/"):
                    z.writestr(zipfile.ZipInfo(filename), "")
                    continue
                    
                if isinstance(file_content, str):
                    z.writestr(filename, file_content)
                else:
                    z.writestr(filename, file_content)
        return zip_path.read_bytes()
    return _create


# Track images created during this test session
_test_images = set()
_pre_existing_images = set()

@pytest.fixture
def track_images():
    """
    Fixture that tracks images created during tests.
    Use this in tests that create images to ensure they get cleaned up.
    """
    def _track(image_id: str):
        _test_images.add(image_id)
    return _track

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_resources():
    """
    Automatically cleanup Docker resources created during test session.
    Only removes images that were created during tests AND didn't exist before.
    This protects manually built images from deletion.
    """
    # Snapshot existing images BEFORE tests run
    try:
        client = docker.from_env()
        existing_images = client.images.list()
        for img in existing_images:
            _pre_existing_images.add(img.id)
    except:
        pass
    
    yield
    
    # Cleanup after all tests complete
    try:
        client = docker.from_env()
        
        print("\nCleaning up test images...")
        
        # Only remove tracked images that didn't exist before tests
        removed_count = 0
        for image_id in _test_images:
            # CRITICAL: Skip if image existed before tests started
            if image_id in _pre_existing_images:
                continue
                
            try:
                client.images.remove(image_id, force=True)
                removed_count += 1
            except Exception:
                pass
        
        # Remove dangling images (safe - these are always orphaned)
        print("Removing dangling images...")
        prune_result = client.images.prune(filters={"dangling": True})
        dangling_count = len(prune_result.get("ImagesDeleted", []))
        
        skipped = len(_test_images & _pre_existing_images)
        if skipped > 0:
            print(f"Protected {skipped} pre-existing image(s) from deletion")
        print(f"Cleaned up {removed_count} new test images and {dangling_count} dangling images")
        
    except Exception as e:
        print(f"Cleanup warning: {e}")