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
def load_zip():
    """Load static ZIP test files from submissions/tests/resources."""
    resources_dir = Path(__file__).parent / "resources"

    def _loader(name: str) -> bytes:
        path = resources_dir / name
        return path.read_bytes()
    
    return _loader
    
@pytest.fixture
def generated_simple_zip(tmp_path):
    agent = tmp_path / "agent.py"
    agent.write_text("print('Agent starting...')")

    zip_path = tmp_path / "agent.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(agent, "agent.py")

    return zip_path.read_bytes()