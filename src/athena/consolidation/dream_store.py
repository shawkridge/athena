"""Dream procedure storage and query operations."""

import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ..core.database import Database
from ..core.base_store import BaseStore
from .dream_models import (
    DreamProcedure,
    DreamType,
    DreamTier,
    DreamStatus,
    DreamGenerationRun,
    DreamMetrics,
)


class DreamStore(BaseStore[DreamProcedure]):
    """Manages dream procedure storage and query operations."""

    table_name = "dream_procedures"
    model_class = DreamProcedure

    def __init__(self, db: Database):
        """Initialize dream store.

        Args:
            db: Database instance
        """
        super().__init__(db)

    def _row_to_model(self, row: Dict[str, Any]) -> DreamProcedure:
        """Convert database row to DreamProcedure model."""
        return DreamProcedure(
            id=row.get("id"),
            base_procedure_id=row.get("base_procedure_id"),
            base_procedure_name=row.get("base_procedure_name"),
            dream_type=row.get("dream_type"),
            code=row.get("code"),
            model_used=row.get("model_used"),
            reasoning=row.get("reasoning"),
            generated_description=row.get("generated_description"),
            status=row.get("status", DreamStatus.PENDING_EVALUATION.value),
            tier=int(row.get("tier")) if row.get("tier") else None,
            viability_score=row.get("viability_score"),
            claude_reasoning=row.get("claude_reasoning"),
            test_outcome=row.get("test_outcome"),
            test_error=row.get("test_error"),
            test_timestamp=self.from_timestamp(row.get("test_timestamp"))
            if row.get("test_timestamp")
            else None,
            novelty_score=row.get("novelty_score"),
            cross_project_matches=row.get("cross_project_matches", 0),
            effectiveness_metric=row.get("effectiveness_metric"),
            generated_at=self.from_timestamp(row.get("generated_at")),
            evaluated_at=self.from_timestamp(row.get("evaluated_at"))
            if row.get("evaluated_at")
            else None,
            created_by=row.get("created_by"),
        )

    def _ensure_schema(self):
        """Ensure dream tables exist."""
        if not hasattr(self.db, "conn"):
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(
                f"{self.__class__.__name__}: PostgreSQL async database detected."
            )
            return

        cursor = self.db.get_cursor()

        # Dream procedures table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dream_procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_procedure_id INTEGER NOT NULL,
                base_procedure_name TEXT NOT NULL,
                dream_type TEXT NOT NULL,
                code TEXT NOT NULL,
                model_used TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                generated_description TEXT,

                status TEXT DEFAULT 'pending_evaluation',
                tier INTEGER,
                viability_score REAL,
                claude_reasoning TEXT,

                test_outcome TEXT,
                test_error TEXT,
                test_timestamp INTEGER,

                novelty_score REAL,
                cross_project_matches INTEGER DEFAULT 0,
                effectiveness_metric REAL,

                generated_at INTEGER NOT NULL,
                evaluated_at INTEGER,
                created_by TEXT DEFAULT 'dream_system',

                FOREIGN KEY(base_procedure_id) REFERENCES procedures(id)
            )
        """
        )

        # Dream generation runs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dream_generation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                total_dreams_generated INTEGER,
                constraint_relaxation_count INTEGER,
                cross_project_synthesis_count INTEGER,
                parameter_exploration_count INTEGER,
                conditional_variant_count INTEGER,
                duration_seconds REAL,
                model_usage TEXT
            )
        """
        )

        # Dream metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dream_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                average_viability_score REAL,
                tier1_count INTEGER,
                tier2_count INTEGER,
                tier3_count INTEGER,
                tier1_test_success_rate REAL,
                tier1_test_count INTEGER,
                average_novelty_score REAL,
                high_novelty_count INTEGER,
                cross_project_adoption_rate REAL,
                dreams_adopted_count INTEGER,
                average_generation_time_seconds REAL,
                api_requests_per_dream REAL,
                novelty_score_weighted REAL,
                quality_evolution_weighted REAL,
                cross_project_leverage_weighted REAL,
                efficiency_weighted REAL,
                compound_health_score REAL
            )
        """
        )

        # Create indexes for common queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dream_status ON dream_procedures(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dream_tier ON dream_procedures(tier)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dream_base_proc ON dream_procedures(base_procedure_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dream_type ON dream_procedures(dream_type)"
        )

        self.db.commit()

    # CRUD Operations

    async def store_dream(self, dream: DreamProcedure) -> int:
        """Store a dream procedure."""
        sql = """
            INSERT INTO dream_procedures (
                base_procedure_id, base_procedure_name, dream_type, code,
                model_used, reasoning, generated_description,
                status, generated_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            dream.base_procedure_id,
            dream.base_procedure_name,
            dream.dream_type,
            dream.code,
            dream.model_used,
            dream.reasoning,
            dream.generated_description,
            dream.status.value if isinstance(dream.status, DreamStatus) else dream.status,
            self.to_timestamp(dream.generated_at),
            dream.created_by,
        )

        cursor = self.db.get_cursor()
        cursor.execute(sql, params)
        self.db.commit()

        return cursor.lastrowid

    async def store_dreams_batch(self, dreams: List[DreamProcedure]) -> List[int]:
        """Store multiple dreams efficiently."""
        ids = []
        for dream in dreams:
            dream_id = await self.store_dream(dream)
            ids.append(dream_id)
        return ids

    async def get_dream(self, dream_id: int) -> Optional[DreamProcedure]:
        """Retrieve a dream by ID."""
        cursor = self.db.get_cursor()
        cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (dream_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(dict(row))

    async def update_dream(self, dream: DreamProcedure) -> bool:
        """Update a dream procedure."""
        sql = """
            UPDATE dream_procedures SET
                status = ?, tier = ?, viability_score = ?,
                claude_reasoning = ?, evaluated_at = ?,
                test_outcome = ?, test_error = ?, test_timestamp = ?,
                novelty_score = ?, cross_project_matches = ?,
                effectiveness_metric = ?
            WHERE id = ?
        """

        params = (
            dream.status.value if isinstance(dream.status, DreamStatus) else dream.status,
            dream.tier.value if isinstance(dream.tier, DreamTier) else dream.tier,
            dream.viability_score,
            dream.claude_reasoning,
            self.to_timestamp(dream.evaluated_at) if dream.evaluated_at else None,
            dream.test_outcome,
            dream.test_error,
            self.to_timestamp(dream.test_timestamp) if dream.test_timestamp else None,
            dream.novelty_score,
            dream.cross_project_matches,
            dream.effectiveness_metric,
            dream.id,
        )

        cursor = self.db.get_cursor()
        cursor.execute(sql, params)
        self.db.commit()

        return cursor.rowcount > 0

    async def delete_dream(self, dream_id: int) -> bool:
        """Delete a dream procedure."""
        cursor = self.db.get_cursor()
        cursor.execute("DELETE FROM dream_procedures WHERE id = ?", (dream_id,))
        self.db.commit()
        return cursor.rowcount > 0

    # Query Operations

    async def get_pending_evaluation(self, limit: int = 100) -> List[DreamProcedure]:
        """Get dreams waiting for Claude evaluation."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT * FROM {self.table_name}
            WHERE status = ?
            ORDER BY generated_at DESC
            LIMIT ?
        """,
            (DreamStatus.PENDING_EVALUATION.value, limit),
        )

        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_by_status(self, status: DreamStatus, limit: int = 100) -> List[DreamProcedure]:
        """Get dreams by status."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT * FROM {self.table_name}
            WHERE status = ?
            ORDER BY evaluated_at DESC
            LIMIT ?
        """,
            (status.value, limit),
        )

        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_by_tier(self, tier: DreamTier, limit: int = 100) -> List[DreamProcedure]:
        """Get dreams by tier."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT * FROM {self.table_name}
            WHERE tier = ? AND status = ?
            ORDER BY viability_score DESC
            LIMIT ?
        """,
            (tier.value, DreamStatus.EVALUATED.value, limit),
        )

        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_by_type(self, dream_type: DreamType, limit: int = 100) -> List[DreamProcedure]:
        """Get dreams by type."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT * FROM {self.table_name}
            WHERE dream_type = ?
            ORDER BY generated_at DESC
            LIMIT ?
        """,
            (dream_type.value, limit),
        )

        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_by_base_procedure(
        self, procedure_id: int, limit: int = 100
    ) -> List[DreamProcedure]:
        """Get all dreams for a base procedure."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT * FROM {self.table_name}
            WHERE base_procedure_id = ?
            ORDER BY generated_at DESC
            LIMIT ?
        """,
            (procedure_id, limit),
        )

        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_high_novelty(self, min_score: float = 0.7, limit: int = 50) -> List[DreamProcedure]:
        """Get dreams with high novelty scores."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT * FROM {self.table_name}
            WHERE novelty_score >= ? AND status = ?
            ORDER BY novelty_score DESC
            LIMIT ?
        """,
            (min_score, DreamStatus.EVALUATED.value, limit),
        )

        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def get_cross_project_viable(self, min_matches: int = 2, limit: int = 50) -> List[DreamProcedure]:
        """Get dreams that could be used across multiple projects."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT * FROM {self.table_name}
            WHERE cross_project_matches >= ? AND tier = ?
            ORDER BY cross_project_matches DESC
            LIMIT ?
        """,
            (min_matches, DreamTier.VIABLE.value, limit),
        )

        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    # Statistics

    async def count_by_status(self) -> Dict[str, int]:
        """Get count of dreams by status."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT status, COUNT(*) as count
            FROM {self.table_name}
            GROUP BY status
        """
        )

        result = {}
        for row in cursor.fetchall():
            result[row["status"]] = row["count"]
        return result

    async def count_by_tier(self) -> Dict[int, int]:
        """Get count of dreams by tier."""
        cursor = self.db.get_cursor()
        cursor.execute(
            f"""
            SELECT tier, COUNT(*) as count
            FROM {self.table_name}
            WHERE tier IS NOT NULL
            GROUP BY tier
        """
        )

        result = {}
        for row in cursor.fetchall():
            if row["tier"]:
                result[row["tier"]] = row["count"]
        return result

    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive dream statistics."""
        cursor = self.db.get_cursor()

        # Total dreams
        cursor.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
        total_dreams = cursor.fetchone()["count"]

        # By status
        status_counts = await self.count_by_status()

        # By tier
        tier_counts = await self.count_by_tier()

        # Average viability
        cursor.execute(
            f"""
            SELECT AVG(viability_score) as avg_viability
            FROM {self.table_name}
            WHERE viability_score IS NOT NULL
        """
        )
        avg_viability = cursor.fetchone()["avg_viability"] or 0.0

        # Average novelty
        cursor.execute(
            f"""
            SELECT AVG(novelty_score) as avg_novelty
            FROM {self.table_name}
            WHERE novelty_score IS NOT NULL
        """
        )
        avg_novelty = cursor.fetchone()["avg_novelty"] or 0.0

        # Test success rate for tier 1
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN test_outcome = 'success' THEN 1 ELSE 0 END) as successes
            FROM {self.table_name}
            WHERE tier = ? AND test_outcome IS NOT NULL
        """,
            (DreamTier.VIABLE.value,),
        )
        test_stats = cursor.fetchone()
        tier1_success_rate = (
            (test_stats["successes"] / test_stats["total"])
            if test_stats["total"] > 0
            else 0.0
        )

        return {
            "total_dreams": total_dreams,
            "by_status": status_counts,
            "by_tier": tier_counts,
            "average_viability": avg_viability,
            "average_novelty": avg_novelty,
            "tier1_success_rate": tier1_success_rate,
        }

    # Dream Generation Run Tracking

    async def record_generation_run(self, run: DreamGenerationRun) -> int:
        """Record a dream generation run."""
        sql = """
            INSERT INTO dream_generation_runs (
                strategy, timestamp, total_dreams_generated,
                constraint_relaxation_count, cross_project_synthesis_count,
                parameter_exploration_count, conditional_variant_count,
                duration_seconds, model_usage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            run.strategy,
            self.to_timestamp(run.timestamp),
            run.total_dreams_generated,
            run.constraint_relaxation_count,
            run.cross_project_synthesis_count,
            run.parameter_exploration_count,
            run.conditional_variant_count,
            run.duration_seconds,
            json.dumps(run.model_usage) if run.model_usage else None,
        )

        cursor = self.db.get_cursor()
        cursor.execute(sql, params)
        self.db.commit()

        return cursor.lastrowid

    # Dream Metrics

    async def store_metrics(self, metrics: DreamMetrics) -> int:
        """Store dream system metrics."""
        sql = """
            INSERT INTO dream_metrics (
                timestamp, average_viability_score, tier1_count, tier2_count, tier3_count,
                tier1_test_success_rate, tier1_test_count, average_novelty_score,
                high_novelty_count, cross_project_adoption_rate, dreams_adopted_count,
                average_generation_time_seconds, api_requests_per_dream,
                novelty_score_weighted, quality_evolution_weighted,
                cross_project_leverage_weighted, efficiency_weighted,
                compound_health_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            self.to_timestamp(metrics.timestamp),
            metrics.average_viability_score,
            metrics.tier1_count,
            metrics.tier2_count,
            metrics.tier3_count,
            metrics.tier1_test_success_rate,
            metrics.tier1_test_count,
            metrics.average_novelty_score,
            metrics.high_novelty_count,
            metrics.cross_project_adoption_rate,
            metrics.dreams_adopted_count,
            metrics.average_generation_time_seconds,
            metrics.api_requests_per_dream,
            metrics.novelty_score_weighted,
            metrics.quality_evolution_weighted,
            metrics.cross_project_leverage_weighted,
            metrics.efficiency_weighted,
            metrics.compound_health_score,
        )

        cursor = self.db.get_cursor()
        cursor.execute(sql, params)
        self.db.commit()

        return cursor.lastrowid

    async def get_latest_metrics(self) -> Optional[DreamMetrics]:
        """Get the most recent metrics."""
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM dream_metrics
            ORDER BY timestamp DESC
            LIMIT 1
        """
        )

        row = cursor.fetchone()
        if not row:
            return None

        row_dict = dict(row)
        row_dict["timestamp"] = self.from_timestamp(row_dict["timestamp"])
        return DreamMetrics(**row_dict)
