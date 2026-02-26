"""Benchmark runner for OpenClaw skills."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    task_name: str
    success: bool
    duration_ms: float
    token_count: int | None = None
    api_calls: int = 0
    retries: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """Runs benchmarks on skills using synthetic tasks."""

    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        self.results: list[BenchmarkResult] = []

    def run_benchmarks(self, tasks: list[dict[str, Any]] | None = None) -> list[BenchmarkResult]:
        """Run benchmark tasks against the skill."""
        self.results = []

        if tasks is None:
            tasks = self._get_default_tasks()

        for task in tasks:
            result = self._run_task(task)
            self.results.append(result)

        return self.results

    def _get_default_tasks(self) -> list[dict[str, Any]]:
        """Get default synthetic tasks for benchmarking."""
        return [
            {
                "name": "skill_load_time",
                "description": "Measure time to load and parse skill",
                "type": "load_test",
            },
            {
                "name": "metadata_extraction",
                "description": "Extract and parse skill metadata",
                "type": "parse_test",
            },
            {
                "name": "script_execution",
                "description": "Execute a simple script from the skill",
                "type": "execution_test",
                "skip_if_no_scripts": True,
            },
        ]

    def _run_task(self, task: dict[str, Any]) -> BenchmarkResult:
        """Run a single benchmark task."""
        start_time = time.time()

        try:
            if task["type"] == "load_test":
                success = self._benchmark_load()
            elif task["type"] == "parse_test":
                success = self._benchmark_parse()
            elif task["type"] == "execution_test":
                success = self._benchmark_execution()
            else:
                success = False

            duration = (time.time() - start_time) * 1000

            return BenchmarkResult(
                task_name=task["name"],
                success=success,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return BenchmarkResult(
                task_name=task["name"],
                success=False,
                duration_ms=duration,
                error_message=str(e),
            )

    def _benchmark_load(self) -> bool:
        """Benchmark skill loading."""
        try:
            skill_md = self.skill_path / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text()
                return len(content) > 0
            return False
        except Exception:
            return False

    def _benchmark_parse(self) -> bool:
        """Benchmark metadata parsing."""
        try:
            import yaml

            skill_md = self.skill_path / "SKILL.md"
            if not skill_md.exists():
                return False

            content = skill_md.read_text()
            # Simple frontmatter extraction
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml.safe_load(parts[1])
            return True
        except Exception:
            return False

    def _benchmark_execution(self) -> bool:
        """Benchmark script execution."""
        # This is a placeholder - actual execution would require sandboxing
        scripts_dir = self.skill_path / "scripts"
        if not scripts_dir.exists():
            return True  # Skip if no scripts

        # Check if scripts are syntactically valid Python
        for script in scripts_dir.glob("*.py"):
            try:
                import py_compile

                py_compile.compile(str(script), doraise=True)
            except Exception:
                return False

        return True

    def get_summary(self) -> dict:
        """Get benchmark summary."""
        if not self.results:
            return {"total_tasks": 0, "success_rate": 0, "avg_duration_ms": 0}

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        avg_duration = sum(r.duration_ms for r in self.results) / total

        return {
            "total_tasks": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total,
            "avg_duration_ms": avg_duration,
            "min_duration_ms": min(r.duration_ms for r in self.results),
            "max_duration_ms": max(r.duration_ms for r in self.results),
        }


def benchmark_skill(
    skill_path: Path, tasks: list[dict[str, Any]] | None = None
) -> tuple[list[BenchmarkResult], dict]:
    """Convenience function to benchmark a skill."""
    runner = BenchmarkRunner(skill_path)
    results = runner.run_benchmarks(tasks)
    summary = runner.get_summary()
    return results, summary
