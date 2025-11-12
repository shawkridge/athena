"""Execution telemetry for tracking and analyzing strategy effectiveness.

This module records detailed telemetry about each query execution:
- Which strategy was chosen and why
- Whether the strategy decision was accurate
- Actual vs estimated latency
- Success/failure outcomes
- Query characteristics (features)

This data feeds back into the system to continuously improve strategy
selection, helping the adaptive selector make better decisions over time.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTelemetry:
    """Detailed telemetry of a single query execution."""

    query_id: str
    timestamp: float = field(default_factory=time.time)
    query_type: str = ""
    query_text: str = ""

    # Strategy chosen
    strategy_chosen: str = ""  # "cache", "parallel", "distributed", "sequential"
    strategy_confidence: float = 0.5  # 0.0-1.0

    # Outcomes
    cache_hit: bool = False
    cache_benefit_ms: float = 0.0  # Latency saved by cache
    parallel_speedup: float = 1.0  # Actual speedup vs sequential
    distributed_speedup: float = 1.0  # Actual speedup vs parallel
    total_latency_ms: float = 0.0
    estimated_latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    # Estimation accuracy
    estimated_vs_actual: float = 1.0  # estimated / actual (1.0 = perfect)
    estimation_error_pct: float = 0.0  # |estimated - actual| / actual * 100

    # Query characteristics (for ML training)
    query_features: Dict[str, float] = field(default_factory=dict)
    execution_path: List[str] = field(default_factory=list)  # Strategy attempts
    layers_queried: List[str] = field(default_factory=list)
    result_count: int = 0
    result_size_bytes: int = 0

    def age_seconds(self) -> float:
        """Get age of telemetry record."""
        return time.time() - self.timestamp


class ExecutionTelemetryCollector:
    """Collects and analyzes execution telemetry for continuous optimization.

    Records detailed information about each query execution to enable:
    - Decision accuracy tracking (was our estimate correct?)
    - Strategy effectiveness measurement (which works best for which queries?)
    - Pattern learning (common query characteristics)
    - Performance trending (is system improving over time?)

    Example:
        collector = ExecutionTelemetryCollector()

        # Record telemetry
        collector.record_execution(ExecutionTelemetry(
            query_id="q123",
            query_type="temporal",
            strategy_chosen="parallel",
            strategy_confidence=0.85,
            estimated_latency_ms=150.0,
            total_latency_ms=145.0,
            success=True,
            query_features={"num_layers": 2, "num_results": 5},
        ))

        # Get insights
        insights = collector.get_decision_accuracy()
    """

    def __init__(self, retention_hours: int = 24, max_records: int = 10000):
        """Initialize telemetry collector.

        Args:
            retention_hours: Hours of telemetry to retain
            max_records: Maximum telemetry records before FIFO eviction
        """
        self.retention_hours = retention_hours
        self.max_records = max_records

        # Telemetry storage
        self.records: List[ExecutionTelemetry] = []

        # Aggregate statistics
        self.strategy_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "success_count": 0,
                "avg_latency_ms": 0.0,
                "avg_speedup": 1.0,
                "avg_estimation_error": 0.0,
                "decision_accuracy": 0.0,  # How accurate were predictions?
            }
        )

        self.query_type_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "success_count": 0,
                "avg_cache_hit_rate": 0.0,
                "preferred_strategy": None,
            }
        )

        logger.info(f"ExecutionTelemetryCollector initialized")

    def record_execution(self, telemetry: ExecutionTelemetry) -> None:
        """Record execution telemetry.

        Args:
            telemetry: Telemetry record to store
        """
        # Trim old records if at capacity
        if len(self.records) >= self.max_records:
            self.records = self.records[-(self.max_records - 1) :]

        self.records.append(telemetry)

        # Update statistics
        self._update_strategy_stats(telemetry)
        self._update_query_type_stats(telemetry)

        logger.debug(
            f"Recorded execution: {telemetry.query_id}, "
            f"strategy={telemetry.strategy_chosen}, "
            f"latency={telemetry.total_latency_ms:.1f}ms, "
            f"success={telemetry.success}"
        )

    def _update_strategy_stats(self, telemetry: ExecutionTelemetry) -> None:
        """Update aggregate statistics for strategy."""
        strategy = telemetry.strategy_chosen
        stats = self.strategy_stats[strategy]

        count = stats["count"]
        stats["count"] += 1

        if telemetry.success:
            stats["success_count"] += 1

        # Update running average latency
        stats["avg_latency_ms"] = (
            (stats["avg_latency_ms"] * count) + telemetry.total_latency_ms
        ) / (count + 1)

        # Update running average speedup
        stats["avg_speedup"] = (
            (stats["avg_speedup"] * count) + telemetry.parallel_speedup
        ) / (count + 1)

        # Update running average estimation error
        stats["avg_estimation_error"] = (
            (stats["avg_estimation_error"] * count) + telemetry.estimation_error_pct
        ) / (count + 1)

    def _update_query_type_stats(self, telemetry: ExecutionTelemetry) -> None:
        """Update aggregate statistics for query type."""
        query_type = telemetry.query_type
        stats = self.query_type_stats[query_type]

        count = stats["count"]
        stats["count"] += 1

        if telemetry.success:
            stats["success_count"] += 1

        # Update cache hit rate
        stats["avg_cache_hit_rate"] = (
            (stats["avg_cache_hit_rate"] * count) + (1.0 if telemetry.cache_hit else 0.0)
        ) / (count + 1)

        # Track preferred strategy for this query type
        if not stats["preferred_strategy"]:
            stats["preferred_strategy"] = telemetry.strategy_chosen
        # Could update this based on success rate

    def get_decision_accuracy(self) -> Dict[str, float]:
        """Get accuracy of strategy selection decisions.

        Measures: How close were estimated latencies to actual?

        Returns:
            Dictionary with accuracy metrics
        """
        if not self.records:
            return {"avg_accuracy": 0.0, "accuracy_by_strategy": {}}

        # Calculate accuracy overall
        total_error = 0.0
        strategy_errors: Dict[str, List[float]] = defaultdict(list)

        for record in self.records:
            if record.estimated_vs_actual > 0:
                error = abs(record.estimation_error_pct)
                total_error += error
                strategy_errors[record.strategy_chosen].append(error)

        avg_accuracy = 100.0 - (total_error / max(len(self.records), 1))
        avg_accuracy = max(avg_accuracy, 0.0)

        # Per-strategy accuracy
        accuracy_by_strategy = {}
        for strategy, errors in strategy_errors.items():
            if errors:
                avg_error = sum(errors) / len(errors)
                strategy_accuracy = 100.0 - avg_error
                accuracy_by_strategy[strategy] = max(strategy_accuracy, 0.0)

        return {
            "avg_accuracy": avg_accuracy,
            "accuracy_by_strategy": accuracy_by_strategy,
            "total_executions": len(self.records),
        }

    def get_strategy_effectiveness(self) -> Dict[str, Dict[str, Any]]:
        """Get effectiveness metrics for each strategy.

        Returns:
            Dictionary mapping strategy -> effectiveness metrics
        """
        return dict(self.strategy_stats)

    def get_query_type_insights(self) -> Dict[str, Dict[str, Any]]:
        """Get insights about query types and their optimal strategies.

        Returns:
            Dictionary mapping query_type -> stats
        """
        return dict(self.query_type_stats)

    def get_performance_trend(self, last_n: int = 100) -> Dict[str, Any]:
        """Get recent performance trend.

        Args:
            last_n: Number of recent records to analyze

        Returns:
            Dictionary with trending metrics
        """
        if not self.records:
            return {
                "recent_avg_latency": 0.0,
                "recent_success_rate": 0.0,
                "trend": "unknown",
            }

        recent = self.records[-last_n:]

        avg_latency = sum(r.total_latency_ms for r in recent) / len(recent)
        success_rate = sum(1 for r in recent if r.success) / len(recent)

        # Simple trend detection: compare first half vs second half
        mid = len(recent) // 2
        first_half_latency = (
            sum(r.total_latency_ms for r in recent[:mid]) / mid if mid > 0 else avg_latency
        )
        second_half_latency = (
            sum(r.total_latency_ms for r in recent[mid:]) / (len(recent) - mid)
            if mid < len(recent)
            else avg_latency
        )

        if second_half_latency < first_half_latency * 0.95:
            trend = "improving"
        elif second_half_latency > first_half_latency * 1.05:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "recent_avg_latency_ms": avg_latency,
            "recent_success_rate": success_rate,
            "trend": trend,
            "first_half_latency_ms": first_half_latency,
            "second_half_latency_ms": second_half_latency,
            "records_analyzed": len(recent),
        }

    def get_strategy_recommendations(self) -> Dict[str, str]:
        """Get recommendations for strategy optimization.

        Analyzes telemetry data and provides suggestions.

        Returns:
            Dictionary with recommendations
        """
        recommendations = {}

        # Recommendation 1: Most effective strategy
        if self.strategy_stats:
            best_strategy = max(
                self.strategy_stats.items(),
                key=lambda x: x[1]["success_count"] / max(x[1]["count"], 1),
            )
            recommendations["best_strategy"] = f"{best_strategy[0]} "
            f"(success rate: {best_strategy[1]['success_count']}/{best_strategy[1]['count']})"

        # Recommendation 2: Accuracy assessment
        accuracy = self.get_decision_accuracy()
        if accuracy["avg_accuracy"] < 70:
            recommendations["accuracy"] = (
                "Decision accuracy is low - consider adjusting strategy thresholds"
            )
        elif accuracy["avg_accuracy"] > 85:
            recommendations["accuracy"] = "Decision accuracy is excellent"

        # Recommendation 3: Trend assessment
        trend = self.get_performance_trend()
        if trend["trend"] == "degrading":
            recommendations["trend"] = "Performance is degrading - investigate bottlenecks"
        elif trend["trend"] == "improving":
            recommendations["trend"] = "Performance is improving - continue optimization"

        return recommendations

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external analysis.

        Returns:
            Complete metrics dictionary
        """
        return {
            "strategy_effectiveness": self.get_strategy_effectiveness(),
            "query_type_insights": self.get_query_type_insights(),
            "decision_accuracy": self.get_decision_accuracy(),
            "performance_trend": self.get_performance_trend(),
            "recommendations": self.get_strategy_recommendations(),
            "total_records": len(self.records),
            "collection_window_hours": self.retention_hours,
        }

    def reset(self) -> None:
        """Reset all telemetry (for testing)."""
        self.records.clear()
        self.strategy_stats.clear()
        self.query_type_stats.clear()
        logger.info("ExecutionTelemetryCollector reset")
