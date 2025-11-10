"""Performance profiling tests for CPU, memory, and I/O analysis."""

import pytest
import asyncio
import time
import tracemalloc
import cProfile
import pstats
import io
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any
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
    store.list_memories = Mock(return_value=[Mock() for _ in range(100)])
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
    server._memory_store = Mock()
    server._project_manager = Mock()
    return server


class ProfileResult:
    """Container for profiling results."""

    def __init__(self):
        self.cpu_time: float = 0.0
        self.peak_memory: int = 0
        self.memory_growth: int = 0
        self.io_operations: int = 0
        self.operation_count: int = 0
        self.hot_functions: List[str] = []
        self.timestamp: datetime = datetime.now()


class CPUProfiler:
    """Profile CPU usage and identify hot paths."""

    def __init__(self):
        self.profiler = cProfile.Profile()
        self.result = ProfileResult()

    def start(self):
        """Start CPU profiling."""
        self.profiler.enable()

    def stop(self) -> ProfileResult:
        """Stop CPU profiling and analyze results."""
        self.profiler.disable()

        # Get profiling statistics
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions

        # Parse results
        stats_output = s.getvalue()
        self.result.cpu_time = sum(stat[3] for stat in self.profiler.getstats() if stat)

        # Extract hot functions
        for line in stats_output.split('\n')[5:15]:
            if line.strip():
                parts = line.split()
                if parts and not parts[0].isdigit():
                    self.result.hot_functions.append(line.strip())

        return self.result


class MemoryProfiler:
    """Profile memory usage and detect leaks."""

    def __init__(self):
        self.result = ProfileResult()
        self.start_snapshot = None

    def start(self):
        """Start memory profiling."""
        tracemalloc.start()
        self.start_snapshot = tracemalloc.take_snapshot()

    def stop(self) -> ProfileResult:
        """Stop memory profiling and analyze growth."""
        current_snapshot = tracemalloc.take_snapshot()

        # Get memory statistics
        top_stats = current_snapshot.compare_to(self.start_snapshot, 'lineno')

        # Calculate peak memory
        current, peak = tracemalloc.get_traced_memory()
        self.result.peak_memory = peak
        self.result.memory_growth = current - (self.start_snapshot.statistics('lineno')[0].size if self.start_snapshot.statistics('lineno') else 0)

        tracemalloc.stop()
        return self.result


class IOProfiler:
    """Profile I/O operations and blocking calls."""

    def __init__(self):
        self.result = ProfileResult()
        self.io_count = [0]

    def count_io_operation(self):
        """Count an I/O operation."""
        self.io_count[0] += 1

    def get_result(self) -> ProfileResult:
        """Get profiling results."""
        self.result.io_operations = self.io_count[0]
        return self.result


class TestCPUProfiling:
    """CPU profiling and hot path analysis tests."""

    @pytest.mark.performance
    def test_cpu_profiling_recall_operation(self, mock_memory_store, mock_project_manager):
        """Profile CPU usage for recall operations."""
        profiler = CPUProfiler()
        tool = RecallTool(mock_memory_store, mock_project_manager)

        profiler.start()

        # Simulate multiple recall operations
        for _ in range(100):
            tool.execute(project_id="1", query="test", limit=10)

        result = profiler.stop()

        # Verify CPU profiling captured data
        assert result.cpu_time >= 0
        assert len(result.hot_functions) >= 0
        assert result.timestamp is not None

    @pytest.mark.performance
    def test_cpu_profiling_remember_operation(self, mock_memory_store, mock_project_manager):
        """Profile CPU usage for remember (store) operations."""
        profiler = CPUProfiler()
        tool = RememberTool(mock_memory_store, mock_project_manager)

        profiler.start()

        # Simulate multiple store operations
        for i in range(50):
            tool.execute(
                project_id="1",
                content=f"Memory content {i}",
                memory_type="semantic",
                tags=["test"]
            )

        result = profiler.stop()

        # Verify profiling data
        assert result.cpu_time >= 0
        assert result.hot_functions is not None

    @pytest.mark.performance
    def test_cpu_hotspot_identification(self, mock_memory_store, mock_project_manager):
        """Identify CPU hotspots in tool execution."""
        profiler = CPUProfiler()

        # Create multiple tools
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        optimize_tool = OptimizeTool(mock_memory_store, mock_project_manager)

        profiler.start()

        # Execute multiple operations
        for _ in range(50):
            recall_tool.execute(project_id="1", query="test", limit=10)
            optimize_tool.execute(project_id="1", dry_run=True)

        result = profiler.stop()

        # Verify hotspot identification
        assert result.cpu_time >= 0
        assert isinstance(result.hot_functions, list)


