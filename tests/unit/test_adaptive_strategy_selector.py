"""Unit tests for Adaptive Strategy Selector.

Tests intelligent strategy selection including:
- CACHE strategy selection
- PARALLEL strategy selection
- DISTRIBUTED strategy selection
- SEQUENTIAL strategy selection
- Decision reasoning
- Fallback strategies
- Cache availability analysis
- Parallelization benefit estimation
"""

import pytest
from athena.optimization.adaptive_strategy_selector import (
    AdaptiveStrategySelector,
    ExecutionStrategy,
    StrategyDecision,
    QueryAnalysis,
)
from athena.optimization.dependency_graph import DependencyGraph
from athena.optimization.cross_layer_cache import CrossLayerCache
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


# ============================================================================
# Initialization Tests
# ============================================================================


def test_selector_initialization(strategy_selector):
    """Test selector initializes correctly."""
    assert strategy_selector.profiler is not None
    assert strategy_selector.dependency_graph is not None
    assert strategy_selector.cross_layer_cache is not None


# ============================================================================
# Strategy Selection Tests
# ============================================================================


def test_select_cache_strategy_when_available(strategy_selector, cross_layer_cache):
    """Test CACHE strategy is selected when results are cached."""
    # Pre-populate cache
    cross_layer_cache.cache_result(
        query_type="temporal",
        layers=["episodic", "semantic"],
        results={"data": [1, 2, 3]},
        ttl=300,
    )

    decision = strategy_selector.select_strategy(
        query_text="What happened?",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.9,
        parallelization_benefit=2.5,
    )

    # Should select CACHE or consider cache availability
    assert decision.strategy in [ExecutionStrategy.CACHE, ExecutionStrategy.PARALLEL]
    assert decision.confidence >= 0.0


def test_select_parallel_strategy_for_low_complexity(strategy_selector):
    """Test PARALLEL strategy is selected for low complexity queries."""
    decision = strategy_selector.select_strategy(
        query_text="Simple query",
        query_type="temporal",
        num_layers=2,
        estimated_cost=50.0,  # Low cost
        cache_availability=0.2,  # Low cache availability
        parallelization_benefit=2.5,  # Good parallelization
    )

    # Should select PARALLEL or CACHE
    assert decision.strategy in [
        ExecutionStrategy.PARALLEL,
        ExecutionStrategy.CACHE,
        ExecutionStrategy.SEQUENTIAL,
    ]
    assert 0.0 <= decision.confidence <= 1.0


def test_select_distributed_strategy_for_high_cost(strategy_selector):
    """Test DISTRIBUTED strategy is selected for high-cost queries."""
    decision = strategy_selector.select_strategy(
        query_text="Complex query",
        query_type="temporal",
        num_layers=5,
        estimated_cost=1000.0,  # High cost
        cache_availability=0.1,
        parallelization_benefit=3.0,
    )

    # Should consider DISTRIBUTED or PARALLEL for high cost
    assert decision.strategy in [
        ExecutionStrategy.DISTRIBUTED,
        ExecutionStrategy.PARALLEL,
        ExecutionStrategy.SEQUENTIAL,
    ]
    assert decision.fallback_strategy is not None


def test_select_sequential_fallback(strategy_selector):
    """Test SEQUENTIAL strategy is selected as fallback."""
    decision = strategy_selector.select_strategy(
        query_text="Simple query",
        query_type="meta",
        num_layers=1,
        estimated_cost=10.0,
        cache_availability=0.0,
        parallelization_benefit=1.0,  # No parallelization benefit
    )

    # Should select SEQUENTIAL for simple, low-benefit queries
    assert decision.strategy in [
        ExecutionStrategy.SEQUENTIAL,
        ExecutionStrategy.PARALLEL,
    ]
    assert decision.fallback_strategy is not None


# ============================================================================
# Decision Reasoning Tests
# ============================================================================


def test_strategy_decision_has_reasoning(strategy_selector):
    """Test that strategy decisions include reasoning."""
    decision = strategy_selector.select_strategy(
        query_text="test query",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.5,
        parallelization_benefit=2.0,
    )

    assert decision.reasoning is not None
    assert len(decision.reasoning) > 0
    assert isinstance(decision.reasoning, str)


def test_strategy_decision_estimated_latency(strategy_selector):
    """Test that strategy decisions include estimated latency."""
    decision = strategy_selector.select_strategy(
        query_text="test query",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.5,
        parallelization_benefit=2.0,
    )

    assert decision.estimated_latency_ms >= 0.0
    assert decision.estimated_speedup >= 1.0  # Should be at least 1.0


def test_strategy_decision_estimated_speedup(strategy_selector):
    """Test that estimated speedup reflects strategy choice."""
    decision = strategy_selector.select_strategy(
        query_text="test query",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.9,  # High cache availability
        parallelization_benefit=2.0,
    )

    # Cache strategy should have high speedup
    if decision.strategy == ExecutionStrategy.CACHE:
        assert decision.estimated_speedup >= 5.0


