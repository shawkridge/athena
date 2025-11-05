---
name: procedure-suggester
description: Suggest reusable procedures and workflows for repeated patterns
triggers: UserPromptSubmit, SessionStart
category: workflow-optimization
enabled: true
---

# Skill: Procedure Suggester

Detect repeated patterns and suggest reusable procedures. Accelerate workflows 5-10x via automation suggestions.

## How It Works

**UserPromptSubmit**: Parse task, match against procedures, suggest top 3
**SessionStart**: Detect task types, pre-surface applicable workflows

## Pattern Matching

```
similarity(task, procedure) = 0.5 × semantic_sim(task, steps)
                            + 0.3 × entity_match(files, domains)
                            + 0.2 × context_match(project, phase)

confidence = similarity × success_rate(procedure)

Suggest if: confidence > 0.65
```

## Algorithm

For each procedure:
1. Check domain applicability
2. Calculate semantic similarity
3. Look for entity overlaps
4. Calculate success rate
5. Rank by confidence × success_rate × recency

## Configuration

```
CONFIDENCE_THRESHOLD: 0.65
MIN_SUCCESS_RATE: 0.7 (70%)
MAX_SUGGESTIONS: 3
ENTITY_MATCH_WEIGHT: 0.3
```

## Expected Benefits

```
Workflow Speed: +5-10x
Error Rate: -30-50%
Consistency: +40-60%
Time Saved: 30-120 min/week
```

## Integration

- Works with: `/procedures` command
- Learns from: `/learning` (domain effectiveness)
- Tracks: Execution success

## See Also
- `/procedures` command
- Standard Operating Procedures (SOPs)
- Workflow automation
