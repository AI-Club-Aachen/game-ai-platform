"""
Agent runner for managing and executing game agents in a safe dockerized environment.
"""

import docker
import yaml
import time
from pathlib import Path

class RunError(Exception):
    pass


def load_secure_defaults() -> dict:
    settings_path = Path(__file__).parent / "secure_default_settings.yaml"
    if not settings_path.exists():
        raise RunError("secure_default_settings.yaml not found.")
    return yaml.safe_load(settings_path.read_text(encoding="utf-8"))

def build_docker_run_kwargs(settings):
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

def run_agent(image_ref: str, extra_env: dict | None = None) -> dict:
    client = docker.from_env()
    settings = load_secure_defaults()
    run_kwargs = build_docker_run_kwargs(settings)

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
