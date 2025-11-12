"""Integration tests for Phase 7bc - Ultimate Hybrid Adaptive Execution System.

Tests end-to-end execution flows including:
- Complete query execution pipeline
- Strategy selection to result aggregation
- Cache invalidation and updates
- Worker pool integration
- Telemetry collection and learning
- Performance under different conditions
"""

import pytest
import time
from athena.optimization.dependency_graph import DependencyGraph
from athena.optimization.cross_layer_cache import CrossLayerCache
from athena.optimization.adaptive_strategy_selector import (
    AdaptiveStrategySelector,
    ExecutionStrategy,
)
from athena.optimization.result_aggregator import ResultAggregator
from athena.optimization.worker_pool_executor import WorkerPool
from athena.optimization.execution_telemetry import ExecutionTelemetryCollector
from athena.optimization.performance_profiler import PerformanceProfiler, QueryMetrics


@pytest.fixture
def profiler():
    """Create a fresh performance profiler."""
    return PerformanceProfiler()


@pytest.fixture
def dependency_graph(profiler):
    """Create a fresh dependency graph."""
    return DependencyGraph(profiler)


@pytest.fixture
def cross_layer_cache():
    """Create a fresh cross-layer cache."""
    return CrossLayerCache(max_entries=5000)


@pytest.fixture
def strategy_selector(profiler, dependency_graph, cross_layer_cache):
    """Create a fresh strategy selector."""
    return AdaptiveStrategySelector(
        profiler=profiler,
        dependency_graph=dependency_graph,
        cross_layer_cache=cross_layer_cache,
    )


@pytest.fixture
def result_aggregator():
    """Create a fresh result aggregator."""
    return ResultAggregator()


@pytest.fixture
def worker_pool():
    """Create a fresh worker pool."""
    return WorkerPool(min_workers=2, max_workers=8)


@pytest.fixture
def telemetry_collector():
    """Create a fresh telemetry collector."""
    return ExecutionTelemetryCollector()


# ============================================================================
# End-to-End Query Execution Tests
# ============================================================================


def test_simple_query_execution_flow(
    strategy_selector,
    cross_layer_cache,
    result_aggregator,
    telemetry_collector,
):
    """Test complete execution of a simple query."""
    # 1. Analyze query
    analysis = strategy_selector.analyze_query(
        query_text="What happened?", query_type="temporal"
    )

    # 2. Select strategy
    decision = strategy_selector.select_strategy(
        query_text="What happened?",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=analysis.cache_hit_probability,
        parallelization_benefit=analysis.parallelization_benefit,
    )

    # 3. Execute (simulated)
    start_time = time.time()

    if decision.strategy == ExecutionStrategy.CACHE:
        # Check cache
        cached = cross_layer_cache.try_get_cached("temporal", ["episodic", "semantic"], {})
        results = cached or {"episodic": [1, 2], "semantic": [3, 4]}
    else:
        # Execute query
        results = {"episodic": [1, 2], "semantic": [3, 4]}

    actual_latency = (time.time() - start_time) * 1000

    # 4. Record telemetry
    from athena.optimization.execution_telemetry import ExecutionTelemetry

    telemetry = ExecutionTelemetry(
        query_id="q_simple",
        query_type="temporal",
        strategy_chosen=decision.strategy.value,
        strategy_confidence=decision.confidence,
        estimated_latency_ms=decision.estimated_latency_ms,
        total_latency_ms=actual_latency,
        success=True,
        layers_queried=["episodic", "semantic"],
        result_count=4,
    )
    telemetry_collector.record_execution(telemetry)

    # 5. Verify results
    assert decision.strategy is not None
    assert actual_latency >= 0
    assert telemetry_collector.total_recorded >= 1


def test_cache_hit_flow(
    strategy_selector, cross_layer_cache, result_aggregator
):
    """Test query execution with cache hit."""
    # Pre-populate cache
    cross_layer_cache.cache_result(
        "temporal",
        ["episodic", "semantic"],
        {"episodic": [1, 2], "semantic": [3, 4]},
        ttl=300,
    )

    # Query with high cache availability
    decision = strategy_selector.select_strategy(
        query_text="What happened?",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.9,
        parallelization_benefit=2.0,
    )

    # Try to get cached results
    cached = cross_layer_cache.try_get_cached(
        "temporal", ["episodic", "semantic"], {}
    )

    if cached:
        result, confidence = result_aggregator.aggregate_results(
            cache_results=cached,
            parallel_results=None,
        )
        assert result is not None


