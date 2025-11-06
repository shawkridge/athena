---
name: semantic-search
description: |
  Advanced semantic search with 4 retrieval strategies for complex domain-specific queries.
  Use for searching where traditional keyword search fails, handling concept-level queries.
  Provides ranked results with confidence scores and strategy explanation.
---

# Semantic Search Skill

Advanced semantic search for complex, domain-specific information retrieval.

## When to Use

- Domain-specific searches requiring concept understanding
- Complex queries with multiple related ideas
- Searches where traditional keywords don't work well
- Finding information by meaning, not just keywords

## Strategies

1. **HyDE**: Ambiguous or short queries
2. **LLM Reranking**: Precision-focused searches
3. **Query Transformation**: Contextual and referential queries
4. **Reflective**: Temporal patterns and causality

## Returns

- Top results ranked by semantic relevance
- Confidence scores for each result
- Selected strategy and reasoning
- Related concepts and context
- Temporal information when applicable

## Examples

- "How do we approach security in our systems?"
- "What authentication strategies have we used?"
- "Tell me about our database design philosophy"

The semantic-search skill activates for concept-level queries requiring deep understanding.
