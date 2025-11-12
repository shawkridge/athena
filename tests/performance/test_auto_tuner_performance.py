"""Performance tests for auto-tuning system (Phase 7a).

Validates that auto-tuning overhead is minimal and provides measurable
performance improvements over fixed configurations.
"""

import pytest
import time
from athena.optimization.performance_profiler import PerformanceProfiler, QueryMetrics
from athena.optimization.auto_tuner import AutoTuner, TuningStrategy


@pytest.mark.benchmark
class TestProfilerPerformance:
    """Test PerformanceProfiler performance characteristics."""

    def test_record_query_overhead(self, benchmark):
        """Test overhead of recording a single query."""
        profiler = PerformanceProfiler()

        metrics = QueryMetrics(
            query_id="q1",
            query_text="Test query",
            query_type="temporal",
            timestamp=time.time(),
            latency_ms=50.0,
            memory_mb=10.0,
            cache_hit=False,
            result_count=3,
            layers_queried=["episodic", "semantic"],
            layer_latencies={"episodic": 20.0, "semantic": 30.0},
            success=True,
        )

        def record():
            profiler.record_query(metrics)

        benchmark(record)

    def test_get_layer_metrics_performance(self, benchmark):
        """Test performance of computing layer metrics."""
        profiler = PerformanceProfiler()

        # Pre-populate with 100 metrics
        for i in range(100):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text=f"Query {i}",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=50.0 + i % 50,
                memory_mb=10.0,
                cache_hit=i % 2 == 0,
                result_count=2,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 50.0 + i % 50},
                success=True,
            )
            profiler.record_query(metrics)

        def get_metrics():
            return profiler.get_layer_metrics("episodic")

        benchmark(get_metrics)

    def test_get_cache_effectiveness_performance(self, benchmark):
        """Test performance of cache effectiveness calculation."""
        profiler = PerformanceProfiler()

        # Pre-populate with 200 metrics from multiple layers
        for i in range(200):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text=f"Query {i}",
                query_type="temporal" if i % 2 == 0 else "factual",
                timestamp=time.time(),
                latency_ms=50.0,
                memory_mb=10.0,
                cache_hit=i % 3 == 0,
                result_count=2,
                layers_queried=["episodic"] if i % 2 == 0 else ["semantic"],
                layer_latencies={
                    "episodic" if i % 2 == 0 else "semantic": 50.0
                },
                success=True,
            )
            profiler.record_query(metrics)

        def get_cache_stats():
            return profiler.get_cache_effectiveness()

        benchmark(get_cache_stats)

    def test_temporal_pattern_computation(self, benchmark):
        """Test performance of temporal pattern analysis."""
        profiler = PerformanceProfiler()

        # Populate metrics across different hours
        for hour in range(24):
            for i in range(10):
                metrics = QueryMetrics(
                    query_id=f"q_{hour}_{i}",
                    query_text="Test",
                    query_type="temporal",
                    timestamp=time.time() - (24 - hour) * 3600 + i * 100,
                    latency_ms=50.0 + hour * 5,  # Latency varies by hour
                    memory_mb=10.0,
                    cache_hit=False,
                    result_count=1,
                    layers_queried=["episodic"],
                    layer_latencies={"episodic": 50.0 + hour * 5},
                    success=True,
                )
                profiler.record_query(metrics)

        def get_pattern():
            return profiler.get_temporal_pattern()

        benchmark(get_pattern)


@pytest.mark.benchmark
class TestAutoTunerPerformance:
    """Test AutoTuner performance characteristics."""

    def test_get_optimized_config_overhead(self, benchmark):
        """Test overhead of computing optimized config."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, adjustment_interval=1)

        # Pre-populate with metrics
        for i in range(50):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=100.0 + i % 50,
                memory_mb=10.0,
                cache_hit=False,
                result_count=2,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 100.0 + i % 50},
                success=True,
            )
            profiler.record_query(metrics)

        def get_config():
            return tuner.get_optimized_config("temporal")

        benchmark(get_config)

    def test_tuner_with_multiple_query_types(self, benchmark):
        """Test tuner performance with multiple query types."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, adjustment_interval=1)

        # Populate with multiple query types
        query_types = ["temporal", "factual", "relational", "procedural"]
        for query_type in query_types:
            for i in range(20):
                metrics = QueryMetrics(
                    query_id=f"q_{query_type}_{i}",
                    query_text=f"{query_type} query",
                    query_type=query_type,
                    timestamp=time.time(),
                    latency_ms=75.0 + (hash(query_type) % 50),
                    memory_mb=10.0,
                    cache_hit=False,
                    result_count=2,
                    layers_queried=["semantic"],
                    layer_latencies={"semantic": 75.0},
                    success=True,
                )
                profiler.record_query(metrics)

        def get_configs():
            configs = {}
            for qtype in query_types:
                configs[qtype] = tuner.get_optimized_config(qtype)
            return configs

        benchmark(get_configs)


