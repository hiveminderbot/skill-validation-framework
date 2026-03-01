"""Entry point for python -m skill_validation.validation."""

import argparse
import json
import sys
from pathlib import Path

from skill_validation.validation import validate_skill


def main():
    parser = argparse.ArgumentParser(description="Validation tester for OpenClaw skills")
    parser.add_argument("skill_path", type=Path, help="Path to the skill to validate")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path, help="Output file (default: stdout)")

    args = parser.parse_args()

    results, summary = validate_skill(args.skill_path)

    if args.format == "json":
        output = json.dumps(
            {
                "results": [
                    {
                        "test_name": r.test_name,
                        "passed": r.passed,
                        "message": r.message,
                        "details": r.details,
                    }
                    for r in results
                ],
                "summary": summary,
            },
            indent=2,
        )
    else:
        lines = [f"Validation Results for {args.skill_path}", "=" * 50]
        for result in results:
            status = "✅" if result.passed else "❌"
            lines.append(f"\n{status} {result.test_name}")
            lines.append(f"   {result.message}")
        lines.append(f"\nPass rate: {summary['pass_rate']:.1%}")
        output = "\n".join(lines)

    if args.output:
        args.output.write_text(output)
    else:
        print(output)

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
