---
name: research-synthesizer
description: Cross-reference and synthesize findings from multiple research sources
trigger: Research completion or user analysis, or /research command completion
confidence: 0.86
---

# Research Synthesizer Skill

Cross-references findings from multiple research sources (8-source research), detects patterns, contradictions, and gaps in knowledge.

## When I Invoke This

I detect:
- Research-coordinator agent completes (8 parallel sources)
- User runs `/research` command
- Multiple sources analyzed simultaneously
- Need to reconcile conflicting findings
- Want to identify research trends or consensus

## What I Do

```
1. Gather research findings
   → Call: recall() to get all recent research
   → Filter: By source (arXiv, GitHub, HN, Reddit, Twitter, Anthropic, Medium, Papers)
   → Extract: Key claims, evidence, confidence, source

2. Cross-reference across sources
   → Compare: Findings across all 8 sources
   → Detect: Overlaps (consensus), contradictions, gaps
   → Score: Agreement level for each finding
   → Weight: By source credibility

3. Identify patterns & trends
   → Cluster: Similar findings (semantic similarity)
   → Detect: Consensus areas (>60% agreement)
   → Detect: Contradictions (direct conflicts)
   → Identify: Knowledge gaps (cited but not explained)
   → Identify: Emerging trends (multiple sources, recent)

4. Generate synthesis
   → Call: create_entity() for synthesized knowledge
   → Call: create_relation() to link source findings
   → Call: add_observation() to document synthesis
   → Return: Comprehensive cross-referenced report
```

## MCP Tools Used

- `smart_retrieve` - Find all research findings
- `recall` - Search semantic memories for research
- `recall_events` - Get episodic research events
- `create_entity` - Create synthesis entity
- `create_relation` - Link sources to synthesis
- `add_observation` - Document cross-reference analysis
- `remember` - Store synthesis as memory
- `record_event` - Track synthesis completion

## Configuration

```
SOURCE_CREDIBILITY:
  arXiv: 0.95 (peer-reviewed academic)
  GitHub: 0.85 (production code, community vetted)
  Anthropic Docs: 0.98 (official, authoritative)
  Twitter/X: 0.65 (expert opinion, varied quality)
  Medium: 0.70 (practitioner blogs, variable depth)
  HackerNews: 0.72 (community discussion, discussion quality)
  Reddit: 0.68 (community, discussion threads)
  PapersWithCode: 0.90 (research + implementations)

CONSENSUS_THRESHOLD: 0.60 (60% agreement = consensus)
CONTRADICTION_THRESHOLD: 0.40 (direct conflict)
CONFIDENCE_WEIGHTS:
  source_credibility: 0.4
  agreement_count: 0.3
  recent_count: 0.2
  detailed_evidence: 0.1
```

## Example Invocation

