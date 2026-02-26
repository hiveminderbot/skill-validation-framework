"""Report generator for skill validation results."""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class SkillReport:
    """Complete validation report for a skill."""
    skill_name: str
    skill_path: Path
    timestamp: str
    security_summary: Dict[str, Any]
    validation_summary: Dict[str, Any]
    benchmark_summary: Dict[str, Any]
    overall_score: float
    recommendations: List[str]


class ReportGenerator:
    """Generates comparative reports for skill validation."""
    
    def __init__(self):
        self.reports: List[SkillReport] = []
    
    def add_report(self, report: SkillReport) -> None:
        """Add a skill report."""
        self.reports.append(report)
    
    def generate_text_report(self, report: SkillReport) -> str:
        """Generate a text report for a single skill."""
        lines = [
            f"# Skill Validation Report: {report.skill_name}",
            f"Generated: {report.timestamp}",
            f"Path: {report.skill_path}",
            "",
            "## Overall Score",
            f"{report.overall_score:.1f}/10",
            "",
            "## Security",
            f"- Total Issues: {report.security_summary.get('total_issues', 0)}",
            f"- Critical: {report.security_summary.get('severity_counts', {}).get('critical', 0)}",
            f"- High: {report.security_summary.get('severity_counts', {}).get('high', 0)}",
            f"- Medium: {report.security_summary.get('severity_counts', {}).get('medium', 0)}",
            f"- Low: {report.security_summary.get('severity_counts', {}).get('low', 0)}",
            f"- Passed: {report.security_summary.get('passed', False)}",
            "",
            "## Validation",
            f"- Total Tests: {report.validation_summary.get('total_tests', 0)}",
            f"- Passed: {report.validation_summary.get('passed', 0)}",
            f"- Failed: {report.validation_summary.get('failed', 0)}",
            f"- Pass Rate: {report.validation_summary.get('pass_rate', 0):.1%}",
            "",
            "## Benchmark",
            f"- Tasks Run: {report.benchmark_summary.get('total_tasks', 0)}",
            f"- Success Rate: {report.benchmark_summary.get('success_rate', 0):.1%}",
            f"- Avg Duration: {report.benchmark_summary.get('avg_duration_ms', 0):.1f}ms",
            "",
            "## Recommendations",
        ]
        
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        
        return "\n".join(lines)
    
    def generate_comparative_report(self) -> str:
        """Generate a comparative report for all skills."""
        if not self.reports:
            return "No reports to compare."
        
        lines = [
            "# Comparative Skill Validation Report",
            f"Generated: {datetime.now().isoformat()}",
            f"Skills Compared: {len(self.reports)}",
            "",
            "## Summary Table",
            "",
            "| Skill | Overall Score | Security | Validation | Benchmark |",
            "|-------|---------------|----------|------------|-----------|",
        ]
        
        for report in sorted(self.reports, key=lambda r: r.overall_score, reverse=True):
            sec_pass = "✓" if report.security_summary.get('passed') else "✗"
            val_rate = f"{report.validation_summary.get('pass_rate', 0):.0%}"
            bench_rate = f"{report.benchmark_summary.get('success_rate', 0):.0%}"
            
            lines.append(
                f"| {report.skill_name} | {report.overall_score:.1f} | {sec_pass} | {val_rate} | {bench_rate} |"
            )
        
        lines.extend([
            "",
            "## Detailed Reports",
            "",
        ])
        
        for report in self.reports:
            lines.append(self.generate_text_report(report))
            lines.append("\n---\n")
        
        return "\n".join(lines)
    
    def calculate_overall_score(
        self,
        security_summary: Dict[str, Any],
        validation_summary: Dict[str, Any],
        benchmark_summary: Dict[str, Any]
    ) -> float:
        """Calculate overall score from 0-10."""
        score = 10.0
        
        # Security penalties
        if not security_summary.get('passed', False):
            severity_counts = security_summary.get('severity_counts', {})
            score -= severity_counts.get('critical', 0) * 3
            score -= severity_counts.get('high', 0) * 2
            score -= severity_counts.get('medium', 0) * 1
            score -= severity_counts.get('low', 0) * 0.5
        
        # Validation score (max 3 points)
        val_rate = validation_summary.get('pass_rate', 0)
        score -= (1 - val_rate) * 3
        
        # Benchmark score (max 2 points)
        bench_rate = benchmark_summary.get('success_rate', 0)
        score -= (1 - bench_rate) * 2
        
        return max(0, min(10, score))
    
    def generate_recommendations(
        self,
        security_summary: Dict[str, Any],
        validation_summary: Dict[str, Any],
        benchmark_summary: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []
        
        # Security recommendations
        if not security_summary.get('passed', False):
            severity_counts = security_summary.get('severity_counts', {})
            if severity_counts.get('critical', 0) > 0:
                recommendations.append("CRITICAL: Remove hardcoded secrets immediately")
            if severity_counts.get('high', 0) > 0:
                recommendations.append("HIGH: Review use of eval/exec for security risks")
            if severity_counts.get('medium', 0) > 0:
                recommendations.append("MEDIUM: Review network calls for necessity")
        
        # Validation recommendations
        val_rate = validation_summary.get('pass_rate', 0)
        if val_rate < 0.5:
            recommendations.append("Add missing required files or fields")
        elif val_rate < 0.8:
            recommendations.append("Improve SKILL.md quality and completeness")
        
        # Benchmark recommendations
        bench_rate = benchmark_summary.get('success_rate', 0)
        if bench_rate < 0.5:
            recommendations.append("Fix failing benchmark tasks")
        
        if not recommendations:
            recommendations.append("No issues found — skill is well-structured")
        
        return recommendations


def generate_report(
    skill_name: str,
    skill_path: Path,
    security_summary: Dict[str, Any],
    validation_summary: Dict[str, Any],
    benchmark_summary: Dict[str, Any]
) -> SkillReport:
    """Convenience function to generate a complete report."""
    generator = ReportGenerator()
    
    overall_score = generator.calculate_overall_score(
        security_summary, validation_summary, benchmark_summary
    )
    
    recommendations = generator.generate_recommendations(
        security_summary, validation_summary, benchmark_summary
    )
    
    return SkillReport(
        skill_name=skill_name,
        skill_path=skill_path,
        timestamp=datetime.now().isoformat(),
        security_summary=security_summary,
        validation_summary=validation_summary,
        benchmark_summary=benchmark_summary,
        overall_score=overall_score,
        recommendations=recommendations,
    )
