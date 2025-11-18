"""Feedback metrics to measure verification improvements over time.

Tracks how verification decisions improve the quality of memory operations
through continuous measurement and learning from outcomes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import math


@dataclass
class MetricSnapshot:
    """A single point-in-time metric measurement."""

    timestamp: datetime
    value: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricTrend:
    """Trend analysis for a metric."""

    metric_name: str
    snapshots: List[MetricSnapshot] = field(default_factory=list)
    mean: float = 0.0
    std_dev: float = 0.0
    trend: str = "flat"  # "improving", "degrading", "flat"
    trend_magnitude: float = 0.0  # How fast is it changing?


class FeedbackMetricsCollector:
    """Collect and analyze feedback metrics for verification system."""

    def __init__(self, window_hours: int = 24):
        """Initialize collector."""
        self.window_hours = window_hours
        self.metrics: Dict[str, List[MetricSnapshot]] = defaultdict(list)
        self.aggregates: Dict[str, Any] = {}

    def record_metric(
        self, metric_name: str, value: float, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a metric value.

        Args:
            metric_name: Name of metric (e.g., "gate_pass_rate", "decision_accuracy")
            value: Metric value (0.0-1.0 for rates)
            context: Additional context about measurement
        """
        snapshot = MetricSnapshot(timestamp=datetime.now(), value=value, context=context or {})

        self.metrics[metric_name].append(snapshot)

    def get_metric_trend(self, metric_name: str) -> MetricTrend:
        """Calculate trend for a metric."""
        snapshots = [
            s
            for s in self.metrics.get(metric_name, [])
            if (datetime.now() - s.timestamp) < timedelta(hours=self.window_hours)
        ]

        if not snapshots:
            return MetricTrend(metric_name=metric_name)

        # Calculate statistics
        values = [s.value for s in snapshots]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        # Calculate trend direction
        trend = "flat"
        trend_magnitude = 0.0

        if len(snapshots) >= 2:
            first_half = values[: len(values) // 2]
            second_half = values[len(values) // 2 :]

            first_mean = sum(first_half) / len(first_half)
            second_mean = sum(second_half) / len(second_half)

            if second_mean > first_mean + std_dev:
                trend = "improving"
                trend_magnitude = (second_mean - first_mean) / first_mean if first_mean > 0 else 0
            elif second_mean < first_mean - std_dev:
                trend = "degrading"
                trend_magnitude = (first_mean - second_mean) / first_mean if first_mean > 0 else 0

        return MetricTrend(
            metric_name=metric_name,
            snapshots=snapshots,
            mean=mean,
            std_dev=std_dev,
            trend=trend,
            trend_magnitude=trend_magnitude,
        )

    def get_improvement_rate(self, metric_name: str) -> float:
        """Get rate of improvement for a metric (0.0 = no improvement, 1.0 = rapid improvement)."""
        trend = self.get_metric_trend(metric_name)
        return trend.trend_magnitude if trend.trend == "improving" else 0.0

    def get_regression_risk(self, metric_name: str) -> float:
        """Get risk of regression for a metric (0.0 = safe, 1.0 = high risk)."""
        trend = self.get_metric_trend(metric_name)

        risk = 0.0

        # High degradation = high risk
        if trend.trend == "degrading":
            risk = trend.trend_magnitude

        # High variance = instability risk
        if trend.mean > 0:
            risk += min(0.3, trend.std_dev / trend.mean)

        return min(1.0, risk)

    def calculate_composite_score(
        self, metric_names: List[str], weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate composite score from multiple metrics."""
        if not metric_names:
            return 0.0

        weights = weights or {name: 1.0 / len(metric_names) for name in metric_names}

        score = 0.0
        for metric_name in metric_names:
            trend = self.get_metric_trend(metric_name)
            metric_score = trend.mean
            weight = weights.get(metric_name, 0.0)
            score += metric_score * weight

        return score

    def get_quality_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all quality metrics."""
        return {
            "decision_accuracy": self._get_decision_accuracy(),
            "gate_pass_rate": self._get_gate_pass_rate(),
            "remediation_effectiveness": self._get_remediation_effectiveness(),
            "operational_efficiency": self._get_operational_efficiency(),
            "violation_reduction": self._get_violation_reduction(),
        }

    def _get_decision_accuracy(self) -> Dict[str, Any]:
        """Get decision accuracy metrics."""
        trend = self.get_metric_trend("decision_accuracy")
        return {
            "current": trend.mean,
            "trend": trend.trend,
            "improvement_rate": trend.trend_magnitude,
        }

    def _get_gate_pass_rate(self) -> Dict[str, Any]:
        """Get gate pass rate metrics."""
        trend = self.get_metric_trend("gate_pass_rate")
        return {
            "current": trend.mean,
            "trend": trend.trend,
            "regression_risk": self.get_regression_risk("gate_pass_rate"),
        }

    def _get_remediation_effectiveness(self) -> Dict[str, Any]:
        """Get remediation effectiveness metrics."""
        trend = self.get_metric_trend("remediation_effectiveness")
        return {
            "current": trend.mean,
            "trend": trend.trend,
        }

    def _get_operational_efficiency(self) -> Dict[str, Any]:
        """Get operational efficiency metrics."""
        latency = self.get_metric_trend("operation_latency_ms")
        throughput = self.get_metric_trend("operations_per_second")

        return {
            "latency_ms": latency.mean,
            "throughput": throughput.mean,
            "latency_trend": latency.trend,
            "throughput_trend": throughput.trend,
        }

    def _get_violation_reduction(self) -> Dict[str, Any]:
        """Get violation reduction metrics."""
        trend = self.get_metric_trend("violation_count")
        return {
            "current": trend.mean,
            "trend": trend.trend,
            "reduction_rate": self.get_improvement_rate("violation_count"),
        }

    def get_anomalies(self, sigma_threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalous metric values."""
        anomalies = []

        for metric_name, snapshots in self.metrics.items():
            recent = [s for s in snapshots if (datetime.now() - s.timestamp) < timedelta(hours=1)]

            if len(recent) < 3:
                continue

            trend = self.get_metric_trend(metric_name)
            values = [s.value for s in recent]

            for value, snapshot in zip(values, recent):
                z_score = abs((value - trend.mean) / trend.std_dev) if trend.std_dev > 0 else 0

                if z_score > sigma_threshold:
                    anomalies.append(
                        {
                            "metric_name": metric_name,
                            "value": value,
                            "expected": trend.mean,
                            "z_score": z_score,
                            "timestamp": snapshot.timestamp.isoformat(),
                        }
                    )

        return anomalies

    def get_metric_alerts(self) -> List[str]:
        """Generate alerts for metric anomalies and regressions."""
        alerts = []

        # Check for regressions
        for metric_name in ["gate_pass_rate", "decision_accuracy", "remediation_effectiveness"]:
            regression_risk = self.get_regression_risk(metric_name)
            if regression_risk > 0.5:
                alerts.append(f"⚠️ High regression risk for {metric_name}: {regression_risk:.0%}")

        # Check for anomalies
        anomalies = self.get_anomalies(sigma_threshold=2.0)
        if anomalies:
            alerts.append(f"🚨 Detected {len(anomalies)} metric anomalies in last hour")

        # Check performance degradation
        latency_trend = self.get_metric_trend("operation_latency_ms")
        if latency_trend.trend == "degrading":
            alerts.append(f"⏱️ Operation latency degrading: {latency_trend.trend_magnitude:.0%}")

        return alerts

    def export_metrics_report(self) -> Dict[str, Any]:
        """Export comprehensive metrics report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_quality_metrics_summary(),
            "trends": {
                metric_name: {
                    "mean": self.get_metric_trend(metric_name).mean,
                    "std_dev": self.get_metric_trend(metric_name).std_dev,
                    "trend": self.get_metric_trend(metric_name).trend,
                }
                for metric_name in self.metrics.keys()
            },
            "anomalies": self.get_anomalies(),
            "alerts": self.get_metric_alerts(),
        }

    def calculate_system_health_score(self) -> float:
        """Calculate overall system health score (0.0-1.0)."""
        key_metrics = [
            "gate_pass_rate",
            "decision_accuracy",
            "remediation_effectiveness",
        ]

        weights = {
            "gate_pass_rate": 0.4,
            "decision_accuracy": 0.4,
            "remediation_effectiveness": 0.2,
        }

        # Score is composite of key metrics
        score = self.calculate_composite_score(key_metrics, weights)

        # Reduce score for regressions
        for metric in key_metrics:
            regression_risk = self.get_regression_risk(metric)
            score *= 1.0 - regression_risk * 0.1

        # Reduce score for anomalies
        anomaly_count = len(self.get_anomalies())
        score *= max(0.5, 1.0 - anomaly_count * 0.05)

        return max(0.0, min(1.0, score))

    def get_recommendations(self) -> List[str]:
        """Get recommendations based on metrics."""
        recommendations = []

        # Check improvement opportunities
        decision_accuracy = self.get_metric_trend("decision_accuracy")
        if decision_accuracy.mean < 0.8:
            recommendations.append("Increase training data size to improve decision accuracy")

        gate_pass_rate = self.get_metric_trend("gate_pass_rate")
        if gate_pass_rate.std_dev > 0.2:
            recommendations.append("Gate thresholds are unstable; consider gradual tuning")

        # Performance recommendations
        latency = self.get_metric_trend("operation_latency_ms")
        if latency.mean > 1000:
            recommendations.append("Operations taking >1s; consider caching or async processing")

        # Remediation recommendations
        remediation = self.get_metric_trend("remediation_effectiveness")
        if remediation.mean < 0.7:
            recommendations.append("Remediation effectiveness low; improve violation handlers")

        return recommendations if recommendations else ["All systems operating normally"]
