"""Entry point for python -m skill_validation.security."""

import argparse
import json
import sys
from pathlib import Path

from skill_validation.security import scan_skill


def main():
    parser = argparse.ArgumentParser(description="Security scanner for OpenClaw skills")
    parser.add_argument("skill_path", type=Path, help="Path to the skill to scan")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--third-party", action="store_true", help="Run third-party scanners")
    parser.add_argument("--output", type=Path, help="Output file (default: stdout)")

    args = parser.parse_args()

    issues, summary = scan_skill(args.skill_path, use_third_party=args.third_party)

    if args.format == "json":
        output = json.dumps({
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": str(i.file),
                    "line": i.line,
                    "message": i.message,
                    "snippet": i.snippet,
                }
                for i in issues
            ],
            "summary": summary,
        }, indent=2)
    else:
        lines = [f"Security Scan Results for {args.skill_path}", "=" * 50]
        if issues:
            for issue in issues:
                lines.append(f"\n[{issue.severity.upper()}] {issue.category}")
                lines.append(f"  File: {issue.file}:{issue.line}")
                lines.append(f"  Message: {issue.message}")
                lines.append(f"  Snippet: {issue.snippet[:100]}...")
        else:
            lines.append("\nNo issues found!")
        lines.append(f"\nTotal: {summary['total_issues']} issues")
        output = "\n".join(lines)

    if args.output:
        args.output.write_text(output)
    else:
        print(output)

    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
