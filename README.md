# Skill Validation Framework

Universal validation and evaluation framework for OpenClaw skills.

## Purpose

Provide systematic validation for all OpenClaw skills across three layers:
1. **Security** — Scan for risky patterns
2. **Validation** — Functional correctness testing
3. **Benchmarking** — Performance measurement and comparison

## Architecture

```
skill-validation-framework/
├── src/
│   ├── security/
│   │   └── scanner.py          # Security pattern detection
│   ├── validation/
│   │   └── tester.py           # Functional correctness tests
│   ├── benchmark/
│   │   └── runner.py           # Performance benchmarking
│   └── report/
│       └── generator.py        # Comparative report generation
├── tests/
│   └── fixtures/               # Synthetic task definitions
├── docs/
│   ├── security-checklist.md
│   ├── validation-criteria.md
│   └── benchmark-suite.md
└── README.md
```

## Usage

```bash
# Security scan
python -m skill_validation.security.scanner ./path/to/skill

# Functional validation
python -m skill_validation.validation.tester ./path/to/skill

# Benchmark
python -m skill_validation.benchmark.runner ./path/to/skill

# Full report
python -m skill_validation.report.generator ./path/to/skill --compare ./path/to/other/skill
```

## License

MIT
