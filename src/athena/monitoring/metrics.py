"""Prometheus metrics for Memory MCP monitoring.

Provides metrics for query latency, throughput, errors, and system health.
"""

from typing import Optional, Dict, Any
import time
from functools import wraps


class MetricsCollector:
    """Collect and track metrics for Memory MCP."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Any] = {
            # Query metrics
            "query_latency_ms": [],
            "query_count": 0,
            "query_errors": 0,
            # Consolidation metrics
            "consolidation_duration_ms": [],
            "consolidation_count": 0,
            "consolidation_errors": 0,
            "events_consolidated": 0,
            "patterns_extracted": 0,
            # Memory metrics
            "memory_count": {},  # project_id -> count
            "memory_by_layer": {},  # layer -> count
            # Cache metrics
            "cache_hits": 0,
            "cache_misses": 0,
            # Error metrics
            "errors_by_type": {},
        }

    def record_query(self, layer: str, duration_ms: float, success: bool = True):
        """Record a query operation."""
        self.metrics["query_count"] += 1
        self.metrics["query_latency_ms"].append(duration_ms)

        if not success:
            self.metrics["query_errors"] += 1

    def record_consolidation(
        self,
        duration_ms: float,
        events_processed: int,
        patterns_extracted: int,
        success: bool = True,
    ):
        """Record a consolidation operation."""
        self.metrics["consolidation_count"] += 1
        self.metrics["consolidation_duration_ms"].append(duration_ms)
        self.metrics["events_consolidated"] += events_processed
        self.metrics["patterns_extracted"] += patterns_extracted

        if not success:
            self.metrics["consolidation_errors"] += 1

    def record_memory(self, project_id: int, layer: str, count: int):
        """Record memory count by project and layer."""
        if project_id not in self.metrics["memory_count"]:
            self.metrics["memory_count"][project_id] = 0
        self.metrics["memory_count"][project_id] = count

        if layer not in self.metrics["memory_by_layer"]:
            self.metrics["memory_by_layer"][layer] = 0
        self.metrics["memory_by_layer"][layer] = count

    def record_cache_hit(self):
        """Record cache hit."""
        self.metrics["cache_hits"] += 1

    def record_cache_miss(self):
        """Record cache miss."""
        self.metrics["cache_misses"] += 1

    def record_error(self, error_type: str):
        """Record an error."""
        if error_type not in self.metrics["errors_by_type"]:
            self.metrics["errors_by_type"][error_type] = 0
        self.metrics["errors_by_type"][error_type] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics stats."""
        import statistics

        stats = {
            "query": {
                "count": self.metrics["query_count"],
                "errors": self.metrics["query_errors"],
            },
            "consolidation": {
                "count": self.metrics["consolidation_count"],
                "errors": self.metrics["consolidation_errors"],
                "events_processed": self.metrics["events_consolidated"],
                "patterns_extracted": self.metrics["patterns_extracted"],
            },
            "memory": {
                "total_memories": sum(self.metrics["memory_count"].values()),
                "by_layer": self.metrics["memory_by_layer"],
            },
            "cache": {
                "hits": self.metrics["cache_hits"],
                "misses": self.metrics["cache_misses"],
                "hit_rate": (
                    self.metrics["cache_hits"]
                    / (self.metrics["cache_hits"] + self.metrics["cache_misses"] or 1)
                ),
            },
            "errors": self.metrics["errors_by_type"],
        }

        # Add latency stats
        if self.metrics["query_latency_ms"]:
            latencies = self.metrics["query_latency_ms"]
            stats["query"]["latency_ms"] = {
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "min": min(latencies),
                "max": max(latencies),
            }

        if self.metrics["consolidation_duration_ms"]:
            durations = self.metrics["consolidation_duration_ms"]
            stats["consolidation"]["duration_ms"] = {
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "min": min(durations),
                "max": max(durations),
            }

        return stats

    def reset(self):
        """Reset all metrics."""
        self.__init__()


