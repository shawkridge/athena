---
name: execution-tracking
description: |
  Track real-time execution with adaptive replanning. Use during work to monitor progress, detect deviations, trigger automatic plan adjustments. Monitors 5 replanning strategies.
---

# Execution Tracking Skill

Real-time task execution monitoring with adaptive replanning.

## When to Use

- During active work execution
- Monitoring progress toward goals
- Detecting deviations from plan
- Enabling automatic plan adjustments

## Monitoring

- Task progress and health
- Deviation detection (>15% from plan)
- Assumption validity
- Blocker identification
- Resource utilization

## Adaptive Replanning

**5 Strategies**:
1. Parallelization (concurrent tasks)
2. Compression (batch related work)
3. Reordering (unblock dependencies)
4. Escalation (add resources)
5. Deferral (move to future)

## Returns

- Task health score (0.0-1.0)
- Progress % and time remaining
- Detected deviations with severity
- Adaptive replans if triggered
- Blocker list with resolutions
- Resource status
- Completion confidence

The execution-tracking skill activates during active task work for continuous monitoring.
