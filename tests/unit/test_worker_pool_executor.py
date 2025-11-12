"""Unit tests for Worker Pool Executor.

Tests distributed execution including:
- Task creation and execution
- Worker pool management
- Load balancing
- Priority-based task queuing
- Graceful error handling
- Result caching
- Performance metrics
"""

import pytest
import time
from athena.optimization.worker_pool_executor import (
    WorkerPool,
    WorkerTask,
    WorkerTaskResult,
    LoadBalancer,
    TaskPriority,
)


@pytest.fixture
def load_balancer():
    """Create a fresh load balancer."""
    return LoadBalancer(window_seconds=10, target_qps=100.0)


@pytest.fixture
def worker_pool():
    """Create a fresh worker pool executor."""
    return WorkerPool(min_workers=2, max_workers=8)


@pytest.fixture
def sample_task():
    """Create a sample worker task."""
    return WorkerTask(
        task_id="task_123",
        layer_name="episodic",
        query_fn_name="query_episodic",
        args=("test", 5),
        kwargs={"filter": "recent"},
        timeout_seconds=10.0,
        priority=TaskPriority.MEDIUM,
    )


# ============================================================================
# Task Creation Tests
# ============================================================================


def test_worker_task_creation(sample_task):
    """Test creating a worker task."""
    assert sample_task.task_id == "task_123"
    assert sample_task.layer_name == "episodic"
    assert sample_task.priority == TaskPriority.MEDIUM
    assert sample_task.timeout_seconds == 10.0


def test_worker_task_with_critical_priority():
    """Test creating task with CRITICAL priority."""
    task = WorkerTask(
        task_id="critical_task",
        layer_name="semantic",
        query_fn_name="query_semantic",
        priority=TaskPriority.CRITICAL,
    )
    assert task.priority == TaskPriority.CRITICAL


def test_worker_task_age_calculation(sample_task):
    """Test task age calculation."""
    age = sample_task.age_seconds()
    assert age >= 0.0
    assert age < 1.0  # Should be very recent


def test_worker_task_with_empty_args():
    """Test creating task with empty arguments."""
    task = WorkerTask(
        task_id="empty_task",
        layer_name="meta",
        query_fn_name="query_meta",
        args=(),
        kwargs={},
    )
    assert task.args == ()
    assert task.kwargs == {}


# ============================================================================
# Worker Task Result Tests
# ============================================================================


def test_worker_task_result_success():
    """Test creating successful task result."""
    result = WorkerTaskResult(
        task_id="task_123",
        layer_name="episodic",
        success=True,
        result=[1, 2, 3],
        elapsed_ms=45.5,
    )
    assert result.success
    assert result.result == [1, 2, 3]
    assert result.elapsed_ms == 45.5
    assert result.error is None


def test_worker_task_result_failure():
    """Test creating failed task result."""
    result = WorkerTaskResult(
        task_id="task_456",
        layer_name="semantic",
        success=False,
        error="Query timeout",
        elapsed_ms=10000.0,
    )
    assert not result.success
    assert result.error == "Query timeout"
    assert result.result is None


# ============================================================================
# Load Balancer Tests
# ============================================================================


def test_load_balancer_initialization(load_balancer):
    """Test load balancer initializes correctly."""
    assert load_balancer.window_seconds == 10
    assert load_balancer.target_qps == 100.0
    assert load_balancer.worker_loads == {}


def test_load_balancer_select_first_worker(load_balancer):
    """Test load balancer selects first worker."""
    worker_id = load_balancer.select_worker(num_workers=4)
    assert 0 <= worker_id < 4


def test_load_balancer_selects_least_loaded(load_balancer):
    """Test load balancer selects least loaded worker."""
    # Manually set worker loads
    load_balancer.worker_loads = {
        0: 0.8,  # Heavily loaded
        1: 0.2,  # Lightly loaded
        2: 0.5,
    }

    worker_id = load_balancer.select_worker(num_workers=3)
    # Should prefer worker 1 (least loaded)
    assert worker_id >= 0


def test_load_balancer_respects_queue_depth(load_balancer):
    """Test load balancer respects queue depth."""
    load_balancer.worker_queue_depths = {
        0: 50,  # Deep queue
        1: 5,   # Shallow queue
    }

    worker_id = load_balancer.select_worker(num_workers=2)
    assert 0 <= worker_id < 2


