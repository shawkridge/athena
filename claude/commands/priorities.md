# /priorities

Rank goals by composite priority score with detailed factor analysis.

## Usage

```bash
/priorities                              # Show all goals ranked
/priorities --project-id 1               # Specific project
/priorities --show-scores                # Detailed score breakdown
/priorities --sort deadline              # Sort by deadline
/priorities --filter active              # Only active goals
/priorities --watch                      # Monitor priority changes
```

## Description

Calculates and displays goals ranked by composite priority score combining multiple factors.

**Composite Priority Score Formula**:
```
Score = (Priority × 0.40) + (Deadline × 0.35) +
         (Progress × 0.15) + (OnTrack × 0.10)

Where:
  • Priority: Explicit goal importance (1-10 scale)
  • Deadline: Urgency based on days remaining
  • Progress: Percentage complete (0-100%)
  • OnTrack: Bonus/penalty for schedule adherence
    - +10% if ahead of schedule
    - 0% if on schedule
    - -10% if behind schedule
```

**Internally calls**:
- `task_management_tools:get_goal_priority_ranking` - Composite scoring
- `task_management_tools:get_active_goals` - Load all goals
- `monitoring_tools:analyze_critical_path` - Deadline analysis

## Options

- `--project-id` (optional) - Project to rank (default: 1)
- `--show-scores` (optional) - Show detailed factor breakdown
- `--sort` (optional) - Sort by: score (default), deadline, priority, progress, status
- `--filter` (optional) - Filter: active, pending, blocked, completed, all
- `--watch` (optional) - Show historical priority changes
- `--by-urgency` (optional) - Focus on deadline-based urgency

## Output

Ranked list showing:
- Rank and goal name
- Composite score (0-10)
- Priority tier (CRITICAL, HIGH, MEDIUM, LOW)
- Score factor breakdown:
  - Priority component
  - Deadline component
  - Progress component
  - On-track status
- Deadline countdown
- Current progress
- On-track indicator
- Next action recommendation

## Example Output

```
> /priorities --show-scores

🎯 Goal Priority Ranking (Project 1)
Generated: 2025-11-05T14:40:00Z

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank 1️⃣ Goal #1 "Implement user authentication"  [CRITICAL] 8.5/10
  Priority:          9/10 (critical)               [36% of score]
  Deadline Urgency:  3 days until due             [35% of score]
  Progress:          25% complete (5/20 tasks)    [15% of score]
  On-Track Status:   ON TRACK ✓                   [10% of score]
  ─────────────────────────────────────────────────
  Composite Score:   8.5/10 (CRITICAL)

  ⏰ Due: 2025-10-27 (3 days remaining)
  📊 Status: 25% done, 75% remaining
  👥 Owner: Alice
  🔴 Status: CRITICAL - Start immediately!

  Recommendations:
    • Activate this goal NOW (/activate-goal --goal-id 1)
    • Allocate 20 hours this week
    • Check /goal-conflicts before starting
    • Use /stress-test-plan for timeline verification

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank 2️⃣ Goal #3 "API documentation"                [HIGH] 6.8/10
  Priority:          7/10 (high)                   [28% of score]
  Deadline Urgency:  14 days until due            [21% of score]
  Progress:          10% complete (1/10 tasks)    [15% of score]
  On-Track Status:   BEHIND SCHEDULE ⚠️           [0% penalty]
  ─────────────────────────────────────────────────
  Composite Score:   6.8/10 (HIGH)

  ⏰ Due: 2025-11-07 (14 days remaining)
  📊 Status: 10% done, 90% remaining
  👥 Owner: Bob
  🟡 Status: HIGH - Schedule review needed

  Recommendations:
    • Review progress - behind schedule
    • Check /goal-conflicts for blockers
    • Consider parallel task execution
    • Plan for acceleration or scope reduction

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank 3️⃣ Goal #5 "Performance optimization"         [MEDIUM] 4.2/10
  Priority:          5/10 (medium)                 [20% of score]
  Deadline Urgency:  30 days until due            [10% of score]
  Progress:          0% complete (0/15 tasks)     [0% of score]
  On-Track Status:   BLOCKED 🔒                   [0% penalty]
  ─────────────────────────────────────────────────
  Composite Score:   4.2/10 (MEDIUM)

  ⏰ Due: 2025-11-23 (30 days remaining)
  📊 Status: Not started, 15 tasks to do
  👥 Owner: Charlie
  🟢 Status: MEDIUM - Low urgency but review blockers

  Recommendations:
    • Resolve blocker with /resolve-conflicts
    • Activate after Goal #1 complete
    • Schedule for 2 weeks out
    • Use /decompose-with-strategy for planning

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
  • Total goals: 3 (active: 2, blocked: 1)
  • Highest urgency: Goal #1 (CRITICAL, 8.5/10)
  • Lowest urgency: Goal #5 (MEDIUM, 4.2/10)
  • Average progress: 11.7%
  • Critical path: Goal #1 → Goal #3 → Goal #5
  • Recommended next: Activate Goal #1 immediately
```

## Integration with Phase 3 Executive Functions

**Composite Scoring**:
- Balances explicit priority with deadline urgency
- Rewards progress and on-track execution
- Identifies critical path items
- Helps distribute attention

**Priority Tiers**:
- 🔴 CRITICAL (8.0-10.0): Start immediately
- 🟡 HIGH (6.0-7.9): This week
- 🟢 MEDIUM (4.0-5.9): Next 2 weeks
- 🔵 LOW (0-3.9): Lower priority, can defer

**Factor Analysis**:
- Priority weighting (40%): Business importance
- Deadline weighting (35%): Time sensitivity
- Progress weighting (15%): Momentum/morale
- On-track weighting (10%): Execution health

## Related Commands

- `/activate-goal` - Switch to high-priority goal
- `/progress` - Update progress for current goal
- `/resolve-conflicts` - Fix blockers
- `/project-status` - View all goals with details
- `/next-goal` - Get AI recommendation
- `/goal-conflicts` - Check for conflicts

## Tips

1. **Focus on CRITICAL tier**: These need immediate attention
2. **Check deadline urgency**: Short deadlines elevate priority
3. **Monitor on-track status**: Behind schedule goals need attention
4. **Balance portfolio**: Mix CRITICAL with HIGH items
5. **Use for sprint planning**: Rank goals for sprint selection
6. **Review weekly**: Priorities change as work progresses

## Phase 3 Integration

This command implements:
- Composite priority scoring algorithm
- Factor weighting (40-35-15-10)
- Tie-breaking logic
- Historical priority tracking
- Priority change alerts

## Related Tools

- `task_management_tools:get_goal_priority_ranking` - Scoring
- `task_management_tools:get_active_goals` - Load goals
- `monitoring_tools:analyze_critical_path` - Path analysis
- `coordination_tools:detect_resource_conflicts` - Conflict detection

## See Also

- `/project-status` - Complete project overview
- `/activate-goal` - Switch to goal
- `/goal-conflicts` - Detect conflicts
- `/task-create` - Create tasks from goals
