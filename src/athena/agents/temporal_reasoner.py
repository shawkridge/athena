"""
Temporal reasoning and pattern analysis for the Predictor Agent.

Analyzes historical metrics to:
- Detect patterns (cycles, trends, anomalies)
- Match similar task signatures
- Extract causal relationships
- Predict based on temporal chains
"""

import math
from typing import Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from .predictor_models import TemporalPattern, PatternType

logger = logging.getLogger(__name__)


class TemporalReasoner:
    """Analyzes temporal patterns in execution metrics."""

    def __init__(self, min_pattern_strength: float = 0.6):
        """Initialize temporal reasoner.

        Args:
            min_pattern_strength: Minimum strength to report patterns (0-1)
        """
        self.min_pattern_strength = min_pattern_strength
        self.metric_history: dict[str, list[Tuple[float, datetime]]] = defaultdict(list)
        self.detected_patterns: dict[str, list[TemporalPattern]] = defaultdict(list)
        self.task_signatures: dict[str, dict] = {}

    def add_metric(
        self, metric_name: str, value: float, timestamp: Optional[datetime] = None
    ):
        """Add a new metric observation.

        Args:
            metric_name: Name of metric (e.g., "duration_seconds", "memory_mb")
            value: Metric value
            timestamp: Observation timestamp
        """
        timestamp = timestamp or datetime.now()
        self.metric_history[metric_name].append((value, timestamp))

        # Keep last 500 observations
        if len(self.metric_history[metric_name]) > 500:
            self.metric_history[metric_name].pop(0)

    def analyze_patterns(self, metric_name: str) -> list[TemporalPattern]:
        """Analyze patterns in a metric's history.

        Returns:
            List of detected patterns (sorted by strength)
        """
        if metric_name not in self.metric_history:
            return []

        data = [v for v, _ in self.metric_history[metric_name]]
        if len(data) < 5:
            return []

        patterns = []

        # Check for stationarity
        stationarity = self._check_stationarity(data)
        if stationarity > self.min_pattern_strength:
            patterns.append(
                TemporalPattern(
                    pattern_type=PatternType.STATIONARY,
                    strength=stationarity,
                    variance=self._calculate_variance(data),
                    explanation=f"Metric is stationary with variance {self._calculate_variance(data):.2f}",
                )
            )

        # Check for trend
        trend_strength, trend_slope = self._check_trend(data)
        if trend_strength > self.min_pattern_strength:
            patterns.append(
                TemporalPattern(
                    pattern_type=PatternType.TRENDING,
                    strength=trend_strength,
                    trend_slope=trend_slope,
                    variance=self._calculate_variance(data),
                    explanation=f"Metric is trending with slope {trend_slope:.4f}",
                )
            )

        # Check for cyclical patterns
        cycles = self._detect_cycles(data)
        for period, strength in cycles:
            if strength > self.min_pattern_strength:
                patterns.append(
                    TemporalPattern(
                        pattern_type=PatternType.CYCLICAL,
                        strength=strength,
                        period_hours=period / 3600.0,  # Convert to hours
                        variance=self._calculate_variance(data),
                        explanation=f"Detected {period/3600:.1f}-hour cycle with strength {strength:.2f}",
                    )
                )

        # Check for anomalies
        anomaly_strength = self._check_anomalies(data)
        if anomaly_strength > self.min_pattern_strength:
            patterns.append(
                TemporalPattern(
                    pattern_type=PatternType.ANOMALOUS,
                    strength=anomaly_strength,
                    variance=self._calculate_variance(data),
                    explanation=f"Detected anomalies in metric with strength {anomaly_strength:.2f}",
                )
            )

        # Sort by strength
        patterns.sort(key=lambda p: p.strength, reverse=True)
        self.detected_patterns[metric_name] = patterns

        return patterns

    def find_similar_tasks(
        self, task_signature: dict, similarity_threshold: float = 0.7
    ) -> list[Tuple[str, float]]:
        """Find similar tasks based on metric signature.

        Args:
            task_signature: Dict of {metric_name: value}
            similarity_threshold: Minimum similarity score

        Returns:
            List of (task_name, similarity_score) tuples
        """
        if not self.task_signatures:
            return []

        similarities = []
        for task_name, signature in self.task_signatures.items():
            similarity = self._calculate_signature_similarity(task_signature, signature)
            if similarity >= similarity_threshold:
                similarities.append((task_name, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities

    def record_task(self, task_id: str, metrics: dict[str, float]):
        """Record a task's metric signature.

        Args:
            task_id: Unique task identifier
            metrics: Dict of {metric_name: value}
        """
        self.task_signatures[task_id] = metrics

    def predict_next_value(self, metric_name: str) -> Tuple[float, float, float]:
        """Predict next value for a metric.

        Returns:
            Tuple of (prediction, lower_ci, upper_ci)
        """
        if metric_name not in self.metric_history:
            return 0.0, 0.0, 0.0

        data = [v for v, _ in self.metric_history[metric_name]]
        if len(data) < 3:
            return data[-1] if data else 0.0, 0.0, 0.0

        # Simple prediction: average of last 3 values + trend
        recent_avg = sum(data[-3:]) / 3
        trend = (data[-1] - data[-3]) / 2 if len(data) >= 3 else 0

        prediction = recent_avg + trend
        std_dev = self._calculate_std_dev(data[-10:])
        ci = std_dev * 1.96

        return max(prediction, 0.0), max(prediction - ci, 0.0), prediction + ci

    @staticmethod
    def _calculate_variance(data: list[float]) -> float:
        """Calculate variance of data."""
        if not data:
            return 0.0
        mean = sum(data) / len(data)
        return sum((x - mean) ** 2 for x in data) / len(data)

    @staticmethod
    def _calculate_std_dev(data: list[float]) -> float:
        """Calculate standard deviation."""
        return math.sqrt(TemporalReasoner._calculate_variance(data))

    @staticmethod
    def _check_stationarity(data: list[float]) -> float:
        """Check if data is stationary (strength 0-1).

        Uses variance ratio test: variance of first half vs second half.
        """
        if len(data) < 10:
            return 0.5

        mid = len(data) // 2
        var1 = TemporalReasoner._calculate_variance(data[:mid])
        var2 = TemporalReasoner._calculate_variance(data[mid:])

        if var1 == 0 or var2 == 0:
            return 0.5

        ratio = min(var1, var2) / max(var1, var2)
        return max(0.0, min(1.0, ratio))

    @staticmethod
    def _check_trend(data: list[float]) -> Tuple[float, float]:
        """Check for trend in data.

        Returns:
            Tuple of (strength, slope)
        """
        if len(data) < 3:
            return 0.0, 0.0

        # Simple linear regression
        n = len(data)
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(data) / n

        numerator = sum((x_values[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0, 0.0

        slope = numerator / denominator

        # Strength based on R-squared
        ss_tot = sum((y - y_mean) ** 2 for y in data)
        if ss_tot == 0:
            return 0.0, 0.0

        ss_res = sum((data[i] - (y_mean + slope * (x_values[i] - x_mean))) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        strength = max(0.0, min(1.0, abs(r_squared)))

        return strength, slope

    @staticmethod
    def _detect_cycles(data: list[float]) -> list[Tuple[float, float]]:
        """Detect cyclical patterns.

        Returns:
            List of (period_in_seconds, strength) tuples
        """
        if len(data) < 20:
            return []

        cycles = []

        # Check for common periods (assuming hourly samples)
        # Test periods: 24h (daily), 7d (weekly), 30d (monthly)
        test_periods = [24, 168, 720]  # In sample units

        for period in test_periods:
            if period >= len(data) // 2:
                continue

            # Autocorrelation at this period
            autocorr = 0.0
            count = 0
            mean = sum(data) / len(data)

            for i in range(period, len(data)):
                autocorr += (data[i] - mean) * (data[i - period] - mean)
                count += 1

            if count > 0:
                var = TemporalReasoner._calculate_variance(data)
                if var > 0:
                    autocorr /= count * var
                    strength = max(0.0, min(1.0, abs(autocorr)))

                    if strength > 0.5:
                        cycles.append((period, strength))

        return cycles

    @staticmethod
    def _check_anomalies(data: list[float]) -> float:
        """Detect anomalies using z-score method.

        Returns:
            Strength of anomaly pattern (0-1)
        """
        if len(data) < 5:
            return 0.0

        mean = sum(data) / len(data)
        std_dev = TemporalReasoner._calculate_std_dev(data)

        if std_dev == 0:
            return 0.0

        # Count outliers (z-score > 2)
        outliers = sum(1 for x in data if abs((x - mean) / std_dev) > 2)
        anomaly_rate = outliers / len(data)

        return min(1.0, anomaly_rate * 2)  # Scale to 0-1

    @staticmethod
    def _calculate_signature_similarity(sig1: dict, sig2: dict) -> float:
        """Calculate similarity between task signatures.

        Uses normalized Euclidean distance on common metrics.

        Returns:
            Similarity score (0-1)
        """
        common_metrics = set(sig1.keys()) & set(sig2.keys())

        if not common_metrics:
            return 0.0

        distance_sum = 0.0
        for metric in common_metrics:
            v1, v2 = sig1[metric], sig2[metric]
            if v1 == 0 and v2 == 0:
                continue

            max_val = max(abs(v1), abs(v2))
            if max_val > 0:
                distance_sum += ((v1 - v2) / max_val) ** 2

        distance = math.sqrt(distance_sum / len(common_metrics))

        # Convert distance to similarity
        similarity = 1.0 / (1.0 + distance)
        return similarity
