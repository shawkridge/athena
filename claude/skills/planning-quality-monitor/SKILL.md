---
name: planning-quality-monitor
description: Detect plan deviations and trigger adaptive replanning in real-time
trigger: Task execution during work, PostToolUse on task status updates, phase progress tracking
confidence: 0.84
---

# Planning Quality Monitor Skill

Monitors plan execution in real-time, detects deviations from projections, and triggers adaptive replanning when needed.

## When I Invoke This

I detect:
- Task execution in progress (tool usage, time passing)
- Task status updates (completion, blocking)
- Phase progress calculation
- Plan timeline at risk
- Quality metrics degrading
- Resource constraints detected

## What I Do

```
1. Track execution progress
   → Call: list_tasks() to get current task status
   → Compare: Actual vs planned (duration, quality, completion)
   → Measure: Tasks completed / total tasks
   → Calculate: Phase progress percentage
   → Detect: Deviations >20% from plan

2. Evaluate quality metrics
   → Track: Quality score per task (target >0.8)
   → Monitor: Error rates (target <1%)
   → Measure: Code coverage (if applicable)
   → Assess: Test pass rate
   → Alert: If quality_score drops >5%

3. Monitor resource constraints
   → Check: Token usage vs budget
   → Check: Time spent vs allocation
   → Check: Agent availability
   → Check: Context window availability
   → Alert: If any constraint approaching limit

4. Detect deviation triggers (6 types)
   → DURATION_EXCEEDED: Task >50% longer than planned
   → QUALITY_DEGRADATION: Quality_score <0.80
   → BLOCKER_ENCOUNTERED: Unexpected obstacles
   → ASSUMPTION_VIOLATED: Plan assumptions failed
   → MILESTONE_MISSED: Milestone dates slipped
   → RESOURCE_CONSTRAINT: Resources unavailable

5. Trigger replanning
   → Call: trigger_replanning() with deviation details
   → Execute: Adaptive replanning logic
   → Adjust: Plan or adjust expectations
   → Update: ExecutionFeedback with learnings
```

## MCP Tools Used

- `list_tasks` - Get current task status
- `get_project_status` - Review plan and progress
- `trigger_replanning` - Initiate adaptive replanning
- `record_execution_feedback` - Track execution metrics
- `update_task_status` - Mark tasks updated
- `suggest_planning_strategy` - Recommend replanning approach

## Configuration

```
DEVIATION_THRESHOLDS:
  duration_exceeded: 50% over planned
  quality_degradation: <0.80 score or >5% drop
  blocker_severity: blocks >1 task
  resource_constraint: >90% utilized

CHECK_FREQUENCY:
  per_task_update: Every task status change
  periodic: Every 30 minutes of execution
  phase_progress: After 25% / 50% / 75% phase completion

ALERT_LEVELS:
  warning: 30% deviation or <0.85 quality
  critical: 50% deviation or <0.80 quality
  emergency: >75% deviation or <0.70 quality
```

## Example Invocation

