---
description: Create tasks with smart triggers, goal alignment, and plan validation
group: Tasks & Goals
aliases: ["/task", "/goal", "/create-goal"]
---

# /task-create

Create tasks with automatic triggers, goal linking, hierarchical decomposition, and plan validation.

## Usage

```bash
/task-create "Task description"
/task-create "Task" --goal "Parent goal"
/task-create "Task" --priority high --deadline 2025-11-15
```

## What It Does

1. **Create task** with status (pending/in-progress/completed/blocked)
2. **Link to goals** automatically
3. **Set triggers** - Time-based, event-based, context-based, file-based
4. **Validate plan** - Ensure task fits project timeline
5. **Track progress** - Active form for status updates

## Example Output

```
Creating new task...

Task: Implement JWT token refresh mechanism
Priority: High
Status: Pending
Deadline: 2025-11-15

Goal Alignment:
  └─ Modernize authentication system
     └─ Phase 1: JWT Implementation

Decomposition:
  1. Design refresh strategy (2h)
     → Decide: 5-min vs 1-hour token lifetime
     → Risk: Conflicts with existing code
  2. Implement refresh logic (3h)
  3. Write tests (2h)
  4. Document approach (1h)

Total Estimate: 8h

Triggers:
  ✓ Time-based: Start if not started in 2 days
  ✓ Event-based: Auto-update when goal changes
  ✓ Context-based: Auto-activate when /focus loads goal
  ✓ File-based: Auto-update on auth/jwt.py changes

Plan Validation:
  ✓ Fits in Phase 1 timeline
  ✓ No resource conflicts
  ✓ Dependencies satisfied
  ✓ Estimated completion: 2025-11-14 (on track)

Task Created: ID: 2847
Status: PENDING → Ready to start
Next: /project-status to see in context
```

## Commands

```bash
/task-create "Description"
/task-create "Description" --goal "Goal ID or name"
/task-create "Description" --priority high --deadline DATE
/task-create "Description" --decompose  # Auto-break down
/task-create "Description" --trigger "event:task-complete-on-id-123"
```

## Integration

Works with:
- `/project-status` - See task in project
- `/plan-validate` - Validate fit in plan
- `/focus` - Load task context
- `/consolidate` - Track learnings

## Related Tools

- `create_task` - Core task creation
- `create_goal` - Link to goals
- `decompose_hierarchically` - Auto-decompose
- `validate_plan` - Check fit
- `list_tasks` - View all tasks

## Smart Triggers

```
--trigger "time:48h"           # Start if not started in 48h
--trigger "event:goal-changed" # Trigger on goal update
--trigger "context:file-*.py"  # Trigger on Python file change
--trigger "event:task-complete-ID" # After other task completes
```

## Tips

1. Link tasks to goals (automatic alignment)
2. Use decomposition for complex tasks
3. Set appropriate triggers for automation
4. Validate plan fit before starting
5. Update status as you work

## See Also

- `/project-status` - View all tasks
- `/plan-validate` - Check timeline
- `/focus` - Load task context