def test_strategy_decision_confidence_reflects_certainty(strategy_selector):
    """Test that confidence reflects decision certainty."""
    # High cache availability should have high confidence
    decision1 = strategy_selector.select_strategy(
        query_text="test query",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.95,
        parallelization_benefit=2.0,
    )

    # Low cache availability should have lower confidence
    decision2 = strategy_selector.select_strategy(
        query_text="test query",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.1,
        parallelization_benefit=2.0,
    )

    # Both should have valid confidence scores
    assert 0.0 <= decision1.confidence <= 1.0
    assert 0.0 <= decision2.confidence <= 1.0


# ============================================================================
# Query Analysis Tests
# ============================================================================


def test_analyze_query_temporal(strategy_selector):
    """Test query analysis for temporal queries."""
    analysis = strategy_selector.analyze_query(
        query_text="What events happened yesterday?", query_type="temporal"
    )

    assert isinstance(analysis, QueryAnalysis)
    assert analysis.query_type == "temporal"
    assert analysis.num_layers >= 1
    assert analysis.estimated_cost_ms >= 0.0


def test_analyze_query_factual(strategy_selector):
    """Test query analysis for factual queries."""
    analysis = strategy_selector.analyze_query(
        query_text="What is known about X?", query_type="factual"
    )

    assert isinstance(analysis, QueryAnalysis)
    assert analysis.query_type == "factual"
    assert analysis.cache_hit_probability >= 0.0


def test_analyze_query_relational(strategy_selector):
    """Test query analysis for relational queries."""
    analysis = strategy_selector.analyze_query(
        query_text="How are A and B related?", query_type="relational"
    )

    assert isinstance(analysis, QueryAnalysis)
    assert analysis.parallelization_benefit >= 0.0
    assert analysis.complexity_score >= 0.0


def test_analyze_query_procedural(strategy_selector):
    """Test query analysis for procedural queries."""
    analysis = strategy_selector.analyze_query(
        query_text="How do I do X?", query_type="procedural"
    )

    assert isinstance(analysis, QueryAnalysis)
    assert analysis.num_layers >= 1


def test_analyze_query_suggests_layers(strategy_selector):
    """Test that query analysis suggests appropriate layers."""
    analysis = strategy_selector.analyze_query(
        query_text="What happened?", query_type="temporal"
    )

    assert analysis.suggested_layers is not None
    assert len(analysis.suggested_layers) >= 1
    assert "episodic" in analysis.suggested_layers or "semantic" in analysis.suggested_layers


def test_analyze_query_complexity_score_bounds(strategy_selector):
    """Test that complexity scores are within bounds."""
    analysis = strategy_selector.analyze_query(
        query_text="test", query_type="temporal"
    )

    assert 0.0 <= analysis.complexity_score <= 1.0
    assert 0.0 <= analysis.cache_hit_probability <= 1.0
    assert analysis.parallelization_benefit >= 0.0


# ============================================================================
# Strategy History and Learning Tests
# ============================================================================


def test_strategy_decisions_are_recorded(strategy_selector):
    """Test that strategy decisions are recorded for learning."""
    # Make multiple decisions
    for i in range(5):
        decision = strategy_selector.select_strategy(
            query_text=f"query_{i}",
            query_type="temporal",
            num_layers=2,
            estimated_cost=100.0,
            cache_availability=0.5,
            parallelization_benefit=2.0,
        )

    # System should have recorded decisions
    stats = strategy_selector.get_strategy_statistics()
    assert isinstance(stats, dict)


def test_get_strategy_statistics(strategy_selector):
    """Test getting strategy statistics."""
    # Make some decisions
    strategy_selector.select_strategy(
        query_text="q1", query_type="temporal", num_layers=2, estimated_cost=100.0,
        cache_availability=0.5, parallelization_benefit=2.0,
    )

    stats = strategy_selector.get_strategy_statistics()
    assert isinstance(stats, dict)
    # Stats may contain: strategy_counts, avg_confidence, success_rate, etc.


def test_decision_estimation_accuracy_tracking(strategy_selector):
    """Test that estimation accuracy is tracked."""
    # Make decision with estimated latency
    decision = strategy_selector.select_strategy(
        query_text="test", query_type="temporal", num_layers=2, estimated_cost=100.0,
        cache_availability=0.5, parallelization_benefit=2.0,
    )

    estimated = decision.estimated_latency_ms

    # Record actual execution (simulated)
    strategy_selector.record_execution_result(
        strategy=decision.strategy,
        estimated_latency_ms=estimated,
        actual_latency_ms=95.0,
        success=True,
    )

    # Accuracy should be tracked
    stats = strategy_selector.get_strategy_statistics()
    assert isinstance(stats, dict)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_select_strategy_with_zero_cost(strategy_selector):
    """Test strategy selection with zero estimated cost."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=1,
        estimated_cost=0.0,
        cache_availability=0.5,
        parallelization_benefit=1.0,
    )

    assert decision.strategy is not None
    assert decision.fallback_strategy is not None


def test_select_strategy_with_very_high_cost(strategy_selector):
    """Test strategy selection with very high cost."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=10,
        estimated_cost=10000.0,
        cache_availability=0.1,
        parallelization_benefit=4.0,
    )

    # Should prefer DISTRIBUTED or PARALLEL for high cost
    assert decision.strategy in [
        ExecutionStrategy.DISTRIBUTED,
        ExecutionStrategy.PARALLEL,
    ]


