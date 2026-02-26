#!/usr/bin/env python3
"""Setup script for skill-validation-framework development environment."""

import subprocess
import sys
from pathlib import Path


def setup_git_hooks() -> bool:
    """Configure git to use the project's hooks."""
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".githooks"

    if not hooks_dir.exists():
        print(f"❌ Hooks directory not found: {hooks_dir}")
        return False

    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", str(hooks_dir)],
            cwd=project_root,
            check=True,
        )
        print(f"✅ Git hooks configured to use: {hooks_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to configure git hooks: {e}")
        return False


def install_dependencies() -> bool:
    """Install development dependencies."""
    project_root = Path(__file__).parent.parent

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev,security]"],
            cwd=project_root,
            check=True,
        )
        print("✅ Development dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def main() -> int:
    """Run setup."""
    print("=" * 60)
    print("Skill Validation Framework - Development Setup")
    print("=" * 60)
    print()

    success = True

    print("[1/2] Installing dependencies...")
    if not install_dependencies():
        success = False

    print()
    print("[2/2] Configuring git hooks...")
    if not setup_git_hooks():
        success = False

    print()
    print("=" * 60)
    if success:
        print("✅ Setup complete!")
        print()
        print("Next steps:")
        print("  1. Run 'python scripts/self_validate.py' to verify")
        print("  2. Make your changes")
        print("  3. Commit - pre-commit hooks will run automatically")
    else:
        print("⚠️  Setup completed with warnings.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
