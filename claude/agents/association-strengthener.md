---
name: association-strengthener
description: Orchestrate Hebbian learning across system via association strengthening
triggers: SessionEnd, PostToolUse
category: coordination
enabled: true
---

# Agent: Association Strengthener

## Purpose
Orchestrate Hebbian learning at system level. Efficiently batch-update association strengths, detect emerging knowledge clusters, and coordinate consolidation.

## Responsibilities

1. **Association Batch Updates** (SessionEnd)
   - Collect all co-retrievals from session
   - Calculate new strengths efficiently
   - Apply batch upsert to DB
   - Update association index

2. **Cluster Discovery**
   - Detect knowledge clusters (cohesive groups)
   - Identify bridge entities (inter-cluster links)
   - Measure cluster strength
   - Track emergence of new clusters

3. **Association Health**
   - Monitor association decay (aging links)
   - Detect orphaned memories (low connectivity)
   - Identify weakly-connected domains
   - Suggest reinforcement through retrieval

4. **Consolidation Coordination**
   - Pass cluster info to consolidation system
   - Suggest high-value consolidation targets
   - Track consolidation impact on associations
   - Update association strengths post-consolidation

## Workflow

```
PostToolUse (every 10 ops):
  1. Record co-retrieved memory pairs
  2. Calculate relevance scores (lazy)
  3. Queue strength updates

SessionEnd (batch):
  1. Collect all queued updates
  2. Recalculate strengths with full context
  3. Detect bridge entities
  4. Identify new/emerging clusters
  5. Apply batch updates to DB
  6. Record as consolidation input
  7. Generate cluster report

PostConsolidation:
  1. Update association strengths based on learned patterns
  2. Create new associations from consolidated insights
  3. Strengthen bridge entities
  4. Record impact metrics
```

## Association Strength Formula

```
new_strength(A, B) = old_strength(A, B) + (0.1 × relevance_score)

Where relevance = 0.6 × co_retrieval_count
                + 0.3 × semantic_similarity
                + 0.1 × recency_weight

Caps at 0.99 (prevents infinite growth)
Minimum update: 0.01 (numerical stability)
```

## Expected Outcomes

- **Knowledge Cluster Formation**: Automatic (no user effort)
- **Emergent Insights**: +30-50% cross-domain connections
- **Consolidation Efficiency**: -30% redundant consolidation
- **Retrieval Quality**: +15% via better association structure

## Integration Points

- Receives: Co-retrieval pairs from `association-learner` skill
- Uses: Association network MCP tools
- Feeds into: Consolidation system
- Coordinates with: `consolidation-trigger` agent
- Records: Association metrics as episodic events

## Configuration

```
BATCH_INTERVAL: SessionEnd (daily)
CO_RETRIEVAL_WINDOW: Session duration
CLUSTER_DETECTION_METHOD: Graph clustering
MIN_ASSOCIATION_STRENGTH: 0.05 (min trackable)
STRENGTH_CAP: 0.99 (max value)
```

## Performance

- SessionEnd batch: 1-5s (depends on retrieval count)
- Cluster detection: 500-2000ms  
- Database upsert: 100-500ms (batch optimized)

## Success Criteria

- ✓ Associations automatically strengthen
- ✓ Knowledge clusters form naturally
- ✓ Bridge entities identified
- ✓ Association decay prevented via use
- ✓ Consolidation targets improved

## See Also

- `association-learner` skill - Per-retrieval strengthening
- `/associations` command - Manual association mgmt
- Hebbian learning in cognitive science
- Knowledge graphs and clustering
