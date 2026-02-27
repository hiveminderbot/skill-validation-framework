---
name: skill-validation-framework
description: Universal validation and evaluation framework for OpenClaw skills. Use when you need to validate, test, or benchmark skills for security, correctness, and performance.
version: 0.1.0
author: Hiveminder Bot
---

# Skill Validation Framework

Universal validation and evaluation framework for OpenClaw skills.

## Purpose

Provide systematic validation for all OpenClaw skills across three layers:
1. **Security** — Scan for risky patterns
2. **Validation** — Functional correctness testing
3. **Benchmarking** — Performance measurement and comparison

## Usage

```bash
# Security scan (using uv)
uv run python -m skill_validation.security.scanner ./path/to/skill

# Or with python3 directly
python3 -m skill_validation.security.scanner ./path/to/skill

# Functional validation
uv run python -m skill_validation.validation.tester ./path/to/skill

# Benchmark
uv run python -m skill_validation.benchmark.runner ./path/to/skill

# Full report
uv run skill-validate report . --output full-report.md
```

## Architecture

```
skill-validation-framework/
├── src/
│   ├── security/
│   │   ├── __init__.py          # Core security scanner
│   │   └── third_party.py       # Third-party tool integrations
│   ├── validation/
│   │   └── __init__.py          # Functional validation
│   ├── benchmark/
│   │   └── __init__.py          # Performance benchmarking
│   └── report/
│       └── __init__.py          # Report generation
├── tests/
│   ├── test_validation.py       # Core tests
│   └── test_third_party.py      # Third-party scanner tests
├── scripts/
│   ├── self_validate.py         # Self-validation script
│   └── setup.py                 # Development setup
├── .github/workflows/
│   └── ci.yml                   # CI/CD pipeline
└── docs/
    └── third-party-security-tools-research.md
```

## Features

### Security Scanning
- Pattern-based detection for secrets, eval, network calls, filesystem operations
- Third-party scanner integration (Bandit, Gitleaks, Safety)
- Configurable severity levels

### Validation
- SKILL.md structure validation
- YAML frontmatter parsing
- Script executable checks

### Benchmarking
- Load time measurement
- Metadata extraction timing
- Script syntax validation

## Development

```bash
# Setup development environment (installs uv if needed)
python3 scripts/setup.py
# Or with uv:
uv run python scripts/setup.py

# Run self-validation
uv run python scripts/self_validate.py
# Or directly (uses uv shebang):
./scripts/self_validate.py

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=skill_validation --cov-report=term-missing
```

## License

MIT
