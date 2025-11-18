"""Predictive Effort Estimator - Phase 3c.

Predicts effort for new tasks based on historical accuracy patterns.
Provides estimates with adjustment factors and confidence levels.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..core.database import Database
from .accuracy import EstimateAccuracyStore

logger = logging.getLogger(__name__)


class PredictiveEstimator:
    """Predicts effort for tasks based on historical patterns."""

    def __init__(self, db: Database):
        """Initialize estimator.

        Args:
            db: Database instance
        """
        self.db = db
        self.accuracy_store = EstimateAccuracyStore(db)

    def predict_effort(
        self,
        project_id: int,
        task_type: str,
        base_estimate: int,
    ) -> Optional[Dict[str, Any]]:
        """Predict effort for a task based on historical patterns.

        Args:
            project_id: Project ID
            task_type: Task type (e.g., 'feature', 'bugfix')
            base_estimate: Initial estimate in minutes

        Returns:
            Prediction dict with adjusted estimate and range
        """
        try:
            # Get historical stats for this type
            stats = self.accuracy_store.get_type_accuracy_stats(project_id, task_type)

            if not stats:
                # No history, return base estimate
                return {
                    "predicted_effort": base_estimate,
                    "base_estimate": base_estimate,
                    "bias_factor": 1.0,
                    "confidence": "low",
                    "explanation": f"No historical data for '{task_type}' tasks. Using base estimate.",
                    "range": {
                        "optimistic": int(base_estimate * 0.8),
                        "expected": base_estimate,
                        "pessimistic": int(base_estimate * 1.2),
                    },
                }

            # Apply bias factor
            bias_factor = stats.get("bias_factor", 1.0)
            predicted = int(base_estimate * bias_factor)

            # Calculate range based on confidence
            confidence = stats.get("confidence", "low")
            range_factor = self._get_range_factor(confidence, stats.get("variance", 0))

            optimistic = int(predicted / (1 + range_factor))
            pessimistic = int(predicted * (1 + range_factor))

            return {
                "predicted_effort": predicted,
                "base_estimate": base_estimate,
                "bias_factor": round(bias_factor, 2),
                "confidence": confidence,
                "sample_count": stats.get("sample_count", 0),
                "explanation": self._generate_explanation(
                    task_type, stats, base_estimate, predicted
                ),
                "range": {
                    "optimistic": optimistic,
                    "expected": predicted,
                    "pessimistic": pessimistic,
                },
            }

        except Exception as e:
            logger.error(f"Failed to predict effort: {e}")
            return None

    def get_estimate_range(
        self,
        project_id: int,
        task_type: str,
        base_estimate: int,
    ) -> Optional[Dict[str, int]]:
        """Get low/medium/high estimate ranges.

        Args:
            project_id: Project ID
            task_type: Task type
            base_estimate: Base estimate

        Returns:
            Dict with 'optimistic', 'expected', 'pessimistic' estimates
        """
        try:
            prediction = self.predict_effort(project_id, task_type, base_estimate)
            if prediction:
                return prediction.get("range")
            return None

        except Exception as e:
            logger.error(f"Failed to get estimate range: {e}")
            return None

    def get_adjustment_factor(
        self,
        project_id: int,
        task_type: str,
    ) -> Optional[float]:
        """Get the adjustment factor (bias factor) for a task type.

        Args:
            project_id: Project ID
            task_type: Task type

        Returns:
            Bias factor or None
        """
        try:
            stats = self.accuracy_store.get_type_accuracy_stats(project_id, task_type)
            if stats:
                return stats.get("bias_factor", 1.0)
            return None

        except Exception as e:
            logger.error(f"Failed to get adjustment factor: {e}")
            return None

    def get_estimation_confidence(
        self,
        project_id: int,
        task_type: str,
    ) -> Optional[str]:
        """Get confidence level for estimates of this type.

        Args:
            project_id: Project ID
            task_type: Task type

        Returns:
            Confidence level: 'low', 'medium', 'high'
        """
        try:
            stats = self.accuracy_store.get_type_accuracy_stats(project_id, task_type)
            if stats:
                return stats.get("confidence", "low")
            return "low"  # No history = low confidence

        except Exception as e:
            logger.error(f"Failed to get confidence: {e}")
            return "low"

    def get_estimation_trends(
        self,
        project_id: int,
        task_type: str,
        days_back: int = 90,
    ) -> Optional[Dict[str, Any]]:
        """Get estimation trend over time.

        Detects if accuracy is improving or degrading.

        Args:
            project_id: Project ID
            task_type: Task type
            days_back: How many days to analyze

        Returns:
            Trend analysis dict
        """
        try:
            cursor = self.db.get_cursor()

            # Get recent accuracy measurements
            since_date = (datetime.now() - timedelta(days=days_back)).date()

            cursor.execute(
                """
                SELECT date, accuracy, sample_count
                FROM estimation_trends
                WHERE project_id = %s AND task_type = %s AND date >= %s
                ORDER BY date ASC
                """,
                (project_id, task_type, since_date),
            )

            rows = cursor.fetchall()
            if not rows or len(rows) < 2:
                return None

            # Calculate trend
            first_accuracy = rows[0][1]
            last_accuracy = rows[-1][1]
            improvement = last_accuracy - first_accuracy

            if improvement > 0.05:  # 5% improvement
                trend = "improving"
            elif improvement < -0.05:
                trend = "degrading"
            else:
                trend = "stable"

            return {
                "task_type": task_type,
                "trend": trend,
                f"accuracy_{days_back}days_ago": round(first_accuracy, 1),
                "accuracy_today": round(last_accuracy, 1),
                "improvement": round(improvement, 2),
                "data_points": len(rows),
                "message": self._trend_message(trend, improvement),
            }

        except Exception as e:
            logger.error(f"Failed to get trends: {e}")
            return None

    @staticmethod
    def _get_range_factor(confidence: str, variance: float) -> float:
        """Get multiplier for estimate range.

        Args:
            confidence: Confidence level
            variance: Variance in estimates

        Returns:
            Range factor (0.0-0.5)
        """
        base_factor = {
            "high": 0.15,
            "medium": 0.30,
            "low": 0.50,
        }.get(confidence, 0.50)

        # Increase range if high variance
        if variance and variance > 0.3:
            base_factor += 0.10

        return min(base_factor, 0.50)  # Cap at 50%

    @staticmethod
    def _generate_explanation(
        task_type: str,
        stats: Dict[str, Any],
        base_estimate: int,
        predicted: int,
    ) -> str:
        """Generate human-readable explanation.

        Args:
            task_type: Task type
            stats: Accuracy stats
            base_estimate: Original estimate
            predicted: Adjusted estimate

        Returns:
            Explanation string
        """
        sample_count = stats.get("sample_count", 0)
        bias_factor = stats.get("bias_factor", 1.0)
        confidence = stats.get("confidence", "low")

        if sample_count == 0:
            return "No historical data available for adjustment."

        adjustment_pct = int((bias_factor - 1.0) * 100)

        if adjustment_pct > 0:
            return (
                f"Based on {sample_count} similar '{task_type}' tasks, "
                f"you consistently underestimate by {adjustment_pct}%. "
                f"Adjusted: {base_estimate}m × {bias_factor:.2f} = {predicted}m. "
                f"Confidence: {confidence}."
            )
        elif adjustment_pct < 0:
            return (
                f"Based on {sample_count} similar '{task_type}' tasks, "
                f"you consistently overestimate by {abs(adjustment_pct)}%. "
                f"Adjusted: {base_estimate}m × {bias_factor:.2f} = {predicted}m. "
                f"Confidence: {confidence}."
            )
        else:
            return (
                f"Based on {sample_count} similar '{task_type}' tasks, "
                f"your estimates are well-calibrated. "
                f"Estimate: {predicted}m. Confidence: {confidence}."
            )

    @staticmethod
    def _trend_message(trend: str, improvement: float) -> str:
        """Generate trend message.

        Args:
            trend: Trend direction
            improvement: Improvement amount

        Returns:
            Message string
        """
        if trend == "improving":
            return f"Great! Your '{trend}' by {improvement:.0%}. Keep refining estimates."
        elif trend == "degrading":
            return f"Caution: Estimates degrading by {abs(improvement):.0%}. Review estimation approach."
        else:
            return "Estimates are stable. No significant trend detected."
