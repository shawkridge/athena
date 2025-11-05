# goal-state-tracker

Auto-triggered skill to monitor goal progress, detect blockers, and evaluate milestone status.

## Purpose

Continuously monitors the state of active goals and automatically:
- Tracks progress toward completion
- Detects blockers and issues
- Identifies milestone achievements
- Warns of deadline risks
- Updates goal health scores

## When Auto-Triggered

Automatically activates when:
- Progress recorded via `/progress` command
- Task completed and `post-task-completion` hook fires
- Session ends (goal state snapshot)
- Deadline approaches (warning phase)
- Health score drops below threshold

## Capabilities

### Progress Tracking
- Monitors step completion
- Calculates progress percentage
- Detects acceleration/deceleration
- Estimates completion time
- Projects deadline accuracy

### Blocker Detection
- Identifies blocking issues
- Categorizes blocker type (resource, dependency, technical)
- Assesses blocker severity
- Suggests mitigation strategies
- Escalates critical blockers

### Milestone Evaluation
- Detects when milestones achieved (25%, 50%, 75%, 100%)
- Records milestone timestamps
- Updates goal state
- Sends notifications
- Feeds data to learning-monitor

### Health Scoring
- Calculates goal health: 0 (failed) to 1 (excellent)
- Factors: progress rate, error count, blocker count
- Detects health degradation
- Triggers interventions if needed

## Auto-Triggers

```yaml
goal_state_tracker:
  # Trigger on progress updates
  on_progress_recorded:
    enabled: true
    condition: "completed % > 10"  # Every 10% increment
    action: evaluate_milestone

  # Trigger on blockers detected
  on_blocker_detected:
    enabled: true
    condition: "blockers > 0"
    action: assess_impact

  # Trigger on deadline approach
  on_deadline_approaching:
    enabled: true
    condition: "days_until_deadline < 3"
    action: warn_and_reschedule

  # Trigger on health degradation
  on_health_degradation:
    enabled: true
    condition: "health_score < 0.6"
    action: trigger_conflict_resolver

  # Trigger on session end
  on_session_end:
    enabled: true
    action: snapshot_goal_state
```

## Output

When activated, goal-state-tracker produces:

### Progress Report
- Current progress percentage
- Steps completed/remaining
- Velocity (steps/day)
- Estimated completion time
- Timeline accuracy (on-track, at-risk, behind)

### Blocker Report
- Blocker count and descriptions
- Severity assessment
- Impact on timeline
- Suggested mitigations

### Milestone Notifications
- Achievement announcements
- Milestone-specific actions
- Next milestone info
- Motivational feedback

### Health Score Update
- Current health (0-1 scale)
- Contributing factors
- Trend (improving, stable, degrading)
- Recommended actions

## Example Output

```
[goal-state-tracker] Goal #1: "Implement user auth"

📊 Progress Report
─────────────────
Current: 30% (3/10 steps)
Velocity: 1.5 steps/day
Est. Completion: Oct 26 (in 2 days)
Timeline: ON TRACK ✓ (scheduled Oct 27)

🚧 Blockers
─────────────
Count: 1
- TypeScript types error (Low severity)
  Impact: 2 hours delay
  Action: Review type definitions, or suppress

📈 Health Score
─────────────
Current: 0.82 (GOOD)
Trend: STABLE →
Factors:
  - Progress: 30% (on pace)
  - Errors: 1 (acceptable)
  - Blockers: 1 low-severity

💡 Recommendation: Continue at current pace, watch for more blockers
```

## Integration with Other Components

**With goal-orchestrator**:
- Feeds goal state updates
- Triggers state transitions (ACTIVE → IN_PROGRESS)
- Reports completion status

**With conflict-resolver**:
- Reports blockers that may be conflicts
- Triggers conflict detection if health drops

**With strategy-orchestrator**:
- Reports strategy effectiveness
- Feeds data for strategy adjustment

**With learning-monitor**:
- Records execution metrics
- Contributes to learning models

## MCP Tools Used

- `record_execution_progress()` - Record progress
- `get_workflow_status()` - Get goal state
- `complete_goal()` - Mark complete when done

## Configuration

```yaml
goal_state_tracker:
  enabled: true
  update_frequency: auto        # Update on events, not polling
  health_threshold_warning: 0.6 # Warn if health < 0.6
  milestone_notifications: true # Announce milestones
  blocker_escalation: true      # Auto-escalate critical blockers
  estimated_completion_method: linear  # linear or trend
```

## Related Skills

- **priority-calculator** - Ranks goals by urgency
- **workflow-monitor** - Monitors all goals
- **conflict-detector** - Detects goal conflicts
- **strategy-selector** - Adjusts strategy based on progress

## See Also

- Phase 3 Executive Functions: Goal Lifecycle
- `/progress` command
- `post-task-completion` hook
