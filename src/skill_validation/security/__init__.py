"""Security scanner for OpenClaw skills."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SecurityIssue:
    """Represents a security issue found in a skill."""

    severity: str  # critical, high, medium, low
    category: str  # secret, eval, network, filesystem, etc.
    file: Path
    line: int
    message: str
    snippet: str


class SecurityScanner:
    """Scans skills for security issues."""

    # Patterns to detect - using explicit type to help mypy
    PATTERNS: dict[str, dict[str, Any]] = {
        "secret": {
            "severity": "critical",
            "patterns": [
                r'[a-zA-Z0-9_-]*(?:api[_-]?key|token|secret|password|credential)["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
                r"gh[pousr]_[A-Za-z0-9_]{36,}",
                r"sk-[a-zA-Z0-9]{48}",
                r"AKIA[0-9A-Z]{16}",
            ],
        },
        "eval": {
            "severity": "high",
            "patterns": [
                r"\beval\s*\(",
                r"\bexec\s*\(",
                r"__import__\s*\(",
                r"subprocess\.call\s*\([^)]*shell\s*=\s*True",
                r"os\.system\s*\(",
            ],
        },
        "network": {
            "severity": "medium",
            "patterns": [
                r"urllib\.request\.urlopen",
                r"requests\.(get|post|put|delete)",
                r"http\.client\.HTTPConnection",
            ],
        },
        "filesystem": {
            "severity": "low",
            "patterns": [
                r'open\s*\([^)]*,\s*["\']w',
                r"shutil\.(rmtree|move)",
                r"os\.(remove|unlink|rmdir)",
            ],
        },
    }

    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        self.issues: list[SecurityIssue] = []

    def scan(self) -> list[SecurityIssue]:
        """Scan the skill for security issues."""
        self.issues = []

        # Scan all files in the skill directory
        for file_path in self.skill_path.rglob("*"):
            if file_path.is_file() and self._should_scan(file_path):
                self._scan_file(file_path)

        return self.issues

    def _should_scan(self, file_path: Path) -> bool:
        """Determine if a file should be scanned."""
        # Skip binary files and common non-code files
        skip_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".ttf",
            ".woff",
            ".woff2",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
        }
        if file_path.suffix in skip_extensions:
            return False

        # Skip directories that don't need scanning
        skip_dirs = [
            ".git/",
            ".venv/",
            "venv/",
            "__pycache__/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            "node_modules/",
            ".tox/",
            "dist/",
            "build/",
            ".egg-info/",
        ]

        path_str = str(file_path)
        for skip_dir in skip_dirs:
            if skip_dir in path_str:
                return False

        # Skip test files (they often contain intentional examples of patterns)
        # Use word boundaries to avoid matching pytest temp dirs like /tmp/pytest-*/test_*
        skip_patterns = [
            "/test_",  # Test files in a directory (but not pytest temp dirs)
            "_test.py",  # Files ending with _test.py
            "/tests/",  # Tests directories
            ".pyc",  # Compiled Python
        ]

        # Special case: don't skip files in pytest temp directories that happen
        # to have 'test' in path. Pytest uses /tmp/pytest-of-*/pytest-*/test_*/
        if "/pytest-of-" in path_str and "/pytest-" in path_str:
            # This is a pytest temp directory, check only the actual filename
            filename = file_path.name
            if filename.startswith("test_") or filename.endswith("_test.py"):
                return False
            return file_path.suffix not in {".pyc"}

        return all(pattern not in path_str for pattern in skip_patterns)

    def _scan_file(self, file_path: Path) -> None:
        """Scan a single file for security issues."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            for category, config in self.PATTERNS.items():
                for pattern in config["patterns"]:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        # Find line number
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                        issue = SecurityIssue(
                            severity=config["severity"],
                            category=category,
                            file=file_path.relative_to(self.skill_path),
                            line=line_num,
                            message=f"Potential {category} issue detected",
                            snippet=line_content.strip()[:100],
                        )
                        self.issues.append(issue)
        except Exception as e:
            # Log error but continue scanning other files
            print(f"Error scanning {file_path}: {e}")

    def get_summary(self) -> dict:
        """Get a summary of scan results."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        return {
            "total_issues": len(self.issues),
            "severity_counts": severity_counts,
            "passed": len(self.issues) == 0,
        }


def scan_skill(
    skill_path: Path,
    use_third_party: bool = False,
    third_party_scanners: list[str] | None = None,
) -> tuple[list[SecurityIssue], dict]:
    """Convenience function to scan a skill.

    Args:
        skill_path: Path to the skill directory
        use_third_party: Whether to run third-party scanners
        third_party_scanners: List of specific scanners to use (None = all available)

    Returns:
        Tuple of (issues list, summary dict)
    """
    scanner = SecurityScanner(skill_path)
    issues = scanner.scan()
    summary = scanner.get_summary()

    # Run third-party scanners if requested
    if use_third_party:
        from skill_validation.security.third_party import ThirdPartyScannerManager

        manager = ThirdPartyScannerManager(skill_path)

        # Determine which scanners to run
        scanners_to_run = third_party_scanners or manager.get_available_scanners()

        for scanner_name in scanners_to_run:
            if manager.register_scanner(scanner_name):
                third_party_issues = manager.scanners[scanner_name].scan()
                issues.extend(third_party_issues)

        # Recalculate summary with third-party results
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        summary = {
            "total_issues": len(issues),
            "severity_counts": severity_counts,
            "passed": len(issues) == 0,
            "third_party_scanners": list(manager.scanners.keys()),
        }

    return issues, summary
