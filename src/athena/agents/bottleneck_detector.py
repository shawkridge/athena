"""
Bottleneck detection and resource constraint analysis for Predictor Agent.

Identifies:
- Resource saturation points
- Critical path bottlenecks
- Mitigation strategies
- Constraint escalation
"""

import math
import logging
from typing import Optional
from datetime import datetime
from collections import defaultdict

from .predictor_models import (
    BottleneckAlert,
    ResourceType,
    RiskLevel,
    ResourceForecast,
    ConfidenceInterval,
)

logger = logging.getLogger(__name__)


class BottleneckDetector:
    """Detects and predicts resource bottlenecks."""

    def __init__(
        self,
        saturation_threshold: float = 0.85,
        critical_threshold: float = 0.95,
        alert_horizon_hours: float = 4.0,
    ):
        """Initialize bottleneck detector.

        Args:
            saturation_threshold: Utilization % at which to warn (0-1)
            critical_threshold: Utilization % at which to alert critical (0-1)
            alert_horizon_hours: How far ahead to predict bottlenecks
        """
        self.saturation_threshold = saturation_threshold
        self.critical_threshold = critical_threshold
        self.alert_horizon_hours = alert_horizon_hours

        # Resource metrics tracking
        self.resource_metrics: dict[ResourceType, list[float]] = defaultdict(list)
        self.resource_capacity: dict[ResourceType, float] = {
            ResourceType.CPU: 100.0,  # %
            ResourceType.MEMORY: 100.0,  # %
            ResourceType.IO: 100.0,  # %
            ResourceType.NETWORK: 100.0,  # Mbps (relative)
            ResourceType.DISK: 100.0,  # %
        }

        self.active_alerts: dict[ResourceType, BottleneckAlert] = {}
        self.historical_alerts: list[BottleneckAlert] = []

    def update_resource_usage(
        self, resource_type: ResourceType, utilization_percent: float, timestamp: Optional[datetime] = None
    ):
        """Update resource usage metric.

        Args:
            resource_type: Type of resource
            utilization_percent: Current utilization (0-100)
            timestamp: Optional timestamp
        """
        # Store as 0-1 internally
        normalized = max(0.0, min(100.0, utilization_percent)) / 100.0
        self.resource_metrics[resource_type].append(normalized)

        # Keep last 500 observations
        if len(self.resource_metrics[resource_type]) > 500:
            self.resource_metrics[resource_type].pop(0)

    def detect_bottlenecks(self) -> list[BottleneckAlert]:
        """Detect current and predicted bottlenecks.

        Returns:
            List of bottleneck alerts
        """
        alerts = []

        for resource_type in ResourceType:
            if resource_type not in self.resource_metrics:
                continue

            metrics = self.resource_metrics[resource_type]
            if not metrics:
                continue

            current_usage = metrics[-1]
            current_percent = current_usage * 100.0

            # Check current saturation
            if current_percent >= self.critical_threshold * 100.0:
                severity = RiskLevel.CRITICAL
            elif current_percent >= self.saturation_threshold * 100.0:
                severity = RiskLevel.HIGH
            else:
                severity = None

            # Predict future saturation
            if len(metrics) >= 3:
                trend = self._calculate_trend(metrics[-10:])
                time_to_saturation = self._predict_saturation_time(
                    current_usage, trend, self.saturation_threshold
                )

                if 0 < time_to_saturation <= self.alert_horizon_hours:
                    if severity is None:
                        severity = RiskLevel.MEDIUM

            # Generate alert if needed
            if severity:
                alert = self._create_bottleneck_alert(
                    resource_type, current_percent, severity, metrics
                )
                alerts.append(alert)
                self.active_alerts[resource_type] = alert
            else:
                # Clear alert if resource is now healthy
                self.active_alerts.pop(resource_type, None)

        self.historical_alerts.extend(alerts)
        return alerts

    def get_resource_forecast(
        self, resource_type: ResourceType, steps_ahead: int = 10
    ) -> ResourceForecast:
        """Get forecast for a resource.

        Args:
            resource_type: Type of resource to forecast
            steps_ahead: Number of steps to forecast

        Returns:
            ResourceForecast with predictions and confidence intervals
        """
        if resource_type not in self.resource_metrics:
            return self._create_empty_forecast(resource_type)

        metrics = self.resource_metrics[resource_type]
        if not metrics:
            return self._create_empty_forecast(resource_type)

        current_usage = metrics[-1]
        current_percent = current_usage * 100.0

        # Estimate trend and forecast
        if len(metrics) >= 3:
            trend = self._calculate_trend(metrics[-10:])
        else:
            trend = 0.0

        forecasts = []
        for i in range(steps_ahead):
            pred = current_usage + trend * (i + 1)
            forecasts.append(max(0.0, min(1.0, pred)))

        avg_forecast = sum(forecasts) / len(forecasts) * 100.0
        std_dev = self._calculate_std_dev(metrics[-10:]) * 100.0

        # Create confidence intervals
        peak_forecast = max(forecasts) * 100.0
        avg_forecast = sum(forecasts) / len(forecasts) * 100.0

        # Predict time to peak
        time_to_peak = self._predict_peak_time(metrics[-10:])

        # Determine if constrained
        is_constrained = (
            peak_forecast >= self.saturation_threshold * 100.0 or
            current_percent >= self.saturation_threshold * 100.0
        )

        return ResourceForecast(
            resource_type=resource_type,
            current_usage=current_percent,
            forecasted_peak=ConfidenceInterval(
                lower_bound=max(0.0, peak_forecast - std_dev),
                point_estimate=peak_forecast,
                upper_bound=peak_forecast + std_dev,
                confidence_level=0.9,
            ),
            forecasted_average=ConfidenceInterval(
                lower_bound=max(0.0, avg_forecast - std_dev),
                point_estimate=avg_forecast,
                upper_bound=avg_forecast + std_dev,
                confidence_level=0.9,
            ),
            time_to_peak_hours=time_to_peak,
            is_constrained=is_constrained,
            utilization_percent=current_percent,
        )

    def get_mitigation_options(self, resource_type: ResourceType) -> list[str]:
        """Get mitigation options for a resource constraint.

        Args:
            resource_type: Type of resource to mitigate

        Returns:
            List of mitigation strategies
        """
        options = {
            ResourceType.CPU: [
                "Reduce task parallelism",
                "Lower quality settings for batch operations",
                "Defer non-critical background tasks",
                "Use more efficient algorithms",
                "Enable CPU throttling",
            ],
            ResourceType.MEMORY: [
                "Reduce in-memory cache sizes",
                "Process data in smaller batches",
                "Use pagination instead of loading all data",
                "Enable swap or overflow to disk",
                "Reduce number of concurrent operations",
            ],
            ResourceType.IO: [
                "Increase I/O buffer sizes",
                "Batch database operations",
                "Use async I/O patterns",
                "Defer non-critical writes",
                "Implement read caching",
            ],
            ResourceType.NETWORK: [
                "Compress data transfers",
                "Reduce request parallelism",
                "Implement request batching",
                "Queue requests with backoff",
                "Use local caching",
            ],
            ResourceType.DISK: [
                "Implement data rotation/archiving",
                "Increase disk capacity",
                "Compress stored data",
                "Implement cleanup policies",
                "Use external storage",
            ],
        }
        return options.get(resource_type, [])

    def _create_bottleneck_alert(
        self,
        resource_type: ResourceType,
        current_percent: float,
        severity: RiskLevel,
        metrics: list[float],
    ) -> BottleneckAlert:
        """Create a bottleneck alert."""
        if len(metrics) >= 3:
            trend = self._calculate_trend(metrics[-10:])
            time_to_saturation = self._predict_saturation_time(
                metrics[-1], trend, self.saturation_threshold
            )
        else:
            time_to_saturation = self.alert_horizon_hours

        peak_percent = max(m * 100.0 for m in metrics[-10:]) if metrics else current_percent

        return BottleneckAlert(
            resource_type=resource_type,
            severity=severity,
            predicted_saturation_time=max(0.0, time_to_saturation),
            current_utilization=current_percent,
            peak_predicted_utilization=peak_percent,
            mitigation_options=self.get_mitigation_options(resource_type),
            confidence=self._calculate_prediction_confidence(metrics),
        )

    def _create_empty_forecast(self, resource_type: ResourceType) -> ResourceForecast:
        """Create empty forecast for unknown resource."""
        return ResourceForecast(
            resource_type=resource_type,
            current_usage=0.0,
            forecasted_peak=ConfidenceInterval(
                lower_bound=0.0, point_estimate=0.0, upper_bound=0.0
            ),
            forecasted_average=ConfidenceInterval(
                lower_bound=0.0, point_estimate=0.0, upper_bound=0.0
            ),
            time_to_peak_hours=0.0,
            is_constrained=False,
            utilization_percent=0.0,
        )

    @staticmethod
    def _calculate_trend(metrics: list[float]) -> float:
        """Calculate trend in metrics (linear regression slope)."""
        if len(metrics) < 2:
            return 0.0

        n = len(metrics)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(metrics) / n

        numerator = sum((x[i] - x_mean) * (metrics[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    @staticmethod
    def _calculate_std_dev(metrics: list[float]) -> float:
        """Calculate standard deviation."""
        if not metrics:
            return 0.0

        mean = sum(metrics) / len(metrics)
        variance = sum((x - mean) ** 2 for x in metrics) / len(metrics)
        return math.sqrt(variance)

    @staticmethod
    def _predict_saturation_time(
        current: float, trend: float, threshold: float
    ) -> float:
        """Predict time (in hours) until saturation.

        Args:
            current: Current utilization (0-1)
            trend: Trend per hour
            threshold: Saturation threshold (0-1)

        Returns:
            Hours until saturation (or negative if won't saturate)
        """
        if trend <= 0:
            return float("inf")  # Won't saturate if not trending up

        if current >= threshold:
            return 0.0  # Already saturated

        time_to_saturation = (threshold - current) / trend
        return max(0.0, time_to_saturation)

    @staticmethod
    def _predict_peak_time(metrics: list[float]) -> float:
        """Estimate time to peak based on historical data."""
        if len(metrics) < 3:
            return 1.0

        # Simple heuristic: 10 hours ahead
        return 10.0

    @staticmethod
    def _calculate_prediction_confidence(metrics: list[float]) -> float:
        """Calculate confidence in predictions based on data quality."""
        if len(metrics) < 5:
            return 0.5  # Low confidence with few data points

        # Higher confidence with more stable data
        std_dev = BottleneckDetector._calculate_std_dev(metrics)
        mean = sum(metrics) / len(metrics)

        if mean == 0:
            return 0.5

        cv = std_dev / mean  # Coefficient of variation
        confidence = 1.0 / (1.0 + cv)  # Convert to 0-1

        return min(1.0, max(0.5, confidence))
