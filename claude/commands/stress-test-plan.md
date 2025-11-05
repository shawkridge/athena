---
description: Stress-test plans with 5 scenario simulations and confidence interval analysis
group: Planning & Validation
aliases: ["/test-plan", "/plan-stress", "/simulate-plan"]
---

# /stress-test-plan

Stress-test your plan under 5 different scenarios to determine success probability and confidence intervals.

## Features

### 5-Scenario Stress Testing

Plans are automatically tested under realistic scenarios to identify risks and bottlenecks:

**Scenario 1: BEST CASE**
- Everything goes perfectly
- Team fully available and productive
- No unexpected blockers
- Optimal dependencies
- **Speed modifier**: +25% (faster execution)

**Scenario 2: WORST CASE**
- Multiple problems occur
- Team unavailable/distracted
- Critical dependencies delayed
- Resource constraints hit
- **Speed modifier**: -40% (slower execution)

**Scenario 3: LIKELY CASE** (Most Probable)
- Normal issues and delays
- Team ~80% productive
- Minor blockers
- Some resource contention
- **Speed modifier**: -10% (baseline +10% variance)

**Scenario 4: CRITICAL PATH**
- Focus on bottleneck tasks
- Identify longest dependency chain
- Measure slack available
- Detect cascading risks
- **Output**: Critical path duration and slack analysis

**Scenario 5: BLACK SWAN**
- Unexpected major event
- Examples: Security vulnerability, scope explosion, key person unavailable
- Variable impact: -50% to +200% of baseline
- Low probability but high impact
- **Output**: Contingency buffer recommendations

### Confidence Intervals

Each scenario generates a confidence envelope:

```
Timeline confidence intervals:
  50% confident: 2.8-3.2 days (±7% of baseline)
  80% confident: 2.5-3.8 days (±27% of baseline)
  90% confident: 2.2-4.4 days (±47% of baseline)
  95% confident: 2.0-5.0 days (±67% of baseline)
```

## Usage

```bash
# Basic stress test (all 5 scenarios)
/stress-test-plan

# Stress test specific task
/stress-test-plan --task-id 123

# Specific project
/stress-test-plan --project-id 1

# Only specific scenarios
/stress-test-plan --scenarios best,worst,likely
/stress-test-plan --scenarios critical_path
/stress-test-plan --scenarios black_swan

# Advanced options
/stress-test-plan --iterations 10        # Run 10 simulations per scenario
/stress-test-plan --confidence 95        # Show 95% confidence intervals
/stress-test-plan --show-bottlenecks     # Detailed bottleneck analysis
/stress-test-plan --risk-sensitivity     # Risk factor sensitivity analysis
/stress-test-plan --monte-carlo 1000     # Monte Carlo simulation (1000 runs)

# Comparison
/stress-test-plan --compare-plans        # Compare multiple plan versions

# Generate report
/stress-test-plan --export json          # Export results as JSON
/stress-test-plan --export html          # Export results as HTML report
```

## Output Example

