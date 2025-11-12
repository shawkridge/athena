---
description: Find and recall information from memory using smart retrieval (filesystem API paradigm) - discovers operations, executes locally, returns summaries
argument-hint: "Search query or pattern to find"
---

# Memory Search (Filesystem API Edition)

Search memory across all layers using the filesystem API paradigm: discover operations, read code, execute locally, return summaries.

Usage: `/memory-search "your search query"`

## How It Works (Filesystem API Paradigm)

This command implements the modern code execution pattern:

### Step 1: Discover
- Use filesystem API to discover available search operations
- List semantic, episodic, procedural, graph layers
- Progressive disclosure (don't load all definitions upfront)

### Step 2: Read
- Read operation code to understand what it does
- Understand parameters and return types
- Know exactly what will execute

### Step 3: Execute
- Execute search operation locally (in sandbox)
- All filtering, ranking, aggregation happens here (not in context)
- Only summary returns to context

### Step 4: Analyze
- Make decisions based on summary metrics
- Review top result IDs and relevance scores
- Drill down into specific results only if needed

## Features

- **Smart RAG Strategy**: Automatically selects optimal strategy based on query
  - HyDE for ambiguous short queries (<5 words)
  - LLM Reranking for standard precision searches
  - Query Transformation for contextual references
  - Reflective Retrieval for temporal patterns

- **Multi-Layer Discovery**: Discovers across layers
  - Episodic: Events and temporal patterns
  - Semantic: Facts, insights, knowledge
  - Procedural: How-to procedures and workflows
  - Graph: Relationships and entities

- **Ranked Summaries**: Returns IDs and relevance scores (not full objects)

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 145,
  "query": "your search query",
  "total_results": 42,
  "high_confidence_count": 28,
  "top_5_ids": [1, 5, 12, 8, 3],
  "top_5_relevance": [0.95, 0.91, 0.88, 0.85, 0.82],
  "by_layer": {
    "semantic": 15,
    "episodic": 18,
    "procedural": 5,
    "graph": 4
  },
  "suggested_strategy": "LLM Reranking",
  "note": "To see full details, call adapter.get_detail() with memory IDs"
}
```

## Token Efficiency

**Before (Old Pattern)**:
- Load tool definitions: 150K tokens
- Return full memory objects: 50K tokens
- Process in context: 15K tokens
- **Total: 165K+ tokens**

**After (Filesystem API)**:
- Discover operations: 100 tokens
- Read code: 200 tokens
- Execute locally: 0 tokens (sandbox)
- Return summary: 300 tokens
- **Total: <300 tokens**

**Savings: 99.8% token reduction** 🎯

## Implementation Notes

The research-coordinator agent uses this command by:
1. Discovering what search operations are available
2. Reading the operation code to understand it
3. Executing the search locally with specific query
4. Analyzing the summary (counts, IDs, relevance scores)
5. Calling `get_detail()` only for specific IDs if needed

This keeps memory research token-efficient while maintaining full functionality.
