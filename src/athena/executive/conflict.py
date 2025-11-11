"""Conflict resolution for competing goals and resource allocation."""

from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from .models import Goal, GoalStatus


@dataclass
class ConflictResolution:
    """Record of a conflict resolution."""

    id: int
    project_id: int
    competing_goals: List[int]  # Goal IDs involved in conflict
    resolution_timestamp: datetime
    primary_goal_id: int  # Which goal won priority
    reasoning: str
    resource_allocation: Dict[int, float]  # goal_id -> allocation_weight


class ConflictResolver:
    """
    Resolves conflicts between competing goals.

    Priority calculation algorithm:
    score = 0.4×priority + 0.3×urgency + 0.2×dependency + 0.1×progress

    Factors:
    1. Explicit priority (user-set, 1-10)
    2. Deadline urgency (remaining days)
    3. Blocker severity (blocked other goals?)
    4. Dependency chain (affects other goals?)
    5. Progress toward completion
    """

    def __init__(self, db_path: str):
        """Initialize conflict resolver."""
        self.db_path = db_path

    def resolve_priority(self, competing_goal_ids: List[int]) -> Dict:
        """
        Resolve priority between competing goals.

        Returns: {
            'primary_goal_id': int,
            'resolution_scores': {goal_id: score},
            'resource_allocation': {goal_id: weight},
            'reasoning': str
        }
        """
        if not competing_goal_ids:
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get goal data
            goals = {}
            for goal_id in competing_goal_ids:
                cursor.execute(
                    """
                    SELECT id, project_id, goal_text, priority, deadline, created_at, progress
                    FROM executive_goals
                    WHERE id = ?
                    """,
                    (goal_id,),
                )
                row = cursor.fetchone()
                if row:
                    goals[goal_id] = {
                        "id": row[0],
                        "project_id": row[1],
                        "text": row[2],
                        "priority": row[3],
                        "deadline": row[4],
                        "created_at": row[5],
                        "progress": row[6],
                    }

            # Calculate scores
            scores = {}
            for goal_id, goal_data in goals.items():
                score = self._calculate_priority_score(goal_data, cursor)
                scores[goal_id] = score

            # Determine primary goal (highest score)
            primary_goal_id = max(scores, key=scores.get)

            # Calculate resource allocation
            allocation = self._calculate_resource_allocation(scores)

            # Generate reasoning
            reasoning = self._generate_reasoning(primary_goal_id, scores, goals)

            # Log resolution
            project_id = goals[primary_goal_id]["project_id"]
            cursor.execute(
                """
                INSERT INTO conflict_resolutions
                (project_id, primary_goal_id, competing_goals, resolution_timestamp, reasoning)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    primary_goal_id,
                    ",".join(str(g) for g in competing_goal_ids),
                    datetime.now().isoformat(),
                    reasoning,
                ),
            )
            conn.commit()

            return {
                "primary_goal_id": primary_goal_id,
                "resolution_scores": scores,
                "resource_allocation": allocation,
                "reasoning": reasoning,
            }

    def suspend_goal(self, goal_id: int, reason: str = "conflict_resolution") -> bool:
        """Suspend a goal (pause work on it)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE executive_goals
                SET status = 'suspended'
                WHERE id = ?
                """,
                (goal_id,),
            )

            cursor.execute(
                """
                INSERT INTO goal_suspension_log (goal_id, reason, suspended_at)
                VALUES (?, ?, ?)
                """,
                (goal_id, reason, datetime.now().isoformat()),
            )

            conn.commit()
            return cursor.rowcount > 0

    def resume_goal(self, goal_id: int) -> bool:
        """Resume a suspended goal."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE executive_goals
                SET status = 'active'
                WHERE id = ? AND status = 'suspended'
                """,
                (goal_id,),
            )

            cursor.execute(
                """
                INSERT INTO goal_suspension_log (goal_id, reason, resumed_at)
                VALUES (?, ?, ?)
                """,
                (goal_id, "conflict_resolved", datetime.now().isoformat()),
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_conflict_resolution_log(self, project_id: int, limit: int = 10) -> List[Dict]:
        """Get conflict resolution history."""
        resolutions = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, primary_goal_id, competing_goals, resolution_timestamp, reasoning
                FROM conflict_resolutions
                WHERE project_id = ?
                ORDER BY resolution_timestamp DESC
                LIMIT ?
                """,
                (project_id, limit),
            )

            for row in cursor.fetchall():
                resolution = {
                    "id": row[0],
                    "primary_goal_id": row[1],
                    "competing_goals": [int(g) for g in row[2].split(",") if g],
                    "resolution_timestamp": row[3],
                    "reasoning": row[4],
                }
                resolutions.append(resolution)

        return resolutions

    def allocate_working_memory_fair(
        self, active_goal_ids: List[int]
    ) -> Dict[int, float]:
        """
        Allocate working memory slots fairly among active goals.

        Uses weighted distribution based on goal priority and progress.
        Total slots = 7±2 (Baddeley's working memory capacity)
        """
        if not active_goal_ids:
            return {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get goal scores
            scores = {}
            for goal_id in active_goal_ids:
                cursor.execute(
                    """
                    SELECT priority, deadline, created_at, progress
                    FROM executive_goals
                    WHERE id = ?
                    """,
                    (goal_id,),
                )
                row = cursor.fetchone()
                if row:
                    goal_data = {
                        "priority": row[0],
                        "deadline": row[1],
                        "created_at": row[2],
                        "progress": row[3],
                    }
                    scores[goal_id] = self._calculate_priority_score(goal_data, cursor)

            # Allocate slots (7 total, distributed by score)
            total_score = sum(scores.values())
            allocation = {}

            for goal_id, score in scores.items():
                if total_score > 0:
                    allocation[goal_id] = 7.0 * (score / total_score)
                else:
                    allocation[goal_id] = 7.0 / len(active_goal_ids)

            return allocation

    def resolve_multiple_conflicts(self, project_id: int) -> Optional[Dict]:
        """
        Resolve conflicts among all active goals in a project.

        If multiple goals have high priority, suspend lower-priority ones.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all active goals
            cursor.execute(
                """
                SELECT id FROM executive_goals
                WHERE project_id = ? AND status = 'active'
                ORDER BY priority DESC
                """,
                (project_id,),
            )

            active_goals = [row[0] for row in cursor.fetchall()]

            if len(active_goals) <= 1:
                return None  # No conflict

            # Resolve conflicts
            resolution = self.resolve_priority(active_goals)

            # Suspend lower-priority goals if needed
            primary_goal = resolution["primary_goal_id"]
            for goal_id in active_goals:
                if goal_id != primary_goal:
                    # Check if goal should be suspended
                    should_suspend = resolution["resource_allocation"].get(goal_id, 0) < 0.5

                    if should_suspend:
                        self.suspend_goal(goal_id, "conflict_resolution_lower_priority")

            return resolution

    # Private helper methods

    def _calculate_priority_score(self, goal_data: Dict, cursor) -> float:
        """Calculate priority score using weighted algorithm."""
        now = datetime.now()

        # Factor 1: Explicit priority (1-10 -> 0-1)
        explicit_priority = goal_data.get("priority", 5) / 10.0

        # Factor 2: Deadline urgency
        deadline_urgency = 0.0
        if goal_data.get("deadline"):
            deadline = datetime.fromisoformat(goal_data["deadline"])
            days_remaining = (deadline.date() - now.date()).days
            if days_remaining <= 0:
                deadline_urgency = 1.0
            elif days_remaining <= 3:
                deadline_urgency = 0.9
            elif days_remaining <= 7:
                deadline_urgency = 0.5
            elif days_remaining <= 14:
                deadline_urgency = 0.2
            else:
                deadline_urgency = 0.0

        # Factor 3: Dependency chain (goals blocked by this one)
        dependency_factor = 0.0
        goal_id = goal_data.get("id")
        if goal_id:
            cursor.execute(
                """
                SELECT COUNT(*) FROM executive_goals
                WHERE parent_goal_id = ? AND status = 'active'
                """,
                (goal_id,),
            )
            dependent_count = cursor.fetchone()[0]
            dependency_factor = min(1.0, dependent_count / 3.0)

        # Factor 4: Progress toward completion (favor goals near completion)
        progress = goal_data.get("progress", 0.0)
        progress_factor = progress  # More progress = higher priority to finish

        # Weighted calculation
        score = (
            0.4 * explicit_priority
            + 0.3 * deadline_urgency
            + 0.2 * dependency_factor
            + 0.1 * progress_factor
        )

        return score

    def _calculate_resource_allocation(self, scores: Dict[int, float]) -> Dict[int, float]:
        """Calculate fair resource allocation based on scores."""
        total_score = sum(scores.values())
        allocation = {}

        for goal_id, score in scores.items():
            if total_score > 0:
                allocation[goal_id] = score / total_score
            else:
                allocation[goal_id] = 1.0 / len(scores)

        return allocation

    def _generate_reasoning(self, primary_goal_id: int, scores: Dict, goals: Dict) -> str:
        """Generate human-readable reasoning for resolution."""
        primary_score = scores[primary_goal_id]
        primary_text = goals[primary_goal_id]["text"][:50]

        reasoning_parts = [f"Selected '{primary_text}' (score: {primary_score:.2f})"]

        # Add context about why
        if goals[primary_goal_id]["priority"] >= 8:
            reasoning_parts.append("high priority")

        if goals[primary_goal_id]["progress"] > 0.75:
            reasoning_parts.append("nearly complete")

        if goals[primary_goal_id]["deadline"]:
            deadline = datetime.fromisoformat(goals[primary_goal_id]["deadline"])
            days_left = (deadline.date() - datetime.now().date()).days
            if days_left <= 3:
                reasoning_parts.append("urgent deadline")

        return " (".join(reasoning_parts) + ")" if len(reasoning_parts) > 1 else reasoning_parts[0]
