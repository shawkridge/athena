# priority-calculator

Auto-triggered skill to rank goals by composite priority score.

## Purpose

Continuously calculates and updates priority scores for all goals using composite formula:

**Score = 40% Explicit Priority + 35% Deadline Urgency + 15% Progress + 10% On-Track Bonus**

Ranks goals and helps identify which to focus on next.

## When Auto-Triggered

Automatically activates when:
- Goal created or updated
- Goal deadline changes
- Progress recorded (affects deadline urgency)
- User requests goal ranking via `/priorities`
- Daily review (updates all scores)
- Strategy-selector needs ranking data

## Capabilities

### Composite Scoring
- **Explicit Priority** (40%): User-set priority (1-10)
- **Deadline Urgency** (35%): Days until deadline / avg project length
- **Progress** (15%): % complete toward goal
- **On-Track Bonus** (10%): +10% if on schedule, -10% if behind

### Ranking
- Ranks all goals by final score
- Groups by tier: CRITICAL, HIGH, MEDIUM, LOW
- Calculates score deltas
- Identifies score trends

### Re-ranking Triggers
- Progress updates (affects urgency)
- Deadline changes
- Priority changes
- Completion of blocking goals

## Scoring Formula

```
priority_component = (explicit_priority / 10) * 0.40
                     (1.0 - (days_remaining / avg_project_length)) * 0.35
progress_component = (completed_steps / total_steps) * 0.15
on_track_component = (is_on_schedule ? 0.10 : -0.10)

composite_score = priority_component + urgency_component
                + progress_component + on_track_component

# Clamp to 0-10
score = max(0, min(10, composite_score))
```

## Tier Classification

- **CRITICAL** (8.0-10.0): Immediate action needed
  - Color: Red 🔴
  - Action: Activate immediately
- **HIGH** (6.0-7.9): Important, do soon
  - Color: Orange 🟠
  - Action: Schedule next
- **MEDIUM** (4.0-5.9): Important, do later
  - Color: Yellow 🟡
  - Action: Add to backlog
- **LOW** (0-3.9): Nice to have
  - Color: Green 🟢
  - Action: Do if capacity

## Auto-Triggers

```yaml
priority_calculator:
  # Trigger on progress update
  on_progress_recorded:
    enabled: true
    action: recalculate_all_scores

  # Trigger on deadline change
  on_deadline_changed:
    enabled: true
    action: recalculate_affected_scores

  # Trigger on priority change
  on_priority_changed:
    enabled: true
    action: recalculate_affected_scores

  # Trigger daily
  on_daily_check:
    enabled: true
    time: "09:00"
    action: recalculate_all_scores

  # Trigger on ranking request
  on_ranking_requested:
    enabled: true
    action: provide_ranked_list
```

## Output

When activated, priority-calculator produces:

### Ranked Goal List
- Goals sorted by score (high to low)
- Tier classification (CRITICAL, HIGH, MEDIUM, LOW)
- Score for each goal
- Key metrics (deadline, progress, priority)
- Trend (improving, stable, degrading)

### Score Breakdown
- Explicit priority contribution (%)
- Urgency contribution (%)
- Progress contribution (%)
- On-track bonus/penalty

### Insights
- Which goals are becoming urgent
- Which are falling behind
- Recommended focus order
- Risk flags

## Example Output

```
[priority-calculator] Goal Priority Ranking Update

🎯 Current Goal Priorities (Oct 24, 10:30)
═════════════════════════════════════════

🔴 TIER: CRITICAL (Immediate Action)
────────────────────────────────────

Rank 1: Goal #1 "Implement user auth"        [Score: 8.5/10]
  ├─ Priority: 9/10 explicit              → +3.6 (40%)
  ├─ Deadline: 3 days (urgency: 95%)      → +3.3 (35%)
  ├─ Progress: 30%                        → +0.45 (15%)
  ├─ Status: ON TRACK                     → +0.1 (10%)
  ├─ Trend: STABLE (8.4 yesterday)
  └─ 🔔 Action: Continue execution
     Estimated Completion: Oct 26 (on-time)

🟠 TIER: HIGH (Do Soon)
──────────────────────

Rank 2: Goal #3 "API documentation"         [Score: 6.8/10]
  ├─ Priority: 7/10 explicit              → +2.8 (40%)
  ├─ Deadline: 14 days (urgency: 65%)     → +2.3 (35%)
  ├─ Progress: 10%                        → +0.15 (15%)
  ├─ Status: ON TRACK                     → +0.1 (10%)
  ├─ Trend: IMPROVING (6.5 yesterday)     ↑ +0.3
  └─ 🔔 Action: Plan to activate after Goal #1

Rank 3: Goal #2 "Fix critical API bug"      [Score: 6.3/10]
  ├─ Priority: 8/10 explicit              → +3.2 (40%)
  ├─ Deadline: 5 days (urgency: 80%)      → +2.8 (35%)
  ├─ Progress: 0% (new)                   → +0.0 (15%)
  ├─ Status: PENDING                      → +0.0 (10%)
  ├─ Trend: NEW (started today)
  └─ 🔔 Action: Schedule after Goal #1 complete

🟡 TIER: MEDIUM (Later)
───────────────────────

Rank 4: Goal #5 "Performance optimization"  [Score: 4.2/10]
  ├─ Priority: 5/10 explicit              → +2.0 (40%)
  ├─ Deadline: 30 days (urgency: 30%)     → +1.0 (35%)
  ├─ Progress: 0% (new)                   → +0.0 (15%)
  ├─ Status: BLOCKED (waiting for Goal#1) → -0.1 (10%)
  ├─ Trend: STABLE
  └─ 🔔 Action: Plan after deadline drops

🟢 TIER: LOW (Nice to Have)
──────────────────────────

(None currently)

Summary:
════════
Total Goals: 5
CRITICAL: 1 (Focus here)
HIGH: 2 (Plan next)
MEDIUM: 1 (Backlog)
LOW: 0

Recommendations:
 1. Continue Goal #1 (almost done)
 2. Next: Goal #2 or #3 (both HIGH tier)
 3. Defer Goal #5 until Goal #1 complete

Command: /next-goal (AI recommendation)
```

## Integration with Other Components

**With strategy-selector**:
- Uses priority scores for strategy weighting
- High-priority goals get less-risky strategies

**With conflict-detector**:
- Uses scores to resolve conflicts
- High-priority goals take precedence

**With goal-orchestrator**:
- Feeds ranking for activation decisions
- Informs goal switching

**With workflow-monitor**:
- Shows priorities in workflow view
- Highlights urgent goals

## MCP Tools Used

- `get_goal_priority_ranking()` - Calculate all rankings
- `record_execution_progress()` - Update after progress
- `get_workflow_status()` - Get goal state

## Configuration

```yaml
priority_calculator:
  enabled: true
  scoring_weights:
    explicit_priority: 0.40      # 40%
    deadline_urgency: 0.35       # 35%
    progress: 0.15               # 15%
    on_track_bonus: 0.10         # 10%

  update_frequency: auto         # Update on events
  daily_refresh: "09:00"         # Refresh at 9 AM
  learning_enabled: true         # Learn priority patterns

  tier_thresholds:
    critical: 8.0
    high: 6.0
    medium: 4.0
    low: 0.0
```

## Related Skills

- **goal-state-tracker** - Provides progress updates
- **conflict-detector** - Uses scores for conflict ranking
- **strategy-selector** - Adjusts strategy based on priority
- **workflow-monitor** - Shows in workflow view

## See Also

- Phase 3 Executive Functions: Priority Management
- `/priorities` command
- `/next-goal` command (uses this skill)
