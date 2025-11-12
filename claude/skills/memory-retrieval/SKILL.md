---
name: memory-retrieval
description: |
  Retrieve relevant information from memory using filesystem API (discover → execute → summarize).
  Advanced RAG strategies with automatic strategy selection.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Memory Retrieval Skill (Filesystem API Edition)

## What This Skill Does

Retrieves relevant information from memory using local execution with intelligent search strategies.

## When to Use

- Finding similar past solutions or implementations
- Understanding recurring patterns in your work
- Recalling previous experiences or learnings
- Searching across multiple memory layers at once

## How It Works (Filesystem API Paradigm)

### Step 1: Discover Operations
- Use `adapter.list_operations_in_layer()` across relevant layers
- Discover available memory operations
- Progressive disclosure

### Step 2: Analyze Query & Select Strategy
- Categorize query type
- Auto-select optimal strategy locally:
  - **HyDE**: Ambiguous or short queries (<5 words)
  - **LLM Reranking**: Standard precision searches
  - **Query Transformation**: Contextual references
  - **Reflective Retrieval**: Temporal patterns

### Step 3: Execute Locally
- Use `adapter.execute_operation()` with selected strategy
- All search happens in sandbox
- No data loaded into context

### Step 4: Return Summary
- Top 10 IDs with relevance scores
- Strategy used and reasoning
- Related concepts (not full analysis)
- Suggested follow-ups

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 156,

  "query": "JWT token management patterns",
  "strategy_selected": "LLM Reranking",
  "reasoning": "Specific technical query requires precision",

  "total_results": 18,
  "high_confidence_results": 14,

  "top_10": [
    {"id": 42, "layer": "procedural", "title": "JWT-Token-Management", "relevance": 0.97},
    {"id": 8, "layer": "semantic", "title": "Token Expiration Strategies", "relevance": 0.93},
    {"id": 156, "layer": "graph", "title": "TokenExpiration", "relevance": 0.89}
  ],

  "by_layer": {
    "procedural": 7,
    "semantic": 8,
    "episodic": 2,
    "graph": 1
  },

  "related_concepts": ["OAuth2", "SecurityPolicy", "SessionManagement"],

  "suggested_follow_ups": [
    "How do we handle token rotation?",
    "What's our refresh token strategy?",
    "How does this compare to session-based auth?"
  ],

  "note": "Call adapter.get_detail(layer, 'memory', id) for full details"
}
```

## Token Efficiency

**Old Pattern**:
- Load all search strategies: 150K tokens
- Execute search + return results: 50K tokens
- Process in context: 15K tokens
- **Total: 215K+ tokens**

**New Pattern (Filesystem API)**:
- Discover strategies: 100 tokens
- Execute locally: 0 tokens (sandbox)
- Return summary: 300 tokens
- **Total: <400 tokens**

**Savings: 99% token reduction** 🎯

## Examples

### Example 1: Find Similar Solutions
```python
from filesystem_api_adapter import FilesystemAPIAdapter

adapter = FilesystemAPIAdapter()

# Discover operations across layers
layers = adapter.list_layers()

# Execute memory retrieval (auto-strategy selection)
result = adapter.execute_operation("semantic", "search", {
    "query": "JWT token management patterns",
    "limit": 10
})

# Get summary with IDs and scores
summary = result.get("result", {})
print(f"Found {summary['total_results']} results")
print(f"Top 10 IDs: {[r['id'] for r in summary['top_10']]}")
```

### Example 2: Temporal Pattern Search
```python
# Search for temporal patterns
result = adapter.execute_operation("semantic", "search", {
    "query": "how has our database approach changed?",
    "strategy": "reflective"
})

# Returns temporal analysis without full history
temporal_summary = result.get("result", {})
print(f"Evolution: {temporal_summary['temporal_trend']}")
```

## Best Practices

- **Be specific**: "OAuth2 JWT implementation" vs. generic "authentication"
- **Include context**: "what did we learn from..." vs. "learning"
- **Use technical terms** relevant to your domain
- **For follow-ups**: Use suggested_follow_ups from results

## Implementation Notes

This skill demonstrates filesystem API paradigm:
1. **Discovers** what operations are available across layers
2. **Executes** locally with auto-selected strategy
3. **Returns** summary with IDs, scores, concepts
4. **Provides** drill-down via `get_detail()` for full content

The skill is automatically invoked when searching memory across multiple layers,
and now executes with 99% fewer tokens than before.
