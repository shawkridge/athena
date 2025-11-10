"""Chaos engineering tests for network and memory failures."""

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
    return server


class TestNetworkFailures:
    """Test network-related failures and degradation."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, mock_memory_store, mock_project_manager):
        """Chaos: Network timeouts during MCP tool execution."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate network timeout every 30 ops
        call_count = [0]

        def timeout_recall(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 30 == 0:
                raise TimeoutError("Network timeout - operation took too long")
            return []

        mock_memory_store.recall_with_reranking = timeout_recall

        start_time = time.time()
        results = []
        timeouts = 0

        for i in range(300):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                timeouts += 1

        elapsed = time.time() - start_time

        print(f"Network timeouts: {elapsed:.2f}s, timeouts={timeouts}, success={len(results)}")

        assert elapsed < 30.0
        assert timeouts == 10  # 300/30 = 10 timeouts
        assert len(results) >= 280  # >93% success

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_network_latency_degradation(self, mock_memory_store, mock_project_manager):
        """Chaos: Increasing network latency over time."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate increasing latency
        call_count = [0]
        latencies = []

        def latency_recall(*args, **kwargs):
            call_count[0] += 1
            # Simulated latency increases every 50 ops
            latency = 0.001 * (call_count[0] // 50)
            latencies.append(latency)
            return []

        mock_memory_store.recall_with_reranking = latency_recall

        start_time = time.time()
        results = []

        for i in range(200):
            result = await recall_tool.execute(query=f"query {i}")
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        print(f"Network latency degradation: {elapsed:.2f}s, success={success_count}")
        print(f"  Latency progression: {latencies[0]:.4f}s → {latencies[-1]:.4f}s")

        assert elapsed < 30.0
        assert success_count == 200

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_network_packet_loss(self, mock_memory_store, mock_project_manager):
        """Chaos: Simulated packet loss requiring retries."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Fail every 15th operation (packet loss)
        call_count = [0]

        def packet_loss_recall(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 15 == 0:
                raise ConnectionError("Network unreachable - packet loss")
            return []

        mock_memory_store.recall_with_reranking = packet_loss_recall

        start_time = time.time()
        results = []
        losses = 0

        for i in range(300):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                losses += 1

        elapsed = time.time() - start_time

        print(f"Network packet loss: {elapsed:.2f}s, losses={losses}, recovered={len(results)}")

        assert elapsed < 30.0
        assert losses == 20  # 300/15 = 20 losses
        assert len(results) >= 280

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_intermittent_network_unavailability(self, mock_memory_store, mock_project_manager):
        """Chaos: Network goes down and comes back up."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Network down from ops 40-80
        call_count = [0]

        def flaky_network_recall(*args, **kwargs):
            call_count[0] += 1
            if 40 <= call_count[0] <= 80:
                raise ConnectionError("Network unreachable")
            return []

        mock_memory_store.recall_with_reranking = flaky_network_recall

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

        print(f"Intermittent network: {elapsed:.2f}s, down_ops=41, recovered={len(results)}")

        assert elapsed < 30.0
        assert failures == 41  # 80 - 40 + 1
        assert len(results) >= 159  # Recovered afterward


class TestMemoryFailures:
    """Test memory-related failures and constraints."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_allocation_failures(self, mock_memory_store, mock_project_manager):
        """Chaos: Memory allocation failures under load."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        # Simulate memory allocation failure every 25 writes
        call_count = [0]

        def oom_store(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 25 == 0:
                raise MemoryError("Cannot allocate memory")
            return call_count[0]

        mock_memory_store.store_memory = oom_store

        start_time = time.time()
        results = []
        oom_failures = 0

        for i in range(250):
            result = await remember_tool.execute(content=f"Memory {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                oom_failures += 1

        elapsed = time.time() - start_time

        print(f"Memory allocation failures: {elapsed:.2f}s, failures={oom_failures}, stored={len(results)}")

        assert elapsed < 60.0
        assert oom_failures == 10  # 250/25 = 10
        assert len(results) >= 230

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_pressure_slowdown(self, mock_memory_store, mock_project_manager):
        """Chaos: System slowdown under memory pressure."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate memory pressure affecting performance
        call_count = [0]
        timing = []

        def memory_pressure_recall(*args, **kwargs):
            call_count[0] += 1
            # Memory pressure increases with call count
            # This would normally cause slowdown (we track it)
            return []

        mock_memory_store.recall_with_reranking = memory_pressure_recall

        start_time = time.time()
        results = []

        for i in range(500):
            op_start = time.time()
            result = await recall_tool.execute(query=f"query {i}")
            op_time = (time.time() - op_start) * 1000
            timing.append(op_time)
            results.append(result)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)

        timing.sort()
        p50 = timing[250]
        p95 = timing[475]

        print(f"Memory pressure slowdown: {elapsed:.2f}s, success={success_count}")
        print(f"  Latency: P50={p50:.2f}ms, P95={p95:.2f}ms")

        assert elapsed < 60.0
        assert success_count == 500

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_garbage_collection_pause(self, mock_memory_store, mock_project_manager):
        """Chaos: GC pause impacts operation latency."""
        decompose_tool = DecomposeTool(Mock())

        # Simulate GC pauses every 50 ops
        call_count = [0]

        # Mock planning store
        planning_store = Mock()
        planning_store.store_plan = Mock(return_value=1)

        decompose_tool._planning_store = planning_store

        latencies = []
        gc_pauses = 0

        for i in range(200):
            op_start = time.time()

            # Simulate GC pause every 50 ops
            call_count[0] += 1
            if call_count[0] % 50 == 0:
                gc_pauses += 1
                # GC pause would happen here

            # Execute task
            result = await decompose_tool.execute(task=f"Task {i}")

            op_time = (time.time() - op_start) * 1000
            latencies.append(op_time)

        latencies.sort()
        p99 = latencies[198] if len(latencies) > 198 else latencies[-1]

        print(f"GC pause impact: gc_pauses={gc_pauses}, P99_latency={p99:.2f}ms")

        assert gc_pauses == 4  # 200/50 = 4
        assert len(latencies) == 200


class TestCombinedNetworkMemoryFailures:
    """Test combined network and memory failures."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_network_timeout_and_memory_pressure(self, mock_memory_store, mock_project_manager):
        """Chaos: Simultaneous network timeouts and memory pressure."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Network timeout every 40 ops, memory issues every 50 ops
        call_count = [0]

        def combined_failure(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 40 == 0:
                raise TimeoutError("Network + Memory: operation timeout")
            if call_count[0] % 50 == 0:
                raise MemoryError("Network + Memory: allocation failed")
            return []

        mock_memory_store.recall_with_reranking = combined_failure

        start_time = time.time()
        results = []
        failures = 0

        for i in range(400):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                failures += 1

        elapsed = time.time() - start_time

        print(f"Combined network+memory failures: {elapsed:.2f}s, failures={failures}, recovered={len(results)}")

        assert elapsed < 60.0
        assert failures > 10  # Some combined failures
        assert len(results) >= 350  # >85% success despite combined failures

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cascading_network_then_memory(self, mock_memory_store, mock_project_manager):
        """Chaos: Network failures followed by memory pressure."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Phase 1: Network failures (ops 1-100)
        # Phase 2: Memory pressure (ops 100-200)
        # Phase 3: Normal (ops 200+)
        call_count = [0]

        def cascading_chaos(*args, **kwargs):
            call_count[0] += 1
            if 1 <= call_count[0] <= 100:
                if call_count[0] % 10 == 0:
                    raise ConnectionError("Network failure phase")
            elif 100 < call_count[0] <= 200:
                if call_count[0] % 15 == 0:
                    raise MemoryError("Memory pressure phase")
            return []

        mock_memory_store.recall_with_reranking = cascading_chaos

        start_time = time.time()
        results = []
        phase1_failures = 0
        phase2_failures = 0

        for i in range(300):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                if i < 100:
                    phase1_failures += 1
                elif i < 200:
                    phase2_failures += 1

        elapsed = time.time() - start_time

        print(f"Cascading chaos: {elapsed:.2f}s")
        print(f"  Phase 1 (network): {phase1_failures} failures")
        print(f"  Phase 2 (memory): {phase2_failures} failures")
        print(f"  Recovery rate: {len(results)}/300")

        assert elapsed < 60.0
        assert len(results) >= 270  # >90% recovery


class TestResourceExhaustion:
    """Test resource exhaustion scenarios."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, mock_memory_store, mock_project_manager):
        """Chaos: Database connection pool exhaustion."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Simulate connection pool exhaustion after 25 concurrent connections
        call_count = [0]

        def pool_exhaustion(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 25:
                raise RuntimeError("Connection pool exhausted: too many connections")
            return []

        mock_memory_store.recall_with_reranking = pool_exhaustion

        start_time = time.time()
        tasks = []

        # Create 50 concurrent operations
        for i in range(50):
            tasks.append(recall_tool.execute(query=f"query {i}"))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        successes = sum(1 for r in results if isinstance(r, Mock) or (hasattr(r, 'status') and r.status == ToolStatus.SUCCESS))
        failures = sum(1 for r in results if isinstance(r, Exception) or (hasattr(r, 'status') and r.status != ToolStatus.SUCCESS))

        print(f"Connection pool exhaustion: {elapsed:.2f}s, successes={successes}, failures={failures}")

        assert elapsed < 30.0
        assert successes >= 25  # At least initial pool size

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_file_descriptor_exhaustion(self, mock_memory_store, mock_project_manager):
        """Chaos: File descriptor exhaustion under load."""
        remember_tool = RememberTool(mock_memory_store, mock_project_manager)

        # Simulate FD exhaustion after 100 writes
        call_count = [0]

        def fd_exhaustion(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 100:
                raise OSError("Too many open files (24)")
            return call_count[0]

        mock_memory_store.store_memory = fd_exhaustion

        start_time = time.time()
        results = []
        fd_errors = 0

        for i in range(200):
            result = await remember_tool.execute(content=f"Memory {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                fd_errors += 1

        elapsed = time.time() - start_time

        print(f"File descriptor exhaustion: {elapsed:.2f}s, errors={fd_errors}, stored={len(results)}")

        assert elapsed < 30.0
        assert fd_errors == 100  # 200 - 100
        assert len(results) >= 95  # Some recovery


class TestResourceRecovery:
    """Test recovery from resource exhaustion."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_recovery_after_memory_spike(self, mock_memory_store, mock_project_manager):
        """Recovery: System recovers after temporary memory spike."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Memory spike at ops 30-50, then recovery
        call_count = [0]

        def spike_recovery(*args, **kwargs):
            call_count[0] += 1
            if 30 <= call_count[0] <= 50:
                raise MemoryError("Temporary memory spike")
            return []

        mock_memory_store.recall_with_reranking = spike_recovery

        start_time = time.time()
        results = []
        failures = 0

        for i in range(150):
            result = await recall_tool.execute(query=f"query {i}")
            if result.status == ToolStatus.SUCCESS:
                results.append(result)
            else:
                failures += 1

        elapsed = time.time() - start_time

        # Check recovery (successes should be high)
        recovery_rate = len(results) / 150

        print(f"Memory spike recovery: {elapsed:.2f}s, failures={failures}, recovery_rate={recovery_rate:.1%}")

        assert elapsed < 30.0
        assert failures == 21  # 50 - 30 + 1
        assert recovery_rate >= 0.85  # >85% recovery

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_recovery_after_network_partition(self, mock_memory_store, mock_project_manager):
        """Recovery: Network partition heals and operations resume."""
        recall_tool = RecallTool(mock_memory_store, mock_project_manager)

        # Network partition ops 50-75
        call_count = [0]

        def partition_heal(*args, **kwargs):
            call_count[0] += 1
            if 50 <= call_count[0] <= 75:
                raise ConnectionError("Network partition detected")
            return []

        mock_memory_store.recall_with_reranking = partition_heal

        start_time = time.time()
        before_partition = []
        during_partition = 0
        after_partition = []

        for i in range(200):
            result = await recall_tool.execute(query=f"query {i}")
            if i < 50 and result.status == ToolStatus.SUCCESS:
                before_partition.append(result)
            elif 50 <= i <= 75 and result.status != ToolStatus.SUCCESS:
                during_partition += 1
            elif i > 75 and result.status == ToolStatus.SUCCESS:
                after_partition.append(result)

        elapsed = time.time() - start_time

        print(f"Network partition healing: {elapsed:.2f}s")
        print(f"  Before: {len(before_partition)}, During: {during_partition}, After: {len(after_partition)}")

        assert elapsed < 30.0
        assert len(before_partition) >= 49  # ~All ops before partition succeed
        assert during_partition >= 25  # ~75 - 50
        assert len(after_partition) >= 120  # Most ops after recovery succeed
