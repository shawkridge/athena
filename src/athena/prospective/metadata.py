"""Task metadata management - Athena prospective layer.

Enriches tasks with effort estimates, actual effort, complexity, and tags.
Part of Phase 3a: Task Dependencies + Metadata integration.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.database import Database
from ..core.base_store import BaseStore

logger = logging.getLogger(__name__)


class MetadataStore(BaseStore):
    """Manages task metadata within Athena prospective memory."""

    table_name = "prospective_tasks"

    def __init__(self, db: Database):
        """Initialize metadata store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure metadata columns exist on prospective_tasks."""
        if not hasattr(self.db, "get_cursor"):
            # Async database, schema handled elsewhere
            logger.debug("Async database detected, skipping sync schema")
            return

        cursor = self.db.get_cursor()

        # Add metadata columns if they don't exist
        metadata_columns = [
            ("effort_estimate", "INTEGER DEFAULT 0"),
            ("effort_actual", "INTEGER DEFAULT 0"),
            ("complexity_score", "INTEGER DEFAULT 5"),
            ("priority_score", "INTEGER DEFAULT 5"),
            ("tags", "TEXT DEFAULT '[]'"),
            ("started_at", "TIMESTAMP"),
            ("completed_at", "TIMESTAMP"),
        ]

        for col_name, col_def in metadata_columns:
            try:
                cursor.execute(f"ALTER TABLE prospective_tasks ADD COLUMN {col_name} {col_def}")
                logger.debug(f"Added column: {col_name}")
            except (OSError, ValueError, TypeError):
                # Column already exists, continue
                pass

        self.db.commit()

    def set_metadata(
        self,
        project_id: int,
        task_id: int,
        effort_estimate: Optional[int] = None,
        complexity_score: Optional[int] = None,
        priority_score: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Set task metadata.

        Args:
            project_id: Project ID
            task_id: Task ID
            effort_estimate: Estimated time in minutes
            complexity_score: 1-10 complexity rating
            priority_score: 1-10 priority rating
            tags: List of tags

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()

            # Build dynamic UPDATE
            set_clauses = []
            values = []

            if effort_estimate is not None:
                set_clauses.append("effort_estimate = %s")
                values.append(effort_estimate)

            if complexity_score is not None:
                if not (1 <= complexity_score <= 10):
                    logger.error("Complexity score must be 1-10")
                    return False
                set_clauses.append("complexity_score = %s")
                values.append(complexity_score)

            if priority_score is not None:
                if not (1 <= priority_score <= 10):
                    logger.error("Priority score must be 1-10")
                    return False
                set_clauses.append("priority_score = %s")
                values.append(priority_score)

            if tags is not None:
                tags_json = json.dumps(tags)
                set_clauses.append("tags = %s")
                values.append(tags_json)

            if not set_clauses:
                logger.warning("No metadata fields to update")
                return False

            # Execute update
            query = f"""
            UPDATE prospective_tasks
            SET {', '.join(set_clauses)}
            WHERE id = %s AND project_id = %s
            """

            values.extend([task_id, project_id])
            cursor.execute(query, values)
            self.db.commit()

            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to set metadata: {e}")
            return False

    def record_actual_effort(self, project_id: int, task_id: int, actual_minutes: int) -> bool:
        """Record actual effort spent on a task.

        Args:
            project_id: Project ID
            task_id: Task ID
            actual_minutes: Actual time spent in minutes

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()

            # Check if started_at is set
            cursor.execute(
                """
                SELECT started_at FROM prospective_tasks
                WHERE id = %s AND project_id = %s
                """,
                (task_id, project_id),
            )

            row = cursor.fetchone()
            if not row:
                logger.error(f"Task {task_id} not found")
                return False

            started_at = row[0] if row[0] else datetime.now()

            # Update actual effort
            cursor.execute(
                """
                UPDATE prospective_tasks
                SET effort_actual = %s, started_at = %s
                WHERE id = %s AND project_id = %s
                """,
                (actual_minutes, started_at, task_id, project_id),
            )

            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to record effort: {e}")
            return False

    def calculate_accuracy(self, project_id: int, task_id: int) -> Optional[Dict[str, Any]]:
        """Calculate estimate accuracy for a task.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Accuracy dict or None
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT effort_estimate, effort_actual
                FROM prospective_tasks
                WHERE id = %s AND project_id = %s
                """,
                (task_id, project_id),
            )

            row = cursor.fetchone()
            if not row:
                return None

            estimate = row[0] or 0
            actual = row[1] or 0

            if estimate == 0 or actual == 0:
                return None  # Can't calculate without both

            accuracy = 100 * min(estimate, actual) / max(estimate, actual)
            variance = actual - estimate

            return {
                "accuracy_percent": round(accuracy, 1),
                "variance_minutes": variance,
                "estimate": estimate,
                "actual": actual,
                "overestimated": variance < 0,
                "underestimated": variance > 0,
            }
        except Exception as e:
            logger.error(f"Failed to calculate accuracy: {e}")
            return None

    def get_task_metadata(self, project_id: int, task_id: int) -> Optional[Dict[str, Any]]:
        """Get all metadata for a task.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Metadata dict or None
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT
                    id, content, status,
                    effort_estimate, effort_actual,
                    complexity_score, priority_score,
                    tags, started_at, completed_at
                FROM prospective_tasks
                WHERE id = %s AND project_id = %s
                """,
                (task_id, project_id),
            )

            row = cursor.fetchone()
            if not row:
                return None

            tags = json.loads(row[7]) if row[7] else []

            metadata = {
                "id": row[0],
                "content": row[1],
                "status": row[2],
                "effort_estimate": row[3],
                "effort_actual": row[4],
                "complexity_score": row[5],
                "priority_score": row[6],
                "tags": tags,
                "started_at": row[8],
                "completed_at": row[9],
            }

            # Include accuracy if both estimate and actual are set
            accuracy = self.calculate_accuracy(project_id, task_id)
            if accuracy:
                metadata["accuracy"] = accuracy

            return metadata
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None

    def get_project_analytics(self, project_id: int) -> Dict[str, Any]:
        """Get aggregate analytics for all tasks in project.

        Args:
            project_id: Project ID

        Returns:
            Analytics dict with summary statistics
        """
        try:
            cursor = self.db.get_cursor()

            # Get all tasks with effort data
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN effort_estimate > 0 THEN 1 ELSE 0 END) as estimated_tasks,
                    SUM(CASE WHEN effort_actual > 0 THEN 1 ELSE 0 END) as tracked_tasks,
                    AVG(effort_estimate) as avg_estimate,
                    AVG(effort_actual) as avg_actual,
                    AVG(complexity_score) as avg_complexity,
                    MAX(complexity_score) as max_complexity,
                    MIN(complexity_score) as min_complexity
                FROM prospective_tasks
                WHERE project_id = %s AND status IN ('completed', 'in_progress')
                """,
                (project_id,),
            )

            row = cursor.fetchone()
            if not row or row[0] == 0:
                return {"error": "No tasks found"}

            total = row[0]
            estimated = row[1] or 0
            tracked = row[2] or 0

            analytics = {
                "total_tasks": total,
                "estimated_tasks": estimated,
                "tracked_tasks": tracked,
                "avg_estimate_minutes": round(row[3], 1) if row[3] else 0,
                "avg_actual_minutes": round(row[4], 1) if row[4] else 0,
                "avg_complexity": round(row[5], 1) if row[5] else 0,
                "complexity_range": (
                    int(row[7]) if row[7] else 1,
                    int(row[6]) if row[6] else 10,
                ),
            }

            # Calculate overall accuracy
            if estimated > 0 and tracked > 0:
                cursor.execute(
                    """
                    SELECT
                        AVG(
                            100 * LEAST(effort_estimate, effort_actual) /
                            GREATEST(effort_estimate, effort_actual)
                        ) as accuracy
                    FROM prospective_tasks
                    WHERE project_id = %s AND effort_estimate > 0 AND effort_actual > 0
                    """,
                    (project_id,),
                )

                accuracy_row = cursor.fetchone()
                if accuracy_row and accuracy_row[0]:
                    analytics["overall_accuracy_percent"] = round(accuracy_row[0], 1)

            return analytics
        except Exception as e:
            logger.error(f"Failed to get project analytics: {e}")
            return {"error": str(e)}

    def add_tags(self, project_id: int, task_id: int, tags: List[str]) -> bool:
        """Add tags to a task (non-destructive).

        Args:
            project_id: Project ID
            task_id: Task ID
            tags: Tags to add

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()

            # Get current tags
            cursor.execute(
                """
                SELECT tags FROM prospective_tasks
                WHERE id = %s AND project_id = %s
                """,
                (task_id, project_id),
            )

            row = cursor.fetchone()
            if not row:
                logger.error(f"Task {task_id} not found")
                return False

            current_tags = json.loads(row[0]) if row[0] else []

            # Add new tags (avoid duplicates)
            updated_tags = list(set(current_tags + tags))

            # Update
            cursor.execute(
                """
                UPDATE prospective_tasks
                SET tags = %s
                WHERE id = %s AND project_id = %s
                """,
                (json.dumps(updated_tags), task_id, project_id),
            )

            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to add tags: {e}")
            return False

    def set_completed_timestamp(self, project_id: int, task_id: int) -> bool:
        """Set completed_at timestamp.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()
            now = datetime.now()

            cursor.execute(
                """
                UPDATE prospective_tasks
                SET completed_at = %s
                WHERE id = %s AND project_id = %s
                """,
                (now, task_id, project_id),
            )

            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to set completion timestamp: {e}")
            return False
