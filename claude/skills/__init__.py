"""Phase 3 Executive Function Skills Package."""

from .skill_goal_state_tracker import GoalStateTrackerSkill, get_skill as get_goal_state_tracker
from .skill_strategy_selector import StrategySelectorSkill, get_skill as get_strategy_selector
from .skill_conflict_detector import ConflictDetectorSkill, get_skill as get_conflict_detector
from .skill_priority_calculator import PriorityCalculatorSkill, get_skill as get_priority_calculator
from .skill_workflow_monitor import WorkflowMonitorSkill, get_skill as get_workflow_monitor

__all__ = [
    "GoalStateTrackerSkill",
    "StrategySelectorSkill",
    "ConflictDetectorSkill",
    "PriorityCalculatorSkill",
    "WorkflowMonitorSkill",
    "get_goal_state_tracker",
    "get_strategy_selector",
    "get_conflict_detector",
    "get_priority_calculator",
    "get_workflow_monitor",
]

# Skill registry for auto-triggering
SKILLS = {
    "goal-state-tracker": get_goal_state_tracker,
    "strategy-selector": get_strategy_selector,
    "conflict-detector": get_conflict_detector,
    "priority-calculator": get_priority_calculator,
    "workflow-monitor": get_workflow_monitor,
}


async def execute_skill(skill_id: str, context: dict):
    """Execute a skill by ID.

    Args:
        skill_id: Skill identifier
        context: Execution context

    Returns:
        Skill result dict
    """
    if skill_id not in SKILLS:
        return {"status": "error", "error": f"Unknown skill: {skill_id}"}

    skill = SKILLS[skill_id]()
    return await skill.execute(context)
