---
name: semantic-search
description: |
  Advanced semantic search using filesystem API paradigm (discover → read → execute → summarize).
  4 retrieval strategies for complex domain-specific queries.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Semantic Search Skill (Filesystem API Edition)

Advanced semantic search for complex, domain-specific information retrieval using local execution.

## When to Use

- Domain-specific searches requiring concept understanding
- Complex queries with multiple related ideas
- Searches where traditional keywords don't work well
- Finding information by meaning, not just keywords
- Precise retrieval with confidence scoring

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- Use `adapter.list_operations_in_layer("semantic")`
- Discover available search strategies
- Show what operations are available

### Step 2: Analyze Query
- Determine query type (ambiguous, contextual, temporal, standard)
- Auto-select optimal strategy
- Prepare transformation if needed

### Step 3: Execute Locally
- Use `adapter.execute_operation("semantic", strategy, args)`
- All search, ranking, filtering happens in sandbox
- No data loaded into context

### Step 4: Return Summary
- Top results: IDs, relevance scores, titles
- Strategy used and reasoning
- Related concepts (not full analysis)
- Temporal context if applicable

## 4 Retrieval Strategies (Auto-Selected)

1. **HyDE**: Hypothetical Document Embeddings
   - Use: Ambiguous or short queries (<5 words)
   - Example: "security approaches"
   - Execution: Generate hypothetical docs locally, embed, rank

2. **LLM Reranking**: Precision-focused retrieval
   - Use: Standard precision-required searches
   - Example: "How do we handle authentication refresh tokens?"
   - Execution: Initial search, LLM reranks locally

3. **Query Transformation**: Context-aware retrieval
   - Use: Contextual references (it, that, those, which)
   - Example: "What else did we learn from that approach?"
   - Execution: Transform query locally, execute search

4. **Reflective**: Temporal pattern retrieval
   - Use: Temporal patterns and causality
   - Example: "How has our auth approach changed over time?"
   - Execution: Temporal analysis, causality inference locally

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 145,

  "query": "security approaches",
  "strategy_selected": "HyDE",
  "strategy_reasoning": "Short ambiguous query, hypothetical docs helpful",

  "total_results": 24,
  "high_confidence_results": 18,

  "top_10": [
    {"id": 42, "title": "Security Framework", "relevance": 0.95},
    {"id": 8, "title": "Auth Patterns", "relevance": 0.91},
    {"id": 156, "title": "Encryption Strategy", "relevance": 0.88}
  ],

  "by_layer": {
    "semantic": 12,
    "procedural": 7,
    "graph": 5
  },

  "related_concepts": ["authentication", "encryption", "authorization"],

  "note": "Call adapter.get_detail('semantic', 'memory', id) for full details"
}
```

## Token Efficiency

**Old Pattern**:
- Load RAG strategy definitions: 150K tokens
- Execute search, return full results: 50K tokens
- Process in context: 15K tokens
- **Total: 215K+ tokens**

**New Pattern (Filesystem API)**:
- Discover strategies: 100 tokens
- Execute locally: 0 tokens (sandbox)
- Return summary: 300 tokens
- **Total: <400 tokens**

**Savings: 99% token reduction** 🎯

## Usage Examples

### Example 1: Simple Semantic Search
```python
from filesystem_api_adapter import FilesystemAPIAdapter

adapter = FilesystemAPIAdapter()

# Discover available search operations
ops = adapter.list_operations_in_layer("semantic")

# Execute search locally
result = adapter.execute_operation("semantic", "search", {
    "query": "security approaches",
    "strategy": "auto"  # Auto-select optimal strategy
})

# Analyze summary
summary = result.get("result", {})
print(f"Found {summary['total_results']} results")
print(f"Top IDs: {summary['top_10']}")
```

### Example 2: Temporal Pattern Search
```python
# Search for temporal patterns
result = adapter.execute_operation("semantic", "search", {
    "query": "how has authentication changed over time?",
    "strategy": "reflective"
})

# Returns temporal analysis, not full history
temporal_summary = result.get("result", {})
print(f"Identified {len(temporal_summary['patterns'])} patterns")
```

## Implementation Notes

This skill demonstrates the filesystem API paradigm:
1. **Progressive Discovery**: Discover what's available first
2. **Local Execution**: All operations run in sandbox
3. **Summary Returns**: Metrics and IDs, never full objects
4. **Graceful Degradation**: Fallback to simpler strategies if needed

The skill activates for concept-level queries requiring deep understanding,
and now executes with 99% fewer tokens than before.