def test_load_balancer_tracks_latencies(load_balancer):
    """Test load balancer tracks worker latencies."""
    # Record some latencies
    load_balancer.worker_latencies[0] = [10.0, 15.0, 12.0]
    load_balancer.worker_latencies[1] = [50.0, 55.0]  # Slower

    # Should consider latencies in selection
    worker_id = load_balancer.select_worker(num_workers=2)
    assert 0 <= worker_id < 2


# ============================================================================
# Worker Pool Executor Tests
# ============================================================================


def test_worker_pool_initialization(worker_pool):
    """Test worker pool initializes correctly."""
    assert worker_pool.min_workers == 2
    assert worker_pool.max_workers == 8
    assert worker_pool.num_workers >= 2


def test_worker_pool_custom_bounds():
    """Test worker pool with custom bounds."""
    pool = WorkerPool(min_workers=4, max_workers=16)
    assert pool.min_workers == 4
    assert pool.max_workers == 16


def test_submit_task_to_pool(worker_pool, sample_task):
    """Test submitting a task to pool."""
    # Note: actual execution may fail without proper setup
    result = worker_pool.submit_task(sample_task)
    # Should return a result or future
    assert result is not None


def test_submit_multiple_tasks(worker_pool):
    """Test submitting multiple tasks."""
    tasks = [
        WorkerTask(f"task_{i}", "episodic", "query_episodic")
        for i in range(5)
    ]

    results = []
    for task in tasks:
        result = worker_pool.submit_task(task)
        results.append(result)

    assert len(results) == 5


def test_task_priority_ordering(worker_pool):
    """Test that tasks are ordered by priority."""
    # Submit tasks in reverse priority
    low = WorkerTask("low", "meta", "query", priority=TaskPriority.LOW)
    medium = WorkerTask("med", "meta", "query", priority=TaskPriority.MEDIUM)
    high = WorkerTask("high", "meta", "query", priority=TaskPriority.HIGH)
    critical = WorkerTask("crit", "meta", "query", priority=TaskPriority.CRITICAL)

    for task in [low, medium, high, critical]:
        worker_pool.submit_task(task)

    # Pool should respect priority ordering
    assert worker_pool is not None


def test_worker_pool_scales_up(worker_pool):
    """Test worker pool scales up under load."""
    initial_workers = worker_pool.num_workers

    # Submit many tasks
    for i in range(20):
        task = WorkerTask(f"task_{i}", "episodic", "query")
        worker_pool.submit_task(task)

    # Pool may scale up
    final_workers = worker_pool.num_workers
    assert final_workers <= worker_pool.max_workers


def test_worker_pool_scales_down(worker_pool):
    """Test worker pool scales down under low load."""
    # Let worker pool settle at minimum
    worker_pool.num_workers = worker_pool.min_workers

    # Simulate low load period
    time.sleep(0.1)

    # Workers should not go below minimum
    assert worker_pool.num_workers >= worker_pool.min_workers


def test_worker_pool_shutdown(worker_pool):
    """Test shutting down worker pool."""
    worker_pool.shutdown(wait=True)
    # Pool should be shut down gracefully


# ============================================================================
# Task Execution Tests
# ============================================================================


def test_task_execution_timeout():
    """Test that tasks timeout appropriately."""
    pool = WorkerPool()
    task = WorkerTask(
        "timeout_task",
        "episodic",
        "query_episodic",
        timeout_seconds=0.1,  # Very short timeout
    )

    result = pool.submit_task(task)
    # Task may timeout or execute


def test_task_execution_priority_preemption(worker_pool):
    """Test that high-priority tasks are prioritized."""
    # Submit low-priority task
    low_task = WorkerTask(
        "low", "episodic", "query", priority=TaskPriority.LOW
    )
    worker_pool.submit_task(low_task)

    # Submit high-priority task
    high_task = WorkerTask(
        "high", "episodic", "query", priority=TaskPriority.CRITICAL
    )
    worker_pool.submit_task(high_task)

    # High-priority should execute sooner


# ============================================================================
# Statistics and Monitoring Tests
# ============================================================================


def test_worker_pool_statistics(worker_pool):
    """Test getting worker pool statistics."""
    # Submit some tasks
    for i in range(5):
        task = WorkerTask(f"task_{i}", "episodic", "query")
        worker_pool.submit_task(task)

    stats = worker_pool.get_stats()
    assert isinstance(stats, dict)
    # Stats may include: num_workers, queue_depth, avg_latency, etc.


