"""Goal hierarchy management - organize goals in parent-child relationships."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple

from ..core.database import Database
from .models import Goal, GoalType, GoalStatus


class GoalHierarchy:
    """
    Manage hierarchical goal structure with context preservation.

    Supports:
    - Multi-level goal hierarchies (max 5 levels)
    - Parent-child relationships
    - Goal status cascade (completing parent affects subgoals)
    - Context preservation during goal transitions
    - Automatic pruning of stale goals
    """

    MAX_HIERARCHY_DEPTH = 5
    STALE_GOAL_DAYS = 7

    def __init__(self, db: Database):
        """Initialize goal hierarchy manager.

        Args:
            db: Database connection
        """
        self.db = db

    def create_goal(
        self,
        project_id: int,
        goal_text: str,
        goal_type: GoalType = GoalType.PRIMARY,
        priority: int = 5,
        parent_goal_id: Optional[int] = None,
        estimated_hours: Optional[float] = None,
        deadline: Optional[datetime] = None,
    ) -> int:
        """Create a new goal.

        Args:
            project_id: Project ID
            goal_text: Goal description
            goal_type: Goal type (primary/subgoal/maintenance)
            priority: Priority level (1-10)
            parent_goal_id: Parent goal ID for subgoals
            estimated_hours: Estimated duration in hours
            deadline: Goal deadline

        Returns:
            Created goal ID

        Raises:
            ValueError: If priority out of range or hierarchy too deep
        """
        if not 1 <= priority <= 10:
            raise ValueError("priority must be between 1 and 10")

        # Check hierarchy depth
        if parent_goal_id:
            depth = self._get_hierarchy_depth(parent_goal_id)
            if depth >= self.MAX_HIERARCHY_DEPTH:
                raise ValueError(f"Goal hierarchy exceeds max depth of {self.MAX_HIERARCHY_DEPTH}")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO executive_goals (
                    project_id, goal_text, goal_type, priority,
                    parent_goal_id, estimated_hours, deadline
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    goal_text,
                    goal_type.value,
                    priority,
                    parent_goal_id,
                    estimated_hours,
                    deadline.isoformat() if deadline else None,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_goal(self, goal_id: int) -> Optional[Goal]:
        """Get goal by ID.

        Args:
            goal_id: Goal ID

        Returns:
            Goal object or None if not found
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT id, project_id, parent_goal_id, goal_text, goal_type, priority,
                       status, progress, estimated_hours, actual_hours, created_at,
                       deadline, completed_at
                FROM executive_goals
                WHERE id = ?
                """,
                (goal_id,),
            ).fetchone()

            if not result:
                return None

            return Goal(
                id=result["id"],
                project_id=result["project_id"],
                goal_text=result["goal_text"],
                goal_type=GoalType(result["goal_type"]),
                priority=result["priority"],
                status=GoalStatus(result["status"]),
                progress=result["progress"],
                created_at=datetime.fromisoformat(result["created_at"]),
                parent_goal_id=result["parent_goal_id"],
                estimated_hours=result["estimated_hours"],
                actual_hours=result["actual_hours"],
                deadline=datetime.fromisoformat(result["deadline"]) if result["deadline"] else None,
                completed_at=datetime.fromisoformat(result["completed_at"]) if result["completed_at"] else None,
            )

    def get_active_goals(self, project_id: int, include_subgoals: bool = True) -> List[Goal]:
        """Get all active goals for a project.

        Args:
            project_id: Project ID
            include_subgoals: Whether to include subgoals

        Returns:
            List of active goals sorted by priority
        """
        with self.db.get_connection() as conn:
            goal_type_filter = ""
            if not include_subgoals:
                goal_type_filter = "AND goal_type IN ('primary', 'maintenance')"

            cursor = conn.execute(
                f"""
                SELECT id, project_id, parent_goal_id, goal_text, goal_type, priority,
                       status, progress, estimated_hours, actual_hours, created_at,
                       deadline, completed_at
                FROM executive_goals
                WHERE project_id = ? AND status IN ('active', 'suspended')
                {goal_type_filter}
                ORDER BY priority DESC, deadline ASC
                """,
                (project_id,),
            )

            goals = []
            for row in cursor.fetchall():
                goals.append(
                    Goal(
                        id=row["id"],
                        project_id=row["project_id"],
                        goal_text=row["goal_text"],
                        goal_type=GoalType(row["goal_type"]),
                        priority=row["priority"],
                        status=GoalStatus(row["status"]),
                        progress=row["progress"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        parent_goal_id=row["parent_goal_id"],
                        estimated_hours=row["estimated_hours"],
                        actual_hours=row["actual_hours"],
                        deadline=datetime.fromisoformat(row["deadline"]) if row["deadline"] else None,
                        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    )
                )

            return goals

    def update_goal(
        self,
        goal_id: int,
        goal_text: Optional[str] = None,
        priority: Optional[int] = None,
        estimated_hours: Optional[float] = None,
        deadline: Optional[datetime] = None,
    ) -> bool:
        """Update goal details.

        Args:
            goal_id: Goal ID
            goal_text: New goal text (optional)
            priority: New priority (optional)
            estimated_hours: New estimated hours (optional)
            deadline: New deadline (optional)

        Returns:
            True if updated, False if goal not found
        """
        if priority is not None and not 1 <= priority <= 10:
            raise ValueError("priority must be between 1 and 10")

        updates = []
        params = []

        if goal_text:
            updates.append("goal_text = ?")
            params.append(goal_text)

        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)

        if estimated_hours is not None:
            updates.append("estimated_hours = ?")
            params.append(estimated_hours)

        if deadline is not None:
            updates.append("deadline = ?")
            params.append(deadline.isoformat())

        if not updates:
            return False

        params.append(goal_id)

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                f"""
                UPDATE executive_goals
                SET {', '.join(updates)}
                WHERE id = ?
                """,
                params,
            )
            conn.commit()
            return cursor.rowcount > 0

    def mark_goal_complete(self, goal_id: int, cascade: bool = False) -> int:
        """Mark goal as completed.

        Args:
            goal_id: Goal ID
            cascade: If True, also complete direct subgoals

        Returns:
            Number of goals marked complete
        """
        with self.db.get_connection() as conn:
            # Mark this goal complete
            conn.execute(
                """
                UPDATE executive_goals
                SET status = ?, completed_at = ?
                WHERE id = ? AND status != 'completed'
                """,
                (GoalStatus.COMPLETED.value, datetime.now().isoformat(), goal_id),
            )

            count = 1

            # Optionally cascade to subgoals
            if cascade:
                cursor = conn.execute(
                    """
                    UPDATE executive_goals
                    SET status = ?, completed_at = ?
                    WHERE parent_goal_id = ? AND status IN ('active', 'suspended')
                    """,
                    (GoalStatus.COMPLETED.value, datetime.now().isoformat(), goal_id),
                )
                count += cursor.rowcount

            conn.commit()

        return count

    def mark_goal_failed(self, goal_id: int) -> bool:
        """Mark goal as failed.

        Args:
            goal_id: Goal ID

        Returns:
            True if marked, False if already in terminal state
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE executive_goals
                SET status = ?
                WHERE id = ? AND status IN ('active', 'suspended')
                """,
                (GoalStatus.FAILED.value, goal_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def mark_goal_abandoned(self, goal_id: int) -> bool:
        """Abandon a goal.

        Args:
            goal_id: Goal ID

        Returns:
            True if abandoned, False if already in terminal state
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE executive_goals
                SET status = ?
                WHERE id = ? AND status IN ('active', 'suspended')
                """,
                (GoalStatus.ABANDONED.value, goal_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def suspend_goal(self, goal_id: int) -> bool:
        """Suspend a goal temporarily.

        Args:
            goal_id: Goal ID

        Returns:
            True if suspended, False if already suspended/completed
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE executive_goals
                SET status = ?
                WHERE id = ? AND status = 'active'
                """,
                (GoalStatus.SUSPENDED.value, goal_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def resume_goal(self, goal_id: int) -> bool:
        """Resume a suspended goal.

        Args:
            goal_id: Goal ID

        Returns:
            True if resumed, False if not suspended
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE executive_goals
                SET status = ?
                WHERE id = ? AND status = 'suspended'
                """,
                (GoalStatus.ACTIVE.value, goal_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_goal_tree(self, project_id: int, parent_goal_id: Optional[int] = None) -> Dict:
        """Get goal hierarchy as tree structure.

        Args:
            project_id: Project ID
            parent_goal_id: Root goal ID (None for all root goals)

        Returns:
            Nested dictionary representing goal tree
        """
        with self.db.get_connection() as conn:
            if parent_goal_id is None:
                cursor = conn.execute(
                    """
                    SELECT id, project_id, parent_goal_id, goal_text, goal_type, priority,
                           status, progress, estimated_hours, actual_hours, created_at,
                           deadline, completed_at
                    FROM executive_goals
                    WHERE project_id = ? AND parent_goal_id IS NULL
                    ORDER BY priority DESC
                    """,
                    (project_id,),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, project_id, parent_goal_id, goal_text, goal_type, priority,
                           status, progress, estimated_hours, actual_hours, created_at,
                           deadline, completed_at
                    FROM executive_goals
                    WHERE project_id = ? AND parent_goal_id = ?
                    ORDER BY priority DESC
                    """,
                    (project_id, parent_goal_id),
                )

            tree = {"goals": []}

            for row in cursor.fetchall():
                goal_dict = {
                    "id": row["id"],
                    "text": row["goal_text"],
                    "type": row["goal_type"],
                    "priority": row["priority"],
                    "status": row["status"],
                    "progress": row["progress"],
                    "deadline": row["deadline"],
                    "subgoals": [],
                }

                # Recursively add subgoals
                subgoals = self.get_goal_tree(project_id, row["id"])
                goal_dict["subgoals"] = subgoals["goals"]

                tree["goals"].append(goal_dict)

            return tree

    def prune_stale_goals(self, project_id: int, days_inactive: int = STALE_GOAL_DAYS) -> int:
        """Remove stale suspended goals not updated for N days.

        Args:
            project_id: Project ID
            days_inactive: Days without update to consider stale

        Returns:
            Number of goals pruned
        """
        cutoff = datetime.now() - timedelta(days=days_inactive)

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM executive_goals
                WHERE project_id = ? AND status = 'suspended'
                AND created_at < ?
                """,
                (project_id, cutoff.isoformat()),
            )
            conn.commit()
            return cursor.rowcount

    def _get_hierarchy_depth(self, goal_id: int, depth: int = 0) -> int:
        """Get the depth of a goal in the hierarchy.

        Args:
            goal_id: Goal ID
            depth: Current depth

        Returns:
            Depth in hierarchy
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                "SELECT parent_goal_id FROM executive_goals WHERE id = ?",
                (goal_id,),
            ).fetchone()

            if not result or not result["parent_goal_id"]:
                return depth

            return self._get_hierarchy_depth(result["parent_goal_id"], depth + 1)
