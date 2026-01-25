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
    """Run all checks: format, lint, and type-check."""
    print("🚀 Running all checks...\n")

    # Run format first
    format_result = format_code()
    if format_result != 0:
        print("\n❌ All checks failed at formatting stage!")
        return format_result

    print()  # Add spacing

    # Run lint
    lint_result = lint()
    if lint_result != 0:
        print("\n❌ All checks failed at linting stage!")
        return lint_result

    print()  # Add spacing

    # Run type check
    type_result = type_check()
    if type_result != 0:
        print("\n❌ All checks failed at type checking stage!")
        return type_result

    print("\n✅ All checks passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(lint())
