---
name: memory-management
description: |
  When you need to retrieve, store, or optimize memories using semantic search.
  When detecting knowledge gaps, tracking expertise, or managing cognitive load.
  When consolidation recommendations or memory quality improvements are needed.
---

# Memory Management Skill

Memory operations specialist for intelligent recall, storage, optimization, and knowledge gap detection.

## When to Use

- Need to search memories with semantic understanding
- Storing new knowledge with proper categorization
- Detecting areas where more knowledge is needed
- Tracking domain expertise
- Monitoring cognitive load
- Recommending memory consolidation
- Optimizing recall quality

## Core Responsibilities

### Memory Retrieval
- Finding and recalling stored memories using semantic search
- Using hybrid search (BM25 + vector) for best results
- Filtering by memory type and tags
- Prioritizing recent high-quality memories

### Memory Storage
- Storing new knowledge and patterns efficiently
- Validating memory content before storage
- Suggesting appropriate tags for categorization
- Calculating importance scores

### Memory Optimization
- Improving recall speed and quality through consolidation
- Detecting memory fragmentation
- Recommending cleanup and consolidation
- Managing memory lifecycle

### Knowledge Gap Detection
- Identifying areas where more knowledge is needed
- Tracking expertise distribution
- Suggesting learning priorities
- Monitoring knowledge coverage

## Tools Available

- **recall**: Search memories with semantic search
- **remember**: Store new knowledge
- **list_memories**: Browse all memories with filters
- **get_expertise**: Track domain expertise
- **detect_knowledge_gaps**: Find areas needing more knowledge

## Example Workflows

### Search for Domain-Specific Memories
1. Use recall() with domain-specific queries
2. Filter by memory_type if needed
3. Suggest related knowledge gaps

### Store New Learning
1. Evaluate content quality
2. Determine memory_type (fact, pattern, decision, context)
3. Suggest relevant tags
4. Calculate importance score
5. Store with remember()

## Quality Criteria

- **Accuracy** - Ensure retrieved memories are relevant
- **Completeness** - Check for gaps in knowledge
- **Freshness** - Prioritize recent high-quality memories
- **Relevance** - Match memories to user context

## Example Use Cases

### Semantic Search
"Recall memories about consolidation strategies"
→ Uses hybrid search, filters for procedural memories, ranks by relevance and freshness

### Knowledge Storage
"Remember new pattern: dual-process consolidation improves quality"
→ Validates content, tags with 'consolidation', 'pattern', 'quality', calculates importance, stores

### Gap Detection
"What knowledge gaps exist in our authentication domain?"
→ Analyzes expertise tracking, identifies weak coverage areas, suggests learning priorities

### Cognitive Load Management
"Check current working memory capacity"
→ Monitors 7±2 items in working memory, suggests consolidation if overloaded

## Best Practices

- Always validate memory content before storage
- Use semantic search for intelligent recall
- Recommend consolidation when memory becomes fragmented
- Suggest memory tags for better categorization
- Monitor cognitive load to prevent overload
- Track expertise to identify strengths and gaps

Use memory management for expert guidance on knowledge retrieval, storage, and optimization.
