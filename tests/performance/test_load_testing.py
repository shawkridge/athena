"""Load testing and performance baseline tests for MCP tools."""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from athena.mcp.tools.memory_tools import RecallTool, RememberTool, OptimizeTool
from athena.mcp.tools.planning_tools import DecomposeTool, ValidatePlanTool
from athena.mcp.tools.system_tools import SystemHealthCheckTool, HealthReportTool
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_memory_store():
    """Create mock memory store."""
    store = Mock()
    store.recall_with_reranking = Mock(return_value=[])
    counter = [0]
    def store_memory_impl(*args, **kwargs):
        counter[0] += 1
        return counter[0]
    store.store_memory = Mock(side_effect=store_memory_impl)
    store.optimize = Mock(return_value={
        "before_count": 1000,
        "after_count": 800,
        "pruned": 200,
        "dry_run": False,
        "avg_score_before": 0.6,
        "avg_score_after": 0.75
    })
    return store


@pytest.fixture
def mock_project_manager():
    """Create mock project manager."""
    manager = Mock()
    mock_project = Mock()
    mock_project.id = 1
    manager.require_project = Mock(return_value=mock_project)
    return manager


@pytest.fixture
def mock_mcp_server():
    """Create mock MCP server."""
    server = Mock()
    server._health_checker = AsyncMock()
    server._health_checker.check = AsyncMock(return_value={
        "status": "healthy",
        "issues": []
    })
    server._health_checker.generate_report = AsyncMock(return_value={
        "summary": "System is healthy",
        "metrics": {}
    })
    return server


@pytest.fixture
def mock_planning_store():
    """Create mock planning store."""
    store = Mock()
    counter = [0]
    def store_plan_impl(*args, **kwargs):
        counter[0] += 1
        return counter[0]
    store.store_plan = Mock(side_effect=store_plan_impl)
    return store


@pytest.fixture
def mock_plan_validator():
    """Create mock plan validator."""
    validator = Mock()
    validator.validate = Mock(return_value={
        "valid": True,
        "issues": [],
        "score": 0.95
    })
    return validator


