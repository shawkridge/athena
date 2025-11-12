"""Performance optimization module for memory system.

This module provides tools to optimize memory operations:
- Tier selection for intelligent cascade depth choice
- Query caching for repeated queries
- Session context caching
- Parallel tier execution

Typical usage:
    from athena.optimization import TierSelector, QueryCache, ParallelLayerExecutor

    selector = TierSelector()
    cache = QueryCache(max_entries=1000)
    executor = ParallelLayerExecutor()

    # Select optimal depth
    depth = selector.select_depth(query, context)

    # Check cache
    cached = cache.get(query, context)
    if cached:
        return cached

    # Run recall with selected depth and parallel execution
    results = manager.recall(query, context, cascade_depth=depth, use_parallel=True)

    # Cache results
    cache.put(query, results, context)
    return results
"""

from .parallel_executor import ParallelLayerExecutor, ParallelTier1Executor, QueryTask
from .query_cache import QueryCache, SessionContextCache
from .tier_selection import TierSelector

__all__ = [
    "TierSelector",
    "QueryCache",
    "SessionContextCache",
    "ParallelLayerExecutor",
    "ParallelTier1Executor",
    "QueryTask",
]
