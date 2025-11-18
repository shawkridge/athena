"""Metrics collection and monitoring for research operations."""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single research operation."""

    operation: str  # "agent_search", "aggregation", "memory_storage", etc.
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    items_processed: int = 0
    items_output: int = 0

    def complete(self, success: bool = True, error: Optional[str] = None, items_output: int = 0):
        """Mark operation as complete.

        Args:
            success: Whether operation succeeded
            error: Error message if failed
            items_output: Number of items produced
        """
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error
        self.items_output = items_output

    @property
    def throughput(self) -> float:
        """Items processed per second."""
        if self.duration_ms is None or self.duration_ms == 0:
            return 0.0
        return (self.items_processed / self.duration_ms) * 1000


class ResearchMetricsCollector:
    """Collects and tracks research operation metrics."""

    def __init__(self, max_history: int = 1000):
        """Initialize metrics collector.

        Args:
            max_history: Maximum metrics to keep in history
        """
        self.max_history = max_history
        self.metrics_history: list[OperationMetrics] = []
        self.current_task_metrics: dict[int, dict] = {}  # task_id -> metrics

    def start_operation(self, operation: str, task_id: Optional[int] = None) -> OperationMetrics:
        """Start tracking an operation.

        Args:
            operation: Operation type
            task_id: Optional task ID

        Returns:
            Metrics object to update
        """
        metrics = OperationMetrics(operation=operation)

        if task_id is not None:
            if task_id not in self.current_task_metrics:
                self.current_task_metrics[task_id] = {}
            self.current_task_metrics[task_id][operation] = metrics
        else:
            self.metrics_history.append(metrics)
            # Trim history if needed
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history :]

        return metrics

    def record_operation(self, metrics: OperationMetrics):
        """Record completed operation metrics.

        Args:
            metrics: Completed operation metrics
        """
        self.metrics_history.append(metrics)

        # Trim history if needed
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history :]

        status = "✓" if metrics.success else "✗"
        logger.debug(
            f"{status} {metrics.operation} completed in {metrics.duration_ms:.1f}ms "
            f"({metrics.items_output} items)"
        )

    def get_task_metrics(self, task_id: int) -> dict:
        """Get all metrics for a task.

        Args:
            task_id: Task ID

        Returns:
            Metrics dict
        """
        return self.current_task_metrics.get(task_id, {})

    def get_operation_stats(self, operation: str) -> dict:
        """Get aggregate statistics for an operation type.

        Args:
            operation: Operation type

        Returns:
            Statistics dict
        """
        ops = [m for m in self.metrics_history if m.operation == operation]

        if not ops:
            return {
                "operation": operation,
                "count": 0,
                "success_rate": 0.0,
            }

        successful = [m for m in ops if m.success]
        durations = [m.duration_ms for m in ops if m.duration_ms is not None]

        return {
            "operation": operation,
            "count": len(ops),
            "successful": len(successful),
            "failed": len(ops) - len(successful),
            "success_rate": len(successful) / len(ops) if ops else 0.0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "min_duration_ms": min(durations) if durations else 0.0,
            "max_duration_ms": max(durations) if durations else 0.0,
            "total_items_processed": sum(m.items_processed for m in ops),
            "total_items_output": sum(m.items_output for m in ops),
        }

    def get_all_stats(self) -> dict:
        """Get all collected metrics and statistics.

        Returns:
            Comprehensive stats dict
        """
        operations = set(m.operation for m in self.metrics_history)

        stats = {
            "total_operations": len(self.metrics_history),
            "unique_operations": len(operations),
            "operations": {op: self.get_operation_stats(op) for op in sorted(operations)},
            "overall": {
                "total_successful": sum(1 for m in self.metrics_history if m.success),
                "total_failed": sum(1 for m in self.metrics_history if not m.success),
            },
        }

        # Calculate overall success rate
        total = len(self.metrics_history)
        if total > 0:
            stats["overall"]["success_rate"] = stats["overall"]["total_successful"] / total

        return stats

    def clear_history(self):
        """Clear all metrics history."""
        self.metrics_history.clear()
        self.current_task_metrics.clear()
        logger.info("Metrics history cleared")
