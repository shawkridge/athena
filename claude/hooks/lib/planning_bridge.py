"""Synchronous bridge for planning and prospective memory operations.

This module provides direct database access to planning and task management,
similar to memory_bridge.py but for planning operations (create_plan, create_task).

This implements the same pattern as memory_bridge:
- Direct database access (no async complexity)
- Connection pooling for performance
- Local execution (no RPC overhead)
- Synchronous functions callable from hooks and CLI

Used by hooks and CLI tools to create plans and tasks without async setup.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

# Import connection pool for performance
from connection_pool import get_connection_pool, PooledConnection

# Configure logging
log_level = logging.DEBUG if os.environ.get('DEBUG') else logging.WARNING
logging.basicConfig(level=log_level, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class PlanningBridge:
    """Direct PostgreSQL bridge for planning operations.

    Provides synchronous access to:
    - create_plan: Create a hierarchical plan for a goal
    - create_task: Create a prospective task with optional dependencies
    - list_plans: List plans filtered by status
    - list_tasks: List tasks filtered by status
    - update_task_status: Update task status and progress
    """

    def __init__(self):
        """Initialize bridge with connection pool."""
        self.pool = get_connection_pool()

    def close(self):
        """Close (no-op for pooled connections)."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def create_plan(
        self,
        goal: str,
        description: str = "",
        depth: int = 3,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a plan for a goal.

        Decomposes a goal into hierarchical steps with effort estimates.
        Plans are stored as prospective_goals for future reference.

        Args:
            goal: Goal to plan for
            description: Additional context/description
            depth: Planning depth 1-5 (default: 3)
            tags: Optional tags for categorization

        Returns:
            Plan dict with id, goal, depth, tags, status
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get default project ID
                cursor.execute(
                    "SELECT id FROM projects WHERE name = 'default' LIMIT 1"
                )
                project_row = cursor.fetchone()
                project_id = project_row[0] if project_row else 1

                # Create plan as a prospective_goal
                now = int(datetime.now().timestamp())

                cursor.execute(
                    """
                    INSERT INTO prospective_goals
                    (project_id, name, description, status, priority,
                     estimated_completion_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        goal[:255],  # name - truncate long goals
                        description,
                        "active",  # status
                        3,  # priority (1=highest, 10=lowest, 5=medium, 3=high)
                        None,  # estimated_completion_date
                    ),
                )

                result = cursor.fetchone()
                plan_id = result[0] if result else None

                conn.commit()

                return {
                    "id": str(plan_id),
                    "goal": goal,
                    "description": description,
                    "depth": depth,
                    "tags": tags or [],
                    "status": "planning",
                    "created_at": datetime.fromtimestamp(now).isoformat(),
                }

        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            return {"error": str(e)}

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        status: str = "pending",
        due_date: Optional[datetime] = None,
        estimated_effort_hours: float = 0,
    ) -> Dict[str, Any]:
        """Create a prospective task.

        Creates a task in the prospective_tasks table for tracking goals
        and deliverables.

        Args:
            title: Task title
            description: Detailed description
            priority: Priority level (low, medium, high, critical)
            status: Initial status (pending, in_progress, completed, blocked)
            due_date: Optional due date
            estimated_effort_hours: Estimated effort in hours

        Returns:
            Task dict with id, title, status, created_at
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get default project ID
                cursor.execute(
                    "SELECT id FROM projects WHERE name = 'default' LIMIT 1"
                )
                project_row = cursor.fetchone()
                project_id = project_row[0] if project_row else 1

                # Map string priority to integer (medium=5)
                priority_map = {
                    "low": 8,
                    "medium": 5,
                    "high": 2,
                    "critical": 1,
                }
                priority_int = priority_map.get(priority.lower(), 5)

                due_date_obj = due_date.date() if due_date else None

                cursor.execute(
                    """
                    INSERT INTO prospective_tasks
                    (project_id, title, description, priority, status,
                     due_date, estimated_effort_hours)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (
                        project_id,
                        title,
                        description,
                        priority_int,
                        status,
                        due_date_obj,
                        estimated_effort_hours,
                    ),
                )

                result = cursor.fetchone()
                task_id = result[0] if result else None
                created_at = result[1] if result else None

                conn.commit()

                return {
                    "id": str(task_id),
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": status,
                    "due_date": due_date.isoformat() if due_date else None,
                    "estimated_effort_hours": estimated_effort_hours,
                    "created_at": created_at.isoformat() if created_at else None,
                }

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {"error": str(e)}

    def list_plans(
        self, status: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List plans, optionally filtered by status.

        Args:
            status: Optional status filter (planning, active, completed, failed)
            limit: Maximum plans to return

        Returns:
            List of plan dicts
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                if status:
                    cursor.execute(
                        """
                        SELECT id, name, description, status, created_at,
                               priority, completion_percentage, estimated_completion_date
                        FROM prospective_goals
                        WHERE status = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (status, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, name, description, status, created_at,
                               priority, completion_percentage, estimated_completion_date
                        FROM prospective_goals
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )

                rows = cursor.fetchall()
                plans = []
                for row in rows:
                    plans.append({
                        "id": str(row[0]),
                        "goal": row[1],
                        "description": row[2],
                        "status": row[3],
                        "created_at": row[4].isoformat() if row[4] else None,
                        "priority": row[5],
                        "completion_percentage": row[6],
                        "estimated_completion_date": row[7].isoformat() if row[7] else None,
                    })

                return plans

        except Exception as e:
            logger.error(f"Error listing plans: {e}")
            return []

    def list_tasks(
        self, status: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status.

        Args:
            status: Optional status filter (pending, in_progress, completed, blocked)
            limit: Maximum tasks to return

        Returns:
            List of task dicts
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                if status:
                    cursor.execute(
                        """
                        SELECT id, title, description, priority, status,
                               due_date, estimated_effort_hours, created_at
                        FROM prospective_tasks
                        WHERE status = %s
                        ORDER BY priority DESC, created_at DESC
                        LIMIT %s
                        """,
                        (status, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, title, description, priority, status,
                               due_date, estimated_effort_hours, created_at
                        FROM prospective_tasks
                        ORDER BY priority DESC, created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )

                rows = cursor.fetchall()
                tasks = []
                for row in rows:
                    # Map priority int to string
                    priority_map = {1: "critical", 2: "high", 5: "medium", 8: "low"}
                    priority_str = priority_map.get(row[3], "medium")

                    tasks.append({
                        "id": str(row[0]),
                        "title": row[1],
                        "description": row[2],
                        "priority": priority_str,
                        "status": row[4],
                        "due_date": row[5].isoformat() if row[5] else None,
                        "estimated_effort_hours": row[6],
                        "created_at": row[7].isoformat() if row[7] else None,
                    })

                return tasks

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []

    def update_task_status(
        self, task_id: str, status: str
    ) -> bool:
        """Update task status.

        Args:
            task_id: Task ID
            status: New status (pending, in_progress, completed, blocked)

        Returns:
            True if successful, False otherwise
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Update started_at if transitioning to in_progress
                started_at_sql = ""
                if status == "in_progress":
                    started_at_sql = ", started_at = now()"

                cursor.execute(
                    f"""
                    UPDATE prospective_tasks
                    SET status = %s{started_at_sql}
                    WHERE id = %s
                    """,
                    (status, int(task_id)),
                )

                conn.commit()
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return False


# Global singleton
_bridge: Optional[PlanningBridge] = None


def get_planning_bridge() -> PlanningBridge:
    """Get or create global planning bridge instance.

    Returns:
        PlanningBridge instance
    """
    global _bridge
    if _bridge is None:
        _bridge = PlanningBridge()
    return _bridge


# Convenience functions
def create_plan(
    goal: str,
    description: str = "",
    depth: int = 3,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a plan. See PlanningBridge.create_plan for details."""
    bridge = get_planning_bridge()
    return bridge.create_plan(goal, description, depth, tags)


def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    status: str = "pending",
    due_date: Optional[datetime] = None,
    estimated_effort_hours: float = 0,
) -> Dict[str, Any]:
    """Create a task. See PlanningBridge.create_task for details."""
    bridge = get_planning_bridge()
    return bridge.create_task(
        title, description, priority, status, due_date, estimated_effort_hours
    )


def list_plans(status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """List plans. See PlanningBridge.list_plans for details."""
    bridge = get_planning_bridge()
    return bridge.list_plans(status, limit)


def list_tasks(status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """List tasks. See PlanningBridge.list_tasks for details."""
    bridge = get_planning_bridge()
    return bridge.list_tasks(status, limit)


def update_task_status(task_id: str, status: str) -> bool:
    """Update task status. See PlanningBridge.update_task_status for details."""
    bridge = get_planning_bridge()
    return bridge.update_task_status(task_id, status)
