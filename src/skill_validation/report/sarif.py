"""SARIF output format support for GitHub Advanced Security integration."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from skill_validation.security import SecurityIssue
from skill_validation.validation import ValidationResult


class SarifGenerator:
    """Generates SARIF (Static Analysis Results Interchange Format) output.

    SARIF is a standard format for static analysis tools, supported by
    GitHub Advanced Security, Azure DevOps, and other platforms.

    Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
    """

    # SARIF version and schema
    SARIF_VERSION = "2.1.0"
    SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

    # Tool information
    TOOL_NAME = "skill-validation-framework"
    TOOL_ORG = "hiveminderbot"

    # Severity mapping to SARIF level
    SEVERITY_TO_LEVEL = {
        "critical": "error",
        "high": "error",
        "medium": "warning",
        "low": "note",
    }

    def __init__(self, tool_version: str = "0.1.0"):
        self.tool_version = tool_version
        self.rules: dict[str, dict[str, Any]] = {}
        self.results: list[dict[str, Any]] = []

    def add_security_issues(
        self, issues: list[SecurityIssue], scanner_name: str = "builtin"
    ) -> None:
        """Add security issues to the SARIF report."""
        for issue in issues:
            rule_id = f"{scanner_name}/{issue.category}"

            # Register rule if not already present
            if rule_id not in self.rules:
                self.rules[rule_id] = self._create_rule(rule_id, issue.category, issue.severity)

            # Create result
            result = {
                "ruleId": rule_id,
                "level": self.SEVERITY_TO_LEVEL.get(issue.severity, "warning"),
                "message": {
                    "text": issue.message,
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": str(issue.file),
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {
                                "startLine": issue.line,
                                "snippet": {
                                    "text": issue.snippet,
                                },
                            },
                        }
                    }
                ],
                "properties": {
                    "severity": issue.severity,
                    "category": issue.category,
                },
            }
            self.results.append(result)

    def add_validation_results(self, results: list[ValidationResult], skill_path: Path) -> None:
        """Add validation results to the SARIF report."""
        for result in results:
            if result.passed:
                continue  # Only include failures

            rule_id = f"validation/{result.test_name}"

            # Register rule if not already present
            if rule_id not in self.rules:
                self.rules[rule_id] = {
                    "id": rule_id,
                    "name": result.test_name,
                    "shortDescription": {
                        "text": f"Validation check: {result.test_name}",
                    },
                    "defaultConfiguration": {
                        "level": "warning",
                    },
                }

            # Create result
            sarif_result = {
                "ruleId": rule_id,
                "level": "warning",
                "message": {
                    "text": result.message,
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": str(skill_path / "SKILL.md"),
                                "uriBaseId": "%SRCROOT%",
                            },
                        }
                    }
                ],
                "properties": {
                    "test_name": result.test_name,
                    "details": result.details,
                },
            }
            self.results.append(sarif_result)

    def _create_rule(self, rule_id: str, category: str, severity: str) -> dict[str, Any]:
        """Create a SARIF rule definition."""
        rule_help = self._get_rule_help(category)

        return {
            "id": rule_id,
            "name": category,
            "shortDescription": {
                "text": f"Security issue: {category}",
            },
            "fullDescription": {
                "text": rule_help["description"],
            },
            "help": {
                "text": rule_help["help_text"],
                "markdown": rule_help["help_markdown"],
            },
            "defaultConfiguration": {
                "level": self.SEVERITY_TO_LEVEL.get(severity, "warning"),
                "rank": self._severity_to_rank(severity),
            },
            "properties": {
                "tags": ["security", category],
                "precision": "high",
                "problem": {
                    "severity": severity,
                },
            },
        }

    def _get_rule_help(self, category: str) -> dict[str, str]:
        """Get help text for a rule category."""
        help_texts = {
            "secret": {
                "description": "Potential secret or credential exposed in code",
                "help_text": (
                    "This issue indicates a potential secret, API key, password, "
                    "or credential may be hardcoded in the source code. "
                    "Remove hardcoded secrets and use environment variables or "
                    "a secure secret management system instead."
                ),
                "help_markdown": (
                    "This issue indicates a potential **secret**, **API key**, "
                    "**password**, or **credential** may be hardcoded in the source code.\n\n"
                    "## Remediation\n\n"
                    "1. Remove the hardcoded secret from the code\n"
                    "2. Use environment variables or a secure secret management system\n"
                    "3. Rotate the exposed credential if it was real\n"
                    "4. Consider using tools like git-secrets or pre-commit hooks"
                ),
            },
            "eval": {
                "description": "Dangerous code execution pattern detected",
                "help_text": (
                    "The code uses eval(), exec(), or similar dangerous functions "
                    "that can execute arbitrary code. This is a security risk. "
                    "Use safer alternatives like ast.literal_eval() for parsing "
                    "or proper parsing libraries."
                ),
                "help_markdown": (
                    "The code uses `eval()`, `exec()`, or similar dangerous functions "
                    "that can execute arbitrary code. This is a **security risk**.\n\n"
                    "## Remediation\n\n"
                    "- Use `ast.literal_eval()` for safely evaluating literal expressions\n"
                    "- Use proper parsing libraries (json, yaml, toml) for data formats\n"
                    "- If dynamic code execution is necessary, use strict sandboxing"
                ),
            },
            "network": {
                "description": "Network request detected",
                "help_text": (
                    "The code makes network requests. Review to ensure these are "
                    "necessary and properly secured. Consider adding timeouts and "
                    "handling connection errors gracefully."
                ),
                "help_markdown": (
                    "The code makes **network requests**. Review to ensure these are "
                    "necessary and properly secured.\n\n"
                    "## Best Practices\n\n"
                    "- Always set timeouts on network requests\n"
                    "- Handle connection errors gracefully\n"
                    "- Validate SSL certificates\n"
                    "- Consider rate limiting for external APIs"
                ),
            },
            "filesystem": {
                "description": "File system operation detected",
                "help_text": (
                    "The code performs file system operations. Ensure proper "
                    "validation of file paths to prevent directory traversal attacks. "
                    "Use pathlib for safer path handling."
                ),
                "help_markdown": (
                    "The code performs **file system operations**.\n\n"
                    "## Security Considerations\n\n"
                    "- Validate file paths to prevent directory traversal\n"
                    "- Use `pathlib` instead of string concatenation for paths\n"
                    "- Check file permissions before operations"
                ),
            },
            "dependency": {
                "description": "Vulnerable dependency detected",
                "help_text": (
                    "A dependency has a known security vulnerability. "
                    "Update to a patched version or find an alternative library."
                ),
                "help_markdown": (
                    "A dependency has a **known security vulnerability**.\n\n"
                    "## Remediation\n\n"
                    "1. Update to the patched version\n"
                    "2. Run tests to ensure compatibility\n"
                    "3. Consider using tools like Dependabot or Renovate"
                ),
            },
        }

        return help_texts.get(
            category,
            {
                "description": f"Security issue in category: {category}",
                "help_text": (
                    f"Review the code for potential security issues related to {category}."
                ),
                "help_markdown": (
                    f"Review the code for potential security issues related to **{category}**."
                ),
            },
        )

    def _severity_to_rank(self, severity: str) -> float:
        """Convert severity to SARIF rank (0.0 to 100.0)."""
        ranks = {
            "critical": 95.0,
            "high": 75.0,
            "medium": 50.0,
            "low": 25.0,
        }
        return ranks.get(severity, 50.0)

    def generate(self, src_root: Path | None = None) -> dict[str, Any]:
        """Generate the complete SARIF document."""
        return {
            "$schema": self.SARIF_SCHEMA,
            "version": self.SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.TOOL_NAME,
                            "organization": self.TOOL_ORG,
                            "version": self.tool_version,
                            "informationUri": "https://github.com/hiveminderbot/skill-validation-framework",
                            "rules": list(self.rules.values()),
                        }
                    },
                    "invocations": [
                        {
                            "executionSuccessful": True,
                            "startTimeUtc": datetime.now().isoformat(),
                        }
                    ],
                    "results": self.results,
                    "originalUriBaseIds": {
                        "%SRCROOT%": {
                            "uri": str(src_root or Path.cwd()) + "/",
                        }
                    },
                }
            ],
        }

    def to_json(self, src_root: Path | None = None, indent: int = 2) -> str:
        """Generate SARIF output as JSON string."""
        return json.dumps(self.generate(src_root), indent=indent)

    def write_file(self, output_path: Path, src_root: Path | None = None) -> None:
        """Write SARIF output to a file."""
        output_path.write_text(self.to_json(src_root))


def generate_sarif_report(
    skill_path: Path,
    security_issues: list[SecurityIssue],
    validation_results: list[ValidationResult],
    output_path: Path | None = None,
    tool_version: str = "0.1.0",
) -> str:
    """Generate a complete SARIF report from validation results.

    Args:
        skill_path: Path to the skill being validated
        security_issues: List of security issues found
        validation_results: List of validation results
        output_path: Optional path to write SARIF file
        tool_version: Version of the tool

    Returns:
        SARIF JSON string
    """
    generator = SarifGenerator(tool_version)

    # Add security issues
    generator.add_security_issues(security_issues)

    # Add validation failures
    generator.add_validation_results(validation_results, skill_path)

    # Generate output
    sarif_json = generator.to_json(src_root=skill_path)

    if output_path:
        output_path.write_text(sarif_json)

    return sarif_json
