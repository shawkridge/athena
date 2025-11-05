---
description: Validate plans with 3-level verification (structure, feasibility, rules)
group: Planning & Validation
aliases: ["/validate", "/plan-check", "/pre-flight"]
---

# /plan-validate

3-level plan validation checking structure, feasibility, and rule compliance before execution.

## Usage

```bash
/plan-validate                # Quick validation
/plan-validate --strict      # Fail on warnings
/plan-validate --project NAME # Validate specific project
/plan-validate --detailed    # Full analysis
```

## What It Validates

**Level 1: Structural Integrity**
- No circular dependencies
- Milestones ordered chronologically
- Tasks properly hierarchical
- Resources allocated

**Level 2: Feasibility Analysis**
- Timeline realistic
- Resource constraints satisfied
- Skill requirements met
- External dependencies available

**Level 3: Rule Compliance**
- Project standards followed
- Quality gates included
- Risk mitigation in place
- Rollback procedures defined

## Example Output

```
PLAN VALIDATION REPORT
═══════════════════════════════════════════

Project: ecommerce-auth-refactor
Plan Name: Phase 1 JWT Implementation
Status: VALID ✓ (with warnings)

═══ LEVEL 1: STRUCTURAL INTEGRITY ═══

✓ Hierarchy valid (4 levels deep)
✓ Dependencies resolved (8 tasks, 0 cycles)
✓ Milestones ordered (5, all future dates)
✓ Resource allocation (8h/day available)

═══ LEVEL 2: FEASIBILITY ═══

✓ Timeline realistic (24h estimate for 8h/day = 3 days)
✓ Estimated completion: 2025-11-15 (on track)
⚠ WARNING: Database migration untested in prod
  → Recommendation: Add pre-prod validation
⚠ WARNING: No rollback procedure documented
  → Recommendation: Document rollback steps

✓ Skill requirements met (team has JWT expertise)
⚠ WARNING: Performance testing not allocated
  → Recommendation: Add 4h for load testing

═══ LEVEL 3: RULE COMPLIANCE ═══

✓ Code review gates included (before merge)
✓ Testing coverage required (>80% target)
✓ Documentation updated (found requirements)
⚠ WARNING: Security audit missing
  → Recommendation: Schedule before production
✓ Risk mitigation (fallback auth method available)
✓ Monitoring configured (error tracking enabled)

═══ SUMMARY ═══

Validation Result: VALID ✓
Confidence Level: 88/100 (Good, minor issues)

Issues Found:
  • 0 Critical
  • 3 Warnings
  • 1 Suggestion

Recommendations:
  1. Document database migration rollback (critical)
  2. Add pre-prod validation step (medium)
  3. Schedule security audit (medium)
  4. Allocate load testing (low)

Ready to Execute: YES, with caveats
Next Step: Address warnings, then /project-status for tracking

Estimated Timeline:
  • Phase duration: 3 calendar days
  • Daily effort: 8h/day
  • Start: ASAP
  • Completion: 2025-11-15
```

## Options

- `--strict` - Fail on any warning
- `--detailed` - Full level-by-level analysis
- `--project NAME` - Validate specific project
- `--level 1|2|3` - Validate specific level
- `--dry-run` - Preview without modifying

## Integration

Works with:
- `/project-status` - See validated plan
- `/task-create` - Create tasks from plan
- `/consolidate` - Extract learnings from validation
- `/focus` - Load plan context

## Related Tools

- `validate_plan` - Core validation
- `verify_plan` - Formal verification
- `suggest_planning_strategy` - Strategy recommendation
- `decompose_hierarchically` - Task decomposition
- `trigger_replanning` - Adaptive replanning

## Validation Levels

| Level | Checks | When |
|-------|--------|------|
| 1 (Structure) | Dependencies, hierarchy, order | Always |
| 2 (Feasibility) | Timeline, resources, skills | Before start |
| 3 (Rules) | Standards, quality, security | Before production |

## Tips

1. Validate before major work
2. Address critical issues immediately
3. Document warnings in project notes
4. Re-validate after major changes
5. Use strict mode for production

## See Also

- `/project-status` - Track plan execution
- `/task-create` - Create tasks from plan
- `/reflect` - Reflect on plan outcomes