```
PLAN STRESS TEST REPORT
═══════════════════════════════════════════════════════════════════════

Project: ecommerce-auth-refactor
Plan: Phase 1 JWT Implementation
Test Date: 2025-11-05T14:35:22Z
Baseline Duration: 3.0 days (24 hours of effort)

═══ SCENARIO 1: BEST CASE (+25% speed) ═══

Duration: 2.25 days (1.8 hours/day effective = 18 hours total)
Resource Peak: 6.5 h/day (comfortable)
Success Probability: 95%

Key Assumptions:
  ✓ Team fully available (all 3 days)
  ✓ No unexpected blockers
  ✓ All dependencies available on time
  ✓ Team velocity at peak (120%)
  ✓ No scope creep

Risk Factors (minimal):
  • Database might be slightly slower than expected: -0.1 days
  • Code review feedback might require minor changes: -0.05 days

Completion Date: 2025-11-07 (Best estimate)
Confidence: 95% (Best case is less likely but possible)

Recommendations:
  → This is the aspirational timeline
  → Use for "everything goes right" planning
  → Keep 1-2 day buffer for reality

═══ SCENARIO 2: WORST CASE (-40% speed) ═══

Duration: 4.2 days (5.7 hours/day effective = 24 hours over 4.2 days)
Resource Peak: 9.5 h/day (EXCEEDS CAPACITY - unsustainable)
Success Probability: 60%

Key Challenges:
  ✗ Team availability issues (conflicts, distractions)
  ✗ Database migration encounters unexpected schema issues
  ✗ JWT implementation has subtle bugs requiring rework
  ✗ Security audit delays testing phase by 1 day
  ✗ Code review requests major refactoring (5h rework)
  ✗ Production issues discovered (8h diagnosis + fix)

Risk Factors (critical):
  • Resource constraint violation: Peak = 9.5 h/day > capacity (8 h/day)
  • Timeline slips beyond predicted window
  • Team burnout due to 4+ consecutive long days
  • Quality degradation from rushing

Completion Date: 2025-11-09 (Worst estimate)
Confidence: 60% (Only 60% chance to succeed under these conditions)

Mitigations:
  → MUST spread over 5 days to stay within 8h/day capacity
  → Parallelize testing with implementation (2h overlap)
  → Pre-allocate security audit to reduce cascade delay
  → Have rollback procedure ready (critical)

ACTION REQUIRED: Do not start if these risks are unmitigated!

═══ SCENARIO 3: LIKELY CASE (~-10% speed) ═══

Duration: 3.3 days (7.2 hours/day effective = 24 hours over 3.3 days)
Resource Peak: 8.2 h/day (near capacity but manageable)
Success Probability: 78%

Key Assumptions:
  ~ Team ~80% productive (normal distractions, interruptions)
  ~ Minor blockers discovered and resolved
  ~ Some scope creep (+5-10% effort)
  ~ Code review feedback requires minor rework
  ~ External dependencies available (slight delays)

Typical Issues:
  • Database migration testing takes 1h longer (schema edge case)
  • Code review finds style issues (1h fix)
  • One team member has other commitments (2h context switching)
  • Environment setup takes 30min longer than expected
  • Unexpected edge case in error handling (2h debug)

Completion Date: 2025-11-08 (Expected completion)
Confidence: 78% (Most likely scenario based on historical data)

Resource Planning:
  • Day 1: 8h (Auth service setup + JWT config)
  • Day 2: 8.2h (Integration testing + fixes)
  • Day 3: 7h (Final testing + deployment prep)

Contingency Buffer: Add 0.5 days = 3.8 day target

Status: ACCEPTABLE - This is the baseline prediction

═══ SCENARIO 4: CRITICAL PATH ANALYSIS ═══

Critical Path Tasks (longest chain):
  1. Database schema migration [8h] ← START
  2. Auth service implementation [6h]
  3. JWT configuration [4h]
  4. Integration testing [3h]
  5. Security audit [2h] ← Blocks production

Critical Path Duration: 2.1 days minimum
Buffer Available: 1.2 days (of 3.3 day baseline)

Critical Tasks (any delay cascades):
  ✗ Database migration: 8h
  ✗ Auth service: 6h
  ✗ Security audit: 2h

Non-critical Tasks (have slack):
  ✓ JWT config: 0.5h slack (can shift 30min later)
  ✓ Unit testing: 1h slack (can parallelize)
  ✓ Documentation: 1.5h slack (can do in parallel)

Bottleneck Analysis:
  1. Database migration is #1 bottleneck (8h, 33% of critical path)
     → Mitigation: Start immediately, parallelize schema design
  2. Auth service is #2 bottleneck (6h, 25% of critical path)
     → Mitigation: Have 2 devs assigned, pair programming
  3. Security audit is #3 bottleneck (2h, 8% of critical path)
     → Mitigation: Run in parallel with integration testing

Slack Timeline:
  Task 1 (DB): 0 days slack (on critical path)
  Task 2 (Auth): 0 days slack (on critical path)
  Task 3 (JWT): 0.5h slack
  Task 4 (Integration): 0 days slack (on critical path)
  Task 5 (Audit): Blocks go-live (treat as critical)

Risk-Critical Dependencies:
  • Database migration → Cannot start auth service without it
  • JWT config → Cannot test without auth service
  • Security audit → Blocks production deployment

Recommendations:
  1. Assign 2 developers to database migration (critical path)
  2. Use WIP limits: database (1 task) → auth → testing
  3. Pre-schedule security audit for day 2-3 afternoon
  4. Have database schema review ready day 0 evening

═══ SCENARIO 5: BLACK SWAN EVENT ═══

Unexpected Major Event (low probability, high impact):

Scenario A: Security Vulnerability Discovered
  • Probability: ~5% (given industry trends)
  • Impact: +3 days (emergency fix + re-test + audit)
  • Timeline becomes: 3.3 + 3.0 = 6.3 days
  • Cost: $15-20K in emergency auditing
  • Mitigation: Security audit earlier (shift from day 3 to day 1)

Scenario B: Key Team Member Unavailable
  • Probability: ~8% (illness, emergency, etc.)
  • Impact: +1.5 days (knowledge transfer + ramp up new person)
  • Timeline becomes: 3.3 + 1.5 = 4.8 days
  • Mitigation: Cross-training on critical database tasks

Scenario C: Scope Explosion
  • Probability: ~15% (client requests feature parity)
  • Impact: +2 days (additional requirements)
  • Timeline becomes: 3.3 + 2.0 = 5.3 days
  • Mitigation: Freeze scope by day 0 EOD, document change process

Scenario D: Database Performance Issues
  • Probability: ~10% (prod data characteristics)
  • Impact: +2.5 days (optimization + re-testing)
  • Timeline becomes: 3.3 + 2.5 = 5.8 days
  • Mitigation: Load test with production dataset (day 2)

Most Likely Black Swan: Scenario A (Security) or C (Scope)
Contingency Buffer Needed: 2-3 extra days
Mitigation Priority: Scope control > Security audit early > Team coverage

═══ CONFIDENCE ENVELOPE ═══

Timeline Distribution:
  Pessimistic (Worst Case):  4.2 days (13%)
  Concerning (75th %ile):     3.8 days (25%)
  Expected (Median):          3.3 days (50%)
  Optimistic (25th %ile):     2.8 days (75%)
  Best Case:                  2.25 days (95%)

Confidence Analysis:
  50% confident to finish within:     2.8-3.2 days (±0.2 days)
  75% confident to finish within:     2.5-3.8 days (±0.5 days)
  80% confident to finish within:     2.4-4.2 days (±0.9 days)
  90% confident to finish within:     2.2-4.8 days (±1.3 days)
  95% confident to finish within:     2.0-5.5 days (±1.75 days)

Graphical Distribution:
  Probability
      ↑
      │     ╱╲
      │    ╱  ╲
      │   ╱    ╲      Likely case
      │  ╱      ╲
      │ ╱        ╲___  Black swan tail
      │╱________________╲
      └─────────────────────→ days
       2    3    4    5    6
      Best  Expected  Worst  Catastrophic

═══ EXECUTION RECOMMENDATIONS ═══

Recommended Timeline: 3.8 days (80% confidence)
  → Adds 0.5 day contingency buffer to likely case
  → Absorbs minor issues (database edge cases, scope creep)
  → Comfortable resource utilization (7-8 h/day)
  → Allows for code review feedback and rework

Resource Allocation:
  Day 1: 8h (Auth service + database migration)
  Day 2: 8h (Integration testing + fixes)
  Day 3: 8h (Security audit + final testing)
  Day 4: 4h (Deployment prep + documentation) ← Buffer day

Team Assignments:
  • Developer A: Database migration (critical path #1)
  • Developer B: Auth service (critical path #2)
  • Developer C: Testing & QA (integration validation)
  • Tech Lead: Code review + unblocking
  • Security: Parallel audit (start day 2)

Risk Controls:
  ✓ Database review before implementation
  ✓ Pair programming on critical path tasks
  ✓ Daily sync on blockers
  ✓ Pre-allocated security audit
  ✓ Rollback procedure documented
  ✓ Monitoring/alerting configured

Go/No-Go Criteria:
  ✓ 78%+ success probability (in likely case) - Met
  ✓ Resource constraints manageable - Met
  ✓ Black swan mitigation in place - Pending
  ✓ Critical path identified and addressed - Met
  ✓ 80%+ confidence acceptable - Met

Decision: PROCEED WITH 3.8 DAY TARGET
  → Adjust timeline if worst-case elements appear
  → Use critical path task assignments
  → Monitor for black swan indicators

═══ SUMMARY ═══

Baseline Plan: 3.0 days (baseline effort)

Scenario Results:
  • Best Case: 2.25 days (95% probability of finishing by this)
  • Likely Case: 3.3 days (78% success probability)
  • Worst Case: 4.2 days (60% success probability)
  • Critical Path: 2.1 days minimum
  • With Black Swan: 5.3-6.3 days (low probability)

Recommended Timeline: 3.8 days (80% confidence)
Confidence Level: 78-80% (Good for production)

Critical Risks:
  1. Database migration complexity (8h bottleneck)
  2. Team resource constraints (peak 8.2 h/day)
  3. External dependency timing (security audit)
  4. Scope creep (typical +5-10%)

Bottleneck #1: Database migration (8h, 33% of critical path)
Bottleneck #2: Auth service implementation (6h, 25%)
Bottleneck #3: Security audit (2h, 8%)

Mitigation Strategy:
  → Assign 2 devs to database migration
  → Parallelize security audit
  → Buffer day for contingencies
  → Scope freeze by day 0 EOD

Ready to Execute: YES
Next Step: Use /plan-validate-advanced for formal Q* verification
```

