---
category: skill
description: Autonomously consolidate memory, optimize storage, and clean up low-value items
trigger: Model detects memory bloat or inefficiency, or user explicitly runs /consolidate
confidence: 0.92
---

# Memory Optimizer Skill

This skill runs autonomously when memory consolidation is needed, extracting patterns and optimizing storage.

## When I Invoke This

I detect signs of memory bloat:
- Memory size >3MB without consolidation in 7 days
- Working memory >70% saturated
- Low-value memories accumulating (usefulness <0.3)
- User runs `/consolidate` command

## What I Do

```
1. Run consolidation
   → Call: run_consolidation()
   → Extract patterns from episodic events
   → Create semantic memories from patterns

2. Measure quality
   → Call: consolidation_quality_metrics()
   → Check: compression ratio (target: 0.7-0.85)
   → Check: retrieval recall (target: >0.8)
   → Validate all metrics pass

3. Optimize memory
   → Call: optimize()
   → Remove memories with usefulness <0.3
   → Update scores for remaining memories
   → Verify size reduction >10%

4. Report results
   → Show: Patterns extracted (count, strength)
   → Show: Quality metrics (all targets met?)
   → Show: Space freed (MB)
   → Show: Timestamp of next consolidation
```

## MCP Tools Used

- `run_consolidation` - Core consolidation pipeline
- `consolidation_quality_metrics` - Measure quality (compression, recall, consistency)
- `optimize` - Clean up low-value memories
- `record_execution` - Track this execution
- `record_event` - Log consolidation event
- `analyze_coverage` - Post-consolidation analysis

## Example Invocation

```
Claude: I notice your memory has 128 episodic events and hasn't been consolidated in 5 days.
Let me run consolidation to extract patterns.

Running memory-optimizer skill...
→ Extracting patterns: 12 patterns found
→ Compression ratio: 0.82 ✓ (target: 0.7-0.85)
→ Retrieval recall: 0.87 ✓ (target: >0.8)
→ Optimization: Removed 8 low-value memories, freed 0.4MB

Consolidation complete!
New patterns available: /memory-query "recent patterns"
Next consolidation: ~7 days
```

## Success Criteria

✓ Consolidation completes without errors
✓ All quality metrics meet targets
✓ Memory size reduced >10%
✓ New patterns created and accessible
✓ No regressions in existing memories

## Related Commands

- `/consolidate` - User-triggered consolidation
- `/memory-health` - Check quality after consolidation
- `/memory-query` - Search new patterns