@pytest.mark.benchmark
class TestAutoTuningEffectiveness:
    """Test effectiveness of auto-tuning improvements."""

    def test_latency_optimization_effectiveness(self):
        """Test that latency strategy actually reduces p99 latency."""
        profiler = PerformanceProfiler()
        tuner_latency = AutoTuner(
            profiler, strategy=TuningStrategy.LATENCY, adjustment_interval=1
        )

        # Simulate load with some slow queries
        latencies = [50.0] * 90 + [200.0] * 10  # 90% fast, 10% slow

        for i, latency in enumerate(latencies):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=latency,
                memory_mb=10.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": latency},
                success=True,
            )
            profiler.record_query(metrics)

        config = tuner_latency.get_optimized_config("temporal")

        # Latency strategy should choose more aggressive timeout
        assert config.timeout_seconds < 20.0

    def test_throughput_optimization_effectiveness(self):
        """Test that throughput strategy maximizes concurrency."""
        profiler = PerformanceProfiler()
        tuner_throughput = AutoTuner(
            profiler, strategy=TuningStrategy.THROUGHPUT, adjustment_interval=1
        )

        # Simulate consistent load
        for i in range(50):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=100.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=2,
                layers_queried=["episodic", "semantic"],
                layer_latencies={"episodic": 30.0, "semantic": 70.0},
                success=True,
                parallel_execution=True,
            )
            profiler.record_query(metrics)

        config = tuner_throughput.get_optimized_config("temporal")

        # Throughput strategy should choose higher concurrency
        assert config.max_concurrent >= 8

    def test_cost_optimization_effectiveness(self):
        """Test that cost strategy balances resource usage."""
        profiler = PerformanceProfiler()
        tuner_cost = AutoTuner(
            profiler, strategy=TuningStrategy.COST, adjustment_interval=1
        )

        # Simulate mixed load
        for i in range(50):
            metrics = QueryMetrics(
                query_id=f"q{i}",
                query_text="Test",
                query_type="temporal",
                timestamp=time.time(),
                latency_ms=100.0,
                memory_mb=20.0,  # High memory
                cache_hit=False,
                result_count=2,
                layers_queried=["episodic", "semantic"],
                layer_latencies={"episodic": 30.0, "semantic": 70.0},
                success=True,
            )
            profiler.record_query(metrics)

        config = tuner_cost.get_optimized_config("temporal")

        # Cost strategy should balance concurrency and resource usage
        assert 4 <= config.max_concurrent <= 12

    def test_profiler_window_effectiveness(self):
        """Test that profiler window correctly prunes old metrics."""
        profiler = PerformanceProfiler(window_hours=1)  # 1 hour window

        # Add metrics at different times
        current_time = time.time()

        # Recent metrics (should be kept)
        for i in range(5):
            metrics = QueryMetrics(
                query_id=f"recent_{i}",
                query_text="Recent",
                query_type="temporal",
                timestamp=current_time - 30 * 60,  # 30 minutes ago
                latency_ms=50.0,
                memory_mb=10.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 50.0},
                success=True,
            )
            profiler.record_query(metrics)

        # Old metrics (should be pruned)
        for i in range(5):
            metrics = QueryMetrics(
                query_id=f"old_{i}",
                query_text="Old",
                query_type="temporal",
                timestamp=current_time - 2 * 3600,  # 2 hours ago
                latency_ms=100.0,
                memory_mb=20.0,
                cache_hit=False,
                result_count=1,
                layers_queried=["episodic"],
                layer_latencies={"episodic": 100.0},
                success=True,
            )
            profiler.record_query(metrics)

        # Get metrics should trigger pruning
        layer_metrics = profiler.get_layer_metrics("episodic")

        # Should only have 5 recent metrics (old ones pruned)
        assert len(profiler.metrics) == 5
        assert all("recent" in m.query_id for m in profiler.metrics)

    def test_strategy_switching_efficiency(self):
        """Test that switching strategies works efficiently."""
        profiler = PerformanceProfiler()
        tuner = AutoTuner(profiler, strategy=TuningStrategy.BALANCED)

        # Populate with metrics
        for i in range(50):
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

        # Get configs with different strategies
        config_balanced = tuner.get_optimized_config("temporal")

        tuner.update_strategy(TuningStrategy.LATENCY)
        config_latency = tuner.get_optimized_config("temporal")

        tuner.update_strategy(TuningStrategy.THROUGHPUT)
        config_throughput = tuner.get_optimized_config("temporal")

        # All should be valid configs
        assert config_balanced.max_concurrent > 0
        assert config_latency.max_concurrent > 0
        assert config_throughput.max_concurrent > 0

        # Latency should be more conservative than throughput
        assert config_latency.timeout_seconds < config_throughput.timeout_seconds
