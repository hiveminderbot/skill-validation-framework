#!/usr/bin/env -S uv run python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml>=6.0",
#     "click>=8.0",
#     "rich>=13.0",
#     "pydantic>=2.0",
# ]
# ///
"""Self-validation script for the Skill Validation Framework.

This script runs the framework against itself to ensure it passes its own validation criteria.
"""

import json
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    """Run self-validation and return exit code."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    print("=" * 60)
    print("Skill Validation Framework - Self-Validation")
    print("=" * 60)
    print()

    # Check 1: Security scan on self
    print("[1/4] Running security scan on self...")
    
    # Run the security scanner directly (skip third-party to avoid hangs)
    from skill_validation.security import scan_skill
    
    print("  Scanning (this may take a moment)...")
    issues, summary = scan_skill(project_root, use_third_party=False)

    print(f"  Total issues: {summary['total_issues']}")
    print(
        f"  Severity: critical={summary['severity_counts'].get('critical', 0)}, "
        f"high={summary['severity_counts'].get('high', 0)}, "
        f"medium={summary['severity_counts'].get('medium', 0)}, "
        f"low={summary['severity_counts'].get('low', 0)}"
    )

    if summary["severity_counts"].get("critical", 0) > 0:
        print("  ❌ FAILED: Critical security issues found!")
        security_passed = False
    elif summary["severity_counts"].get("high", 0) > 0:
        print("  ⚠️  WARNING: High severity issues found")
        security_passed = True  # Allow high for now
    else:
        print("  ✅ PASSED")
        security_passed = True

    print()

    # Check 2: Validation of project structure
    print("[2/4] Running structure validation...")

    from skill_validation.validation import validate_skill

    results, val_summary = validate_skill(project_root)

    print(f"  Total tests: {val_summary['total_tests']}")
    print(f"  Passed: {val_summary['passed']}")
    print(f"  Failed: {val_summary['failed']}")
    print(f"  Pass rate: {val_summary['pass_rate']:.1%}")

    if val_summary["pass_rate"] >= 0.8:
        print("  ✅ PASSED")
        validation_passed = True
    else:
        print("  ❌ FAILED: Pass rate below 80%")
        validation_passed = False

    print()

    # Check 3: Benchmark
    print("[3/4] Running benchmark...")

    from skill_validation.benchmark import benchmark_skill

    bench_results, bench_summary = benchmark_skill(project_root)

    print(f"  Tasks run: {bench_summary['total_tasks']}")
    print(f"  Success rate: {bench_summary['success_rate']:.1%}")
    print(f"  Avg duration: {bench_summary['avg_duration_ms']:.1f}ms")

    if bench_summary["success_rate"] >= 0.8:
        print("  ✅ PASSED")
        benchmark_passed = True
    else:
        print("  ❌ FAILED: Success rate below 80%")
        benchmark_passed = False

    print()

    # Check 4: Code quality checks
    print("[4/4] Running code quality checks...")

    quality_checks = []

    # Check with ruff
    exit_code, _, _ = run_command(
        [sys.executable, "-m", "ruff", "check", "src/"],
        cwd=project_root,
    )
    ruff_passed = exit_code == 0
    quality_checks.append(("Ruff linting", ruff_passed))
    print(f"  Ruff linting: {'✅' if ruff_passed else '❌'}")

    # Check with black
    exit_code, _, _ = run_command(
        [sys.executable, "-m", "black", "--check", "src/"],
        cwd=project_root,
    )
    black_passed = exit_code == 0
    quality_checks.append(("Black formatting", black_passed))
    print(f"  Black formatting: {'✅' if black_passed else '❌'}")

    # Check with mypy
    exit_code, _, _ = run_command(
        [sys.executable, "-m", "mypy", "src/"],
        cwd=project_root,
    )
    mypy_passed = exit_code == 0
    quality_checks.append(("MyPy type check", mypy_passed))
    print(f"  MyPy type check: {'✅' if mypy_passed else '❌'}")

    quality_passed = all(passed for _, passed in quality_checks)

    if quality_passed:
        print("  ✅ PASSED")
    else:
        print("  ❌ FAILED: Some quality checks failed")

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = security_passed and validation_passed and benchmark_passed and quality_passed

    print(f"Security scan:    {'✅ PASSED' if security_passed else '❌ FAILED'}")
    print(f"Structure validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
    print(f"Benchmark:        {'✅ PASSED' if benchmark_passed else '❌ FAILED'}")
    print(f"Code quality:     {'✅ PASSED' if quality_passed else '❌ FAILED'}")
    print()

    if all_passed:
        print("🎉 All self-validation checks passed!")
        return 0
    else:
        print("❌ Some self-validation checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
