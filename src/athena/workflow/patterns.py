"""Workflow Pattern Mining and Analysis - Phase 3b.

Discovers implicit patterns from completed task sequences.
Suggests next tasks based on historical workflows.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict

from ..core.database import Database
from ..core.base_store import BaseStore

logger = logging.getLogger(__name__)


class WorkflowPatternStore(BaseStore):
    """Stores and retrieves workflow patterns mined from completed tasks."""

    table_name = "workflow_patterns"

    def __init__(self, db: Database):
        """Initialize pattern store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure workflow pattern tables exist."""
        if not hasattr(self.db, "get_cursor"):
            logger.debug("Async database detected, skipping sync schema")
            return

        cursor = self.db.get_cursor()

        # Main patterns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_patterns (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                from_task_type VARCHAR(50),
                to_task_type VARCHAR(50),
                frequency INTEGER DEFAULT 1,
                confidence FLOAT DEFAULT 0.0,
                avg_duration_hours FLOAT DEFAULT 0.0,
                std_dev_duration FLOAT DEFAULT 0.0,
                last_occurrence TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, from_task_type, to_task_type)
            )
        """
        )

        # Task type workflows table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_type_workflows (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                task_type VARCHAR(50),
                workflow_sequence TEXT,
                confidence_avg FLOAT DEFAULT 0.0,
                avg_total_duration_hours FLOAT DEFAULT 0.0,
                task_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, task_type)
            )
        """
        )

        self.db.commit()

    def store_pattern(
        self,
        project_id: int,
        from_type: str,
        to_type: str,
        duration_hours: float = 0.0,
    ) -> bool:
        """Record a task transition pattern.

        Args:
            project_id: Project ID
            from_type: Task type that completed
            to_type: Task type that followed
            duration_hours: Hours between completion

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                INSERT INTO workflow_patterns
                (project_id, from_task_type, to_task_type, frequency, last_occurrence)
                VALUES (%s, %s, %s, 1, %s)
                ON CONFLICT (project_id, from_task_type, to_task_type)
                DO UPDATE SET
                    frequency = frequency + 1,
                    last_occurrence = EXCLUDED.last_occurrence
                """,
                (project_id, from_type, to_type, datetime.now()),
            )

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store pattern: {e}")
            return False

    def calculate_confidence(self, project_id: int) -> bool:
        """Calculate confidence scores for all patterns.

        Confidence = frequency / total occurrences of from_type

        Args:
            project_id: Project ID

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()

            # Get all patterns for this project
            cursor.execute(
                """
                SELECT from_task_type, to_task_type, frequency
                FROM workflow_patterns
                WHERE project_id = %s
                """,
                (project_id,),
            )

            patterns = cursor.fetchall()
            if not patterns:
                return True

            # Calculate totals for each from_type
            from_type_totals = defaultdict(int)
            for from_type, _, frequency in patterns:
                from_type_totals[from_type] += frequency

            # Update confidence for each pattern
            for from_type, to_type, frequency in patterns:
                total = from_type_totals[from_type]
                confidence = frequency / total if total > 0 else 0.0

                cursor.execute(
                    """
                    UPDATE workflow_patterns
                    SET confidence = %s
                    WHERE project_id = %s AND from_task_type = %s AND to_task_type = %s
                    """,
                    (confidence, project_id, from_type, to_type),
                )

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return False

    def get_successor_patterns(
        self, project_id: int, task_type: str, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """Get tasks that typically follow a given task type.

        Args:
            project_id: Project ID
            task_type: Task type to analyze
            limit: Max patterns to return

        Returns:
            List of successor patterns sorted by confidence
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT to_task_type, frequency, confidence, avg_duration_hours
                FROM workflow_patterns
                WHERE project_id = %s AND from_task_type = %s
                ORDER BY confidence DESC, frequency DESC
                LIMIT %s
                """,
                (project_id, task_type, limit),
            )

            rows = cursor.fetchall()
            if not rows:
                return None

            patterns = []
            for row in rows:
                patterns.append(
                    {
                        "task_type": row[0],
                        "frequency": row[1],
                        "confidence": round(row[2], 3) if row[2] else 0.0,
                        "avg_duration_hours": row[3],
                    }
                )

            return patterns
        except Exception as e:
            logger.error(f"Failed to get successor patterns: {e}")
            return None

    def get_predecessor_patterns(
        self, project_id: int, task_type: str, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """Get tasks that typically precede a given task type.

        Args:
            project_id: Project ID
            task_type: Task type to analyze
            limit: Max patterns to return

        Returns:
            List of predecessor patterns sorted by confidence
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT from_task_type, frequency, confidence, avg_duration_hours
                FROM workflow_patterns
                WHERE project_id = %s AND to_task_type = %s
                ORDER BY confidence DESC, frequency DESC
                LIMIT %s
                """,
                (project_id, task_type, limit),
            )

            rows = cursor.fetchall()
            if not rows:
                return None

            patterns = []
            for row in rows:
                patterns.append(
                    {
                        "task_type": row[0],
                        "frequency": row[1],
                        "confidence": round(row[2], 3) if row[2] else 0.0,
                        "avg_duration_hours": row[3],
                    }
                )

            return patterns
        except Exception as e:
            logger.error(f"Failed to get predecessor patterns: {e}")
            return None

    def store_workflow_sequence(
        self,
        project_id: int,
        task_type: str,
        sequence: List[str],
        confidence_avg: float = 0.0,
        avg_duration: float = 0.0,
        task_count: int = 0,
    ) -> bool:
        """Store a typical workflow sequence for a task type.

        Args:
            project_id: Project ID
            task_type: Task type (e.g., 'feature', 'bug')
            sequence: Ordered list of task types in workflow
            confidence_avg: Average confidence of sequence steps
            avg_duration: Average total duration in hours
            task_count: Number of completed tasks of this type

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()

            sequence_json = json.dumps(sequence)

            cursor.execute(
                """
                INSERT INTO task_type_workflows
                (project_id, task_type, workflow_sequence, confidence_avg,
                 avg_total_duration_hours, task_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, task_type)
                DO UPDATE SET
                    workflow_sequence = EXCLUDED.workflow_sequence,
                    confidence_avg = EXCLUDED.confidence_avg,
                    avg_total_duration_hours = EXCLUDED.avg_total_duration_hours,
                    task_count = EXCLUDED.task_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (project_id, task_type, sequence_json, confidence_avg, avg_duration, task_count),
            )

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store workflow sequence: {e}")
            return False

    def get_workflow_sequence(self, project_id: int, task_type: str) -> Optional[Dict[str, Any]]:
        """Get typical workflow sequence for a task type.

        Args:
            project_id: Project ID
            task_type: Task type

        Returns:
            Workflow sequence dict or None
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT workflow_sequence, confidence_avg, avg_total_duration_hours, task_count
                FROM task_type_workflows
                WHERE project_id = %s AND task_type = %s
                """,
                (project_id, task_type),
            )

            row = cursor.fetchone()
            if not row:
                return None

            sequence = json.loads(row[0]) if row[0] else []

            return {
                "task_type": task_type,
                "workflow_sequence": sequence,
                "confidence_avg": round(row[1], 3) if row[1] else 0.0,
                "avg_duration_hours": row[2],
                "task_count": row[3],
            }
        except Exception as e:
            logger.error(f"Failed to get workflow sequence: {e}")
            return None

    def find_anomalies(
        self, project_id: int, confidence_threshold: float = 0.1
    ) -> Optional[List[Dict[str, Any]]]:
        """Find unusual workflow patterns (low confidence transitions).

        Args:
            project_id: Project ID
            confidence_threshold: Confidence threshold (default: 0.1 = 10%)

        Returns:
            List of anomalous patterns
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT from_task_type, to_task_type, frequency, confidence
                FROM workflow_patterns
                WHERE project_id = %s AND confidence < %s AND frequency > 0
                ORDER BY confidence ASC, frequency DESC
                """,
                (project_id, confidence_threshold),
            )

            rows = cursor.fetchall()
            if not rows:
                return None

            anomalies = []
            for row in rows:
                anomalies.append(
                    {
                        "from_type": row[0],
                        "to_type": row[1],
                        "frequency": row[2],
                        "confidence": round(row[3], 3),
                        "message": f"{row[0]} → {row[1]} occurs {row[2]}x "
                        f"({row[3]:.1%} of {row[0]} tasks)",
                    }
                )

            return anomalies
        except Exception as e:
            logger.error(f"Failed to find anomalies: {e}")
            return None

    def get_all_patterns(self, project_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get all workflow patterns for a project.

        Args:
            project_id: Project ID

        Returns:
            List of all patterns
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT from_task_type, to_task_type, frequency, confidence,
                       avg_duration_hours, last_occurrence
                FROM workflow_patterns
                WHERE project_id = %s
                ORDER BY confidence DESC, frequency DESC
                """,
                (project_id,),
            )

            rows = cursor.fetchall()
            if not rows:
                return None

            patterns = []
            for row in rows:
                patterns.append(
                    {
                        "from_type": row[0],
                        "to_type": row[1],
                        "frequency": row[2],
                        "confidence": round(row[3], 3) if row[3] else 0.0,
                        "avg_duration_hours": row[4],
                        "last_occurrence": row[5],
                    }
                )

            return patterns
        except Exception as e:
            logger.error(f"Failed to get all patterns: {e}")
            return None
