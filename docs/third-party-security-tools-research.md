# Third-Party Security Tools Research

## Research Date: 2026-02-26

## Executive Summary

This document outlines third-party security tools that can be integrated into the Skill Validation Framework to enhance security scanning capabilities beyond the current regex-based approach.

## Tools Researched

### 1. Bandit (Python SAST)
- **Purpose**: Static Application Security Testing (SAST) for Python
- **Strengths**: 
  - Detects insecure function use (eval, exec, subprocess with shell=True)
  - Identifies hardcoded passwords and weak crypto
  - Checks for SQL injection patterns
  - Active project with regular updates
- **Integration**: Can be run as a subprocess, outputs JSON
- **License**: Apache 2.0
- **Priority**: HIGH

### 2. Semgrep
- **Purpose**: Lightweight static analysis with custom rules
- **Strengths**:
  - Fast, lightweight program analysis
  - Custom rule support
  - Multiple language support
  - Active community with rule registry
- **Integration**: CLI tool with JSON output
- **License**: LGPL 2.1 (open source engine)
- **Priority**: HIGH

### 3. Gitleaks
- **Purpose**: Secret detection (API keys, tokens, passwords)
- **Strengths**:
  - Specialized for secret detection
  - 700+ detection rules
  - Can scan git history
  - Fast scanning
- **Integration**: CLI with JSON output
- **License**: MIT
- **Priority**: MEDIUM-HIGH

### 4. TruffleHog
- **Purpose**: Secret detection with verification
- **Strengths**:
  - 700+ detection rules
  - Secret verification (checks if live)
  - Git history scanning
  - Enterprise features available
- **Integration**: CLI with JSON output
- **License**: AGPL-3.0
- **Priority**: MEDIUM-HIGH

### 5. Safety (Dependency Scanning)
- **Purpose**: Check Python dependencies for known vulnerabilities
- **Strengths**:
  - Scans requirements.txt, poetry.lock, etc.
  - Database of known CVEs
  - Commercial API available for more data
- **Integration**: CLI with JSON output
- **License**: MIT
- **Priority**: MEDIUM

## Integration Strategy

### Phase 1: Bandit Integration
- Add bandit as optional dependency
- Create wrapper module in `security/bandit_integration.py`
- Parse JSON output and convert to SecurityIssue format
- Add CLI flag `--use-bandit`

### Phase 2: Secret Scanning (Gitleaks)
- Add gitleaks as optional dependency
- Create wrapper in `security/gitleaks_integration.py`
- Focus on current files (not git history for speed)
- Add CLI flag `--use-gitleaks`

### Phase 3: Dependency Scanning (Safety)
- Add safety as optional dependency
- Create wrapper in `security/safety_integration.py`
- Scan for vulnerable dependencies
- Add CLI flag `--use-safety`

### Phase 4: Semgrep Rules
- Create custom semgrep rules for OpenClaw-specific patterns
- Add to `security/rules/` directory
- Run semgrep with custom ruleset

## Implementation Plan

1. Create `ThirdPartyScanner` base class
2. Implement individual scanner wrappers
3. Add configuration file support (.skill-validation.yaml)
4. Update CLI to support tool selection
5. Update CI pipeline to run all scanners

## Recommendations

1. **Start with Bandit** - Best ROI for Python security
2. **Add Gitleaks** - Better secret detection than current regex
3. **Consider Safety** - Dependency scanning is valuable
4. **Evaluate Semgrep** - Custom rules for OpenClaw patterns

## References

- Bandit: https://bandit.readthedocs.io/
- Semgrep: https://semgrep.dev/
- Gitleaks: https://github.com/gitleaks/gitleaks
- TruffleHog: https://github.com/trufflesecurity/trufflehog
- Safety: https://github.com/pyupio/safety