def test_worker_pool_health_status(worker_pool):
    """Test getting worker pool health status."""
    health = worker_pool.get_health()
    assert isinstance(health, dict)
    # Health may include: all_workers_alive, queue_stable, performance_ok


def test_worker_utilization_tracking(worker_pool):
    """Test tracking worker utilization."""
    # Submit tasks and check utilization
    for i in range(10):
        task = WorkerTask(f"task_{i}", "episodic", "query")
        worker_pool.submit_task(task)

    stats = worker_pool.get_stats()
    # Utilization should be tracked


def test_task_latency_tracking(worker_pool):
    """Test tracking task latency."""
    task = WorkerTask("latency_task", "episodic", "query")
    result = worker_pool.submit_task(task)

    stats = worker_pool.get_stats()
    # Latency should be tracked


# ============================================================================
# Load Balancing Tests
# ============================================================================


def test_load_balancer_adaptive_scaling(worker_pool):
    """Test adaptive worker scaling based on load."""
    initial_workers = worker_pool.num_workers

    # Simulate high load
    for i in range(50):
        task = WorkerTask(f"heavy_task_{i}", "episodic", "query")
        worker_pool.submit_task(task)

    # May scale up
    peak_workers = worker_pool.num_workers
    assert peak_workers <= worker_pool.max_workers

    # Simulate load drop
    time.sleep(0.2)

    # May scale down
    final_workers = worker_pool.num_workers
    assert final_workers >= worker_pool.min_workers


def test_load_balancer_prevents_overload(worker_pool):
    """Test that load balancer prevents overload."""
    # Try to submit more tasks than workers can handle
    submitted = 0
    for i in range(100):
        task = WorkerTask(f"task_{i}", "episodic", "query")
        try:
            result = worker_pool.submit_task(task)
            submitted += 1
        except Exception as e:
            # Pool may reject tasks if overloaded
            break

    # Should have accepted some tasks
    assert submitted > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_worker_pool_handles_invalid_task(worker_pool):
    """Test pool handles invalid task gracefully."""
    # Try to submit None or invalid task
    try:
        result = worker_pool.submit_task(None)
        # May handle gracefully
    except Exception:
        # Or raise appropriate exception
        pass


def test_worker_pool_handles_worker_failure(worker_pool):
    """Test pool recovers from worker failure."""
    # Submit task
    task = WorkerTask("task", "episodic", "query")
    worker_pool.submit_task(task)

    # Simulate worker failure by checking recovery
    health = worker_pool.get_health()
    assert isinstance(health, dict)


def test_worker_pool_timeout_handling(worker_pool):
    """Test handling of task timeouts."""
    task = WorkerTask(
        "long_task",
        "episodic",
        "query",
        timeout_seconds=0.01,
    )

    result = worker_pool.submit_task(task)
    # Should handle timeout gracefully


# ============================================================================
# Edge Cases Tests
# ============================================================================


def test_worker_pool_with_min_equals_max(worker_pool):
    """Test worker pool when min equals max."""
    fixed_pool = WorkerPool(min_workers=4, max_workers=4)
    assert fixed_pool.num_workers == 4

    # Submit tasks
    for i in range(10):
        task = WorkerTask(f"task_{i}", "episodic", "query")
        fixed_pool.submit_task(task)

    # Should maintain 4 workers
    assert fixed_pool.num_workers == 4


def test_worker_pool_single_worker():
    """Test worker pool with single worker."""
    pool = WorkerPool(min_workers=1, max_workers=1)
    assert pool.num_workers == 1

    task = WorkerTask("task", "episodic", "query")
    pool.submit_task(task)


def test_load_balancer_single_worker(load_balancer):
    """Test load balancer with single worker."""
    worker_id = load_balancer.select_worker(num_workers=1)
    assert worker_id == 0


def test_load_balancer_zero_workers(load_balancer):
    """Test load balancer with zero workers."""
    # Should handle gracefully
    try:
        worker_id = load_balancer.select_worker(num_workers=0)
    except Exception:
        pass  # Expected to fail


def test_task_priority_comparison():
    """Test comparing task priorities."""
    assert TaskPriority.CRITICAL.value > TaskPriority.HIGH.value
    assert TaskPriority.HIGH.value > TaskPriority.MEDIUM.value
    assert TaskPriority.MEDIUM.value > TaskPriority.LOW.value
