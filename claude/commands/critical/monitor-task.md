---
description: Real-time execution monitoring with adaptive replanning when deviations detected
argument-hint: "Task ID to monitor"
---

# Monitor Task

Track real-time task execution with automatic detection of deviations and adaptive replanning.

Usage: `/monitor-task <task_id>` or `/monitor-task` for current task

Features:
- **Real-Time Health**: Monitor task status, progress, blockers
- **Deviation Detection**: Alert when execution deviates >15% from plan
- **Adaptive Replanning**: Auto-trigger plan adjustments using 5 strategies:
  1. **Parallelization**: Execute non-dependent tasks concurrently
  2. **Compression**: Batch related tasks, consolidate steps
  3. **Reordering**: Topological sort optimization
  4. **Escalation**: Add resources to critical path
  5. **Deferral**: Move non-critical tasks to future phases

- **Assumption Validation**: Check if initial assumptions still hold
- **Blocker Resolution**: Identify and suggest resolution for blockers

Returns:
- Current task health (0.0-1.0)
- Progress percentage and time remaining
- Any detected deviations with severity
- Adaptive replans if triggered (with impact analysis)
- Blocker list with suggested resolutions
- Resource utilization status
- Confidence in completion by deadline

The execution-monitor agent autonomously watches active tasks and triggers this during work.

Typical output: Updates every 30 seconds during active execution, suggesting plan adjustments in real-time.
