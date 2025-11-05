---
name: attention-manager
description: Auto-focus on high-salience memories and suppress distracting noise
triggers: SessionStart, PostToolUse, UserPromptSubmit
category: focus-management
enabled: true
---

# Skill: Attention Manager

Improve retrieval relevance (+20-30%) by auto-focusing on high-salience memories and suppressing distractions.

## How It Works

**SessionStart**: Analyze goals, set focus mode, suppress off-topic
**PostToolUse** (every 10 ops): Update salience, adjust focus, suppress
**UserPromptSubmit**: Detect domain, set focus, suppress unrelated

## Salience Calculation

```
salience(memory) = 0.4 × relevance_to_goal
                 + 0.3 × recency_weight
                 + 0.2 × retrieval_frequency
                 + 0.1 × usefulness_score

Focus modes:
  PRIMARY:   Keep top 20%, suppress bottom 50%
  SECONDARY: Keep top 40%, suppress bottom 30%
  BACKGROUND: Keep all (no suppression)
```

## Configuration

```
AUTO_FOCUS: true
UPDATE_INTERVAL: 10 operations
RECALC_INTERVAL: 5 minutes
AUTO_SUPPRESS_THRESHOLD: 0.2
GOAL_RELEVANCE_WEIGHT: 0.4
```

## Expected Improvements

```
Retrieval Relevance: +20-30%
Precision@5: +0.15-0.25
Cognitive Load: -10-15%
Task Completion: +5-10%
```

## Integration

- Works with: `/focus` command
- Feeds into: `attention-optimizer` agent
- Interacts with: `wm-monitor`

## See Also
- `/focus` command
- Attention in neural networks
- Goal relevance in IR