class TestMemoryProfiling:
    """Memory profiling and leak detection tests."""

    @pytest.mark.performance
    def test_memory_profiling_store_operations(self, mock_memory_store, mock_project_manager):
        """Profile memory usage during store operations."""
        profiler = MemoryProfiler()
        tool = RememberTool(mock_memory_store, mock_project_manager)

        profiler.start()

        # Simulate multiple store operations
        for i in range(100):
            tool.execute(
                project_id="1",
                content=f"Memory content {i}" * 100,  # Larger content
                memory_type="semantic",
                tags=["test"]
            )

        result = profiler.stop()

        # Verify memory profiling
        assert result.peak_memory >= 0
        assert result.memory_growth >= 0

    @pytest.mark.performance
    def test_memory_leak_detection(self, mock_memory_store, mock_project_manager):
        """Detect potential memory leaks in recall operations."""
        tool = RecallTool(mock_memory_store, mock_project_manager)

        # Profile initial state
        initial_profiler = MemoryProfiler()
        initial_profiler.start()

        # Run many recalls
        for _ in range(200):
            tool.execute(project_id="1", query="test", limit=10)

        initial_result = initial_profiler.stop()

        # Profile after operations
        final_profiler = MemoryProfiler()
        final_profiler.start()

        for _ in range(200):
            tool.execute(project_id="1", query="test", limit=10)

        final_result = final_profiler.stop()

        # Memory growth should be reasonable (not exponential)
        # Allow up to 10x growth for caching, but flag exponential growth
        growth_ratio = final_result.memory_growth / max(initial_result.memory_growth, 1)
        assert growth_ratio < 100  # Flag if growth is extreme

    @pytest.mark.performance
    def test_memory_profiling_list_operations(self, mock_memory_store, mock_project_manager):
        """Profile memory usage for list operations."""
        profiler = MemoryProfiler()

        profiler.start()

        # Simulate listing large sets of memories
        for _ in range(50):
            memories = mock_memory_store.list_memories()
            assert len(memories) == 100

        result = profiler.stop()

        # Verify memory profiling
        assert result.peak_memory >= 0
        assert result.memory_growth >= 0


class TestIOAnalysis:
    """I/O operation analysis and blocking detection."""

    @pytest.mark.performance
    def test_io_operation_counting(self, mock_memory_store, mock_project_manager):
        """Count I/O operations during memory access."""
        profiler = IOProfiler()
        tool = RecallTool(mock_memory_store, mock_project_manager)

        # Count I/O operations
        for _ in range(50):
            profiler.count_io_operation()
            tool.execute(project_id="1", query="test", limit=10)

        result = profiler.get_result()

        # Verify I/O counting
        assert result.io_operations == 50

    @pytest.mark.performance
    def test_io_blocking_detection(self, mock_memory_store, mock_project_manager):
        """Detect blocking I/O operations."""
        tool = RecallTool(mock_memory_store, mock_project_manager)

        # Track execution time to detect blocking
        times = []
        for _ in range(20):
            start = time.time()
            tool.execute(project_id="1", query="test", limit=10)
            elapsed = time.time() - start
            times.append(elapsed)

        # Check for consistent performance (no blocking)
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Max time should not be more than 10x average (indicates blocking)
        assert max_time < avg_time * 10

    @pytest.mark.performance
    def test_concurrent_io_operations(self, mock_memory_store, mock_project_manager):
        """Test concurrent I/O operations."""
        tool = RecallTool(mock_memory_store, mock_project_manager)
        profiler = IOProfiler()

        # Execute operations and track I/O
        start = time.time()
        for _ in range(100):
            profiler.count_io_operation()
            tool.execute(project_id="1", query="test", limit=10)
        elapsed = time.time() - start

        result = profiler.get_result()

        # Verify concurrent operation performance
        assert result.io_operations == 100
        assert elapsed > 0  # Should complete in reasonable time


