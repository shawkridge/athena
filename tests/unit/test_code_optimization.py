"""Tests for performance optimization system."""

import pytest
import time

from src.athena.code_search.code_optimization import (
    OptimizationLevel,
    PerformanceMetrics,
    QueryOptimizer,
    SearchOptimizer,
    BatchOptimizer,
    PerformanceProfiler,
    OptimizationEngine,
)


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = PerformanceMetrics(
            operation="test_op",
            execution_time_ms=100.5,
            items_processed=10,
        )

        assert metrics.operation == "test_op"
        assert metrics.execution_time_ms == 100.5
        assert metrics.items_processed == 10

    def test_throughput_calculation(self):
        """Test throughput calculation."""
        metrics = PerformanceMetrics(
            operation="test",
            execution_time_ms=1000,  # 1 second
            items_processed=100,
        )

        throughput = metrics.calculate_throughput()
        assert throughput == 100.0  # 100 ops/sec


class TestQueryOptimizer:
    """Tests for QueryOptimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create query optimizer."""
        return QueryOptimizer()

    def test_optimize_query_none_level(self, optimizer):
        """Test no optimization."""
        query = "find functions with high complexity"
        optimized = optimizer.optimize_query(query, OptimizationLevel.NONE)
        assert optimized == query

    def test_optimize_query_basic(self, optimizer):
        """Test basic optimization."""
        query = "find   functions   that   validate"
        optimized = optimizer.optimize_query(query, OptimizationLevel.BASIC)

        # Should remove extra spaces and stop words
        assert "  " not in optimized
        assert len(optimized.split()) <= len(query.split())

    def test_optimize_query_aggressive(self, optimizer):
        """Test aggressive optimization."""
        query = "find small x function big validate"
        optimized = optimizer.optimize_query(query, OptimizationLevel.AGGRESSIVE)

        # Should reorder terms (longer first)
        terms = optimized.split()
        assert len(terms) > 0

    def test_predict_query_cost(self, optimizer):
        """Test query cost prediction."""
        simple_query = "process"
        complex_query = "find functions with high complexity and validate with deep analysis"

        simple_cost = optimizer.predict_query_cost(simple_query)
        complex_cost = optimizer.predict_query_cost(complex_query)

        assert simple_cost < complex_cost
        assert 0.0 <= simple_cost <= 1.0
        assert 0.0 <= complex_cost <= 1.0

    def test_record_query_performance(self, optimizer):
        """Test recording query performance."""
        metrics = PerformanceMetrics(operation="query", execution_time_ms=50.0)
        optimizer.record_query_performance("test query", metrics)

        assert "test query" in optimizer.optimization_history


class TestSearchOptimizer:
    """Tests for SearchOptimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create search optimizer."""
        return SearchOptimizer()

    def test_optimize_result_processing_none(self, optimizer):
        """Test no optimization."""
        results = [
            {"name": "func1", "combined_score": 0.9},
            {"name": "func2", "combined_score": 0.8},
        ]

        optimized = optimizer.optimize_result_processing(results, OptimizationLevel.NONE)
        assert optimized == results

    def test_optimize_deduplication(self, optimizer):
        """Test deduplication."""
        results = [
            {"name": "func1", "file_path": "utils.py", "combined_score": 0.9},
            {"name": "func1", "file_path": "utils.py", "combined_score": 0.9},
            {"name": "func2", "file_path": "tools.py", "combined_score": 0.8},
        ]

        optimized = optimizer.optimize_result_processing(results, OptimizationLevel.BASIC)
        assert len(optimized) == 2

    def test_optimize_sorting(self, optimizer):
        """Test score-based sorting."""
        results = [
            {"name": "func1", "combined_score": 0.7},
            {"name": "func2", "combined_score": 0.95},
            {"name": "func3", "combined_score": 0.8},
        ]

        optimized = optimizer.optimize_result_processing(results, OptimizationLevel.AGGRESSIVE)
        scores = [r.get("combined_score", 0) for r in optimized]

        # Should be in descending order
        assert scores == sorted(scores, reverse=True)

    def test_estimate_result_quality(self, optimizer):
        """Test result quality estimation."""
        results = [
            {"name": "f1", "combined_score": 1.0},
            {"name": "f2", "combined_score": 0.8},
            {"name": "f3", "combined_score": 0.6},
        ]

        quality = optimizer.estimate_result_quality(results)
        assert 0.0 <= quality <= 1.0
        assert quality > 0.7


class TestBatchOptimizer:
    """Tests for BatchOptimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create batch optimizer."""
        return BatchOptimizer(optimal_batch_size=100)

    def test_calculate_batch_size(self, optimizer):
        """Test batch size calculation."""
        batch_size = optimizer.calculate_optimal_batch_size(
            items_count=1000,
            item_size_bytes=1000,
            memory_limit_mb=10,
        )

        assert batch_size > 0
        assert batch_size <= 100

    def test_batch_items(self, optimizer):
        """Test batching items."""
        items = list(range(250))
        batches = optimizer.batch_items(items, batch_size=100)

        assert len(batches) == 3
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 50

    def test_batch_with_auto_size(self, optimizer):
        """Test batching with automatic size."""
        items = list(range(150))
        batches = optimizer.batch_items(items)

        assert len(batches) > 0
        assert sum(len(b) for b in batches) == len(items)


