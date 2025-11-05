---
category: skill
description: Automatically select optimal retrieval strategy based on query characteristics
trigger: Model has ambiguous query or needs memory search, or user runs /memory-query
confidence: 0.94
---

# Query Strategist Skill

This skill intelligently selects the best retrieval strategy (HyDE, LLM reranking, query transformation, reflective) based on query characteristics.

## When I Invoke This

I detect:
- Short/ambiguous queries (<5 words or vague)
- Queries with pronouns ("it", "that", "those") requiring context
- Complex multi-part queries with multiple "?" or "and"
- User runs `/memory-query` command
- I need to search across multiple memory layers

## What I Do

```
1. Analyze query characteristics
   → Length: count words
   → Ambiguity: check for vague terms
   → References: detect pronouns
   → Complexity: count conjunctions
   → Context: check conversation history

2. Select strategy
   → If ambiguous: Use HyDE (hypothetical examples)
   → If references: Use Query Transform (resolve context)
   → If complex: Use Reflective (iterative refinement)
   → If standard: Use LLM Reranking (semantic + relevance)

3. Execute retrieval
   → Call: smart_retrieve() with selected strategy
   → Search all memory layers:
     - Semantic: vector + BM25 hybrid
     - Episodic: temporal events
     - Procedural: workflows and procedures
     - Knowledge graph: entities and relations
     - Prospective: tasks and triggers

4. Rank and present results
   → By relevance score
   → By memory type
   → By recency
   → Show: Content, ID, memory type, confidence
```

## MCP Tools Used

- `smart_retrieve` - Core retrieval with auto-strategy selection
- `recall` - Fallback basic vector search
- `recall_events` - Search temporal events
- `search_graph` - Query knowledge graph
- `search_projects` - Cross-project search
- `record_execution` - Track strategy used

## Retrieval Strategies

| Query Type | Strategy | Why |
|-----------|----------|-----|
| Short/ambiguous | HyDE | Hypothetical examples bridge meaning |
| With references | Transform | Resolves "it", "that" from context |
| Complex/multi-part | Reflective | Iterative refinement for clarity |
| Standard queries | LLM Reranking | 70% vector + 30% semantic relevance |

## Example Invocation

```
You: /memory-query "authentication patterns"

Query Strategist analyzing...
→ Query characteristics: Standard (clear, single-topic)
→ Strategy selected: LLM Reranking
→ Search layers: semantic, procedural, episodic

Results (ranked by relevance):
  1. JWT Implementation Pattern (score: 0.98, ID: 456)
  2. OAuth2 Design Decision (score: 0.91, ID: 789)
  3. Error Handling Strategy (score: 0.87, ID: 123)

Next: /memory-query "ID:456" for details
```

## Success Criteria

✓ Correct strategy selected
✓ All relevant results retrieved
✓ Results ranked by relevance
✓ Strategy appropriate to query type

## Related Commands

- `/memory-query` - User-triggered search
- `/memory-health` - Query effectiveness analysis