class TestLoadTestingInfrastructure:
    """Test load testing infrastructure and baselines."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_load_baseline_100_recalls(self, mock_memory_store, mock_project_manager):
        """Baseline: 100 sequential recall operations."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        results = []

        for i in range(100):
            result = await recall_tool.execute(query=f"query {i}")
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        # Performance assertions
        assert success_count == 100
        assert elapsed < 10.0  # Should complete in under 10 seconds
        print(f"100 recalls: {elapsed:.2f}s ({1000*elapsed/100:.2f}ms per op)")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_load_baseline_100_remembers(self, mock_memory_store, mock_project_manager):
        """Baseline: 100 sequential remember operations."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        start_time = time.time()
        results = []

        for i in range(100):
            result = await remember_tool.execute(content=f"Memory {i}")
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        assert success_count == 100
        assert elapsed < 10.0
        print(f"100 remembers: {elapsed:.2f}s ({1000*elapsed/100:.2f}ms per op)")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_load_baseline_100_decompose(self, mock_planning_store):
        """Baseline: 100 sequential decompose operations."""
        decompose_tool = DecomposeTool(mock_planning_store)

        start_time = time.time()
        results = []

        for i in range(100):
            result = await decompose_tool.execute(task=f"Task {i}")
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        assert success_count == 100
        assert elapsed < 10.0
        print(f"100 decompose: {elapsed:.2f}s ({1000*elapsed/100:.2f}ms per op)")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_load_baseline_100_health_checks(self, mock_mcp_server):
        """Baseline: 100 sequential health check operations."""
        health_check_tool = SystemHealthCheckTool(mock_mcp_server)

        start_time = time.time()
        results = []

        for i in range(100):
            result = await health_check_tool.execute()
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        assert success_count == 100
        assert elapsed < 5.0
        print(f"100 health checks: {elapsed:.2f}s ({1000*elapsed/100:.2f}ms per op)")


class TestConcurrentLoadBaseline:
    """Test concurrent load baselines."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_50_recalls(self, mock_memory_store, mock_project_manager):
        """Baseline: 50 concurrent recall operations."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()

        tasks = [
            recall_tool.execute(query=f"query {i}")
            for i in range(50)
        ]

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        assert success_count == 50
        assert elapsed < 5.0
        print(f"50 concurrent recalls: {elapsed:.2f}s")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_50_remembers(self, mock_memory_store, mock_project_manager):
        """Baseline: 50 concurrent remember operations."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        start_time = time.time()

        tasks = [
            remember_tool.execute(content=f"Memory {i}")
            for i in range(50)
        ]

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        assert success_count == 50
        assert elapsed < 5.0
        print(f"50 concurrent remembers: {elapsed:.2f}s")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_100_mixed_operations(self, mock_memory_store, mock_project_manager, mock_planning_store):
        """Baseline: 100 concurrent mixed operations."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)
        decompose_tool = DecomposeTool(mock_planning_store)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()

        tasks = []
        for i in range(100):
            if i % 3 == 0:
                tasks.append(recall_tool.execute(query=f"query {i}"))
            elif i % 3 == 1:
                tasks.append(remember_tool.execute(content=f"Memory {i}"))
            else:
                tasks.append(decompose_tool.execute(task=f"Task {i}"))

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        assert success_count >= 95  # Allow some failures
        assert elapsed < 10.0
        print(f"100 mixed concurrent: {elapsed:.2f}s")


class TestMemoryFootprint:
    """Test memory usage under load."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_baseline_1000_items(self, mock_memory_store, mock_project_manager):
        """Baseline: Memory usage with 1000 remembered items."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        start_time = time.time()
        results = []

        for i in range(1000):
            result = await remember_tool.execute(content=f"Item {i}" * 100)
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        assert success_count == 1000
        assert elapsed < 30.0  # 30s for 1000 items
        print(f"1000 remembers: {elapsed:.2f}s ({1000*elapsed/1000:.2f}ms per op)")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_retrieval_scaling(self, mock_memory_store, mock_project_manager):
        """Test recall performance with large result sets."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate large result set
        mock_results = []
        for i in range(100):
            mock_result = Mock()
            mock_result.similarity = 0.95 - (i * 0.005)
            mock_result.memory = Mock()
            mock_result.memory.id = i
            mock_result.memory.content = f"Memory {i}" * 10
            mock_result.memory.memory_type = "semantic"
            mock_result.memory.tags = ["test"]
            mock_result.memory.created_at = Mock()
            mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")
            mock_results.append(mock_result)

        mock_memory_store.recall_with_reranking.return_value = mock_results

        start_time = time.time()
        result = await recall_tool.execute(query="test", k=100)
        elapsed = time.time() - start_time

        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 100
        assert elapsed < 2.0  # Should be fast even with large results
        print(f"Recall with 100 results: {elapsed*1000:.2f}ms")


class TestThroughputMetrics:
    """Test throughput and capacity metrics."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_throughput_recall_per_second(self, mock_memory_store, mock_project_manager):
        """Measure recall throughput (operations per second)."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        count = 0

        while time.time() - start_time < 1.0:  # Run for 1 second
            result = await recall_tool.execute(query="test")
            if result.status == ToolStatus.SUCCESS:
                count += 1

        throughput = count / 1.0
        print(f"Recall throughput: {throughput:.0f} ops/sec")
        assert throughput > 10  # At least 10 ops/sec

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_throughput_remember_per_second(self, mock_memory_store, mock_project_manager):
        """Measure remember throughput (operations per second)."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        start_time = time.time()
        count = 0

        while time.time() - start_time < 1.0:  # Run for 1 second
            result = await remember_tool.execute(content="test")
            if result.status == ToolStatus.SUCCESS:
                count += 1

        throughput = count / 1.0
        print(f"Remember throughput: {throughput:.0f} ops/sec")
        assert throughput > 10  # At least 10 ops/sec


class TestLatencyDistribution:
    """Test latency distribution and percentiles."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_latency_distribution_recalls(self, mock_memory_store, mock_project_manager):
        """Measure latency distribution for recall operations."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        latencies = []

        for i in range(100):
            start = time.time()
            result = await recall_tool.execute(query=f"query {i}")
            elapsed = (time.time() - start) * 1000  # ms
            if result.status == ToolStatus.SUCCESS:
                latencies.append(elapsed)

        latencies.sort()

        p50 = latencies[50] if len(latencies) > 50 else 0
        p95 = latencies[95] if len(latencies) > 95 else 0
        p99 = latencies[99] if len(latencies) > 99 else 0

        print(f"Recall latencies - P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")

        assert p50 < 10.0  # P50 under 10ms
        assert p95 < 50.0  # P95 under 50ms


class TestResourceScaling:
    """Test resource scaling with increasing load."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_scaling_sequential_load(self, mock_memory_store, mock_project_manager):
        """Test scaling with increasing sequential load."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        load_sizes = [10, 50, 100, 500]
        times = []

        for load_size in load_sizes:
            start = time.time()

            for i in range(load_size):
                await recall_tool.execute(query=f"query {i}")

            elapsed = time.time() - start
            times.append(elapsed)
            print(f"Load {load_size}: {elapsed:.2f}s ({1000*elapsed/load_size:.2f}ms per op)")

        # Verify scaling is linear (time roughly doubles when load doubles)
        ratio_1 = times[1] / times[0]  # 50/10 = 5x
        assert ratio_1 < 10  # Should be roughly 5x, allow some variance

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_scaling_concurrent_load(self, mock_memory_store, mock_project_manager):
        """Test scaling with increasing concurrent load."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        concurrent_sizes = [10, 25, 50, 100]
        times = []

        for concurrent_size in concurrent_sizes:
            start = time.time()

            tasks = [
                recall_tool.execute(query=f"query {i}")
                for i in range(concurrent_size)
            ]

            await asyncio.gather(*tasks)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"Concurrent {concurrent_size}: {elapsed:.2f}s")

        # Concurrent should not scale linearly - much better than sequential
        assert times[-1] < times[0] * 10  # 100 concurrent shouldn't be 10x slower than 10


