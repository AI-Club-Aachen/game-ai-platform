import docker
import pytest

from lib.agent_builder import build_from_zip
from lib.agent_manager import delete_agent_container
from lib.agent_runner import RunError, run_agent, start_agent_container


@pytest.fixture
def sleeper_agent(create_zip, track_images):
    """Creates an agent that sleeps for 2 seconds then exits."""
    zip_bytes = create_zip({"agent.py": "import time; time.sleep(2); print('Awake')"})
    res = build_from_zip(zip_bytes, owner_id="runner_test")
    track_images(res["image_id"])
    return res["tag"]


@pytest.fixture
def error_agent(create_zip, track_images):
    """Creates an agent that exits with code 1."""
    zip_bytes = create_zip({"agent.py": "exit(1)"})
    res = build_from_zip(zip_bytes, owner_id="runner_test")
    track_images(res["image_id"])
    return res["tag"]


@pytest.fixture
def echo_agent(create_zip, track_images):
    """Creates an agent that prints env vars."""
    zip_bytes = create_zip({"agent.py": "import os; print(os.environ.get('MY_VAR'))"})
    res = build_from_zip(zip_bytes, owner_id="runner_test")
    track_images(res["image_id"])
    return res["tag"]


def test_run_agent_success(sleeper_agent):
    """Test successful agent execution."""
    result = run_agent(sleeper_agent)
    assert result["exit_code"] == 0
    assert not result["timeout"]
    assert "Awake" in result["logs"]


def test_run_agent_timeout(create_zip, track_images):
    """Test agent execution timeout."""
    from lib import agent_runner

    original_loader = agent_runner._load_secure_defaults

    def mocked_loader():
        s = original_loader()
        s["time_limit_seconds"] = 1
        return s

    agent_runner._load_secure_defaults = mocked_loader

    try:
        zip_bytes = create_zip({"agent.py": "import time; time.sleep(5)"})
        res = build_from_zip(zip_bytes, owner_id="timeout_test")
        tag = res["tag"]
        track_images(res["image_id"])

        result = run_agent(tag)
        assert result["timeout"] is True
        assert result["exit_code"] == 124
    finally:
        agent_runner._load_secure_defaults = original_loader


def test_run_agent_error(error_agent):
    """Test agent execution with non-zero exit code."""
    result = run_agent(error_agent)
    assert result["exit_code"] == 1


def test_start_agent_container(echo_agent):
    """Test starting an agent container with environment variables."""
    res = start_agent_container(
        echo_agent,
        match_id="m_run",
        agent_id="a_run",
        owner_id="runner_test",
        extra_env={"MY_VAR": "HelloRunner"},
    )
    cid = res["container_id"]

    try:
        client = docker.from_env()
        container = client.containers.get(cid)
        container.wait()

        logs = container.logs().decode()
        assert "HelloRunner" in logs
        assert container.labels["org.gameai.match_id"] == "m_run"

    finally:
        delete_agent_container(cid, force=True)


def test_run_agent_image_not_found():
    """Test error handling when image doesn't exist."""
    with pytest.raises(RunError, match="Image not found"):
        run_agent("non_existent_image:tag")


def test_run_agent_log_truncation(create_zip, track_images):
    """Test that logs are truncated when exceeding 5MB."""
    # Create an agent that produces ~6MB of output (exceeds the 5MB limit)
    # Each line is ~1000 bytes, so 6000 lines = ~6MB
    agent_code = """
for i in range(6000):
    print('X' * 1000)
"""
    zip_bytes = create_zip({"agent.py": agent_code})
    res = build_from_zip(zip_bytes, owner_id="truncation_test")
    track_images(res["image_id"])

    result = run_agent(res["tag"])

    # Verify the agent ran successfully
    assert result["exit_code"] == 0
    assert not result["timeout"]

    # Verify logs were truncated
    logs = result["logs"]
    log_size = len(logs.encode("utf-8"))

    # Should be around 5MB + truncation message, definitely less than 6MB
    assert log_size < 6 * 1024 * 1024, f"Logs were not truncated: {log_size} bytes"
    assert "Logs truncated due to size limit" in logs, "Truncation message not found"

    # Should have some content (at least some of the X's)
    assert "X" in logs
