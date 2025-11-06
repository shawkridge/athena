---
description: Validate plan using Q* formal verification and 5-scenario stress testing
argument-hint: "Plan ID or plan description to validate"
---

# Validate Plan

Comprehensively validate a plan using Q* formal verification (5 properties) and 5-scenario stress testing.

Usage: `/validate-plan "plan description or ID"`

Validation includes:

**3-Level Validation**:
1. **Structure**: Format, step sequencing, dependency correctness
2. **Feasibility**: Resource availability, timeline realism, assumption validity
3. **Rules**: Compliance with constraints, best practices, organizational standards

**Q* Formal Verification** (5 Properties):
- **Optimality**: Minimize resource consumption
- **Completeness**: Cover all requirements
- **Consistency**: No conflicts or contradictions
- **Soundness**: Valid assumptions, correct logic
- **Minimality**: No redundant steps

**5-Scenario Stress Testing**:
1. **Best Case**: Everything perfect (+25% speed)
2. **Worst Case**: Multiple issues (-40% speed)
3. **Likely Case**: Normal issues (~-10% speed)
4. **Critical Path**: Focus on bottlenecks
5. **Black Swan**: Unexpected events

Returns:
- Q* Score (0.0-1.0): EXCELLENT (≥0.8), GOOD (0.6-0.8), FAIR (0.4-0.6), POOR (<0.4)
- Validation issues with severity levels
- 5 scenario results with confidence intervals
- Critical path and bottleneck analysis
- Resource conflict detection
- Optimization recommendations

The plan-validator agent autonomously invokes this before complex execution.
