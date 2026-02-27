"""Tests for third-party security scanner integrations."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_validation.security import SecurityIssue
from skill_validation.security.third_party import (
    BanditScanner,
    GitleaksScanner,
    SafetyScanner,
    ThirdPartyScannerConfig,
    ThirdPartyScannerManager,
)


class TestBanditScanner:
    """Tests for Bandit scanner integration."""

    def test_name(self, tmp_path: Path):
        """Test scanner name."""
        scanner = BanditScanner(tmp_path)
        assert scanner.name == "bandit"

    def test_is_available_when_installed(self, tmp_path: Path):
        """Test availability check when bandit is installed."""
        scanner = BanditScanner(tmp_path)

        with patch.object(scanner, "_run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert scanner.is_available is True

    def test_is_available_when_not_installed(self, tmp_path: Path):
        """Test availability check when bandit is not installed."""
        scanner = BanditScanner(tmp_path)

        with patch.object(scanner, "_run_command") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert scanner.is_available is False

    def test_scan_with_mock_results(self, tmp_path: Path):
        """Test scanning with mocked bandit output."""
        scanner = BanditScanner(tmp_path)

        # Create the test file so the path exists
        test_file = tmp_path / "test.py"
        test_file.write_text("os.system(cmd)\n")

        mock_output = json.dumps(
            {
                "results": [
                    {
                        "issue_severity": "HIGH",
                        "test_id": "B605",
                        "filename": str(test_file.resolve()),
                        "line_number": 10,
                        "issue_text": "Possible shell injection",
                        "code": "os.system(cmd)",
                    }
                ]
            }
        )

        # Mock _run_command to simulate bandit being available and returning results
        with patch.object(scanner, "_run_command") as mock_run:
            # First call is is_available (bandit --version), second is the actual scan
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="bandit 1.7.0"),  # is_available check
                MagicMock(returncode=1, stdout=mock_output),  # actual scan
            ]
            issues = scanner.scan()

        assert len(issues) == 1
        assert issues[0].severity == "high"
        assert issues[0].category == "bandit:B605"
        assert "shell injection" in issues[0].message

    def test_scan_with_no_issues(self, tmp_path: Path):
        """Test scanning when no issues found."""
        scanner = BanditScanner(tmp_path)

        mock_output = json.dumps({"results": []})

        with patch.object(scanner, "_run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            issues = scanner.scan()

        assert len(issues) == 0


class TestGitleaksScanner:
    """Tests for Gitleaks scanner integration."""

    def test_name(self, tmp_path: Path):
        """Test scanner name."""
        scanner = GitleaksScanner(tmp_path)
        assert scanner.name == "gitleaks"

    def test_scan_with_mock_results(self, tmp_path: Path):
        """Test scanning with mocked gitleaks output."""
        scanner = GitleaksScanner(tmp_path)

        # Create the test file so the path exists
        config_file = tmp_path / "config.py"
        config_file.write_text("AKIAIOSFODNN7EXAMPLE\n")

        mock_output = json.dumps(
            {
                "File": str(config_file.resolve()),
                "StartLine": 5,
                "Description": "AWS Access Key",
                "Match": "AKIAIOSFODNN7EXAMPLE",
            }
        )

        # Mock _run_command to simulate gitleaks being available and returning results
        with patch.object(scanner, "_run_command") as mock_run:
            # First call is is_available (gitleaks version), second is the actual scan
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="gitleaks version 8.0.0"),  # is_available check
                MagicMock(returncode=1, stdout=mock_output),  # actual scan
            ]
            issues = scanner.scan()

        assert len(issues) == 1
        assert issues[0].severity == "critical"
        assert issues[0].category == "secret"
        assert "AWS Access Key" in issues[0].message


class TestSafetyScanner:
    """Tests for Safety scanner integration."""

    def test_name(self, tmp_path: Path):
        """Test scanner name."""
        scanner = SafetyScanner(tmp_path)
        assert scanner.name == "safety"

    def test_scan_skips_without_requirements(self, tmp_path: Path):
        """Test scanning skips when no requirements files exist."""
        scanner = SafetyScanner(tmp_path)
        issues = scanner.scan()
        assert len(issues) == 0

    def test_scan_with_mock_results(self, tmp_path: Path):
        """Test scanning with mocked safety output."""
        # Create a requirements.txt
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.19.0\n")

        scanner = SafetyScanner(tmp_path)

        mock_output = json.dumps(
            {
                "vulnerabilities": [
                    {
                        "vulnerability_id": "CVE-2018-18074",
                        "cvssv3_score": 9.8,
                        "advisory": "Requests vulnerability",
                        "package_name": "requests",
                        "vulnerable_spec": "<2.20.0",
                    }
                ]
            }
        )

        with patch.object(scanner, "_run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            issues = scanner.scan()

        assert len(issues) == 1
        assert issues[0].severity == "critical"  # CVSS 9.8
        assert issues[0].category == "dependency"
        assert "CVE-2018-18074" in issues[0].message


class TestThirdPartyScannerManager:
    """Tests for scanner manager."""

    def test_get_available_scanners(self, tmp_path: Path):
        """Test getting available scanners."""
        manager = ThirdPartyScannerManager(tmp_path)

        with patch.object(BanditScanner, "is_available", new_callable=lambda: True):
            available = manager.get_available_scanners()
            assert "bandit" in available

    def test_register_scanner(self, tmp_path: Path):
        """Test registering a scanner."""
        manager = ThirdPartyScannerManager(tmp_path)

        with patch.object(BanditScanner, "is_available", new_callable=lambda: True):
            result = manager.register_scanner("bandit")
            assert result is True
            assert "bandit" in manager.scanners

    def test_register_unavailable_scanner(self, tmp_path: Path):
        """Test registering an unavailable scanner."""
        manager = ThirdPartyScannerManager(tmp_path)

        with patch.object(BanditScanner, "is_available", new_callable=lambda: False):
            result = manager.register_scanner("bandit")
            assert result is False
            assert "bandit" not in manager.scanners

    def test_scan_all(self, tmp_path: Path):
        """Test running all registered scanners."""
        manager = ThirdPartyScannerManager(tmp_path)

        mock_issue = SecurityIssue(
            severity="high",
            category="test",
            file=Path("test.py"),
            line=1,
            message="Test issue",
            snippet="test",
        )

        with patch.object(BanditScanner, "is_available", new_callable=lambda: True):
            manager.register_scanner("bandit")
            with patch.object(manager.scanners["bandit"], "scan", return_value=[mock_issue]):
                results = manager.scan_all()

        assert "bandit" in results
        assert len(results["bandit"]) == 1
