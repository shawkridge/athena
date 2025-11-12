"""Performance optimization module for memory system.

Phase 7a + Phase 7bc: Ultimate hybrid adaptive execution system

This module provides comprehensive optimization tools:
- Tier selection for intelligent cascade depth
- Query caching and cross-layer caching
- Parallel layer execution
- Dependency graph learning
- Adaptive strategy selection
- Distributed execution via worker pool
- Execution telemetry and continuous learning

Phase 7a Components:
- PerformanceProfiler: Track query metrics
- AutoTuner: Dynamic parameter optimization

Phase 7bc Ultimate Components:
- DependencyGraph: Learn layer relationships
- CrossLayerCache: Cache multi-layer results
- AdaptiveStrategySelector: Choose CACHE vs PARALLEL vs DISTRIBUTED
- ResultAggregator: Intelligently merge results
- WorkerPool: Distributed execution with dynamic scaling
- ExecutionTelemetry: Track strategy effectiveness

Typical usage:
    from athena.optimization import (
        DependencyGraph, CrossLayerCache, AdaptiveStrategySelector,
        ResultAggregator, WorkerPool
    )

    # Create components
    dep_graph = DependencyGraph(profiler)
    cross_cache = CrossLayerCache()
    strategy_selector = AdaptiveStrategySelector(profiler, dep_graph, cross_cache)
    result_agg = ResultAggregator(confidence_scorer)
    worker_pool = WorkerPool(min_workers=2, max_workers=20)

    # Smart query execution
    strategy = strategy_selector.select_strategy(
        query_text, query_type, num_layers, cost,
        cache_avail, parallelization_benefit
    )

    if strategy == ExecutionStrategy.CACHE:
        results = cross_cache.try_get_cached(query_type, layers, params)
    elif strategy == ExecutionStrategy.PARALLEL:
        results = await parallel_executor(layers)
    elif strategy == ExecutionStrategy.DISTRIBUTED:
        results = await worker_pool.submit_task(task)

    # Merge and return
    final, confidence = result_agg.aggregate_results(
        cache_results, parallel_results, distributed_results, scores
    )
"""

# Phase 7a components
from .auto_tuner import AutoTuner, TuningConfig, TuningMetrics, TuningStrategy
from .parallel_executor import ParallelLayerExecutor, QueryTask
from .parallel_tier1 import ParallelTier1Executor
from .performance_profiler import (
    PerformanceProfiler,
    QueryMetrics,
    LayerMetrics,
    QueryTypeMetrics,
)
from .query_cache import QueryCache, SessionContextCache
from .tier_selection import TierSelector

# Phase 7bc components
from .adaptive_strategy_selector import (
    AdaptiveStrategySelector,
    ExecutionStrategy,
    StrategyDecision,
    QueryAnalysis,
)
from .cross_layer_cache import CrossLayerCache, CrossLayerCacheEntry
from .dependency_graph import DependencyGraph, LayerDependency, QueryPattern
from .execution_telemetry import ExecutionTelemetry, ExecutionTelemetryCollector
from .result_aggregator import ResultAggregator, SourceConfidence
from .worker_pool_executor import (
    WorkerPool,
    WorkerTask,
    WorkerTaskResult,
    LoadBalancer,
    TaskPriority,
)

__all__ = [
    # Phase 7a
    "AutoTuner",
    "TuningConfig",
    "TuningMetrics",
    "TuningStrategy",
    "ParallelLayerExecutor",
    "ParallelTier1Executor",
    "PerformanceProfiler",
    "QueryMetrics",
    "LayerMetrics",
    "QueryTypeMetrics",
    "QueryCache",
    "SessionContextCache",
    "QueryTask",
    "TierSelector",
    # Phase 7bc
    "AdaptiveStrategySelector",
    "ExecutionStrategy",
    "StrategyDecision",
    "QueryAnalysis",
    "CrossLayerCache",
    "CrossLayerCacheEntry",
    "DependencyGraph",
    "LayerDependency",
    "QueryPattern",
    "ExecutionTelemetry",
    "ExecutionTelemetryCollector",
    "ResultAggregator",
    "SourceConfidence",
    "WorkerPool",
    "WorkerTask",
    "WorkerTaskResult",
    "LoadBalancer",
    "TaskPriority",
]
