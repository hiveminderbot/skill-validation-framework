"""Tests for the skill validation framework."""

import pytest
from pathlib import Path
from skill_validation.security import SecurityScanner, SecurityIssue, scan_skill
from skill_validation.validation import SkillValidator, ValidationResult, validate_skill
from skill_validation.benchmark import BenchmarkRunner, BenchmarkResult, benchmark_skill
from skill_validation.report import ReportGenerator, SkillReport, generate_report


class TestSecurityScanner:
    """Tests for the security scanner."""

    def test_scanner_initialization(self, tmp_path):
        """Test scanner can be initialized."""
        scanner = SecurityScanner(tmp_path)
        assert scanner.skill_path == tmp_path
        assert scanner.issues == []

    def test_should_scan_skips_binary_files(self, tmp_path):
        """Test binary files are skipped."""
        scanner = SecurityScanner(tmp_path)
        
        # Create a binary file
        binary_file = tmp_path / "test.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n")
        
        assert not scanner._should_scan(binary_file)

    def test_should_scan_allows_code_files(self, tmp_path):
        """Test code files are scanned."""
        scanner = SecurityScanner(tmp_path)
        
        code_file = tmp_path / "test.py"
        code_file.write_text("print('hello')")
        
        assert scanner._should_scan(code_file)

    def test_detects_api_key_pattern(self, tmp_path):
        """Test API key patterns are detected."""
        scanner = SecurityScanner(tmp_path)
        
        # Create a file with an API key
        test_file = tmp_path / "config.py"
        test_file.write_text('API_KEY = "sk-abcdefghijklmnopqrstuvwxyz12345678901234567890"')
        
        issues = scanner.scan()
        
        assert len(issues) > 0
        assert any(i.category == "secret" for i in issues)

    def test_detects_eval_pattern(self, tmp_path):
        """Test eval() usage is detected."""
        scanner = SecurityScanner(tmp_path)
        
        test_file = tmp_path / "script.py"
        test_file.write_text("result = eval(user_input)")
        
        issues = scanner.scan()
        
        assert len(issues) > 0
        assert any(i.category == "eval" for i in issues)

    def test_get_summary_empty(self, tmp_path):
        """Test summary with no issues."""
        scanner = SecurityScanner(tmp_path)
        scanner.scan()
        
        summary = scanner.get_summary()
        
        assert summary["total_issues"] == 0
        assert summary["passed"] is True
        assert summary["severity_counts"]["critical"] == 0