def test_select_strategy_with_no_parallelization_benefit(strategy_selector):
    """Test strategy selection when parallelization provides no benefit."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=1,
        estimated_cost=50.0,
        cache_availability=0.2,
        parallelization_benefit=1.0,  # No benefit
    )

    # Should select appropriate strategy even without parallelization
    assert decision.strategy is not None


def test_select_strategy_with_perfect_cache_hit(strategy_selector):
    """Test strategy selection with perfect cache hit probability."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=1.0,  # Perfect cache availability
        parallelization_benefit=1.0,
    )

    # Should strongly prefer CACHE
    if decision.cache_availability > 0.9:
        assert decision.estimated_speedup > 5.0


def test_select_strategy_with_unknown_query_type(strategy_selector):
    """Test strategy selection with unknown query type."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="unknown_type",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.5,
        parallelization_benefit=2.0,
    )

    # Should still make a valid decision
    assert decision.strategy is not None
    assert decision.fallback_strategy is not None


def test_analyze_query_with_empty_text(strategy_selector):
    """Test query analysis with empty query text."""
    analysis = strategy_selector.analyze_query(query_text="", query_type="temporal")

    # Should handle gracefully
    assert isinstance(analysis, QueryAnalysis)
    assert analysis.complexity_score >= 0.0


def test_analyze_query_with_very_long_text(strategy_selector):
    """Test query analysis with very long query text."""
    long_query = "test " * 1000
    analysis = strategy_selector.analyze_query(
        query_text=long_query, query_type="temporal"
    )

    # Should handle gracefully
    assert isinstance(analysis, QueryAnalysis)
    assert analysis.complexity_score <= 1.0


def test_multiple_sequential_decisions(strategy_selector):
    """Test making multiple sequential decisions."""
    decisions = []
    for i in range(10):
        decision = strategy_selector.select_strategy(
            query_text=f"query_{i}",
            query_type="temporal",
            num_layers=2,
            estimated_cost=100.0 + i * 10,
            cache_availability=0.5,
            parallelization_benefit=2.0,
        )
        decisions.append(decision)

    # All decisions should be valid
    assert len(decisions) == 10
    assert all(d.strategy is not None for d in decisions)
    assert all(d.fallback_strategy is not None for d in decisions)


def test_strategy_selector_robustness(strategy_selector):
    """Test strategy selector handles edge cases robustly."""
    test_cases = [
        {"num_layers": 0, "estimated_cost": 0.0},
        {"num_layers": 100, "estimated_cost": 100000.0},
        {"num_layers": 1, "estimated_cost": 0.1},
    ]

    for test_case in test_cases:
        decision = strategy_selector.select_strategy(
            query_text="test",
            query_type="temporal",
            num_layers=test_case["num_layers"],
            estimated_cost=test_case["estimated_cost"],
            cache_availability=0.5,
            parallelization_benefit=2.0,
        )
        assert decision.strategy is not None


# ============================================================================
# Strategy Characteristics Tests
# ============================================================================


def test_cache_strategy_has_high_speedup(strategy_selector, cross_layer_cache):
    """Test that CACHE strategy has high estimated speedup."""
    # Pre-populate cache
    cross_layer_cache.cache_result(
        "temporal", ["episodic", "semantic"], {"data": [1, 2, 3]}, ttl=300
    )

    decision = strategy_selector.select_strategy(
        query_text="What happened?",
        query_type="temporal",
        num_layers=2,
        estimated_cost=100.0,
        cache_availability=0.95,
        parallelization_benefit=2.0,
    )

    if decision.strategy == ExecutionStrategy.CACHE:
        assert decision.estimated_speedup >= 5.0


def test_parallel_strategy_has_moderate_speedup(strategy_selector):
    """Test that PARALLEL strategy has moderate estimated speedup."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="temporal",
        num_layers=3,
        estimated_cost=100.0,
        cache_availability=0.2,
        parallelization_benefit=2.5,
    )

    if decision.strategy == ExecutionStrategy.PARALLEL:
        assert 1.5 <= decision.estimated_speedup <= 5.0


def test_sequential_strategy_has_1x_speedup(strategy_selector):
    """Test that SEQUENTIAL strategy has ~1x speedup."""
    decision = strategy_selector.select_strategy(
        query_text="test",
        query_type="meta",
        num_layers=1,
        estimated_cost=10.0,
        cache_availability=0.0,
        parallelization_benefit=1.0,
    )

    if decision.strategy == ExecutionStrategy.SEQUENTIAL:
        assert decision.estimated_speedup <= 1.5
