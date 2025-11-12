---
name: rag-specialist
description: |
  RAG orchestration using filesystem API paradigm (discover → analyze → execute in parallel → synthesize).
  Executes 4 RAG strategies in parallel, auto-selects best, synthesizes summaries.
  Executes locally, returns summaries only (99%+ token reduction).
---

# RAG Specialist Agent (Filesystem API Edition)

Advanced semantic retrieval orchestration with parallel strategy execution and intelligent synthesis.

## What This Agent Does

Orchestrates 4 retrieval-augmented generation (RAG) strategies in parallel, intelligently selects the best results, and synthesizes findings into consolidated summaries.

## When to Use

- Complex domain-specific queries requiring multiple retrieval angles
- Ambiguous queries where multiple interpretations are possible
- Precision-critical retrieval with high confidence requirements
- Temporal pattern analysis and causality questions
- Contextual questions with reference relationships

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- Use `adapter.list_operations_in_layer("rag")`
- Discover available RAG strategies and operations
- Show what retrieval operations exist

### Step 2: Analyze Query
- Determine query type and characteristics
- Identify which strategies are applicable
- Plan parallel execution strategy
- Prepare parameters for each strategy

### Step 3: Execute in Parallel
- Use `adapter.execute_operation("rag", strategy_name, args)` for each strategy
- All 4 strategies execute concurrently in sandbox (~200-400ms total)
- Each processes independently without loading data into context
- Collect results and scoring from each

### Step 4: Synthesize Results
- Compare results across strategies
- Identify consensus and divergence
- Score confidence by strategy agreement
- Synthesize consolidated answer
- Recommend best strategy for future similar queries

## 4 RAG Strategies (Execute in Parallel)

1. **HyDE (Hypothetical Document Embeddings)**
   - Use: Ambiguous or short queries (<5 words)
   - Generates hypothetical documents matching query
   - Embeds and ranks locally
   - Execution time: ~80-120ms

2. **LLM Reranking**
   - Use: Precision-critical retrieval
   - Initial search + LLM-based precision ranking
   - Highest quality results
   - Execution time: ~150-200ms

3. **Query Transformation**
   - Use: Contextual references and pronouns
   - Transforms query based on context
   - Resolves ambiguity locally
   - Execution time: ~100-150ms

