---
name: plan-verification
description: |
  Verify plans using Q* formal verification and 5-scenario stress testing.
  Use before committing to plans for high-risk changes. Checks 5 properties and simulates scenarios.
  Provides confidence intervals and detailed validation results.
---

# Plan Verification Skill

Comprehensive plan validation with formal verification and stress testing.

## When to Use

- Before committing to complex plans
- For high-risk or critical changes
- When you need confidence in plan feasibility
- Assessing plan quality before execution

## Validation Checks

**3 Levels**:
1. Structure: Format, sequencing, dependency correctness
2. Feasibility: Resources, timeline, assumptions
3. Rules: Constraints, best practices, compliance

**Q* Properties**:
- Optimality (resource efficiency)
- Completeness (requirement coverage)
- Consistency (no conflicts)
- Soundness (valid logic)
- Minimality (no redundancy)

**5 Scenarios**:
- Best case (+25% speed)
- Worst case (-40% speed)
- Likely case (~-10% speed)
- Critical path focus
- Black swan events

## Returns

- Q* Score (0.0-1.0): EXCELLENT/GOOD/FAIR/POOR
- Validation issues with severity
- Scenario results with confidence intervals
- Critical path analysis
- Resource conflicts
- Recommendations

The plan-verification skill activates before major execution commitments.
