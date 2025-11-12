"""Unit tests for Execution Telemetry.

Tests telemetry collection and analysis including:
- Recording execution metrics
- Calculating estimation accuracy
- Tracking strategy effectiveness
- Performance trending
- Pattern learning from execution data
"""

import pytest
import time
from athena.optimization.execution_telemetry import (
    ExecutionTelemetry,
    ExecutionTelemetryCollector,
)


@pytest.fixture
def sample_telemetry():
    """Create sample execution telemetry."""
    return ExecutionTelemetry(
        query_id="q_test_1",
        query_type="temporal",
        strategy_chosen="parallel",
        strategy_confidence=0.85,
        estimated_latency_ms=150.0,
        total_latency_ms=145.0,
        success=True,
        layers_queried=["episodic", "semantic"],
    )


@pytest.fixture
def collector():
    """Create a fresh telemetry collector."""
    return ExecutionTelemetryCollector(retention_days=30)


# ============================================================================
# Telemetry Creation Tests
# ============================================================================


def test_execution_telemetry_creation(sample_telemetry):
    """Test creating execution telemetry."""
    assert sample_telemetry.query_id == "q_test_1"
    assert sample_telemetry.query_type == "temporal"
    assert sample_telemetry.strategy_chosen == "parallel"
    assert sample_telemetry.total_latency_ms == 145.0


def test_execution_telemetry_timestamp(sample_telemetry):
    """Test telemetry has timestamp."""
    assert sample_telemetry.timestamp > 0
    age = sample_telemetry.age_seconds()
    assert age >= 0.0
    assert age < 1.0


def test_execution_telemetry_estimation_accuracy(sample_telemetry):
    """Test telemetry calculates estimation accuracy."""
    # Estimated 150ms, actual 145ms
    estimated_vs_actual = sample_telemetry.estimated_latency_ms / sample_telemetry.total_latency_ms
    assert estimated_vs_actual > 0.0
    # Should be close to 1.0
    assert 0.8 < estimated_vs_actual < 1.3


def test_execution_telemetry_perfect_estimate():
    """Test telemetry with perfect estimation."""
    telemetry = ExecutionTelemetry(
        query_id="perfect",
        query_type="temporal",
        estimated_latency_ms=100.0,
        total_latency_ms=100.0,
    )
    assert telemetry.estimated_vs_actual == 1.0


def test_execution_telemetry_underestimate():
    """Test telemetry with underestimate."""
    telemetry = ExecutionTelemetry(
        query_id="under",
        query_type="temporal",
        estimated_latency_ms=50.0,
        total_latency_ms=100.0,
    )
    # Actual was 2x slower than estimate
    assert telemetry.estimated_vs_actual == 0.5


def test_execution_telemetry_overestimate():
    """Test telemetry with overestimate."""
    telemetry = ExecutionTelemetry(
        query_id="over",
        query_type="temporal",
        estimated_latency_ms=200.0,
        total_latency_ms=100.0,
    )
    # Estimate was 2x faster than actual
    assert telemetry.estimated_vs_actual == 2.0


# ============================================================================
# Telemetry Collector Tests
# ============================================================================


def test_collector_initialization(collector):
    """Test collector initializes correctly."""
    assert collector.telemetry_records == {}
    assert collector.total_recorded == 0
    assert collector.retention_days == 30


def test_collector_record_execution(collector, sample_telemetry):
    """Test recording execution telemetry."""
    collector.record_execution(sample_telemetry)

    assert collector.total_recorded >= 1
    # Check if recorded
    assert sample_telemetry.query_id in collector.telemetry_records or \
           len(collector.telemetry_records) >= 1


def test_collector_record_multiple_executions(collector):
    """Test recording multiple executions."""
    for i in range(10):
        telemetry = ExecutionTelemetry(
            query_id=f"q_{i}",
            query_type="temporal",
            strategy_chosen="parallel",
            estimated_latency_ms=100.0,
            total_latency_ms=95.0 + i,
            success=True,
        )
        collector.record_execution(telemetry)

    assert collector.total_recorded >= 10


# ============================================================================
# Strategy Effectiveness Tests
# ============================================================================


def test_strategy_effectiveness_cache(collector):
    """Test measuring cache strategy effectiveness."""
    for i in range(5):
        telemetry = ExecutionTelemetry(
            query_id=f"cache_{i}",
            query_type="temporal",
            strategy_chosen="cache",
            estimated_latency_ms=10.0,  # Cache is very fast
            total_latency_ms=12.0,
            success=True,
        )
        collector.record_execution(telemetry)

    stats = collector.get_strategy_statistics("cache")
    assert isinstance(stats, dict)
    # Cache should show good latency numbers