## Options

- `--task-id ID` - Stress test specific task
- `--project-id ID` - Stress test project (default: 1)
- `--scenarios LIST` - Only run specific scenarios (best, worst, likely, critical_path, black_swan)
- `--iterations N` - Run N simulation iterations per scenario (default: 100)
- `--confidence PCT` - Show N% confidence intervals (default: 80%)
- `--show-bottlenecks` - Detailed bottleneck analysis
- `--risk-sensitivity` - Show how plan changes with different risk levels
- `--monte-carlo N` - Run N Monte Carlo simulations (probabilistic)
- `--compare-plans` - Compare multiple plan versions
- `--export FORMAT` - Export results (json, html, csv)

## Scenario Descriptions

| Scenario | Speed Modifier | Success Rate | Use Case |
|----------|---|---|---|
| Best Case | +25% | 95% | Aspirational planning |
| Worst Case | -40% | 60% | Risk assessment |
| Likely Case | -10% | 78% | **Expected outcome** |
| Critical Path | N/A | Varies | Bottleneck identification |
| Black Swan | -50 to +200% | <10% | Contingency planning |

## Confidence Intervals

The command calculates confidence envelopes showing:

- **50% confidence**: 7% variance (most likely band)
- **80% confidence**: 27% variance (planning band)
- **90% confidence**: 47% variance (worst-case acceptable)
- **95% confidence**: 67% variance (extreme outliers)

## Related Commands

- `/plan-validate-advanced` - Formal validation with Q*
- `/project-status` - Track plan execution
- `/task-create` - Create tasks from plan
- `/resolve-conflicts` - Fix plan conflicts
- `/consolidate` - Extract learnings

## Tips

1. **Always stress test critical projects**: Use before major work
2. **Focus on critical path**: 80% of delays come from 20% of tasks
3. **Plan for likely case**: Use 80% confidence interval as target
4. **Have contingency**: Add buffer equal to likely-to-worst delta
5. **Monitor real-time**: Track actual vs. predicted daily

## Success Criteria

Plan is ready when:
- ✓ Likely case success ≥ 75%
- ✓ 80% confidence interval acceptable
- ✓ Critical path mitigated
- ✓ Black swan contingency ≥ 2 days
- ✓ Resource peak ≤ 8 h/day (sustainable)

## See Also

- `/plan-validate-advanced` - Q* formal verification
- `/decompose-with-strategy` - Task decomposition
- `/check-goal-conflicts` - Conflict detection
- `/project-status` - Plan execution tracking
