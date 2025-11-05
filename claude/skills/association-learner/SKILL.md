---
name: association-learner
description: Auto-strengthen memory associations through Hebbian learning feedback
triggers: PostToolUse, SessionEnd
category: learning
enabled: true
---

# Skill: Association Learner

## Purpose
Automatically strengthen associations between memories when co-retrieved (Hebbian learning). Creates emergent knowledge clusters without user intervention.

## How It Works

### On PostToolUse
1. Detect co-retrieved memories
2. Calculate relevance: recency × frequency × similarity
3. Increase association strength by 0.1 × relevance_score
4. Detect bridge entities (high-degree connectors)
5. Record episodic events for consolidation

### On SessionEnd  
1. Batch process all co-retrievals from session
2. Update association strengths efficiently
3. Trigger association-strengthener agent if >10 updates

## Algorithm

```
For each co-retrieved memory pair (A, B):
  relevance = 0.6 × co_retrieval_count
            + 0.3 × semantic_similarity(A, B)
            + 0.1 × recency_weight

  new_strength = strength(A, B) + (0.1 × relevance)
  
  If new_strength > 0.85:
    Mark as bridge entity (connects 2+ clusters)
```

## Configuration

```
POST_TOOL_USE_INTERVAL: 10 operations
SESSION_END_BATCH: true
MIN_RELEVANCE_THRESHOLD: 0.3
STRENGTH_BOOST_FACTOR: 0.1
BRIDGE_ENTITY_MIN_DEGREE: 3
```

## Performance

- Per-operation: <10ms
- Session batch: 500-2000ms
- Memory overhead: 2-5MB

## Integration

- Works with: `/associations` command
- Feeds into: `consolidation-trigger`
- Tracks: Episodic events

## Behavioral Notes

- Silent operation (no notifications)
- Gradual strengthening (prevents false positives)
- Caps strength at 0.99 (prevents infinite loops)

## See Also

- `/associations` command - Manual association management
- Hebbian learning in cognitive science
