# /progress

Record execution progress toward goal completion with health analysis.

## Usage

```bash
/progress --goal-id 1 --completed 5 --total 10    # Tasks completed
/progress --goal-id 1 --percent 50                 # Or by percentage
/progress --goal-id 1 --percent 50 --errors 2     # Include errors
/progress --goal-id 1 --percent 50 --blockers 1   # Include blockers
/progress --goal-id 1 --percent 50 --notes "..."  # Add notes
```

## Description

Records and tracks progress for a goal with comprehensive health analysis.

Updates:
- Completion percentage and task counts
- Error count and impact assessment
- Blocker count and mitigation status
- Health score (0-1 scale)
- On-track status vs. timeline
- Milestone tracking and reached events
- Estimated completion with variance
- Risk assessment

**Internally calls**:
- `task_management_tools:record_execution_progress` - Progress recording
- `task_management_tools:update_milestone_progress` - Milestone tracking
- `monitoring_tools:get_task_health` - Health calculation
- `monitoring_tools:detect_bottlenecks` - Blocker analysis

## Options

- `--goal-id` (required) - Goal ID to update
- `--completed` (optional) - Steps/items completed
- `--total` (optional) - Total steps/items
- `--percent` (optional) - Completion percentage (0-100)
- `--errors` (optional) - Error count encountered
- `--blockers` (optional) - Blocker count
- `--notes` (optional) - Progress notes/updates
- `--milestone` (optional) - Mark milestone as reached
- `--velocity-rate` (optional) - Update estimated velocity

## Output

Comprehensive progress report showing:
- ✓ Confirmation of progress recording
- **Progress Metrics**:
  - Completion percentage
  - Tasks completed / total
  - Velocity (tasks per hour)
- **Health Analysis**:
  - Health score (0-1, color coded)
  - On-track status with explanation
  - Error assessment
  - Blocker impact
- **Timeline**:
  - Estimated completion date
  - Days remaining
  - Variance from baseline
  - Confidence level
- **Milestone Status**:
  - Reached milestones
  - Next milestone target
  - Estimated time to next
- **Risk Assessment**:
  - Risk factors
  - Bottleneck identification
  - Recommendations

## Example Output

```
> /progress --goal-id 1 --completed 3 --total 10 --errors 1 --blockers 0 --notes "Auth service setup complete"

✓ Progress recorded for Goal #1: "Implement user authentication"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 PROGRESS METRICS

Completion: 30% (3 of 10 steps)
  ├─ Completed:     3 steps ✓
  ├─ In Progress:   2 steps 🔄
  ├─ Remaining:     5 steps ⏳
  └─ Blocked:       0 steps 🔒

Velocity:
  ├─ Current pace:  0.5 steps/hour
  ├─ Baseline:      0.4 steps/hour (+25% ahead)
  └─ Trend:         ↗ Accelerating

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💚 HEALTH ANALYSIS

Health Score: 0.85/1.0 (GOOD) ✓
  ├─ Progress:      0.9 (Excellent pace)
  ├─ Error Rate:    0.8 (One minor error)
  ├─ Blockers:      1.0 (None)
  └─ Timeline:      0.8 (On track, slight variance)

On-Track Status: ✓ YES - On Schedule
  ├─ Expected at 30%: Oct 22
  ├─ Actual progress: Oct 22
  └─ Variance:       On target (0 days)

Errors Encountered: 1
  ├─ TypeScript type mismatch in auth.ts
  ├─ Severity:      MINOR
  ├─ Status:        RESOLVED ✓
  └─ Learning:      Added types to error handling

Blockers: None currently
  └─ Status: Clear to proceed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ TIMELINE

Start Date:         Oct 20
Target Completion:  Oct 27 (7 days)
Progress Time:      2 days (Oct 20-22)

Current Estimate:
  ├─ Time elapsed:   2 days
  ├─ Time remaining: 4.7 days (estimated)
  ├─ Projected end:  Oct 27 (on schedule)
  └─ Confidence:     85% (high confidence in timeline)

Variance Analysis:
  ├─ Baseline:       7 days (20 steps at 2.9/day)
  ├─ Actual (to 30%): 2 days (ahead of baseline pace)
  ├─ Variance:       -0.8 days (ahead, good momentum)
  └─ Trend:          ↗ Getting faster

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 MILESTONE STATUS

Milestones Reached:
  ✓ Auth service setup (Oct 22)
  ✓ JWT configuration started

Next Milestone: Integration testing
  ├─ Target:       Oct 25
  ├─ Current ETA:  Oct 24 (1 day early)
  └─ Confidence:   85%

Completed Milestones: 2 of 5
  └─ Overall progress: 40% to next major gate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ RISK ASSESSMENT

Current Risks:
  🟢 LOW (1 item) - OAuth integration complexity
    → Mitigation: Start early, spike risk on day 3
  🟡 MEDIUM (0 items) - None identified

Bottleneck Analysis:
  → No critical bottlenecks
  → Velocity is good and accelerating
  → Resource utilization: Healthy

Recommendations:
  1. ✓ Continue at current pace (ahead of schedule)
  2. → Prepare for OAuth integration (next step)
  3. → Consider spike investigation on security patterns
  4. → Document decisions for future auth work

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Notes:
  "Auth service setup complete - JWT configuration started"

Next Action: Run /progress again when next task completes
  → Target: Oct 23 (JWT config completion)
  → Use: /progress --goal-id 1 --completed 4 --total 10
```

## Integration with Phase 3 Executive Functions

**Progress Tracking**:
- Records raw progress metrics (completed/total, percent)
- Maintains task-level tracking
- Updates velocity measurements
- Tracks error and blocker counts

**Health Analysis**:
- Calculates composite health score
- Detects on-track vs. behind schedule
- Identifies bottlenecks
- Generates risk assessment

**Timeline Management**:
- Estimates completion based on velocity
- Calculates variance from baseline
- Predicts milestone completion
- Generates confidence intervals

**Milestone Tracking**:
- Records reached milestones
- Predicts next milestone timing
- Tracks milestone velocity
- Enables phase-based progress

## Related Commands

- `/activate-goal` - Set goal as active
- `/goal-complete` - Mark goal as complete
- `/priorities` - Check goal vs. priority
- `/project-status` - See all goals' progress
- `/goal-conflicts` - Check for blockers
- `/workflow-status` - View all active work

## Tips

1. **Update regularly**: Record progress daily or after milestones
2. **Note errors**: Document issues for learning
3. **Track blockers**: Help identify system-wide issues
4. **Use velocity**: Compare to baseline to detect changes
5. **Monitor health**: Watch health score for degradation
6. **Plan based on velocity**: Use actual pace for future estimates

## Phase 3 Integration

This command implements:
- Progress percentage tracking
- Health score calculation
- On-track status determination
- Milestone tracking
- Velocity measurement
- Risk assessment

## Related Tools

- `task_management_tools:record_execution_progress` - Core tracking
- `task_management_tools:update_milestone_progress` - Milestone updates
- `monitoring_tools:get_task_health` - Health calculation
- `monitoring_tools:detect_bottlenecks` - Blocker detection

## See Also

- `/activate-goal` - Start working on goal
- `/goal-complete` - Mark goal done
- `/project-status` - View all goals
- `/priorities` - Goal ranking
- `/stress-test-plan` - Timeline validation
