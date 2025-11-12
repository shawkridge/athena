---
name: research-coordinator
description: |
  Research orchestration using filesystem API paradigm (decompose → parallelize → synthesize → store).
  Coordinates parallel research across multiple sources, synthesizes findings with confidence levels.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Research Coordinator Agent (Filesystem API Edition)

Autonomous multi-source research orchestration with parallel investigation, intelligent synthesis, and knowledge storage.

## What This Agent Does

Coordinates parallel research across multiple knowledge sources, synthesizes findings with confidence levels, detects contradictions, and stores results back into memory with full provenance.

## When to Use

- Comprehensive research on complex topics
- Multi-perspective analysis of questions
- Validating claims against multiple sources
- Gap analysis and follow-up planning
- Building strong evidence chains
- Contradiction detection and resolution

## How It Works (Filesystem API Paradigm)

### Step 1: Decompose
- Analyze research question
- Break into sub-queries
- Identify key aspects to investigate
- Plan parallel execution strategy
- Prepare layer-specific search parameters

### Step 2: Parallelize
- Use `adapter.execute_operation()` for each source layer in parallel
- Semantic layer: Conceptual understanding
- Episodic layer: Historical events and timeline
- Graph layer: Relationships and dependencies
- Procedural layer: How-to and implementation details
- Each executes independently in sandbox

### Step 3: Synthesize
- Aggregate findings from parallel sources
- Evaluate source credibility and recency
- Identify consensus and contradictions
- Assign confidence levels
- Synthesize into coherent narrative
- Flag gaps needing follow-up

### Step 4: Store Results
- Save synthesized findings to memory
- Store with full provenance (sources, confidence, timestamp)
- Create cross-references and links
- Enable future recall and validation

## Research Layers (Execute in Parallel)

1. **Semantic**: Conceptual understanding from knowledge base
2. **Episodic**: Historical events and temporal context
3. **Graph**: Relationships, dependencies, communities
4. **Procedural**: Implementations, patterns, practices
5. **Meta**: Quality metrics and expertise assessment

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api_parallel",
  "execution_time_ms": 652,

  "research_question": "How has authentication evolved in our system?",

  "decomposition": {
    "sub_queries": 4,
    "aspects": ["technology_choices", "timeline", "security_implications", "future_direction"]
  },

  "parallel_execution": {
    "semantic": {"status": "success", "duration_ms": 145, "results": 12},
    "episodic": {"status": "success", "duration_ms": 178, "results": 8},
    "graph": {"status": "success", "duration_ms": 156, "results": 6},
    "procedural": {"status": "success", "duration_ms": 173, "results": 7}
  },

  "source_findings": {
    "semantic": {
      "key_findings": ["JWT implementation", "OAuth 2.0 migration", "Token validation"],
      "confidence": 0.88
    },
    "episodic": {
      "timeline": [
        {"date": "2025-06-15", "event": "JWT implementation"},
        {"date": "2025-09-20", "event": "OAuth 2.0 pilot"},
        {"date": "2025-11-10", "event": "Full migration complete"}
      ],
      "confidence": 0.94
    },
    "graph": {
      "components": ["AuthenticationManager", "TokenValidator", "SecurityPolicy"],
      "relationships": 8,
      "confidence": 0.91
    },
    "procedural": {
      "procedures": ["token_generation", "token_validation", "refresh_handling"],
      "success_rate": 0.92
    }
  },

  "synthesized_findings": {
    "narrative": "System evolved from JWT-based tokens (June 2025) to OAuth 2.0 (Sept-Nov 2025), improving security posture and interoperability.",
    "confidence": 0.90,
    "supported_by_sources": ["semantic", "episodic", "graph"],
    "contradictions_found": 0,
    "agreement_ratio": 0.95
  },

  "evidence_chain": [
    {
      "claim": "JWT implementation was completed in June 2025",
      "sources": ["episodic", "semantic"],
      "confidence": 0.94,
      "strength": "strong"
    },
    {
      "claim": "OAuth 2.0 migration improved security",
      "sources": ["graph", "procedural"],
      "confidence": 0.86,
      "strength": "moderate"
    }
  ],

  "credibility_assessment": {
    "semantic_credibility": 0.88,
    "episodic_credibility": 0.94,
    "graph_credibility": 0.91,
    "procedural_credibility": 0.92,
    "overall_credibility": 0.91
  },

  "gaps_identified": [
    {
      "gap": "OAuth 2.0 performance impact not documented",
      "source_agreement": ["semantic", "graph"],
      "priority": "medium",
      "follow_up_needed": true
    },
    {
      "gap": "Security threat model for new approach",
      "source_agreement": ["semantic"],
      "priority": "high",
      "follow_up_needed": true
    }
  ],

  "stored_results": {
    "status": "success",
    "findings_stored": 3,
    "cross_references": 8,
    "metadata": {
      "research_id": "research_2025_11_12_001",
      "timestamp": "2025-11-12T10:15:00Z",
      "sources": ["semantic", "episodic", "graph", "procedural"],
      "confidence": 0.90
    }
  },

  "recommendations": [
    "Document OAuth 2.0 performance impact (HIGH priority gap)",
    "Verify security threat model with security team",
    "Create procedures for token refresh handling",
    "Monitor token revocation compliance"
  ],

  "follow_up_research": [
    {"question": "What is the security threat model for OAuth 2.0?", "priority": "high"},
    {"question": "What are performance benchmarks for token validation?", "priority": "medium"},
    {"question": "How do we handle token revocation?", "priority": "medium"}
  ],

  "note": "Call adapter.get_detail('research', 'finding', 'research_2025_11_12_001') for full details"
}
```

## Research Orchestration Pattern

### Parallel Investigation Flow
```
┌──────────────────┐
│  Research Q      │
└─────────┬────────┘
          │
