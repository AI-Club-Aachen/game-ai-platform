#!/usr/bin/env python3
"""
Keep environment configuration consistent, so no setting is silently ignored.

    python3 scripts/check_env.py                    # repo consistency (runs in CI)
    python3 scripts/check_env.py --env-file FILE    # audit a real env file, e.g. a copy of Dokploy's

Repo mode checks that
  * every backend Settings field is passed to the backend container by docker-compose.yml,
    as ${NAME:-} (default lives in code) or ${NAME:?...} (required), and nothing else is passed;
  * every env var the workers read is passed to a worker container;
  * every variable docker-compose.yml uses is documented in .env.example, every documented
    variable is used somewhere, and the "[UI]" markers match the admin-editable settings.

Env-file mode reports required variables that are missing and variables nothing uses
(typos or leftovers such as a renamed setting).

Needs only Python 3.10+ and `docker compose` (to read the compose file).
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"
SETTINGS_FILE = ROOT / "backend/app/core/config.py"
RUNTIME_SETTINGS_FILE = ROOT / "backend/app/core/runtime_settings.py"
WORKER_SOURCES = [*ROOT.glob("orchestration/*.py"), *ROOT.glob("orchestration/lib/*.py")]
WORKER_SERVICES = ("agent-builder", "match-runner")

# Settings fields deliberately not passed to the backend container (with the reason).
NOT_PASSED = {
    "UPLOAD_DIR": "must match the volume mount in the backend image",
    "SUBMISSIONS_DIR": "must match the volume mount in the backend image",
}
# Backend container vars that are not Settings fields.
EXTRA_BACKEND_VARS = {
    "BACKEND_PORT": "read by the Dockerfile CMD",
    "SEED_DB": "read directly by app/main.py at startup",
}
# Settings whose compose value is built from other variables instead of ${NAME...}.
DERIVED = {"DATABASE_URL", "REDIS_URL"}
# Env vars the worker code reads that are not meant for the worker containers.
WORKER_VARS_NOT_PASSED = {"AGENT_FILE", "AGENT_ONLINE"}
# Documented in .env.example but used outside docker-compose (local runs, tests).
USED_OUTSIDE_COMPOSE = {"DATABASE_URL", "REDIS_URL", "BACKEND_URL", "TEST_DATABASE_URL"}

VAR_REF = re.compile(r"\$\{([A-Z][A-Z0-9_]*)(:?[-?])?")
EXAMPLE_LINE = re.compile(r"^#?\s*(\[UI\]\s*)?([A-Z][A-Z0-9_]*)=")
WORKER_ENV_READ = re.compile(r"""os\.(?:getenv|environ\.get)\(\s*["']([A-Z][A-Z0-9_]*)["']|os\.environ\[\s*["']([A-Z][A-Z0-9_]*)["']\]""")


def settings_fields() -> set[str]:
    tree = ast.parse(SETTINGS_FILE.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Settings")
    return {
        stmt.target.id
        for stmt in cls.body
        if isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.target, ast.Name)
        and "ClassVar" not in ast.unparse(stmt.annotation)
    }


def editable_settings() -> set[str]:
    tree = ast.parse(RUNTIME_SETTINGS_FILE.read_text())
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "EDITABLE_SETTINGS":
            assert isinstance(node.value, ast.Dict)
            return {ast.literal_eval(key) for key in node.value.keys if key is not None}
    raise SystemExit("EDITABLE_SETTINGS not found in runtime_settings.py")


def compose_services() -> dict:
    try:
        out = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config", "--no-interpolate", "--format", "json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise SystemExit(f"Could not read {COMPOSE.name} with `docker compose config`: {e}") from e
    return json.loads(out)["services"]


def service_env(service: dict) -> dict[str, str]:
    env = service.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) if "=" in item else (item, "") for item in env)
    return {key: "" if value is None else str(value) for key, value in env.items()}


def compose_vars(path: Path) -> dict[str, str]:
    """Variables referenced in a compose file -> "required" or "optional"."""
    found: dict[str, str] = {}
    for name, op in VAR_REF.findall(path.read_text()):
        if op.endswith("?"):
            found[name] = "required"
        else:
            found.setdefault(name, "optional")
    return found


