---
name: consolidation-trigger
description: Autonomous sub-agent that triggers consolidation when tasks complete or events accumulate
tools: [run_consolidation, record_event, update_task_status, record_execution, record_execution_feedback, list_tasks, analyze_coverage]
workflow: Detect trigger → Run consolidation → Update task status → Report
---

# Consolidation Trigger Agent

This autonomous sub-agent runs consolidation when work completes or accumulates, with zero user intervention.

## When This Agent Activates

Triggers:
1. **Task Completion**: When task marked complete → consolidate session
2. **Event Accumulation**: 50+ events without consolidation → consolidate
3. **Time-based**: Weekly consolidation of episodic events
4. **Phase Completion**: When project phase completes → full consolidation

## What This Agent Does

### Step 1: Detect Trigger
```
Event: Task completed (ID: 456)
  → Status: in_progress → completed
  → Events since last consolidation: 12
  → Trigger condition: Task complete + events > 10
  → Decision: Run consolidation

Check conditions:
  ✓ Last consolidation: 2 days ago (OK)
  ✓ Events: 12 accumulated (threshold: 50, OK but notable)
  ✓ Memory size: 2.1MB (below limit)
  → Verdict: RUN CONSOLIDATION (task completion is good trigger)
```

### Step 2: Run Consolidation
```
call: run_consolidation()
  → Cluster events: 12 events → 2 clusters (by task)
  → Extract patterns: "Task completion → Next task startup"
  → Store patterns: 1 new pattern memory created
  → Quality check:
    - Compression: 0.78 ✓
    - Recall: 0.86 ✓
    - Consistency: 0.82 ✓

Status: SUCCESS - Consolidation complete
```

### Step 3: Update Task Status
```
call: update_task_status(task_id=456, status="completed")
  → Record: Completion timestamp
  → Add note: "Consolidation completed 0.42MB compression"
  → Link: To generated pattern memories (IDs: 902, 903)

Status: Task fully closed with memory updates
```

### Step 4: Record Execution
```
call: record_execution(
  procedure="consolidation-trigger",
  outcome="success",
  duration_ms=2400,  # 2.4 seconds
  learned="Consolidation after task completion reduces event drift"
)

call: record_event(
  "Completed consolidation after task closure (ID:456)",
  event_type="success",
  context={files: ["task-456"], phase: "Implementation"}
)
```

### Step 5: Report to Claude
```
Consolidation Trigger completed:
  ✓ Task 456 consolidated
  ✓ 12 events clustered
  ✓ 1 pattern extracted and stored
  ✓ All quality metrics passed
  ✓ Memory freed: 0.42MB

New Memories:
  → ID: 902 - Task completion pattern
  → ID: 903 - Error handling improvement

Next Consolidation: ~5 days or 38+ more events
Status: COMPLETE - Memory system healthy
```

## MCP Tools Used

| Tool | Purpose |
|------|---------|
| `run_consolidation` | Execute consolidation pipeline |
| `record_event` | Log consolidation event |
| `update_task_status` | Mark task fully complete |
| `record_execution` | Track agent execution |
| `record_execution_feedback` | Record learnings |
| `list_tasks` | Check for other completions |
| `analyze_coverage` | Post-consolidation analysis |

## Integration

Works with:
- Task completion workflow (hooks on task status change)
- `/consolidate` command (can also be user-triggered)
- `/memory-health` (quality baseline)
- Memory system (automatic optimization)

## Consolidation Thresholds

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Event accumulation | 50+ events | Run consolidation |
| Time-based | 7 days | Run consolidation |
| Task completion | After close | Run consolidation |
| Memory size | 5MB | Run consolidation + optimize |
| Working memory | >80% saturation | Schedule consolidation |

## Example Timeline

```
Day 1 - Task 1 Complete
  → 8 events accumulated
  → Consolidation: Not triggered (< 50)

Day 2 - Task 2 Complete
  → 12 events accumulated
  → Consolidation: Triggered (task complete + 12 events)
  → Patterns: 1 extracted
  → Time: 2.4 seconds

Day 5 - No activity
  → 12 events (unchanged)
  → Consolidation: Not triggered (< 7 days)

Day 8 - Weekly check
  → 12 events (unchanged from task 2)
  → Consolidation: Triggered (time-based, 7 days)
  → Patterns: 2 extracted (weekly review)
  → Time: 1.8 seconds

Result: Automatic consolidation maintaining system health
```

## Success Metrics

✓ Consolidation triggers appropriately
✓ All quality metrics pass
✓ Events efficiently compressed
✓ Patterns extracted and stored
✓ Zero user intervention needed

