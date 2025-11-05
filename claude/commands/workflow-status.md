# workflow-status

Get comprehensive view of execution state of all active workflows.

## Usage

```bash
/workflow-status
/workflow-status --project-id 1
/workflow-status --detailed
/workflow-status --focus active
```

## Description

Displays dashboard of current workflow state including:
- Active goals and their progress
- Recent goal switches and costs
- Execution health metrics
- Resource utilization
- Blocking dependencies
- Timeline progress

Internally calls the `get_workflow_status` MCP tool from Phase 3 Executive Functions.

## Options

- `--project-id` (optional) - Project to view (default: current)
- `--detailed` (optional) - Show full metrics and analysis
- `--focus` (optional) - Filter: active, pending, blocked, completed
- `--timeline` (optional) - Show Gantt chart view
- `--risks` (optional) - Highlight risks and blockers

## Output

- Current workflow state
- Active goal ID and count
- Recent switches and costs
- Average switch cost
- Goal health metrics
- Timeline progress
- Resource utilization

## Example

```
> /workflow-status --detailed
📊 Workflow Status Dashboard

Project: Memory MCP (Project 1)
Timeline: Oct 20 - Nov 27 (38 days total)
Progress: 42% (16/38 days elapsed)

Current Workflow State: ACTIVE
├─ Status: ON TRACK
├─ Health: 0.82 (GOOD)
└─ Last Updated: 2 min ago

Active Goals: 2/5
────────────────────────
1. Goal #1: "Phase 3 integration" ⭐
   ├─ Progress: 85% (31/36 steps)
   ├─ Health: 0.88 (EXCELLENT)
   ├─ Deadline: Nov 2 (4 days)
   ├─ Status: ON TRACK ✓
   ├─ Estimated: Oct 31 (-2 days early) ⚡
   └─ Current Task: Create commands (Phase 2 of 5)

2. Goal #5: "Documentation"
   ├─ Progress: 10% (2/20 steps)
   ├─ Health: 0.71 (FAIR)
   ├─ Deadline: Nov 15 (17 days)
   ├─ Status: ON TRACK ✓
   └─ Current: Blocked - waiting for Phase 3 complete

Pending Goals: 3/5
────────────────────────
- Goal #2: "Testing" (starts Oct 28)
- Goal #3: "Optimization" (starts Nov 5)
- Goal #4: "Deployment" (starts Nov 15)

Recent Goal Switches: 3
────────────────────────
Switch #1: Goal #3 → Goal #1 (Oct 28, 10:30)
  ├─ Context Loss: 15 min
  ├─ Resume Time: 5 min
  └─ Reason: P0 issue required attention

Switch #2: Goal #1 → Goal #3 (Oct 29, 14:45)
  ├─ Context Loss: 10 min
  ├─ Resume Time: 3 min
  └─ Reason: Documentation needed for deployment

Switch #3: Goal #3 → Goal #1 (Oct 29, 16:20)
  ├─ Context Loss: 8 min
  └─ Reason: Back to primary focus

Average Switch Cost: 11 min (Moderate)

Resource Utilization
────────────────────────
Person: Alice
  ├─ Allocated: 40 hrs/week
  ├─ Current Goals: Goal #1, Goal #5
  └─ Utilization: 65% (26/40 hrs)

Person: Bob
  ├─ Allocated: 40 hrs/week
  ├─ Current Goals: Goal #2 (prep)
  └─ Utilization: 20% (8/40 hrs)

Risks & Blockers
────────────────────────
🟡 MEDIUM: Goal #2 depends on Goal #1 (unblock Oct 31)
🟡 MEDIUM: Goal #5 documentation backlog (may impact Nov 15)
🟢 LOW: Alice context switching every 2-3 hours (manageable)

Timeline Progress
────────────────────────
Planned:  |████████░░░░░░░░░░░░░| (42% planned)
Actual:   |████████░░░░░░░░░░░░░| (42% actual)
Status:   ✓ ON SCHEDULE

Metrics Summary
────────────────────────
Total Goals: 5
Active: 2 | Pending: 3 | On-Track: 4 | At-Risk: 1
Avg Health: 0.78 (GOOD)
Critical Path: 38 days
Slack: 0 days (tight timeline)
```

## Related Commands

- `/activate-goal` - Switch to a different goal
- `/priorities` - See goal priorities
- `/progress` - Update progress for current goal
- `/goal-conflicts` - Check for conflicts

## See Also

- Memory MCP Phase 3: Executive Functions
