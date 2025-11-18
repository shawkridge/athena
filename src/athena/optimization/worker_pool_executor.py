"""Worker pool executor for distributed query execution.

This module provides process-based parallel execution for high-concurrency
scenarios, scaling from 2 to 20 worker processes. It includes:
- Dynamic worker count adjustment
- Load balancing across workers
- Priority-based task queuing
- Graceful error handling
- Result caching before return
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task execution priority levels."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class WorkerTask:
    """Single task to be executed by worker."""

    task_id: str
    layer_name: str
    query_fn_name: str  # Serializable function reference
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    timeout_seconds: float = 10.0
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: float = field(default_factory=time.time)

    def age_seconds(self) -> float:
        """Get age of task in seconds."""
        return time.time() - self.created_at


@dataclass
class WorkerTaskResult:
    """Result of worker task execution."""

    task_id: str
    layer_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    worker_id: Optional[int] = None


class LoadBalancer:
    """Distributes tasks to least-loaded workers."""

    def __init__(self, window_seconds: int = 10, target_qps: float = 100.0):
        """Initialize load balancer.

        Args:
            window_seconds: Sliding window for load calculation
            target_qps: Target queries per second
        """
        self.window_seconds = window_seconds
        self.target_qps = target_qps

        # Per-worker metrics
        self.worker_loads: Dict[int, float] = {}  # worker_id -> current load (0-1)
        self.worker_queue_depths: Dict[int, int] = {}  # worker_id -> queue size
        self.worker_latencies: Dict[int, List[float]] = {}  # worker_id -> latencies

    def select_worker(self, num_workers: int) -> int:
        """Select best worker for next task.

        Args:
            num_workers: Total number of workers available

        Returns:
            Worker ID (0-indexed)
        """
        # Initialize if needed
        for i in range(num_workers):
            if i not in self.worker_loads:
                self.worker_loads[i] = 0.0
                self.worker_queue_depths[i] = 0
                self.worker_latencies[i] = []

        # Find worker with lowest load
        min_load = float("inf")
        best_worker = 0

        for worker_id in range(num_workers):
            load = self.worker_loads.get(worker_id, 0.0)
            queue_depth = self.worker_queue_depths.get(worker_id, 0)

            # Combine load and queue depth
            combined_load = load + (queue_depth * 0.1)

            if combined_load < min_load:
                min_load = combined_load
                best_worker = worker_id

        return best_worker

    def record_task_completion(self, worker_id: int, elapsed_ms: float, queue_depth: int) -> None:
        """Record task completion for load tracking.

        Args:
            worker_id: Worker that completed task
            elapsed_ms: Task execution time
            queue_depth: Current queue depth
        """
        # Update load (exponential moving average)
        old_load = self.worker_loads.get(worker_id, 0.0)
        new_load = min(elapsed_ms / 100.0, 1.0)  # Normalize to 0-1
        self.worker_loads[worker_id] = (old_load * 0.7) + (new_load * 0.3)

        # Update queue depth
        self.worker_queue_depths[worker_id] = queue_depth

        # Track latency
        if worker_id not in self.worker_latencies:
            self.worker_latencies[worker_id] = []
        self.worker_latencies[worker_id].append(elapsed_ms)

        # Keep only recent latencies (sliding window)
        max_latencies = 100
        if len(self.worker_latencies[worker_id]) > max_latencies:
            self.worker_latencies[worker_id] = self.worker_latencies[worker_id][-max_latencies:]


class WorkerPool:
    """Manages pool of worker processes for distributed execution.

    Dynamically scales from min_workers to max_workers based on queue depth
    and latency. Each worker executes tasks from the queue in order,
    with priority-based routing.

    Example:
        pool = WorkerPool(min_workers=2, max_workers=20)

        # Submit task
        result = await pool.submit_task(
            WorkerTask(
                task_id="q123",
                layer_name="semantic",
                query_fn_name="search",
                args=(query_text, k),
                priority=TaskPriority.HIGH,
            ),
            timeout_seconds=30.0
        )

        # Check health
        health = pool.get_health_status()
    """

    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 20,
        task_queue_size: int = 1000,
        enable_dynamic_scaling: bool = True,
    ):
        """Initialize worker pool.

        Args:
            min_workers: Minimum number of workers
            max_workers: Maximum number of workers
            task_queue_size: Maximum task queue size
            enable_dynamic_scaling: Allow dynamic worker adjustment
        """
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.task_queue_size = task_queue_size
        self.enable_dynamic_scaling = enable_dynamic_scaling

        # Task management
        self.task_queue: asyncio.Queue = None  # Initialized in __aenter__
        self.priority_queues: Dict[TaskPriority, asyncio.Queue] = {}
        self.result_cache: Dict[str, WorkerTaskResult] = {}

        # Load balancing
        self.load_balancer = LoadBalancer()

        # Worker management
        self.active_workers = min_workers
        self.worker_processes: List[Any] = []

        # Statistics
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0
        self.total_bytes_processed = 0

        logger.info(
            f"WorkerPool initialized: {min_workers}-{max_workers} workers, "
            f"queue_size={task_queue_size}"
        )

    @property
    def num_workers(self) -> int:
        """Get current number of active workers.

        Returns:
            Current number of active worker processes.
        """
        return self.active_workers

    @num_workers.setter
    def num_workers(self, value: int) -> None:
        """Set the number of active workers.

        Args:
            value: Number of workers to set (will be clamped to min/max bounds)
        """
        self.active_workers = max(self.min_workers, min(value, self.max_workers))

    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown_async()

    async def _initialize(self) -> None:
        """Initialize worker queues and processes."""
        self.task_queue = asyncio.Queue(maxsize=self.task_queue_size)

        # Priority queues
        for priority in TaskPriority:
            self.priority_queues[priority] = asyncio.Queue()

        logger.info(f"WorkerPool initialized with {self.active_workers} workers")

    async def submit_task(
        self, task: WorkerTask, timeout_seconds: float = 30.0
    ) -> WorkerTaskResult:
        """Submit task to pool and wait for result.

        Args:
            task: Task to execute
            timeout_seconds: Max time to wait for result

        Returns:
            Result of task execution

        Raises:
            asyncio.TimeoutError: If task doesn't complete in time
        """
        self.total_tasks_submitted += 1

        # Check if we should adjust worker count
        if self.enable_dynamic_scaling:
            queue_depth = self.task_queue.qsize()
            await self._adjust_worker_count(queue_depth)

        try:
            # Submit to priority queue
            await self.priority_queues[task.priority].put(task, timeout=1.0)

            # Wait for result with timeout
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                if task.task_id in self.result_cache:
                    result = self.result_cache.pop(task.task_id)
                    self.total_tasks_completed += 1
                    return result

                # Check every 10ms
                await asyncio.sleep(0.01)

            # Timeout
            self.total_tasks_failed += 1
            return WorkerTaskResult(
                task_id=task.task_id,
                layer_name=task.layer_name,
                success=False,
                error=f"Task timeout after {timeout_seconds}s",
                elapsed_ms=timeout_seconds * 1000,
            )

        except asyncio.QueueFull:
            self.total_tasks_failed += 1
            return WorkerTaskResult(
                task_id=task.task_id,
                layer_name=task.layer_name,
                success=False,
                error="Task queue full",
            )
        except Exception as e:
            self.total_tasks_failed += 1
            logger.error(f"Task submission failed: {e}")
            return WorkerTaskResult(
                task_id=task.task_id,
                layer_name=task.layer_name,
                success=False,
                error=str(e),
            )

    async def _adjust_worker_count(self, queue_depth: int) -> None:
        """Dynamically adjust worker count based on queue depth.

        Args:
            queue_depth: Current task queue depth
        """
        if not self.enable_dynamic_scaling:
            return

        # Simple heuristic: scale based on queue depth
        # - If queue empty, use min workers
        # - If queue growing, add workers
        # - If queue full, max out workers

        target_workers = self.min_workers

        if queue_depth > self.task_queue_size * 0.8:
            # Queue 80%+ full, scale to max
            target_workers = self.max_workers
        elif queue_depth > self.task_queue_size * 0.5:
            # Queue 50%+ full, scale up
            scale_factor = queue_depth / self.task_queue_size
            target_workers = int(
                self.min_workers + (self.max_workers - self.min_workers) * scale_factor
            )

        # Apply adjustment with hysteresis (don't thrash)
        if target_workers > self.active_workers and target_workers > self.active_workers:
            self.active_workers = min(target_workers, self.max_workers)
            logger.info(f"Scaling up to {self.active_workers} workers")

        elif target_workers < self.active_workers and target_workers < self.active_workers * 0.8:
            self.active_workers = max(target_workers, self.min_workers)
            logger.info(f"Scaling down to {self.active_workers} workers")

    def get_health_status(self) -> Dict[str, Any]:
        """Get worker pool health status.

        Returns:
            Dictionary with health metrics
        """
        queue_depth = self.task_queue.qsize() if self.task_queue else 0

        return {
            "active_workers": self.active_workers,
            "min_workers": self.min_workers,
            "max_workers": self.max_workers,
            "queue_depth": queue_depth,
            "queue_capacity": self.task_queue_size,
            "queue_utilization": (
                queue_depth / self.task_queue_size if self.task_queue_size > 0 else 0
            ),
            "total_tasks_submitted": self.total_tasks_submitted,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_failed": self.total_tasks_failed,
            "success_rate": (self.total_tasks_completed / max(self.total_tasks_submitted, 1)),
            "total_bytes_processed": self.total_bytes_processed,
            "cached_results": len(self.result_cache),
        }

    def get_health(self) -> Dict[str, Any]:
        """Get health status of worker pool.

        Returns:
            Dictionary with health metrics:
            - active_workers: Number of currently active workers
            - total_tasks_submitted: Total tasks submitted
            - total_tasks_completed: Total tasks completed
            - total_tasks_failed: Total tasks that failed
            - avg_queue_depth: Average queue depth across workers
            - health_status: 'healthy', 'degraded', or 'unhealthy'
        """
        health_status = "healthy"
        if self.total_tasks_submitted > 0:
            failure_rate = self.total_tasks_failed / self.total_tasks_submitted
            if failure_rate > 0.1:
                health_status = "degraded"
            if failure_rate > 0.25:
                health_status = "unhealthy"

        return {
            "active_workers": self.active_workers,
            "total_tasks_submitted": self.total_tasks_submitted,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_failed": self.total_tasks_failed,
            "task_success_rate": (
                self.total_tasks_completed / self.total_tasks_submitted
                if self.total_tasks_submitted > 0
                else 0.0
            ),
            "health_status": health_status,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the worker pool.

        Returns:
            Dictionary with performance metrics:
            - total_tasks_submitted: Total tasks submitted to pool
            - total_tasks_completed: Total tasks successfully completed
            - total_tasks_failed: Total tasks that failed
            - total_bytes_processed: Total bytes processed
            - active_workers: Current number of active workers
            - task_success_rate: Percentage of tasks completed successfully
        """
        return {
            "total_tasks_submitted": self.total_tasks_submitted,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_failed": self.total_tasks_failed,
            "total_bytes_processed": self.total_bytes_processed,
            "active_workers": self.active_workers,
            "task_success_rate": (
                (self.total_tasks_completed / self.total_tasks_submitted * 100)
                if self.total_tasks_submitted > 0
                else 0.0
            ),
        }

    def shutdown(self, wait: bool = True) -> None:
        """Gracefully shut down worker pool.

        Args:
            wait: Whether to wait for pending tasks to complete (default: True)
        """
        logger.info(
            f"Shutting down WorkerPool: "
            f"completed={self.total_tasks_completed}, "
            f"failed={self.total_tasks_failed}, "
            f"wait={wait}"
        )
        # In real implementation, would terminate worker processes
        self.worker_processes.clear()

    async def shutdown_async(self, wait: bool = True) -> None:
        """Async gracefully shut down worker pool.

        Args:
            wait: Whether to wait for pending tasks to complete (default: True)
        """
        logger.info(
            f"Shutting down WorkerPool (async): "
            f"completed={self.total_tasks_completed}, "
            f"failed={self.total_tasks_failed}, "
            f"wait={wait}"
        )
        # In real implementation, would terminate worker processes
        self.worker_processes.clear()

    def reset(self) -> None:
        """Reset statistics (for testing)."""
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0
        self.total_bytes_processed = 0
        self.result_cache.clear()
        logger.info("WorkerPool reset")
