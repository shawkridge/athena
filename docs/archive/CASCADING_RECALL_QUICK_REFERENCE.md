# Cascading Recall - Quick Reference Guide

## File Locations

| Component | File | Lines |
|-----------|------|-------|
| Main recall() | `/src/athena/manager.py` | 751-863 |
| Tier 1 logic | `/src/athena/manager.py` | 865-906 |
| Tier 2 logic | `/src/athena/manager.py` | 908-951 |
| Tier 3 logic | `/src/athena/manager.py` | 953-994 |
| RAG synthesis | `/src/athena/rag/manager.py` | 156-214 |
| Session context | `/src/athena/session/context_manager.py` | 164-481 |
| Caching | `/src/athena/performance/cache.py` | 46-368 |
| Performance monitoring | `/src/athena/performance/monitor.py` | 1-348 |
| Cascade safety | `/src/athena/hooks/lib/cascade_monitor.py` | 1-193 |

## Architecture Summary

```
recall(query, cascade_depth=3)
├─ Tier 1 (50-150ms): Layer-specific searches
│  ├─ Episodic (temporal, recent events)
│  ├─ Semantic (factual knowledge)
│  ├─ Procedural (workflows)
│  ├─ Prospective (tasks/goals)
│  └─ Graph (relationships)
├─ Tier 2 (100-300ms, if depth >= 2): Cross-layer enrichment
│  ├─ Hybrid search
│  ├─ Meta-memory
│  └─ Session context injection
└─ Tier 3 (500-2000ms, if depth >= 3): LLM synthesis
   ├─ RAG retrieval
   └─ Planning synthesis
```

## Performance Baselines

| Metric | Time | Bottleneck |
|--------|------|-----------|
| Tier 1 only | 50-150ms | Semantic embedding lookup |
| +Tier 2 | 150-450ms | Hybrid search coordination |
| +Tier 3 | 650-2450ms | LLM API call |
| Repeated query (cached) | 50-100ms | Cache lookup + merge |

## Top 3 Optimization Opportunities

### 1. Cascade Result Caching (HIGHEST ROI)
- **Where**: `manager.py:recall()` entry/exit
- **What**: Cache results for 5 minutes by (query, context, depth) hash
- **Impact**: 10-30x speedup for repeated queries, 30-40% cache hit rate
- **Complexity**: LOW - Use existing LRUCache

### 2. Parallelize Tier 1 Queries
- **Where**: `manager.py:_recall_tier_1()`
- **What**: Use `asyncio.gather()` instead of sequential execution
- **Impact**: 30-50% faster for Tier 1, 20-30% overall
- **Complexity**: MEDIUM - Requires async refactor

### 3. Query Complexity Classification
- **Where**: New method in `manager.py`
- **What**: Auto-select depth based on keywords + context
- **Impact**: 25-30% average latency, 40% fewer RAG calls
- **Complexity**: LOW - Keyword heuristics

## Current Limitations

1. **No caching at recall level** - Each query recomputes all tiers
2. **Sequential Tier 1 execution** - Independent layer queries run one-by-one
3. **Always executes Tier 3 if depth=3** - No intelligence about when LLM synthesis adds value
4. **Manual depth selection** - Users must specify cascade_depth, no auto-selection
5. **Session context loaded per recall** - Database query even if unchanged
6. **No batch operations** - Tier 1 queries each do separate embeddings/projections

## Key Query Types & Routing

| Query | Indicators | Routed to |
|-------|-----------|-----------|
| Temporal | when, last, recent, error | Episodic |
| Factual | (default) | Semantic |
| Relational | depends, related, connected | Graph |
| Procedural | how to, workflow, steps | Procedural |
| Prospective | task, goal, todo, remind | Prospective |
| Meta | what do we know, coverage | Meta (Tier 2) |
| Planning | decompose, plan, strategy | Planning RAG (Tier 3) |

## Code Snippets

### Add Query Complexity Classification
```python
def _select_cascade_depth(query: str, context: dict) -> int:
    """Recommend depth: 1 (simple), 2 (contextual), 3 (reasoning)"""
    if any(kw in query.lower() for kw in 
           ["decompose", "plan", "strategy", "validate"]):
        return 3  # Needs reasoning
    if context.get("phase") or context.get("recent_events"):
        return 2  # Needs context enrichment
    return 1  # Simple factual query
```

### Cache Cascade Results
```python
def recall(self, query, context=None, cascade_depth=3, ...):
    cache_key = hashlib.md5(
        f"{query}:{sorted(context.items())}:{cascade_depth}".encode()
    ).hexdigest()
    
    # Check cache first
    cached = self._cascade_cache.get(cache_key)
    if cached:
        return cached
    
    # Compute results (existing code)
    results = self._compute_cascade(...)
    
    # Cache for 5 minutes
    self._cascade_cache.set(cache_key, results, ttl_seconds=300)
    return results
```

### Parallelize Tier 1
```python
async def _recall_tier_1_async(self, query, context, k):
    """Execute layer queries in parallel."""
    tasks = {
        "episodic": self._query_episodic_async(query, context, k),
        "semantic": self._query_semantic_async(query, context, k),
        "procedural": self._query_procedural_async(query, context, k),
        "prospective": self._query_prospective_async(query, context, k),
        "graph": self._query_graph_async(query, context, k),
    }
    return await asyncio.gather(*tasks.values())
```

## Testing

All cascade depth scenarios covered in:
- `tests/unit/test_cascading_recall.py` (456 lines)
- Tests for Tier 1, 2, 3 separately
- Tests for context integration
- Tests for error handling
- Tests for edge cases (empty query, unicode, etc.)

## Metrics to Monitor

```python
# Record these with performance/monitor.py
timer("recall_tier_1").record()
timer("recall_tier_2").record()
timer("recall_tier_3").record()
timer("recall_total").record()

# Track cache performance
cache.get_stats()  # {hits, misses, hit_rate, size}

# Track depth distribution
depth_1_calls += 1
depth_2_calls += 1
depth_3_calls += 1
```

## Common Issues & Solutions

### Problem: Slow queries (>500ms)
- **Check**: Is cascade_depth=3? Try depth=1 first
- **Check**: Are repeated queries hitting cache?
- **Check**: Is RAG configured properly?

### Problem: High memory usage
- **Check**: Cache size - default 500 entries, may need limits
- **Check**: Session context - invalidate old sessions

### Problem: Many RAG synthesis calls
- **Check**: Use `_should_use_tier_3_rag()` to skip unnecessary syntheses
- **Check**: Check relevance scores from Tier 1 before using Tier 3

## Next Steps

1. **Implement caching** (1-2 days, highest ROI)
2. **Add depth auto-selection** (1 day)
3. **Parallelize Tier 1** (2-3 days)
4. **Add metrics collection** (1 day)
5. **Monitor in production** (ongoing)

Expected improvement: **25-40% average latency reduction**, **10-30x for repeated queries**