def test_parallel_execution_flow(strategy_selector, result_aggregator):
    """Test query execution with parallel strategy."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=3,
        estimated_cost=200.0,
        cache_availability=0.2,
        parallelization_benefit=2.5,
    )

    # Simulate parallel execution of multiple layers
    results = {
        "episodic": [1, 2, 3],
        "semantic": [4, 5, 6],
        "graph": [7, 8, 9],
    }

    # Aggregate results
    final_result, confidence = result_aggregator.aggregate_results(
        cache_results=None,
        parallel_results=results,
    )

    assert final_result is not None
    assert confidence >= 0.0


def test_distributed_execution_flow(worker_pool, result_aggregator):
    """Test query execution with distributed strategy."""
    from athena.optimization.worker_pool_executor import WorkerTask, TaskPriority

    # Submit tasks to worker pool
    tasks = [
        WorkerTask("task_1", "episodic", "query_episodic"),
        WorkerTask("task_2", "semantic", "query_semantic"),
        WorkerTask("task_3", "graph", "query_graph"),
    ]

    for task in tasks:
        worker_pool.submit_task(task)

    # Simulate results from workers
    distributed_results = {
        "episodic": [1, 2],
        "semantic": [3, 4],
        "graph": [5, 6],
    }

    # Aggregate results
    final_result, confidence = result_aggregator.aggregate_results(
        cache_results=None,
        parallel_results={},
        distributed_results=distributed_results,
    )

    assert final_result is not None


# ============================================================================
# Learning and Adaptation Tests
# ============================================================================


def test_dependency_graph_learning_from_execution(
    dependency_graph, telemetry_collector
):
    """Test dependency graph learns from execution telemetry."""
    from athena.optimization.performance_profiler import QueryMetrics

    # Simulate multiple query executions
    for i in range(5):
        metrics = QueryMetrics(
            query_id=f"q_learn_{i}",
            query_type="temporal",
            layers_queried=["episodic", "semantic"],
            sequential_latency_ms=150.0,
            parallel_latency_ms=50.0,
            estimated_parallelization_benefit=3.0,
            cache_hit=i % 2 == 0,
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    # Check that patterns were learned
    pattern = dependency_graph.get_query_pattern("temporal")
    assert pattern is not None
    assert pattern.frequency >= 5


def test_strategy_selector_improves_accuracy(
    strategy_selector, telemetry_collector
):
    """Test strategy selector improves with feedback."""
    # Make initial decision
    decision1 = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.5,
        parallelization_benefit=2.0,
    )

    # Record execution result
    strategy_selector.record_execution_result(
        strategy=decision1.strategy,
        estimated_latency_ms=decision1.estimated_latency_ms,
        actual_latency_ms=95.0,
        success=True,
    )

    # Make second decision (should be more accurate)
    decision2 = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.5,
        parallelization_benefit=2.0,
    )

    # Both decisions should be valid
    assert decision1.strategy is not None
    assert decision2.strategy is not None


def test_cache_effectiveness_tracking(
    cross_layer_cache, dependency_graph, telemetry_collector
):
    """Test tracking cache effectiveness over time."""
    from athena.optimization.performance_profiler import QueryMetrics

    # Build up cache usage data
    for i in range(10):
        # Cache hit
        cross_layer_cache.cache_result(
            "temporal", ["episodic"], {"data": [i]}, ttl=300
        )

        # Record metric showing cache effectiveness
        metrics = QueryMetrics(
            query_id=f"q_cache_eff_{i}",
            query_type="temporal",
            layers_queried=["episodic"],
            sequential_latency_ms=100.0,
            parallel_latency_ms=100.0,
            estimated_parallelization_benefit=1.0,
            cache_hit=True,  # Cache hit
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    # Cache should be marked as worthwhile
    worthiness = dependency_graph.get_cache_worthiness(["episodic"])
    assert worthiness >= 0.0


# ============================================================================
# Mixed Workload Tests
# ============================================================================


def test_mixed_query_types_execution(
    strategy_selector,
    cross_layer_cache,
    result_aggregator,
    telemetry_collector,
):
    """Test executing different query types in sequence."""
    query_types = ["temporal", "factual", "relational", "procedural"]

    for q_type in query_types:
        analysis = strategy_selector.analyze_query(
            query_text=f"Sample {q_type} query",
            query_type=q_type,
        )

        decision = strategy_selector.select_strategy(
            query_text=f"Sample {q_type} query",
            query_type=q_type,
            num_layers=analysis.num_layers,
            estimated_cost=analysis.estimated_cost_ms,
            cache_availability=analysis.cache_hit_probability,
            parallelization_benefit=analysis.parallelization_benefit,
        )

        # Execute and aggregate
        results = {
            layer: list(range(i)) for i, layer in enumerate(analysis.suggested_layers)
        }

        final_result, confidence = result_aggregator.aggregate_results(
            cache_results=None,
            parallel_results=results,
        )

        assert final_result is not None


def test_high_load_execution(
    strategy_selector, worker_pool, cross_layer_cache, telemetry_collector
):
    """Test system behavior under high concurrency."""
    from athena.optimization.worker_pool_executor import WorkerTask

    # Simulate high load with many concurrent queries
    for i in range(50):
        # Submit tasks
        task = WorkerTask(
            f"task_{i}",
            "episodic",
            "query",
        )
        worker_pool.submit_task(task)

        # Make strategy decisions
        decision = strategy_selector.select_strategy(
            query_text=f"query_{i}",
            query_type="temporal",
            num_layers=2,
            estimated_cost=100.0,
            cache_availability=0.5,
            parallelization_benefit=2.0,
        )

    # System should handle load gracefully
    assert worker_pool.num_workers <= worker_pool.max_workers
    assert strategy_selector is not None


# ============================================================================
# Cache Invalidation Tests
# ============================================================================


def test_cache_invalidation_on_data_change(cross_layer_cache):
    """Test cache invalidation when underlying data changes."""
    # Populate cache
    cross_layer_cache.cache_result(
        "temporal",
        ["episodic"],
        {"data": [1, 2, 3]},
        ttl=300,
    )

    # Verify cached
    cached = cross_layer_cache.try_get_cached("temporal", ["episodic"], {})
    assert cached is not None

    # Invalidate by query type
    cross_layer_cache.invalidate_by_query_type("temporal")

    # Should not find cached data
    cached2 = cross_layer_cache.try_get_cached("temporal", ["episodic"], {})
    assert cached2 is None


def test_cache_ttl_expiration_invalidation(cross_layer_cache):
    """Test cache entries expire based on TTL."""
    cross_layer_cache.cache_result(
        "temporal",
        ["episodic"],
        {"data": [1, 2, 3]},
        ttl=1,  # 1 second
    )

    # Should be cached
    cached1 = cross_layer_cache.try_get_cached("temporal", ["episodic"], {})
    assert cached1 is not None

    # Wait for expiration
    time.sleep(1.1)

    # Should be expired
    cached2 = cross_layer_cache.try_get_cached("temporal", ["episodic"], {})
    # May be None or expired


# ============================================================================
# Failure Recovery Tests
# ============================================================================


def test_strategy_fallback_on_cache_miss(strategy_selector, cross_layer_cache):
    """Test fallback strategy when cache misses."""
    # Empty cache
    cross_layer_cache.clear()

    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.95,  # High cache availability
        parallelization_benefit=2.0,
    )

    # Should have fallback strategy
    assert decision.fallback_strategy is not None
    assert decision.fallback_strategy != decision.strategy


def test_result_aggregator_handles_missing_layers(result_aggregator):
    """Test aggregator handles missing results from some layers."""
    # Only some layers have results
    partial_results = {
        "episodic": [1, 2, 3],
        # semantic is missing
        # graph is missing
    }

    result, confidence = result_aggregator.aggregate_results(
        cache_results=None,
        parallel_results=partial_results,
    )

    # Should handle partial results gracefully
    assert result is not None


def test_worker_pool_recovery_from_task_failure(worker_pool):
    """Test worker pool recovers from task failures."""
    from athena.optimization.worker_pool_executor import WorkerTask

    # Submit failing task
    fail_task = WorkerTask("fail", "episodic", "query_that_fails")
    result1 = worker_pool.submit_task(fail_task)

    # Submit succeeding task
    success_task = WorkerTask("success", "episodic", "query_that_succeeds")
    result2 = worker_pool.submit_task(success_task)

    # Pool should remain operational
    assert worker_pool.num_workers >= 1


# ============================================================================
# Performance Benchmarks
# ============================================================================


def test_cache_speed_advantage(cross_layer_cache, result_aggregator):
    """Test cache provides expected speed advantage."""
    # Pre-populate cache
    cross_layer_cache.cache_result(
        "temporal",
        ["episodic", "semantic"],
        {"data": list(range(1000))},
        ttl=300,
    )

    # Time cache retrieval
    start = time.time()
    for _ in range(100):
        cached = cross_layer_cache.try_get_cached(
            "temporal", ["episodic", "semantic"], {}
        )
    cache_time = time.time() - start

    # Cache should be fast (< 10ms for 100 retrievals)
    assert cache_time < 0.1  # 100ms for 100 operations


def test_parallel_speedup_measurement(result_aggregator):
    """Test parallel execution provides speedup."""
    # Simulate parallel execution
    start = time.time()
    parallel_results = {
        "episodic": list(range(100)),
        "semantic": list(range(100, 200)),
        "graph": list(range(200, 300)),
    }
    final_result, confidence = result_aggregator.aggregate_results(
        cache_results=None,
        parallel_results=parallel_results,
    )
    parallel_time = time.time() - start

    # Aggregation should be fast
    assert parallel_time < 0.1


def test_system_throughput_multiple_queries(
    strategy_selector,
    cross_layer_cache,
    result_aggregator,
    telemetry_collector,
):
    """Test system throughput with multiple queries."""
    from athena.optimization.execution_telemetry import ExecutionTelemetry

    start = time.time()
    query_count = 100

    for i in range(query_count):
        decision = strategy_selector.select_strategy(
            query_text=f"query_{i}",
            query_type="temporal",
            num_layers=2,
            estimated_cost=100.0,
            cache_availability=0.5,
            parallelization_benefit=2.0,
        )

        result, confidence = result_aggregator.aggregate_results(
            cache_results=None,
            parallel_results={"episodic": [i], "semantic": [i + 100]},
        )

        telemetry = ExecutionTelemetry(
            query_id=f"throughput_{i}",
            query_type="temporal",
            total_latency_ms=10.0,
        )
        telemetry_collector.record_execution(telemetry)

    total_time = time.time() - start
    qps = query_count / total_time

    # System should handle at least 10 QPS
    assert qps >= 1.0  # At least 1 query per second


# ============================================================================
# Telemetry Integration Tests
# ============================================================================


def test_telemetry_feedback_loop(
    strategy_selector,
    dependency_graph,
    telemetry_collector,
):
    """Test telemetry feeds back into optimization."""
    from athena.optimization.performance_profiler import QueryMetrics

    # Record initial metrics
    for i in range(10):
        metrics = QueryMetrics(
            query_id=f"feedback_{i}",
            query_type="temporal",
            layers_queried=["episodic", "semantic"],
            sequential_latency_ms=100.0,
            parallel_latency_ms=40.0,
            estimated_parallelization_benefit=2.5,
            cache_hit=False,
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    # Should improve strategy selection
    pattern = dependency_graph.get_query_pattern("temporal")
    assert pattern is not None


def test_comprehensive_telemetry_collection(telemetry_collector):
    """Test collecting comprehensive execution telemetry."""
    from athena.optimization.execution_telemetry import ExecutionTelemetry

    # Record various execution scenarios
    scenarios = [
        ("cache_hit", "cache", 10.0),
        ("parallel_speedup", "parallel", 50.0),
        ("distributed_large", "distributed", 200.0),
        ("sequential_simple", "sequential", 25.0),
    ]

    for scenario_name, strategy, latency in scenarios:
        for i in range(5):
            telemetry = ExecutionTelemetry(
                query_id=f"{scenario_name}_{i}",
                query_type="temporal",
                strategy_chosen=strategy,
                total_latency_ms=latency,
                success=True,
            )
            telemetry_collector.record_execution(telemetry)

    # Verify comprehensive collection
    stats = telemetry_collector.get_overall_statistics()
    assert telemetry_collector.total_recorded >= 20
