"""Functional validation for OpenClaw skills."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ValidationResult:
    """Result of a validation test."""

    test_name: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None


class SkillValidator:
    """Validates skill structure and functionality."""

    REQUIRED_FILES = ["SKILL.md"]
    OPTIONAL_DIRS = ["scripts", "references", "assets"]

    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        self.results: list[ValidationResult] = []
        self.skill_metadata: dict[str, Any] | None = None

    def validate(self) -> list[ValidationResult]:
        """Run all validation tests."""
        self.results = []

        # Structure validation
        self._validate_structure()

        # SKILL.md validation
        self._validate_skill_md()

        # Scripts validation (if present)
        if (self.skill_path / "scripts").exists():
            self._validate_scripts()

        return self.results

    def _validate_structure(self) -> None:
        """Validate basic skill structure."""
        # Check required files
        for req_file in self.REQUIRED_FILES:
            file_path = self.skill_path / req_file
            self.results.append(
                ValidationResult(
                    test_name=f"required_file_{req_file}",
                    passed=file_path.exists(),
                    message=f"{req_file} {'exists' if file_path.exists() else 'missing'}",
                )
            )

        # Check optional directories
        for opt_dir in self.OPTIONAL_DIRS:
            dir_path = self.skill_path / opt_dir
            if dir_path.exists():
                self.results.append(
                    ValidationResult(
                        test_name=f"optional_dir_{opt_dir}",
                        passed=True,
                        message=f"{opt_dir}/ directory present",
                    )
                )

    def _validate_skill_md(self) -> None:
        """Validate SKILL.md content."""
        skill_md_path = self.skill_path / "SKILL.md"
        if not skill_md_path.exists():
            return

        content = skill_md_path.read_text(encoding="utf-8")

        # Check for YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        has_frontmatter = frontmatter_match is not None

        self.results.append(
            ValidationResult(
                test_name="skill_md_frontmatter",
                passed=has_frontmatter,
                message=(
                    "YAML frontmatter present" if has_frontmatter else "YAML frontmatter missing"
                ),
            )
        )

        if has_frontmatter:
            try:
                metadata = yaml.safe_load(frontmatter_match.group(1))
                self.skill_metadata = metadata

                # Check required fields
                self.results.append(
                    ValidationResult(
                        test_name="skill_md_name_field",
                        passed="name" in metadata,
                        message=(
                            "name field present" if "name" in metadata else "name field missing"
                        ),
                    )
                )

                self.results.append(
                    ValidationResult(
                        test_name="skill_md_description_field",
                        passed="description" in metadata,
                        message=(
                            "description field present"
                            if "description" in metadata
                            else "description field missing"
                        ),
                    )
                )

                # Check description quality
                if "description" in metadata:
                    desc = metadata["description"]
                    desc_quality = len(desc) > 50 and "use when" in desc.lower()
                    self.results.append(
                        ValidationResult(
                            test_name="skill_md_description_quality",
                            passed=desc_quality,
                            message=(
                                "Description has triggering guidance"
                                if desc_quality
                                else "Description lacks triggering guidance"
                            ),
                        )
                    )
            except yaml.YAMLError as e:
                self.results.append(
                    ValidationResult(
                        test_name="skill_md_yaml_valid",
                        passed=False,
                        message=f"Invalid YAML frontmatter: {e}",
                    )
                )

        # Check body content
        has_body = len(content) > 200
        self.results.append(
            ValidationResult(
                test_name="skill_md_body_content",
                passed=has_body,
                message="Body content present" if has_body else "Body content too short",
            )
        )

    def _validate_scripts(self) -> None:
        """Validate scripts directory."""
        scripts_dir = self.skill_path / "scripts"
        if not scripts_dir.exists():
            return

        for script_file in scripts_dir.iterdir():
            if script_file.is_file():
                # Check if script is executable (Unix)
                is_executable = script_file.stat().st_mode & 0o111 != 0
                self.results.append(
                    ValidationResult(
                        test_name=f"script_executable_{script_file.name}",
                        passed=is_executable,
                        message=(
                            f"{script_file.name} is executable"
                            if is_executable
                            else f"{script_file.name} not executable"
                        ),
                    )
                )

    def get_summary(self) -> dict:
        """Get validation summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        return {
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self.results) if self.results else 0,
        }


def validate_skill(skill_path: Path) -> tuple[list[ValidationResult], dict]:
    """Convenience function to validate a skill."""
    validator = SkillValidator(skill_path)
    results = validator.validate()
    summary = validator.get_summary()
    return results, summary
