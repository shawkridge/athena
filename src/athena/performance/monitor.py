"""Performance monitoring and metrics collection."""

import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional

import psutil


class PerformanceMetric:
    """Single performance metric."""

    def __init__(self, name: str, unit: str = "ms"):
        """Initialize metric.

        Args:
            name: Metric name
            unit: Measurement unit (default: milliseconds)
        """
        self.name = name
        self.unit = unit
        self.samples: deque[tuple[datetime, float]] = deque(maxlen=1000)  # Keep last 1000 samples
        self.total = 0.0
        self.count = 0

    def record(self, value: float):
        """Record a metric value.

        Args:
            value: Metric value
        """
        self.samples.append((datetime.now(), value))
        self.total += value
        self.count += 1

    def get_average(self) -> float:
        """Get average value.

        Returns:
            Average value or 0 if no samples
        """
        return self.total / self.count if self.count > 0 else 0

    def get_min(self) -> Optional[float]:
        """Get minimum value.

        Returns:
            Minimum value or None
        """
        if not self.samples:
            return None
        return min(value for _, value in self.samples)

    def get_max(self) -> Optional[float]:
        """Get maximum value.

        Returns:
            Maximum value or None
        """
        if not self.samples:
            return None
        return max(value for _, value in self.samples)

    def get_percentile(self, percentile: int) -> Optional[float]:
        """Get percentile value.

        Args:
            percentile: Percentile (0-100)

        Returns:
            Value at percentile or None
        """
        if not self.samples:
            return None

        values = sorted([value for _, value in self.samples])
        idx = int(len(values) * percentile / 100)
        return values[min(idx, len(values) - 1)]

    def get_stats(self) -> dict:
        """Get metric statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "name": self.name,
            "unit": self.unit,
            "count": self.count,
            "total": self.total,
            "average": self.get_average(),
            "min": self.get_min(),
            "max": self.get_max(),
            "p50": self.get_percentile(50),
            "p95": self.get_percentile(95),
            "p99": self.get_percentile(99),
        }


class OperationTimer:
    """Context manager for timing operations."""

    def __init__(self, monitor: "PerformanceMonitor", operation_name: str):
        """Initialize operation timer.

        Args:
            monitor: PerformanceMonitor instance
            operation_name: Name of operation to time
        """
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record."""
        if self.start_time:
            elapsed_ms = (time.time() - self.start_time) * 1000
            self.monitor.record_operation(self.operation_name, elapsed_ms)


class PerformanceMonitor:
    """Monitor system performance metrics."""

    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: dict[str, PerformanceMetric] = {}
        self.operation_counts: defaultdict[str, int] = defaultdict(int)
        self.error_counts: defaultdict[str, int] = defaultdict(int)
        self.start_time = datetime.now()

    def record_operation(self, operation_name: str, duration_ms: float):
        """Record operation timing.

        Args:
            operation_name: Name of operation
            duration_ms: Duration in milliseconds
        """
        if operation_name not in self.metrics:
            self.metrics[operation_name] = PerformanceMetric(operation_name)

        self.metrics[operation_name].record(duration_ms)
        self.operation_counts[operation_name] += 1

    def record_error(self, operation_name: str):
        """Record operation error.

        Args:
            operation_name: Name of operation that errored
        """
        self.error_counts[operation_name] += 1

    def timer(self, operation_name: str) -> OperationTimer:
        """Get context manager for timing operation.

        Args:
            operation_name: Name of operation

        Returns:
            OperationTimer context manager
        """
        return OperationTimer(self, operation_name)

    def get_metric(self, operation_name: str) -> Optional[dict]:
        """Get statistics for operation.

        Args:
            operation_name: Name of operation

        Returns:
            Statistics dictionary or None
        """
        if operation_name in self.metrics:
            return self.metrics[operation_name].get_stats()
        return None

    def get_all_metrics(self) -> dict[str, dict]:
        """Get all operation metrics.

        Returns:
            Dictionary of operation statistics
        """
        return {name: metric.get_stats() for name, metric in self.metrics.items()}

    def get_summary(self) -> dict:
        """Get summary of all operations.

        Returns:
            Summary dictionary
        """
        uptime = datetime.now() - self.start_time
        total_operations = sum(self.operation_counts.values())
        total_errors = sum(self.error_counts.values())

        # Calculate total time spent
        total_time_ms = sum(metric.total for metric in self.metrics.values())

        return {
            "uptime": uptime.total_seconds(),
            "total_operations": total_operations,
            "total_errors": total_errors,
            "total_time_ms": total_time_ms,
            "average_operation_time_ms": (
                total_time_ms / total_operations if total_operations > 0 else 0
            ),
            "operations_per_second": (
                total_operations / (uptime.total_seconds()) if uptime.total_seconds() > 0 else 0
            ),
            "error_rate": total_errors / total_operations if total_operations > 0 else 0,
        }

    def get_slowest_operations(self, limit: int = 10) -> list[dict]:
        """Get slowest operations.

        Args:
            limit: Maximum number to return

        Returns:
            List of slowest operation stats
        """
        operations = [(name, metric.get_max() or 0) for name, metric in self.metrics.items()]

        operations.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "operation": name,
                "max_duration_ms": duration,
                "stats": self.get_metric(name),
            }
            for name, duration in operations[:limit]
        ]

    def get_system_stats(self) -> dict:
        """Get system resource statistics.

        Returns:
            System statistics
        """
        try:
            process = psutil.Process()

            return {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "memory_percent": process.memory_percent(),
                "open_files": len(process.open_files()),
                "threads": process.num_threads(),
            }
        except Exception as e:
            print(f"Error getting system stats: {e}")
            return {}

    def print_summary(self):
        """Print performance summary to console."""
        summary = self.get_summary()
        metrics = self.get_slowest_operations(5)

        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)

        print(f"\nUptime: {summary['uptime']:.2f}s")
        print(f"Total Operations: {summary['total_operations']}")
        print(f"Total Errors: {summary['total_errors']}")
        print(f"Error Rate: {summary['error_rate']:.2%}")
        print(f"Ops/Sec: {summary['operations_per_second']:.0f}")
        print(f"Avg Op Time: {summary['average_operation_time_ms']:.2f}ms")

        print("\nSLOWEST OPERATIONS:")
        for i, op in enumerate(metrics, 1):
            stats = op["stats"]
            print(
                f"  {i}. {op['operation']}: "
                f"avg={stats['average']:.2f}ms, "
                f"max={stats['max']:.2f}ms, "
                f"p95={stats['p95']:.2f}ms"
            )

        system = self.get_system_stats()
        if system:
            print("\nSYSTEM RESOURCES:")
            print(f"  CPU: {system.get('cpu_percent', 0):.1f}%")
            print(
                f"  Memory: {system.get('memory_mb', 0):.1f}MB ({system.get('memory_percent', 0):.1f}%)"
            )
            print(f"  Threads: {system.get('threads', 0)}")

        print("=" * 60 + "\n")


# Global performance monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance.

    Returns:
        PerformanceMonitor instance
    """
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def record_operation(operation_name: str, duration_ms: float):
    """Record operation timing globally.

    Args:
        operation_name: Name of operation
        duration_ms: Duration in milliseconds
    """
    get_monitor().record_operation(operation_name, duration_ms)


def record_error(operation_name: str):
    """Record operation error globally.

    Args:
        operation_name: Name of operation
    """
    get_monitor().record_error(operation_name)


def timer(operation_name: str) -> OperationTimer:
    """Get timer context manager globally.

    Args:
        operation_name: Name of operation

    Returns:
        OperationTimer context manager
    """
    return get_monitor().timer(operation_name)
