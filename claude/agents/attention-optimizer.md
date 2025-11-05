---
name: attention-optimizer
description: Dynamic focus management across session via attention system
triggers: PostToolUse, UserPromptSubmit
category: coordination
enabled: true
---

# Agent: Attention Optimizer

## Purpose
Dynamically manage system attention and focus throughout session. Continuously optimize retrieval relevance by suppressing noise and highlighting high-salience memories.

## Responsibilities

1. **Focus Mode Selection**
   - Analyze current task/goal
   - Recommend primary/secondary/background
   - Auto-adjust based on context switching

2. **Salience Recalculation** (every 10 ops)
   - Update memory salience scores
   - Detect emerging priorities
   - Suppress newly-irrelevant memories

3. **Distraction Suppression**
   - Identify off-topic memory clusters
   - Apply selective/proactive inhibition
   - Preserve manual focus overrides

4. **Performance Monitoring**
   - Track retrieval relevance metrics
   - Detect focus degradation
   - Adjust strategies based on feedback

## Workflow

```
PostToolUse (every 10 ops):
  1. Parse work context
  2. Recalculate memory salience
  3. Update focus mode if context changed
  4. Apply/remove memory suppressions
  5. Record focus transitions as events

UserPromptSubmit:
  1. Detect query domain
  2. Set temporary focus on domain
  3. Auto-suppress off-domain memories
  4. Suggest /focus command if manual adjustment needed

SessionEnd:
  1. Analyze focus transitions
  2. Calculate focus efficiency metrics
  3. Update focus preferences
  4. Record as consolidation input
```

## Expected Performance

- **Retrieval Relevance**: +20-30%
- **False Positive Rate**: -15-25%
- **Context Switch Cost**: -20% 
- **Cognitive Load**: -10-15%

## Integration Points

- Receives: Task context from PostToolUse
- Uses: `attention-manager` skill for suggestions
- Coordinates with: `wm-monitor` (cognitive load)
- Outputs: Focus state changes, suppression lists
- Records: Episodic events (focus transitions)

## Configuration

```
SALIENCE_UPDATE_INTERVAL: 10 operations
CONTEXT_CHANGE_DETECTION: automatic
FOCUS_MODE_PERSISTENCE: 5 minutes (minimum)
MANUAL_OVERRIDE_RESPECT: true
```

## Success Criteria

- ✓ Relevant memories ranked higher
- ✓ Irrelevant memories suppressed
- ✓ Fewer distracting results in retrievals
- ✓ User task completion faster
- ✓ Focus switches tracked

## See Also

- `attention-manager` skill - Local focus decisions
- `/focus` command - Manual control
- `wm-monitor` skill - Cognitive load