class TestSustainedLoad1K:
    """Test sustained load with 1000 operations."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_1000_sequential_recalls(self, mock_memory_store, mock_project_manager):
        """Sustained load: 1000 sequential recall operations."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        results = []
        latencies = []

        for i in range(1000):
            op_start = time.time()
            result = await recall_tool.execute(query=f"query {i}")
            op_time = (time.time() - op_start) * 1000
            results.append(result)
            latencies.append(op_time)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        latencies.sort()
        p50 = latencies[500]
        p95 = latencies[950]
        p99 = latencies[990]

        print(f"1000 recalls: {elapsed:.2f}s ({elapsed/1000*1000:.2f}ms avg)")
        print(f"  P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")

        assert success_count == 1000
        assert elapsed < 60.0  # Complete in under 60s
        assert p95 < 100.0  # P95 under 100ms

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_1000_sequential_remembers(self, mock_memory_store, mock_project_manager):
        """Sustained load: 1000 sequential remember operations."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        start_time = time.time()
        results = []
        latencies = []

        for i in range(1000):
            op_start = time.time()
            result = await remember_tool.execute(content=f"Memory {i}")
            op_time = (time.time() - op_start) * 1000
            results.append(result)
            latencies.append(op_time)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        latencies.sort()
        p50 = latencies[500]
        p95 = latencies[950]
        p99 = latencies[990]

        print(f"1000 remembers: {elapsed:.2f}s ({elapsed/1000*1000:.2f}ms avg)")
        print(f"  P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")

        assert success_count == 1000
        assert elapsed < 60.0
        assert p95 < 100.0

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_1000_concurrent_mixed(self, mock_memory_store, mock_project_manager, mock_planning_store):
        """Sustained load: 1000 concurrent mixed operations (batched)."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)
        decompose_tool = DecomposeTool(mock_planning_store)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        total_success = 0
        batch_size = 100
        latencies = []

        # Process in batches of 100
        for batch in range(10):
            batch_start = time.time()
            tasks = []

            for i in range(batch_size):
                op_num = batch * batch_size + i
                if op_num % 3 == 0:
                    tasks.append(recall_tool.execute(query=f"query {op_num}"))
                elif op_num % 3 == 1:
                    tasks.append(remember_tool.execute(content=f"Memory {op_num}"))
                else:
                    tasks.append(decompose_tool.execute(task=f"Task {op_num}"))

            results = await asyncio.gather(*tasks)
            batch_time = (time.time() - batch_start) * 1000
            latencies.append(batch_time)
            total_success += sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        elapsed = time.time() - start_time
        latencies.sort()

        print(f"1000 concurrent mixed (10 batches): {elapsed:.2f}s")
        print(f"  Batch latencies - P50: {latencies[5]:.2f}ms, P95: {latencies[9]:.2f}ms")

        assert total_success >= 950  # Allow some failures
        assert elapsed < 30.0  # Should complete faster than sequential


