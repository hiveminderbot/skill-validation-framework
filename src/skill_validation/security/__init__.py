"""Security scanner for OpenClaw skills."""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


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
    
    # Patterns to detect
    PATTERNS = {
        "secret": {
            "severity": "critical",
            "patterns": [
                r'[a-zA-Z0-9_-]*(?:api[_-]?key|token|secret|password|credential)["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
                r'gh[pousr]_[A-Za-z0-9_]{36,}',
                r'sk-[a-zA-Z0-9]{48}',
                r'AKIA[0-9A-Z]{16}',
            ]
        },
        "eval": {
            "severity": "high",
            "patterns": [
                r'\beval\s*\(',
                r'\bexec\s*\(',
                r'__import__\s*\(',
                r'subprocess\.call\s*\([^)]*shell\s*=\s*True',
                r'os\.system\s*\(',
            ]
        },
        "network": {
            "severity": "medium",
            "patterns": [
                r'urllib\.request\.urlopen',
                r'requests\.(get|post|put|delete)',
                r'http\.client\.HTTPConnection',
            ]
        },
        "filesystem": {
            "severity": "low",
            "patterns": [
                r'open\s*\([^)]*,\s*["\']w',
                r'shutil\.(rmtree|move)',
                r'os\.(remove|unlink|rmdir)',
            ]
        },
    }
    
    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        self.issues: List[SecurityIssue] = []
    
    def scan(self) -> List[SecurityIssue]:
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
        skip_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.ttf', '.woff', '.woff2'}
        return file_path.suffix not in skip_extensions
    
    def _scan_file(self, file_path: Path) -> None:
        """Scan a single file for security issues."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            for category, config in self.PATTERNS.items():
                for pattern in config["patterns"]:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                        
                        issue = SecurityIssue(
                            severity=config["severity"],
                            category=category,
                            file=file_path.relative_to(self.skill_path),
                            line=line_num,
                            message=f"Potential {category} issue detected",
                            snippet=line_content.strip()[:100]
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


def scan_skill(skill_path: Path) -> tuple[List[SecurityIssue], dict]:
    """Convenience function to scan a skill."""
    scanner = SecurityScanner(skill_path)
    issues = scanner.scan()
    summary = scanner.get_summary()
    return issues, summary
