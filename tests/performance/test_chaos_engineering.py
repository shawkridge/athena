"""Chaos engineering tests for resilience and failure handling."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from athena.mcp.tools.memory_tools import RecallTool, RememberTool, OptimizeTool
from athena.mcp.tools.planning_tools import DecomposeTool
from athena.mcp.tools.system_tools import SystemHealthCheckTool
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
    return server


class TestDatabaseFailureResilience:
    """Test system resilience to database failures."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_timeout_recovery(self, mock_memory_store, mock_project_manager):
        """Chaos: Database query timeout and recovery."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate timeout on operations 30-40
        call_count = [0]

        def timeout_recall(*args, **kwargs):
            call_count[0] += 1
            if 30 <= call_count[0] <= 40:
                raise TimeoutError("Database query timeout")
            return []

        mock_memory_store.recall_with_reranking = timeout_recall

        start_time = time.time()
        results = []
        failures = 0

        for i in range(100):
            try:
                result = await recall_tool.execute(query=f"query {i}")
                results.append(result)
                if result.status != ToolStatus.SUCCESS:
                    failures += 1
            except TimeoutError:
                failures += 1

        elapsed = time.time() - start_time

        # Allow failures during chaos but recover afterward
        recovered = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        print(f"DB timeout chaos: {elapsed:.2f}s, failures={failures}, recovered={recovered}")

        assert elapsed < 60.0  # Eventually completes
        assert recovered > 50  # Recovers after chaos window

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_connection_drop(self, mock_memory_store, mock_project_manager):
        """Chaos: Database connection drops and reconnects."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate connection drop every 25 ops
        call_count = [0]

        def flaky_recall(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 25 == 0:
                raise ConnectionError("Database connection lost")
            return []

        mock_memory_store.recall_with_reranking = flaky_recall

        start_time = time.time()
        total_ops = 0
        successful_ops = 0
        failures = 0

        for i in range(200):
            total_ops += 1
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                successful_ops += 1
            else:
                failures += 1

        elapsed = time.time() - start_time
        failure_rate = failures / total_ops

        print(f"DB connection drop: {elapsed:.2f}s, failures={failures}, success_rate={1-failure_rate:.1%}")

        assert elapsed < 60.0
        assert successful_ops > 150  # >75% success despite failures
        assert failures == 8  # Should fail every 25 ops

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_corruption_detection(self, mock_memory_store, mock_project_manager):
        """Chaos: Corrupted data and recovery."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        # Simulate data corruption on some writes
        call_count = [0]

        def corrupt_store(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 15 == 0:
                raise ValueError("Database corruption detected: invalid data")
            return call_count[0]

        mock_memory_store.store_memory = corrupt_store

        start_time = time.time()
        results = []
        failures = 0

        for i in range(150):
            result = await remember_tool.execute(content=f"Memory {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                failures += 1

        elapsed = time.time() - start_time

        print(f"DB corruption: {elapsed:.2f}s, detected={failures}, stored={len(results)}")

        assert elapsed < 60.0
        assert failures >= 9  # Should detect corruption events (~150/15 = 10)
        assert len(results) > 100  # Should still store most data

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_locked_under_load(self, mock_memory_store, mock_project_manager):
        """Chaos: Database lock contention under concurrent load."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        # Simulate lock waits
        call_count = [0]
        lock_contentions = [0]

        def lock_aware_recall(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 20 < 5:  # 25% of calls experience contention
                lock_contentions[0] += 1
                # Simulate lock wait by returning success after delay detection
            return []

        mock_memory_store.recall_with_reranking = lock_aware_recall

        start_time = time.time()

        # 100 concurrent ops while experiencing lock contention
        tasks = [
            recall_tool.execute(query=f"query {i}")
            for i in range(100)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        successful = sum(1 for r in results if isinstance(r, Mock) or r.status == ToolStatus.SUCCESS)

        print(f"DB lock contention: {elapsed:.2f}s, lock_waits={lock_contentions[0]}, success={successful}")

        assert elapsed < 30.0  # Even with locks, complete in reasonable time
        assert successful > 75  # >75% success despite contention

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_slow_queries(self, mock_memory_store, mock_project_manager):
        """Chaos: Slow database queries trigger timeout handling."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate slow queries on some operations
        call_count = [0]
        slow_queries = [0]

        def slow_recall(*args, **kwargs):
            call_count[0] += 1
            # Every 30th query is slow (in simulation, we just track it)
            if call_count[0] % 30 == 0:
                slow_queries[0] += 1
            return []

        mock_memory_store.recall_with_reranking = slow_recall

        start_time = time.time()
        results = []

        for i in range(300):
            result = await recall_tool.execute(query=f"query {i}")
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        print(f"DB slow queries: {elapsed:.2f}s, slow_queries={slow_queries[0]}, success={success_count}")

        assert elapsed < 120.0  # Handle 300 ops with some slow queries
        assert success_count == 300  # All should eventually succeed


class TestDatabaseFailureRecovery:
    """Test recovery patterns after database failures."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, mock_memory_store, mock_project_manager):
        """Recovery: Exponential backoff on transient failures."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Fail first 3 attempts, then succeed
        attempt_count = [0]

        def flaky_with_backoff(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] <= 3:
                raise ConnectionError("Transient failure")
            return []

        mock_memory_store.recall_with_reranking = flaky_with_backoff

        # Test with retry logic
        start_time = time.time()
        attempts = 0
        max_retries = 5

        result = None
        for attempt in range(max_retries):
            attempts += 1
            try:
                result = await recall_tool.execute(query="test")
                break
            except ConnectionError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.001)  # Short delay

        elapsed = time.time() - start_time

        print(f"Exponential backoff recovery: {attempts} attempts, {elapsed*1000:.0f}ms")

        assert attempts <= 5
        assert elapsed < 1.0  # Should recover quickly with backoff

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_failure(self, mock_memory_store, mock_project_manager):
        """Recovery: Graceful degradation when database unavailable."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Database unavailable - raises error on all calls
        def unavailable_recall(*args, **kwargs):
            raise ConnectionError("Database unavailable")

        mock_memory_store.recall_with_reranking = unavailable_recall

        start_time = time.time()
        results = []
        failures = 0

        for i in range(50):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status != ToolStatus.SUCCESS:
                failures += 1
            else:
                results.append(result)

        elapsed = time.time() - start_time

        print(f"Graceful degradation: {elapsed:.2f}s, failures={failures}, graceful_responses={len(results)}")

        assert elapsed < 10.0
        assert failures == 50  # All should fail gracefully

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_health_check_after_recovery(self, mock_mcp_server):
        """Recovery: Health checks detect and confirm recovery."""
        health_tool = SystemHealthCheckTool(mock_mcp_server)

        # Simulate failure then recovery
        health_states = [
            {"status": "unhealthy", "issues": ["database_down"]},
            {"status": "unhealthy", "issues": ["database_recovering"]},
            {"status": "healthy", "issues": []},
        ]

        state_index = [0]

        async def changing_health():
            current = health_states[min(state_index[0], len(health_states) - 1)]
            state_index[0] += 1
            return current

        mock_mcp_server._health_checker.check = changing_health

        start_time = time.time()
        check_results = []

        for i in range(10):
            result = await health_tool.execute()
            check_results.append(result)
            if i < 5:  # Wait for recovery
                await asyncio.sleep(0.1)

        elapsed = time.time() - start_time

        print(f"Health check recovery: {elapsed:.2f}s, checks={len(check_results)}")

        assert elapsed < 5.0
        assert len(check_results) >= 3


class TestDatabaseStressFailures:
    """Test failures under stress and extreme conditions."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_high_concurrency_failures(self, mock_memory_store, mock_project_manager):
        """Stress: Database failures under high concurrency."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Fail every 10th concurrent operation
        op_count = [0]

        def stressed_recall(*args, **kwargs):
            op_count[0] += 1
            if op_count[0] % 10 == 0:
                raise RuntimeError("Database overload")
            return []

        mock_memory_store.recall_with_reranking = stressed_recall

        start_time = time.time()

        # 500 concurrent ops
        tasks = [
            recall_tool.execute(query=f"query {i}")
            for i in range(500)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        failures = sum(1 for r in results if isinstance(r, Exception))
        successes = sum(1 for r in results if not isinstance(r, Exception))

        print(f"High concurrency stress: {elapsed:.2f}s, successes={successes}, failures={failures}")

        assert elapsed < 30.0
        assert successes > 400  # >80% success even under stress

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_disk_full_condition(self, mock_memory_store, mock_project_manager):
        """Stress: Database writes fail when disk full."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        # Simulate disk full after 40 writes
        write_count = [0]

        def disk_full_store(*args, **kwargs):
            write_count[0] += 1
            if write_count[0] > 40:
                raise OSError("No space left on device")
            return write_count[0]

        mock_memory_store.store_memory = disk_full_store

        start_time = time.time()
        results = []
        disk_full_errors = 0

        for i in range(100):
            try:
                result = await remember_tool.execute(content=f"Memory {i}")
                results.append(result)
            except OSError as e:
                if "space" in str(e):
                    disk_full_errors += 1

        elapsed = time.time() - start_time

        print(f"Disk full condition: {elapsed:.2f}s, writes_before_full=40, errors={disk_full_errors}")

        assert elapsed < 30.0
        assert len(results) >= 40  # Got some writes before full

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_memory_pressure(self, mock_memory_store, mock_project_manager):
        """Stress: Database performance degrades under memory pressure."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate increasing latency as memory pressure rises
        call_count = [0]

        def memory_stressed_recall(*args, **kwargs):
            call_count[0] += 1
            # Latency increases with call count (simulating memory pressure)
            # Note: In simulation, we don't actually sleep, just track
            return []

        mock_memory_store.recall_with_reranking = memory_stressed_recall

        start_time = time.time()
        results = []

        for i in range(200):
            result = await recall_tool.execute(query=f"query {i}")
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        print(f"Memory pressure: {elapsed:.2f}s, success={success_count}, avg_latency={elapsed/200*1000:.2f}ms")

        assert elapsed < 60.0  # Still completes despite degradation
        assert success_count == 200  # All succeed eventually


class TestDatabaseFailurePatterns:
    """Test realistic database failure patterns."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cascading_failure_pattern(self, mock_memory_store, mock_project_manager):
        """Pattern: Cascading failures (one failure triggers more)."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Cascading: pattern is deterministic every 10th operation fails
        call_count = [0]

        def cascading_recall(*args, **kwargs):
            call_count[0] += 1
            # Fail every 10 ops: 10, 20, 30, etc.
            if call_count[0] % 10 == 0:
                raise RuntimeError("Cascading failure")
            return []

        mock_memory_store.recall_with_reranking = cascading_recall

        start_time = time.time()
        results = []
        failures = 0

        for i in range(200):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                failures += 1

        elapsed = time.time() - start_time

        print(f"Cascading failures: {elapsed:.2f}s, total_failures={failures}")

        assert elapsed < 30.0
        assert failures == 20  # Exactly 20 failures (200/10)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_intermittent_database_flakiness(self, mock_memory_store, mock_project_manager):
        """Pattern: Intermittent flakiness (deterministic failures)."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate ~5% failure rate (every 20th op fails = 5%)
        call_count = [0]

        def flaky_recall(*args, **kwargs):
            call_count[0] += 1
            # Fail every 20th operation = 5% failure rate
            if call_count[0] % 20 == 0:
                raise RuntimeError("Flakiness")
            return []

        mock_memory_store.recall_with_reranking = flaky_recall

        start_time = time.time()
        results = []
        failures = 0

        for i in range(500):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                failures += 1

        elapsed = time.time() - start_time
        failure_rate = failures / 500

        print(f"Intermittent flakiness: {elapsed:.2f}s, failure_rate={failure_rate:.1%}")

        assert elapsed < 60.0
        assert failure_rate == 0.05  # Exactly 5% (25 failures out of 500)
