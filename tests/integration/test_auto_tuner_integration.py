"""Integration tests for auto-tuning system (Phase 7a).

Tests the PerformanceProfiler, AutoTuner, and integration with manager.recall()
to verify adaptive parameter optimization works end-to-end.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from athena.optimization.performance_profiler import (
    PerformanceProfiler,
    QueryMetrics,
    LayerMetrics,
)
from athena.optimization.auto_tuner import (
    AutoTuner,
    TuningStrategy,
    TuningConfig,
)


class TestPerformanceProfiler:
    """Test PerformanceProfiler functionality."""

    def test_record_single_query(self):
        """Test recording a single query metric."""
        profiler = PerformanceProfiler()

        metrics = QueryMetrics(
            query_id="q1",
            query_text="What was the failing test?",
            query_type="temporal",
            timestamp=time.time(),
            latency_ms=42.5,
            memory_mb=12.3,
            cache_hit=True,
            result_count=3,
            layers_queried=["episodic", "semantic"],
            layer_latencies={"episodic": 10.2, "semantic": 32.3},
            success=True,
        )

        profiler.record_query(metrics)
        assert len(profiler.metrics) == 1
        assert profiler.metrics[0].query_id == "q1"

    def test_record_multiple_queries(self):
        """Test recording multiple queries."""
        profiler = PerformanceProfiler()

        for i in range(10):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text=f"Query {i}",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=50.0 + i * 5,
                memory_mb=10.0,
                cache_hit=i % 2 == 0,
                result_count=3,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 50.0 + i * 5},
                success=True,
            )
            profiler.record_query(metrics)

        assert len(profiler.metrics) == 10

    def test_get_layer_metrics(self):
        """Test retrieving layer aggregate metrics."""
        profiler = PerformanceProfiler()

        # Record 5 queries for episodic layer
        for i in range(5):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text=f"Query {i}",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=100.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 100.0},
                success=True,
            )
            profiler.record_query(metrics)

        layer_metrics = profiler.get_layer_metrics("episodic")
        assert layer_metrics is not None
        assert layer_metrics.total_queries == 5
        assert layer_metrics.avg_latency_ms == 100.0

    def test_get_query_type_metrics(self):
        """Test retrieving query type metrics."""
        profiler = PerformanceProfiler()

        # Record temporal queries
        for i in range(3):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text=f"When was {i}?",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=50.0,
                memory_mb=5.0,
                cache_hit=False,
                result_count=2,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 50.0},
                success=True,
            )
            profiler.record_query(metrics)

        # Record factual queries
        for i in range(2):
            metrics = QueryMetrics(
                query_id=f"f{i}",
                query_text=f"What is {i}?",
                query_type="factual",
                timestamp=time.time(),
                latency_ms=100.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=3,
                layers_queried=["semantic"],
                layer_latencies={"semantic": 100.0},
                success=True,
            )
            profiler.record_query(metrics)

        temporal_metrics = profiler.get_query_type_metrics("temporal")
        factual_metrics = profiler.get_query_type_metrics("factual")

        assert temporal_metrics.total_queries == 3
        assert temporal_metrics.avg_latency_ms == 50.0
        assert factual_metrics.total_queries == 2
        assert factual_metrics.avg_latency_ms == 100.0

    def test_cache_effectiveness(self):
        """Test cache hit rate calculation."""
        profiler = PerformanceProfiler()

        # 7 cache hits, 3 misses
        for i in range(7):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Same query",
                query_type="factual",
                timestamp=time.time(),
                latency_ms=10.0,  # Fast because cached
                memory_mb=1.0,
                cache_hit=True,
                result_count=5,
                layers_queried=["semantic"],
                layer_latencies={},
                success=True,
            )
            profiler.record_query(metrics)

        for i in range(3):
            metrics = QueryMetrics(
                query_id=f"miss{i}",
                query_text=f"New query {i}",
                query_type="factual",
                timestamp=time.time(),
                latency_ms=100.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=5,
                layers_queried=["semantic"],
                layer_latencies={"semantic": 100.0},
                success=True,
            )
            profiler.record_query(metrics)

        cache_stats = profiler.get_cache_effectiveness()
        assert cache_stats["overall"] == pytest.approx(0.7, rel=0.01)

    def test_trending_queries(self):
        """Test identification of trending queries."""
        profiler = PerformanceProfiler()

        # Record same query multiple times
        for i in range(5):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="What was the failing test?",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=50.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=3,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 50.0},
                success=True,
            )
            profiler.record_query(metrics)

        trending = profiler.get_trending_queries(limit=1)
        assert len(trending) == 1
        assert trending[0] == "What was the failing test?"

    def test_slow_queries(self):
        """Test identification of slow queries."""
        profiler = PerformanceProfiler()

        # Record mix of fast and slow queries
        latencies = [10, 20, 30, 40, 50, 500, 550, 600]
        for i, latency in enumerate(latencies):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text=f"Query {i} ({latency}ms)",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=float(latency),
                memory_mb=10.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": float(latency)},
                success=True,
            )
            profiler.record_query(metrics)

        slow = profiler.get_slow_queries(percentile=90, limit=3)
        # Should get the slowest queries
        assert len(slow) <= 3
        assert slow[0][1] >= 500  # First (slowest) should be >= 500ms


class TestAutoTuner:
    """Test AutoTuner functionality."""

    def test_initialization(self):
        """Test AutoTuner initialization."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, strategy=TuningStrategy.LATENCY)

        assert tuner.strategy == TuningStrategy.LATENCY
        assert tuner.current_config.max_concurrent == 5  # Default
        assert tuner.current_config.strategy == TuningStrategy.LATENCY

    def test_get_optimized_config_insufficient_samples(self):
        """Test that tuner returns current config with insufficient samples."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, min_samples=10)

        # Record only 5 queries
        for i in range(5):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=100.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 100.0},
                success=True,
            )
            profiler.record_query(metrics)

        config = tuner.get_optimized_config()
        assert config == tuner.current_config  # Should not change

    def test_optimal_concurrency_fast_queries(self):
        """Test concurrency tuning for fast queries."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, strategy=TuningStrategy.LATENCY, adjustment_interval=1)

        # Record fast queries (p99 < 100ms)
        for i in range(15):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Fast query",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=50.0,
                memory_mb=5.0,
                cache_hit=False,
                result_count=2,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 50.0},
                success=True,
                parallel_execution=True,
            )
            profiler.record_query(metrics)

        config = tuner.get_optimized_config("temporal")
        # Fast queries should result in higher concurrency
        assert config.max_concurrent >= tuner.MIN_CONCURRENT

    def test_optimal_timeout_by_strategy(self):
        """Test timeout calculation varies by strategy."""
        profiler = PerformanceProfiler()

        # Record consistent metrics
        for i in range(15):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=200.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 200.0},
                success=True,
            )
            profiler.record_query(metrics)

        # Test different strategies
        tuner_latency = AutoTuner(
            profiler, strategy=TuningStrategy.LATENCY, adjustment_interval=1
        )
        config_latency = tuner_latency.get_optimized_config()

        tuner_throughput = AutoTuner(
            profiler, strategy=TuningStrategy.THROUGHPUT, adjustment_interval=1
        )
        config_throughput = tuner_throughput.get_optimized_config()

        # Latency strategy should have more aggressive timeout
        assert config_latency.timeout_seconds < config_throughput.timeout_seconds

    def test_update_strategy(self):
        """Test updating tuning strategy."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, strategy=TuningStrategy.BALANCED)

        assert tuner.strategy == TuningStrategy.BALANCED
        tuner.update_strategy(TuningStrategy.LATENCY)
        assert tuner.strategy == TuningStrategy.LATENCY

    def test_get_tuning_report(self):
        """Test generation of tuning report."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler)

        # Record some metrics
        for i in range(15):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=100.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 100.0},
                success=True,
            )
            profiler.record_query(metrics)

        report = tuner.get_tuning_report()
        assert "strategy" in report
        assert "current_config" in report
        assert "metrics" in report
        assert report["strategy"] == "balanced"


