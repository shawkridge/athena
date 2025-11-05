"""Priority Calculator Skill - Composite goal scoring."""

from typing import Any, Dict, List
from datetime import datetime
from .base_skill import BaseSkill, SkillResult


class PriorityCalculatorSkill(BaseSkill):
    """Calculates and ranks goals by composite priority score."""

    def __init__(self):
        super().__init__(
            skill_id="priority-calculator",
            skill_name="Priority Calculator"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate priority scores for all goals.

        Score = 40% Priority + 35% Deadline + 15% Progress + 10% On-Track
        """
        try:
            goals = context.get('goals', [])

            if not goals:
                return SkillResult(
                    status="skipped",
                    data={"reason": "No goals to rank"}
                ).to_dict()

            # Score all goals
            scored = []
            for goal in goals:
                score = self._calculate_score(goal)
                scored.append({
                    "goal_id": goal['id'],
                    "goal_name": goal.get('name', 'Unknown'),
                    "score": score,
                    "tier": self._get_tier(score),
                    "components": self._get_components(goal),
                })

            # Sort by score
            ranked = sorted(scored, key=lambda g: g['score'], reverse=True)

            result = SkillResult(
                status="success",
                data={
                    "ranked_goals": ranked,
                    "total_goals": len(ranked),
                    "critical_count": sum(1 for g in ranked if g['tier'] == "CRITICAL"),
                    "high_count": sum(1 for g in ranked if g['tier'] == "HIGH"),
                    "timestamp": datetime.now().isoformat(),
                },
                actions=[
                    f"Highest priority: Goal #{ranked[0]['goal_id']}" if ranked else "",
                    "Run /priorities for full breakdown",
                ] if ranked else []
            )

            self._log_execution(result.to_dict())
            return result.to_dict()

        except Exception as e:
            return SkillResult(status="failed", error=str(e)).to_dict()

    def _calculate_score(self, goal: Dict) -> float:
        """Calculate composite priority score."""
        priority = goal.get('priority', 5) / 10.0  # Normalize 0-1
        deadline_urgency = self._calc_deadline_urgency(goal)
        progress = goal.get('progress', 0) / goal.get('total_steps', 100)
        on_track = 1.0 if goal.get('on_track', False) else -0.1

        return (
            priority * 0.40 +
            deadline_urgency * 0.35 +
            progress * 0.15 +
            on_track * 0.10
        ) * 10

    def _calc_deadline_urgency(self, goal: Dict) -> float:
        """Calculate deadline urgency (0-1)."""
        from datetime import datetime, timedelta
        deadline_str = goal.get('deadline', '')
        if not deadline_str:
            return 0.5

        try:
            deadline = datetime.fromisoformat(deadline_str)
            days_left = (deadline - datetime.now()).days
            max_days = 30  # Reference
            urgency = max(0.0, min(1.0, 1.0 - (days_left / max_days)))
            return urgency
        except:
            return 0.5

    def _get_components(self, goal: Dict) -> Dict:
        """Get score component breakdown."""
        priority = goal.get('priority', 5) / 10.0 * 0.40
        deadline = self._calc_deadline_urgency(goal) * 0.35
        progress = (goal.get('progress', 0) / goal.get('total_steps', 100)) * 0.15
        on_track = (0.10 if goal.get('on_track', False) else -0.10)

        return {
            "priority_contrib": round(priority * 10, 1),
            "deadline_contrib": round(deadline * 10, 1),
            "progress_contrib": round(progress * 10, 1),
            "on_track_contrib": round(on_track * 10, 1),
        }

    def _get_tier(self, score: float) -> str:
        """Get priority tier."""
        if score >= 8:
            return "CRITICAL"
        elif score >= 6:
            return "HIGH"
        elif score >= 4:
            return "MEDIUM"
        else:
            return "LOW"


_instance = None

def get_skill():
    global _instance
    if _instance is None:
        _instance = PriorityCalculatorSkill()
    return _instance
