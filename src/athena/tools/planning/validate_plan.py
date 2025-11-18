"""
VALIDATE_PLAN Tool - Validate plans using formal verification and scenario testing

This tool is discoverable via filesystem and directly executable.
Agents can import and call this function directly.

Usage:
    from athena.tools.planning.validate_plan import validate_plan
    result = validate_plan(plan, scenarios=5)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from athena.manager import UnifiedMemoryManager


def validate_plan(plan, scenarios: int = 5):
    """
    Validate a plan using formal verification and scenario testing

    Parameters:
        plan: Plan object to validate
        scenarios: Number of failure scenarios to test (default: 5)

    Returns:
        ValidationResult - Validity status, issues, and recommendations

    Example:
        >>> result = validate_plan(my_plan, scenarios=10)
        >>> if result.is_valid:
        ...     print("Plan is feasible!")
        ... else:
        ...     print(f"Issues: {result.issues}")

    Raises:
        ValueError: If plan is None or scenarios invalid
        RuntimeError: If validation process fails
    """
    if plan is None:
        raise ValueError("Plan cannot be None")

    if not isinstance(scenarios, int) or not (1 <= scenarios <= 20):
        raise ValueError(f"scenarios must be 1-20, got {scenarios}")

    try:
        manager = UnifiedMemoryManager()
        result = manager.validate_plan(plan=plan, scenarios=scenarios)
        return result
    except Exception as e:
        raise RuntimeError(f"Plan validation failed: {str(e)}") from e
