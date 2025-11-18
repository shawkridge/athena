"""Estimate Accuracy Tracking - Phase 3c.

Tracks and analyzes estimate accuracy per task type.
Detects systematic biases and calculates adjustment factors.
"""

import logging
from typing import Optional, Dict, Any, List

from ..core.database import Database
from ..core.base_store import BaseStore

logger = logging.getLogger(__name__)


class EstimateAccuracyStore(BaseStore):
    """Tracks estimate accuracy per task type."""

    table_name = "estimate_accuracy"

    def __init__(self, db: Database):
        """Initialize accuracy store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure estimate accuracy tables exist."""
        if not hasattr(self.db, "get_cursor"):
            logger.debug("Async database detected, skipping sync schema")
            return

        cursor = self.db.get_cursor()

        # Main accuracy table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS estimate_accuracy (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                task_type VARCHAR(50),
                accuracy_percent FLOAT DEFAULT 0.0,
                bias_factor FLOAT DEFAULT 1.0,
                variance FLOAT DEFAULT 0.0,
                sample_count INTEGER DEFAULT 0,
                avg_estimate INTEGER DEFAULT 0,
                avg_actual INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, task_type)
            )
        """
        )

        # Trends table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS estimation_trends (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                task_type VARCHAR(50),
                date DATE,
                accuracy FLOAT,
                sample_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """
        )

        self.db.commit()

    def record_completion(
        self,
        project_id: int,
        task_type: str,
        estimate_minutes: int,
        actual_minutes: int,
    ) -> bool:
        """Record a completed task's estimate accuracy.

        Args:
            project_id: Project ID
            task_type: Task type (e.g., 'feature', 'bugfix')
            estimate_minutes: Original estimate
            actual_minutes: Actual time taken

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()

            # Calculate accuracy
            accuracy = self._calculate_accuracy(estimate_minutes, actual_minutes)
            bias = actual_minutes / estimate_minutes if estimate_minutes > 0 else 1.0

            # Update aggregate stats
            cursor.execute(
                """
                INSERT INTO estimate_accuracy
                (project_id, task_type, accuracy_percent, bias_factor, sample_count,
                 avg_estimate, avg_actual)
                VALUES (%s, %s, %s, %s, 1, %s, %s)
                ON CONFLICT (project_id, task_type)
                DO UPDATE SET
                    accuracy_percent = (accuracy_percent * sample_count + %s) / (sample_count + 1),
                    bias_factor = (bias_factor * sample_count + %s) / (sample_count + 1),
                    sample_count = sample_count + 1,
                    avg_estimate = (avg_estimate * sample_count + %s) / (sample_count + 1),
                    avg_actual = (avg_actual * sample_count + %s) / (sample_count + 1),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    project_id,
                    task_type,
                    accuracy,
                    bias,
                    estimate_minutes,
                    actual_minutes,
                    accuracy,
                    bias,
                    estimate_minutes,
                    actual_minutes,
                ),
            )

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to record completion: {e}")
            return False

    def get_type_accuracy_stats(self, project_id: int, task_type: str) -> Optional[Dict[str, Any]]:
        """Get accuracy statistics for a task type.

        Args:
            project_id: Project ID
            task_type: Task type

        Returns:
            Statistics dict or None
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT accuracy_percent, bias_factor, variance, sample_count,
                       avg_estimate, avg_actual
                FROM estimate_accuracy
                WHERE project_id = %s AND task_type = %s
                """,
                (project_id, task_type),
            )

            row = cursor.fetchone()
            if not row:
                return None

            accuracy, bias, variance, sample_count, avg_est, avg_act = row

            confidence = self._calculate_confidence(sample_count, variance or 0.0)

            return {
                "task_type": task_type,
                "accuracy_percent": round(accuracy, 1) if accuracy else 0.0,
                "bias_factor": round(bias, 2) if bias else 1.0,
                "variance": round(variance, 2) if variance else 0.0,
                "sample_count": sample_count,
                "avg_estimate": avg_est or 0,
                "avg_actual": avg_act or 0,
                "confidence": confidence,
                "recommendation": self._get_recommendation(bias or 1.0, confidence),
            }

        except Exception as e:
            logger.error(f"Failed to get accuracy stats: {e}")
            return None

    def get_all_type_stats(self, project_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get accuracy stats for all task types in project.

        Args:
            project_id: Project ID

        Returns:
            List of statistics dicts
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT task_type, accuracy_percent, bias_factor, variance, sample_count
                FROM estimate_accuracy
                WHERE project_id = %s
                ORDER BY sample_count DESC
                """,
                (project_id,),
            )

            rows = cursor.fetchall()
            if not rows:
                return None

            stats = []
            for row in rows:
                task_type, accuracy, bias, variance, sample_count = row

                stats.append(
                    {
                        "task_type": task_type,
                        "accuracy_percent": round(accuracy, 1) if accuracy else 0.0,
                        "bias_factor": round(bias, 2) if bias else 1.0,
                        "sample_count": sample_count,
                        "confidence": self._calculate_confidence(sample_count, variance or 0.0),
                    }
                )

            return stats

        except Exception as e:
            logger.error(f"Failed to get all stats: {e}")
            return None

    def get_overall_accuracy(self, project_id: int) -> Optional[float]:
        """Get overall average accuracy across all task types.

        Args:
            project_id: Project ID

        Returns:
            Overall accuracy percent or None
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT AVG(accuracy_percent) FROM estimate_accuracy
                WHERE project_id = %s
                """,
                (project_id,),
            )

            row = cursor.fetchone()
            return round(row[0], 1) if row and row[0] else None

        except Exception as e:
            logger.error(f"Failed to get overall accuracy: {e}")
            return None

    @staticmethod
    def _calculate_accuracy(estimate: int, actual: int) -> float:
        """Calculate accuracy as percentage.

        Accuracy = min(estimate, actual) / max(estimate, actual) * 100

        Args:
            estimate: Estimated minutes
            actual: Actual minutes

        Returns:
            Accuracy percent (0-100)
        """
        if estimate == 0 or actual == 0:
            return 0.0

        return (min(estimate, actual) / max(estimate, actual)) * 100

    @staticmethod
    def _calculate_confidence(sample_count: int, variance: float) -> str:
        """Calculate confidence level.

        Args:
            sample_count: Number of completed tasks
            variance: Variance in estimates

        Returns:
            Confidence level: 'low', 'medium', 'high'
        """
        if sample_count < 5:
            return "low"
        elif sample_count < 15:
            if variance and variance > 0.3:
                return "low"
            return "medium"
        else:
            if variance and variance > 0.4:
                return "medium"
            return "high"

    @staticmethod
    def _get_recommendation(bias_factor: float, confidence: str) -> str:
        """Get recommendation based on bias.

        Args:
            bias_factor: Bias factor (>1 = underestimate)
            confidence: Confidence level

        Returns:
            Recommendation string
        """
        if confidence == "low":
            return "Gather more data before adjusting estimates"

        underestimate = bias_factor - 1.0
        overestimate = 1.0 - bias_factor

        if abs(underestimate) < 0.05:  # Within ±5%
            return "Estimates are well-calibrated. Keep current approach."
        elif underestimate > 0.15:
            factor_pct = int(underestimate * 100)
            return f"Multiply estimates by {bias_factor:.2f}x to account for {factor_pct}% underestimation"
        elif overestimate > 0.15:
            factor_pct = int(overestimate * 100)
            return f"Reduce estimates by {(1-bias_factor):.2f}x to account for {factor_pct}% overestimation"
        else:
            return "Small bias detected. Monitor for trends."
