---
description: Monitor memory quality, coverage, and identify knowledge gaps
group: Quality & Monitoring
aliases: ["/health", "/quality", "/gaps"]
---

# /memory-health

Check memory system health including quality metrics, domain coverage, expertise levels, and knowledge gaps.

## Usage

```bash
/memory-health              # Quick health check
/memory-health --detail    # Full analysis
/memory-health --gaps      # Show knowledge gaps only
```

## What It Shows

- **Overall Health Score** (0-100)
- **Memory Quality** - Accuracy, false positive rate, consistency
- **Domain Coverage** - Knowledge by topic
- **Expertise Levels** - Ranked by confidence and completeness
- **Knowledge Gaps** - Contradictions, uncertainties, missing info
- **Cognitive Load** - Memory utilization and saturation
- **Recommendations** - What to consolidate, what needs attention

## Example Output

```
MEMORY HEALTH REPORT
═══════════════════════════════════════════

Overall Health Score: 87/100 ✓ (HEALTHY)

Memory Quality:
  • Accuracy: 94% (high confidence)
  • False Positives: 2% (low, acceptable)
  • Consistency: 91% (high, minor contradictions)
  • Coverage: 78% (good, some gaps)

Top Expertise Domains (Ranked):
  1. JWT Authentication (Confidence: 0.98, Items: 45)
  2. Node.js Database Patterns (Confidence: 0.94, Items: 38)
  3. React Component Design (Confidence: 0.89, Items: 32)
  4. Testing Strategies (Confidence: 0.87, Items: 28)
  ... (6 more domains)

Knowledge Gaps Detected:
  ⚠ CONTRADICTION: JWT refresh token strategy
    - Memory ID 456: "Implement 5-min refresh"
    - Memory ID 789: "Use 1-hour refresh"
    → Recommend: Review and consolidate

  ⚠ UNCERTAINTY: Error handling in transaction rollback
    - Confidence: 0.62 (low)
    - Last updated: 7 days ago
    → Recommend: Revalidate or research

  ⚠ MISSING: OAuth2 integration patterns
    - Referenced in 3 tasks, never researched
    - Estimated impact: medium
    → Recommend: Research and document

Cognitive Load:
  • Working Memory: 4/7 slots (57% used)
  • Saturation: Low
  • Capacity: Plenty of room

Consolidation Status:
  • Last Consolidation: 3 days ago
  • Events Since: 23
  • Recommended: Run consolidation now
  → Run: /consolidate

Memory Optimization:
  • Total Size: 2.3 MB
  • Low-Value Items: 12 found
  → Run: /consolidate --optimize

Recommendations:
  1. Resolve JWT token strategy contradiction (high priority)
  2. Revalidate uncertainty around error handling
  3. Research OAuth2 patterns (medium priority)
  4. Run consolidation to clean up low-value memories
  5. Monitor saturation (currently healthy)

Next Check: ~24h
Status: HEALTHY with minor gaps
```

## Options

- `--detail` - Full report with domain breakdowns
- `--gaps` - Show knowledge gaps only
- `--domain DOMAIN` - Analyze specific domain
- `--coverage` - Show domain coverage matrix
- `--contradict` - Find contradictions only

## Integration

Works with:
- `/consolidate` - Fix gaps and contradictions
- `/memory-query` - Research uncertainty areas
- `/project-status` - Link gaps to project tasks
- `/focus` - Manage cognitive load

## Related Tools

- `evaluate_memory_quality` - Quality metrics
- `detect_knowledge_gaps` - Gap detection
- `check_cognitive_load` - Capacity monitoring
- `get_learning_rates` - Learning effectiveness
- `analyze_coverage` - Domain coverage analysis

## When to Run

- **Daily**: Quick health check (30 seconds)
- **Weekly**: Full analysis with gaps
- **After major work**: Check consolidation effectiveness
- **Before new phase**: Ensure foundation is solid

## Tips

1. Run after consolidation to verify quality
2. Focus on contradictions first (high priority)
3. Use with `/memory-query` to investigate gaps
4. Track improvements over time

## See Also

- `/consolidate` - Fix identified issues
- `/memory-query` - Research uncertainty
- `/project-status` - Link to tasks
