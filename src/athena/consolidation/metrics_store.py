"""ConsolidationMetricsStore - Persist and track consolidation quality metrics."""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import ConsolidationRun


class ConsolidationMetricsStore(BaseStore[ConsolidationRun]):
    """Store and retrieve consolidation quality metrics with historical tracking."""

    # Research targets (Chen et al. 2024, LightMem 2024)
    TARGETS = {
        "compression_ratio": {"min": 0.70, "max": 0.85},
        "retrieval_recall": {"min": 0.80},
        "pattern_consistency": {"min": 0.75},
        "avg_information_density": {"min": 0.70},
    }

    table_name = "consolidation_runs"
    model_class = ConsolidationRun

    def __init__(self, db: Database):
        """Initialize metrics store.

        Args:
            db: Database instance
        """
        super().__init__(db)

    def _row_to_model(self, row: Dict[str, Any]) -> ConsolidationRun:
        """Convert database row to ConsolidationRun model.

        Args:
            row: Database row as dict

        Returns:
            ConsolidationRun instance
        """
        return ConsolidationRun(
            id=row.get("id"),
            project_id=row.get("project_id"),
            started_at=self.from_timestamp(row.get("started_at")) or datetime.now(),
            completed_at=self.from_timestamp(row.get("completed_at")),
            status=row.get("status", "running"),
            memories_scored=row.get("memories_scored", 0),
            memories_pruned=row.get("memories_pruned", 0),
            patterns_extracted=row.get("patterns_extracted", 0),
            conflicts_resolved=row.get("conflicts_resolved", 0),
            avg_quality_before=row.get("avg_quality_before"),
            avg_quality_after=row.get("avg_quality_after"),
            consolidation_type=row.get("consolidation_type", "scheduled"),
            notes=row.get("notes"),
        )

    def store_run_metrics(
        self,
        run_id: int,
        compression_ratio: float,
        retrieval_recall: float,
        pattern_consistency: float,
        avg_information_density: float,
    ) -> bool:
        """Store quality metrics for a consolidation run.

        Args:
            run_id: Consolidation run ID
            compression_ratio: Compression ratio (0-1)
            retrieval_recall: Retrieval recall score (0-1)
            pattern_consistency: Pattern consistency score (0-1)
            avg_information_density: Average information density (0-1)

        Returns:
            True if stored successfully
        """
        try:
            # Validate metrics against targets
            targets_met = self._validate_metrics(
                compression_ratio,
                retrieval_recall,
                pattern_consistency,
                avg_information_density,
            )

            # Calculate overall score
            overall_score = (
                compression_ratio * 0.25
                + retrieval_recall * 0.25
                + pattern_consistency * 0.25
                + avg_information_density * 0.25
            )

            # Store in database (using BaseStore.execute() helper)
            self.execute(
                """
                UPDATE consolidation_runs
                SET compression_ratio = ?,
                    compression_target_met = ?,
                    retrieval_recall = ?,
                    recall_target_met = ?,
                    pattern_consistency = ?,
                    consistency_target_met = ?,
                    avg_information_density = ?,
                    density_target_met = ?,
                    overall_quality_score = ?,
                    quality_metrics_json = ?
                WHERE id = ?
                """,
                (
                    compression_ratio,
                    targets_met["compression_ratio"],
                    retrieval_recall,
                    targets_met["retrieval_recall"],
                    pattern_consistency,
                    targets_met["pattern_consistency"],
                    avg_information_density,
                    targets_met["avg_information_density"],
                    overall_score,
                    self.serialize_json({
                        "compression_ratio": compression_ratio,
                        "retrieval_recall": retrieval_recall,
                        "pattern_consistency": pattern_consistency,
                        "avg_information_density": avg_information_density,
                        "overall_quality_score": overall_score,
                        "targets_met": targets_met,
                    }),
                    run_id,
                ),
            )
            self.commit()
            return True

        except Exception as e:
            print(f"Error storing metrics: {e}")
            return False

    def get_run_metrics(self, run_id: int) -> Optional[Dict]:
        """Retrieve metrics for a consolidation run.

        Args:
            run_id: Consolidation run ID

        Returns:
            Metrics dict if found, None otherwise
        """
        try:
            result = self.execute(
                """
                SELECT
                    id, project_id, started_at, completed_at,
                    compression_ratio, retrieval_recall,
                    pattern_consistency, avg_information_density,
                    overall_quality_score, quality_metrics_json
                FROM consolidation_runs
                WHERE id = ?
                """,
                (run_id,),
                fetch_one=True
            )
            if not result:
                return None

            return {
                "run_id": result[0],
                "project_id": result[1],
                "started_at": result[2],
                "completed_at": result[3],
                "compression_ratio": result[4],
                "retrieval_recall": result[5],
                "pattern_consistency": result[6],
                "avg_information_density": result[7],
                "overall_quality_score": result[8],
                "metrics_json": result[9],
            }

        except Exception as e:
            print(f"Error retrieving metrics: {e}")
            return None

    def get_project_metrics_history(
        self, project_id: int, days: int = 30
    ) -> List[Dict]:
        """Retrieve consolidation metrics history for a project.

        Args:
            project_id: Project ID
            days: Number of days to look back

        Returns:
            List of consolidation runs with metrics
        """
        try:
            # Calculate cutoff timestamp (using BaseStore helper)
            cutoff_ts = int((datetime.now() - timedelta(days=days)).timestamp())

            rows = self.execute(
                """
                SELECT
                    id, started_at, completed_at,
                    compression_ratio, retrieval_recall,
                    pattern_consistency, avg_information_density,
                    overall_quality_score, status
                FROM consolidation_runs
                WHERE project_id = ? AND started_at >= ?
                ORDER BY started_at DESC
                """,
                (project_id, cutoff_ts),
                fetch_all=True
            )

            results = []
            for row in rows:
                results.append(
                    {
                        "run_id": row[0],
                        "started_at": row[1],
                        "completed_at": row[2],
                        "compression_ratio": row[3],
                        "retrieval_recall": row[4],
                        "pattern_consistency": row[5],
                        "avg_information_density": row[6],
                        "overall_quality_score": row[7],
                        "status": row[8],
                    }
                )

            return results

        except Exception as e:
            print(f"Error retrieving project metrics: {e}")
            return []

    def get_global_metrics_summary(self) -> Dict:
        """Get global consolidation metrics summary across all projects.

        Returns:
            Summary statistics
        """
        try:
            result = self.execute(
                """
                SELECT
                    COUNT(*) as run_count,
                    AVG(compression_ratio) as avg_compression,
                    AVG(retrieval_recall) as avg_recall,
                    AVG(pattern_consistency) as avg_consistency,
                    AVG(avg_information_density) as avg_density,
                    AVG(overall_quality_score) as overall_avg,
                    MIN(overall_quality_score) as min_score,
                    MAX(overall_quality_score) as max_score
                FROM consolidation_runs
                WHERE overall_quality_score IS NOT NULL
                """,
                fetch_one=True
            )

            if not result or result[0] == 0:
                return {
                    "run_count": 0,
                    "message": "No consolidation runs with metrics",
                }

            return {
                "run_count": result[0],
                "avg_compression_ratio": result[1],
                "avg_retrieval_recall": result[2],
                "avg_pattern_consistency": result[3],
                "avg_information_density": result[4],
                "overall_avg_quality_score": result[5],
                "min_quality_score": result[6],
                "max_quality_score": result[7],
            }

        except Exception as e:
            print(f"Error retrieving global metrics: {e}")
            return {}

    def validate_against_targets(self, metrics: Dict) -> Dict[str, bool]:
        """Validate metrics against research targets.

        Args:
            metrics: Metrics dict with compression_ratio, etc.

        Returns:
            Dict with pass/fail for each metric
        """
        return {
            "compression_ratio": self._check_target(
                metrics.get("compression_ratio", 0),
                self.TARGETS["compression_ratio"],
            ),
            "retrieval_recall": self._check_target(
                metrics.get("retrieval_recall", 0),
                self.TARGETS["retrieval_recall"],
            ),
            "pattern_consistency": self._check_target(
                metrics.get("pattern_consistency", 0),
                self.TARGETS["pattern_consistency"],
            ),
            "avg_information_density": self._check_target(
                metrics.get("avg_information_density", 0),
                self.TARGETS["avg_information_density"],
            ),
        }

    # Private methods

    def _validate_metrics(
        self,
        compression_ratio: float,
        retrieval_recall: float,
        pattern_consistency: float,
        avg_information_density: float,
    ) -> Dict[str, bool]:
        """Validate all metrics against targets.

        Returns:
            Dict with pass/fail for each metric
        """
        return {
            "compression_ratio": self._check_target(
                compression_ratio,
                self.TARGETS["compression_ratio"],
            ),
            "retrieval_recall": self._check_target(
                retrieval_recall,
                self.TARGETS["retrieval_recall"],
            ),
            "pattern_consistency": self._check_target(
                pattern_consistency,
                self.TARGETS["pattern_consistency"],
            ),
            "avg_information_density": self._check_target(
                avg_information_density,
                self.TARGETS["avg_information_density"],
            ),
        }

    def _check_target(self, value: float, target: Dict) -> bool:
        """Check if value meets target.

        Args:
            value: Actual value
            target: Target spec (min/max)

        Returns:
            True if target met
        """
        if "min" in target and "max" in target:
            return target["min"] <= value <= target["max"]
        elif "min" in target:
            return value >= target["min"]
        else:
            return True
