"""get_prediction_range - Get low/medium/high estimate ranges for a task.

Part of Phase 3c: Predictive Analytics
"""

from typing import Dict, Any, Optional


def get_prediction_range(
    project_id: int,
    task_type: str,
    base_estimate: int,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get low/medium/high estimate ranges for a task.

    Provides three scenarios for planning with uncertainty:
    - Optimistic: Best case scenario (when everything goes right)
    - Expected: Most likely outcome (based on historical averages)
    - Pessimistic: Worst case scenario (accounting for delays)

    Args:
        project_id (int): Project ID
        task_type (str): Task type (e.g., 'feature', 'bugfix')
        base_estimate (int): Base estimate in minutes
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with optimistic/expected/pessimistic estimates

    Examples:
        >>> get_prediction_range(project_id=1, task_type='feature', base_estimate=120)
        {
            'task_type': 'feature',
            'base_estimate': 120,
            'range': {
                'optimistic': 120,    # Best case
                'expected': 138,      # Most likely
                'pessimistic': 160    # Worst case
            },
            'summary': 'Estimate range: 120-160 minutes (expected: 138)'
        }

    How ranges work:
        1. Start with base_estimate
        2. Apply bias factor: predicted = base × bias_factor
        3. Apply confidence-based variance:
           - High confidence: ±15% range (tight, reliable)
           - Medium confidence: ±30% range (moderate variance)
           - Low confidence: ±50% range (wide, need more data)
        4. Calculate bounds:
           - optimistic = predicted / (1 + variance_factor)
           - pessimistic = predicted × (1 + variance_factor)

    Use this for:
        - Sprint planning (what's realistic?)
        - Buffer allocation (what's the worst case?)
        - Risk management (plan for pessimistic case)
        - Client communication (give range instead of point estimate)
    """

    try:
        if db is None:
            from ..core.database import Database

            db = Database()

        from ..predictive.estimator import PredictiveEstimator

        estimator = PredictiveEstimator(db)
        range_data = estimator.get_estimate_range(project_id, task_type, base_estimate)

        if not range_data:
            return {
                "message": f"No estimation data for {task_type}. Using base estimate.",
                "range": {
                    "optimistic": int(base_estimate * 0.8),
                    "expected": base_estimate,
                    "pessimistic": int(base_estimate * 1.2),
                },
            }

        return {
            "task_type": task_type,
            "base_estimate": base_estimate,
            "range": range_data,
            "summary": f"Estimate range: {range_data['optimistic']}-{range_data['pessimistic']} minutes "
            f"(expected: {range_data['expected']})",
        }

    except Exception as e:
        return {
            "error": f"Failed to get prediction range: {str(e)}",
            "task_type": task_type,
            "base_estimate": base_estimate,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "get_prediction_range"
__tool_category__ = "predictive_analytics"
__tool_summary__ = "Get low/medium/high estimate ranges for a task"
__tool_version__ = "1.0.0"
__tool_tags__ = ["estimation", "range", "scenario-planning", "risk-management"]
