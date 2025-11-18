"""Progress monitoring with adaptive milestones, blocker detection, and completion forecasting."""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .models import ProgressMilestone


@dataclass
class Blocker:
    """Represents a blocker on a goal."""

    goal_id: int
    blocker_text: str
    detected_at: datetime
    severity: str  # 'low', 'medium', 'high'


@dataclass
class Burndown:
    """Burndown tracking data."""

    goal_id: int
    expected_progress: float  # What we expected at this point
    actual_progress: float  # What we achieved
    days_elapsed: float
    on_track: bool
    trend: str  # 'improving', 'stable', 'degrading'


class ProgressMonitor:
    """Manages goal progress tracking with adaptive milestones and forecasting."""

    BLOCKER_THRESHOLD_MINUTES = 120  # 2 hours of no progress
    MAX_MILESTONE_COUNT = 5  # Maximum milestones per goal

    def __init__(self, db_path: str):
        """Initialize progress monitor."""
        self.db_path = db_path

    async def generate_milestones(
        self, goal_id: int, goal_text: str, estimated_hours: Optional[float]
    ) -> List[ProgressMilestone]:
        """
        Generate adaptive milestones based on goal complexity and estimated duration.

        Algorithm:
        1. Classify goal complexity (1-5 scale based on keywords)
        2. Determine milestone count: 3 for simple, 4 for medium, 5 for complex
        3. Generate evenly-spaced milestones (25%, 50%, 75%, 100%)
        4. Calculate target dates based on estimated_hours
        """
        complexity = self._classify_complexity(goal_text)
        milestone_count = self._milestone_count_for_complexity(complexity)

        milestones = []
        progress_increments = [1.0 / milestone_count * (i + 1) for i in range(milestone_count)]

        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT created_at FROM executive_goals WHERE id = ?", (goal_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    return []

                created_at = datetime.fromisoformat(row[0])

                for i, progress in enumerate(progress_increments):
                    milestone_text = self._milestone_text_for_progress(progress, complexity)
                    target_date = None

                    if estimated_hours:
                        hours_to_milestone = estimated_hours * progress
                        target_date = created_at + timedelta(hours=hours_to_milestone)

                    milestone = ProgressMilestone(
                        id=0,  # Will be assigned by DB
                        goal_id=goal_id,
                        milestone_text=milestone_text,
                        expected_progress=progress,
                        actual_progress=0.0,
                        target_date=target_date,
                        completed_at=None,
                    )

                    await cursor.execute(
                        """
                        INSERT INTO progress_milestones
                        (goal_id, milestone_text, expected_progress, actual_progress, target_date)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            goal_id,
                            milestone_text,
                            progress,
                            0.0,
                            target_date.isoformat() if target_date else None,
                        ),
                    )
                    milestone.id = cursor.lastrowid
                    milestones.append(milestone)

                conn.commit()

        return milestones

    async def get_milestones(self, goal_id: int) -> List[ProgressMilestone]:
        """Get all milestones for a goal."""
        milestones = []

        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT id, goal_id, milestone_text, expected_progress, actual_progress,
                           target_date, completed_at
                    FROM progress_milestones
                WHERE goal_id = ?
                ORDER BY expected_progress
                """,
                    (goal_id,),
                )

                for row in await cursor.fetchall():
                    milestone = ProgressMilestone(
                        id=row[0],
                        goal_id=row[1],
                        milestone_text=row[2],
                        expected_progress=row[3],
                        actual_progress=row[4],
                        target_date=datetime.fromisoformat(row[5]) if row[5] else None,
                        completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    )
                    milestones.append(milestone)

        return milestones

    async def update_milestone_progress(
        self, milestone_id: int, actual_progress: float
    ) -> ProgressMilestone:
        """Update milestone progress."""
        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                completed_at = None
                if actual_progress >= 1.0:
                    completed_at = datetime.now().isoformat()

                await cursor.execute(
                    """
                    UPDATE progress_milestones
                    SET actual_progress = %s, completed_at = ?
                    WHERE id = ?
                    """,
                    (actual_progress, completed_at, milestone_id),
                )

                await cursor.execute(
                    """
                    SELECT id, goal_id, milestone_text, expected_progress, actual_progress,
                           target_date, completed_at
                    FROM progress_milestones
                    WHERE id = ?
                    """,
                    (milestone_id,),
                )
                row = await cursor.fetchone()
                conn.commit()

        milestone = ProgressMilestone(
            id=row[0],
            goal_id=row[1],
            milestone_text=row[2],
            expected_progress=row[3],
            actual_progress=row[4],
            target_date=datetime.fromisoformat(row[5]) if row[5] else None,
            completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
        )

        return milestone

    async def detect_blockers(self, goal_id: int) -> List[Blocker]:
        """
        Detect blockers on a goal based on lack of progress over time.

        A blocker is detected when:
        - Goal progress hasn't changed in 2+ hours
        - Goal is marked as active
        """
        blockers = []

        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                # Get goal info
                await cursor.execute(
                    "SELECT id, progress FROM executive_goals WHERE id = ?", (goal_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    return []

                current_progress = row[1]

                # Check if we have progress history
                await cursor.execute(
                    """
                    SELECT progress, updated_at FROM goal_progress_history
                    WHERE goal_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (goal_id,),
                )
                history_row = await cursor.fetchone()

                if history_row:
                    previous_progress = history_row[0]
                    last_update = datetime.fromisoformat(history_row[1])
                    time_elapsed = datetime.now() - last_update

                    # Check for stale progress
                    if current_progress == previous_progress and time_elapsed > timedelta(
                        minutes=self.BLOCKER_THRESHOLD_MINUTES
                    ):
                        blocker = Blocker(
                            goal_id=goal_id,
                            blocker_text=f"No progress for {time_elapsed.total_seconds() / 60:.0f} minutes",
                            detected_at=datetime.now(),
                            severity="high",
                        )
                        blockers.append(blocker)

        return blockers

    async def calculate_burndown(self, goal_id: int) -> Optional[Burndown]:
        """
        Calculate burndown metrics.

        Returns expected progress vs actual progress over time.
        """
        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT id, progress, created_at, estimated_hours, actual_hours
                    FROM executive_goals
                    WHERE id = ?
                    """,
                    (goal_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    return None

                goal_id, current_progress, created_at, estimated_hours, actual_hours = row

                created_at = datetime.fromisoformat(created_at)
                days_elapsed = (datetime.now() - created_at).total_seconds() / (24 * 3600)

                # Calculate expected progress
                if estimated_hours and estimated_hours > 0:
                    hours_elapsed = days_elapsed * 24
                    expected_progress = min(1.0, hours_elapsed / estimated_hours)
                else:
                    expected_progress = current_progress  # No estimate, use actual

                # Determine trend
                trend = self._determine_trend(goal_id, current_progress, expected_progress)

                # Determine if on track (with 20% buffer)
                on_track = current_progress >= expected_progress * 0.8

                return Burndown(
                    goal_id=goal_id,
                    expected_progress=expected_progress,
                    actual_progress=current_progress,
                    days_elapsed=days_elapsed,
                    on_track=on_track,
                    trend=trend,
                )

    async def forecast_completion(self, goal_id: int) -> Optional[Tuple[datetime, float]]:
        """
        Forecast completion time and confidence.

        Returns: (estimated_completion_date, confidence_0_to_1)
        """
        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT progress, created_at, estimated_hours, deadline
                    FROM executive_goals
                    WHERE id = ?
                    """,
                    (goal_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    return None

                progress, created_at, estimated_hours, deadline = row

                if progress == 0:
                    return None  # Can't forecast with zero progress

                created_at = datetime.fromisoformat(created_at)
                deadline_dt = datetime.fromisoformat(deadline) if deadline else None

                # Calculate velocity (progress per hour)
                hours_elapsed = (datetime.now() - created_at).total_seconds() / 3600
                if hours_elapsed == 0:
                    return None

                velocity = progress / hours_elapsed

                # Estimate remaining hours
                remaining_progress = 1.0 - progress
                estimated_remaining_hours = (
                    remaining_progress / velocity if velocity > 0 else float("inf")
                )

                # Forecast completion
                estimated_completion = datetime.now() + timedelta(hours=estimated_remaining_hours)

                # Calculate confidence based on alignment with estimated hours
                confidence = 1.0
                if estimated_hours:
                    ratio = estimated_remaining_hours / (estimated_hours - hours_elapsed)
                    if ratio > 2.0 or ratio < 0.5:
                        confidence = 0.5  # Low confidence if way off

                return (estimated_completion, confidence)

    async def get_next_milestone(self, goal_id: int) -> Optional[ProgressMilestone]:
        """Get the next incomplete milestone for a goal."""
        milestones = self.get_milestones(goal_id)

        for milestone in milestones:
            if milestone.completed_at is None and milestone.actual_progress < 1.0:
                return milestone

        return None

    async def get_milestone_status(self, milestone_id: int) -> Optional[dict]:
        """Get detailed status of a milestone."""
        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT id, goal_id, milestone_text, expected_progress, actual_progress,
                           target_date, completed_at
                    FROM progress_milestones
                    WHERE id = ?
                    """,
                    (milestone_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    return None

                milestone = ProgressMilestone(
                    id=row[0],
                    goal_id=row[1],
                    milestone_text=row[2],
                    expected_progress=row[3],
                    actual_progress=row[4],
                    target_date=datetime.fromisoformat(row[5]) if row[5] else None,
                    completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                )

                is_completed = milestone.completed_at is not None
                is_on_track = milestone.is_on_track()

                return {
                    "milestone": milestone,
                    "completed": is_completed,
                    "on_track": is_on_track,
                    "progress": milestone.actual_progress,
                    "days_to_target": (
                        (milestone.target_date.date() - datetime.now().date()).days
                        if milestone.target_date
                        else None
                    ),
                }

    # Private helper methods

    def _classify_complexity(self, goal_text: str) -> int:
        """
        Classify goal complexity on 1-5 scale based on keywords.

        Simple (1-2): quick, simple, fix, small
        Medium (2-3): add, implement, change, update
        Complex (4-5): refactor, redesign, architecture, optimize
        """
        text_lower = goal_text.lower()

        simple_keywords = ["quick", "simple", "fix", "small", "minor", "patch"]
        complex_keywords = [
            "refactor",
            "redesign",
            "architecture",
            "optimize",
            "performance",
            "rewrite",
        ]

        complex_count = sum(1 for kw in complex_keywords if kw in text_lower)
        simple_count = sum(1 for kw in simple_keywords if kw in text_lower)

        if complex_count >= 2:
            return 5
        elif complex_count >= 1:
            return 4
        elif simple_count >= 2:
            return 1
        elif simple_count >= 1:
            return 2
        else:
            return 3  # Default to medium

    def _milestone_count_for_complexity(self, complexity: int) -> int:
        """Determine milestone count based on complexity."""
        if complexity <= 2:
            return 3
        elif complexity <= 3:
            return 4
        else:
            return 5

    def _milestone_text_for_progress(self, progress: float, complexity: int) -> str:
        """Generate milestone description based on progress percentage."""
        percentage = int(progress * 100)

        if complexity <= 2:  # Simple goals
            milestones = {
                25: "Initial setup",
                50: "Core implementation",
                75: "Testing",
                100: "Complete",
            }
        elif complexity <= 3:  # Medium goals
            milestones = {
                25: "Research & design",
                50: "Implementation",
                75: "Testing & review",
                100: "Complete",
            }
        else:  # Complex goals
            milestones = {
                20: "Architecture",
                40: "Core implementation",
                60: "Integration",
                80: "Testing & optimization",
                100: "Complete",
            }

        # Find closest milestone percentage
        closest_pct = min(milestones.keys(), key=lambda x: abs(x - percentage))
        return milestones[closest_pct]

    def _determine_trend(
        self, goal_id: int, current_progress: float, expected_progress: float
    ) -> str:
        """Determine progress trend."""
        if current_progress >= expected_progress:
            return "improving"
        elif current_progress >= expected_progress * 0.8:
            return "stable"
        else:
            return "degrading"
