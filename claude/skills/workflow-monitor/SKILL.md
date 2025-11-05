# workflow-monitor

Auto-triggered skill to track execution state and health of all active workflows.

## Purpose

Continuously monitors workflow execution state including:
- Active goals and their progress
- Recent goal switches and costs
- Resource utilization
- Timeline progress vs plan
- Blocking dependencies
- Risk indicators

## When Auto-Triggered

Automatically activates when:
- User requests `/workflow-status` command
- Session starts (load workflow state)
- Session ends (save workflow state)
- Goal state changes significantly
- Daily review (workflow health snapshot)
- Periodic check (every 30 min during work)

## Capabilities

### Workflow State Tracking
- Current workflow state (IDLE, ACTIVE, PAUSED, BLOCKED)
- Active goal ID
- Count of active goals
- Recent switches and costs
- Average switch cost

### Progress Monitoring
- Timeline progress (% of time elapsed vs % complete)
- Goal progress tracking
- Milestone detection
- Deadline countdown
- Slack time calculation

### Health Metrics
- Overall workflow health (0-1 scale)
- Individual goal health scores
- Resource utilization
- Team morale indicators
- Risk score

### Resource Tracking
- Person allocation tracking
- Tool/environment usage
- Concurrent work management
- Bottleneck detection
- Capacity analysis

## Auto-Triggers

```yaml
workflow_monitor:
  # Trigger on goal activation
  on_goal_activated:
    enabled: true
    action: start_tracking

  # Trigger on progress update
  on_progress_recorded:
    enabled: true
    action: update_timeline

  # Trigger on periodic check
  on_periodic_check:
    enabled: true
    interval: 30_minutes
    action: refresh_workflow_state

  # Trigger on session end
  on_session_end:
    enabled: true
    action: save_workflow_snapshot

  # Trigger on risk detection
  on_risk_detected:
    enabled: true
    condition: "health < 0.6 OR behind_schedule"
    action: escalate_alert
```

## Output

When activated, workflow-monitor produces:

### Workflow Dashboard
- Current state visualization
- Active goals list
- Progress bars
- Timeline view
- Resource allocation
- Risk indicators

### Metrics Summary
- Total goals (active/pending/blocked/completed)
- Average health score
- Timeline accuracy
- Resource utilization
- Critical path status

### Alerts & Warnings
- Goals at risk
- Approaching deadlines
- Resource conflicts
- Bottleneck warnings
- Slipped timelines

## Example Output

```
[workflow-monitor] Workflow Status Dashboard

📊 Workflow State: ACTIVE
═════════════════════════════════════════

Timeline: Oct 20 - Nov 27 (38 days total)
Progress: 42% (16/38 days elapsed)
Health: 0.82 (GOOD) — Status: ON TRACK ✓

Current Goals: 2/5
─────────────────────
1. ⭐ Goal #1: "Phase 3 integration"
   ├─ Progress: 85% (31/36 steps)
   ├─ Health: 0.88 (EXCELLENT)
   ├─ Deadline: Nov 2 (4 days)
   ├─ Est. Completion: Oct 31 ⚡ (-2 days early)
   └─ Status: ON TRACK ✓

2. Goal #5: "Documentation"
   ├─ Progress: 10% (2/20 steps)
   ├─ Health: 0.71 (FAIR)
   ├─ Deadline: Nov 15 (17 days)
   ├─ Est. Completion: Nov 12 ✓
   └─ Status: ON TRACK (blocked by Goal #1)

Pending Goals: 3/5
─────────────────────
→ Goal #2: "Testing" (starts Oct 28)
→ Goal #3: "Optimization" (starts Nov 5)
→ Goal #4: "Deployment" (starts Nov 15)

Resource Utilization
─────────────────────
Alice: 65% (26/40 hrs) — Healthy
Bob: 20% (8/40 hrs) — Underutilized
Room for more work: 15 hrs/week

Recent Goal Switches: 3
─────────────────────
#1: Goal #3→#1 (Oct 28, 10:30) — Cost: 15 min
#2: Goal #1→#3 (Oct 29, 14:45) — Cost: 10 min
#3: Goal #3→#1 (Oct 29, 16:20) — Cost: 8 min
Avg Cost: 11 min (Moderate)

Timeline Progress
─────────────────────
Planned:  |████████░░░░░░░░░░░░░| 42%
Actual:   |████████░░░░░░░░░░░░░| 42%
Status:   ✓ ON SCHEDULE

Critical Path: 38 days
Slack: 0 days (tight timeline ⚠️)

🚨 Alerts & Risks
─────────────────────
🟡 MEDIUM: Goal #2 depends on Goal #1
   → Goal #1 on track (unblock Oct 31)

🟡 MEDIUM: Goal #5 backlog (documentation)
   → May impact Nov 15 deadline
   → Consider more capacity

🟢 LOW: Context switching every 2-3 hours
   → Moderate, manageable pace

Health Score: 0.82/1.0 (GOOD)
├─ Timeline accuracy: 0.9 (excellent)
├─ Resource balance: 0.8 (good)
├─ Goal completion: 0.75 (solid)
└─ Risk factors: 0.7 (moderate risk)

Next Actions:
1. Continue Goal #1 (on track to complete Oct 31)
2. Prepare Goal #2 (testing) for Oct 28 start
3. Monitor Goal #5 for capacity issues
4. Consider risk mitigation for tight slack

Command: /next-goal (get AI recommendation)
```

## Integration with Other Components

**With goal-orchestrator**:
- Receives goal state changes
- Tracks lifecycle events
- Updates on activation/completion

**With goal-state-tracker**:
- Gets progress updates
- Monitors health scores
- Detects milestone achievements

**With priority-calculator**:
- Uses priority rankings in display
- Shows urgent goals prominently

**With conflict-detector**:
- Reports conflicts detected
- Shows blocker status

**With learning-monitor**:
- Records workflow metrics
- Feeds data for optimization
- Learns timeline patterns

## MCP Tools Used

- `get_workflow_status()` - Get all workflow state
- `get_goal_priority_ranking()` - Get goal rankings
- `get_task_health()` - Get task-level health (Phase 5 integration)

## Configuration

```yaml
workflow_monitor:
  enabled: true
  dashboard_refresh: auto           # Update on events
  periodic_check_interval: 30       # minutes
  timeline_visualization: gantt     # gantt or timeline
  show_critical_path: true          # Highlight critical path
  alert_on_risk: true               # Alert if health < 0.6
  capacity_warning_threshold: 0.85  # Alert at 85%
  learning_enabled: true            # Learn timeline patterns

  metrics_tracked:
    - timeline_accuracy
    - resource_utilization
    - goal_health
    - context_switching_cost
    - critical_path_status
    - dependency_graph
```

## Related Skills

- **goal-state-tracker** - Provides goal-level metrics
- **priority-calculator** - Provides goal rankings
- **conflict-detector** - Reports blocking conflicts
- **goal-state-tracker** - Detects milestones

## See Also

- Phase 3 Executive Functions: Workflow Monitoring
- `/workflow-status` command
- `/project-status` command (macro view)
