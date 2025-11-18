"""Consolidation run history tracking and metrics.

This module tracks consolidation pipeline execution metrics including:
- Execution timestamps and duration
- Events processed and consolidated
- Patterns extracted
- Quality improvements
- Error rates and failure modes
- Performance metrics (throughput, latency)

The history is used for:
1. Monitoring consolidation effectiveness over time
2. Performance optimization (identifying bottlenecks)
3. Anomaly detection (unusual failure patterns)
4. Learning and feedback (what patterns work best)
5. Debugging (understanding what happened during a run)

Database Schema:
```sql
CREATE TABLE consolidation_runs (
    run_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT,  -- 'pending', 'running', 'success', 'failed', 'partial'

    -- Metrics
    events_processed INTEGER,
    events_consolidated INTEGER,
    patterns_extracted INTEGER,
    patterns_validated INTEGER,

    -- Quality metrics
    quality_before FLOAT,
    quality_after FLOAT,
    quality_improvement FLOAT,

    -- Performance
    duration_seconds FLOAT,
    events_per_second FLOAT,

    -- Error tracking
    errors INTEGER,
    error_messages TEXT,

    -- Metadata
    config TEXT,  -- JSON config used
    notes TEXT,

    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX idx_consolidation_runs_project_id ON consolidation_runs(project_id);
CREATE INDEX idx_consolidation_runs_created_at ON consolidation_runs(started_at);
```
"""

