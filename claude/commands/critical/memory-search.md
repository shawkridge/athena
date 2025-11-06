---
description: Find and recall information from memory using smart retrieval - searches episodic events, semantic knowledge, and procedures
argument-hint: "Search query or pattern to find"
---

# Memory Search

Search memory across all layers using smart retrieval to find relevant information, past solutions, or related patterns.

Usage: `/memory-search "your search query"`

Features:
- **Smart RAG Strategy**: Automatically selects optimal retrieval strategy
  - HyDE (Hypothetical Documents) for ambiguous short queries (<5 words)
  - LLM Reranking for high-precision results
  - Query Transformation for contextual references
  - Reflective Retrieval for temporal patterns

- **Multi-Layer Search**: Searches across
  - Episodic events (what happened, when)
  - Semantic knowledge (facts, patterns, insights)
  - Procedural memory (how to do things)
  - Knowledge graph (relationships, entities)

- **Ranked Results**: Returns findings ranked by relevance with confidence scores

Returns:
- Top 5-10 matching memories with context
- Related memories and connections
- Similar past solutions or patterns
- Confidence scores for each result

The research-coordinator agent may invoke this autonomously for complex research tasks.
