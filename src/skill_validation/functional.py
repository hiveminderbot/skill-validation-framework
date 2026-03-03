"""Functional testing module for OpenClaw skills.

This module provides actual functional testing capabilities for skills,
including test case definitions, sandboxed execution, and result validation.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TestCase:
    """Definition of a single functional test case."""

    name: str
    description: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any] | None = None
    expected_behavior: str | None = None
    timeout_seconds: int = 30
    requires_tools: list[str] = field(default_factory=list)
    setup_commands: list[str] = field(default_factory=list)
    cleanup_commands: list[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Result of running a functional test."""

    test_name: str
    passed: bool
    duration_ms: float
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    message: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    """A collection of test cases for a skill."""

    name: str
    description: str
    test_cases: list[TestCase]
    setup_commands: list[str] = field(default_factory=list)
    cleanup_commands: list[str] = field(default_factory=list)


class TestCaseParser:
    """Parse test case definitions from YAML files."""

    @staticmethod
    def parse_file(path: Path) -> TestSuite:
        """Parse a test suite from a YAML file."""
        content = yaml.safe_load(path.read_text(encoding="utf-8"))

        test_cases = []
        for tc_data in content.get("tests", []):
            test_cases.append(
                TestCase(
                    name=tc_data["name"],
                    description=tc_data.get("description", ""),
                    input_data=tc_data.get("input", {}),
                    expected_output=tc_data.get("expected_output"),
                    expected_behavior=tc_data.get("expected_behavior"),
                    timeout_seconds=tc_data.get("timeout_seconds", 30),
                    requires_tools=tc_data.get("requires_tools", []),
                    setup_commands=tc_data.get("setup_commands", []),
                    cleanup_commands=tc_data.get("cleanup_commands", []),
                )
            )

        return TestSuite(
            name=content.get("name", "Unnamed Suite"),
            description=content.get("description", ""),
            test_cases=test_cases,
            setup_commands=content.get("setup_commands", []),
            cleanup_commands=content.get("cleanup_commands", []),
        )

    @staticmethod
    def parse_directory(path: Path) -> list[TestSuite]:
        """Parse all test suites from a directory."""
        suites = []
        tests_dir = path / "tests"

        if not tests_dir.exists():
            return suites

        for file_path in tests_dir.iterdir():
            if file_path.suffix in (".yaml", ".yml"):
                try:
                    suites.append(TestCaseParser.parse_file(file_path))
                except Exception as e:
                    # Log error but continue with other test files
                    print(f"Error parsing {file_path}: {e}")

        return suites