```
User: /research "llm memory architectures"

Research Synthesizer analyzing findings from 8 sources...

═════════════════════════════════════════════════════════════
RESEARCH SYNTHESIS: LLM Memory Architectures
═════════════════════════════════════════════════════════════

🔍 CONSENSUS FINDINGS (>80% agreement across sources):

1. Episodic Memory Importance (Consensus: 88%)
   ✓ arXiv (3 papers)
   ✓ GitHub (4+ implementations)
   ✓ Anthropic Docs
   ✓ Papers with Code (2 benchmarks)
   ✓ Medium (2 articles)
   ✓ HackerNews (discussed 4x)
   Finding: Episodic → Semantic consolidation critical for reasoning
   Evidence: Chen et al. (2024), Wamsley (2011), 10+ implementations
   Confidence: 0.96 (Very High)

2. Spatial-Temporal Grounding (Consensus: 76%)
   ✓ arXiv (2 papers)
   ✓ GitHub (3+ implementations)
   ✓ PapersWithCode (1 benchmark)
   ✓ Medium (1 article)
   ✓ Anthropic Docs (mentioned in context)
   Finding: File paths + timestamps improve memory retrieval
   Evidence: O'Keefe (2014), Horwitz (2023), production systems
   Confidence: 0.91 (High)

3. Hebbian Learning (Consensus: 82%)
   ✓ arXiv (2 papers)
   ✓ GitHub (8+ implementations)
   ✓ PapersWithCode (benchmarks)
   ✓ Medium (3 articles)
   ✓ HackerNews (discussed 3x)
   Finding: Co-activated memories strengthen associations
   Evidence: Hebbian principle (1949), modern implementations
   Confidence: 0.94 (Very High)

⚠️  CONTRADICTIONS (direct conflicts):

1. Working Memory Capacity Model
   Source A (Reddit, HN): 7±2 items (Baddeley 1986)
   Source B (arXiv): 4±1 items (revisionist research)
   Source C (Anthropic): Context window dependent
   Resolution Status: UNRESOLVED
   Recommendation: Use conservative 4±1 in safety-critical, document both
   Confidence in Resolution: 0.62 (Medium)

2. Consolidation Trigger Frequency
   Source A (arXiv): Every 50+ events (Chen et al.)
   Source B (GitHub): 5-minute intervals (production systems)
   Source C (Medium): Task completion only
   Source D (Reddit): Continuous (incremental)
   Resolution Status: CONTEXT-DEPENDENT
   Recommendation: Multiple triggers (frequency + event count + task completion)
   Confidence in Resolution: 0.79 (High)

3. RAG Strategy Selection
   Source A (arXiv - 2 papers): HyDE always superior
   Source B (GitHub - 5 implementations): Context-dependent
   Source C (Twitter - expert consensus): Use all 4 strategies with voting
   Resolution Status: CONTEXT-DEPENDENT
   Recommendation: Strategy selection based on query characteristics (our approach)
   Confidence in Resolution: 0.87 (High)

🔗 KNOWLEDGE GAPS (cited but not explained):

1. Metacognitive Error Correction (mentioned in 3 sources)
   • arXiv: Schraw & Dennison (1994) evaluation → adjustment loop
   • GitHub: Some implementations have partial loops
   • Missing: Clear implementation guidelines
   → Action: Research error correction frameworks (Assign to literature review)

2. Catastrophic Forgetting Prevention (mentioned in 2 sources)
   • arXiv: Continual learning problem
   • GitHub: Replay buffers used, limited documentation
   • Missing: Production techniques for LLM memory systems
   → Action: Investigate replay mechanisms and consolidation timing

3. Formal Verification for Plans (mentioned in 2 sources)
   • arXiv: LTL properties, symbolic reasoning
   • GitHub: Limited implementation
   • Missing: Integration with LLM-based planning
   → Action: Research hybrid symbolic-LLM verification

📈 EMERGING TRENDS (multiple recent sources):

1. Distributed Memory Systems (4 sources, 2024-2025)
   • Increasing interest in multi-agent shared memory
   • Trend: Moving from single-system to network-based
   Implication: Consider distributed consolidation

2. Neural + Symbolic Hybrids (3 sources, 2024)
   • Combining neural (semantic) with symbolic (formal) reasoning
   • Success rate: 15-30% accuracy improvement
   Implication: Formal verification worth investigating

3. Source Credibility Weighting (2 sources, late 2024)
   • Bayesian surprise for source evaluation
   • Information gain metrics for consolidation triggers
   Implication: Upgrade from manual weighting

📊 SYNTHESIS QUALITY METRICS:

Consensus Coverage: 78% (7/9 findings have >60% agreement)
Contradiction Resolution: 67% (2/3 unresolved or partial)
Gap Identification: 100% (All mentioned gaps identified)
Emerging Trend Detection: 3 trends identified (healthy)

Overall Synthesis Confidence: 0.84 (High)
Actionability: 8/9 findings suggest concrete next steps

═════════════════════════════════════════════════════════════

🎯 STRATEGIC IMPLICATIONS:

High Priority (act on immediately):
  1. Implement episodic→semantic consolidation (consensus, high impact)
  2. Add spatial-temporal grounding (consensus, proven)
  3. Strengthen Hebbian learning (consensus, widely used)

Medium Priority (investigate this quarter):
  1. Resolve working memory capacity model discrepancy
  2. Test multiple consolidation triggers together
  3. Evaluate RAG strategy selection approach

Emerging Opportunities (research next):
  1. Distributed memory for multi-agent systems
  2. Neural + symbolic hybrid reasoning
  3. Bayesian surprise for source credibility

═════════════════════════════════════════════════════════════

✅ Synthesis Complete
Generated: 2025-10-25 17:15:23
Sources: 8 (arXiv, GitHub, HN, Reddit, Twitter, Anthropic, Medium, Papers)
Memories Created: 3 synthesis entities with cross-references
```

## Expected Benefits

```
Knowledge Integration: +40-60% better understanding
Gap Identification: Surface missing knowledge proactively
Consensus Detection: Identify safe areas vs contested
Trend Analysis: Stay on cutting edge of research
Contradiction Resolution: Resolve conflicts systematically
```

## Performance

- 8-source research execution: <30s total
- Cross-reference analysis: 2-5s
- Synthesis generation: 3-8s
- Total synthesis latency: <1 minute

## Integration Points

- Works with: `/research` command (8-source research)
- Triggered by: research-coordinator agent completion
- Feeds into: knowledge-analyst skill (gap identification)
- Feeds into: memory-optimizer (consolidation planning)
- Stores: Synthesis as entities with cross-references

## Quality Metrics

```
Consensus Detection Accuracy: Target >85%
Contradiction Detection Accuracy: Target >90%
Gap Identification Completeness: Target >90%
False Positive Rate: Target <5%
```

## Limitations

- Requires at least 5 sources to reach meaningful consensus
- Performance depends on source credibility data accuracy
- Contradictions may be context-dependent (not true conflicts)
- Emerging trends need 2+ months to establish credibility

## Related Commands

- `/research` - Trigger multi-source research (synthesizer auto-runs on completion)
- `/memory-health --gaps` - View knowledge gaps identified by synthesizer
- `/learning` - Assess learning effectiveness of synthesized knowledge
- `/consolidate` - Consolidate synthesis into long-term memory

## Success Criteria

✓ Cross-references findings from all 8 sources
✓ Identifies consensus (>60% agreement)
✓ Detects contradictions with resolution suggestions
✓ Surfaces knowledge gaps and emerging trends
✓ Synthesized knowledge stored with full provenance
✓ Actionable strategic implications identified