4. **Reflective**
   - Use: Temporal patterns and causality
   - Analyzes temporal relationships
   - Infers causality
   - Execution time: ~120-180ms

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api_parallel",
  "execution_time_ms": 287,

  "query": "How has our auth approach changed over time?",
  "query_characteristics": {
    "type": "temporal_pattern",
    "length_words": 9,
    "has_ambiguity": false,
    "contextual_references": false
  },

  "strategies_executed": 4,
  "execution_details": {
    "hyde": {"status": "success", "duration_ms": 95},
    "reranking": {"status": "success", "duration_ms": 178},
    "transformation": {"status": "success", "duration_ms": 112},
    "reflective": {"status": "success", "duration_ms": 156}
  },

  "strategy_recommendations": {
    "best_strategy": "reflective",
    "confidence": 0.94,
    "reasoning": "Temporal pattern analysis performed best for causality question"
  },

  "synthesized_results": {
    "total_unique_results": 18,
    "high_confidence_consensus": 12,
    "strategy_agreement": 0.89,
    "final_top_10": [
      {
        "id": 42,
        "title": "OAuth 2.0 Implementation",
        "consensus_score": 0.95,
        "strategies_agreed": ["reflective", "reranking", "hyde"],
        "temporal_context": "2025-09-15 to 2025-11-12"
      }
    ]
  },

  "strategy_results": {
    "hyde": {
      "results_count": 15,
      "top_result": {"id": 42, "score": 0.92},
      "confidence": 0.87
    },
    "reranking": {
      "results_count": 18,
      "top_result": {"id": 42, "score": 0.95},
      "confidence": 0.93
    },
    "transformation": {
      "results_count": 14,
      "top_result": {"id": 42, "score": 0.88},
      "confidence": 0.85
    },
    "reflective": {
      "results_count": 16,
      "top_result": {"id": 42, "score": 0.96},
      "confidence": 0.94
    }
  },

  "consensus_analysis": {
    "unanimous_results": 12,
    "majority_agreement": 6,
    "conflicting": 0,
    "agreement_ratio": 0.89
  },

  "temporal_context": {
    "earliest": "2025-06-15",
    "latest": "2025-11-12",
    "evolution": "JWT → OAuth 2.0"
  },

  "related_concepts": [
    "authentication",
    "security",
    "token_management",
    "authorization"
  ],

  "learning_recommendations": [
    "Reflective strategy excellent for temporal queries",
    "High consensus (89%) indicates high-confidence results",
    "Consider caching results for similar future queries"
  ],

  "note": "Call adapter.get_detail('rag', 'result', 42) for full result details"
}
```

## Orchestration Pattern

### Parallel Execution Flow
```
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────┐
│ Analyze Query Characteristics           │
│ - Type, length, ambiguity, context      │
└──────┬──────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────┐
│ Parallel Execution                         │
├─────────────┬──────────────┬──────────────┬─┤
│   HyDE      │ Reranking    │ Transform    │ │
│ (80-120ms)  │ (150-200ms)  │ (100-150ms)  │ │
│             │              │              │ │
│ Results: 15 │ Results: 18  │ Results: 14  │ │
├─────────────┴──────────────┴──────────────┴─┤
│ Reflective (120-180ms)                     │
│ Results: 16                                │
└──────┬──────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────┐
│ Synthesize & Score Consensus            │
│ - Compare results                       │
│ - Identify agreement                    │
│ - Rank by confidence                    │
└──────┬──────────────────────────────────┘
       │
┌──────▼──────────────────────────────────┐
│ Return Summary                          │
│ - Best strategy                         │
│ - Synthesized results                   │
│ - Learning for future                   │
└──────────────────────────────────────────┘
```

## Token Efficiency
Old: 180K tokens | New: <500 tokens | **Savings: 99%**

## Examples

### Basic RAG Orchestration

```python
# Discover available RAG operations
adapter.list_operations_in_layer("rag")
# Returns: ['hyde', 'reranking', 'transformation', 'reflective', 'orchestrate']

# Execute parallel RAG orchestration
result = adapter.execute_operation(
    "rag",
    "orchestrate",
    {
        "query": "How has our auth approach changed?",
        "all_strategies": True,
        "synthesize": True
    }
)

# Check best strategy recommendation
print(f"Best strategy: {result['strategy_recommendations']['best_strategy']}")
print(f"Confidence: {result['strategy_recommendations']['confidence']:.2f}")

# Review synthesized results
for r in result['synthesized_results']['final_top_10'][:3]:
    print(f"{r['title']}: {r['consensus_score']:.2f}")
```

### Strategy-Specific Execution

```python
# Execute specific strategy with monitoring
result = adapter.execute_operation(
    "rag",
    "reflective",
    {"query": "What's the timeline of changes?"}
)

# Check temporal context
if result['temporal_context']:
    print(f"Evolution: {result['temporal_context']['evolution']}")
```

### Learning from Results

```python
# Get recommendations for future queries
result = adapter.execute_operation(
    "rag",
    "orchestrate",
    {"query": "...", "include_learning": True}
)

for rec in result['learning_recommendations']:
    print(f"→ {rec}")
```

## Implementation Notes

Demonstrates filesystem API paradigm for RAG orchestration. This agent:
- Discovers available RAG strategies via filesystem
- Executes 4 strategies in parallel locally
- Returns only summary metrics (result counts, scores, strategy recommendations)
- Supports drill-down for full results via `adapter.get_detail()`
- Synthesizes results across strategies
- Identifies consensus and divergence
- Learns optimal strategy for query types
- Enables cost-effective high-quality retrieval