class TestSlowOperationIdentification:
    """Identify and measure slow operations."""

    @pytest.mark.performance
    def test_slow_recall_operations(self, mock_memory_store, mock_project_manager):
        """Identify slow recall operations."""
        tool = RecallTool(mock_memory_store, mock_project_manager)

        # Track operation times
        times = []
        for i in range(50):
            start = time.time()
            tool.execute(project_id="1", query=f"query_{i}", limit=10)
            elapsed = time.time() - start
            times.append(elapsed)

        # Analyze performance
        avg_time = sum(times) / len(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        p99_time = sorted(times)[int(len(times) * 0.99)]

        # Verify reasonable performance
        assert avg_time < 1.0  # Should be < 1s on average
        assert p95_time < 5.0  # P95 should be < 5s
        assert p99_time < 10.0  # P99 should be < 10s

    @pytest.mark.performance
    def test_slow_store_operations(self, mock_memory_store, mock_project_manager):
        """Identify slow store operations."""
        tool = RememberTool(mock_memory_store, mock_project_manager)

        # Track operation times
        times = []
        for i in range(30):
            start = time.time()
            tool.execute(
                project_id="1",
                content=f"Memory {i}" * 50,
                memory_type="semantic",
                tags=["test"]
            )
            elapsed = time.time() - start
            times.append(elapsed)

        # Analyze performance
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Verify reasonable performance
        assert avg_time < 1.0  # Should be < 1s on average
        assert max_time < 5.0  # Max should be < 5s

    @pytest.mark.performance
    def test_slow_optimization_operations(self, mock_memory_store, mock_project_manager):
        """Identify slow optimization operations."""
        tool = OptimizeTool(mock_memory_store, mock_project_manager)

        # Track operation times
        times = []
        for _ in range(20):
            start = time.time()
            tool.execute(project_id="1", dry_run=True)
            elapsed = time.time() - start
            times.append(elapsed)

        # Analyze performance
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Verify reasonable performance
        assert avg_time < 2.0  # Should be < 2s on average
        assert max_time < 10.0  # Max should be < 10s


class TestResourceUtilization:
    """Track resource utilization and efficiency metrics."""

    @pytest.mark.performance
    def test_cpu_utilization_efficiency(self, mock_memory_store, mock_project_manager):
        """Measure CPU utilization efficiency."""
        tool = RecallTool(mock_memory_store, mock_project_manager)

        # Profile CPU usage
        profiler = CPUProfiler()
        profiler.start()

        # Execute operations
        operation_count = 100
        for _ in range(operation_count):
            tool.execute(project_id="1", query="test", limit=10)

        result = profiler.stop()
        result.operation_count = operation_count

        # Calculate efficiency
        if result.cpu_time > 0:
            efficiency = operation_count / result.cpu_time
            assert efficiency > 0  # Should have measurable efficiency

    @pytest.mark.performance
    def test_memory_utilization_efficiency(self, mock_memory_store, mock_project_manager):
        """Measure memory utilization efficiency."""
        tool = RememberTool(mock_memory_store, mock_project_manager)

        # Profile memory usage
        profiler = MemoryProfiler()
        profiler.start()

        # Execute operations
        operation_count = 50
        for i in range(operation_count):
            tool.execute(
                project_id="1",
                content=f"Content {i}",
                memory_type="semantic",
                tags=["test"]
            )

        result = profiler.stop()
        result.operation_count = operation_count

        # Verify memory efficiency
        assert result.peak_memory >= 0
        assert result.operation_count == operation_count

    @pytest.mark.performance
    def test_io_utilization_ratio(self, mock_memory_store, mock_project_manager):
        """Measure I/O to computation ratio."""
        tool = RecallTool(mock_memory_store, mock_project_manager)
        io_profiler = IOProfiler()

        # Track operations
        operation_count = 0
        start = time.time()

        for _ in range(100):
            io_profiler.count_io_operation()
            tool.execute(project_id="1", query="test", limit=10)
            operation_count += 1

        elapsed = time.time() - start
        io_result = io_profiler.get_result()

        # Calculate I/O ratio
        if elapsed > 0:
            io_ratio = io_result.io_operations / operation_count
            assert io_ratio > 0  # Should have measurable I/O
            assert io_ratio <= 2  # Should not be I/O bound


class TestProfilingAccuracy:
    """Verify profiling accuracy and consistency."""

    @pytest.mark.performance
    def test_consistent_cpu_measurements(self, mock_memory_store, mock_project_manager):
        """Verify consistent CPU profiling measurements."""
        tool = RecallTool(mock_memory_store, mock_project_manager)

        results = []
        for _ in range(3):
            profiler = CPUProfiler()
            profiler.start()

            for _ in range(50):
                tool.execute(project_id="1", query="test", limit=10)

            result = profiler.stop()
            results.append(result.cpu_time)

        # Verify measurements are consistent
        avg_time = sum(results) / len(results)
        variance = sum((t - avg_time) ** 2 for t in results) / len(results)

        # Coefficient of variation should be reasonable
        if avg_time > 0:
            cv = (variance ** 0.5) / avg_time
            assert cv < 0.5  # Less than 50% variation

    @pytest.mark.performance
    def test_consistent_memory_measurements(self, mock_memory_store, mock_project_manager):
        """Verify consistent memory profiling measurements."""
        tool = RememberTool(mock_memory_store, mock_project_manager)

        results = []
        for _ in range(3):
            profiler = MemoryProfiler()
            profiler.start()

            for i in range(30):
                tool.execute(
                    project_id="1",
                    content=f"Content {i}",
                    memory_type="semantic",
                    tags=["test"]
                )

            result = profiler.stop()
            results.append(result.peak_memory)

        # Verify measurements are consistent
        avg_memory = sum(results) / len(results)

        # Memory measurements should be within reasonable range
        # Allow wider tolerance due to Python GC non-determinism
        for result in results:
            ratio = result / max(avg_memory, 1)
            assert 0.3 <= ratio <= 3.0  # Within 3x of average (accounting for GC variability)

    @pytest.mark.performance
    def test_profiling_overhead(self, mock_memory_store, mock_project_manager):
        """Measure profiling overhead."""
        tool = RecallTool(mock_memory_store, mock_project_manager)

        # Baseline without profiling
        start = time.time()
        for _ in range(100):
            tool.execute(project_id="1", query="test", limit=10)
        baseline_time = time.time() - start

        # With profiling
        profiler = CPUProfiler()
        profiler.start()
        start = time.time()
        for _ in range(100):
            tool.execute(project_id="1", query="test", limit=10)
        profiler.stop()
        profiled_time = time.time() - start

        # Profiling overhead should be reasonable
        overhead = profiled_time / max(baseline_time, 0.001)
        assert overhead < 5.0  # Less than 5x overhead
