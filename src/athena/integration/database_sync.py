"""Database Layer for TodoWrite ↔ Athena Sync

Provides database operations for storing and retrieving plans created from TodoWrite todos.
Extends the existing planning store with TodoWrite-specific functionality.

This module handles:
- Storing plans created from todos
- Retrieving plans by todo mapping
- Updating plan status from todo changes
- Syncing bidirectionally with database

Database Schema: todowrite_plans table
- Stores plans created/managed via TodoWrite
- Maintains mapping between todo_id and plan_id
- Tracks sync state and last update time
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core.database import Database

logger = logging.getLogger(__name__)


class TodoWritePlanStore:
    """Database store for TodoWrite-synced plans.

    Manages persistence of plans created from TodoWrite todos,
    including mappings and sync state tracking.
    """

    def __init__(self, db: Database):
        """Initialize the TodoWrite plan store.

        Args:
            db: Database instance
        """
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure the todowrite_plans table exists.

        Creates table with schema for storing plans synced from TodoWrite.
        Idempotent - safe to call multiple times.
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todowrite_plans (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,

                -- TodoWrite mapping
                todo_id VARCHAR(255) UNIQUE NOT NULL,
                plan_id VARCHAR(255) UNIQUE NOT NULL,

                -- Plan content
                goal TEXT NOT NULL,
                description TEXT,

                -- Status and phase
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                phase INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 5,

                -- Metadata
                tags TEXT,  -- JSON array of strings
                steps TEXT,  -- JSON array of steps
                assumptions TEXT,  -- JSON array
                risks TEXT,  -- JSON array

                -- Sync tracking
                last_synced_at INTEGER,
                sync_status VARCHAR(50) DEFAULT 'pending',  -- pending, synced, conflict
                sync_conflict_reason TEXT,

                -- Original todo
                original_todo TEXT,  -- JSON object

                -- Timestamps
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                INDEX idx_todo_id (todo_id),
                INDEX idx_plan_id (plan_id),
                INDEX idx_project_id (project_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            )
        """)

        cursor.close()

    async def store_plan_from_todo(
        self,
        todo_id: str,
        plan: Dict[str, Any],
        project_id: int = 1,
    ) -> Tuple[bool, str]:
        """Store a plan created from a TodoWrite todo.

        Args:
            todo_id: TodoWrite todo ID
            plan: Plan dict from todowrite_sync.convert_todo_to_plan()
            project_id: Project ID

        Returns:
            (success, plan_id or error_message)
        """
        try:
            plan_id = plan.get("id", f"plan_{todo_id}_{int(datetime.now().timestamp())}")
            goal = plan.get("goal", "")
            description = plan.get("description", "")
            status = plan.get("status", "pending")
            phase = plan.get("phase", 1)
            priority = plan.get("priority", 5)

            now = int(datetime.now().timestamp())

            cursor = self.db.get_cursor()

            cursor.execute("""
                INSERT INTO todowrite_plans (
                    project_id, todo_id, plan_id, goal, description,
                    status, phase, priority,
                    tags, steps, assumptions, risks,
                    original_todo,
                    last_synced_at, sync_status,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                project_id,
                todo_id,
                plan_id,
                goal,
                description,
                status,
                phase,
                priority,
                json.dumps(plan.get("tags", [])),
                json.dumps(plan.get("steps", [])),
                json.dumps(plan.get("assumptions", [])),
                json.dumps(plan.get("risks", [])),
                json.dumps(plan.get("original_todo", {})),
                now,
                "synced",
                now,
                now,
            ))

            cursor.close()
            logger.info(f"Stored plan {plan_id} for todo {todo_id}")
            return True, plan_id

        except Exception as e:
            logger.error(f"Failed to store plan for todo {todo_id}: {e}")
            return False, str(e)

    async def get_plan_by_todo_id(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a plan by its todo ID.

        Args:
            todo_id: TodoWrite todo ID

        Returns:
            Plan dict or None if not found
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute("""
                SELECT * FROM todowrite_plans WHERE todo_id = %s
            """, (todo_id,))

            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get plan for todo {todo_id}: {e}")
            return None

    async def get_plan_by_plan_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a plan by its plan ID.

        Args:
            plan_id: Athena plan ID

        Returns:
            Plan dict or None if not found
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute("""
                SELECT * FROM todowrite_plans WHERE plan_id = %s
            """, (plan_id,))

            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get plan {plan_id}: {e}")
            return None

    async def update_plan_status(
        self,
        plan_id: str,
        status: str,
        phase: Optional[int] = None,
    ) -> bool:
        """Update plan status (and optionally phase).

        Args:
            plan_id: Athena plan ID
            status: New status
            phase: Optional new phase

        Returns:
            True if updated, False otherwise
        """
        try:
            now = int(datetime.now().timestamp())

            if phase is not None:
                query = """
                    UPDATE todowrite_plans
                    SET status = %s, phase = %s, updated_at = %s
                    WHERE plan_id = %s
                """
                params = (status, phase, now, plan_id)
            else:
                query = """
                    UPDATE todowrite_plans
                    SET status = %s, updated_at = %s
                    WHERE plan_id = %s
                """
                params = (status, now, plan_id)

            cursor = self.db.get_cursor()
            cursor.execute(query, params)
            cursor.close()

            logger.info(f"Updated plan {plan_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update plan {plan_id}: {e}")
            return False

    async def update_sync_status(
        self,
        plan_id: str,
        sync_status: str,
        conflict_reason: Optional[str] = None,
    ) -> bool:
        """Update sync status for a plan.

        Args:
            plan_id: Athena plan ID
            sync_status: New sync status (pending, synced, conflict)
            conflict_reason: Optional conflict reason

        Returns:
            True if updated, False otherwise
        """
        try:
            now = int(datetime.now().timestamp())

            cursor = self.db.get_cursor()

            cursor.execute("""
                UPDATE todowrite_plans
                SET sync_status = %s, sync_conflict_reason = %s,
                    last_synced_at = %s, updated_at = %s
                WHERE plan_id = %s
            """, (sync_status, conflict_reason, now, now, plan_id))

            cursor.close()

            logger.info(f"Updated plan {plan_id} sync status to {sync_status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update sync status for {plan_id}: {e}")
            return False

    async def list_plans_by_status(
        self,
        status: str,
        project_id: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List plans by status.

        Args:
            status: Filter by status
            project_id: Project ID
            limit: Maximum results

        Returns:
            List of plan dicts
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute("""
                SELECT * FROM todowrite_plans
                WHERE project_id = %s AND status = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (project_id, status, limit))

            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list plans by status {status}: {e}")
            return []

    async def list_plans_by_sync_status(
        self,
        sync_status: str,
        project_id: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List plans by sync status.

        Args:
            sync_status: Filter by sync status (pending, synced, conflict)
            project_id: Project ID
            limit: Maximum results

        Returns:
            List of plan dicts
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute("""
                SELECT * FROM todowrite_plans
                WHERE project_id = %s AND sync_status = %s
                ORDER BY updated_at DESC
                LIMIT %s
            """, (project_id, sync_status, limit))

            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list plans by sync status {sync_status}: {e}")
            return []

    async def get_sync_conflicts(
        self,
        project_id: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all plans with sync conflicts.

        Args:
            project_id: Project ID
            limit: Maximum results

        Returns:
            List of conflicted plan dicts
        """
        return await self.list_plans_by_sync_status("conflict", project_id, limit)

    async def get_pending_syncs(
        self,
        project_id: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all plans pending sync.

        Args:
            project_id: Project ID
            limit: Maximum results

        Returns:
            List of pending plan dicts
        """
        return await self.list_plans_by_sync_status("pending", project_id, limit)

    async def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan and its todo mapping.

        Args:
            plan_id: Athena plan ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute("""
                DELETE FROM todowrite_plans WHERE plan_id = %s
            """, (plan_id,))

            cursor.close()

            logger.info(f"Deleted plan {plan_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete plan {plan_id}: {e}")
            return False

    async def get_statistics(self, project_id: int = 1) -> Dict[str, Any]:
        """Get statistics about synced plans.

        Args:
            project_id: Project ID

        Returns:
            Statistics dict
        """
        try:
            cursor = self.db.get_cursor()

            # Total count
            cursor.execute("""
                SELECT COUNT(*) FROM todowrite_plans WHERE project_id = %s
            """, (project_id,))
            total = cursor.fetchone()[0]

            # By status
            cursor.execute("""
                SELECT status, COUNT(*) FROM todowrite_plans
                WHERE project_id = %s
                GROUP BY status
            """, (project_id,))
            by_status = {row[0]: row[1] for row in cursor.fetchall()}

            # By sync status
            cursor.execute("""
                SELECT sync_status, COUNT(*) FROM todowrite_plans
                WHERE project_id = %s
                GROUP BY sync_status
            """, (project_id,))
            by_sync_status = {row[0]: row[1] for row in cursor.fetchall()}

            # Conflicts
            cursor.execute("""
                SELECT COUNT(*) FROM todowrite_plans
                WHERE project_id = %s AND sync_status = 'conflict'
            """, (project_id,))
            conflicts = cursor.fetchone()[0]

            cursor.close()

            return {
                "total_plans": total,
                "by_status": by_status,
                "by_sync_status": by_sync_status,
                "conflicts": conflicts,
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "total_plans": 0,
                "by_status": {},
                "by_sync_status": {},
                "conflicts": 0,
                "error": str(e),
            }

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to plan dict.

        Args:
            row: Database row tuple

        Returns:
            Plan dict
        """
        return {
            "id": row[0],
            "project_id": row[1],
            "todo_id": row[2],
            "plan_id": row[3],
            "goal": row[4],
            "description": row[5],
            "status": row[6],
            "phase": row[7],
            "priority": row[8],
            "tags": json.loads(row[9]) if row[9] else [],
            "steps": json.loads(row[10]) if row[10] else [],
            "assumptions": json.loads(row[11]) if row[11] else [],
            "risks": json.loads(row[12]) if row[12] else [],
            "last_synced_at": row[13],
            "sync_status": row[14],
            "sync_conflict_reason": row[15],
            "original_todo": json.loads(row[16]) if row[16] else None,
            "created_at": row[17],
            "updated_at": row[18],
        }


# Global instance (lazy-initialized)
_store: Optional[TodoWritePlanStore] = None


def initialize(db: Database) -> None:
    """Initialize the global TodoWritePlanStore instance.

    Args:
        db: Database instance
    """
    global _store
    _store = TodoWritePlanStore(db)
    logger.info("TodoWritePlanStore initialized")


def get_store() -> TodoWritePlanStore:
    """Get the global TodoWritePlanStore instance.

    Returns:
        TodoWritePlanStore instance

    Raises:
        RuntimeError: If not initialized
    """
    if _store is None:
        raise RuntimeError(
            "TodoWritePlanStore not initialized. Call initialize(db) first."
        )
    return _store
