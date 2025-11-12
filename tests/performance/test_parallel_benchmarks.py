"""Performance benchmarks for parallel query execution.

Measures performance improvements from parallel Tier 1 execution:
- Concurrent vs sequential execution
- Concurrency limit impact
- Timeout overhead
- Real-world layer query simulation
"""

import asyncio
import pytest
import time

from athena.optimization.parallel_executor import (
    ParallelLayerExecutor,
    ParallelTier1Executor,
    QueryTask,
)


class TestParallelExecutionBenchmarks:
    """Benchmark parallel execution performance."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_parallel_execution_5_layers(self):
        """Test parallel execution of 5 layer queries (~100ms each)."""
        async def mock_layer_query():
            await asyncio.sleep(0.1)
            return ["result1", "result2"]

        executor = ParallelLayerExecutor()

        tasks = [
            QueryTask(f"layer_{i}", mock_layer_query, (), {})
            for i in range(5)
        ]

        start = time.perf_counter()
        results = await executor.execute_parallel(tasks)
        parallel_time = time.perf_counter() - start

        # All should succeed
        assert len(results) == 5
        assert all(r.success for r in results.values())

        # Should take ~100ms (parallel) not ~500ms (sequential)
        assert parallel_time < 0.15, f"Parallel execution too slow: {parallel_time:.3f}s"

        print(f"\nParallel 5 layers: {parallel_time*1000:.2f}ms (vs ~500ms sequential)")

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_sequential_fallback_performance(self):
        """Test sequential fallback with single task."""
        async def mock_query():
            await asyncio.sleep(0.05)
            return "result"

        executor = ParallelLayerExecutor()

        task = QueryTask("layer", mock_query, (), {})

        start = time.perf_counter()
        results = await executor.execute_parallel([task])
        elapsed = time.perf_counter() - start

        assert results["layer"].success
        assert elapsed >= 0.05

        print(f"\nSequential fallback: {elapsed*1000:.2f}ms")

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrency_limit_impact(self):
        """Test impact of concurrency limit on execution time."""
        async def slow_query():
            await asyncio.sleep(0.1)
            return "result"

        # Create 8 tasks
        tasks = [QueryTask(f"layer_{i}", slow_query, (), {}) for i in range(8)]

        # Test with different limits
        results = {}

        # Unlimited (max_concurrent=8)
        executor_unlimited = ParallelLayerExecutor(max_concurrent=8)
        start = time.perf_counter()
        await executor_unlimited.execute_parallel(tasks)
        unlimited_time = time.perf_counter() - start

        # Limited (max_concurrent=2)
        executor_limited = ParallelLayerExecutor(max_concurrent=2)
        start = time.perf_counter()
        await executor_limited.execute_parallel(tasks)
        limited_time = time.perf_counter() - start

        print(f"\nConcurrency limits (8 tasks @ 0.1s each):")
        print(f"  max_concurrent=8: {unlimited_time*1000:.2f}ms")
        print(f"  max_concurrent=2: {limited_time*1000:.2f}ms")

        # Limited should take longer
        assert limited_time > unlimited_time

    @pytest.mark.benchmark
    def test_sync_wrapper_performance(self):
        """Test performance of sync wrapper."""
        async def fast_query():
            return "result"

        executor = ParallelLayerExecutor()
        task = QueryTask("test", fast_query, (), {})

        start = time.perf_counter()
        for _ in range(100):
            results = executor.execute_parallel_sync([task])
        elapsed = time.perf_counter() - start

        avg_time = elapsed / 100 * 1000  # ms

        print(f"\nSync wrapper (100 iterations): {avg_time:.2f}ms avg per call")

        # Should be fast
        assert avg_time < 2.0, f"Sync wrapper too slow: {avg_time:.2f}ms"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_timeout_performance_impact(self):
        """Test timeout overhead on execution time."""
        async def fast_query():
            return "result"

        async def slow_query():
            await asyncio.sleep(0.2)
            return "result"

        executor = ParallelLayerExecutor()

        # Task with generous timeout
        task_generous = QueryTask(
            "generous", slow_query, (), {}, timeout_seconds=10.0
        )

        # Task with tight timeout (should fail)
        task_tight = QueryTask("tight", slow_query, (), {}, timeout_seconds=0.05)

        start = time.perf_counter()
        results_generous = await executor.execute_parallel([task_generous])
        generous_time = time.perf_counter() - start

        start = time.perf_counter()
        results_tight = await executor.execute_parallel([task_tight])
        tight_time = time.perf_counter() - start

        print(f"\nTimeout overhead:")
        print(f"  Generous (10s, succeeds): {generous_time*1000:.3f}ms")
        print(f"  Tight (50ms, should timeout): {tight_time*1000:.3f}ms")

        # Generous should succeed
        assert results_generous["generous"].success
        # Tight timeout should fail
        assert not results_tight["tight"].success

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_real_world_tier1_simulation(self):
        """Simulate real Tier 1 execution with varying latencies."""
        async def episodic_query():
            await asyncio.sleep(0.08)  # ~80ms episodic query
            return ["event1", "event2", "event3"]

        async def semantic_query():
            await asyncio.sleep(0.12)  # ~120ms semantic search
            return ["fact1", "fact2", "fact3", "fact4"]

        async def procedural_query():
            await asyncio.sleep(0.06)  # ~60ms procedural lookup
            return ["proc1", "proc2"]

        async def prospective_query():
            await asyncio.sleep(0.05)  # ~50ms task lookup
            return ["task1"]

        async def graph_query():
            await asyncio.sleep(0.07)  # ~70ms graph traversal
            return ["relation1", "relation2"]

        executor = ParallelTier1Executor()

        query_methods = {
            "episodic": episodic_query,
            "semantic": semantic_query,
            "procedural": procedural_query,
            "prospective": prospective_query,
            "graph": graph_query,
        }

        # Sequential timing (80 + 120 + 60 + 50 + 70 = 380ms)
        start = time.perf_counter()
        for layer_name, query_fn in query_methods.items():
            await query_fn()
        sequential_time = time.perf_counter() - start

        # Parallel timing
        start = time.perf_counter()
        results = await executor.execute_tier_1(
            query="What happened in debugging?",
            context={"phase": "debugging"},
            k=5,
            query_methods=query_methods,
        )
        parallel_time = time.perf_counter() - start

        # Calculate speedup
        speedup = sequential_time / parallel_time

        print(f"\nReal-world Tier 1 simulation:")
        print(f"  Sequential: {sequential_time*1000:.2f}ms")
        print(f"  Parallel: {parallel_time*1000:.2f}ms")
        print(f"  Speedup: {speedup:.1f}x")

        # Should achieve 3-4x speedup with 5 layers
        assert speedup > 2.5, f"Speedup too low: {speedup:.1f}x"
        assert all(results.values()), "All layers should return results"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test performance impact of error handling."""
        async def failing_query():
            raise ValueError("Simulated error")

        async def successful_query():
            return "success"

        executor = ParallelLayerExecutor()

        tasks = [
            QueryTask("success1", successful_query, (), {}),
            QueryTask("fail", failing_query, (), {}),
            QueryTask("success2", successful_query, (), {}),
        ]

        start = time.perf_counter()
        results = await executor.execute_parallel(tasks)
        elapsed = time.perf_counter() - start

        # All should complete despite failure
        assert len(results) == 3
        assert not results["fail"].success
        assert results["success1"].success
        assert results["success2"].success

        print(f"\nError handling: {elapsed*1000:.2f}ms for 3 tasks (1 failing)")

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_statistics_tracking_overhead(self):
        """Test overhead of statistics tracking."""
        async def quick_query():
            return "result"

        executor = ParallelLayerExecutor()

        # Execute many quick tasks to measure tracking overhead
        tasks = [QueryTask(f"layer_{i}", quick_query, (), {}) for i in range(10)]

        start = time.perf_counter()
        results = await executor.execute_parallel(tasks)
        elapsed = time.perf_counter() - start

        stats = executor.get_stats()

        avg_per_task = elapsed / len(tasks) * 1000

        print(f"\nStatistics tracking:")
        print(f"  10 fast tasks: {elapsed*1000:.2f}ms ({avg_per_task:.2f}ms per task)")
        print(f"  Stats: {stats}")

        # Should be very fast even with tracking
        assert avg_per_task < 1.0, f"Per-task time too high: {avg_per_task:.2f}ms"