class TestSustainedLoad5K:
    """Test sustained load with 5000 operations."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_5000_sequential_recalls(self, mock_memory_store, mock_project_manager):
        """Sustained load: 5000 sequential recall operations."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        results = []
        latencies = []
        checkpoint_times = []

        for i in range(5000):
            op_start = time.time()
            result = await recall_tool.execute(query=f"query {i}")
            op_time = (time.time() - op_start) * 1000
            results.append(result)
            latencies.append(op_time)

            # Track checkpoints every 1000 ops
            if (i + 1) % 1000 == 0:
                checkpoint_elapsed = time.time() - start_time
                checkpoint_times.append(checkpoint_elapsed)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        latencies.sort()
        p50 = latencies[2500]
        p95 = latencies[4750]
        p99 = latencies[4950]

        print(f"5000 recalls: {elapsed:.2f}s total")
        print(f"  Checkpoints: 1K={checkpoint_times[0]:.1f}s, 2K={checkpoint_times[1]:.1f}s, 3K={checkpoint_times[2]:.1f}s")
        print(f"  4K={checkpoint_times[3]:.1f}s, 5K={checkpoint_times[4]:.1f}s")
        print(f"  Latencies - P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")

        assert success_count == 5000
        assert elapsed < 300.0  # Complete in under 5 minutes
        assert p95 < 150.0  # P95 under 150ms even under sustained load

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_5000_sequential_remembers(self, mock_memory_store, mock_project_manager):
        """Sustained load: 5000 sequential remember operations."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        start_time = time.time()
        results = []
        latencies = []
        checkpoint_times = []

        for i in range(5000):
            op_start = time.time()
            result = await remember_tool.execute(content=f"Memory {i}")
            op_time = (time.time() - op_start) * 1000
            results.append(result)
            latencies.append(op_time)

            if (i + 1) % 1000 == 0:
                checkpoint_elapsed = time.time() - start_time
                checkpoint_times.append(checkpoint_elapsed)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        latencies.sort()
        p50 = latencies[2500]
        p95 = latencies[4750]
        p99 = latencies[4950]

        print(f"5000 remembers: {elapsed:.2f}s total")
        print(f"  Checkpoints: 1K={checkpoint_times[0]:.1f}s, 2K={checkpoint_times[1]:.1f}s, 3K={checkpoint_times[2]:.1f}s")
        print(f"  4K={checkpoint_times[3]:.1f}s, 5K={checkpoint_times[4]:.1f}s")
        print(f"  Latencies - P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")

        assert success_count == 5000
        assert elapsed < 300.0
        assert p95 < 150.0

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_5000_concurrent_batched(self, mock_memory_store, mock_project_manager):
        """Sustained load: 5000 concurrent operations in batches of 500."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        total_success = 0
        batch_size = 500
        batch_times = []

        # Process in 10 batches of 500
        for batch in range(10):
            batch_start = time.time()
            tasks = []

            for i in range(batch_size):
                op_num = batch * batch_size + i
                if op_num % 2 == 0:
                    tasks.append(recall_tool.execute(query=f"query {op_num}"))
                else:
                    tasks.append(remember_tool.execute(content=f"Memory {op_num}"))

            results = await asyncio.gather(*tasks)
            batch_time = time.time() - batch_start
            batch_times.append(batch_time)
            total_success += sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        elapsed = time.time() - start_time

        print(f"5000 concurrent (10 batches of 500): {elapsed:.2f}s total")
        print(f"  Batch times: min={min(batch_times):.2f}s, max={max(batch_times):.2f}s, avg={sum(batch_times)/len(batch_times):.2f}s")

        assert total_success >= 4900  # Allow some failures
        assert elapsed < 120.0  # Should be much faster than sequential