class TestSkillValidator:
    """Tests for the skill validator."""

    def test_validator_initialization(self, tmp_path):
        """Test validator can be initialized."""
        validator = SkillValidator(tmp_path)
        assert validator.skill_path == tmp_path

    def test_validates_required_files_missing(self, tmp_path):
        """Test validation fails when SKILL.md is missing."""
        validator = SkillValidator(tmp_path)
        results = validator.validate()
        
        required_file_results = [r for r in results if r.test_name == "required_file_SKILL.md"]
        assert len(required_file_results) == 1
        assert required_file_results[0].passed is False

    def test_validates_required_files_present(self, tmp_path):
        """Test validation passes when SKILL.md exists."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test\n---\n# Test Skill")
        
        validator = SkillValidator(tmp_path)
        results = validator.validate()
        
        required_file_results = [r for r in results if r.test_name == "required_file_SKILL.md"]
        assert len(required_file_results) == 1
        assert required_file_results[0].passed is True

    def test_validates_frontmatter(self, tmp_path):
        """Test frontmatter validation."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test\ndescription: A test skill for use when testing\n---\n# Test")
        
        validator = SkillValidator(tmp_path)
        results = validator.validate()
        
        frontmatter_results = [r for r in results if r.test_name == "skill_md_frontmatter"]
        assert len(frontmatter_results) == 1
        assert frontmatter_results[0].passed is True

    def test_validates_description_quality(self, tmp_path):
        """Test description quality validation."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\nname: test\ndescription: This is a comprehensive test skill. Use when testing validation framework functionality.\n---\n# Test"
        )
        
        validator = SkillValidator(tmp_path)
        results = validator.validate()
        
        quality_results = [r for r in results if r.test_name == "skill_md_description_quality"]
        assert len(quality_results) == 1
        assert quality_results[0].passed is True


class TestBenchmarkRunner:
    """Tests for the benchmark runner."""

    def test_runner_initialization(self, tmp_path):
        """Test runner can be initialized."""
        runner = BenchmarkRunner(tmp_path)
        assert runner.skill_path == tmp_path

    def test_default_tasks(self, tmp_path):
        """Test default tasks are defined."""
        runner = BenchmarkRunner(tmp_path)
        tasks = runner._get_default_tasks()
        
        assert len(tasks) >= 2
        assert any(t["name"] == "skill_load_time" for t in tasks)
        assert any(t["name"] == "metadata_extraction" for t in tasks)

    def test_benchmark_load_fails_without_skill_md(self, tmp_path):
        """Test load benchmark fails without SKILL.md."""
        runner = BenchmarkRunner(tmp_path)
        success = runner._benchmark_load()
        
        assert success is False

    def test_benchmark_load_succeeds_with_skill_md(self, tmp_path):
        """Test load benchmark succeeds with SKILL.md."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Test Skill\n\nThis is a test.")
        
        runner = BenchmarkRunner(tmp_path)
        success = runner._benchmark_load()
        
        assert success is True

    def test_get_summary_empty(self, tmp_path):
        """Test summary with no results."""
        runner = BenchmarkRunner(tmp_path)
        summary = runner.get_summary()
        
        assert summary["total_tasks"] == 0
        assert summary["success_rate"] == 0

    def test_get_summary_with_results(self, tmp_path):
        """Test summary with results."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Test")
        
        runner = BenchmarkRunner(tmp_path)
        runner.run_benchmarks()
        summary = runner.get_summary()
        
        assert summary["total_tasks"] > 0
        assert "success_rate" in summary
        assert "avg_duration_ms" in summary


class TestReportGenerator:
    """Tests for the report generator."""

    def test_generator_initialization(self):
        """Test generator can be initialized."""
        generator = ReportGenerator()
        assert generator.reports == []

    def test_calculate_overall_score_perfect(self):
        """Test score calculation for perfect results."""
        generator = ReportGenerator()
        
        security = {"passed": True, "severity_counts": {}}
        validation = {"pass_rate": 1.0}
        benchmark = {"success_rate": 1.0}
        
        score = generator.calculate_overall_score(security, validation, benchmark)
        
        assert score == 10.0

    def test_calculate_overall_score_with_security_issues(self):
        """Test score calculation with security issues."""
        generator = ReportGenerator()
        
        security = {
            "passed": False,
            "severity_counts": {"critical": 1, "high": 0, "medium": 0, "low": 0}
        }
        validation = {"pass_rate": 1.0}
        benchmark = {"success_rate": 1.0}
        
        score = generator.calculate_overall_score(security, validation, benchmark)
        
        assert score == 7.0  # 10 - 3 for critical

    def test_generate_recommendations_clean(self):
        """Test recommendations for clean results."""
        generator = ReportGenerator()
        
        security = {"passed": True, "severity_counts": {}}
        validation = {"pass_rate": 1.0}
        benchmark = {"success_rate": 1.0}
        
        recs = generator.generate_recommendations(security, validation, benchmark)
        
        assert len(recs) == 1
        assert "No issues found" in recs[0]

    def test_generate_recommendations_with_issues(self):
        """Test recommendations with issues."""
        generator = ReportGenerator()
        
        security = {
            "passed": False,
            "severity_counts": {"critical": 1}
        }
        validation = {"pass_rate": 0.3}
        benchmark = {"success_rate": 0.5}
        
        recs = generator.generate_recommendations(security, validation, benchmark)
        
        assert any("CRITICAL" in r for r in recs)


class TestIntegration:
    """Integration tests for the full validation pipeline."""

    def test_full_validation_pipeline(self, tmp_path):
        """Test the complete validation pipeline on a sample skill."""
        # Create a sample skill
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "name: test-skill\n"
            "description: A test skill for use when testing the validation framework\n"
            "---\n"
            "\n"
            "# Test Skill\n"
            "\n"
            "This is a test skill with sufficient content to pass validation.\n"
            "It includes multiple paragraphs to ensure the body content check passes.\n"
            "\n"
            "## Usage\n"
            "\n"
            "Use this skill when you need to test the validation framework.\n"
        )
        
        # Run security scan
        sec_issues, sec_summary = scan_skill(tmp_path)
        
        # Run validation
        val_results, val_summary = validate_skill(tmp_path)
        
        # Run benchmark
        bench_results, bench_summary = benchmark_skill(tmp_path)
        
        # Generate report
        report = generate_report(
            skill_name="test-skill",
            skill_path=tmp_path,
            security_summary=sec_summary,
            validation_summary=val_summary,
            benchmark_summary=bench_summary,
        )
        
        # Assertions
        assert isinstance(report, SkillReport)
        assert report.skill_name == "test-skill"
        assert 0 <= report.overall_score <= 10
        assert isinstance(report.recommendations, list)

    def test_convenience_functions(self, tmp_path):
        """Test convenience functions work correctly."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test\n---\n# Test\n\nContent here.")
        
        # Test scan_skill
        issues, summary = scan_skill(tmp_path)
        assert isinstance(issues, list)
        assert "total_issues" in summary
        
        # Test validate_skill
        results, summary = validate_skill(tmp_path)
        assert isinstance(results, list)
        assert "pass_rate" in summary
        
        # Test benchmark_skill
        results, summary = benchmark_skill(tmp_path)
        assert isinstance(results, list)
        assert "success_rate" in summary
