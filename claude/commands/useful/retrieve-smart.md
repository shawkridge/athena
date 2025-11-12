---
description: Advanced semantic search with filesystem API (4 RAG strategies) - executes locally, returns summaries
argument-hint: "Search query (supports complex boolean and semantic queries)"
---

# Retrieve Smart (Filesystem API Edition)

Advanced semantic search with 4 intelligent RAG strategies for high-precision retrieval using filesystem API paradigm.

Usage: `/retrieve-smart "complex search query"`

## How It Works

### Step 1: Discover RAG Operations
- List available RAG strategy implementations
- Discover which strategies are available (HyDE, reranking, etc.)
- Progressive disclosure of RAG operations

### Step 2: Analyze Query
- Categorize query type (ambiguous, contextual, temporal, standard)
- Auto-select optimal strategy based on query characteristics
- Prepare query transformation if needed

### Step 3: Execute Search
- Read selected strategy code
- Execute search locally in sandbox
- All ranking, filtering, aggregation happens here
- No full data in context

### Step 4: Return Summary
- Return ranked IDs with relevance scores
- Return strategy explanation
- Return suggested follow-up queries
- Never return full memory objects

## 4 RAG Strategies (Auto-Selected)

1. **HyDE** (Hypothetical Document Embeddings)
   - Use: Ambiguous or short queries (<5 words)
   - Example: `/retrieve-smart "JWT tokens"`
   - Execution: Generates hypothetical docs locally, embeds, ranks

2. **LLM Reranking**
   - Use: Standard searches requiring precision
   - Example: `/retrieve-smart "how do we handle authentication refresh tokens"`
   - Execution: Initial search, LLM reranks locally, returns top-K

3. **Query Transformation**
   - Use: References to context (it, that, those, which)
   - Example: `/retrieve-smart "what else did we learn from that approach"`
   - Execution: Transforms query locally, executes search, returns results

4. **Reflective Retrieval**
   - Use: Temporal patterns and causality
   - Example: `/retrieve-smart "what changed in our auth approach over time"`
   - Execution: Temporal analysis, causality inference, returns temporal summaries

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 287,

  "query": "JWT token expiration strategies",
  "strategy_selected": "LLM Reranking",
  "strategy_reasoning": "Standard precision search query with multiple contextual keywords",

  "total_results": 18,
  "high_confidence_results": 12,

  "top_10_results": [
    {"id": 42, "type": "procedure", "title": "JWT-Token-Management", "relevance": 0.95},
    {"id": 8, "type": "semantic", "title": "Token Expiration Strategies", "relevance": 0.88},
    {"id": 156, "type": "graph", "title": "TokenExpiration", "relevance": 0.82}
  ],

  "by_layer": {
    "procedural": 4,
    "semantic": 8,
    "graph": 5,
    "episodic": 1
  },

  "related_concepts": ["AccessControl", "SecurityPolicy", "SessionManagement"],

  "suggested_follow_ups": [
    "How do we handle refresh token rotation?",
    "What's our token revocation strategy?",
    "How does this compare to other approaches over time?"
  ],

  "note": "Use adapter.get_detail(layer, 'memory', id) to see full details for specific results"
}
```

## Token Efficiency

**Old Pattern**:
- Load 4 RAG strategy definitions: 150K tokens
- Return full search results with context: 50K tokens
- Process in model context: 15K tokens
- **Total: 215K+ tokens**

**New Pattern (Filesystem API)**:
- Discover RAG operations: 100 tokens
- Execute search locally: 0 tokens (sandbox)
- Return summary: 300 tokens
- **Total: <400 tokens**

**Savings: 99%+ token reduction** 🎯

## Features

- **Auto-Strategy Selection**: Analyzes query, selects optimal strategy locally
- **Ranked Summaries**: Returns IDs and scores (not full objects)
- **Multi-Layer Search**: Searches episodic, semantic, procedural, graph
- **Context Preservation**: Maintains relationship context in summaries
- **Explanation**: Shows strategy selection and reasoning

## Implementation Notes

The rag-specialist agent uses this by:
1. Discovering available RAG strategies
2. Analyzing query characteristics
3. Selecting strategy and executing locally
4. Analyzing summary results
5. Calling `get_detail()` only for specific result IDs if full content needed

This keeps advanced retrieval token-efficient while maintaining precision and flexibility.