# Global metrics collector
_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def track_operation(operation_name: str):
    """Decorator to track operation timing and errors."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            collector = get_collector()
            start = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000

                if operation_name == "query":
                    collector.record_query(
                        layer=kwargs.get("layer", "unknown"),
                        duration_ms=elapsed_ms,
                        success=True,
                    )
                elif operation_name == "consolidation":
                    collector.record_consolidation(
                        duration_ms=elapsed_ms,
                        events_processed=kwargs.get("events_processed", 0),
                        patterns_extracted=kwargs.get("patterns_extracted", 0),
                        success=True,
                    )

                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                collector.record_error(type(e).__name__)

                if operation_name == "query":
                    collector.record_query(
                        layer=kwargs.get("layer", "unknown"),
                        duration_ms=elapsed_ms,
                        success=False,
                    )
                elif operation_name == "consolidation":
                    collector.record_consolidation(
                        duration_ms=elapsed_ms,
                        events_processed=0,
                        patterns_extracted=0,
                        success=False,
                    )

                raise

        return wrapper

    return decorator


# Prometheus-compatible metric classes
class Counter:
    """Simple counter metric."""

    def __init__(self, name: str, help_text: str, labels: Optional[list] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or []
        self.value = 0
        self.label_values = {}

    def inc(self, amount: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment counter."""
        if labels:
            key = tuple(labels.items())
            self.label_values[key] = self.label_values.get(key, 0) + amount
        else:
            self.value += amount

    def get(self) -> float:
        """Get counter value."""
        return self.value


class Gauge:
    """Simple gauge metric."""

    def __init__(self, name: str, help_text: str, labels: Optional[list] = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or []
        self.value = 0
        self.label_values = {}

    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        if labels:
            key = tuple(labels.items())
            self.label_values[key] = value
        else:
            self.value = value

    def inc(self, amount: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment gauge."""
        if labels:
            key = tuple(labels.items())
            self.label_values[key] = self.label_values.get(key, 0) + amount
        else:
            self.value += amount

    def dec(self, amount: float = 1, labels: Optional[Dict[str, str]] = None):
        """Decrement gauge."""
        if labels:
            key = tuple(labels.items())
            self.label_values[key] = self.label_values.get(key, 0) - amount
        else:
            self.value -= amount

    def get(self) -> float:
        """Get gauge value."""
        return self.value


class Histogram:
    """Simple histogram metric."""

    def __init__(
        self,
        name: str,
        help_text: str,
        buckets: Optional[list] = None,
        labels: Optional[list] = None,
    ):
        self.name = name
        self.help_text = help_text
        self.buckets = buckets or [0.1, 0.5, 1.0, 5.0, 10.0]
        self.labels = labels or []
        self.observations = []

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value."""
        self.observations.append(value)

    def get_stats(self):
        """Get histogram stats."""
        if not self.observations:
            return {}

        import statistics

        return {
            "count": len(self.observations),
            "sum": sum(self.observations),
            "mean": statistics.mean(self.observations),
            "median": statistics.median(self.observations),
            "min": min(self.observations),
            "max": max(self.observations),
        }


# Standard metrics
query_latency = Histogram(
    "memory_query_latency_ms",
    "Query latency in milliseconds",
    buckets=[10, 50, 100, 250, 500, 1000],
    labels=["layer", "operation"],
)

query_count = Counter("memory_queries_total", "Total queries executed", labels=["layer", "status"])

consolidation_duration = Histogram(
    "consolidation_duration_ms",
    "Consolidation duration in milliseconds",
    buckets=[100, 500, 1000, 5000, 10000],
)

consolidation_count = Counter(
    "consolidation_total", "Total consolidations executed", labels=["status"]
)

memory_count = Gauge(
    "memory_total_count",
    "Total memories stored",
    labels=["project_id", "layer"],
)

cache_hits = Counter("cache_hits_total", "Cache hits", labels=["cache_type"])
cache_misses = Counter("cache_misses_total", "Cache misses", labels=["cache_type"])

errors_total = Counter("errors_total", "Total errors", labels=["error_type"])
