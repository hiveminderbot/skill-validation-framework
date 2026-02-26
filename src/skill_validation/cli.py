"""CLI for skill validation framework."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from skill_validation.benchmark import benchmark_skill
from skill_validation.report import ReportGenerator, generate_report
from skill_validation.security import scan_skill
from skill_validation.validation import validate_skill

console = Console()


@click.group()
def cli():
    """Skill Validation Framework — Validate OpenClaw skills."""
    pass


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--third-party", "use_third_party", is_flag=True, help="Run third-party scanners")
@click.option(
    "--scanner",
    "scanners",
    multiple=True,
    type=click.Choice(["bandit", "gitleaks", "safety"]),
    help="Specific third-party scanner to use (can be used multiple times)",
)
def security(
    skill_path: Path, output_format: str, use_third_party: bool, scanners: tuple[str, ...]
):
    """Run security scan on a skill."""
    console.print(f"[bold]Scanning {skill_path} for security issues...[/bold]")

    third_party_list = list(scanners) if scanners else None
    issues, summary = scan_skill(skill_path, use_third_party, third_party_list)

    if output_format == "json":
        import json

        console.print(
            json.dumps(
                {
                    "issues": [
                        {
                            "severity": i.severity,
                            "category": i.category,
                            "file": str(i.file),
                            "line": i.line,
                            "message": i.message,
                        }
                        for i in issues
                    ],
                    "summary": summary,
                },
                indent=2,
            )
        )
    else:
        if issues:
            table = Table(title="Security Issues")
            table.add_column("Severity", style="red")
            table.add_column("Category")
            table.add_column("File")
            table.add_column("Line")
            table.add_column("Message")

            for issue in issues:
                table.add_row(
                    issue.severity,
                    issue.category,
                    str(issue.file),
                    str(issue.line),
                    issue.message,
                )
            console.print(table)
        else:
            console.print("[green]✓ No security issues found[/green]")

        console.print(f"\nTotal issues: {summary['total_issues']}")
        console.print(f"Passed: {summary['passed']}")

        if summary.get("third_party_scanners"):
            console.print(
                f"Third-party scanners used: {', '.join(summary['third_party_scanners'])}"
            )


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def validate(skill_path: Path, output_format: str):
    """Validate skill structure and functionality."""
    console.print(f"[bold]Validating {skill_path}...[/bold]")

    results, summary = validate_skill(skill_path)

    if output_format == "json":
        import json

        console.print(
            json.dumps(
                {
                    "results": [
                        {
                            "test_name": r.test_name,
                            "passed": r.passed,
                            "message": r.message,
                        }
                        for r in results
                    ],
                    "summary": summary,
                },
                indent=2,
            )
        )
    else:
        table = Table(title="Validation Results")
        table.add_column("Test")
        table.add_column("Status")
        table.add_column("Message")

        for result in results:
            status = "[green]✓[/green]" if result.passed else "[red]✗[/red]"
            table.add_row(result.test_name, status, result.message)

        console.print(table)
        console.print(f"\nPass rate: {summary['pass_rate']:.1%}")


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def benchmark(skill_path: Path, output_format: str):
    """Run benchmarks on a skill."""
    console.print(f"[bold]Benchmarking {skill_path}...[/bold]")

    results, summary = benchmark_skill(skill_path)

    if output_format == "json":
        import json

        console.print(
            json.dumps(
                {
                    "results": [
                        {
                            "task_name": r.task_name,
                            "success": r.success,
                            "duration_ms": r.duration_ms,
                        }
                        for r in results
                    ],
                    "summary": summary,
                },
                indent=2,
            )
        )
    else:
        table = Table(title="Benchmark Results")
        table.add_column("Task")
        table.add_column("Status")
        table.add_column("Duration (ms)")

        for result in results:
            status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
            table.add_row(result.task_name, status, f"{result.duration_ms:.1f}")

        console.print(table)
        console.print(f"\nSuccess rate: {summary['success_rate']:.1%}")
        console.print(f"Avg duration: {summary['avg_duration_ms']:.1f}ms")


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--compare", "compare_path", type=click.Path(exists=True, path_type=Path), default=None
)
@click.option("--output", "output_path", type=click.Path(path_type=Path), default=None)
def report(skill_path: Path, compare_path: Path | None, output_path: Path | None):
    """Generate full validation report."""
    skill_name = skill_path.name

    console.print(f"[bold]Generating report for {skill_name}...[/bold]")

    # Run all checks
    _, security_summary = scan_skill(skill_path)
    _, validation_summary = validate_skill(skill_path)
    _, benchmark_summary = benchmark_skill(skill_path)

    # Generate report
    report = generate_report(
        skill_name=skill_name,
        skill_path=skill_path,
        security_summary=security_summary,
        validation_summary=validation_summary,
        benchmark_summary=benchmark_summary,
    )

    # Handle comparison
    if compare_path:
        compare_name = compare_path.name
        console.print(f"[bold]Comparing with {compare_name}...[/bold]")

        _, sec2 = scan_skill(compare_path)
        _, val2 = validate_skill(compare_path)
        _, bench2 = benchmark_skill(compare_path)

        report2 = generate_report(
            skill_name=compare_name,
            skill_path=compare_path,
            security_summary=sec2,
            validation_summary=val2,
            benchmark_summary=bench2,
        )

        generator = ReportGenerator()
        generator.add_report(report)
        generator.add_report(report2)
        output = generator.generate_comparative_report()
    else:
        generator = ReportGenerator()
        output = generator.generate_text_report(report)

    # Output
    if output_path:
        output_path.write_text(output)
        console.print(f"[green]Report saved to {output_path}[/green]")
    else:
        console.print(output)


if __name__ == "__main__":
    cli()
