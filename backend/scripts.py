"""
Scripts for linting and formatting code.
These are called by the project scripts defined in pyproject.toml.
"""

import subprocess
import sys


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

    # Run ruff format
    format_result = subprocess.run(
        ["ruff", "format", "."],
        check=False,
        capture_output=False,
    )

    # Run ruff check with --fix
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


if __name__ == "__main__":
    sys.exit(lint())
