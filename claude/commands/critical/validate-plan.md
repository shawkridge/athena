---
description: Validate plan using Q* formal verification and scenario testing - assesses feasibility, risk, and success probability
argument-hint: "Plan ID or plan description to validate"
---

# Validate Plan - Plan Validation and Risk Assessment

Validates plan structure, feasibility, and quality using Q* properties and scenario analysis.

## How It Works

1. **Discover** - Analyze plan structure (goals, timeline, resources, criteria)
2. **Execute** - Verify Q* properties (optimality, completeness, consistency, soundness)
3. **Summarize** - Return validation report with risk assessment and recommendations

## Implementation

```bash
#!/bin/bash
# Validate Plan Command
# Usage: /critical:validate-plan "plan description" [--scenarios]

PLAN="${1:-}"

if [ -z "$PLAN" ]; then
  echo '{"status": "error", "error": "Plan description required"}'
  exit 1
fi

cd /home/user/.work/athena
PYTHONPATH=/home/user/.work/athena/src python3 -m athena.cli --json validate-plan "$PLAN"
```

## Examples

```bash
# Validate plan structure
/critical:validate-plan "Implement context injection with MemoryBridge and CLI"

# Validate with scenario analysis
/critical:validate-plan "Add memory search to slash commands" --scenarios

# Quick validation check
/critical:validate-plan "My task"
```

## Response Format

```json
{
  "status": "success",
  "plan_description": "implement memory search...",
  "validation_passed": true,
  "risk_level": "low",
  "checks_performed": 5,
  "checks_passed": 5,
  "issues": [],
  "recommendations": [],
  "ready_for_execution": true,
  "execution_time_ms": 15
}
```

## Validation Checks

1. **Clear Goal** - Plan has explicit objective
2. **Timeline** - Plan specifies when/duration
3. **Resources** - Plan lists team, tools, budget
4. **Success Criteria** - Plan defines how to measure success
5. **Reasonable Scope** - Plan under 5000 characters

## Risk Levels

- **Low Risk**: 4-5 checks passed
- **Medium Risk**: 2-3 checks passed
- **High Risk**: 0-1 checks passed

## Pattern Details

### Phase 1: Discover
- Analyzes plan text for structure elements
- Detects goal, timeline, resources, criteria
- Returns: structural_analysis

### Phase 2: Execute
- Runs 5 validation checks
- Verifies Q* properties
- Assesses risk level
- Returns: validation_results

### Phase 3: Summarize
- Formats validation report
- Lists issues and recommendations
- Indicates readiness for execution
- Returns structured JSON (<300 tokens)

## Q* Properties Checked

- **Optimality**: Does plan achieve goals efficiently?
- **Completeness**: Does plan cover all necessary steps?
- **Consistency**: Are steps logically consistent?
- **Soundness**: Do assumptions hold true?
- **Minimality**: Are there unnecessary steps?
