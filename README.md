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

### CLI Commands

The framework provides a unified CLI via the `skill-validate` command:

```bash
# Activate virtual environment first
source .venv/bin/activate

# Security scan
skill-validate security ./path/to/skill

# Functional validation
skill-validate validate ./path/to/skill

# Benchmark
skill-validate benchmark ./path/to/skill

# Full report
skill-validate report ./path/to/skill --compare ./path/to/other/skill
```

### Alternative: Module Execution

You can also run via Python module:

```bash
python -m skill_validation security ./path/to/skill
python -m skill_validation validate ./path/to/skill
python -m skill_validation benchmark ./path/to/skill
python -m skill_validation report ./path/to/skill
```

### JSON Output

Add `--format json` to any command for machine-readable output:

```bash
skill-validate security ./path/to/skill --format json
skill-validate validate ./path/to/skill --format json
```

## License

MIT