import logging
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ConsolidationStatus(Enum):
    """Status of a consolidation run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some channels/projects succeeded, others failed


@dataclass
class ConsolidationRunMetrics:
    """Metrics from a single consolidation run."""

    # Identity
    run_id: Optional[int] = None
    project_id: int = 1

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status
    status: ConsolidationStatus = ConsolidationStatus.PENDING

    # Processing metrics
    events_processed: int = 0
    events_consolidated: int = 0
    patterns_extracted: int = 0
    patterns_validated: int = 0
    memories_created: int = 0

    # Quality metrics
    quality_before: float = 0.0
    quality_after: float = 0.0

    # Performance metrics
    throughput_events_per_sec: float = 0.0
    avg_pattern_confidence: float = 0.0

    # Error tracking
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)

    # Configuration and metadata
    config: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @property
    def duration_seconds(self) -> float:
        """Calculate run duration in seconds."""
        if not self.started_at or not self.completed_at:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def quality_improvement(self) -> float:
        """Calculate quality improvement (percentage)."""
        if self.quality_before == 0:
            return 0.0
        improvement = (self.quality_after - self.quality_before) / self.quality_before
        return max(0.0, min(1.0, improvement))  # Clamp to [0, 1]

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-1)."""
        if self.events_processed == 0:
            return 0.0
        return self.events_consolidated / self.events_processed

    @property
    def is_complete(self) -> bool:
        """Check if run is complete (has end time)."""
        return self.completed_at is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        data = asdict(self)
        # Convert datetime to ISO string
        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        # Convert enum to string
        data["status"] = self.status.value
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ConsolidationRunMetrics":
        """Create from dictionary."""
        # Parse datetime strings
        if isinstance(data.get("started_at"), str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if isinstance(data.get("completed_at"), str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        # Parse enum
        if isinstance(data.get("status"), str):
            data["status"] = ConsolidationStatus(data["status"])
        return ConsolidationRunMetrics(**data)


class ConsolidationRunHistory:
    """Track and query consolidation run history."""

    def __init__(self, db: Any):
        """Initialize history tracker.

        Args:
            db: Database connection (PostgreSQL)
        """
        self.db = db
        self._init_schema()

    def _init_schema(self) -> None:
        """Create schema if it doesn't exist (idempotent)."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS consolidation_runs (
                run_id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pending',

                -- Metrics
                events_processed INTEGER DEFAULT 0,
                events_consolidated INTEGER DEFAULT 0,
                patterns_extracted INTEGER DEFAULT 0,
                patterns_validated INTEGER DEFAULT 0,
                memories_created INTEGER DEFAULT 0,

                -- Quality
                quality_before FLOAT DEFAULT 0.0,
                quality_after FLOAT DEFAULT 0.0,

                -- Performance
                throughput_events_per_sec FLOAT DEFAULT 0.0,
                avg_pattern_confidence FLOAT DEFAULT 0.0,

                -- Errors
                errors INTEGER DEFAULT 0,
                error_messages TEXT,  -- JSON array

                -- Metadata
                config TEXT,  -- JSON
                notes TEXT,

                FOREIGN KEY (project_id) REFERENCES projects(project_id)
                    ON DELETE CASCADE
            );
        """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_consolidation_runs_project_id
            ON consolidation_runs(project_id);
        """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_consolidation_runs_started_at
            ON consolidation_runs(started_at DESC);
        """
        )

        self.db.conn.commit()

    def create_run(self, project_id: int, config: Optional[Dict[str, Any]] = None) -> int:
        """Create a new consolidation run record.

        Args:
            project_id: Project ID
            config: Optional configuration dict

        Returns:
            run_id of the new run
        """
        config_json = json.dumps(config or {})

        self.db.execute(
            """
            INSERT INTO consolidation_runs
            (project_id, status, config, started_at)
            VALUES (%s, %s, %s, NOW())
        """,
            (project_id, ConsolidationStatus.RUNNING.value, config_json),
        )

        # Get the inserted ID
        result = self.db.execute(
            """
            SELECT run_id FROM consolidation_runs
            WHERE project_id = %s
            ORDER BY started_at DESC
            LIMIT 1
        """,
            (project_id,),
            fetch_one=True,
        )

        run_id = result[0] if result else None
        if run_id:
            self.db.conn.commit()
            logger.info(f"Created consolidation run {run_id} for project {project_id}")

        return run_id

    def update_run(self, run_id: int, metrics: ConsolidationRunMetrics) -> bool:
        """Update a consolidation run with metrics.

        Args:
            run_id: Run ID to update
            metrics: ConsolidationRunMetrics with updated values

        Returns:
            True if successful, False otherwise
        """
        try:
            error_messages_json = (
                json.dumps(metrics.error_messages) if metrics.error_messages else None
            )
            config_json = json.dumps(metrics.config) if metrics.config else None

            self.db.execute(
                """
                UPDATE consolidation_runs
                SET
                    completed_at = %s,
                    status = %s,
                    events_processed = %s,
                    events_consolidated = %s,
                    patterns_extracted = %s,
                    patterns_validated = %s,
                    memories_created = %s,
                    quality_before = %s,
                    quality_after = %s,
                    throughput_events_per_sec = %s,
                    avg_pattern_confidence = %s,
                    errors = %s,
                    error_messages = %s,
                    config = %s,
                    notes = %s
                WHERE run_id = %s
            """,
                (
                    metrics.completed_at,
                    metrics.status.value,
                    metrics.events_processed,
                    metrics.events_consolidated,
                    metrics.patterns_extracted,
                    metrics.patterns_validated,
                    metrics.memories_created,
                    metrics.quality_before,
                    metrics.quality_after,
                    metrics.throughput_events_per_sec,
                    metrics.avg_pattern_confidence,
                    metrics.errors,
                    error_messages_json,
                    config_json,
                    metrics.notes,
                    run_id,
                ),
            )

            self.db.conn.commit()
            logger.debug(f"Updated consolidation run {run_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update run {run_id}: {e}")
            return False

    def get_run(self, run_id: int) -> Optional[ConsolidationRunMetrics]:
        """Get a specific consolidation run.

        Args:
            run_id: Run ID

        Returns:
            ConsolidationRunMetrics or None
        """
        try:
            result = self.db.execute(
                """
                SELECT
                    run_id, project_id, started_at, completed_at, status,
                    events_processed, events_consolidated,
                    patterns_extracted, patterns_validated, memories_created,
                    quality_before, quality_after,
                    throughput_events_per_sec, avg_pattern_confidence,
                    errors, error_messages, config, notes
                FROM consolidation_runs
                WHERE run_id = %s
            """,
                (run_id,),
                fetch_one=True,
            )

            if not result:
                return None

            return self._row_to_metrics(result)

        except Exception as e:
            logger.error(f"Failed to get run {run_id}: {e}")
            return None

    def get_recent_runs(
        self,
        project_id: int,
        limit: int = 10,
        days: int = 30,
    ) -> List[ConsolidationRunMetrics]:
        """Get recent consolidation runs for a project.

        Args:
            project_id: Project ID
            limit: Max results (default: 10)
            days: Look back (default: 30 days)

        Returns:
            List of ConsolidationRunMetrics, sorted by date descending
        """
        try:
            results = self.db.execute(
                """
                SELECT
                    run_id, project_id, started_at, completed_at, status,
                    events_processed, events_consolidated,
                    patterns_extracted, patterns_validated, memories_created,
                    quality_before, quality_after,
                    throughput_events_per_sec, avg_pattern_confidence,
                    errors, error_messages, config, notes
                FROM consolidation_runs
                WHERE project_id = %s
                  AND started_at > NOW() - INTERVAL '%s days'
                ORDER BY started_at DESC
                LIMIT %s
            """,
                (project_id, days, limit),
                fetch_all=True,
            )

            return [self._row_to_metrics(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get recent runs: {e}")
            return []

    def get_run_statistics(self, project_id: int, days: int = 30) -> Dict[str, Any]:
        """Get aggregate statistics for recent runs.

        Args:
            project_id: Project ID
            days: Look back period (default: 30 days)

        Returns:
            Dictionary with aggregate stats
        """
        try:
            result = self.db.execute(
                """
                SELECT
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
                    AVG(events_processed) as avg_events_processed,
                    SUM(patterns_extracted) as total_patterns_extracted,
                    AVG(quality_after - quality_before) as avg_quality_improvement,
                    AVG(throughput_events_per_sec) as avg_throughput,
                    SUM(errors) as total_errors,
                    MAX(completed_at) as last_run_time
                FROM consolidation_runs
                WHERE project_id = %s
                  AND started_at > NOW() - INTERVAL '%s days'
            """,
                (project_id, days),
                fetch_one=True,
            )

            if not result:
                return {}

            return {
                "total_runs": result[0] or 0,
                "successful_runs": result[1] or 0,
                "failed_runs": result[2] or 0,
                "avg_events_processed": float(result[3] or 0),
                "total_patterns_extracted": result[4] or 0,
                "avg_quality_improvement": float(result[5] or 0),
                "avg_throughput": float(result[6] or 0),
                "total_errors": result[7] or 0,
                "last_run_time": result[8].isoformat() if result[8] else None,
                "success_rate": (result[1] or 0) / (result[0] or 1),
            }

        except Exception as e:
            logger.error(f"Failed to get run statistics: {e}")
            return {}

    def _row_to_metrics(self, row: tuple) -> ConsolidationRunMetrics:
        """Convert database row to ConsolidationRunMetrics."""
        (
            run_id,
            project_id,
            started_at,
            completed_at,
            status,
            events_processed,
            events_consolidated,
            patterns_extracted,
            patterns_validated,
            memories_created,
            quality_before,
            quality_after,
            throughput,
            confidence,
            errors,
            error_messages_json,
            config_json,
            notes,
        ) = row

        error_messages = []
        if error_messages_json:
            try:
                error_messages = json.loads(error_messages_json)
            except json.JSONDecodeError:
                error_messages = [error_messages_json]

        config = {}
        if config_json:
            try:
                config = json.loads(config_json)
            except json.JSONDecodeError:
                pass

        return ConsolidationRunMetrics(
            run_id=run_id,
            project_id=project_id,
            started_at=started_at,
            completed_at=completed_at,
            status=ConsolidationStatus(status),
            events_processed=events_processed or 0,
            events_consolidated=events_consolidated or 0,
            patterns_extracted=patterns_extracted or 0,
            patterns_validated=patterns_validated or 0,
            memories_created=memories_created or 0,
            quality_before=quality_before or 0.0,
            quality_after=quality_after or 0.0,
            throughput_events_per_sec=throughput or 0.0,
            avg_pattern_confidence=confidence or 0.0,
            errors=errors or 0,
            error_messages=error_messages,
            config=config,
            notes=notes or "",
        )