class TestPerformanceProfiler:
    """Tests for PerformanceProfiler."""

    @pytest.fixture
    def profiler(self):
        """Create profiler."""
        return PerformanceProfiler()

    def test_profile_operation(self, profiler):
        """Test profiling an operation."""
        def dummy_operation():
            time.sleep(0.01)
            return "result"

        result, metrics = profiler.profile_operation("test_op", dummy_operation)

        assert result == "result"
        assert metrics.execution_time_ms > 0
        assert metrics.operation == "test_op"

    def test_operation_stats(self, profiler):
        """Test getting operation stats."""
        def dummy_op():
            time.sleep(0.01)

        # Profile multiple times
        for _ in range(3):
            profiler.profile_operation("op", dummy_op)

        stats = profiler.get_operation_stats("op")

        assert stats["count"] == 3
        assert stats["avg_ms"] > 0
        assert stats["min_ms"] <= stats["avg_ms"] <= stats["max_ms"]

    def test_get_slowest_operations(self, profiler):
        """Test getting slowest operations."""
        def slow_op():
            time.sleep(0.05)

        def fast_op():
            time.sleep(0.01)

        profiler.profile_operation("slow", slow_op)
        profiler.profile_operation("fast", fast_op)

        slowest = profiler.get_slowest_operations(1)

        assert slowest[0][0] == "slow"

    def test_generate_performance_report(self, profiler):
        """Test report generation."""
        def op():
            pass

        profiler.profile_operation("test", op)

        report = profiler.generate_performance_report()

        assert "PERFORMANCE PROFILING REPORT" in report
        assert "test" in report


class TestOptimizationEngine:
    """Tests for OptimizationEngine."""

    @pytest.fixture
    def engine(self):
        """Create optimization engine."""
        return OptimizationEngine()

    def test_engine_creation(self, engine):
        """Test creating engine."""
        assert engine.query_optimizer is not None
        assert engine.search_optimizer is not None
        assert engine.batch_optimizer is not None
        assert engine.profiler is not None

    def test_optimize_search_pipeline(self, engine):
        """Test optimizing search pipeline."""
        query = "find functions"

        def execute_search(q):
            return [
                {"name": "func1", "combined_score": 0.9},
                {"name": "func2", "combined_score": 0.8},
            ]

        def process_results(r):
            return r

        results, info = engine.optimize_search_pipeline(
            query,
            execute_search,
            process_results,
            OptimizationLevel.BASIC,
        )

        assert len(results) > 0
        assert info is not None
        assert "query_cost_estimate" in info
        assert "execution_metrics" in info

    def test_set_optimization_level(self, engine):
        """Test setting optimization level."""
        engine.set_optimization_level(OptimizationLevel.MAXIMUM)
        assert engine.optimization_level == OptimizationLevel.MAXIMUM

    def test_get_performance_insights(self, engine):
        """Test getting performance insights."""
        def dummy():
            pass

        engine.profiler.profile_operation("op1", dummy)

        insights = engine.get_performance_insights()

        assert "optimization_level" in insights
        assert "slowest_operations" in insights
        assert "recommendation" in insights


class TestOptimizationIntegration:
    """Integration tests for optimization."""

    def test_full_optimization_workflow(self):
        """Test complete optimization workflow."""
        engine = OptimizationEngine()

        query = "find functions with high complexity in utils module"

        def mock_search(q):
            # Simulate search results with some duplication
            return [
                {"name": "process_data", "file_path": "utils.py", "combined_score": 0.95},
                {"name": "process_data", "file_path": "utils.py", "combined_score": 0.95},
                {"name": "handle_data", "file_path": "utils.py", "combined_score": 0.85},
                {"name": "validate_data", "file_path": "validators.py", "combined_score": 0.75},
            ]

        def mock_process(results):
            return results

        results, info = engine.optimize_search_pipeline(
            query,
            mock_search,
            mock_process,
            OptimizationLevel.AGGRESSIVE,
        )

        # After optimization: deduplication and sorting
        assert len(results) <= 4
        assert results[0]["combined_score"] >= results[-1]["combined_score"]
        assert info["deduplication_ratio"] > 0
        assert info["result_quality"] > 0

    def test_optimization_levels_comparison(self):
        """Test different optimization levels."""
        query_optimizer = QueryOptimizer()
        query = "find functions that validate input with high complexity"

        optimized_basic = query_optimizer.optimize_query(query, OptimizationLevel.BASIC)
        optimized_aggressive = query_optimizer.optimize_query(query, OptimizationLevel.AGGRESSIVE)
        optimized_max = query_optimizer.optimize_query(query, OptimizationLevel.MAXIMUM)

        # More aggressive = more optimized (shorter or rearranged)
        assert len(optimized_basic) <= len(query)
        assert len(optimized_aggressive) <= len(optimized_basic)
