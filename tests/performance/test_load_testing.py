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
