"""Prometheus metrics exporters for Athena memory system (Phase 3).

Exposes metrics for:
- Operation counts and latencies
- Resource usage (memory, CPU, connections)
- Cache performance (hits, misses, evictions)
- Business metrics (memories stored, consolidations, procedures learned)

Integration with Prometheus:
- Exposes metrics at /metrics endpoint
- Configurable push gateway support
- Histogram-based latency tracking with percentiles
"""

import time
import psutil
import logging
from contextlib import contextmanager
from typing import Optional
from functools import wraps

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Prometheus metrics collection for Athena operations."""

    def __init__(self, registry: Optional["CollectorRegistry"] = None):
        """Initialize Prometheus metrics.

        Args:
            registry: Optional CollectorRegistry (defaults to global registry)
        """
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus not available. Install with: pip install prometheus-client")
            self.enabled = False
            return

        self.enabled = True
        self.registry = registry

        # Operation metrics
        self.operation_counter = Counter(
            "athena_operations_total",
            "Total operations by type and status",
            ["operation_type", "status"],
            registry=self.registry,
        )

        self.operation_latency = Histogram(
            "athena_operation_latency_seconds",
            "Operation latency in seconds",
            ["operation_type"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry,
        )

        # Resource metrics
        self.memory_usage = Gauge(
            "athena_memory_bytes", "Memory usage in bytes", registry=self.registry
        )

        self.cpu_usage = Gauge("athena_cpu_percent", "CPU usage percentage", registry=self.registry)

        self.db_connections = Gauge(
            "athena_db_connections_active", "Active database connections", registry=self.registry
        )

        # Cache metrics
        self.cache_hits = Counter(
            "athena_cache_hits_total",
            "Total cache hits by type",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_misses = Counter(
            "athena_cache_misses_total",
            "Total cache misses by type",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_evictions = Counter(
            "athena_cache_evictions_total",
            "Total LRU evictions by cache type",
            ["cache_type"],
            registry=self.registry,
        )

        # Business metrics
        self.memories_stored = Gauge(
            "athena_memories_stored_total", "Total memories stored", registry=self.registry
        )

        self.consolidations_total = Counter(
            "athena_consolidations_total",
            "Total consolidation runs",
            ["strategy"],
            registry=self.registry,
        )

        self.procedures_learned = Gauge(
            "athena_procedures_learned_total", "Total procedures extracted", registry=self.registry
        )

        self.graph_entities = Gauge(
            "athena_graph_entities_total",
            "Total entities in knowledge graph",
            registry=self.registry,
        )

        self.graph_relations = Gauge(
            "athena_graph_relations_total",
            "Total relations in knowledge graph",
            registry=self.registry,
        )

        # Error metrics
        self.operation_errors = Counter(
            "athena_operation_errors_total",
            "Total operation errors by type",
            ["operation_type", "error_type"],
            registry=self.registry,
        )

        # Working memory metrics
        self.working_memory_items = Gauge(
            "athena_working_memory_items_current",
            "Current items in working memory",
            registry=self.registry,
        )

    def record_operation(self, operation_type: str, status: str = "success", duration: float = 0):
        """Record an operation metric.

        Args:
            operation_type: Type of operation (recall, remember, consolidate, etc.)
            status: Operation status (success, error, timeout)
            duration: Operation duration in seconds
        """
        if not self.enabled:
            return

        self.operation_counter.labels(operation_type=operation_type, status=status).inc()
        if duration > 0:
            self.operation_latency.labels(operation_type=operation_type).observe(duration)

    def record_error(self, operation_type: str, error_type: str):
        """Record an operation error.

        Args:
            operation_type: Type of operation that failed
            error_type: Type of error (ValueError, TimeoutError, etc.)
        """
        if not self.enabled:
            return

        self.operation_errors.labels(operation_type=operation_type, error_type=error_type).inc()

    def record_cache_hit(self, cache_type: str):
        """Record a cache hit.

        Args:
            cache_type: Type of cache (semantic, graph, etc.)
        """
        if not self.enabled:
            return

        self.cache_hits.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str):
        """Record a cache miss.

        Args:
            cache_type: Type of cache
        """
        if not self.enabled:
            return

        self.cache_misses.labels(cache_type=cache_type).inc()

    def record_cache_eviction(self, cache_type: str):
        """Record a cache eviction.

        Args:
            cache_type: Type of cache
        """
        if not self.enabled:
            return

        self.cache_evictions.labels(cache_type=cache_type).inc()

    def set_memories_stored(self, count: int):
        """Set total memories stored count.

        Args:
            count: Total memory count
        """
        if not self.enabled:
            return

        self.memories_stored.set(count)

    def record_consolidation(self, strategy: str):
        """Record a consolidation run.

        Args:
            strategy: Consolidation strategy used
        """
        if not self.enabled:
            return

        self.consolidations_total.labels(strategy=strategy).inc()

    def set_procedures_learned(self, count: int):
        """Set total procedures learned.

        Args:
            count: Total procedure count
        """
        if not self.enabled:
            return

        self.procedures_learned.set(count)

    def set_graph_metrics(self, entities: int, relations: int):
        """Set knowledge graph metrics.

        Args:
            entities: Total entity count
            relations: Total relation count
        """
        if not self.enabled:
            return

        self.graph_entities.set(entities)
        self.graph_relations.set(relations)

    def update_resource_metrics(self):
        """Update resource usage metrics (memory, CPU)."""
        if not self.enabled:
            return

        try:
            process = psutil.Process()

            # Memory usage in bytes
            memory_info = process.memory_info()
            self.memory_usage.set(memory_info.rss)

            # CPU usage percentage
            cpu_percent = process.cpu_percent(interval=0.1)
            self.cpu_usage.set(cpu_percent)

        except Exception as e:
            logger.warning(f"Failed to update resource metrics: {e}")

    def set_working_memory_items(self, count: int):
        """Set current working memory item count.

        Args:
            count: Current item count
        """
        if not self.enabled:
            return

        self.working_memory_items.set(count)

    def set_db_connections(self, count: int):
        """Set active database connection count.

        Args:
            count: Connection count
        """
        if not self.enabled:
            return

        self.db_connections.set(count)

    @contextmanager
    def operation_context(self, operation_type: str):
        """Context manager for tracking operation timing and errors.

        Args:
            operation_type: Type of operation

        Yields:
            Dictionary for tracking operation context
        """
        context = {"start_time": time.time(), "status": "success"}
        try:
            yield context
        except Exception as e:
            context["status"] = "error"
            error_type = type(e).__name__
            self.record_error(operation_type, error_type)
            raise
        finally:
            duration = time.time() - context["start_time"]
            self.record_operation(operation_type, context["status"], duration)

    def track_operation(self, operation_type: str):
        """Decorator for tracking operation metrics.

        Args:
            operation_type: Type of operation

        Returns:
            Decorated function
        """

        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.operation_context(operation_type) as ctx:
                    return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.operation_context(operation_type) as ctx:
                    return func(*args, **kwargs)

            # Return appropriate wrapper based on function type
            if hasattr(func, "__await__"):
                return async_wrapper
            return sync_wrapper

        return decorator

    def export_metrics(self) -> str:
        """Export metrics in Prometheus text format.

        Returns:
            Prometheus format metrics string
        """
        if not self.enabled:
            return "# Prometheus metrics not available"

        try:
            return generate_latest(self.registry).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return "# Error exporting metrics"


# Global metrics instance
_metrics_instance: Optional[PrometheusMetrics] = None


def get_metrics() -> PrometheusMetrics:
    """Get global metrics instance.

    Returns:
        PrometheusMetrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics()
    return _metrics_instance


def initialize_metrics(registry: Optional["CollectorRegistry"] = None) -> PrometheusMetrics:
    """Initialize global metrics instance.

    Args:
        registry: Optional CollectorRegistry

    Returns:
        PrometheusMetrics instance
    """
    global _metrics_instance
    _metrics_instance = PrometheusMetrics(registry)
    return _metrics_instance
