---
category: skill
description: Autonomously analyze knowledge gaps and domain coverage, recommend research
trigger: Model detects knowledge gaps or incomplete understanding, or user runs /memory-health
confidence: 0.88
---

# Knowledge Analyst Skill

Analyzes memory coverage, detects gaps and contradictions, and recommends research areas.

## When I Invoke This

I detect:
- Uncertainty about a topic (<0.7 confidence)
- Contradictory memories
- Missing information referenced in multiple places
- User runs `/memory-health` with gaps option
- Domain with low coverage

## What I Do

```
1. Analyze coverage
   → Call: analyze_coverage()
   → Map: Known vs unknown
   → Identify: High-confidence domains
   → Identify: Low-confidence areas
   → Identify: Contradictions

2. Detect gaps
   → Call: detect_knowledge_gaps()
   → Find: Contradiction gaps (conflicting info)
   → Find: Uncertainty gaps (low confidence)
   → Find: Missing info gaps (referenced but unknown)
   → Rank: By impact on current work

3. Get expertise levels
   → Call: get_expertise()
   → Rank: Domains by confidence
   → Show: Gaps in top domains
   → Show: Emerging domains needing attention

4. Recommend research
   → Suggest: Topics to research
   → Suggest: Priority (high/medium/low)
   → Suggest: Search terms
   → Link: To related existing memories
```

## MCP Tools Used

- `analyze_coverage` - Domain coverage analysis
- `detect_knowledge_gaps` - Find gaps
- `get_expertise` - Expertise ranking
- `smart_retrieve` - Search current knowledge
- `record_execution` - Track analysis
- `remember` - Store new learnings

## Example Invocation

```
You: /memory-health --gaps

Knowledge Analyst analyzing...

Domain Coverage:
  ★★★★★ JWT (0.95) - Expert
  ★★★★☆ Node.js (0.89) - Advanced
  ★★★☆☆ Database (0.71) - Intermediate
  ★★☆☆☆ DevOps (0.58) - Beginner
  ★☆☆☆☆ Kubernetes (0.42) - Novice

Gaps Detected:

CONTRADICTION (High Priority):
  JWT token lifetime: 5-min vs 1-hour
    → Memory 456: "Use 5-minute lifetime"
    → Memory 789: "Use 1-hour lifetime"
    → Impact: Medium (decisions conflicting)

UNCERTAINTY (Medium Priority):
  Error handling in rollback: 0.62 confidence
    → Referenced in: 3 locations
    → Last update: 7 days ago
    → Recommendation: Revalidate or research

MISSING (Low Priority):
  OAuth2 integration: Referenced but never researched
    → Found in: 2 tasks, 1 memory
    → Estimated impact: Low (future feature)
    → Recommendation: Research when needed

Recommendation:
  1. Resolve JWT contradiction (high priority)
  2. Revalidate error handling (if needed soon)
  3. Research OAuth2 (for future work)
```

## Success Criteria

✓ All gaps identified
✓ Ranked by impact
✓ Contradictions highlighted
✓ Research recommendations provided

## Related Commands

- `/memory-health` - Full health report
- `/memory-query` - Search for resolution
- `/consolidate` - Extract patterns (may resolve contradictions)

