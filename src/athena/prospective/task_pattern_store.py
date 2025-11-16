"""Task pattern storage and analysis."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .task_patterns import (
    TaskPattern,
    TaskExecutionMetrics,
    TaskPropertyCorrelation,
    PatternType,
    ExtractionMethod,
    PatternStatus,
)

logger = logging.getLogger(__name__)


class TaskPatternStore(BaseStore):
    """Manages task patterns and execution metrics."""

    table_name = "task_patterns"  # Primary table for base_store compatibility
    model_class = TaskPattern

    def __init__(self, db: Database):
        """Initialize task pattern store.

        Args:
            db: Database instance
        """
        super().__init__(db)

    def _row_to_model(self, row: Dict[str, Any]) -> TaskPattern:
        """Convert database row to TaskPattern model."""
        if isinstance(row, dict):
            return TaskPattern(**row)
        return TaskPattern(**dict(row))

    def _ensure_schema(self):
        """Ensure all task pattern tables exist."""
        if not hasattr(self.db, "conn"):
            logger.debug(
                f"{self.__class__.__name__}: PostgreSQL async database detected. "
                "Schema management handled by _init_schema()."
            )
            return

        cursor = self.db.get_cursor()

        # Task patterns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_patterns (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,

                -- Pattern Identity
                pattern_name VARCHAR(255) NOT NULL,
                pattern_type VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,

                -- Pattern Extraction
                condition_json JSONB NOT NULL,
                prediction TEXT NOT NULL,

                -- Validation
                sample_size INTEGER DEFAULT 1,
                confidence_score REAL NOT NULL,
                success_rate REAL NOT NULL,
                failure_count INTEGER DEFAULT 0,

                -- Lifecycle
                status VARCHAR(20) DEFAULT 'active',
                extraction_method VARCHAR(50) NOT NULL,
                system_2_validated BOOLEAN DEFAULT FALSE,
                validation_notes TEXT,

                -- Metadata
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                last_validated_at BIGINT,

                -- Relationships
                learned_from_tasks JSONB DEFAULT '[]',
                related_patterns JSONB DEFAULT '[]',

                CONSTRAINT pattern_type_check CHECK (
                    pattern_type IN ('duration', 'success_rate', 'phase_correlation', 'property_correlation')
                ),
                CONSTRAINT status_check CHECK (
                    status IN ('active', 'deprecated', 'archived')
                )
            )
        """
        )

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_patterns_project
            ON task_patterns(project_id)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_patterns_status
            ON task_patterns(status)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_patterns_confidence
            ON task_patterns(confidence_score DESC)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_patterns_type
            ON task_patterns(pattern_type)
        """
        )

        # Task execution metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_execution_metrics (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL REFERENCES prospective_tasks(id) ON DELETE CASCADE,

                -- Time Tracking
                estimated_total_minutes INTEGER NOT NULL,
                actual_total_minutes REAL NOT NULL,
                estimation_error_percent REAL,

                -- Phase Breakdown
                planning_phase_minutes REAL DEFAULT 0,
                plan_ready_phase_minutes REAL DEFAULT 0,
                executing_phase_minutes REAL DEFAULT 0,
                verifying_phase_minutes REAL DEFAULT 0,

                -- Success
                success BOOLEAN NOT NULL DEFAULT TRUE,
                failure_mode TEXT,

                -- Task Properties
                priority VARCHAR(20) DEFAULT 'medium',
                complexity_estimate INTEGER,
                dependencies_count INTEGER DEFAULT 0,
                has_blockers BOOLEAN DEFAULT FALSE,

                -- Execution Quality
                retries_count INTEGER DEFAULT 0,
                external_blockers BOOLEAN DEFAULT FALSE,
                scope_change BOOLEAN DEFAULT FALSE,

                -- Metadata
                completed_at BIGINT NOT NULL,
                created_at BIGINT NOT NULL,

                CONSTRAINT priority_check CHECK (
                    priority IN ('low', 'medium', 'high', 'critical')
                )
            )
        """
        )

        # Create indexes for metrics
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_execution_metrics_task
            ON task_execution_metrics(task_id)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_execution_metrics_success
            ON task_execution_metrics(success)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_execution_metrics_priority
            ON task_execution_metrics(priority)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_execution_metrics_completed
            ON task_execution_metrics(completed_at DESC)
        """
        )

        # Task property correlations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_property_correlations (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,

                -- Property Analysis
                property_name VARCHAR(100) NOT NULL,
                property_value VARCHAR(255) NOT NULL,

                -- Metrics
                total_tasks INTEGER NOT NULL DEFAULT 1,
                successful_tasks INTEGER NOT NULL DEFAULT 0,
                failed_tasks INTEGER NOT NULL DEFAULT 0,
                success_rate REAL NOT NULL,

                -- Statistics
                sample_size INTEGER NOT NULL DEFAULT 1,
                confidence_level REAL,
                p_value REAL,

                -- Time Correlation
                avg_estimated_minutes REAL DEFAULT 0,
                avg_actual_minutes REAL DEFAULT 0,
                estimation_accuracy_percent REAL DEFAULT 0,

                -- Metadata
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                last_analyzed BIGINT NOT NULL,

                UNIQUE (project_id, property_name, property_value)
            )
        """
        )

        # Create indexes for correlations
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_property_correlations_project
            ON task_property_correlations(project_id)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_property_correlations_property
            ON task_property_correlations(property_name)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_property_correlations_success
            ON task_property_correlations(success_rate DESC)
        """
        )

        self.db.conn.commit()

    # ============================================================================
    # TaskPattern Operations
    # ============================================================================

    def save_pattern(self, pattern: TaskPattern) -> int:
        """Save or update a task pattern.

        Args:
            pattern: TaskPattern to save

        Returns:
            Pattern ID
        """
        cursor = self.db.get_cursor()

        now = int(datetime.now().timestamp() * 1000)
        pattern.updated_at = datetime.fromtimestamp(now / 1000)

        if pattern.id:
            # Update existing
            cursor.execute(
                """
                UPDATE task_patterns
                SET pattern_name = %s,
                    pattern_type = %s,
                    description = %s,
                    condition_json = %s,
                    prediction = %s,
                    sample_size = %s,
                    confidence_score = %s,
                    success_rate = %s,
                    failure_count = %s,
                    status = %s,
                    extraction_method = %s,
                    system_2_validated = %s,
                    validation_notes = %s,
                    updated_at = %s,
                    last_validated_at = %s,
                    learned_from_tasks = %s,
                    related_patterns = %s
                WHERE id = %s
            """,
                (
                    pattern.pattern_name,
                    pattern.pattern_type,
                    pattern.description,
                    pattern.condition_json,
                    pattern.prediction,
                    pattern.sample_size,
                    pattern.confidence_score,
                    pattern.success_rate,
                    pattern.failure_count,
                    pattern.status,
                    pattern.extraction_method,
                    pattern.system_2_validated,
                    pattern.validation_notes,
                    now,
                    int(pattern.last_validated_at.timestamp() * 1000)
                    if pattern.last_validated_at
                    else None,
                    pattern.learned_from_tasks,
                    pattern.related_patterns,
                    pattern.id,
                ),
            )
        else:
            # Insert new
            created_at = int(pattern.created_at.timestamp() * 1000)
            cursor.execute(
                """
                INSERT INTO task_patterns
                (project_id, pattern_name, pattern_type, description, condition_json, prediction,
                 sample_size, confidence_score, success_rate, failure_count, status, extraction_method,
                 system_2_validated, validation_notes, created_at, updated_at, last_validated_at,
                 learned_from_tasks, related_patterns)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    pattern.project_id,
                    pattern.pattern_name,
                    pattern.pattern_type,
                    pattern.description,
                    pattern.condition_json,
                    pattern.prediction,
                    pattern.sample_size,
                    pattern.confidence_score,
                    pattern.success_rate,
                    pattern.failure_count,
                    pattern.status,
                    pattern.extraction_method,
                    pattern.system_2_validated,
                    pattern.validation_notes,
                    created_at,
                    now,
                    int(pattern.last_validated_at.timestamp() * 1000)
                    if pattern.last_validated_at
                    else None,
                    pattern.learned_from_tasks,
                    pattern.related_patterns,
                ),
            )
            pattern.id = cursor.fetchone()[0]

        self.db.conn.commit()
        return pattern.id

    def get_pattern(self, pattern_id: int) -> Optional[TaskPattern]:
        """Get a task pattern by ID."""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM task_patterns WHERE id = %s", (pattern_id,))
        row = cursor.fetchone()
        return self._row_to_model(dict(row)) if row else None

    def get_patterns_by_project(
        self,
        project_id: int,
        status: Optional[str] = None,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[TaskPattern]:
        """Get patterns for a project with filtering.

        Args:
            project_id: Project ID
            status: Optional status filter (active, deprecated, archived)
            pattern_type: Optional type filter
            min_confidence: Minimum confidence score (default 0.0)

        Returns:
            List of TaskPattern objects
        """
        cursor = self.db.get_cursor()

        query = "SELECT * FROM task_patterns WHERE project_id = %s AND confidence_score >= %s"
        params = [project_id, min_confidence]

        if status:
            query += " AND status = %s"
            params.append(status)

        if pattern_type:
            query += " AND pattern_type = %s"
            params.append(pattern_type)

        query += " ORDER BY confidence_score DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    def get_active_patterns(self, project_id: int) -> List[TaskPattern]:
        """Get all active patterns for a project."""
        return self.get_patterns_by_project(project_id, status=PatternStatus.ACTIVE)

    # ============================================================================
    # TaskExecutionMetrics Operations
    # ============================================================================

    def save_execution_metrics(self, metrics: TaskExecutionMetrics) -> int:
        """Save execution metrics for a completed task.

        Args:
            metrics: TaskExecutionMetrics to save

        Returns:
            Metrics ID
        """
        cursor = self.db.get_cursor()

        completed_at = int(metrics.completed_at.timestamp() * 1000)
        created_at = int(metrics.created_at.timestamp() * 1000)

        # Calculate estimation error if not provided
        if metrics.estimation_error_percent is None:
            metrics.estimation_error_percent = (
                (metrics.actual_total_minutes - metrics.estimated_total_minutes)
                / metrics.estimated_total_minutes
                * 100
            )

        cursor.execute(
            """
            INSERT INTO task_execution_metrics
            (task_id, estimated_total_minutes, actual_total_minutes, estimation_error_percent,
             planning_phase_minutes, plan_ready_phase_minutes, executing_phase_minutes,
             verifying_phase_minutes, success, failure_mode, priority, complexity_estimate,
             dependencies_count, has_blockers, retries_count, external_blockers, scope_change,
             completed_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                metrics.task_id,
                metrics.estimated_total_minutes,
                metrics.actual_total_minutes,
                metrics.estimation_error_percent,
                metrics.planning_phase_minutes,
                metrics.plan_ready_phase_minutes,
                metrics.executing_phase_minutes,
                metrics.verifying_phase_minutes,
                metrics.success,
                metrics.failure_mode,
                metrics.priority,
                metrics.complexity_estimate,
                metrics.dependencies_count,
                metrics.has_blockers,
                metrics.retries_count,
                metrics.external_blockers,
                metrics.scope_change,
                completed_at,
                created_at,
            ),
        )

        metrics.id = cursor.fetchone()[0]
        self.db.conn.commit()
        return metrics.id

    def get_execution_metrics(self, task_id: int) -> Optional[TaskExecutionMetrics]:
        """Get execution metrics for a task."""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM task_execution_metrics WHERE task_id = %s", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        data["completed_at"] = datetime.fromtimestamp(data["completed_at"] / 1000)
        return TaskExecutionMetrics(**data)

    def get_recent_metrics(
        self, project_id: int, limit: int = 100
    ) -> List[TaskExecutionMetrics]:
        """Get recent execution metrics for analysis.

        Args:
            project_id: Project ID
            limit: Maximum number of metrics to return

        Returns:
            List of TaskExecutionMetrics, most recent first
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT m.*
            FROM task_execution_metrics m
            JOIN prospective_tasks t ON m.task_id = t.id
            WHERE t.project_id = %s
            ORDER BY m.completed_at DESC
            LIMIT %s
        """,
            (project_id, limit),
        )

        rows = cursor.fetchall()
        metrics = []
        for row in rows:
            data = dict(row)
            data["completed_at"] = datetime.fromtimestamp(data["completed_at"] / 1000)
            metrics.append(TaskExecutionMetrics(**data))

        return metrics

    # ============================================================================
    # TaskPropertyCorrelation Operations
    # ============================================================================

    def save_correlation(self, correlation: TaskPropertyCorrelation) -> int:
        """Save or update a property correlation."""
        cursor = self.db.get_cursor()

        now = int(datetime.now().timestamp() * 1000)

        if correlation.id:
            cursor.execute(
                """
                UPDATE task_property_correlations
                SET total_tasks = %s,
                    successful_tasks = %s,
                    failed_tasks = %s,
                    success_rate = %s,
                    sample_size = %s,
                    confidence_level = %s,
                    p_value = %s,
                    avg_estimated_minutes = %s,
                    avg_actual_minutes = %s,
                    estimation_accuracy_percent = %s,
                    updated_at = %s,
                    last_analyzed = %s
                WHERE id = %s
            """,
                (
                    correlation.total_tasks,
                    correlation.successful_tasks,
                    correlation.failed_tasks,
                    correlation.success_rate,
                    correlation.sample_size,
                    correlation.confidence_level,
                    correlation.p_value,
                    correlation.avg_estimated_minutes,
                    correlation.avg_actual_minutes,
                    correlation.estimation_accuracy_percent,
                    now,
                    now,
                    correlation.id,
                ),
            )
        else:
            created_at = int(correlation.created_at.timestamp() * 1000)
            cursor.execute(
                """
                INSERT INTO task_property_correlations
                (project_id, property_name, property_value, total_tasks, successful_tasks,
                 failed_tasks, success_rate, sample_size, confidence_level, p_value,
                 avg_estimated_minutes, avg_actual_minutes, estimation_accuracy_percent,
                 created_at, updated_at, last_analyzed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, property_name, property_value)
                DO UPDATE SET
                    total_tasks = EXCLUDED.total_tasks,
                    successful_tasks = EXCLUDED.successful_tasks,
                    failed_tasks = EXCLUDED.failed_tasks,
                    success_rate = EXCLUDED.success_rate,
                    sample_size = EXCLUDED.sample_size,
                    confidence_level = EXCLUDED.confidence_level,
                    p_value = EXCLUDED.p_value,
                    avg_estimated_minutes = EXCLUDED.avg_estimated_minutes,
                    avg_actual_minutes = EXCLUDED.avg_actual_minutes,
                    estimation_accuracy_percent = EXCLUDED.estimation_accuracy_percent,
                    updated_at = %s,
                    last_analyzed = %s
                RETURNING id
            """,
                (
                    correlation.project_id,
                    correlation.property_name,
                    correlation.property_value,
                    correlation.total_tasks,
                    correlation.successful_tasks,
                    correlation.failed_tasks,
                    correlation.success_rate,
                    correlation.sample_size,
                    correlation.confidence_level,
                    correlation.p_value,
                    correlation.avg_estimated_minutes,
                    correlation.avg_actual_minutes,
                    correlation.estimation_accuracy_percent,
                    created_at,
                    now,
                    now,
                    now,
                ),
            )
            correlation.id = cursor.fetchone()[0]

        self.db.conn.commit()
        return correlation.id

    def get_correlations_for_property(
        self, project_id: int, property_name: str
    ) -> List[TaskPropertyCorrelation]:
        """Get all correlations for a specific property."""
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM task_property_correlations
            WHERE project_id = %s AND property_name = %s
            ORDER BY success_rate DESC
        """,
            (project_id, property_name),
        )

        rows = cursor.fetchall()
        return [TaskPropertyCorrelation(**dict(row)) for row in rows]

    def get_high_confidence_correlations(
        self, project_id: int, min_confidence: float = 0.8
    ) -> List[TaskPropertyCorrelation]:
        """Get correlations with high statistical confidence."""
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM task_property_correlations
            WHERE project_id = %s AND confidence_level >= %s
            ORDER BY confidence_level DESC, success_rate DESC
        """,
            (project_id, min_confidence),
        )

        rows = cursor.fetchall()
        return [TaskPropertyCorrelation(**dict(row)) for row in rows]