class TestSustainedLoad10K:
    """Test sustained load with 10000 operations."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_10000_sequential_recalls(self, mock_memory_store, mock_project_manager):
        """Sustained load: 10000 sequential recall operations."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        success_count = 0
        latencies = []
        checkpoint_times = []

        for i in range(10000):
            op_start = time.time()
            result = await recall_tool.execute(query=f"query {i}")
            op_time = (time.time() - op_start) * 1000
            latencies.append(op_time)

            if result.status == ToolStatus.SUCCESS:
                success_count += 1

            # Track checkpoints every 2000 ops
            if (i + 1) % 2000 == 0:
                checkpoint_elapsed = time.time() - start_time
                checkpoint_times.append(checkpoint_elapsed)

        elapsed = time.time() - start_time

        latencies.sort()
        p50 = latencies[5000]
        p95 = latencies[9500]
        p99 = latencies[9900]

        print(f"10000 recalls: {elapsed:.2f}s total")
        print(f"  Checkpoints: 2K={checkpoint_times[0]:.1f}s, 4K={checkpoint_times[1]:.1f}s, 6K={checkpoint_times[2]:.1f}s")
        print(f"  8K={checkpoint_times[3]:.1f}s, 10K={checkpoint_times[4]:.1f}s")
        print(f"  Latencies - P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")

        assert success_count == 10000
        assert elapsed < 600.0  # Complete in under 10 minutes
        assert p95 < 200.0  # P95 under 200ms even at 10K scale

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_10000_concurrent_large_batches(self, mock_memory_store, mock_project_manager):
        """Sustained load: 10000 concurrent operations in batches of 1000."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)
        optimize_tool = OptimizeTool(mock_memory_store, mock_project_manager)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        total_success = 0
        batch_size = 1000
        batch_times = []

        # Process in 10 batches of 1000
        for batch in range(10):
            batch_start = time.time()
            tasks = []

            for i in range(batch_size):
                op_num = batch * batch_size + i
                if op_num % 3 == 0:
                    tasks.append(recall_tool.execute(query=f"query {op_num}"))
                elif op_num % 3 == 1:
                    tasks.append(remember_tool.execute(content=f"Memory {op_num}"))
                else:
                    tasks.append(optimize_tool.execute())

            results = await asyncio.gather(*tasks)
            batch_time = time.time() - batch_start
            batch_times.append(batch_time)
            total_success += sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        elapsed = time.time() - start_time

        print(f"10000 concurrent (10 batches of 1000): {elapsed:.2f}s total")
        print(f"  Batch times: min={min(batch_times):.2f}s, max={max(batch_times):.2f}s, avg={sum(batch_times)/len(batch_times):.2f}s")
        print(f"  Success rate: {total_success}/10000 ({100*total_success/10000:.1f}%)")

        assert total_success >= 9800  # Allow 200 failures
        assert elapsed < 180.0  # Should be reasonable despite 10K ops

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_10000_mixed_realistic(self, mock_memory_store, mock_project_manager, mock_planning_store, mock_mcp_server):
        """Sustained load: 10000 mixed operations mimicking realistic workload."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)
        decompose_tool = DecomposeTool(mock_planning_store)
        health_tool = SystemHealthCheckTool(mock_mcp_server)
        mock_memory_store.recall_with_reranking.return_value = []

        start_time = time.time()
        total_ops = 10000
        ops_per_batch = 500
        total_success = 0
        batch_times = []

        # Realistic distribution: 40% recall, 35% remember, 20% decompose, 5% health checks
        for batch in range(total_ops // ops_per_batch):
            batch_start = time.time()
            tasks = []

            for i in range(ops_per_batch):
                op_num = batch * ops_per_batch + i
                rand_val = op_num % 100

                if rand_val < 40:
                    tasks.append(recall_tool.execute(query=f"query {op_num}"))
                elif rand_val < 75:
                    tasks.append(remember_tool.execute(content=f"Memory {op_num}"))
                elif rand_val < 95:
                    tasks.append(decompose_tool.execute(task=f"Task {op_num}"))
                else:
                    tasks.append(health_tool.execute())

            results = await asyncio.gather(*tasks)
            batch_time = time.time() - batch_start
            batch_times.append(batch_time)
            total_success += sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        elapsed = time.time() - start_time

        print(f"10000 mixed realistic ops: {elapsed:.2f}s total")
        print(f"  Batch times: min={min(batch_times):.2f}s, max={max(batch_times):.2f}s, avg={sum(batch_times)/len(batch_times):.2f}s")
        print(f"  Success rate: {total_success}/{total_ops} ({100*total_success/total_ops:.1f}%)")
        print(f"  Throughput: {total_ops/elapsed:.0f} ops/sec")

        assert total_success >= 9700  # 97% success rate
        assert elapsed < 200.0  # Must complete in under 200s
        assert (total_ops / elapsed) > 50  # At least 50 ops/sec throughput
