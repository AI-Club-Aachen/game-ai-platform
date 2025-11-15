"""
Agent runner for managing and executing game agents in a safe dockerized environment.
"""

import docker
import yaml
import time
from pathlib import Path

class RunError(Exception):
    pass


def _load_secure_defaults() -> dict:
    settings_path = Path(__file__).parent / "secure_default_settings.yaml"
    if not settings_path.exists():
        raise RunError("secure_default_settings.yaml not found.")
    return yaml.safe_load(settings_path.read_text(encoding="utf-8"))

def _build_docker_run_kwargs(settings):
    allowed = [
        "cap_drop",
        "security_opt",
        "read_only",
        "tmpfs",
        "pids_limit",
        "ulimits",
        "mem_limit",
        "nano_cpus",
        "network_mode"
    ]
    return {k: settings[k] for k in allowed if k in settings}

# ---------------------------------------------------------------------------
# INTERNAL USE ONLY
# ---------------------------------------------------------------------------

def run_agent(image_ref: str, extra_env: dict | None = None) -> dict:
    """
    Run an agent image as a blocking task.

    This method is intended for local tests or short debug runs.
    It should not be used for real matches, because it waits for the
    container to finish and removes it afterwards.

    Use start_agent_container() for actual match execution.
    """

    client = docker.from_env()
    settings = _load_secure_defaults()
    run_kwargs = _build_docker_run_kwargs(settings)

    base_env = settings.get("env") or {}
    env = dict(base_env)
    if extra_env:
        env.update(extra_env)

    time_limit = settings.get("time_limit_seconds", 30)
    log_tail = settings.get("log_tail", 10000)
    stop_timeout = settings.get("stop_timeout", 2)

    try:
        container = client.containers.run(
            image_ref,
            detach=True,
            environment=env,
            **run_kwargs
        )
    except docker.errors.ImageNotFound:
        raise RunError(f"Image not found: {image_ref}")
    except Exception as e:
        raise RunError(f"Failed to start container: {e}")

    timeout_flag = False
    exit_code = None

    try:
        result = container.wait(timeout=time_limit)
        exit_code = result.get("StatusCode")
    except Exception:
        timeout_flag = True
        try:
            container.stop(timeout=stop_timeout)
        except Exception:
            pass
        try:
            container.kill()
        except Exception:
            pass
        exit_code = 124 # standard timeout code

    try:
        raw_logs = container.logs(stdout=True, stderr=True, tail=log_tail)
    except Exception:
        raw_logs = b""

    logs = raw_logs.decode(errors="replace")

    try:
        container.remove(force=True)
    except Exception:
        pass

    return {
        "exit_code": exit_code,
        "timeout": timeout_flag,
        "logs": logs,
        "container_id": container.id
    }

# ---------------------------------------------------------------------------
# PUBLIC API – for match execution
# ---------------------------------------------------------------------------

def start_agent_container(
        image_ref: str,
        *,
        match_id: str,
        agent_id: str,
        owner_id: str,
        extra_env: dict[str, str] | None = None,
        name: str | None = None
) -> dict:
    """
    Start a long-running agent container for a match.

    The container runs independently and is not removed automatically.
    It stays active until stopped or deleted by management functions.

    Returns a dict containing:
        container_id: Docker container ID
        name:         assigned container name
        image:        image reference used
    """
    
    client = docker.from_env()
    settings = _load_secure_defaults()
    run_kwargs = _build_docker_run_kwargs(settings)

    base_env = settings.get("env") or {}
    env = dict(base_env)
    if extra_env:
        env.update(extra_env)

    if name is None:
        name = f"match-{match_id}-agent-{agent_id}"
    
    labels = {
        "org.gameai.kind": "agent-container",
        "org.gameai.owner_id": owner_id,
        "org.gameai.agent_id": agent_id,
        "org.gameai.match_id": match_id
    }

    try:
        container = client.containers.run(
            image_ref,
            detach=True,
            name=name,
            environment=env,
            labels=labels,
            **run_kwargs
        )
    except docker.errors.ImageNotFound:
        raise RunError(f"Image not found: {image_ref}")
    except Exception as e:
        raise RunError(f"Failed to start container: {e}")
    
    return {
        "conatiner_id": container.id,
        "name": container.name,
        "image": image_ref
    }




if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run a built agent image with secure defaults.")
    parser.add_argument("image_ref", help="Image tag or ID, e.g. agent-1234abcd")
    args = parser.parse_args()

    try:
        result = run_agent(args.image_ref)
        print("Exit code:", result["exit_code"])
        print("Timeout:", result["timeout"])
        print("--- Logs ---")
        print(result["logs"])
    except Exception as e:
        print("Run failed:", e)
        exit(1)