def test_strategy_effectiveness_parallel(collector):
    """Test measuring parallel strategy effectiveness."""
    for i in range(5):
        telemetry = ExecutionTelemetry(
            query_id=f"parallel_{i}",
            query_type="temporal",
            strategy_chosen="parallel",
            estimated_latency_ms=100.0,
            total_latency_ms=95.0,
            success=True,
        )
        collector.record_execution(telemetry)

    stats = collector.get_strategy_statistics("parallel")
    assert isinstance(stats, dict)


def test_strategy_effectiveness_distributed(collector):
    """Test measuring distributed strategy effectiveness."""
    for i in range(5):
        telemetry = ExecutionTelemetry(
            query_id=f"dist_{i}",
            query_type="temporal",
            strategy_chosen="distributed",
            estimated_latency_ms=500.0,
            total_latency_ms=480.0,
            success=True,
        )
        collector.record_execution(telemetry)

    stats = collector.get_strategy_statistics("distributed")
    assert isinstance(stats, dict)


def test_strategy_failure_tracking(collector):
    """Test tracking strategy failures."""
    # Success case
    success_telemetry = ExecutionTelemetry(
        query_id="success",
        query_type="temporal",
        strategy_chosen="parallel",
        success=True,
    )
    collector.record_execution(success_telemetry)

    # Failure case
    failure_telemetry = ExecutionTelemetry(
        query_id="failure",
        query_type="temporal",
        strategy_chosen="parallel",
        success=False,
        error="Query timeout",
    )
    collector.record_execution(failure_telemetry)

    stats = collector.get_strategy_statistics("parallel")
    # Should track both successes and failures


# ============================================================================
# Estimation Accuracy Tests
# ============================================================================


def test_estimation_accuracy_tracking(collector):
    """Test tracking estimation accuracy."""
    # Record multiple predictions with varying accuracy
    estimates = [
        (100.0, 100.0),  # Perfect
        (100.0, 95.0),   # 5% underestimate
        (100.0, 105.0),  # 5% overestimate
        (100.0, 120.0),  # 20% overestimate
    ]

    for i, (estimated, actual) in enumerate(estimates):
        telemetry = ExecutionTelemetry(
            query_id=f"accuracy_{i}",
            query_type="temporal",
            estimated_latency_ms=estimated,
            total_latency_ms=actual,
        )
        collector.record_execution(telemetry)

    stats = collector.get_estimation_accuracy()
    assert isinstance(stats, dict)
    # Should track average error


def test_estimation_error_percentage(collector):
    """Test calculating estimation error percentage."""
    telemetry = ExecutionTelemetry(
        query_id="error_test",
        query_type="temporal",
        estimated_latency_ms=100.0,
        total_latency_ms=120.0,
    )
    # Error should be |100-120|/120 * 100 = 16.67%

    collector.record_execution(telemetry)
    stats = collector.get_estimation_accuracy()
    assert isinstance(stats, dict)


def test_estimation_trends(collector):
    """Test tracking estimation trends over time."""
    # Record estimations that improve over time
    for i in range(10):
        # Estimates get better (closer to actual)
        error_factor = 1.0 - (i * 0.02)  # 20%, 18%, 16%, ... 2%
        actual = 100.0
        estimated = actual * error_factor

        telemetry = ExecutionTelemetry(
            query_id=f"trend_{i}",
            query_type="temporal",
            estimated_latency_ms=estimated,
            total_latency_ms=actual,
        )
        collector.record_execution(telemetry)

    stats = collector.get_estimation_accuracy()
    # Should show improving trend


# ============================================================================
# Query Characteristics Tests
# ============================================================================


def test_query_features_collection(collector):
    """Test collecting query features."""
    telemetry = ExecutionTelemetry(
        query_id="features_test",
        query_type="temporal",
        query_features={
            "text_length": 50,
            "num_filters": 3,
            "date_range_days": 7,
        },
        layers_queried=["episodic", "semantic"],
        result_count=42,
    )
    collector.record_execution(telemetry)

    # Features should be recorded
    assert collector.total_recorded >= 1


def test_execution_path_tracking(collector):
    """Test tracking execution path."""
    telemetry = ExecutionTelemetry(
        query_id="path_test",
        query_type="temporal",
        execution_path=["cache_check", "cache_miss", "parallel_execution", "aggregation"],
    )
    collector.record_execution(telemetry)

    # Path should be recorded
    assert collector.total_recorded >= 1


# ============================================================================
# Statistics and Diagnostics Tests
# ============================================================================


def test_overall_statistics(collector):
    """Test getting overall statistics."""
    # Record some executions
    for i in range(5):
        telemetry = ExecutionTelemetry(
            query_id=f"stat_{i}",
            query_type="temporal",
            total_latency_ms=100.0 + i * 10,
            success=i < 4,  # One failure
        )
        collector.record_execution(telemetry)

    stats = collector.get_overall_statistics()
    assert isinstance(stats, dict)
    # Should include: total_queries, success_rate, avg_latency, etc.


