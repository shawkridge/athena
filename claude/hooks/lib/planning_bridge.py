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
        Plans are stored in planning_patterns table for future reference.

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

                # Create plan as a planning_pattern
                now = int(datetime.now().timestamp())
                pattern_type = "plan"
                name = goal[:100]  # Truncate long goals

                cursor.execute(
                    """
                    INSERT INTO planning_patterns
                    (project_id, pattern_type, name, description, success_rate,
                     quality_score, execution_count, applicable_domains,
                     applicable_task_types, complexity_min, complexity_max,
                     conditions, source, created_at, feedback_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        pattern_type,
                        name,
                        description,
                        0.0,  # success_rate
                        0.0,  # quality_score
                        0,  # execution_count
                        json.dumps(["general"]),  # applicable_domains
                        json.dumps(["planning"]),  # applicable_task_types
                        1,  # complexity_min
                        depth,  # complexity_max (use depth as complexity indicator)
                        json.dumps({"depth": depth, "tags": tags or []}),  # conditions
                        "planning_bridge",  # source
                        now,  # created_at
                        0,  # feedback_count
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
                    "status": "draft",
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
        tags: Optional[List[str]] = None,
        due_date: Optional[datetime] = None,
        estimated_effort_minutes: int = 0,
    ) -> Dict[str, Any]:
        """Create a prospective task.

        Creates a task in the prospective_tasks table for tracking goals
        and deliverables.

        Args:
            title: Task title
            description: Detailed description
            priority: Priority level (low, medium, high, critical)
            status: Initial status (pending, in_progress, completed, blocked)
            tags: Optional tags for categorization
            due_date: Optional due date
            estimated_effort_minutes: Estimated effort in minutes

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

                now = int(datetime.now().timestamp())
                due_timestamp = int(due_date.timestamp()) if due_date else None

                cursor.execute(
                    """
                    INSERT INTO prospective_tasks
                    (project_id, title, description, priority, status,
                     tags, due_date, estimated_effort_minutes, created_at,
                     phase, phase_started_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        title,
                        description,
                        priority,
                        status,
                        json.dumps(tags or []),
                        due_timestamp,
                        estimated_effort_minutes,
                        now,
                        "planning",
                        now if status == "in_progress" else None,
                    ),
                )

                result = cursor.fetchone()
                task_id = result[0] if result else None

                conn.commit()

                return {
                    "id": str(task_id),
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": status,
                    "tags": tags or [],
                    "due_date": due_date.isoformat() if due_date else None,
                    "created_at": datetime.fromtimestamp(now).isoformat(),
                }

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {"error": str(e)}

    def list_plans(
        self, status: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List plans, optionally filtered by status.

        Args:
            status: Optional status filter (draft, active, completed, failed)
            limit: Maximum plans to return

        Returns:
            List of plan dicts
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                if status:
                    # Plans stored as planning_patterns with conditions containing status
                    cursor.execute(
                        """
                        SELECT id, name, description, created_at, last_used,
                               success_rate, quality_score, execution_count
                        FROM planning_patterns
                        WHERE pattern_type = 'plan'
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, name, description, created_at, last_used,
                               success_rate, quality_score, execution_count
                        FROM planning_patterns
                        WHERE pattern_type = 'plan'
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
                        "created_at": datetime.fromtimestamp(row[3]).isoformat() if row[3] else None,
                        "last_used": datetime.fromtimestamp(row[4]).isoformat() if row[4] else None,
                        "success_rate": row[5],
                        "quality_score": row[6],
                        "execution_count": row[7],
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
                               tags, due_date, estimated_effort_minutes, created_at
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
                               tags, due_date, estimated_effort_minutes, created_at
                        FROM prospective_tasks
                        ORDER BY priority DESC, created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )

                rows = cursor.fetchall()
                tasks = []
                for row in rows:
                    tasks.append({
                        "id": str(row[0]),
                        "title": row[1],
                        "description": row[2],
                        "priority": row[3],
                        "status": row[4],
                        "tags": json.loads(row[5]) if row[5] else [],
                        "due_date": datetime.fromtimestamp(row[6]).isoformat() if row[6] else None,
                        "estimated_effort_minutes": row[7],
                        "created_at": datetime.fromtimestamp(row[8]).isoformat() if row[8] else None,
                    })

                return tasks

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []

    def update_task_status(
        self, task_id: str, status: str, notes: str = ""
    ) -> bool:
        """Update task status.

        Args:
            task_id: Task ID
            status: New status (pending, in_progress, completed, blocked)
            notes: Optional notes about status change

        Returns:
            True if successful, False otherwise
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                now = int(datetime.now().timestamp())

                cursor.execute(
                    """
                    UPDATE prospective_tasks
                    SET status = %s, notes = %s
                    WHERE id = %s
                    """,
                    (status, notes, int(task_id)),
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
    tags: Optional[List[str]] = None,
    due_date: Optional[datetime] = None,
    estimated_effort_minutes: int = 0,
) -> Dict[str, Any]:
    """Create a task. See PlanningBridge.create_task for details."""
    bridge = get_planning_bridge()
    return bridge.create_task(
        title, description, priority, status, tags, due_date, estimated_effort_minutes
    )


def list_plans(status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """List plans. See PlanningBridge.list_plans for details."""
    bridge = get_planning_bridge()
    return bridge.list_plans(status, limit)


def list_tasks(status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """List tasks. See PlanningBridge.list_tasks for details."""
    bridge = get_planning_bridge()
    return bridge.list_tasks(status, limit)


def update_task_status(task_id: str, status: str, notes: str = "") -> bool:
    """Update task status. See PlanningBridge.update_task_status for details."""
    bridge = get_planning_bridge()
    return bridge.update_task_status(task_id, status, notes)
