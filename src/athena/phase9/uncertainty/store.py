"""Database store for Phase 9.1: Uncertainty-Aware Generation."""

from typing import Optional

from athena.core.database import Database
from athena.phase9.uncertainty.models import (
    ConfidenceCalibration,
    ConfidenceInterval,
    ConfidenceLevel,
    ConfidenceScore,
    ConfidenceTrendAnalysis,
    PlanAlternative,
    UncertaintyBreakdown,
    UncertaintyType,
)


class UncertaintyStore:
    """Store for uncertainty and confidence data."""

    def __init__(self, db: Database):
        """Initialize store with database connection."""
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create tables on first use."""
        cursor = self.db.conn.cursor()

        # Plan alternatives table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_alternatives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                plan_type TEXT NOT NULL,
                steps TEXT NOT NULL,
                estimated_duration_minutes INTEGER,
                confidence_score REAL,
                confidence_level TEXT,
                risk_factors TEXT,
                parallelizable_steps INTEGER,
                uncertainty_sources TEXT,
                dependencies TEXT,
                created_at INTEGER,
                rank INTEGER,
                FOREIGN KEY(task_id) REFERENCES prospective_tasks(id)
            )
            """
        )

        # Confidence scores table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS confidence_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                aspect TEXT NOT NULL,
                value REAL,
                confidence_level TEXT,
                uncertainty_sources TEXT,
                contributing_factors TEXT,
                lower_bound REAL,
                upper_bound REAL,
                supporting_evidence TEXT,
                contradicting_evidence TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                FOREIGN KEY(task_id) REFERENCES prospective_tasks(id)
            )
            """
        )

        # Uncertainty breakdown table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS uncertainty_breakdowns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                total_uncertainty REAL,
                uncertainty_sources TEXT,
                reducible_uncertainty REAL,
                irreducible_uncertainty REAL,
                mitigations TEXT,
                created_at INTEGER,
                FOREIGN KEY(task_id) REFERENCES prospective_tasks(id)
            )
            """
        )

        # Confidence calibration table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS confidence_calibrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                aspect TEXT NOT NULL,
                predicted_confidence REAL,
                actual_outcome INTEGER,
                calibration_error REAL,
                sample_count INTEGER,
                created_at INTEGER,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # Confidence trend analysis table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS confidence_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                aspect TEXT NOT NULL,
                average_confidence REAL,
                confidence_trend TEXT,
                trend_strength REAL,
                overconfidence_ratio REAL,
                underconfidence_ratio REAL,
                recommendations TEXT,
                period_days INTEGER,
                sample_size INTEGER,
                created_at INTEGER,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_plan_alternatives_task ON plan_alternatives(task_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_confidence_scores_task ON confidence_scores(task_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_uncertainty_breakdowns_task ON uncertainty_breakdowns(task_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_confidence_calibrations_project ON confidence_calibrations(project_id, aspect)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_confidence_trends_project ON confidence_trends(project_id, aspect)"
        )

        self.db.conn.commit()

    def create_plan_alternative(self, plan: PlanAlternative) -> PlanAlternative:
        """Create a new plan alternative."""
        import json
        from datetime import datetime

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO plan_alternatives
            (task_id, plan_type, steps, estimated_duration_minutes, confidence_score,
             confidence_level, risk_factors, parallelizable_steps, uncertainty_sources,
             dependencies, created_at, rank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan.task_id,
                plan.plan_type,
                json.dumps(plan.steps),
                plan.estimated_duration_minutes,
                plan.confidence_score,
                plan.confidence_level,
                json.dumps(plan.risk_factors),
                plan.parallelizable_steps,
                json.dumps(plan.uncertainty_sources),
                json.dumps(plan.dependencies),
                int(datetime.now().timestamp()),
                plan.rank,
            ),
        )
        self.db.conn.commit()
        plan.id = cursor.lastrowid
        return plan

    def get_plan_alternative(self, id: int) -> Optional[PlanAlternative]:
        """Get plan alternative by ID."""
        import json

        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM plan_alternatives WHERE id = ?",
            (id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_plan_alternative_row(row)

    def list_plan_alternatives(
        self, task_id: int, min_confidence: float = 0.0
    ) -> list[PlanAlternative]:
        """List plan alternatives for a task."""
        import json

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM plan_alternatives
            WHERE task_id = ? AND confidence_score >= ?
            ORDER BY confidence_score DESC, rank ASC
            """,
            (task_id, min_confidence),
        )
        rows = cursor.fetchall()
        return [self._parse_plan_alternative_row(row) for row in rows]

    def create_confidence_score(self, score: ConfidenceScore) -> ConfidenceScore:
        """Create a new confidence score."""
        import json
        from datetime import datetime

        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp())
        cursor.execute(
            """
            INSERT INTO confidence_scores
            (task_id, aspect, value, confidence_level, uncertainty_sources,
             contributing_factors, lower_bound, upper_bound, supporting_evidence,
             contradicting_evidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                score.task_id,
                score.aspect,
                score.value,
                score.confidence_level,
                json.dumps(score.uncertainty_sources),
                json.dumps(score.contributing_factors),
                score.lower_bound,
                score.upper_bound,
                json.dumps(score.supporting_evidence),
                json.dumps(score.contradicting_evidence),
                now,
                now,
            ),
        )
        self.db.conn.commit()
        score.id = cursor.lastrowid
        return score

    def get_confidence_scores(
        self, task_id: int, aspect: Optional[str] = None
    ) -> list[ConfidenceScore]:
        """Get confidence scores for a task."""
        import json

        cursor = self.db.conn.cursor()
        if aspect:
            cursor.execute(
                "SELECT * FROM confidence_scores WHERE task_id = ? AND aspect = ? ORDER BY created_at DESC",
                (task_id, aspect),
            )
        else:
            cursor.execute(
                "SELECT * FROM confidence_scores WHERE task_id = ? ORDER BY created_at DESC",
                (task_id,),
            )
        rows = cursor.fetchall()
        return [self._parse_confidence_score_row(row) for row in rows]

    def create_uncertainty_breakdown(
        self, breakdown: UncertaintyBreakdown
    ) -> UncertaintyBreakdown:
        """Create uncertainty breakdown."""
        import json
        from datetime import datetime

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO uncertainty_breakdowns
            (task_id, total_uncertainty, uncertainty_sources, reducible_uncertainty,
             irreducible_uncertainty, mitigations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                breakdown.task_id,
                breakdown.total_uncertainty,
                json.dumps(breakdown.uncertainty_sources),
                breakdown.reducible_uncertainty,
                breakdown.irreducible_uncertainty,
                json.dumps(breakdown.mitigations),
                int(datetime.now().timestamp()),
            ),
        )
        self.db.conn.commit()
        # Return unchanged since UncertaintyBreakdown doesn't have id field
        return breakdown

    def get_uncertainty_breakdown(self, task_id: int) -> Optional[UncertaintyBreakdown]:
        """Get latest uncertainty breakdown for task."""
        import json

        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM uncertainty_breakdowns WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_uncertainty_breakdown_row(row)

    def record_calibration(
        self, calibration: ConfidenceCalibration
    ) -> ConfidenceCalibration:
        """Record confidence calibration data."""
        from datetime import datetime

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO confidence_calibrations
            (project_id, aspect, predicted_confidence, actual_outcome,
             calibration_error, sample_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                calibration.project_id,
                calibration.aspect,
                calibration.predicted_confidence,
                1 if calibration.actual_outcome else 0,
                calibration.calibration_error,
                calibration.sample_count,
                int(datetime.now().timestamp()),
            ),
        )
        self.db.conn.commit()
        calibration.id = cursor.lastrowid
        return calibration

    def get_calibration_data(
        self, project_id: int, aspect: str, limit: int = 100
    ) -> list[ConfidenceCalibration]:
        """Get calibration data for analysis."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM confidence_calibrations
            WHERE project_id = ? AND aspect = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_id, aspect, limit),
        )
        rows = cursor.fetchall()
        return [self._parse_calibration_row(row) for row in rows]

    def save_trend_analysis(
        self, trend: ConfidenceTrendAnalysis
    ) -> ConfidenceTrendAnalysis:
        """Save trend analysis."""
        import json
        from datetime import datetime

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO confidence_trends
            (project_id, aspect, average_confidence, confidence_trend,
             trend_strength, overconfidence_ratio, underconfidence_ratio,
             recommendations, period_days, sample_size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trend.project_id,
                trend.aspect,
                trend.average_confidence,
                trend.confidence_trend,
                trend.trend_strength,
                trend.overconfidence_ratio,
                trend.underconfidence_ratio,
                json.dumps(trend.recommendations),
                trend.period_days,
                trend.sample_size,
                int(datetime.now().timestamp()),
            ),
        )
        self.db.conn.commit()
        return trend

    def get_latest_trend(
        self, project_id: int, aspect: str
    ) -> Optional[ConfidenceTrendAnalysis]:
        """Get latest trend analysis."""
        import json

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM confidence_trends
            WHERE project_id = ? AND aspect = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id, aspect),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_trend_row(row)

    # Helper methods for parsing rows

    @staticmethod
    def _parse_plan_alternative_row(row) -> PlanAlternative:
        """Parse database row to PlanAlternative."""
        import json

        return PlanAlternative(
            id=row[0],
            task_id=row[1],
            plan_type=row[2],
            steps=json.loads(row[3]),
            estimated_duration_minutes=row[4],
            confidence_score=row[5],
            confidence_level=row[6],
            risk_factors=json.loads(row[7]),
            parallelizable_steps=row[8],
            uncertainty_sources=json.loads(row[9]),
            dependencies=json.loads(row[10]),
            created_at=row[11],
            rank=row[12],
        )

    @staticmethod
    def _parse_confidence_score_row(row) -> ConfidenceScore:
        """Parse database row to ConfidenceScore."""
        import json

        return ConfidenceScore(
            id=row[0],
            task_id=row[1],
            aspect=row[2],
            value=row[3],
            confidence_level=row[4],
            uncertainty_sources=json.loads(row[5]),
            contributing_factors=json.loads(row[6]),
            lower_bound=row[7],
            upper_bound=row[8],
            supporting_evidence=json.loads(row[9]),
            contradicting_evidence=json.loads(row[10]),
            created_at=row[11],
            updated_at=row[12],
        )

    @staticmethod
    def _parse_uncertainty_breakdown_row(row) -> UncertaintyBreakdown:
        """Parse database row to UncertaintyBreakdown."""
        import json

        return UncertaintyBreakdown(
            task_id=row[1],
            total_uncertainty=row[2],
            uncertainty_sources=json.loads(row[3]),
            reducible_uncertainty=row[4],
            irreducible_uncertainty=row[5],
            mitigations=json.loads(row[6]),
            created_at=row[7],
        )

    @staticmethod
    def _parse_calibration_row(row) -> ConfidenceCalibration:
        """Parse database row to ConfidenceCalibration."""
        return ConfidenceCalibration(
            id=row[0],
            project_id=row[1],
            aspect=row[2],
            predicted_confidence=row[3],
            actual_outcome=bool(row[4]),
            calibration_error=row[5],
            sample_count=row[6],
            created_at=row[7],
        )

    @staticmethod
    def _parse_trend_row(row) -> ConfidenceTrendAnalysis:
        """Parse database row to ConfidenceTrendAnalysis."""
        import json

        return ConfidenceTrendAnalysis(
            project_id=row[1],
            aspect=row[2],
            average_confidence=row[3],
            confidence_trend=row[4],
            trend_strength=row[5],
            overconfidence_ratio=row[6],
            underconfidence_ratio=row[7],
            recommendations=json.loads(row[8]),
            period_days=row[9],
            sample_size=row[10],
            created_at=row[11],
        )
