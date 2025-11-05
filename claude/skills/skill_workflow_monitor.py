"""Workflow Monitor Skill - Track workflow state and health."""

from typing import Any, Dict, List
from datetime import datetime
from .base_skill import BaseSkill, SkillResult


class WorkflowMonitorSkill(BaseSkill):
    """Monitors execution state and health of active workflows."""

    def __init__(self):
        super().__init__(
            skill_id="workflow-monitor",
            skill_name="Workflow Monitor"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor workflow state and health.

        Tracks:
        - Active goals and progress
        - Timeline progress
        - Resource utilization
        - Risk indicators
        """
        try:
            active_goals = context.get('active_goals', [])
            timeline_start = context.get('timeline_start')
            timeline_end = context.get('timeline_end')

            if not active_goals:
                return SkillResult(
                    status="skipped",
                    data={"reason": "No active goals"}
                ).to_dict()

            # Calculate timeline progress
            timeline = self._calc_timeline(timeline_start, timeline_end)

            # Calculate health metrics
            overall_health = self._calc_health(active_goals)

            # Identify risks
            risks = self._identify_risks(active_goals)

            result = SkillResult(
                status="success",
                data={
                    "workflow_state": "ACTIVE",
                    "active_goal_count": len(active_goals),
                    "timeline": timeline,
                    "health_score": overall_health,
                    "health_rating": self._rate_health(overall_health),
                    "risks": risks,
                    "resource_utilization": self._calc_resource_util(active_goals),
                    "timestamp": datetime.now().isoformat(),
                },
                actions=[
                    "✓ Workflow healthy" if overall_health > 0.7 else "⚠️ Health degraded",
                    "/workflow-status (for full dashboard)" if active_goals else "",
                ] if active_goals else []
            )

            self._log_execution(result.to_dict())
            return result.to_dict()

        except Exception as e:
            return SkillResult(status="failed", error=str(e)).to_dict()

    def _calc_timeline(self, start: str, end: str) -> Dict:
        """Calculate timeline progress."""
        try:
            from datetime import datetime
            start_date = datetime.fromisoformat(start) if start else datetime.now()
            end_date = datetime.fromisoformat(end) if end else datetime.now()

            total_days = (end_date - start_date).days or 1
            elapsed = (datetime.now() - start_date).days
            progress_percent = min(100, (elapsed / total_days * 100) if total_days else 0)

            return {
                "start": start,
                "end": end,
                "total_days": total_days,
                "elapsed_days": elapsed,
                "progress_percent": progress_percent,
                "status": "ON_TRACK" if progress_percent <= 50 else "AT_RISK" if progress_percent <= 80 else "CRITICAL",
            }
        except:
            return {"error": "Could not calculate timeline"}

    def _calc_health(self, goals: List[Dict]) -> float:
        """Calculate overall workflow health (0-1)."""
        if not goals:
            return 1.0

        goal_healths = []
        for goal in goals:
            # Simple health: based on progress and blockers
            progress = goal.get('progress', 0) / max(1, goal.get('total_steps', 1))
            blockers = goal.get('blockers', 0)
            health = progress * (1.0 - min(0.3, blockers * 0.1))
            goal_healths.append(health)

        return sum(goal_healths) / len(goal_healths) if goal_healths else 0.5

    def _rate_health(self, health: float) -> str:
        """Get health rating."""
        if health >= 0.8:
            return "🟢 EXCELLENT"
        elif health >= 0.6:
            return "🟡 GOOD"
        elif health >= 0.4:
            return "🟠 FAIR"
        else:
            return "🔴 POOR"

    def _identify_risks(self, goals: List[Dict]) -> List[str]:
        """Identify workflow risks."""
        risks = []

        total_blockers = sum(g.get('blockers', 0) for g in goals)
        if total_blockers > 2:
            risks.append(f"⚠️ {total_blockers} blockers detected")

        avg_health = sum(g.get('health', 0.7) for g in goals) / max(1, len(goals))
        if avg_health < 0.6:
            risks.append("⚠️ Average health below threshold")

        overdue = sum(1 for g in goals if g.get('days_overdue', 0) > 0)
        if overdue > 0:
            risks.append(f"⚠️ {overdue} goals overdue")

        return risks if risks else ["✓ No major risks detected"]

    def _calc_resource_util(self, goals: List[Dict]) -> Dict:
        """Calculate resource utilization."""
        total_effort = sum(g.get('estimated_hours', 40) for g in goals)
        available = 40 * len(goals)  # Assume multi-person
        utilization = (total_effort / available * 100) if available else 0

        return {
            "total_effort_hours": total_effort,
            "available_hours": available,
            "utilization_percent": utilization,
            "status": "HEALTHY" if utilization <= 85 else "WARNING" if utilization <= 100 else "OVERLOADED",
        }


_instance = None

def get_skill():
    global _instance
    if _instance is None:
        _instance = WorkflowMonitorSkill()
    return _instance
