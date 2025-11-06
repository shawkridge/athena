---
name: memory-retrieval
description: |
  Retrieve relevant information from memory using advanced RAG strategies.
  Use when you need to find similar past solutions, understand patterns, or recall previous implementations.
  Automatically selects optimal search strategy (HyDE for ambiguous queries, LLM reranking for precision).
  Provides ranked results with confidence scores and related concepts.
---

# Memory Retrieval Skill

## What This Skill Does

Retrieves relevant information from your memory system using intelligent search strategies.

## When to Use

- Finding similar past solutions or implementations
- Understanding recurring patterns in your work
- Recalling previous experiences or learnings
- Searching across multiple memory layers at once

## How It Works

**Automatic Strategy Selection**:
- **HyDE**: For ambiguous or short queries (<5 words)
- **LLM Reranking**: For standard precision searches
- **Query Transformation**: For contextual references
- **Reflective Retrieval**: For temporal patterns and causality

## What You Get

- Top 10 results ranked by relevance
- Confidence scores (0.0-1.0) per result
- Related concepts and connections
- Temporal context and relationships
- Suggested follow-up queries

## Examples

- "JWT token management patterns" → finds similar auth implementations
- "how do we handle database migrations" → finds migration procedures
- "performance optimization from last month" → temporal pattern search

## Best Results

- Be specific: "OAuth2 JWT implementation" vs. generic "authentication"
- Include context: "what did we learn from..." vs. "learning"
- Use technical terms relevant to your domain

The memory-retrieval skill is automatically invoked when searching memory across multiple layers.
