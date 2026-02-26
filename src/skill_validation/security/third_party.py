"""Third-party security scanner integrations."""

import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_validation.security import SecurityIssue


@dataclass
class ThirdPartyScannerConfig:
    """Configuration for third-party scanners."""

    enabled: bool = True
    severity_threshold: str = "low"  # low, medium, high, critical
    extra_args: list[str] | None = None


class ThirdPartyScanner(ABC):
    """Base class for third-party security scanner integrations."""

    def __init__(self, skill_path: Path, config: ThirdPartyScannerConfig | None = None):
        self.skill_path = Path(skill_path)
        self.config = config or ThirdPartyScannerConfig()
        self.issues: list[SecurityIssue] = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Scanner name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the scanner is installed and available."""
        pass

    @abstractmethod
    def scan(self) -> list[SecurityIssue]:
        """Run the scanner and return issues."""
        pass

    def _run_command(self, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a subprocess command safely."""
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.skill_path),
            **kwargs,
        )


class BanditScanner(ThirdPartyScanner):
    """Bandit SAST scanner integration for Python code."""

    SEVERITY_MAP = {
        "LOW": "low",
        "MEDIUM": "medium",
        "HIGH": "high",
    }

    CONFIDENCE_MAP = {
        "LOW": 0.3,
        "MEDIUM": 0.6,
        "HIGH": 1.0,
    }

    @property
    def name(self) -> str:
        return "bandit"

    @property
    def is_available(self) -> bool:
        """Check if bandit is installed."""
        try:
            result = self._run_command(["bandit", "--version"], check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def scan(self) -> list[SecurityIssue]:
        """Run bandit scan and convert results."""
        self.issues = []

        if not self.is_available:
            return self.issues

        cmd = [
            "bandit",
            "-r",  # recursive
            "-f", "json",  # JSON output
            "-ll",  # severity level (low and above)
            str(self.skill_path),
        ]

        if self.config.extra_args:
            cmd.extend(self.config.extra_args)

        result = self._run_command(cmd, check=False)

        # Bandit returns 1 when issues found, which is expected
        if result.returncode not in (0, 1):
            return self.issues

        try:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                try:
                    filename = issue.get("filename", "")
                    file_path = Path(filename)
                    # Handle both absolute and relative paths
                    if file_path.is_absolute():
                        file_path = file_path.relative_to(self.skill_path.resolve())
                    else:
                        file_path = file_path.relative_to(self.skill_path)
                except ValueError:
                    # If relative_to fails, use the filename as-is
                    file_path = Path(filename)

                security_issue = SecurityIssue(
                    severity=self.SEVERITY_MAP.get(issue.get("issue_severity", "LOW"), "low"),
                    category=f"bandit:{issue.get('test_id', 'unknown')}",
                    file=file_path,
                    line=issue.get("line_number", 0),
                    message=issue.get("issue_text", "Unknown issue"),
                    snippet=issue.get("code", "")[:100],
                )
                self.issues.append(security_issue)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        return self.issues


class GitleaksScanner(ThirdPartyScanner):
    """Gitleaks secret detection integration."""

    SEVERITY_MAP = {
        "low": "low",
        "medium": "medium",
        "high": "high",
        "critical": "critical",
    }

    @property
    def name(self) -> str:
        return "gitleaks"

    @property
    def is_available(self) -> bool:
        """Check if gitleaks is installed."""
        try:
            result = self._run_command(["gitleaks", "version"], check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def scan(self) -> list[SecurityIssue]:
        """Run gitleaks scan and convert results."""
        self.issues = []

        if not self.is_available:
            return self.issues

        cmd = [
            "gitleaks",
            "detect",
            "-s", str(self.skill_path),
            "-f", "json",
            "-r", "/dev/stdout" if subprocess.os.name != "nt" else "CON",
            "--no-git",  # Don't scan git history, just files
            "-v",  # verbose
        ]

        if self.config.extra_args:
            cmd.extend(self.config.extra_args)

        result = self._run_command(cmd, check=False)

        # Gitleaks returns 1 when leaks found
        if result.returncode not in (0, 1):
            return self.issues

        try:
            # Gitleaks outputs one JSON object per line
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                issue = json.loads(line)
                try:
                    filename = issue.get("File", "")
                    file_path = Path(filename)
                    # Handle both absolute and relative paths
                    if file_path.is_absolute():
                        file_path = file_path.relative_to(self.skill_path.resolve())
                    else:
                        file_path = file_path.relative_to(self.skill_path)
                except ValueError:
                    # If relative_to fails, use the filename as-is
                    file_path = Path(filename)

                security_issue = SecurityIssue(
                    severity="critical",  # Secrets are always critical
                    category="secret",
                    file=file_path,
                    line=issue.get("StartLine", 0),
                    message=f"Potential secret: {issue.get('Description', 'Unknown')}",
                    snippet=issue.get("Match", "")[:100],
                )
                self.issues.append(security_issue)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        return self.issues


class SafetyScanner(ThirdPartyScanner):
    """Safety dependency vulnerability scanner integration."""

    @property
    def name(self) -> str:
        return "safety"

    @property
    def is_available(self) -> bool:
        """Check if safety is installed."""
        try:
            result = self._run_command(["safety", "--version"], check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def scan(self) -> list[SecurityIssue]:
        """Run safety scan and convert results."""
        self.issues = []

        if not self.is_available:
            return self.issues

        # Check for requirements files
        req_files = list(self.skill_path.rglob("requirements*.txt"))
        req_files.extend(self.skill_path.rglob("pyproject.toml"))
        req_files.extend(self.skill_path.rglob("poetry.lock"))
        req_files.extend(self.skill_path.rglob("Pipfile"))

        if not req_files:
            return self.issues

        for req_file in req_files:
            cmd = [
                "safety",
                "check",
                "--file", str(req_file),
                "--json",
            ]

            if self.config.extra_args:
                cmd.extend(self.config.extra_args)

            result = self._run_command(cmd, check=False)

            try:
                data = json.loads(result.stdout)
                for vuln in data.get("vulnerabilities", []):
                    security_issue = SecurityIssue(
                        severity=self._map_cvss(vuln.get("cvssv3_score")),
                        category="dependency",
                        file=req_file.relative_to(self.skill_path),
                        line=0,
                        message=f"{vuln.get('vulnerability_id', 'Unknown')}: {vuln.get('advisory', 'No details')}",
                        snippet=f"{vuln.get('package_name', 'unknown')} {vuln.get('vulnerable_spec', '')}",
                    )
                    self.issues.append(security_issue)
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        return self.issues

    def _map_cvss(self, score: float | None) -> str:
        """Map CVSS score to severity."""
        if score is None:
            return "medium"
        if score >= 9.0:
            return "critical"
        if score >= 7.0:
            return "high"
        if score >= 4.0:
            return "medium"
        return "low"


class ThirdPartyScannerManager:
    """Manages multiple third-party scanners."""

    SCANNERS = {
        "bandit": BanditScanner,
        "gitleaks": GitleaksScanner,
        "safety": SafetyScanner,
    }

    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        self.scanners: dict[str, ThirdPartyScanner] = {}

    def register_scanner(self, name: str, config: ThirdPartyScannerConfig | None = None) -> bool:
        """Register a scanner by name."""
        if name not in self.SCANNERS:
            return False

        scanner_class = self.SCANNERS[name]
        scanner = scanner_class(self.skill_path, config)

        if scanner.is_available:
            self.scanners[name] = scanner
            return True
        return False

    def scan_all(self) -> dict[str, list[SecurityIssue]]:
        """Run all registered scanners."""
        results = {}
        for name, scanner in self.scanners.items():
            results[name] = scanner.scan()
        return results

    def get_available_scanners(self) -> list[str]:
        """Get list of available scanner names."""
        available = []
        for name, scanner_class in self.SCANNERS.items():
            scanner = scanner_class(self.skill_path)
            if scanner.is_available:
                available.append(name)
        return available
