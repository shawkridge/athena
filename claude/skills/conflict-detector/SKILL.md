# conflict-detector

Auto-triggered skill to find and report resource/dependency conflicts between goals.

## Purpose

Automatically detects conflicts between active goals including:
- Resource contention (person/tool needed by multiple)
- Dependency cycles (circular dependencies)
- Timing conflicts (overlapping deadlines)
- Capacity overload (too much work)
- Priority conflicts (high-priority goals blocking each other)

## When Auto-Triggered

Automatically activates when:
- New goal activated
- Goal deadline changes
- Resource availability changes
- Goal state changes
- Goal conflict check requested
- Scheduled periodic check (daily)

## Capabilities

### Conflict Detection
- Analyzes all active goals
- Identifies all conflict types
- Calculates severity scores (0-10)
- Ranks by impact
- Groups related conflicts

### Conflict Types

1. **RESOURCE_CONTENTION** - Same resource needed
   - Same person allocated to 2+ goals
   - Same tool/environment needed
   - Severity: Based on overlap hours
   - Example: Alice needed for both Goal #1 (40 hrs) and Goal #3 (40 hrs)

2. **DEPENDENCY_CYCLE** - Circular dependencies
   - Goal A depends on B, B depends on A
   - Severity: Critical (9-10)
   - Example: Goal #4 → Goal #5 → Goal #4

3. **TIMING_CONFLICT** - Overlapping deadlines
   - Both need to be done same day
   - Limited capacity
   - Severity: Based on duration overlap
   - Example: Goal #2 (due Oct 27) + Goal #4 (due Oct 27)

4. **CAPACITY_OVERLOAD** - Too much work
   - Team capacity >100%
   - Timeline impossible
   - Severity: Based on utilization
   - Example: 80 hours work in 40-hour week

5. **PRIORITY_CONFLICT** - High-priority goals block each other
   - Both are critical
   - Both depend on same resource
   - Severity: 7-8 (decision required)

### Conflict Classification
- Groups conflicts by type
- Calculates combined impact
- Identifies "conflict clusters"
- Prioritizes by severity

## Auto-Triggers

```yaml
conflict_detector:
  # Trigger on goal activation
  on_goal_activated:
    enabled: true
    action: check_new_conflicts

  # Trigger on deadline change
  on_deadline_changed:
    enabled: true
    action: recheck_timing_conflicts

  # Trigger on resource change
  on_resource_availability_changed:
    enabled: true
    action: recheck_resource_conflicts

  # Trigger on periodic check
  on_daily_check:
    enabled: true
    time: "09:00"  # Every day at 9 AM
    action: full_conflict_analysis

  # Trigger on conflict escalation
  on_severity_threshold:
    enabled: true
    condition: "max_severity >= 8"  # Critical conflicts
    action: escalate_to_conflict_resolver
```

## Output

When activated, conflict-detector produces:

### Conflict Report
- Total conflicts found
- Breakdown by type
- Severity scores
- Affected goals
- Timeline impact estimate
- Cost/resource impact

### Conflict Descriptions
- What's conflicting (which goals)
- Why it matters (impact)
- When it occurs (timeline)
- Who's affected (team members)

### Recommendations
- Priority for resolution
- Suggested fixes (from conflict-resolver)
- Timeline impact of each option
- Risk assessment

## Example Output

```
[conflict-detector] Daily Conflict Check

🔍 Conflict Analysis
────────────────────
Total Conflicts: 3
Critical (8-10): 1
High (6-7): 1
Medium (4-5): 1
Low (0-3): 0

Conflicts Found:
════════════════════════════════════════

Conflict #1: RESOURCE_CONTENTION [CRITICAL 8.2/10]
─────────────────────────────────────────────────
Goals: #1 (Auth) + #3 (API)
Resource: Alice (person)
Overlap: 16 hours (Mon-Wed both need 40 hrs)

Timeline:
  Goal #1: Mon 9am - Thu 9am (40 hrs)
  Goal #3: Wed 9am - Fri 9am (40 hrs)
  Overlap: Wed 9am - Thu 9am

Impact: Both miss deadlines if concurrent
Recommendation: Move Goal #3 to following week
  → Cost: 7-day delay for Goal #3
  → Benefit: No conflicts, both succeed

Conflict #2: TIMING_CONFLICT [HIGH 6.3/10]
─────────────────────────────────────────
Goals: #2 (Testing) + #4 (Docs)
Issue: Both due same day, 50 hrs work
Capacity: 40 hours available
Overload: 25% over capacity

Impact: One will miss deadline
Recommendation: Move Docs to next week
  → Cost: 7-day delay for Goal #4
  → Benefit: Testing completes, no burnout

Conflict #3: PRIORITY_CONFLICT [MEDIUM 5.1/10]
──────────────────────────────────────────────
Goals: #1 (Auth - HIGH) + #2 (Testing - HIGH)
Both critical path items
Both need alice (40 hrs each)

Impact: Hard to choose priority
Recommendation: Sequential (Auth first)
  → Auth unblocks other work
  → Testing can run on Goal #2 timeline

Summary:
════════
✓ Conflicts detected: 3
✓ Critical issues: 1 (requires action)
✓ Timeline impact: +7 days if all resolved
✓ Recommendation: Activate conflict-resolver

Run: /resolve-conflicts to auto-fix
```

## Integration with Other Components

**With conflict-resolver (agent)**:
- Detector identifies conflicts
- Agent resolves them

**With goal-orchestrator**:
- Receives goal state changes
- Triggers on new goals

**With goal-state-tracker**:
- Reports blockers as conflicts
- Escalates if health drops due to conflicts

**With priority-calculator**:
- Uses priority scores for ranking

## MCP Tools Used

- `check_goal_conflicts()` - Get conflicts
- `get_workflow_status()` - Get goal state
- `get_goal_priority_ranking()` - Get priorities

## Configuration

```yaml
conflict_detector:
  enabled: true
  severity_threshold: 4          # Alert on MEDIUM+ (>= 4)
  check_frequency: daily         # Daily check
  critical_escalation: true      # Auto-escalate critical
  group_related: true            # Group conflict clusters
  impact_estimation: true        # Show timeline impact
  learning_enabled: true         # Learn conflict patterns
```

## Related Skills

- **conflict-resolver** (agent for resolution)
- **priority-calculator** - Used for conflict ranking
- **goal-state-tracker** - Detects blocker-type conflicts
- **workflow-monitor** - Monitors all conflicts

## See Also

- Phase 3 Executive Functions: Conflict Management
- `/goal-conflicts` command
- conflict-resolver agent
