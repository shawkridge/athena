"""Cognitive load monitoring and capacity management."""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from statistics import mean

from .models import CognitiveLoad, SaturationLevel


class CognitiveLoadMonitor:
    """
    Monitors system cognitive load and working memory capacity.

    Capabilities:
    - Track active memory utilization
    - Monitor query latency
    - Detect saturation conditions
    - Predict capacity overflow
    - Recommend optimizations
    - Generate load reports
    - Track trends over time
    """

    # Default configuration
    DEFAULT_MAX_CAPACITY = 7  # Baddeley's magical number

    def __init__(self, db_path: str, max_capacity: int = DEFAULT_MAX_CAPACITY):
        """Initialize load monitor."""
        self.db_path = db_path
        self.max_capacity = max_capacity

    def record_cognitive_load(
        self,
        project_id: int,
        active_memory_count: int,
        query_latency_ms: float,
    ) -> bool:
        """
        Record a cognitive load snapshot.

        Args:
            project_id: Project ID
            active_memory_count: Number of active memories
            query_latency_ms: Query latency in milliseconds
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            utilization = self.calculate_utilization(active_memory_count)
            saturation = self.detect_saturation_level(
                utilization, query_latency_ms
            )

            cursor.execute(
                """
                INSERT INTO metacognition_cognitive_load
                (project_id, active_memory_count, max_capacity, utilization_percent,
                 query_latency_ms, saturation_level, metric_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    active_memory_count,
                    self.max_capacity,
                    utilization,
                    query_latency_ms,
                    saturation.value,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return True

    def calculate_utilization(self, active_memory_count: int) -> float:
        """
        Calculate memory utilization percentage.

        Returns: Percentage (0-100)
        """
        if self.max_capacity == 0:
            return 0.0
        return (active_memory_count / self.max_capacity) * 100.0

    def detect_saturation_level(
        self, utilization_percent: float, query_latency_ms: float
    ) -> SaturationLevel:
        """
        Determine saturation level based on utilization and latency.

        Saturation levels:
        - LOW: <50% capacity, latency <100ms
        - MEDIUM: 50-75% capacity, latency 100-300ms
        - HIGH: 75-90% capacity, latency 300-500ms
        - CRITICAL: >90% capacity, latency >500ms
        """
        if utilization_percent > 90 or query_latency_ms > 500:
            return SaturationLevel.CRITICAL
        elif utilization_percent > 75 or query_latency_ms > 300:
            return SaturationLevel.HIGH
        elif utilization_percent > 50 or query_latency_ms > 100:
            return SaturationLevel.MEDIUM
        else:
            return SaturationLevel.LOW

    def get_current_load(self, project_id: int) -> Optional[Dict]:
        """
        Get current cognitive load status.

        Returns:
            Dictionary with current load metrics or None if no data
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT active_memory_count, utilization_percent, query_latency_ms,
                       saturation_level, metric_timestamp
                FROM metacognition_cognitive_load
                WHERE project_id = ?
                ORDER BY metric_timestamp DESC
                LIMIT 1
                """,
                (project_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        active_count, util, latency, saturation, timestamp = row
        return {
            "active_memory_count": active_count,
            "utilization_percent": util,
            "query_latency_ms": latency,
            "saturation_level": saturation,
            "timestamp": timestamp,
        }

    def predict_saturation(self, project_id: int, hours_ahead: int = 1) -> Dict:
        """
        Predict if saturation will occur based on trends.

        Args:
            project_id: Project ID
            hours_ahead: How many hours ahead to predict

        Returns:
            Dictionary with prediction:
            - will_saturate: Boolean
            - predicted_utilization: Expected utilization
            - time_to_saturation: Minutes until saturation (if applicable)
            - confidence: Confidence in prediction (0-1)
            - recommendation: Suggested action
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get recent load data
            cutoff_time = (
                (datetime.now() - timedelta(hours=1)).isoformat()
            )
            cursor.execute(
                """
                SELECT utilization_percent, metric_timestamp
                FROM metacognition_cognitive_load
                WHERE project_id = ? AND metric_timestamp >= ?
                ORDER BY metric_timestamp
                LIMIT 20
                """,
                (project_id, cutoff_time),
            )
            rows = cursor.fetchall()

        if len(rows) < 2:
            return {
                "will_saturate": False,
                "predicted_utilization": 0.0,
                "time_to_saturation": None,
                "confidence": 0.0,
                "recommendation": "Insufficient data for prediction",
            }

        utilizations = [r[0] for r in rows]
        current_utilization = utilizations[-1]

        # Simple trend: calculate rate of change
        if len(utilizations) > 1:
            rate_of_change = (utilizations[-1] - utilizations[0]) / len(
                utilizations
            )
        else:
            rate_of_change = 0.0

        # Project forward
        predicted_utilization = current_utilization + (rate_of_change * hours_ahead)
        predicted_utilization = max(0.0, min(100.0, predicted_utilization))

        # Determine if will saturate
        will_saturate = predicted_utilization > 75

        time_to_saturation = None
        if rate_of_change > 0 and current_utilization < 75:
            # Calculate minutes until 75% saturation
            minutes_to_saturation = (75 - current_utilization) / rate_of_change / 60
            if minutes_to_saturation > 0:
                time_to_saturation = int(minutes_to_saturation)

        # Recommendation
        if will_saturate:
            recommendation = "Begin consolidation immediately"
        elif predicted_utilization > 50:
            recommendation = "Monitor closely and prepare for consolidation"
        else:
            recommendation = "No immediate action required"

        return {
            "will_saturate": will_saturate,
            "predicted_utilization": predicted_utilization,
            "time_to_saturation": time_to_saturation,
            "confidence": min(len(rows) / 20.0, 1.0),  # Confidence increases with data
            "recommendation": recommendation,
        }

    def recommend_optimization(self, project_id: int) -> List[Dict]:
        """
        Generate optimization recommendations based on load patterns.

        Returns:
            List of recommendations with:
            - action: What to do
            - reason: Why it's recommended
            - priority: 'low', 'medium', 'high'
            - expected_improvement: Estimated improvement percentage
        """
        current = self.get_current_load(project_id)
        if not current:
            return []

        recommendations = []
        saturation = current["saturation_level"]
        utilization = current["utilization_percent"]
        latency = current["query_latency_ms"]

        # Saturation-based recommendations
        if saturation == SaturationLevel.CRITICAL:
            recommendations.append(
                {
                    "action": "Force consolidation immediately",
                    "reason": f"Critical saturation: {utilization:.1f}% utilization, {latency:.1f}ms latency",
                    "priority": "high",
                    "expected_improvement": 0.4,
                }
            )
            recommendations.append(
                {
                    "action": "Pause new memory creation",
                    "reason": "System is at critical capacity",
                    "priority": "high",
                    "expected_improvement": 0.3,
                }
            )

        elif saturation == SaturationLevel.HIGH:
            recommendations.append(
                {
                    "action": "Begin consolidation",
                    "reason": f"High saturation: {utilization:.1f}% utilization",
                    "priority": "medium",
                    "expected_improvement": 0.3,
                }
            )
            recommendations.append(
                {
                    "action": "Optimize query patterns",
                    "reason": f"Latency is elevated: {latency:.1f}ms",
                    "priority": "medium",
                    "expected_improvement": 0.15,
                }
            )

        elif saturation == SaturationLevel.MEDIUM:
            recommendations.append(
                {
                    "action": "Monitor trends closely",
                    "reason": f"Medium saturation: {utilization:.1f}% utilization",
                    "priority": "low",
                    "expected_improvement": 0.1,
                }
            )

        # Latency-specific recommendations
        if latency > 300:
            recommendations.append(
                {
                    "action": "Profile and optimize hot queries",
                    "reason": f"Query latency is high: {latency:.1f}ms",
                    "priority": "medium",
                    "expected_improvement": 0.2,
                }
            )

        return recommendations

    def get_load_history(
        self, project_id: int, hours: int = 24
    ) -> List[Dict]:
        """
        Get historical load data.

        Returns:
            List of load measurements over time
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cutoff_time = (
                (datetime.now() - timedelta(hours=hours)).isoformat()
            )
            cursor.execute(
                """
                SELECT active_memory_count, utilization_percent, query_latency_ms,
                       saturation_level, metric_timestamp
                FROM metacognition_cognitive_load
                WHERE project_id = ? AND metric_timestamp >= ?
                ORDER BY metric_timestamp
                """,
                (project_id, cutoff_time),
            )
            rows = cursor.fetchall()

        history = []
        for row in rows:
            active_count, util, latency, saturation, timestamp = row
            history.append(
                {
                    "active_memory_count": active_count,
                    "utilization_percent": util,
                    "query_latency_ms": latency,
                    "saturation_level": saturation,
                    "timestamp": timestamp,
                }
            )

        return history

    def get_cognitive_load_report(self, project_id: int) -> Dict:
        """
        Generate comprehensive cognitive load report.

        Returns:
            Dictionary with complete analysis:
            - current_load: Current metrics
            - trend: Load trend over time
            - saturation_risk: Risk assessment
            - recommendations: Optimization suggestions
            - summary: High-level summary
        """
        current = self.get_current_load(project_id)
        history = self.get_load_history(project_id, hours=24)
        prediction = self.predict_saturation(project_id, hours_ahead=1)
        recommendations = self.recommend_optimization(project_id)

        # Calculate trend
        if len(history) > 1:
            utilizations = [h["utilization_percent"] for h in history]
            trend_direction = (
                "increasing"
                if utilizations[-1] > utilizations[0]
                else "decreasing"
            )
            avg_utilization = mean(utilizations)
        else:
            trend_direction = "unknown"
            avg_utilization = current["utilization_percent"] if current else 0.0

        # Risk assessment
        if current:
            saturation = current["saturation_level"]
            if saturation == SaturationLevel.CRITICAL:
                saturation_risk = "CRITICAL"
            elif saturation == SaturationLevel.HIGH:
                saturation_risk = "HIGH"
            elif saturation == SaturationLevel.MEDIUM:
                saturation_risk = "MODERATE"
            else:
                saturation_risk = "LOW"
        else:
            saturation_risk = "UNKNOWN"

        summary = (
            f"Cognitive Load Report - Project {project_id}\n"
            f"Current Utilization: {current['utilization_percent']:.1f}% "
            if current
            else "No load data\n"
        )
        if current:
            summary += f"({current['active_memory_count']}/{self.max_capacity})\n"
            summary += f"Query Latency: {current['query_latency_ms']:.1f}ms\n"
            summary += f"Saturation Level: {saturation_risk}\n"
            summary += f"Trend: {trend_direction}\n"
            summary += f"Risk: {saturation_risk}"

        return {
            "current_load": current,
            "history": history,
            "trend": {"direction": trend_direction, "avg_utilization": avg_utilization},
            "prediction": prediction,
            "saturation_risk": saturation_risk,
            "recommendations": recommendations,
            "summary": summary,
        }
