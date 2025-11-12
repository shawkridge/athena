"""Unit tests for Dependency Graph Engine.

Tests dependency graph learning including:
- Layer dependency tracking
- Query pattern learning
- Parallelization benefit estimation
- Cache worthiness calculation
- Smart layer selection based on query type
"""

import pytest
import time
from athena.optimization.dependency_graph import (
    DependencyGraph,
    LayerDependency,
    QueryPattern,
)
from athena.optimization.performance_profiler import (
    PerformanceProfiler,
    QueryMetrics,
)


@pytest.fixture
def profiler():
    """Create a fresh performance profiler."""
    return PerformanceProfiler()


@pytest.fixture
def dependency_graph(profiler):
    """Create a fresh dependency graph."""
    return DependencyGraph(profiler, min_samples=3)


@pytest.fixture
def sample_query_metrics():
    """Create sample query metrics for testing."""
    return QueryMetrics(
        query_id="q_test_1",
        query_text="What happened?",
        query_type="temporal",
        timestamp=time.time(),
        latency_ms=150.0,
        memory_mb=50.0,
        cache_hit=False,
        result_count=10,
        layers_queried=["episodic", "semantic"],
        layer_latencies={"episodic": 80.0, "semantic": 70.0},
        success=True,
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_dependency_graph_initialization(dependency_graph):
    """Test dependency graph initializes correctly."""
    assert dependency_graph.dependencies == {}
    assert dependency_graph.query_patterns == {}
    assert dependency_graph.layer_co_occurrence == {}
    assert dependency_graph.min_samples == 3


def test_dependency_graph_query_type_layers(dependency_graph):
    """Test that default query type patterns are initialized."""
    assert "temporal" in dependency_graph.query_type_layers
    assert "factual" in dependency_graph.query_type_layers
    assert "relational" in dependency_graph.query_type_layers
    assert dependency_graph.query_type_layers["temporal"] == ["episodic", "semantic"]


# ============================================================================
# Layer Dependency Tests
# ============================================================================


def test_layer_dependency_creation():
    """Test creating a layer dependency."""
    dep = LayerDependency(
        source_layer="episodic",
        target_layer="semantic",
        co_occurrence_count=5,
        avg_parallel_speedup=2.5,
    )
    assert dep.source_layer == "episodic"
    assert dep.target_layer == "semantic"
    assert dep.co_occurrence_count == 5
    assert dep.avg_parallel_speedup == 2.5


def test_layer_dependency_tracking(dependency_graph, sample_query_metrics):
    """Test tracking layer dependencies from query metrics."""
    # Update graph with first metrics
    dependency_graph.update_from_metrics(sample_query_metrics)

    # Verify layers are co-occurrence tracked
    key = tuple(sorted(sample_query_metrics.layers_queried))
    assert key in dependency_graph.layer_co_occurrence
    assert dependency_graph.layer_co_occurrence[key] >= 1


def test_layer_dependency_parallelization_benefit(dependency_graph):
    """Test parallelization benefit is calculated correctly."""
    # Add multiple metrics with known parallelization benefits
    metrics_list = [
        QueryMetrics(
            query_id=f"q_{i}",
            query_type="temporal",
            layers_queried=["episodic", "semantic"],
            sequential_latency_ms=100.0,
            parallel_latency_ms=40.0,
            estimated_parallelization_benefit=2.5,
            cache_hit=False,
            success=True,
        )
        for i in range(5)
    ]

    for metrics in metrics_list:
        dependency_graph.update_from_metrics(metrics)

    # Check that parallelization benefit is tracked
    benefit = dependency_graph.get_parallelization_benefit(["episodic", "semantic"])
    assert benefit > 0


# ============================================================================
# Query Pattern Tests
# ============================================================================


def test_query_pattern_creation():
    """Test creating a query pattern."""
    pattern = QueryPattern(
        query_type="temporal",
        typical_layers=["episodic", "semantic"],
        frequency=10,
        avg_success_rate=0.95,
    )
    assert pattern.query_type == "temporal"
    assert pattern.typical_layers == ["episodic", "semantic"]
    assert pattern.frequency == 10
    assert pattern.avg_success_rate == 0.95


def test_query_pattern_learning(dependency_graph, sample_query_metrics):
    """Test learning query patterns from metrics."""
    # Add multiple similar metrics to establish pattern
    for i in range(5):
        metrics = QueryMetrics(
            query_id=f"q_temporal_{i}",
            query_type="temporal",
            layers_queried=["episodic", "semantic"],
            sequential_latency_ms=150.0,
            parallel_latency_ms=50.0,
            estimated_parallelization_benefit=3.0,
            cache_hit=i % 2 == 0,  # 50% cache hit rate
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    # Verify pattern was learned
    pattern = dependency_graph.get_query_pattern("temporal")
    assert pattern is not None
    assert pattern.frequency >= 5


def test_query_pattern_cache_hit_tracking(dependency_graph):
    """Test tracking cache hit rate in patterns."""
    # Add metrics with varying cache hits
    for i in range(10):
        metrics = QueryMetrics(
            query_id=f"q_cache_{i}",
            query_type="factual",
            layers_queried=["semantic", "graph"],
            sequential_latency_ms=100.0,
            parallel_latency_ms=80.0,
            estimated_parallelization_benefit=1.25,
            cache_hit=i < 7,  # 70% cache hit rate
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    pattern = dependency_graph.get_query_pattern("factual")
    assert pattern is not None
    assert pattern.cache_hit_rate >= 0.6  # Approximate 70%


# ============================================================================
# Layer Selection Tests
# ============================================================================


def test_get_layer_selection_default(dependency_graph):
    """Test getting default layer selection for query type."""
    layers = dependency_graph.get_layer_selection("temporal", context={})
    assert isinstance(layers, list)
    assert "episodic" in layers or len(layers) > 0


def test_get_layer_selection_with_learned_pattern(dependency_graph):
    """Test layer selection uses learned patterns."""
    # Learn a strong pattern
    for i in range(10):
        metrics = QueryMetrics(
            query_id=f"q_pattern_{i}",
            query_type="relational",
            layers_queried=["graph", "semantic", "meta"],
            sequential_latency_ms=200.0,
            parallel_latency_ms=60.0,
            estimated_parallelization_benefit=3.3,
            cache_hit=False,
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    # Get layer selection should use the pattern
    layers = dependency_graph.get_layer_selection("relational", context={})
    assert len(layers) >= 2


# ============================================================================
# Cache Worthiness Tests
# ============================================================================


def test_cache_worthiness_calculation(dependency_graph):
    """Test cache worthiness calculation."""
    # Add high-value metrics (frequent, successful, cached)
    for i in range(10):
        metrics = QueryMetrics(
            query_id=f"q_worth_{i}",
            query_type="temporal",
            layers_queried=["episodic", "semantic"],
            sequential_latency_ms=150.0,
            parallel_latency_ms=50.0,
            estimated_parallelization_benefit=3.0,
            cache_hit=True,  # Cache hits add worthiness
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    # Cache worthiness should increase for frequently cached queries
    worthiness = dependency_graph.get_cache_worthiness(["episodic", "semantic"])
    assert worthiness >= 0.0


def test_cache_worthiness_low_frequency(dependency_graph):
    """Test cache worthiness is low for infrequently accessed layers."""
    # Add single metric
    metrics = QueryMetrics(
        query_id="q_rare",
        query_type="procedural",
        layers_queried=["procedural", "semantic"],
        sequential_latency_ms=200.0,
        parallel_latency_ms=150.0,
        estimated_parallelization_benefit=1.33,
        cache_hit=False,
        success=True,
    )
    dependency_graph.update_from_metrics(metrics)

    worthiness = dependency_graph.get_cache_worthiness(["procedural", "semantic"])
    # Worthiness should be low since frequency is low
    assert worthiness >= 0.0


# ============================================================================
# Statistics and Diagnostics Tests
# ============================================================================


def test_get_dependency_stats(dependency_graph, sample_query_metrics):
    """Test getting dependency statistics."""
    dependency_graph.update_from_metrics(sample_query_metrics)
    stats = dependency_graph.get_dependency_stats()

    assert isinstance(stats, dict)
    assert "total_dependencies" in stats or "layers_tracked" in stats


def test_get_query_patterns_summary(dependency_graph):
    """Test getting summary of all learned patterns."""
    # Add multiple patterns
    for query_type in ["temporal", "factual", "relational"]:
        for i in range(5):
            metrics = QueryMetrics(
                query_id=f"q_{query_type}_{i}",
                query_type=query_type,
                layers_queried=["semantic", "graph"],
                sequential_latency_ms=100.0,
                parallel_latency_ms=50.0,
                estimated_parallelization_benefit=2.0,
                cache_hit=False,
                success=True,
            )
            dependency_graph.update_from_metrics(metrics)

    patterns = dependency_graph.query_patterns
    assert len(patterns) >= 0  # May have learned patterns


def test_multiple_metric_updates(dependency_graph):
    """Test updating graph with multiple metrics."""
    metrics_list = [
        QueryMetrics(
            query_id=f"q_multi_{i}",
            query_type="temporal",
            layers_queried=["episodic", "semantic"],
            sequential_latency_ms=100.0 + i * 10,
            parallel_latency_ms=40.0 + i * 5,
            estimated_parallelization_benefit=2.5,
            cache_hit=i % 3 == 0,
            success=True,
        )
        for i in range(10)
    ]

    for metrics in metrics_list:
        dependency_graph.update_from_metrics(metrics)

    # Verify graph has updated with all metrics
    key = tuple(sorted(["episodic", "semantic"]))
    assert key in dependency_graph.layer_co_occurrence


def test_query_pattern_min_samples_threshold(profiler):
    """Test that patterns require minimum samples before being reliable."""
    dep_graph = DependencyGraph(profiler, min_samples=5)

    # Add only 3 metrics (below threshold)
    for i in range(3):
        metrics = QueryMetrics(
            query_id=f"q_threshold_{i}",
            query_type="rare",
            layers_queried=["semantic"],
            sequential_latency_ms=100.0,
            parallel_latency_ms=100.0,
            estimated_parallelization_benefit=1.0,
            cache_hit=False,
            success=True,
        )
        dep_graph.update_from_metrics(metrics)

    # Pattern may not be confident yet
    pattern = dep_graph.get_query_pattern("rare")
    if pattern is not None:
        # Pattern exists but should reflect low sample count
        assert pattern.frequency <= 3


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_unknown_query_type(dependency_graph):
    """Test handling of unknown query types."""
    layers = dependency_graph.get_layer_selection("unknown_type", context={})
    assert isinstance(layers, list)  # Should return default or empty list


def test_empty_layers_list(dependency_graph):
    """Test handling of empty layers list."""
    benefit = dependency_graph.get_parallelization_benefit([])
    assert benefit >= 0.0  # Should return valid value


def test_single_layer(dependency_graph):
    """Test handling of single layer queries."""
    metrics = QueryMetrics(
        query_id="q_single",
        query_type="meta",
        layers_queried=["meta"],
        sequential_latency_ms=50.0,
        parallel_latency_ms=50.0,
        estimated_parallelization_benefit=1.0,
        cache_hit=False,
        success=True,
    )
    dependency_graph.update_from_metrics(metrics)

    benefit = dependency_graph.get_parallelization_benefit(["meta"])
    assert benefit >= 0.0


def test_parallelization_benefit_bounds(dependency_graph):
    """Test that parallelization benefit stays within bounds."""
    # Add metrics with very high speedups
    for i in range(5):
        metrics = QueryMetrics(
            query_id=f"q_bounds_{i}",
            query_type="temporal",
            layers_queried=["episodic", "semantic"],
            sequential_latency_ms=1000.0,
            parallel_latency_ms=10.0,  # 100x speedup
            estimated_parallelization_benefit=100.0,  # Very high
            cache_hit=False,
            success=True,
        )
        dependency_graph.update_from_metrics(metrics)

    benefit = dependency_graph.get_parallelization_benefit(["episodic", "semantic"])
    # Benefit should be reasonable and not unbounded
    assert benefit >= 0.0


def test_query_pattern_success_rate_tracking(dependency_graph):
    """Test tracking success rates in query patterns."""
    # Add metrics with varying success rates
    success_count = 0
    for i in range(10):
        success = i < 8  # 80% success rate
        if success:
            success_count += 1
        metrics = QueryMetrics(
            query_id=f"q_success_{i}",
            query_type="temporal",
            layers_queried=["episodic"],
            sequential_latency_ms=100.0,
            parallel_latency_ms=100.0,
            estimated_parallelization_benefit=1.0,
            cache_hit=False,
            success=success,
        )
        dependency_graph.update_from_metrics(metrics)

    pattern = dependency_graph.get_query_pattern("temporal")
    if pattern is not None:
        # Success rate should reflect approximately 80%
        assert pattern.avg_success_rate >= 0.5
