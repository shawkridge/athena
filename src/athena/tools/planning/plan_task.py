"""
PLAN_TASK Tool - Decompose tasks into executable hierarchical plans

This tool is discoverable via filesystem and directly executable.
Agents can import and call this function directly.

Usage:
    from athena.tools.planning.plan_task import plan_task
    plan = plan_task('Implement user authentication', depth=4)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from athena.manager import UnifiedMemoryManager


def plan_task(description: str, depth: int = 3, include_risks: bool = True):
    """
    Decompose a task into an executable hierarchical plan

    Parameters:
        description: Task description (what needs to be done)
        depth: Planning depth - how many levels of subtasks (1-5, default: 3)
        include_risks: Include risk analysis in plan (default: True)

    Returns:
        Plan - Hierarchical task breakdown with steps, effort estimates, dependencies

    Example:
        >>> plan = plan_task('Implement user authentication', depth=4)
        >>> print(f"Task has {len(plan.steps)} top-level steps")
        >>> print(f"Estimated effort: {plan.estimated_hours} hours")

    Raises:
        ValueError: If description empty or depth invalid
        RuntimeError: If planning process fails
    """
    if not description or not description.strip():
        raise ValueError("Task description cannot be empty")

    if not isinstance(depth, int) or not (1 <= depth <= 5):
        raise ValueError(f"Planning depth must be 1-5, got {depth}")

    try:
        manager = UnifiedMemoryManager()
        plan = manager.plan_task(description=description, depth=depth)
        return plan
    except Exception as e:
        raise RuntimeError(f"Task planning failed: {str(e)}") from e

