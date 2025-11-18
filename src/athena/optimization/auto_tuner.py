"""Adaptive parameter tuning for parallel execution optimization.

This module automatically adjusts execution parameters (concurrency, timeouts,
layer selection) based on workload characteristics and performance metrics,
achieving optimal performance for different query types and workload patterns.

Key features:
- Dynamic concurrency adjustment (2-20 based on workload)
- Per-layer timeout optimization (5-30 seconds)
- Query type-specific tuning profiles
- Multiple optimization strategies (latency, throughput, cost, balanced)
- Automatic fallback and recovery
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

from .performance_profiler import PerformanceProfiler, QueryTypeMetrics

logger = logging.getLogger(__name__)


class TuningStrategy(Enum):
    """Strategy for parameter optimization."""

    LATENCY = "latency"  # Minimize p99 response time
    THROUGHPUT = "throughput"  # Maximize queries/sec
    COST = "cost"  # Minimize resource usage (memory, CPU)
    BALANCED = "balanced"  # 70% latency, 20% throughput, 10% cost


@dataclass
class TuningConfig:
    """Configuration parameters for parallel execution."""

    max_concurrent: int = 5  # Max concurrent tasks (2-20)
    timeout_seconds: float = 10.0  # Per-layer timeout
    layer_selection_enabled: bool = True  # Use smart layer selection
    strategy: TuningStrategy = TuningStrategy.BALANCED
    enable_cache: bool = True
    enable_parallel: bool = True

    def __hash__(self):
        return hash((self.max_concurrent, self.timeout_seconds, self.strategy.value))

    def __eq__(self, other):
        if not isinstance(other, TuningConfig):
            return False
        return (
            self.max_concurrent == other.max_concurrent
            and self.timeout_seconds == other.timeout_seconds
            and self.strategy == other.strategy
        )


@dataclass
class TuningMetrics:
    """Metrics from a tuning adjustment."""

    previous_config: TuningConfig
    new_config: TuningConfig
    improvement: float  # Percentage improvement (0.0-1.0)
    latency_improvement: float
    throughput_improvement: float
    memory_improvement: float
    is_effective: bool  # Whether improvement is statistically significant


class AutoTuner:
    """Automatically optimizes execution parameters for different workloads.

    Monitors query performance, analyzes patterns, and adjusts execution
    parameters to maximize performance according to selected strategy.

    Example:
        profiler = PerformanceProfiler()
        tuner = AutoTuner(
            profiler=profiler,
            strategy=TuningStrategy.LATENCY,
            adjustment_interval=100  # Adjust every 100 queries
        )

        # In main loop
        results = manager.recall(query, use_parallel=True)
        profiler.record_query(metrics)

        # Periodically get updated config
        if query_count % 100 == 0:
            new_config = tuner.get_optimized_config(query_type)
            executor.update_config(new_config)
    """

    # Parameter bounds
    MIN_CONCURRENT = 2
    MAX_CONCURRENT = 20
    MIN_TIMEOUT = 5.0
    MAX_TIMEOUT = 30.0

    # Query type thresholds
    FAST_QUERY_THRESHOLD_MS = 100
    SLOW_QUERY_THRESHOLD_MS = 500

    def __init__(
        self,
        profiler: PerformanceProfiler,
        strategy: TuningStrategy = TuningStrategy.BALANCED,
        adjustment_interval: int = 100,
        min_samples: int = 10,
    ):
        """Initialize auto-tuner.

        Args:
            profiler: PerformanceProfiler instance for metrics
            strategy: Optimization strategy
            adjustment_interval: Recalculate after N queries
            min_samples: Minimum metrics needed before tuning
        """
        self.profiler = profiler
        self.strategy = strategy
        self.adjustment_interval = adjustment_interval
        self.min_samples = min_samples

        # Current configuration
        self.current_config = TuningConfig(strategy=strategy)
        self.query_count_since_adjustment = 0

        # History of adjustments for learning
        self.adjustment_history: Dict[str, list] = {}

    def update_strategy(self, strategy: TuningStrategy) -> None:
        """Update optimization strategy.

        Args:
            strategy: New optimization strategy
        """
        self.strategy = strategy
        self.current_config.strategy = strategy
        logger.info(f"Updated tuning strategy to {strategy.value}")

    def get_optimized_config(self, query_type: Optional[str] = None) -> TuningConfig:
        """Get optimized configuration for current workload.

        Args:
            query_type: Optional query type for type-specific tuning

        Returns:
            Optimized TuningConfig
        """
        self.query_count_since_adjustment += 1

        # Check if it's time to recalculate
        if self.query_count_since_adjustment < self.adjustment_interval:
            return self.current_config

        # Get metrics
        if query_type:
            metrics = self.profiler.get_query_type_metrics(query_type)
        else:
            # Use aggregate metrics across all query types
            metrics = self._get_aggregate_metrics()

        if not metrics or metrics.total_queries < self.min_samples:
            logger.debug(
                f"Insufficient samples for tuning (have {metrics.total_queries if metrics else 0})"
            )
            return self.current_config

        # Calculate optimal config
        new_config = self._calculate_optimal_config(metrics, query_type)

        # Check if improvement is significant
        if self._is_config_change_effective(new_config):
            self.current_config = new_config
            logger.info(
                f"Updated tuning config: "
                f"max_concurrent={new_config.max_concurrent}, "
                f"timeout={new_config.timeout_seconds}s"
            )

        self.query_count_since_adjustment = 0
        return self.current_config

    def _calculate_optimal_config(
        self, metrics: QueryTypeMetrics, query_type: Optional[str] = None
    ) -> TuningConfig:
        """Calculate optimal configuration from metrics.

        Args:
            metrics: QueryTypeMetrics to analyze
            query_type: Query type for logging

        Returns:
            Optimized TuningConfig
        """
        # Determine optimal concurrency
        max_concurrent = self._optimal_concurrency(metrics)

        # Determine optimal timeout
        timeout_seconds = self._optimal_timeout(metrics)

        # Determine whether to use parallel execution
        enable_parallel = metrics.parallel_speedup > 1.2  # >20% speedup justifies parallel

        new_config = TuningConfig(
            max_concurrent=max_concurrent,
            timeout_seconds=timeout_seconds,
            enable_parallel=enable_parallel,
            strategy=self.strategy,
        )

        logger.debug(
            f"Calculated config for {query_type or 'aggregate'}: "
            f"concurrent={max_concurrent}, timeout={timeout_seconds}s, "
            f"parallel={enable_parallel}, speedup={metrics.parallel_speedup:.2f}x"
        )

        return new_config

    def _optimal_concurrency(self, metrics: QueryTypeMetrics) -> int:
        """Calculate optimal concurrency level.

        Logic:
        - Fast queries (p99 < 100ms): Can use higher concurrency (10-20)
        - Medium queries (100-500ms): Medium concurrency (5-10)
        - Slow queries (p99 > 500ms): Lower concurrency (2-5)
        - Adjust based on parallelization effectiveness
        """
        p99_latency = metrics.p99_latency_ms

        if p99_latency < self.FAST_QUERY_THRESHOLD_MS:
            # Fast queries - maximize concurrency
            base_concurrency = 15
        elif p99_latency < self.SLOW_QUERY_THRESHOLD_MS:
            # Medium queries - balance
            base_concurrency = 8
        else:
            # Slow queries - lower concurrency
            base_concurrency = 4

        # Adjust based on parallel speedup
        if metrics.parallel_speedup > 2.0:
            # High parallelization benefit - can go higher
            adjustment = 1.2
        elif metrics.parallel_speedup < 1.1:
            # Low parallelization benefit - reduce
            adjustment = 0.7
        else:
            adjustment = 1.0

        optimal = int(base_concurrency * adjustment)

        # Clamp to bounds
        return max(self.MIN_CONCURRENT, min(optimal, self.MAX_CONCURRENT))

    def _optimal_timeout(self, metrics: QueryTypeMetrics) -> float:
        """Calculate optimal timeout per layer.

        Logic:
        - Base timeout: p99 latency * 1.5 (add margin for outliers)
        - Adjust by strategy:
          - Latency: More aggressive (p99 * 1.2)
          - Throughput: More lenient (p99 * 2.0)
          - Cost: Balanced (p99 * 1.5)
        """
        p99_latency = metrics.p99_latency_ms

        if self.strategy == TuningStrategy.LATENCY:
            # Aggressive - fail fast
            multiplier = 1.2
        elif self.strategy == TuningStrategy.THROUGHPUT:
            # Lenient - allow slow queries
            multiplier = 2.0
        elif self.strategy == TuningStrategy.COST:
            # Balanced
            multiplier = 1.5
        else:  # BALANCED
            # Default balanced
            multiplier = 1.5

        timeout = (p99_latency / 1000.0) * multiplier  # Convert ms to seconds

        # Clamp to bounds
        return max(self.MIN_TIMEOUT, min(timeout, self.MAX_TIMEOUT))

    def _is_config_change_effective(self, new_config: TuningConfig) -> bool:
        """Check if new config is significantly different from current.

        Args:
            new_config: Proposed new configuration

        Returns:
            True if change is large enough to apply
        """
        if new_config == self.current_config:
            return False

        # Check concurrency change
        concurrency_diff = abs(new_config.max_concurrent - self.current_config.max_concurrent)
        concurrency_pct = concurrency_diff / self.current_config.max_concurrent

        # Check timeout change
        timeout_diff = abs(new_config.timeout_seconds - self.current_config.timeout_seconds)
        timeout_pct = timeout_diff / self.current_config.timeout_seconds

        # Apply if either change is > 10%
        return concurrency_pct > 0.1 or timeout_pct > 0.1

    def _get_aggregate_metrics(self) -> Optional[QueryTypeMetrics]:
        """Get aggregate metrics across all query types.

        Returns:
            Synthetic QueryTypeMetrics or None if no data
        """
        all_types = list(self.profiler.query_type_metrics.values())

        if not all_types:
            return None

        # Calculate weighted averages
        total_queries = sum(m.total_queries for m in all_types)
        if total_queries == 0:
            return None

        weighted_latency = (
            sum(m.avg_latency_ms * m.total_queries for m in all_types) / total_queries
        )
        weighted_p99 = sum(m.p99_latency_ms * m.total_queries for m in all_types) / total_queries
        weighted_speedup = (
            sum(m.parallel_speedup * m.total_queries for m in all_types) / total_queries
        )
        weighted_success = sum(m.success_rate * m.total_queries for m in all_types) / total_queries

        return QueryTypeMetrics(
            query_type="__aggregate__",
            total_queries=total_queries,
            avg_latency_ms=weighted_latency,
            p99_latency_ms=weighted_p99,
            parallel_speedup=weighted_speedup,
            success_rate=weighted_success,
        )

    def get_tuning_report(self) -> Dict[str, any]:
        """Get comprehensive tuning report for diagnostics.

        Returns:
            Dict with current config, recommendations, and metrics
        """
        aggregate = self._get_aggregate_metrics()

        report = {
            "strategy": self.strategy.value,
            "current_config": {
                "max_concurrent": self.current_config.max_concurrent,
                "timeout_seconds": self.current_config.timeout_seconds,
                "enable_parallel": self.current_config.enable_parallel,
            },
            "metrics": {
                "total_queries": aggregate.total_queries if aggregate else 0,
                "avg_latency_ms": aggregate.avg_latency_ms if aggregate else 0,
                "p99_latency_ms": aggregate.p99_latency_ms if aggregate else 0,
                "parallel_speedup": aggregate.parallel_speedup if aggregate else 1.0,
                "success_rate": aggregate.success_rate if aggregate else 0,
            },
        }

        return report
