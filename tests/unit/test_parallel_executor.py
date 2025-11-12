"""Tests for parallel query execution framework.

Tests cover:
- Async/sync execution patterns
- Concurrency control and semaphores
- Timeout handling
- Error isolation
- Performance improvements
- Fallback mechanisms
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from athena.optimization.parallel_executor import (
    ParallelLayerExecutor,
    ParallelTier1Executor,
    QueryTask,
    ExecutionResult,
)


class TestQueryTask:
    """Tests for QueryTask data class."""

    def test_query_task_creation(self):
        """Test basic QueryTask creation."""
        async def dummy_query(*args, **kwargs):
            return "result"

        task = QueryTask(
            layer_name="semantic",
            query_fn=dummy_query,
            args=("query", {}, 5),
            kwargs={"extra": "param"},
            timeout_seconds=10.0,
        )

        assert task.layer_name == "semantic"
        assert task.timeout_seconds == 10.0
        assert len(task.args) == 3

    def test_query_task_default_timeout(self):
        """Test default timeout for QueryTask."""
        async def dummy_query():
            pass

        task = QueryTask(
            layer_name="episodic",
            query_fn=dummy_query,
            args=(),
            kwargs={},
        )

        assert task.timeout_seconds == 10.0


class TestExecutionResult:
    """Tests for ExecutionResult data class."""

    def test_successful_result(self):
        """Test creating successful execution result."""
        result = ExecutionResult(
            layer_name="semantic",
            success=True,
            result=["item1", "item2"],
            elapsed_ms=45.5,
        )

        assert result.success
        assert result.result == ["item1", "item2"]
        assert result.error is None

    def test_failed_result(self):
        """Test creating failed execution result."""
        result = ExecutionResult(
            layer_name="episodic",
            success=False,
            error="Timeout error",
            elapsed_ms=100.0,
        )

        assert not result.success
        assert result.error == "Timeout error"
        assert result.result is None


class TestParallelLayerExecutor:
    """Tests for ParallelLayerExecutor."""

    @pytest.mark.asyncio
    async def test_single_task_execution(self):
        """Test executing a single task."""
        async def mock_query():
            return ["result1", "result2"]

        executor = ParallelLayerExecutor()
        task = QueryTask(
            layer_name="semantic",
            query_fn=mock_query,
            args=(),
            kwargs={},
        )

        results = await executor.execute_parallel([task])

        assert "semantic" in results
        assert results["semantic"].success
        assert results["semantic"].result == ["result1", "result2"]

    @pytest.mark.asyncio
    async def test_multiple_tasks_concurrent(self):
        """Test executing multiple tasks concurrently."""
        async def mock_episodic():
            await asyncio.sleep(0.1)
            return ["event1", "event2"]

        async def mock_semantic():
            await asyncio.sleep(0.1)
            return ["fact1", "fact2"]

        async def mock_procedural():
            await asyncio.sleep(0.1)
            return ["proc1", "proc2"]

        executor = ParallelLayerExecutor()

        tasks = [
            QueryTask("episodic", mock_episodic, (), {}),
            QueryTask("semantic", mock_semantic, (), {}),
            QueryTask("procedural", mock_procedural, (), {}),
        ]

        start = time.perf_counter()
        results = await executor.execute_parallel(tasks)
        elapsed = time.perf_counter() - start

        # All should succeed
        assert all(r.success for r in results.values())
        assert len(results) == 3

        # Should be roughly concurrent (~0.1s not 0.3s)
        assert elapsed < 0.25, f"Parallel execution took too long: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Test that concurrency limit is respected."""
        async def slow_query():
            await asyncio.sleep(0.2)
            return "result"

        executor = ParallelLayerExecutor(max_concurrent=2)

        # Create 5 tasks
        tasks = [
            QueryTask(f"layer_{i}", slow_query, (), {})
            for i in range(5)
        ]

        start = time.perf_counter()
        results = await executor.execute_parallel(tasks)
        elapsed = time.perf_counter() - start

        # With max_concurrent=2 and 5 tasks, expect ~0.6s (3 batches)
        assert len(results) == 5
        assert elapsed >= 0.4  # At least 2 batches worth of time

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling for long-running tasks."""
        async def slow_query():
            await asyncio.sleep(5.0)
            return "result"

        executor = ParallelLayerExecutor()

        task = QueryTask(
            layer_name="slow",
            query_fn=slow_query,
            args=(),
            kwargs={},
            timeout_seconds=0.1,
        )

        results = await executor.execute_parallel([task])

        assert not results["slow"].success
        assert "timeout" in results["slow"].error.lower()

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """Test that one task failure doesn't block others."""
        async def failing_query():
            raise ValueError("Task failed")

        async def successful_query():
            return "success"

        executor = ParallelLayerExecutor()

        tasks = [
            QueryTask("failing", failing_query, (), {}),
            QueryTask("success", successful_query, (), {}),
        ]

        results = await executor.execute_parallel(tasks)

        # Both should complete
        assert len(results) == 2
        assert not results["failing"].success
        assert results["success"].success

    @pytest.mark.asyncio
    async def test_sync_function_wrapping(self):
        """Test execution of synchronous functions."""
        def sync_query():
            return "sync_result"

        executor = ParallelLayerExecutor()

        task = QueryTask(
            layer_name="sync",
            query_fn=sync_query,
            args=(),
            kwargs={},
        )

        results = await executor.execute_parallel([task])

        assert results["sync"].success
        assert results["sync"].result == "sync_result"

    @pytest.mark.asyncio
    async def test_sequential_fallback(self):
        """Test fallback to sequential execution with single task."""
        async def mock_query():
            return "result"

        executor = ParallelLayerExecutor()

        tasks = [QueryTask("only", mock_query, (), {})]

        results = await executor.execute_parallel(tasks)

        # Should still work even with single task
        assert results["only"].success

    def test_execute_parallel_sync(self):
        """Test synchronous wrapper for parallel execution."""
        async def mock_query():
            return "result"

        executor = ParallelLayerExecutor()

        task = QueryTask(
            layer_name="test",
            query_fn=mock_query,
            args=(),
            kwargs={},
        )

        results = executor.execute_parallel_sync([task])

        assert results["test"].success
        assert results["test"].result == "result"

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test that execution statistics are tracked."""
        async def mock_query1():
            return "result1"

        async def mock_query2():
            return "result2"

        async def mock_query3():
            return "result3"

        executor = ParallelLayerExecutor()

        # Execute multiple queries (>1 task to avoid sequential fallback)
        tasks = [
            QueryTask("layer_1", mock_query1, (), {}),
            QueryTask("layer_2", mock_query2, (), {}),
            QueryTask("layer_3", mock_query3, (), {}),
        ]
        await executor.execute_parallel(tasks)

        stats = executor.get_stats()

        assert stats["parallel_queries"] == 1  # One parallel execution with 3 tasks
        assert stats["total_queries"] == 1
        assert "parallel_percentage" in stats

    def test_record_speedup(self):
        """Test recording speedup measurements."""
        executor = ParallelLayerExecutor()

        executor.record_speedup(100.0, 60.0)  # 40ms speedup
        executor.record_speedup(100.0, 70.0)  # 30ms speedup

        stats = executor.get_stats()
        avg_speedup_ms = float(stats["avg_speedup_ms"])

        assert avg_speedup_ms > 0
        assert 30 <= avg_speedup_ms <= 40  # Should be between the two values


class TestParallelTier1Executor:
    """Tests for ParallelTier1Executor."""

    @pytest.mark.asyncio
    async def test_tier1_execution_basic(self):
        """Test basic Tier 1 parallel execution."""
        async def mock_episodic(*args, **kwargs):
            return ["event1"]

        async def mock_semantic(*args, **kwargs):
            return ["fact1"]

        executor = ParallelTier1Executor()

        query_methods = {
            "episodic": mock_episodic,
            "semantic": mock_semantic,
            "procedural": AsyncMock(return_value=["proc1"]),
            "prospective": AsyncMock(return_value=["task1"]),
            "graph": AsyncMock(return_value=["rel1"]),
        }

        results = await executor.execute_tier_1(
            query="What happened recently?",
            context={"phase": "debugging"},
            k=5,
            query_methods=query_methods,
        )

        # Should have episodic and semantic results
        assert "episodic" in results
        assert "semantic" in results

    @pytest.mark.asyncio
    async def test_tier1_layer_selection(self):
        """Test that Tier 1 selects appropriate layers based on query."""
        async def mock_query(*args, **kwargs):
            return []

        executor = ParallelTier1Executor()

        query_methods = {
            "episodic": AsyncMock(return_value=[]),
            "semantic": AsyncMock(return_value=[]),
            "procedural": AsyncMock(return_value=[]),
            "prospective": AsyncMock(return_value=[]),
            "graph": AsyncMock(return_value=[]),
        }

        # Query about procedures
        await executor.execute_tier_1(
            query="How do I implement this?",
            context={},
            k=5,
            query_methods=query_methods,
        )

        # Semantic should always be called
        assert query_methods["semantic"].called

    @pytest.mark.asyncio
    async def test_tier1_context_aware_selection(self):
        """Test context-aware layer selection."""
        async def mock_query(*args, **kwargs):
            return []

        executor = ParallelTier1Executor()

        query_methods = {
            "episodic": AsyncMock(return_value=[]),
            "semantic": AsyncMock(return_value=[]),
            "procedural": AsyncMock(return_value=[]),
            "prospective": AsyncMock(return_value=[]),
            "graph": AsyncMock(return_value=[]),
        }

        # Debugging phase should trigger episodic
        await executor.execute_tier_1(
            query="What's happening?",
            context={"phase": "debugging"},
            k=5,
            query_methods=query_methods,
        )

        assert query_methods["episodic"].called

    def test_tier1_sync_wrapper(self):
        """Test synchronous wrapper for Tier 1 executor."""
        async def mock_query(*args, **kwargs):
            return ["result"]

        executor = ParallelTier1Executor()

        query_methods = {
            "semantic": mock_query,
            "episodic": mock_query,
            "procedural": mock_query,
            "prospective": mock_query,
            "graph": mock_query,
        }

        # Should not raise even though we're using sync wrapper
        results = executor.execute_tier_1_sync(
            query="Test",
            context={},
            k=5,
            query_methods=query_methods,
        )

        # Should have some results
        assert isinstance(results, dict)


class TestParallelVsSequential:
    """Compare parallel vs sequential execution performance."""

    @pytest.mark.asyncio
    async def test_parallel_faster_than_sequential(self):
        """Test that parallel execution is faster than sequential."""
        async def slow_query():
            await asyncio.sleep(0.05)
            return ["result"]

        # Sequential execution
        start = time.perf_counter()
        for _ in range(5):
            await slow_query()
        sequential_time = time.perf_counter() - start

        # Parallel execution
        executor = ParallelLayerExecutor()
        tasks = [
            QueryTask(f"layer_{i}", slow_query, (), {})
            for i in range(5)
        ]

        start = time.perf_counter()
        results = await executor.execute_parallel(tasks)
        parallel_time = time.perf_counter() - start

        # Parallel should be significantly faster
        assert parallel_time < sequential_time * 0.7, (
            f"Parallel ({parallel_time:.3f}s) not faster than sequential ({sequential_time:.3f}s)"
        )

    def test_disabled_parallel_falls_back_sequential(self):
        """Test that disabling parallel falls back to sequential."""
        def sync_query():
            time.sleep(0.05)
            return "result"

        executor = ParallelLayerExecutor(enable_parallel=False)

        task = QueryTask(
            layer_name="test",
            query_fn=sync_query,
            args=(),
            kwargs={},
        )

        results = executor.execute_parallel_sync([task])

        assert results["test"].success
