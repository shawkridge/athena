---
name: gap-detector
description: Proactively detect knowledge gaps, contradictions, and uncertainties
triggers: UserPromptSubmit, SessionEnd
category: knowledge-management
enabled: true
---

# Skill: Gap Detector

Scan for knowledge gaps, contradictions, and uncertainties. Alert to knowledge needing improvement.

## Gap Types Detected

1. **Contradictions**: Memory A vs NOT Memory B (both confident)
2. **Uncertainties**: Low confidence, never validated
3. **Missing Info**: Related topics not covered
4. **Stale Knowledge**: Not retrieved in 30+ days
5. **Underexposed**: Important but low-retrieval-count

## How It Works

**UserPromptSubmit**: Analyze query topic, search related, detect issues
**SessionEnd**: Scan all memories, detect inconsistencies

## Algorithm

```
contradiction_score = semantic_similarity(A, NOT B)
                    × min(confidence_A, confidence_B)

uncertainty_score = 1 - confidence + recency_decay

coverage_score = domain_memories / expected_size

gap_significance = max(scores)

Alert if: gap_significance > 0.7
```

## Configuration

```
CONFIDENCE_THRESHOLD: 0.7
COVERAGE_MIN: 0.4 (40% of domain)
STALE_THRESHOLD: 30 days
CONSOLIDATION_REQUIRED: 2 retrievals
```

## Integration

- Works with: `/memory-health` command
- Feeds into: `consolidation-trigger`
- Tracks: Gap history

## See Also
- `/memory-health` command
- Knowledge gap theory
- Contradiction detection in KGs
