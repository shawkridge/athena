---
category: skill
description: Generate meta-insights from memory analysis and reflection
trigger: Model performing meta-analysis, or user runs /reflect or /consolidate
confidence: 0.85
---

# Insight Generator Skill

Synthesizes memories and patterns to generate strategic insights and recommendations.

## When I Invoke This

I detect:
- Consolidation completing (patterns ready)
- User runs `/reflect --deep`
- Project milestone completed (time to assess)
- Multiple related memories exist
- Meta-analysis requested

## What I Do

```
1. Gather perspectives
   → Call: recall() - Search semantic memories
   → Call: smart_retrieve() - Find related learnings
   → Call: get_expertise() - Review domain coverage
   → Call: get_self_reflection() - Meta-analysis data

2. Synthesize patterns
   → Identify: Recurring themes
   → Find: Contradictions and tensions
   → Extract: Key learnings
   → Identify: Blindspots

3. Generate insights
   → Call: get_metacognition_insights()
   → Analyze: System performance
   → Project: Future needs
   → Recommend: Strategic improvements

4. Present findings
   → Insight #1: What I learned
   → Insight #2: What works well
   → Insight #3: What needs improvement
   → Recommendation: Next steps
```

## MCP Tools Used

- `recall` - Search semantic memories
- `smart_retrieve` - Advanced search
- `get_expertise` - Domain analysis
- `get_self_reflection` - Meta-analysis
- `get_metacognition_insights` - System insights
- `analyze_coverage` - Coverage analysis
- `record_event` - Document insights

## Example Invocation

```
You: /reflect --deep

Insight Generator synthesizing deep analysis...

KEY INSIGHTS FROM 3 WEEKS OF WORK:

Insight #1: Episodic Learning Works Best
  • Pattern: Consolidating daily events → strong retention
  • Evidence: 94% accuracy on episodic facts vs 78% ad-hoc
  • Implication: Structure work as discrete events
  • Action: Always use /consolidate weekly

Insight #2: Procedural Extraction Saves Time
  • Pattern: Documented workflows reduce task time 30-40%
  • Evidence: JWT implementation: 8h → 5h (37% improvement)
  • Implication: Invest in procedure documentation
  • Action: Extract 2+ workflows per project

Insight #3: Knowledge Graph Connections Improve Recall
  • Pattern: Items with 3+ associations: 0.89 recall
  • Evidence: Items with 0 associations: 0.61 recall
  • Implication: Build rich connections during learning
  • Action: Strengthen 1-2 links per session

Insight #4: Consolidation Quality Matters
  • Pattern: High-quality consolidation (>0.85 compression):
    Retention 91%, vs low-quality 68%
  • Implication: Invest in consolidation process
  • Action: Run weekly /consolidate with validation

Strategic Recommendations:

High Impact (Do Now):
  1. Establish weekly consolidation routine (15 min)
  2. Extract 1-2 workflows per project phase
  3. Build association graph (3+ links per memory)

Medium Impact (This Month):
  4. Deep dive into low-confidence areas (DevOps, Kubernetes)
  5. Cross-link projects to build meta-patterns
  6. Document decision rationales (prevent attribution errors)

Lower Impact (Quarterly):
  7. Strategic quarterly review (1-2h)
  8. Refresh organization structure (keep relevant)
  9. Archive old learnings (keep current)

Confidence: 0.91 (High - based on 3 weeks data)
Next Insight Review: 2 weeks
```

## Success Criteria

✓ Insights grounded in data
✓ Recommendations actionable
✓ Strategic value identified
✓ Improvements measurable

## Related Commands

- `/reflect` - Generate insights
- `/consolidate` - Extract learnings
- `/project-status` - Assess project outcomes
- `/memory-health` - Validate insights

