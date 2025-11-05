"""Memory quality monitoring and evaluation."""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from statistics import mean, stdev

from .models import QualityMetrics


class MemoryQualityMonitor:
    """
    Monitors and evaluates memory quality.

    Tracks:
    - Recall accuracy (successful vs total retrievals)
    - False positive rate (incorrect memories returned)
    - False negative rate (missed memories)
    - Quality scores per memory and per layer
    - Quality trends over time
    """

    def __init__(self, db_path: str):
        """Initialize quality monitor."""
        self.db_path = db_path

    def record_retrieval(
        self,
        project_id: int,
        memory_id: int,
        memory_layer: str,
        successful: bool,
        was_false_positive: bool = False,
        was_false_negative: bool = False,
    ) -> bool:
        """
        Record a retrieval attempt.

        Args:
            project_id: Project ID
            memory_id: Memory ID
            memory_layer: Layer (semantic, episodic, etc)
            successful: Whether retrieval was successful
            was_false_positive: Whether this was incorrectly returned
            was_false_negative: Whether this was missed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get or create quality metrics record
            cursor.execute(
                """
                SELECT id FROM metacognition_quality_metrics
                WHERE project_id = ? AND memory_id = ? AND memory_layer = ?
                """,
                (project_id, memory_id, memory_layer),
            )
            row = cursor.fetchone()

            if row:
                record_id = row[0]
                # Update existing record
                cursor.execute(
                    """
                    UPDATE metacognition_quality_metrics
                    SET query_count = query_count + 1,
                        successful_retrievals = successful_retrievals + ?,
                        false_positives = false_positives + ?,
                        false_negatives = false_negatives + ?,
                        last_evaluated = ?
                    WHERE id = ?
                    """,
                    (
                        1 if successful else 0,
                        1 if was_false_positive else 0,
                        1 if was_false_negative else 0,
                        datetime.now().isoformat(),
                        record_id,
                    ),
                )
            else:
                # Create new record
                cursor.execute(
                    """
                    INSERT INTO metacognition_quality_metrics
                    (project_id, memory_id, memory_layer, query_count, successful_retrievals,
                     false_positives, false_negatives, last_evaluated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        memory_id,
                        memory_layer,
                        1,
                        1 if successful else 0,
                        1 if was_false_positive else 0,
                        1 if was_false_negative else 0,
                        datetime.now().isoformat(),
                    ),
                )

            conn.commit()
            return True

    def evaluate_memory_quality(self, memory_id: int) -> Optional[Dict]:
        """
        Evaluate quality of a specific memory.

        Returns quality metrics including accuracy, false positive rate, quality score.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, memory_id, memory_layer, query_count, successful_retrievals,
                       false_positives, false_negatives, last_evaluated
                FROM metacognition_quality_metrics
                WHERE memory_id = ?
                """,
                (memory_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            metrics = QualityMetrics(
                memory_id=row[1],
                memory_layer=row[2],
                query_count=row[3],
                successful_retrievals=row[4],
                false_positives=row[5],
                false_negatives=row[6],
                last_evaluated=datetime.fromisoformat(row[7]) if row[7] else None,
            )

            metrics.accuracy_score = metrics.calculate_quality_score()

            return {
                "memory_id": metrics.memory_id,
                "memory_layer": metrics.memory_layer,
                "query_count": metrics.query_count,
                "accuracy": metrics.calculate_accuracy(),
                "false_positive_rate": metrics.calculate_false_positive_rate(),
                "false_negative_rate": (
                    metrics.false_negatives / metrics.query_count if metrics.query_count > 0 else 0.0
                ),
                "quality_score": metrics.accuracy_score,
                "last_evaluated": metrics.last_evaluated,
            }

    def get_quality_by_layer(self, project_id: int) -> Dict[str, Dict]:
        """
        Get aggregated quality metrics by memory layer.

        Returns quality statistics for each layer.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT memory_layer,
                       COUNT(*) as total_memories,
                       AVG(CAST(successful_retrievals AS FLOAT) / CASE WHEN query_count > 0 THEN query_count ELSE 1 END) as avg_accuracy,
                       AVG(CAST(false_positives AS FLOAT) / CASE WHEN query_count > 0 THEN query_count ELSE 1 END) as avg_false_pos,
                       AVG(CAST(false_negatives AS FLOAT) / CASE WHEN query_count > 0 THEN query_count ELSE 1 END) as avg_false_neg
                FROM metacognition_quality_metrics
                WHERE project_id = ?
                GROUP BY memory_layer
                """,
                (project_id,),
            )

            result = {}
            for row in cursor.fetchall():
                layer = row[0]
                result[layer] = {
                    "total_memories": row[1],
                    "avg_accuracy": row[2] if row[2] else 0.0,
                    "avg_false_positive_rate": row[3] if row[3] else 0.0,
                    "avg_false_negative_rate": row[4] if row[4] else 0.0,
                }

            return result

    def identify_poor_performers(
        self, project_id: int, accuracy_threshold: float = 0.6
    ) -> List[Dict]:
        """
        Identify memories with accuracy below threshold.

        Returns list of underperforming memories with their quality metrics.
        """
        poor_performers = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, memory_id, memory_layer, query_count, successful_retrievals,
                       false_positives, false_negatives
                FROM metacognition_quality_metrics
                WHERE (CAST(successful_retrievals AS FLOAT) / query_count) < ?
                AND query_count >= 5
                ORDER BY (CAST(successful_retrievals AS FLOAT) / query_count) ASC
                """,
                (accuracy_threshold,),
            )

            for row in cursor.fetchall():
                accuracy = row[4] / row[3] if row[3] > 0 else 0.0
                false_pos_rate = row[5] / row[3] if row[3] > 0 else 0.0

                poor_performers.append(
                    {
                        "memory_id": row[1],
                        "memory_layer": row[2],
                        "query_count": row[3],
                        "accuracy": accuracy,
                        "false_positive_rate": false_pos_rate,
                        "recommendation": self._recommend_action(accuracy, false_pos_rate),
                    }
                )

        return poor_performers

    def detect_quality_degradation(self, memory_id: int, window_size: int = 10) -> Optional[Dict]:
        """
        Detect if memory quality is degrading over time.

        Uses rolling window to detect recent degradation.
        Returns None if insufficient data.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get quality history (simulated by checking if recent queries are worse)
            cursor.execute(
                """
                SELECT successful_retrievals, query_count, last_evaluated
                FROM metacognition_quality_metrics
                WHERE memory_id = ?
                ORDER BY last_evaluated DESC
                LIMIT 1
                """,
                (memory_id,),
            )

            row = cursor.fetchone()
            if not row or row[1] < window_size:
                return None

            recent_accuracy = row[0] / row[1] if row[1] > 0 else 0.0

            # Get historical average (if available)
            historical_query = """
                SELECT AVG(CAST(successful_retrievals AS FLOAT) / query_count)
                FROM metacognition_quality_metrics
                WHERE memory_id = ? AND last_evaluated < ?
            """

            cutoff_time = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute(historical_query, (memory_id, cutoff_time))

            hist_row = cursor.fetchone()
            historical_accuracy = hist_row[0] if hist_row and hist_row[0] else 0.5

            degradation = historical_accuracy - recent_accuracy
            is_degrading = degradation > 0.15  # 15% drop is significant

            return {
                "memory_id": memory_id,
                "recent_accuracy": recent_accuracy,
                "historical_accuracy": historical_accuracy,
                "degradation": degradation,
                "is_degrading": is_degrading,
                "severity": self._degradation_severity(degradation),
            }

    def get_quality_report(self, project_id: int, include_poor_performers: bool = True) -> Dict:
        """
        Generate comprehensive quality report for project.

        Returns overview of memory quality across all layers.
        """
        quality_by_layer = self.get_quality_by_layer(project_id)

        # Calculate overall statistics
        all_accuracies = []
        all_false_pos_rates = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT successful_retrievals, query_count, false_positives
                FROM metacognition_quality_metrics
                WHERE query_count > 0
                """
            )

            for row in cursor.fetchall():
                all_accuracies.append(row[0] / row[1] if row[1] > 0 else 0.0)
                all_false_pos_rates.append(row[2] / row[1] if row[1] > 0 else 0.0)

        report = {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "quality_by_layer": quality_by_layer,
            "overall_avg_accuracy": mean(all_accuracies) if all_accuracies else 0.0,
            "overall_avg_false_positive_rate": mean(all_false_pos_rates) if all_false_pos_rates else 0.0,
        }

        if include_poor_performers:
            report["poor_performers"] = self.identify_poor_performers(project_id)

        return report

    # Private helper methods

    def _recommend_action(self, accuracy: float, false_pos_rate: float) -> str:
        """Generate recommendation based on quality metrics."""
        if accuracy < 0.5 and false_pos_rate > 0.2:
            return "investigate_and_repair"
        elif accuracy < 0.6:
            return "improve_encoding"
        elif false_pos_rate > 0.3:
            return "reduce_false_positives"
        else:
            return "monitor"

    def _degradation_severity(self, degradation: float) -> str:
        """Determine degradation severity."""
        if degradation > 0.4:
            return "critical"
        elif degradation > 0.25:
            return "high"
        elif degradation > 0.15:
            return "medium"
        else:
            return "low"