def example_vars() -> tuple[set[str], set[str]]:
    """Names documented in .env.example (commented or not), and those marked [UI]."""
    names: set[str] = set()
    ui: set[str] = set()
    pending_ui = False
    for line in ENV_EXAMPLE.read_text().splitlines():
        match = EXAMPLE_LINE.match(line.strip())
        if match:
            names.add(match.group(2))
            if match.group(1) or pending_ui:
                ui.add(match.group(2))
            pending_ui = False
        elif line.lstrip("# ").startswith("[UI]"):
            pending_ui = True  # a "# [UI] ..." comment line marks the next variable
    return names, ui


def check_repo() -> list[str]:
    errors: list[str] = []
    services = compose_services()
    backend_env = service_env(services["backend"])
    fields = settings_fields()

    for name in sorted(fields - backend_env.keys() - NOT_PASSED.keys()):
        errors.append(f"Settings.{name} is not passed to the backend in docker-compose.yml (add `{name}: ${{{name}:-}}`)")
    for name in sorted(backend_env.keys() - fields - EXTRA_BACKEND_VARS.keys()):
        errors.append(f"backend env {name} in docker-compose.yml is not a Settings field (typo or obsolete?)")
    for name, value in sorted(backend_env.items()):
        if name not in fields or name in DERIVED:
            continue
        if not re.fullmatch(rf"\$\{{{name}(:-|:\?[^}}]*)\}}", value):
            errors.append(
                f"backend env {name}={value!r}: use ${{{name}:-}} (default in config.py) or ${{{name}:?...}} (required)"
            )

    worker_env = set().union(*(service_env(services[s]).keys() for s in WORKER_SERVICES))
    worker_reads = {m[0] or m[1] for f in WORKER_SOURCES for m in WORKER_ENV_READ.findall(f.read_text())}
    for name in sorted(worker_reads - worker_env - WORKER_VARS_NOT_PASSED):
        errors.append(f"orchestration reads {name}, but no worker service in docker-compose.yml passes it")

    used = compose_vars(COMPOSE)
    for extra in ROOT.glob("docker-compose.*.yml"):
        used.update({k: v for k, v in compose_vars(extra).items() if k not in used})
    documented, marked_ui = example_vars()
    for name in sorted(compose_vars(COMPOSE).keys() - documented):
        errors.append(f"{name} is used in docker-compose.yml but not documented in .env.example")
    for name in sorted(documented - used.keys() - USED_OUTSIDE_COMPOSE):
        errors.append(f"{name} is documented in .env.example but no compose file uses it (obsolete?)")
    editable = editable_settings()
    for name in sorted(editable - marked_ui):
        errors.append(f"{name} is editable on the settings page; mark it [UI] in .env.example")
    for name in sorted(marked_ui - editable):
        errors.append(f"{name} is marked [UI] in .env.example but is not editable on the settings page")
    return errors


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def audit_env_file(path: Path) -> list[str]:
    errors: list[str] = []
    env = parse_env_file(path)
    used = compose_vars(COMPOSE)
    documented, _ = example_vars()

    for name in sorted(n for n, kind in used.items() if kind == "required" and not env.get(n)):
        errors.append(f"missing required variable {name}")
    for name in sorted(env.keys() - used.keys()):
        if name in USED_OUTSIDE_COMPOSE:
            print(f"note: {name} is only used outside docker-compose; the deployment ignores it")
        elif name in documented:
            print(f"note: {name} is documented but not used by docker-compose.yml")
        else:
            errors.append(f"{name} is not used anywhere (typo, or a renamed/removed setting?)")
    unset = sorted(n for n, kind in used.items() if kind == "optional" and not env.get(n))
    if unset:
        print(f"info: {len(unset)} optional variable(s) unset, using defaults: {', '.join(unset)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, help="audit this env file instead of checking the repo")
    args = parser.parse_args()

    errors = audit_env_file(args.env_file) if args.env_file else check_repo()
    for error in errors:
        print(f"error: {error}")
    if not errors:
        print("OK: environment configuration is consistent")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
