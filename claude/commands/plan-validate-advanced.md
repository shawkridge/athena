---
description: Comprehensive plan validation with Q* verification, formal properties, and scenario testing
group: Planning & Validation
aliases: ["/validate-advanced", "/plan-check-advanced", "/verify-plan"]
---

# /plan-validate-advanced

Advanced comprehensive plan validation with formal Q* verification, 5-property checks, and optional scenario stress testing.

## Features

### Phase 6 Formal Verification (Q* Pattern)

Validates 5 formal properties required for high-confidence plans:

**Hard Properties (SMT Solver - Z3 verification)**:
- **Optimality** (0-1 score): Minimize resource consumption and timeline
- **Completeness** (0-1 score): Cover all stated requirements

**Soft Properties (LLM Extended Thinking)**:
- **Consistency** (0-1 score): No conflicts or contradictions
- **Soundness** (0-1 score): Valid assumptions and correct logic
- **Minimality** (0-1 score): No redundant or unnecessary steps

**Q* Score Formula**:
```
Q* = (Hard_Score × 0.6) + (Soft_Score × 0.4)
```

**Quality Levels**:
- **EXCELLENT** (≥0.8): Ready for execution
- **GOOD** (0.6-0.8): Proceed with caution
- **FAIR** (0.4-0.6): Requires refinement
- **POOR** (<0.4): Reject or heavily refine

## Usage

```bash
# Basic advanced validation
/plan-validate-advanced

# With active task context
/plan-validate-advanced --task-id 123

# Full validation including scenario testing
/plan-validate-advanced --include-simulation

# Strict mode (fail on Q* < 0.8)
/plan-validate-advanced --strict

# Deep analysis with LLM extended thinking
/plan-validate-advanced --deep

# Dry-run preview without persisting results
/plan-validate-advanced --dry-run

# Specific project
/plan-validate-advanced --project-id 1

# All options combined
/plan-validate-advanced --task-id 123 --include-simulation --strict --deep
```

## Output Example

```
ADVANCED PLAN VALIDATION REPORT
═══════════════════════════════════════════════════════════════

Project: ecommerce-auth-refactor
Plan Name: Phase 1 JWT Implementation
Validation Date: 2025-11-05T14:32:15Z
Status: GOOD ✓ (Q* = 0.72)

═══ PHASE 6: Q* FORMAL VERIFICATION ═══

Hard Properties (SMT Solver):
  ✓ Optimality:    0.75 (Good - minimal resource overhead)
  ✓ Completeness:  0.85 (Excellent - covers all requirements)

Soft Properties (LLM Extended Thinking):
  ✓ Consistency:   0.70 (Good - minor contradictions resolved)
  ✓ Soundness:     0.68 (Good - valid assumptions)
  ✓ Minimality:    0.72 (Good - some redundant tasks exist)

Q* COMPOSITE SCORE: 0.72 → GOOD ✓

Property Breakdown:
  • Optimality:    [████████░░] 0.75
  • Completeness:  [████████░░] 0.85
  • Consistency:   [███████░░░] 0.70
  • Soundness:     [███████░░░] 0.68
  • Minimality:    [███████░░░] 0.72

═══ PHASE 3: 3-LEVEL VALIDATION ═══

LEVEL 1: STRUCTURAL INTEGRITY
  ✓ Hierarchy valid (4 levels deep, max depth acceptable)
  ✓ Dependencies resolved (8 tasks, 0 cycles detected)
  ✓ Milestones ordered (5 milestones, chronologically valid)
  ✓ Resource allocation (8h/day available vs. 7h/day needed)

LEVEL 2: FEASIBILITY ANALYSIS
  ✓ Timeline realistic (24h estimate for 8h/day = 3 days)
  ✓ Estimated completion: 2025-11-15 (on track)
  ✓ Skill requirements met (team has JWT expertise)
  ⚠ WARNING: Database migration untested in prod
    → Confidence impact: -5%
    → Mitigation: Add pre-prod validation step

LEVEL 3: RULE COMPLIANCE
  ✓ Code review gates included (before merge)
  ✓ Testing coverage required (>80% target)
  ✓ Documentation updated (requirements found)
  ✓ Risk mitigation (fallback auth method available)
  ⚠ WARNING: Security audit missing
    → Timeline impact: +2h recommended
    → Mitigation: Schedule audit in parallel

═══ SCENARIO ANALYSIS (Optional) ═══
[Only included if --include-simulation flag used]

Scenario Simulations (5 scenarios):

BEST CASE (+25% speed):
  • Estimated duration: 2.25 days (vs. 3 baseline)
  • Resource peak: 6.5 h/day
  • Success probability: 95%
  • Key assumptions: Team fully available, no blockers

WORST CASE (-40% speed):
  • Estimated duration: 4.2 days (vs. 3 baseline)
  • Resource peak: 9.5 h/day (EXCEEDS CAPACITY)
  • Success probability: 60%
  • Key risks: Database issues, missing expertise
  • Mitigation: Add contingency buffer

LIKELY CASE (~-10% speed):
  • Estimated duration: 3.3 days (vs. 3 baseline)
  • Resource peak: 8.2 h/day (near capacity)
  • Success probability: 78%
  • Confidence interval: 2.8-3.8 days (80% confidence)
  • Key variables: Team velocity, scope creep

CRITICAL PATH:
  • Critical tasks: [Auth-Service, JWT-Config, Testing]
  • Critical path length: 2.1 days
  • Slack available: 1.2 days
  • Risk: Any critical task delay cascades
  • Mitigation: Parallelize non-critical tasks

BLACK SWAN (Unexpected event):
  • Example: Security vulnerability discovered
  • Impact variance: -50% to +200%
  • Likelihood: Low (~5%)
  • Contingency needed: Yes
  • Buffer recommendation: 2 extra days

Confidence Analysis:
  • Overall confidence: 73% (GOOD)
  • Distribution: ┌─────────┐
                   └─────────┘
  • 80% likely to complete: 2.8-3.8 days
  • 90% likely to complete: 2.4-4.4 days
  • Risk-adjusted timeline: 3.8 days (recommended)

═══ RECOMMENDATIONS ═══

Priority 1 (Critical):
  1. Add database migration rollback plan (blocks execution)
  2. Schedule security audit in parallel (2h)
  3. Verify team availability for 3 consecutive days

Priority 2 (High):
  1. Add pre-prod validation step (4h)
  2. Document failure recovery procedures (2h)
  3. Allocate load testing time (4h)

Priority 3 (Medium):
  1. Review JWT implementation patterns
  2. Update monitoring and alerting rules
  3. Prepare communication plan for production

═══ EXECUTION CHECKLIST ═══

Pre-Execution:
  ☑ Q* Score ≥ 0.6 (GOOD or better) - Met
  ☑ Critical issues resolved - 2 pending
  ☑ Team availability confirmed - Pending
  ☑ Dependencies available - Confirmed
  ☑ Rollback procedures defined - Missing
  ☑ Monitoring configured - Pending

Go/No-Go Decision: CONDITIONAL PROCEED
  → Can start with prerequisites:
     1. Address critical issues (1-2 hours)
     2. Confirm team 3-day availability
     3. Document rollback steps

═══ SUMMARY ═══

Validation Result: GOOD ✓
Q* Score: 0.72 (Soft properties need improvement)
Confidence Level: 73/100
3-Level Status: VALID ✓

Issues Found:
  • Critical: 2 (blocking, high effort to fix)
  • Warnings: 3 (address before execution)
  • Suggestions: 2 (nice to have)

Timeline:
  • Best case: 2.25 days
  • Expected: 3.3 days
  • Risk-adjusted: 3.8 days
  • Worst case: 4.2 days

Resource Utilization:
  • Average: 7 h/day
  • Peak (likely): 8.2 h/day
  • Peak (worst): 9.5 h/day (over capacity)
  • Mitigation: Spread worst-case over 4 days

Ready to Execute: YES, with prerequisites
Next Steps:
  1. Resolve 2 critical issues (2 hours)
  2. Run /stress-test-plan for detailed risk analysis
  3. Update /project-status when ready to start
```