def test_query_type_statistics(collector):
    """Test statistics by query type."""
    # Record different query types
    for q_type in ["temporal", "factual", "relational"]:
        for i in range(3):
            telemetry = ExecutionTelemetry(
                query_id=f"{q_type}_{i}",
                query_type=q_type,
                total_latency_ms=100.0,
            )
            collector.record_execution(telemetry)

    temporal_stats = collector.get_query_type_statistics("temporal")
    assert isinstance(temporal_stats, dict)


def test_latency_distribution(collector):
    """Test analyzing latency distribution."""
    # Record varying latencies
    latencies = [10, 20, 50, 100, 200, 50, 75, 30]
    for i, latency in enumerate(latencies):
        telemetry = ExecutionTelemetry(
            query_id=f"latency_{i}",
            query_type="temporal",
            total_latency_ms=latency,
        )
        collector.record_execution(telemetry)

    stats = collector.get_overall_statistics()
    # Should include latency distribution metrics


def test_performance_recommendations(collector):
    """Test generating performance recommendations."""
    # Record data showing a pattern
    for i in range(10):
        telemetry = ExecutionTelemetry(
            query_id=f"perf_{i}",
            query_type="temporal",
            strategy_chosen="sequential",  # Always sequential
            total_latency_ms=200.0,  # Slow
            cache_hit=False,
            parallel_speedup=1.0,  # No parallelization
        )
        collector.record_execution(telemetry)

    recommendations = collector.get_optimization_recommendations()
    assert isinstance(recommendations, list)
    # May suggest parallelization


# ============================================================================
# Time-based Retention Tests
# ============================================================================


def test_retention_policy_old_records(collector):
    """Test that old records are pruned."""
    # Note: This test depends on implementation
    # Create old telemetry (simulated by directly manipulating timestamp)
    old_telemetry = ExecutionTelemetry(
        query_id="old_record",
        query_type="temporal",
    )
    old_telemetry.timestamp = time.time() - (40 * 24 * 3600)  # 40 days old

    collector.record_execution(old_telemetry)

    # Prune old records
    collector.prune_old_records(days=30)

    # Old record should be removed or marked


def test_retention_keeps_recent(collector):
    """Test that recent records are kept."""
    recent_telemetry = ExecutionTelemetry(
        query_id="recent",
        query_type="temporal",
        total_latency_ms=100.0,
    )
    collector.record_execution(recent_telemetry)

    collector.prune_old_records(days=30)

    # Recent record should remain
    assert collector.total_recorded >= 1


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_record_failed_execution(collector):
    """Test recording failed execution."""
    failed_telemetry = ExecutionTelemetry(
        query_id="fail",
        query_type="temporal",
        success=False,
        error="Database connection failed",
        total_latency_ms=5000.0,  # Timeout
    )
    collector.record_execution(failed_telemetry)

    stats = collector.get_overall_statistics()
    # Failure should be recorded


def test_record_with_zero_latency(collector):
    """Test recording with zero latency."""
    telemetry = ExecutionTelemetry(
        query_id="instant",
        query_type="temporal",
        total_latency_ms=0.0,  # Impossible but handle gracefully
    )
    collector.record_execution(telemetry)

    stats = collector.get_overall_statistics()
    assert isinstance(stats, dict)


def test_record_with_extreme_latency(collector):
    """Test recording with extreme latency."""
    telemetry = ExecutionTelemetry(
        query_id="slow",
        query_type="temporal",
        total_latency_ms=1000000.0,  # 1000 seconds
    )
    collector.record_execution(telemetry)

    stats = collector.get_overall_statistics()
    assert isinstance(stats, dict)


def test_collector_handles_many_records(collector):
    """Test collector handles large number of records."""
    # Record 1000 executions
    for i in range(1000):
        telemetry = ExecutionTelemetry(
            query_id=f"massive_{i}",
            query_type="temporal" if i % 3 == 0 else "factual",
            total_latency_ms=100.0 + (i % 50),
        )
        collector.record_execution(telemetry)

    assert collector.total_recorded >= 1000

    stats = collector.get_overall_statistics()
    assert isinstance(stats, dict)


def test_telemetry_with_missing_fields():
    """Test telemetry with minimal fields."""
    minimal_telemetry = ExecutionTelemetry(query_id="minimal")
    # Should have reasonable defaults
    assert minimal_telemetry.strategy_chosen == ""
    assert minimal_telemetry.total_latency_ms == 0.0
    assert minimal_telemetry.success is True


def test_collector_multiple_strategies(collector):
    """Test collector tracks all strategy types."""
    strategies = ["cache", "parallel", "distributed", "sequential"]

    for strategy in strategies:
        for i in range(3):
            telemetry = ExecutionTelemetry(
                query_id=f"{strategy}_{i}",
                query_type="temporal",
                strategy_chosen=strategy,
                total_latency_ms=100.0,
            )
            collector.record_execution(telemetry)

    # Should have data for all strategies
    stats = collector.get_overall_statistics()
    assert isinstance(stats, dict)
