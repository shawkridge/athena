"""
Goal State Tracker Skill - Phase 3 Executive Function.

Monitors goal progress, detects blockers, and evaluates milestone status.
Auto-triggers on progress updates and periodic checks.
"""

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from .base_skill import BaseSkill, SkillResult


class GoalStateTrackerSkill(BaseSkill):
    """Monitors goal progress and health."""

    def __init__(self):
        """Initialize skill."""
        super().__init__(
            skill_id="goal-state-tracker",
            skill_name="Goal State Tracker"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute goal tracking.

        Monitors:
        - Progress percentage
        - Blockers and errors
        - Milestone achievements
        - Health score degradation
        - Timeline projections

        Args:
            context: Execution context with memory_manager, active_goal_id

        Returns:
            Result dict with progress report and recommendations
        """
        try:
            memory_manager = context.get('memory_manager')
            active_goal_id = context.get('active_goal_id')
            event = context.get('event')

            if not memory_manager or not active_goal_id:
                return SkillResult(
                    status="skipped",
                    data={"reason": "No active goal"}
                ).to_dict()

            # Get goal state from working memory/memory manager
            goal_state = await self._get_goal_state(
                memory_manager, active_goal_id
            )

            if not goal_state:
                return SkillResult(
                    status="skipped",
                    data={"reason": f"Goal #{active_goal_id} not found"}
                ).to_dict()

            # Calculate progress metrics
            progress_data = await self._calculate_progress(goal_state)

            # Detect blockers
            blockers = await self._detect_blockers(goal_state)

            # Evaluate milestones
            milestones = await self._evaluate_milestones(
                progress_data['progress_percent'],
                goal_state
            )

            # Calculate health score
            health_score = self._calculate_health(progress_data, blockers)

            # Determine actions
            actions = self._recommend_actions(
                progress_data, blockers, health_score, goal_state
            )

            # Build result
            result = SkillResult(
                status="success",
                data={
                    "goal_id": active_goal_id,
                    "progress": progress_data,
                    "blockers": blockers,
                    "milestones": milestones,
                    "health_score": health_score,
                    "timeline": {
                        "estimated_completion": progress_data.get('estimated_completion'),
                        "on_track": progress_data.get('on_track'),
                        "days_remaining": progress_data.get('days_remaining'),
                    },
                    "timestamp": datetime.now().isoformat(),
                },
                actions=actions
            )

            self._log_execution(result.to_dict())
            return result.to_dict()

        except Exception as e:
            return SkillResult(
                status="failed",
                error=str(e)
            ).to_dict()

    async def _get_goal_state(self, memory_manager, goal_id: int) -> Optional[Dict]:
        """Get goal state from memory manager.

        In production, would call:
        memory_manager.get_goal_state(goal_id)
        """
        # Mock implementation - would call memory manager
        return {
            "id": goal_id,
            "name": "Goal",
            "progress": 0,
            "total_steps": 10,
            "errors": 0,
            "blockers": 0,
            "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
            "created_at": datetime.now().isoformat(),
            "milestones": [],
        }

    async def _calculate_progress(self, goal_state: Dict) -> Dict[str, Any]:
        """Calculate progress metrics."""
        progress = goal_state.get('progress', 0)
        total = goal_state.get('total_steps', 10)
        progress_percent = (progress / total * 100) if total > 0 else 0

        # Estimate completion
        if progress > 0:
            rate_per_day = progress / max(1, self._days_elapsed(goal_state))
            days_remaining = (total - progress) / max(1, rate_per_day)
        else:
            days_remaining = (total - progress)  # Assume 1 per day

        deadline = datetime.fromisoformat(goal_state.get('deadline'))
        days_to_deadline = (deadline - datetime.now()).days

        est_completion = datetime.now() + timedelta(days=days_remaining)

        return {
            "progress_percent": progress_percent,
            "steps_completed": progress,
            "total_steps": total,
            "velocity": self._calculate_velocity(goal_state),
            "estimated_completion": est_completion.isoformat(),
            "days_remaining": max(0, days_remaining),
            "days_to_deadline": days_to_deadline,
            "on_track": days_remaining <= days_to_deadline,
        }

    async def _detect_blockers(self, goal_state: Dict) -> Dict[str, Any]:
        """Detect blockers and issues."""
        blockers = goal_state.get('blockers', 0)
        errors = goal_state.get('errors', 0)

        blocker_list = []
        if blockers > 0:
            blocker_list.append({
                "type": "resource",
                "count": blockers,
                "severity": "high" if blockers > 2 else "medium",
            })

        if errors > 5:
            blocker_list.append({
                "type": "error_rate",
                "count": errors,
                "severity": "high",
            })

        return {
            "count": blockers + (1 if errors > 5 else 0),
            "blockers": blocker_list,
            "has_critical": any(b['severity'] == 'high' for b in blocker_list),
        }

    async def _evaluate_milestones(self, progress_percent: float,
                                   goal_state: Dict) -> Dict[str, Any]:
        """Evaluate milestone achievements."""
        milestones = goal_state.get('milestones', [])
        achieved = []

        if progress_percent >= 25:
            achieved.append("25% Complete")
        if progress_percent >= 50:
            achieved.append("50% Complete (Halfway)")
        if progress_percent >= 75:
            achieved.append("75% Complete (Final Push)")
        if progress_percent >= 100:
            achieved.append("100% Complete (Goal Ready)")

        return {
            "achieved": achieved,
            "next_milestone": self._get_next_milestone(progress_percent),
            "progress_to_next": self._progress_to_next(progress_percent),
        }

    def _calculate_health(self, progress_data: Dict,
                         blockers: Dict) -> float:
        """Calculate goal health score (0-1)."""
        # Base on progress velocity
        on_track = 1.0 if progress_data['on_track'] else 0.8

        # Reduce for blockers
        blocker_penalty = min(0.3, blockers['count'] * 0.1)

        # Bonus for steady progress
        if progress_data.get('velocity', 0) > 0:
            progress_bonus = 0.1
        else:
            progress_bonus = 0

        health = on_track - blocker_penalty + progress_bonus
        return max(0.0, min(1.0, health))

    def _recommend_actions(self, progress_data: Dict, blockers: Dict,
                          health_score: float, goal_state: Dict) -> list:
        """Recommend actions based on goal state."""
        actions = []

        if health_score < 0.6:
            actions.append("⚠️ Goal health degraded - consider intervention")

        if blockers['has_critical']:
            actions.append("🚧 Critical blockers detected - escalate")

        if not progress_data['on_track']:
            actions.append("📅 Behind schedule - accelerate progress")

        if progress_data['progress_percent'] >= 100:
            actions.append("✅ Goal complete - run /goal-complete")

        if not actions:
            actions.append("→ Continue at current pace")

        return actions

    def _days_elapsed(self, goal_state: Dict) -> float:
        """Days since goal creation."""
        created = datetime.fromisoformat(goal_state.get('created_at'))
        return max(0.1, (datetime.now() - created).days)

    def _calculate_velocity(self, goal_state: Dict) -> float:
        """Calculate progress velocity (steps per day)."""
        progress = goal_state.get('progress', 0)
        days = max(0.1, self._days_elapsed(goal_state))
        return progress / days

    def _get_next_milestone(self, progress_percent: float) -> str:
        """Get next milestone threshold."""
        if progress_percent < 25:
            return "25%"
        elif progress_percent < 50:
            return "50%"
        elif progress_percent < 75:
            return "75%"
        elif progress_percent < 100:
            return "100%"
        else:
            return "Complete"

    def _progress_to_next(self, progress_percent: float) -> float:
        """Percent progress to next milestone."""
        if progress_percent < 25:
            return progress_percent / 0.25
        elif progress_percent < 50:
            return (progress_percent - 25) / 0.25
        elif progress_percent < 75:
            return (progress_percent - 50) / 0.25
        elif progress_percent < 100:
            return (progress_percent - 75) / 0.25
        else:
            return 100.0


# Singleton instance
_instance = None


def get_skill():
    """Get or create skill instance."""
    global _instance
    if _instance is None:
        _instance = GoalStateTrackerSkill()
    return _instance