```
User: [Working on phase 2 of OAuth2 implementation]

Planning Quality Monitor tracking...

📊 PHASE 2 PROGRESS CHECKPOINT (2 hours elapsed)
═════════════════════════════════════════════════

Plan vs Reality:

Task 1: JWT Signing Implementation
  Planned: 2 hours
  Actual: 1.5 hours (75% complete)
  Status: ✅ ON TRACK
  Quality: 0.92 (exceeds target 0.80)

Task 2: Token Validation
  Planned: 2 hours
  Actual: 2.2 hours elapsed (50% complete)
  Status: ⚠️  DURATION_EXCEEDED
  Progress: 50% (slower than planned)
  Quality: 0.78 (below target 0.80)
  Deviation: +10% over planned duration

Task 3: Refresh Token Logic (Not Started)
  Planned: Start at 2h mark
  Actual: Delayed by 0.2h
  Status: ⚠️  SLIGHT DELAY (acceptable)
  Impact: 0.2h slip on phase completion

Overall Phase 2 Progress:
  Planned: 33% complete (2h of 6h)
  Actual: 42% complete (2.5h effective work)
  Status: ✅ AHEAD OF SCHEDULE (surprising!)
  Reason: Task 1 completed faster than expected

═════════════════════════════════════════════════════════════

⚠️  DEVIATIONS DETECTED:

1. DURATION_EXCEEDED (Task 2: Token Validation)
   Duration: +10% over planned (2.0h planned, 2.2h actual)
   Quality: 0.78 (below 0.80 threshold)
   Severity: WARNING (not blocking, <20% overage)
   Cause Analysis: "Complex edge cases in validation logic"

   Options:
   a) Continue current approach (task quality acceptable)
   b) Allocate +15min to improve quality to >0.85
   c) Reduce scope (move some tests to phase 3)

   Recommendation: Option (a) - Continue, monitor next tasks
   Updated Timeline Impact: +10min on phase 2 (still on track)

2. QUALITY_DEGRADATION (Task 2: Token Validation)
   Quality Score: 0.78 (target: 0.80)
   Degradation: -0.02 (minor)
   Severity: WARNING
   Factors:
     • Test coverage: 85% (should be >90%)
     • Code review: Not yet done
     • Error handling: Some edge cases unclear

   Mitigation:
     → Add +20min for edge case tests
     → Fast code review before moving forward
     → Clear error handling documentation

   Recommendation: Block on code review (10min), continue testing

═════════════════════════════════════════════════════════════

📈 ADAPTIVE REPLANNING TRIGGERED

Deviation Type: DURATION_EXCEEDED + QUALITY_DEGRADATION
Severity: WARNING (not critical)
Replanning Mode: ADAPTIVE (adjust, don't abandon)

Current Plan (Original):
  Phase 2 Duration: 6 hours
  Phase 2 Target: Complete by 4:00 PM

Adaptive Replanning Options:
  Option 1 - Extend Timeline (Lower Risk)
    • Phase 2: 6.5 hours (extends to 4:30 PM)
    • Rationale: +10% overage on duration, quality maintained
    • Risk: Phase 3 delayed by 30min
    • Recommendation: ACCEPT (minor impact)

  Option 2 - Reduce Scope (Higher Risk)
    • Phase 2: 5.5 hours (cut 0.5h of testing)
    • Rationale: Move advanced tests to phase 3
    • Risk: Quality suffers (0.75 → 0.70), phase 3 overloaded
    • Recommendation: NOT RECOMMENDED

  Option 3 - Increase Parallelization (Medium Risk)
    • Phase 2: 6 hours (keep same total)
    • Rationale: Run Task 3 in parallel with Task 2
    • Risk: Dependency on Task 2 completion
    • Recommendation: POSSIBLE (if Task 3 has no Task 2 dependency)

Selected: Option 1 (Extend Timeline)
  Updated Phase 2 Duration: 6.5 hours
  New Target Completion: 4:30 PM
  Phase 3 Impact: Delayed 30 min (6:30 PM → 7:00 PM)
  Total Project Impact: 30 min longer (acceptable)

═════════════════════════════════════════════════════════════

✅ REPLANNING COMPLETE

Updated Plan:
  ✓ Phase 2 timeline extended to 6.5h (4:30 PM)
  ✓ Task 2 effort increased to 2.25h (better quality)
  ✓ Task 3 starts at 4:00 PM as scheduled
  ✓ Code review inserted before Task 3 (prevents cascading)

Monitoring Continues:
  • Next checkpoint: After Task 2 complete (2:30 PM)
  • Watch: Task 3 duration (if also at risk, escalate)
  • Quality: Continue targeting 0.80+

📋 ExecutionFeedback Recorded:
  • Task: Token Validation
  • Duration: 2.2h (10% overage)
  • Quality: 0.78 (below target)
  • Learning: "Complex edge cases require +15min planning"
  • Applied to: Future validation tasks (JWT, OAuth2, etc.)
```

## Expected Benefits

```
Risk Prevention: Detect deviations early, before cascading
Plan Adaptability: Adjust plans automatically instead of failing
Learning: Track what deviations occur, improve estimates
Transparency: User always knows plan status vs reality
Quality Maintenance: Ensure quality never degrades unnoticed
```

## Performance

- Status check: <500ms
- Deviation calculation: <1s
- Replanning decision: <5s
- Total latency: <10s (non-blocking)

## Integration Points

- Works with: Task execution tracking (every status update)
- Triggered by: PostToolUse on task updates
- Feeds into: consolidation-trigger (execution feedback)
- Works with: `/project-status` (shows deviations)
- Works with: `/plan-validate` (enforces new plan)

## Adaptive Replanning Triggers

```
1. DURATION_EXCEEDED
   Condition: Task duration >50% over planned
   Action: Adjust timeline or reduce scope

2. QUALITY_DEGRADATION
   Condition: Quality score <0.80 or drop >5%
   Action: Allocate time for quality improvement

3. BLOCKER_ENCOUNTERED
   Condition: Unexpected obstacle blocking progress
   Action: Create workaround path or adjust scope

4. ASSUMPTION_VIOLATED
   Condition: Plan assumption no longer valid
   Action: Replan affected phases

5. MILESTONE_MISSED
   Condition: Milestone date slipped >5%
   Action: Adjust downstream milestones

6. RESOURCE_CONSTRAINT
   Condition: Resources >90% utilized
   Action: Free resources or parallelize differently
```

## Quality Metrics Tracked

```
Per Task:
  • Duration (actual vs planned)
  • Quality score (target >0.80)
  • Error rate (target <1%)
  • Code coverage (if applicable)
  • Test pass rate (target 100%)

Per Phase:
  • Overall progress (% complete)
  • Milestones on track
  • Quality trending
  • Risk score (0-1.0)

Per Project:
  • Timeline buffer remaining
  • Quality trending
  • Assumption violations
  • Overall risk assessment
```

## Limitations

- Cannot predict unknown unknowns
- Quality metrics depend on good measurement
- Replanning can only adjust existing plan (not invent new options)
- Works best with well-decomposed tasks (30-min chunks)

## Related Commands

- `/project-status` - See plan and current deviations
- `/plan-validate` - Validate replanned plan before execution
- `/focus` - Adjust focus when blocker encountered
- `/task-create` - Create workaround tasks for blockers

## Success Criteria

✓ Detects deviations >20% from plan
✓ Quality degradation caught immediately
✓ Adaptive replanning triggered automatically
✓ Execution feedback recorded for learning
✓ Plans remain realistic and achievable
✓ User informed of changes proactively
