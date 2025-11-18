"""get_accuracy_stats - Get accuracy statistics for a task type.

Part of Phase 3c: Predictive Analytics
"""

from typing import Dict, Any, Optional


def get_accuracy_stats(
    project_id: int,
    task_type: str,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get accuracy statistics for a task type.

    Returns historical accuracy data that shows how well you estimate
    a particular type of task. Useful for understanding bias patterns.

    Args:
        project_id (int): Project ID
        task_type (str): Task type (e.g., 'feature', 'bugfix')
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with accuracy stats including bias factor and recommendation

    Examples:
        >>> get_accuracy_stats(project_id=1, task_type='feature')
        {
            'task_type': 'feature',
            'accuracy_percent': 87.0,
            'bias_factor': 1.15,
            'variance': 0.12,
            'sample_count': 25,
            'confidence': 'high',
            'recommendation': 'Multiply estimates by 1.15x to account for 15% underestimation'
        }

    Statistics explained:
        - accuracy_percent: How often are you close? (0-100%)
          - 100% = perfect estimates
          - 50% = estimates off by 2x
        - bias_factor: Systematic over/under-estimation
          - 1.15 = underestimate by 15%
          - 0.90 = overestimate by 10%
          - 1.00 = well-calibrated
        - variance: Consistency of estimates
          - Low (0.0-0.2) = predictable
          - Medium (0.2-0.4) = somewhat variable
          - High (>0.4) = unpredictable
        - sample_count: Number of similar completed tasks
          - <5 = not enough data
          - 5-15 = reasonable data
          - >15 = strong historical base
        - confidence: How much to trust the stats
          - low = need more data
          - medium = reasonable confidence
          - high = strong confidence
    """

    try:
        if db is None:
            from ..core.database import Database

            db = Database()

        from ..predictive.accuracy import EstimateAccuracyStore

        store = EstimateAccuracyStore(db)
        return store.get_type_accuracy_stats(project_id, task_type) or {
            "message": f"No accuracy data yet for task type: {task_type}",
            "recommendation": "Complete 5+ tasks of this type to gather statistics",
        }

    except Exception as e:
        return {
            "error": f"Failed to get accuracy stats: {str(e)}",
            "task_type": task_type,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "get_accuracy_stats"
__tool_category__ = "predictive_analytics"
__tool_summary__ = "Get accuracy statistics for a task type"
__tool_version__ = "1.0.0"
__tool_tags__ = ["estimation", "accuracy", "statistics", "bias", "analysis"]
