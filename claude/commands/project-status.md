---
description: Get comprehensive project overview with goals, tasks, progress, and recommendations
group: Status & Overview
aliases: ["/status", "/progress", "/overview"]
---

# /project-status

Display full project status including active goals, task progress, completion estimates, and recommendations.

## Usage

```bash
/project-status                    # Current project (auto-detected from cwd)
/project-status ecommerce-auth     # Specific project
/project-status --detail          # Full details with task breakdown
```

## What It Displays

- **Project Name & Description**
- **Active Goals** with progress and priorities
- **Phase Status** (if applicable)
- **Tasks** - Completed, in-progress, pending, blocked
- **Metrics**:
  - Completion percentage
  - Burn rate (tasks/day)
  - Estimated completion date
  - On-track / at-risk / blocked status
- **Recommendations** - Next actions based on current state

## Example Output

```
Project: ecommerce-auth-refactor
Status: Active
Last Updated: 2 hours ago

Primary Goal:
  Modernize authentication system using JWT (Priority: 10/10)
  Deadline: 2025-11-15
  Progress: 60% (9/15 tasks complete)

Current Phase:
  Phase 1: JWT Implementation (60% complete)
  - 9/15 tasks completed
  - 2 in progress: Token validation, User migration
  - 4 pending: Edge case testing, Performance, Docs

Task Summary:
  ✓ 9 completed
  → 2 in progress (6h each, 4h remaining)
  ⏸ 4 pending (estimated 20h)
  ⚠ 0 blocked

Burn Rate: 1.2 tasks/day
Estimated Completion: 2025-11-12 (on track)

Recommendations:
  • Continue token validation (in progress)
  • Start performance testing in parallel (low dependency)
  • Review edge case requirements (pending)

Memory References:
  📌 Phase 1 Goal (ID: 123)
  📌 JWT Architecture (ID: 456)
  📌 Known Issues (ID: 789)

Recent Activity:
  • 30 min ago: Updated token validation task
  • 2h ago: Started user migration
  • 5h ago: Completed middleware implementation
```

## Options

- `--detail` - Show full task breakdown with times
- `--project NAME` - Override auto-detection
- `--goals` - Show goals only
- `--tasks` - Show tasks only
- `--metrics` - Show metrics and burn rate analysis

## Integration

Works with:
- `/task-create` - Create new tasks within project
- `/plan-validate` - Validate project plans
- `/memory-query` - Search project decisions and patterns
- `/focus` - Load project goals into working memory
- `/consolidate` - Consolidate project learnings

## Related Tools

- `get_project_status` - Core status retrieval
- `get_active_goals` - List project goals
- `list_tasks` - List all tasks by status
- `analyze_coverage` - Analyze project knowledge

## Tips

1. Run at start of session to get context
2. Use with `/memory-query` to find related memories
3. Check burn rate to adjust time estimates
4. Review recommendations for next actions

## See Also

- `/task-create` - Add new tasks
- `/plan-validate` - Check plan correctness
- `/consolidate` - Extract learnings
