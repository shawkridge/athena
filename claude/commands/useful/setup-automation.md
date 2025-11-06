---
description: Create event-driven automation with triggers - time-based, event-based, or file-based
argument-hint: "$1 = trigger type (time|event|file), $2 = trigger condition, $3 = action"
---

# Setup Automation

Create smart event-driven automation with time-based, event-based, or file-based triggers.

Usage:
- `/setup-automation time "every monday 9am" "consolidate"` - Weekly consolidation
- `/setup-automation event "task-completed" "run-next-step"` - Chain tasks
- `/setup-automation file "*.py" "analyze-code"` - Auto-analyze Python files

**Trigger Types**:

1. **Time-Based**
   - Cron-style scheduling
   - Examples: "every Monday 9am", "daily at 5pm", "monthly on 1st"

2. **Event-Based**
   - Actions: task-completed, goal-achieved, error-detected, memory-consolidated
   - Examples: "on task-completed run /consolidate"

3. **File-Based**
   - File patterns and watch for changes
   - Examples: "on *.py change run /analyze-code", "on README.md update notify"

**Automation Actions**:
- Execute slash commands (`/command-name`)
- Run procedures (`execute procedure "name"`)
- Trigger agents (`delegate to planning-orchestrator`)
- Send notifications
- Create memories/logs

Returns:
- Automation rule ID created
- Trigger condition and action
- Schedule if time-based
- Execution history once activated
- Recommendations for optimization

The automation-engine agent creates and manages automation rules for you.

Example setup:
```
Rule: "Weekly-Consolidation"
  Trigger: Time-based, every Friday 5pm
  Action: /consolidate --strategy quality
  Status: Active (last run: 2025-11-06 5:00pm)
  Success Rate: 100% (4 executions)
  Avg Duration: 2.3 minutes
```
