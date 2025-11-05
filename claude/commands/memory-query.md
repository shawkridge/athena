---
description: Query all memory layers with Advanced RAG and intelligent strategy selection
group: Query & Search
aliases: ["/recall", "/search", "/find"]
---

# /memory-query

Advanced semantic memory search across all layers with automatic strategy selection (HyDE, LLM reranking, query transformation, reflective retrieval).

## Usage

```bash
/memory-query "your search query"
/memory-query "your query" --k 10 --type fact    # Filter by memory type
/memory-query "your query" --project ecommerce   # Search specific project
```

## What It Does

Searches semantic memory (vectors + BM25), episodic timeline, procedural workflows, knowledge graph, and prospective tasks using Advanced RAG that:

- **Auto-selects strategy**: HyDE for ambiguous queries, Query Transform for references, LLM Reranking for standard queries
- **Multi-layer retrieval**: Searches facts, patterns, decisions, events, procedures, tasks, entities
- **Context-aware**: Uses conversation history and files for better results
- **Fast**: <2 seconds for typical queries

## Examples

```bash
# Search all memory
/memory-query "JWT implementation patterns"
→ Returns: memories from semantic, episodic, procedural layers
→ Shows: Memory IDs for deep dives, related tasks, relevant events

# Search specific type
/memory-query "authentication" --type pattern
→ Returns only: Coding patterns, common approaches

# Search project memory
/memory-query "API design decisions" --project ecommerce
→ Returns: Decisions made in ecommerce project only

# Combine with other commands
/memory-query "phase 1 progress" --type fact
→ Use with: /project-status for full overview
```

## Advanced Usage

### Memory Types
- `fact`: Concrete information (e.g., "Bayesian Surprise handles 10M tokens")
- `pattern`: Coding conventions and techniques
- `decision`: Architectural choices and rationales
- `context`: Project state and progress

### Query Strategies (Automatic)
Query strategist automatically selects:
- **HyDE**: Short/ambiguous queries → Hypothetical examples bridge meaning gap
- **Query Transform**: References ("it", "that") → Resolved via conversation history
- **LLM Reranking**: Standard queries → 70% vector + 30% semantic relevance
- **Reflective**: Multiple "?" or complex queries → Iterative refinement

### Integration

Works with:
- `/project-status` - See tasks related to found memories
- `/consolidate` - Extract patterns from memories
- `/focus` - Load found memories into working memory
- `/memory-health` - Analyze domain coverage for searches

## Related Tools

- `smart_retrieve` - Core retrieval engine (Advanced RAG)
- `recall` - Basic vector search (faster, less accurate)
- `recall_events` - Search temporal events
- `search_projects` - Find memories across projects
- `search_graph` - Query knowledge graph relationships

## Tips

1. **Be specific**: "JWT token signing in Node.js" better than "auth stuff"
2. **Use memory types**: Filter by fact/pattern/decision for focused results
3. **Ask follow-ups**: Chat continues context, so "/memory-query related" builds on previous search
4. **Check project**: Use --project to narrow scope in multi-project repos
5. **Review IDs**: Each result shows memory ID for `/memory-query ID:123` deep dive

## See Also

- `/project-status` - Explore tasks and goals
- `/consolidate` - Extract learnings from memories
- `/workflow` - Find related procedures
- `/connections` - Explore memory associations

