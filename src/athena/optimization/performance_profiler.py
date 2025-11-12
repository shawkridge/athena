"""Performance profiler for query execution tracking and analysis.

This module tracks detailed performance metrics for queries, enabling the
auto-tuner to make intelligent optimization decisions based on real workload
characteristics.

Key features:
- Per-query-type performance tracking (latency, memory, accuracy)
- Temporal pattern detection (time-of-day effects, session patterns)
- Layer-specific performance analysis
- Aggregate statistics and trend analysis
- Configurable metrics retention and windowing
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""

    query_id: str
    query_text: str
    query_type: str  # "temporal", "factual", "relational", "procedural", etc.
    timestamp: float  # Unix timestamp
    latency_ms: float  # Total execution time
    memory_mb: float  # Peak memory usage
    cache_hit: bool  # Did it hit the cache?
    result_count: int  # Number of results returned
    layers_queried: List[str]  # Which layers were accessed
    layer_latencies: Dict[str, float]  # Per-layer execution time
    success: bool  # Did the query succeed?
    error: Optional[str] = None
    parallel_execution: bool = False
    concurrency_level: int = 1
    accuracy_score: float = 1.0  # Self-assessed accuracy (0.0-1.0)
    user_satisfaction: Optional[float] = None  # 0-1, set if user provided feedback


@dataclass
class LayerMetrics:
    """Aggregate metrics for a single layer."""

    layer_name: str
    total_queries: int = 0
    successful_queries: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_memory_mb: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0


@dataclass
class QueryTypeMetrics:
    """Aggregate metrics for a query type."""

    query_type: str
    total_queries: int = 0
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    parallel_speedup: float = 1.0  # Parallel latency / Sequential latency
    cache_hit_rate: float = 0.0
    success_rate: float = 0.0
    avg_accuracy: float = 0.8


class PerformanceProfiler:
    """Tracks and analyzes query performance metrics for optimization.

    Records detailed metrics per query and provides aggregate statistics
    organized by query type, layer, and temporal patterns.

    Example:
        profiler = PerformanceProfiler(window_hours=24, max_metrics=10000)

        # Record a query
        profiler.record_query(QueryMetrics(
            query_id="q123",
            query_text="What was the failing test?",
            query_type="temporal",
            timestamp=time.time(),
            latency_ms=42.5,
            memory_mb=12.3,
            cache_hit=True,
            result_count=3,
            layers_queried=["episodic", "semantic"],
            layer_latencies={"episodic": 10.2, "semantic": 32.3},
            success=True,
            parallel_execution=True
        ))

        # Get statistics
        stats = profiler.get_layer_metrics("semantic")
        trend = profiler.get_trending_queries()
    """

    def __init__(
        self,
        window_hours: int = 24,
        max_metrics: int = 10000,
        temporal_bins: int = 24,
    ):
        """Initialize performance profiler.

        Args:
            window_hours: Keep metrics for last N hours (default 24)
            max_metrics: Maximum metrics to retain (LRU eviction after)
            temporal_bins: Number of time-of-day bins for pattern detection
        """
        self.window_hours = window_hours
        self.max_metrics = max_metrics
        self.temporal_bins = temporal_bins

        # Storage
        self.metrics: List[QueryMetrics] = []  # All recorded metrics (windowed)
        self.layer_metrics: Dict[str, LayerMetrics] = {}  # Per-layer aggregate
        self.query_type_metrics: Dict[str, QueryTypeMetrics] = {}  # Per-type aggregate
        self.temporal_distribution: Dict[int, List[QueryMetrics]] = defaultdict(
            list
        )  # By hour of day

        # Statistics cache (invalidated on new metrics)
        self._cache_valid = False
        self._cached_stats = {}

    def record_query(self, metrics: QueryMetrics) -> None:
        """Record metrics for a query execution.

        Args:
            metrics: QueryMetrics instance with execution details
        """
        # Add timestamp if not set
        if metrics.timestamp == 0:
            metrics.timestamp = time.time()

        # Add to metrics list
        self.metrics.append(metrics)

        # Enforce max_metrics limit (simple FIFO for now)
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics :]

        # Invalidate cache
        self._cache_valid = False

        # Update temporal distribution
        hour_bin = int(datetime.fromtimestamp(metrics.timestamp).hour)
        self.temporal_distribution[hour_bin].append(metrics)

        # Log for debugging
        logger.debug(
            f"Recorded query {metrics.query_id}: {metrics.query_type} "
            f"({metrics.latency_ms:.1f}ms, {metrics.result_count} results)"
        )

    def get_layer_metrics(self, layer_name: str) -> Optional[LayerMetrics]:
        """Get aggregate metrics for a specific layer.

        Args:
            layer_name: Name of the layer (e.g., "episodic", "semantic")

        Returns:
            LayerMetrics or None if no data for layer
        """
        # Compute if cache invalid
        if not self._cache_valid:
            self._compute_metrics()

        return self.layer_metrics.get(layer_name)

    def get_query_type_metrics(self, query_type: str) -> Optional[QueryTypeMetrics]:
        """Get aggregate metrics for a query type.

        Args:
            query_type: Query type (e.g., "temporal", "factual")

        Returns:
            QueryTypeMetrics or None if no data for type
        """
        if not self._cache_valid:
            self._compute_metrics()

        return self.query_type_metrics.get(query_type)

    def get_trending_queries(self, hours: int = 1, limit: int = 10) -> List[str]:
        """Get trending queries (by frequency and recency).

        Args:
            hours: Look at queries from last N hours
            limit: Max queries to return

        Returns:
            List of query texts sorted by trend score
        """
        cutoff_time = time.time() - (hours * 3600)
        recent = [m for m in self.metrics if m.timestamp > cutoff_time]

        # Count occurrences
        query_counts: Dict[str, int] = defaultdict(int)
        for metric in recent:
            query_counts[metric.query_text] += 1

        # Sort by count (descending)
        trending = sorted(
            query_counts.items(), key=lambda x: x[1], reverse=True
        )[:limit]
        return [q for q, _ in trending]

    def get_slow_queries(self, percentile: int = 99, limit: int = 10) -> List[Tuple[str, float]]:
        """Get slowest queries (by percentile).

        Args:
            percentile: Which percentile to consider slow (e.g., 99)
            limit: Max queries to return

        Returns:
            List of (query_text, latency_ms) tuples
        """
        if not self.metrics:
            return []

        # Calculate threshold
        latencies = sorted([m.latency_ms for m in self.metrics])
        idx = int(len(latencies) * percentile / 100)
        threshold = latencies[min(idx, len(latencies) - 1)]

        # Get slow queries
        slow = [(m.query_text, m.latency_ms) for m in self.metrics if m.latency_ms >= threshold]
        slow.sort(key=lambda x: x[1], reverse=True)

        return slow[:limit]

    def get_temporal_pattern(self) -> Dict[int, Dict[str, float]]:
        """Get temporal pattern of query performance by hour of day.

        Returns:
            Dict mapping hour (0-23) to metrics dict with avg_latency_ms, qps, etc.
        """
        pattern = {}

        for hour in range(24):
            metrics_in_hour = self.temporal_distribution.get(hour, [])

            if not metrics_in_hour:
                pattern[hour] = {
                    "avg_latency_ms": 0,
                    "query_count": 0,
                    "success_rate": 0,
                }
            else:
                pattern[hour] = {
                    "avg_latency_ms": sum(m.latency_ms for m in metrics_in_hour) / len(metrics_in_hour),
                    "query_count": len(metrics_in_hour),
                    "success_rate": sum(1 for m in metrics_in_hour if m.success) / len(metrics_in_hour),
                }

        return pattern

    def get_layer_dependency_analysis(self) -> Dict[str, Dict[str, float]]:
        """Analyze which layers appear together in queries.

        Returns:
            Dict mapping from_layer -> to_layer -> co-occurrence_rate
        """
        co_occurrences: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        layer_totals: Dict[str, int] = defaultdict(int)

        for metric in self.metrics:
            for layer in metric.layers_queried:
                layer_totals[layer] += 1
                for other_layer in metric.layers_queried:
                    if layer != other_layer:
                        co_occurrences[layer][other_layer] += 1

        # Convert to rates
        result = {}
        for from_layer, others in co_occurrences.items():
            result[from_layer] = {}
            total = layer_totals.get(from_layer, 1)
            for to_layer, count in others.items():
                result[from_layer][to_layer] = count / total

        return result

    def get_cache_effectiveness(self) -> Dict[str, float]:
        """Analyze cache hit rates by layer and query type.

        Returns:
            Dict with cache_overall, cache_by_layer, cache_by_type
        """
        if not self.metrics:
            return {"overall": 0.0}

        cache_hits = sum(1 for m in self.metrics if m.cache_hit)
        overall_rate = cache_hits / len(self.metrics)

        by_layer = {}
        for layer_name in set(l for m in self.metrics for l in m.layers_queried):
            metrics_with_layer = [m for m in self.metrics if layer_name in m.layers_queried]
            if metrics_with_layer:
                hits = sum(1 for m in metrics_with_layer if m.cache_hit)
                by_layer[layer_name] = hits / len(metrics_with_layer)

        by_type = {}
        for query_type in set(m.query_type for m in self.metrics):
            metrics_of_type = [m for m in self.metrics if m.query_type == query_type]
            if metrics_of_type:
                hits = sum(1 for m in metrics_of_type if m.cache_hit)
                by_type[query_type] = hits / len(metrics_of_type)

        return {
            "overall": overall_rate,
            "by_layer": by_layer,
            "by_type": by_type,
        }

    def get_concurrency_effectiveness(self) -> Dict[str, float]:
        """Analyze effectiveness of parallel execution.

        Returns:
            Dict with parallel_usage, avg_speedup, successful_parallelizations
        """
        if not self.metrics:
            return {"parallel_usage": 0.0}

        parallel_metrics = [m for m in self.metrics if m.parallel_execution]

        if not parallel_metrics:
            return {
                "parallel_usage": 0.0,
                "avg_speedup": 1.0,
                "successful": 0,
            }

        # Calculate speedup (rough estimate: sum of layer latencies / total latency)
        speedups = []
        for metric in parallel_metrics:
            if metric.layer_latencies:
                sum_layer_latencies = sum(metric.layer_latencies.values())
                if metric.latency_ms > 0:
                    speedup = sum_layer_latencies / metric.latency_ms
                    speedups.append(speedup)

        avg_speedup = sum(speedups) / len(speedups) if speedups else 1.0

        return {
            "parallel_usage": len(parallel_metrics) / len(self.metrics),
            "avg_speedup": avg_speedup,
            "successful": len(parallel_metrics),
        }

    def _compute_metrics(self) -> None:
        """Recompute all aggregate metrics from raw data."""
        self.layer_metrics.clear()
        self.query_type_metrics.clear()

        # Prune old metrics (outside window)
        cutoff_time = time.time() - (self.window_hours * 3600)
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]

        if not self.metrics:
            self._cache_valid = True
            return

        # Compute per-layer metrics
        layers: Dict[str, List[QueryMetrics]] = defaultdict(list)
        for metric in self.metrics:
            for layer in metric.layers_queried:
                layers[layer].append(metric)

        for layer_name, metrics in layers.items():
            latencies = [m.latency_ms for m in metrics]
            latencies_sorted = sorted(latencies)

            success_count = sum(1 for m in metrics if m.success)
            cache_hits = sum(1 for m in metrics if m.cache_hit)

            self.layer_metrics[layer_name] = LayerMetrics(
                layer_name=layer_name,
                total_queries=len(metrics),
                successful_queries=success_count,
                avg_latency_ms=sum(latencies) / len(latencies),
                p50_latency_ms=latencies_sorted[len(latencies_sorted) // 2],
                p99_latency_ms=latencies_sorted[int(len(latencies_sorted) * 0.99)],
                avg_memory_mb=sum(m.memory_mb for m in metrics) / len(metrics),
                error_rate=1 - (success_count / len(metrics)),
                cache_hit_rate=cache_hits / len(metrics) if metrics else 0,
            )

        # Compute per-query-type metrics
        query_types: Dict[str, List[QueryMetrics]] = defaultdict(list)
        for metric in self.metrics:
            query_types[metric.query_type].append(metric)

        for query_type, metrics in query_types.items():
            latencies = sorted([m.latency_ms for m in metrics])
            parallel_metrics = [m for m in metrics if m.parallel_execution]
            success_count = sum(1 for m in metrics if m.success)
            cache_hits = sum(1 for m in metrics if m.cache_hit)

            # Calculate parallel speedup
            parallel_speedup = 1.0
            if parallel_metrics:
                speedups = []
                for m in parallel_metrics:
                    if m.layer_latencies:
                        sum_layer = sum(m.layer_latencies.values())
                        if m.latency_ms > 0:
                            speedups.append(sum_layer / m.latency_ms)
                if speedups:
                    parallel_speedup = sum(speedups) / len(speedups)

            self.query_type_metrics[query_type] = QueryTypeMetrics(
                query_type=query_type,
                total_queries=len(metrics),
                avg_latency_ms=sum(m.latency_ms for m in metrics) / len(metrics),
                p99_latency_ms=latencies[int(len(latencies) * 0.99)] if latencies else 0,
                parallel_speedup=parallel_speedup,
                cache_hit_rate=cache_hits / len(metrics) if metrics else 0,
                success_rate=success_count / len(metrics),
                avg_accuracy=sum(m.accuracy_score for m in metrics) / len(metrics),
            )

        self._cache_valid = True