class TestAutoTuningIntegration:
    """Test auto-tuning integration with manager."""

    def test_profiler_accepts_query_metrics(self):
        """Test that manager can record query metrics properly."""
        profiler = PerformanceProfiler()

        # Simulate what manager does
        metrics = QueryMetrics(
            query_id="q_test",
            query_text="What was the failing test?",
            query_type="temporal",
            timestamp=time.time(),
            latency_ms=45.2,
            memory_mb=12.5,
            cache_hit=False,
            result_count=3,
            layers_queried=["episodic", "semantic"],
            layer_latencies={"episodic": 15.0, "semantic": 30.2},
            success=True,
            parallel_execution=True,
            concurrency_level=5,
        )

        profiler.record_query(metrics)
        assert len(profiler.metrics) == 1
        recorded = profiler.metrics[0]
        assert recorded.query_text == "What was the failing test?"
        assert recorded.parallel_execution is True

    def test_auto_tuner_works_with_profiler(self):
        """Test that AutoTuner correctly uses PerformanceProfiler."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, adjustment_interval=10)

        # Record 15 queries
        for i in range(15):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test query",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=75.0,
                memory_mb=8.0,
                cache_hit=i % 3 == 0,
                result_count=2,
                layers_queried=["episodic", "semantic"],
                layer_latencies={"episodic": 25.0, "semantic": 50.0},
                success=True,
                parallel_execution=i >= 5,  # Enable after 5 queries
            )
            profiler.record_query(metrics)

        # After enough metrics, get optimized config
        config = tuner.get_optimized_config("temporal")
        assert config is not None
        assert config.max_concurrent > 0
        assert config.timeout_seconds > 0

    def test_tuning_improves_under_load(self):
        """Test that tuner adjusts parameters as load characteristics change."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, adjustment_interval=10)

        # Phase 1: Light load with fast queries
        for i in range(10):
            metrics = QueryMetrics(
                query_id=f"light_{i}",
                query_text="Fast query",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=50.0,
                memory_mb=5.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 50.0},
                success=True,
            )
            profiler.record_query(metrics)

        config_light = tuner.get_optimized_config("temporal")
        tuner.current_config = TuningConfig()  # Reset for next phase

        # Phase 2: Heavy load with slow queries
        for i in range(10):
            metrics = QueryMetrics(
                query_id=f"heavy_{i}",
                query_text="Slow query",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=500.0,
                memory_mb=50.0,
                cache_hit=False,
                result_count=5,
                layers_queried=["episodic", "semantic", "graph"],
                layer_latencies={
                    "episodic": 100.0,
                    "semantic": 200.0,
                    "graph": 200.0,
                },
                success=True,
            )
            profiler.record_query(metrics)

        config_heavy = tuner.get_optimized_config("temporal")

        # Heavy queries should have lower concurrency than light queries
        assert config_heavy.max_concurrent <= config_light.max_concurrent