## Options

- `--task-id ID` - Validate specific task plan
- `--project-id ID` - Validate specific project (default: 1)
- `--include-simulation` - Include 5-scenario stress testing
- `--strict` - Fail if Q* < 0.8 (EXCELLENT threshold)
- `--deep` - Use LLM extended thinking for all properties
- `--dry-run` - Preview without persisting results
- `--level 1|2|3|6` - Only validate specific level(s)
- `--show-properties` - Detailed property explanations

## Validation Levels

| Level | Name | What It Checks |
|-------|------|----------------|
| 1 | Structure | Dependencies, cycles, hierarchy, ordering |
| 2 | Feasibility | Timeline, resources, skills, constraints |
| 3 | Rules | Standards, gates, security, monitoring |
| 6 | Q* Properties | Optimality, completeness, consistency, soundness, minimality |

## Related Commands

- `/stress-test-plan` - Run 5-scenario stress testing separately
- `/plan-validate` - Quick basic validation
- `/project-status` - Track plan execution
- `/task-create` - Create tasks from validated plan
- `/resolve-conflicts` - Fix plan conflicts
- `/consolidate` - Extract learnings from plans

## Tips

1. **Run before major work**: Always validate before starting
2. **Address Q* < 0.6**: FAIR plans need refinement
3. **Use simulation for critical paths**: Stress test risky tasks
4. **Update after changes**: Re-validate after scope changes
5. **Document decisions**: Keep notes on validation decisions
6. **Monitor execution**: Track actual vs. predicted timeline

## Integration with Phase 6 Features

This command integrates Phase 6 planning tools:

- `validate_plan_comprehensive` - 3-level validation
- `verify_plan_properties` - Q* formal verification
- `simulate_plan_scenarios` - 5-scenario stress testing
- `validate_plan_with_llm` - Extended thinking validation
- `create_validation_gate` - Human-in-the-loop gates

## Performance

- **Basic validation**: <1 second (structure + feasibility)
- **Full validation**: <3 seconds (add rules check)
- **Q* verification**: <2 seconds (soft+hard properties)
- **With simulation**: <5 seconds (5 scenarios)
- **Deep analysis**: <10 seconds (LLM extended thinking)

## Success Metrics

A plan is ready when:
- ✓ Q* Score ≥ 0.7 (GOOD or better)
- ✓ All critical issues resolved
- ✓ Confidence level ≥ 70%
- ✓ Risk-adjusted timeline acceptable
- ✓ Team availability confirmed
- ✓ Dependencies secured

## See Also

- `/stress-test-plan` - Detailed scenario analysis
- `/decompose-with-strategy` - Task decomposition
- `/check-goal-conflicts` - Conflict detection
- `/resolve-conflicts` - Auto conflict resolution
