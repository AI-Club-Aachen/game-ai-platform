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
        "network_mode",
        "stop_timeout",
    ]
    return {k: settings[k] for k in allowed if k in settings}

def run_agent(image_ref: str, extra_env: dict | None = None) -> dict:
    return {}



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