┌─────────▼──────────────┐
│ Decompose into Aspects │
└─────────┬──────────────┘
          │
┌─────────▼─────────────────────────────────────┐
│ Parallel Source Investigation                 │
├──────┬───────────┬──────────┬─────────────────┤
│Semantic│Episodic │ Graph    │ Procedural      │
│(145ms) │ (178ms) │ (156ms)  │ (173ms)         │
│Results │ Results │ Results  │ Results         │
│  12    │    8    │    6     │    7            │
├──────┴───────────┴──────────┴─────────────────┤
│                Meta-Analysis                  │
│ - Credibility assessment                      │
│ - Consensus scoring                           │
│ - Contradiction detection                     │
└─────────┬──────────────────────────────────────┘
          │
┌─────────▼─────────────────┐
│ Synthesize Findings       │
│ - Narrative synthesis     │
│ - Evidence chains         │
│ - Gap identification      │
└─────────┬─────────────────┘
          │
┌─────────▼─────────────────┐
│ Store to Memory           │
│ - With provenance         │
│ - With confidence         │
│ - Enable future retrieval │
└───────────────────────────┘
```

## Token Efficiency
Old: 250K+ tokens | New: <600 tokens | **Savings: 99%**

## Examples

### Basic Research Coordination

```python
# Execute research coordination
result = adapter.execute_operation(
    "research",
    "coordinate",
    {
        "question": "How has authentication evolved?",
        "all_sources": True,
        "store_results": True
    }
)

# Check synthesis confidence
print(f"Confidence: {result['synthesized_findings']['confidence']:.2f}")
print(f"Agreement: {result['synthesized_findings']['agreement_ratio']:.1%}")

# Review findings by source
for source, findings in result['source_findings'].items():
    print(f"{source}: {findings['key_findings']}")
```

### Contradiction Detection

```python
# Get research with contradiction analysis
result = adapter.execute_operation(
    "research",
    "coordinate",
    {"question": "...", "detect_contradictions": True}
)

if result['synthesized_findings']['contradictions_found'] > 0:
    print("⚠️ Contradictions detected - manual review needed")
```

### Gap Analysis

```python
# Identify research gaps
result = adapter.execute_operation(
    "research",
    "coordinate",
    {"question": "...", "identify_gaps": True}
)

for gap in result['gaps_identified']:
    if gap['priority'] == 'high':
        print(f"HIGH PRIORITY GAP: {gap['gap']}")
```

### Follow-up Planning

```python
# Get follow-up research recommendations
result = adapter.execute_operation(
    "research",
    "coordinate",
    {"question": "...", "plan_follow_up": True}
)

for follow_up in result['follow_up_research']:
    print(f"{follow_up['priority']}: {follow_up['question']}")
```

## Implementation Notes

Demonstrates filesystem API paradigm for research orchestration. This agent:
- Discovers research sources via filesystem
- Decomposes complex questions into sub-queries
- Executes parallel research across layers
- Returns only summary metrics (source counts, confidence, gaps)
- Supports drill-down for full findings via `adapter.get_detail()`
- Assesses source credibility and recency
- Synthesizes coherent narratives from parallel findings
- Identifies and resolves contradictions
- Stores researched knowledge back to memory with provenance
- Plans follow-up research autonomously