class SandboxedExecutor:
    """Execute tests in a sandboxed environment."""

    def __init__(self, skill_path: Path, temp_dir: Path | None = None):
        self.skill_path = Path(skill_path)
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp(prefix="skill_test_"))
        self.env = os.environ.copy()
        self.env["SKILL_PATH"] = str(self.skill_path)
        self.env["TEST_MODE"] = "1"

    def execute(
        self,
        command: list[str],
        input_data: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> tuple[int, str, str]:
        """Execute a command and return exit code, stdout, stderr."""
        try:
            # Write input data to temp file if provided
            input_file = None
            if input_data:
                input_file = self.temp_dir / "input.json"
                input_file.write_text(json.dumps(input_data))
                self.env["TEST_INPUT_FILE"] = str(input_file)

            # Run the command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self.env,
                cwd=str(self.temp_dir),
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -1, "", str(e)

    def cleanup(self) -> None:
        """Clean up temporary files."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class FunctionalTester:
    """Main functional testing engine."""

    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        self.results: list[TestResult] = []
        self.test_suites: list[TestSuite] = []

    def load_tests(self) -> bool:
        """Load test suites from the skill's tests directory."""
        self.test_suites = TestCaseParser.parse_directory(self.skill_path)
        return len(self.test_suites) > 0

    def run_tests(self) -> list[TestResult]:
        """Run all loaded functional tests."""
        self.results = []

        for suite in self.test_suites:
            self._run_suite(suite)

        return self.results

    def _run_suite(self, suite: TestSuite) -> None:
        """Run all tests in a suite."""
        import time

        # Run suite-level setup
        executor = SandboxedExecutor(self.skill_path)

        for cmd in suite.setup_commands:
            exit_code, stdout, stderr = executor.execute(cmd.split())
            if exit_code != 0:
                # Suite setup failed, mark all tests as failed
                for tc in suite.test_cases:
                    self.results.append(
                        TestResult(
                            test_name=f"{suite.name}/{tc.name}",
                            passed=False,
                            duration_ms=0,
                            message=f"Suite setup failed: {stderr}",
                        )
                    )
                executor.cleanup()
                return

        # Run each test case
        for test_case in suite.test_cases:
            start_time = time.time()

            # Check required tools
            missing_tools = self._check_required_tools(test_case.requires_tools)
            if missing_tools:
                duration_ms = (time.time() - start_time) * 1000
                self.results.append(
                    TestResult(
                        test_name=f"{suite.name}/{test_case.name}",
                        passed=False,
                        duration_ms=duration_ms,
                        message=f"Missing required tools: {', '.join(missing_tools)}",
                    )
                )
                continue

            # Run test case setup
            setup_failed = False
            for cmd in test_case.setup_commands:
                exit_code, _, stderr = executor.execute(cmd.split())
                if exit_code != 0:
                    setup_failed = True
                    duration_ms = (time.time() - start_time) * 1000
                    self.results.append(
                        TestResult(
                            test_name=f"{suite.name}/{test_case.name}",
                            passed=False,
                            duration_ms=duration_ms,
                            message=f"Test setup failed: {stderr}",
                        )
                    )
                    break

            if setup_failed:
                continue

            # Run the actual test
            exit_code, stdout, stderr = executor.execute(
                ["python", "-m", "skill_validation.test_runner"],
                input_data=test_case.input_data,
                timeout=test_case.timeout_seconds,
            )

            duration_ms = (time.time() - start_time) * 1000

            # Validate results
            passed, message = self._validate_result(test_case, exit_code, stdout, stderr)

            self.results.append(
                TestResult(
                    test_name=f"{suite.name}/{test_case.name}",
                    passed=passed,
                    duration_ms=duration_ms,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    message=message,
                )
            )

            # Run test case cleanup
            for cmd in test_case.cleanup_commands:
                executor.execute(cmd.split())

        # Run suite-level cleanup
        for cmd in suite.cleanup_commands:
            executor.execute(cmd.split())

        executor.cleanup()

    def _check_required_tools(self, tools: list[str]) -> list[str]:
        """Check which required tools are missing."""
        missing = []
        for tool in tools:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
            )
            if result.returncode != 0:
                missing.append(tool)
        return missing

    def _validate_result(
        self,
        test_case: TestCase,
        exit_code: int,
        stdout: str,
        stderr: str,
    ) -> tuple[bool, str]:
        """Validate test results against expectations."""
        # Check exit code
        if exit_code != 0:
            return False, f"Non-zero exit code: {exit_code}"

        # Check expected output if defined
        if test_case.expected_output:
            try:
                actual_output = json.loads(stdout)
                if not self._compare_outputs(test_case.expected_output, actual_output):
                    return False, f"Output mismatch. Expected: {test_case.expected_output}"
            except json.JSONDecodeError:
                return False, f"Output is not valid JSON: {stdout[:200]}"

        # Check expected behavior if defined
        if test_case.expected_behavior:
            if (
                test_case.expected_behavior not in stdout
                and test_case.expected_behavior not in stderr
            ):
                return (
                    False,
                    f"Expected behavior '{test_case.expected_behavior}' not found in output",
                )

        return True, "Test passed"

    def _compare_outputs(self, expected: dict[str, Any], actual: dict[str, Any]) -> bool:
        """Compare expected vs actual output (subset matching)."""
        for key, value in expected.items():
            if key not in actual:
                return False
            if actual[key] != value:
                return False
        return True

    def get_summary(self) -> dict[str, Any]:
        """Get test execution summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total_duration = sum(r.duration_ms for r in self.results)

        return {
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self.results) if self.results else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / len(self.results) if self.results else 0,
        }


def run_functional_tests(skill_path: Path) -> tuple[list[TestResult], dict[str, Any]]:
    """Convenience function to run functional tests on a skill."""
    tester = FunctionalTester(skill_path)

    if not tester.load_tests():
        return [], {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0,
            "message": "No functional tests found",
        }

    results = tester.run_tests()
    summary = tester.get_summary()
    return results, summary
