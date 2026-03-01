"""Tests for SARIF output generation."""

import json
import tempfile
from pathlib import Path

import pytest

from skill_validation.report.sarif import SarifGenerator, generate_sarif_report
from skill_validation.security import SecurityIssue
from skill_validation.validation import ValidationResult


class TestSarifGenerator:
    """Test suite for SARIF generation."""

    def test_initialization(self):
        """Test SARIF generator initialization."""
        generator = SarifGenerator(tool_version="1.0.0")
        assert generator.tool_version == "1.0.0"
        assert generator.rules == {}
        assert generator.results == []

    def test_add_security_issues(self):
        """Test adding security issues to SARIF report."""
        generator = SarifGenerator()

        issues = [
            SecurityIssue(
                severity="critical",
                category="secret",
                file=Path("test.py"),
                line=10,
                message="API key found",
                snippet="api_key = 'secret123'",
            ),
            SecurityIssue(
                severity="high",
                category="eval",
                file=Path("test.py"),
                line=20,
                message="Eval usage detected",
                snippet="eval(user_input)",
            ),
        ]

        generator.add_security_issues(issues)

        assert len(generator.results) == 2
        assert len(generator.rules) == 2

        # Check first result
        result = generator.results[0]
        assert result["ruleId"] == "builtin/secret"
        assert result["level"] == "error"
        assert result["message"]["text"] == "API key found"
        assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 10

    def test_add_validation_results(self):
        """Test adding validation results to SARIF report."""
        generator = SarifGenerator()

        results = [
            ValidationResult(
                test_name="required_file_SKILL.md",
                passed=False,
                message="SKILL.md is missing",
            ),
            ValidationResult(
                test_name="skill_md_frontmatter",
                passed=True,
                message="YAML frontmatter present",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir)
            generator.add_validation_results(results, skill_path)

            # Only failed results should be added
            assert len(generator.results) == 1
            assert generator.results[0]["ruleId"] == "validation/required_file_SKILL.md"
            assert generator.results[0]["level"] == "warning"

    def test_generate_sarif_document(self):
        """Test generating complete SARIF document."""
        generator = SarifGenerator(tool_version="0.1.0")

        issues = [
            SecurityIssue(
                severity="medium",
                category="network",
                file=Path("test.py"),
                line=5,
                message="Network request detected",
                snippet="requests.get(url)",
            ),
        ]

        generator.add_security_issues(issues)

        with tempfile.TemporaryDirectory() as tmpdir:
            src_root = Path(tmpdir)
            doc = generator.generate(src_root)

            assert doc["$schema"] == generator.SARIF_SCHEMA
            assert doc["version"] == "2.1.0"
            assert len(doc["runs"]) == 1

            run = doc["runs"][0]
            assert run["tool"]["driver"]["name"] == "skill-validation-framework"
            assert run["tool"]["driver"]["version"] == "0.1.0"
            assert len(run["tool"]["driver"]["rules"]) == 1
            assert len(run["results"]) == 1

    def test_severity_to_level_mapping(self):
        """Test severity to SARIF level mapping."""
        generator = SarifGenerator()

        test_cases = [
            ("critical", "error"),
            ("high", "error"),
            ("medium", "warning"),
            ("low", "note"),
            ("unknown", "warning"),  # Default
        ]

        for severity, expected_level in test_cases:
            issues = [
                SecurityIssue(
                    severity=severity,
                    category="test",
                    file=Path("test.py"),
                    line=1,
                    message="Test",
                    snippet="test",
                ),
            ]

            generator = SarifGenerator()  # Fresh generator
            generator.add_security_issues(issues)
            assert generator.results[0]["level"] == expected_level

    def test_to_json_output(self):
        """Test JSON output generation."""
        generator = SarifGenerator()

        issues = [
            SecurityIssue(
                severity="low",
                category="filesystem",
                file=Path("test.py"),
                line=1,
                message="File operation",
                snippet="open('file.txt')",
            ),
        ]

        generator.add_security_issues(issues)
        json_output = generator.to_json()

        # Should be valid JSON
        parsed = json.loads(json_output)
        assert parsed["version"] == "2.1.0"
        assert len(parsed["runs"][0]["results"]) == 1

    def test_write_file(self):
        """Test writing SARIF to file."""
        generator = SarifGenerator()

        issues = [
            SecurityIssue(
                severity="high",
                category="eval",
                file=Path("test.py"),
                line=1,
                message="Eval used",
                snippet="eval('1+1')",
            ),
        ]

        generator.add_security_issues(issues)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.sarif"
            generator.write_file(output_path)

            assert output_path.exists()
            content = output_path.read_text()
            parsed = json.loads(content)
            assert parsed["version"] == "2.1.0"

    def test_rule_help_texts(self):
        """Test that rule help texts are defined for known categories."""
        generator = SarifGenerator()

        categories = ["secret", "eval", "network", "filesystem", "dependency"]

        for category in categories:
            help_data = generator._get_rule_help(category)
            assert "description" in help_data
            assert "help_text" in help_data
            assert "help_markdown" in help_data
            assert len(help_data["description"]) > 0

    def test_unknown_category_fallback(self):
        """Test fallback for unknown categories."""
        generator = SarifGenerator()

        help_data = generator._get_rule_help("unknown_category")
        assert "unknown_category" in help_data["description"]
        assert "unknown_category" in help_data["help_text"]

    def test_severity_to_rank(self):
        """Test severity to rank conversion."""
        generator = SarifGenerator()

        ranks = {
            "critical": 95.0,
            "high": 75.0,
            "medium": 50.0,
            "low": 25.0,
        }

        for severity, expected_rank in ranks.items():
            assert generator._severity_to_rank(severity) == expected_rank

        # Default for unknown
        assert generator._severity_to_rank("unknown") == 50.0


class TestGenerateSarifReport:
    """Test the convenience function for generating SARIF reports."""

    def test_generate_complete_report(self):
        """Test generating a complete SARIF report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir)

            security_issues = [
                SecurityIssue(
                    severity="critical",
                    category="secret",
                    file=Path("skill.py"),
                    line=5,
                    message="Hardcoded API key",
                    snippet="API_KEY = 'xxx'",
                ),
            ]

            validation_results = [
                ValidationResult(
                    test_name="required_file",
                    passed=False,
                    message="Missing file",
                ),
            ]

            output_path = skill_path / "report.sarif"

            json_output = generate_sarif_report(
                skill_path=skill_path,
                security_issues=security_issues,
                validation_results=validation_results,
                output_path=output_path,
                tool_version="0.1.0",
            )

            # Check file was written
            assert output_path.exists()

            # Check output is valid JSON
            parsed = json.loads(json_output)
            assert parsed["version"] == "2.1.0"

            # Should have both security and validation results
            results = parsed["runs"][0]["results"]
            assert len(results) == 2  # 1 security + 1 validation

    def test_generate_without_output_path(self):
        """Test generating report without writing to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir)

            json_output = generate_sarif_report(
                skill_path=skill_path,
                security_issues=[],
                validation_results=[],
                output_path=None,
            )

            # Should still return valid JSON
            parsed = json.loads(json_output)
            assert parsed["version"] == "2.1.0"
            assert len(parsed["runs"][0]["results"]) == 0
