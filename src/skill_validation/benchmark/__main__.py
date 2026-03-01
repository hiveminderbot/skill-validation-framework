"""Entry point for python -m skill_validation.benchmark."""

import argparse
import json
import sys
from pathlib import Path

from skill_validation.benchmark import benchmark_skill


def main():
    parser = argparse.ArgumentParser(description="Benchmark runner for OpenClaw skills")
    parser.add_argument("skill_path", type=Path, help="Path to the skill to benchmark")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path, help="Output file (default: stdout)")

    args = parser.parse_args()

    results, summary = benchmark_skill(args.skill_path)

    if args.format == "json":
        output = json.dumps(
            {
                "results": [
                    {
                        "task_name": r.task_name,
                        "success": r.success,
                        "duration_ms": r.duration_ms,
                        "metadata": r.metadata,
                    }
                    for r in results
                ],
                "summary": summary,
            },
            indent=2,
        )
    else:
        lines = [f"Benchmark Results for {args.skill_path}", "=" * 50]
        for result in results:
            status = "✅" if result.success else "❌"
            lines.append(f"\n{status} {result.task_name}: {result.duration_ms:.2f}ms")
        lines.append(f"\nSuccess rate: {summary['success_rate']:.1%}")
        lines.append(f"Avg duration: {summary['avg_duration_ms']:.2f}ms")
        output = "\n".join(lines)

    if args.output:
        args.output.write_text(output)
    else:
        print(output)

    return 0 if summary["success_rate"] == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
