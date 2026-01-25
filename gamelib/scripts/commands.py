"""Scripts for linting, formatting, and type-checking the gamelib package."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence


def lint() -> int:
    """Run linting checks with ruff."""
    print("🔍 Running ruff linter...")
    result = subprocess.run(
        ["ruff", "check", "."],
        check=False,
        capture_output=False,
    )

    if result.returncode != 0:
        print("\n❌ Linting failed! Run 'uv run format' to auto-fix issues.")
        return result.returncode

    print("✅ All linting checks passed!")
    return 0


def format_code() -> int:
    """Format code with ruff."""
    print("🎨 Formatting code with ruff...")

    format_result = subprocess.run(
        ["ruff", "format", "."],
        check=False,
        capture_output=False,
    )

    fix_result = subprocess.run(
        ["ruff", "check", "--fix", "."],
        check=False,
        capture_output=False,
    )

    if format_result.returncode != 0 or fix_result.returncode != 0:
        print("\n❌ Formatting failed!")
        return max(format_result.returncode, fix_result.returncode)

    print("✅ Code formatted successfully!")
    return 0


def type_check() -> int:
    """Run type checks with mypy."""
    print("🧠 Running mypy type checks...")
    result = subprocess.run(
        ["mypy", "."],
        check=False,
        capture_output=False,
    )

    if result.returncode != 0:
        print("\n❌ Type checking failed!")
        return result.returncode

    print("✅ All type checks passed!")
    return 0


def checks_all() -> int:
    """Run formatting, linting, and type checking guards in sequence."""
    print("🚀 Running all checks...\n")

    format_result = format_code()
    if format_result != 0:
        print("\n❌ All checks failed at formatting stage!")
        return format_result

    print()

    lint_result = lint()
    if lint_result != 0:
        print("\n❌ All checks failed at linting stage!")
        return lint_result

    print()

    type_result = type_check()
    if type_result != 0:
        print("\n❌ All checks failed at type checking stage!")
        return type_result

    print("\n✅ All checks passed successfully!")
    return 0


COMMANDS: dict[str, Callable[[], int]] = {
    "lint": lint,
    "format": format_code,
    "type-check": type_check,
    "checks-all": checks_all,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch the requested command and return its exit code."""
    parser = argparse.ArgumentParser(description="Run gamelib maintenance commands.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=COMMANDS,
        default="lint",
        help="Command to run (default: lint).",
    )
    args = parser.parse_args(argv)

    return COMMANDS[args.command]()


if __name__ == "__main__":
    sys.exit(main())
