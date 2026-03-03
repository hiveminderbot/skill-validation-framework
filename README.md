# Skill Validation Framework

Universal validation and evaluation framework for OpenClaw skills.

## Purpose

Provide systematic validation for all OpenClaw skills across four layers:
1. **Security** — Scan for risky patterns
2. **Validation** — Structure and metadata validation
3. **Benchmarking** — Performance measurement and comparison
4. **Functional Testing** — Actual behavior testing with test cases

## Architecture

```
skill-validation-framework/
├── src/
│   ├── security/
│   │   └── scanner.py          # Security pattern detection
│   ├── validation/
│   │   └── tester.py           # Structure validation
│   ├── functional.py           # Functional testing module
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

# Structure validation
skill-validate validate ./path/to/skill

# Functional tests
skill-validate functional ./path/to/skill

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
python -m skill_validation functional ./path/to/skill
python -m skill_validation benchmark ./path/to/skill
python -m skill_validation report ./path/to/skill
```

### Functional Testing

Create a `tests/` directory in your skill with YAML test definitions:

```yaml
# tests/basic.yaml
name: Basic Skill Tests
description: Core functionality tests

setup_commands:
  - echo "Setting up"

tests:
  - name: test_basic_execution
    description: Test basic functionality
    input:
      action: test
      data:
        value: 42
    expected_output:
      status: success
    timeout_seconds: 10
    requires_tools:
      - python3
```

Run with: `skill-validate functional ./path/to/skill`

### JSON Output

Add `--format json` to any command for machine-readable output:

```bash
skill-validate security ./path/to/skill --format json
skill-validate validate ./path/to/skill --format json
```

## License

MIT
