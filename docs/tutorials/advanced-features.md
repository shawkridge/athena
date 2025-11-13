# Advanced Features Guide

Advanced usage patterns, optimization techniques, and expert workflows.

**Prerequisites**: Complete [getting-started.md](./getting-started.md) and [memory-basics.md](./memory-basics.md) first.

## Table of Contents

- [Knowledge Graph Operations](#knowledge-graph-operations)
- [Advanced RAG Strategies](#advanced-rag-strategies)
- [Query Optimization](#query-optimization)
- [Consolidation Strategies](#consolidation-strategies)
- [Performance Tuning](#performance-tuning)
- [Working Memory Management](#working-memory-management)

---

## Knowledge Graph Operations

### Building Entity Relationships

Create rich semantic networks:

```python
from athena.graph.store import GraphStore
from athena.graph.models import Entity, Relation

graph = GraphStore(db)

# Create entities
python = graph.create_entity(
    name="Python",
    type="language",
    metadata={"version": "3.10", "year_created": 2000},
)

concurrency = graph.create_entity(
    name="Concurrency",
    type="concept",
)

# Create relationship
graph.create_relation(
    source_id=python,
    target_id=concurrency,
    relation_type="supports",
    strength=0.85,  # 0-1, how strong the relationship
)
```

### Community Detection

Find natural groupings:

```python
# Detect communities in knowledge graph
communities = graph.detect_communities(
    algorithm="leiden",  # Leiden algorithm
    resolution=1.0,      # 0.5 = fewer communities, 2.0 = more
)

# Analyze communities
for community in communities:
    print(f"Community {community.id}:")
    for entity in community.entities:
        print(f"  - {entity.name}")
```

### Knowledge Graph Queries

```python
# Find neighbors (related entities)
related = graph.get_neighbors(entity_id=python, max_distance=2)

# Find paths between entities
path = graph.shortest_path(source_id=python, target_id=concurrency)

# Get entity observations (contextual info)
observations = graph.get_observations(entity_id=python)
```

---

## Advanced RAG Strategies

### HyDE (Hypothetical Document Embeddings)

Generate hypothetical answers first, then search:

```python
from athena.rag.hyde import HyDERetriever

hyde = HyDERetriever(db)

# Query generates hypothetical documents first
results = hyde.retrieve(
    query="How to implement thread-safe singleton?",
    num_hypothetical=3,  # Generate 3 hypotheticals
    top_k=5,
)
```

### Reranking

Re-score search results for better relevance:

```python
from athena.rag.reranker import Reranker

reranker = Reranker(db)

# Initial search
initial_results = semantic_store.search("threading", limit=20)

# Rerank for better relevance
reranked = reranker.rerank(
    query="Python threading GIL impact",
    candidates=initial_results,
    top_k=5,  # Return top 5 after reranking
)
```

### Reflective Search

Self-improve queries iteratively:

```python
from athena.rag.reflective import ReflectiveRetriever

reflective = ReflectiveRetriever(db)

# Search reflects on initial results and refines query
results = reflective.retrieve(
    query="debugging concurrency issues",
    iterations=2,  # Self-refine 2 times
    top_k=5,
)
```

### Query Transformation

Expand or rephrase queries:

```python
from athena.rag.query_transformer import QueryTransformer

transformer = QueryTransformer(db)

# Transform improves query
original = "Python threading"
transformed = transformer.transform(
    original,
    strategy="expand",  # or "rephrase", "summarize"
)
print(f"Original: {original}")
print(f"Transformed: {transformed}")

# Search with both
results = semantic_store.search(transformed, limit=10)
```

---

## Query Optimization

### Hybrid Semantic + Keyword Search

Combine vector and BM25 for best results:

```python
# Search both semantic and keyword
semantic_results = semantic_store.vector_search("threading", limit=100)
keyword_results = semantic_store.bm25_search("threading", limit=100)

# Combine with weighting
combined = merge_results(
    semantic_results,
    keyword_results,
    semantic_weight=0.7,
    keyword_weight=0.3,
)

# Deduplicate and return top-k
final = combined[:10]
```

### Domain-Specific Search

```python
# Search within specific domain
python_memories = semantic_store.search(
    query="concurrency",
    domain="python_concurrency",  # Restrict to domain
    limit=10,
)
```

### Temporal Search

```python
# Search events from specific time range
from datetime import datetime, timedelta

week_ago = datetime.now() - timedelta(days=7)
recent_events = episodic_store.search_by_time(
    since=week_ago,
    until=datetime.now(),
    tags=["learning"],
)
```

---

## Consolidation Strategies

### Custom Consolidation

Control how consolidation happens:

```python
from athena.consolidation.consolidator import Consolidator

consolidator = Consolidator(db)

# Consolidate with specific strategy
patterns = consolidator.consolidate(
    strategy="quality",        # balanced, speed, or quality
    days_back=14,             # Only recent events
    min_cluster_size=2,       # Minimum events to form pattern
    validation_threshold=0.7, # Confidence needed
)
```

### Selective Consolidation

```python
# Consolidate specific tags only
tagged_patterns = consolidator.consolidate_by_tags(
    tags=["bug-fix", "performance"],
    strategy="quality",
)
```

### Incremental Consolidation

```python
# Consolidate only new events since last run
incremental = consolidator.consolidate_incremental(
    since_last_consolidation=True,
)
```

---

## Performance Tuning

### Vector Cache

Cache common semantic searches:

```python
from athena.semantic.cache import SearchCache

cache = SearchCache(max_size=1000)

# Cached search
results = cache.search("threading", limit=10, ttl=3600)  # 1 hour TTL
```

### Index Optimization

```python
# Rebuild BM25 index for better search speed
semantic_store.optimize_indexes()

# Analyze query performance
plan = semantic_store.analyze_query("threading")
print(f"Query plan: {plan}")
```

### Batch Operations

```python
# Bulk insert events more efficiently
events = [create_event() for _ in range(1000)]

episodic_store.bulk_insert(
    events,
    batch_size=100,  # Commit every 100
)
```

---

## Working Memory Management

### 7±2 Cognitive Limit

Athena enforces Baddeley's working memory limit:

```python
from athena.episodic.buffer import WorkingMemoryBuffer

buffer = WorkingMemoryBuffer(max_items=7)

# Add items (discards oldest if over limit)
for event in recent_events:
    buffer.add(event)

# Retrieve focus items
focus_items = buffer.get_items()  # At most 7
```

### Attention Salience

Mark important memories for recall:

```python
# Update attention weight (0-1)
semantic_store.update_attention(
    memory_id=123,
    salience=0.95,  # Very important
)

# Retrieve high-salience memories
important = semantic_store.get_salient_memories(
    min_salience=0.8,
    limit=7,
)
```

### Context Window Management

```python
# Get working memory snapshot
context = buffer.get_context_window(
    max_tokens=2000,  # Respect token limits
)

print(f"Current context: {len(context)} items")
```

---

## Expert Patterns

### Pattern 1: Learn-Consolidate-Refine Cycle

```python
# 1. Record experiences
for event in daily_events:
    episodic_store.store_event(event)

# 2. Consolidate at day end
patterns = consolidator.consolidate(strategy="quality")

# 3. Review and rate memories
for memory in patterns:
    usefulness = rate_memory(memory)
    semantic_store.update_importance(memory.id, usefulness)

# 4. Extract procedures from successful patterns
procedures = procedural_store.extract_from_patterns(patterns)
```

### Pattern 2: Goal-Driven Learning

```python
# 1. Create goal
goal = goal_store.create_goal("Master distributed systems")

# 2. Track progress with tasks
for topic in ["consensus", "RPC", "state-machines"]:
    task = task_store.create_task(
        title=f"Study {topic}",
        goal_id=goal.id,
    )

# 3. Link learning to goal
for memory in learned_memories:
    semantic_store.link_to_goal(memory.id, goal.id)

# 4. Track progress
progress = goal_store.get_progress(goal.id)
```

### Pattern 3: Knowledge Graph Inference

```python
# 1. Build graph from memories
for memory in semantic_memories:
    entities = extract_entities(memory.content)
    for entity in entities:
        graph.create_entity(entity.name, entity.type)

# 2. Find communities
communities = graph.detect_communities()

# 3. Use communities for better search
for community in communities:
    community_memories = semantic_store.search(
        query=query,
        entities=community.entities,
    )
```

---

## Troubleshooting Advanced Features

### Slow Consolidation

```python
# Profile consolidation
with consolidator.profile():
    patterns = consolidator.consolidate()

# Use speed strategy instead of quality
patterns = consolidator.consolidate(strategy="speed")
```

### Low Quality RAG Results

```python
# Try different strategies
strategies = ["hyde", "reranking", "reflective"]

for strategy in strategies:
    results = rag.retrieve(query, strategy=strategy, limit=3)
    quality = evaluate_results(results)
    print(f"{strategy}: {quality}")
```

### Memory Leaks

```python
# Check cache usage
cache.stats()  # Shows hit rate, size, etc.

# Clear old cache entries
cache.cleanup(ttl=3600)

# Monitor growth
db.analyze_table_sizes()
```

---

## Next Steps

- Explore [memory-basics.md](./memory-basics.md) for layer details
- Check [ARCHITECTURE.md](../ARCHITECTURE.md) for internals
- See [TESTING_GUIDE.md](../TESTING_GUIDE.md) for testing advanced features
- Read [API_REFERENCE.md](../API_REFERENCE.md) for complete API

---

**Questions?** See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) or check the [API_REFERENCE.md](../API_REFERENCE.md).
