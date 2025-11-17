---
name: athena-semantic
description: >
  Search semantic memory: find facts, search knowledge, learn new information.
  Access learned facts and explore your knowledge base.

  Use when: "what do I know", "facts", "search knowledge", "define", "explain concept"
---

# Athena Semantic Memory Skill

Search your learned facts and knowledge base. Find definitions, understand concepts, store new learnings.

## What This Skill Does

- **Semantic Search**: Find facts by meaning
- **Knowledge Lookup**: Find definitions and concepts
- **Learn Fact**: Store new knowledge
- **Similarity**: Compare concepts

## When to Use

- **"What do I know about..."** - Search knowledge
- **"Define this concept"** - Look up definition
- **"Learn this fact"** - Store knowledge
- **"Are these similar?"** - Compare concepts

## Available Tools

### semanticSearch(query, limit)
Search semantic memory by meaning.

### learnFact(content, tags)
Store new fact in memory.

### querySimilarity(concept1, concept2)
Compare similarity between concepts.

## Architecture

Integrates with Athena's Layer 2 (Semantic Memory):
- 50,000+ learned facts
- Vector + BM25 hybrid search
- Concept similarity analysis
