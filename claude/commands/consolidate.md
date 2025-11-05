---
description: Run memory consolidation with dry-run, domain filtering, and quality metrics
group: Consolidation & Learning
aliases: ["/consolidate-memory", "/sleep"]
---

# /consolidate

Extract patterns from episodic events (sleep-like consolidation), measure quality, and optimize memory.

## Usage

```bash
/consolidate                    # Run full consolidation
/consolidate --dry-run         # Preview without changes
/consolidate --domain research # Filter by domain
/consolidate --detail          # Show detailed metrics
```

## What It Does

Consolidation is "sleep for AI" - extracting patterns from episodic events and storing as semantic memories:

1. **Cluster Events** - Group by session, temporal proximity, file overlap
2. **Extract Patterns** - Use Claude to identify recurring themes
3. **Store Memories** - Save patterns as semantic memories with source references
4. **Measure Quality** - Track compression ratio, retrieval recall, consistency
5. **Optimize** - Clean up low-value memories, update usefulness scores

## Example Output

```
Consolidating 127 episodic events...

Events Processed: 127
Sessions Identified: 8
Time Span: 7 days

Patterns Extracted: 12
  • JWT implementation workflow (strength: 0.95)
  • Database schema iteration pattern (strength: 0.88)
  • Error recovery heuristics (strength: 0.82)
  • Code review checklist (strength: 0.79)
  ... (8 more patterns)

Quality Metrics:
  • Compression Ratio: 0.82 (82% compression, target: 0.7-0.85) ✓
  • Retrieval Recall: 0.87 (87% info preserved, target: >0.8) ✓
  • Pattern Consistency: 0.81 (81% generalization, target: >0.75) ✓
  • Information Density: 0.76 (76% relevant info/token, target: >0.7) ✓

Memory Optimization:
  • Memories Analyzed: 456
  • Low-Value Removed: 12
  • Usefulness Scores Updated: 89
  • Memory Shrink: 2.3MB → 1.9MB

New Semantic Memories: 12 created
  → ID: 902 - JWT implementation workflow
  → ID: 903 - Database iteration pattern
  ... (10 more)

Next Consolidation: ~168h (7 days)
Status: SUCCESS - All quality targets met
```

## Options

- `--dry-run` - Preview without modifying
- `--domain DOMAIN` - Filter events by domain (research, implementation, testing, etc.)
- `--detail` - Show detailed quality metrics
- `--no-optimize` - Skip memory optimization step
- `--force` - Run even if recently consolidated

## Quality Targets

| Metric | Target | What It Means |
|--------|--------|---------------|
| Compression | 0.7-0.85 | 70-85% of space saved |
| Recall | >0.80 | 80%+ of info preserved |
| Consistency | >0.75 | Patterns generalize well |
| Density | >0.70 | Efficient info per token |

## Integration

Works with:
- `/memory-health` - Check memory quality after consolidation
- `/memory-query` - Search newly created patterns
- `/project-status` - See impact on project learnings
- `/focus` - Load consolidated memories into working memory

## Related Tools

- `run_consolidation` - Core consolidation engine
- `consolidation_quality_metrics` - Measure quality
- `optimize` - Clean up memories
- `analyze_coverage` - Domain analysis

## When to Run

- **Weekly**: Recommended for ongoing projects
- **After major work**: Following multi-day implementation sprints
- **Before transitions**: Before switching projects or phases
- **On cleanup**: When memory gets large (>100 events/session)

## Tips

1. Run `/consolidate --dry-run` first to preview
2. Review extracted patterns with `/memory-query`
3. Check quality metrics to validate consolidation
4. Run during downtime (not during active coding)

## See Also

- `/memory-health` - Analyze memory quality
- `/memory-query` - Search consolidated patterns
- `/project-status` - See project learnings

