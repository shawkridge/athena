"""get_estimation_confidence - Get confidence level for estimates of a task type.

Part of Phase 3c: Predictive Analytics
"""

from typing import Dict, Any, Optional


def get_estimation_confidence(
    project_id: int,
    task_type: str,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get confidence level for estimates of a task type.

    Tells you how much to trust predictions for this task type.
    Higher confidence = more historical data and more consistent estimates.

    Args:
        project_id (int): Project ID
        task_type (str): Task type (e.g., 'feature', 'bugfix')
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with confidence level and explanation

    Examples:
        >>> get_estimation_confidence(project_id=1, task_type='feature')
        {
            'task_type': 'feature',
            'confidence': 'high',
            'sample_count': 25,
            'explanation': 'High confidence (25 samples). Strong historical data supports these predictions.'
        }

    Confidence levels:
        - low: <5 similar tasks
          → "Need more data before trusting predictions"
        - medium: 5-15 similar tasks (or high variance)
          → "Predictions reasonably reliable but watch for variations"
        - high: >15 similar tasks with low variance
          → "Strong historical data supports these predictions"

    Use this to decide:
        - Trust adjustments? (high confidence = yes)
        - More data needed? (low confidence = maybe collect more)
        - Wide estimate ranges? (low confidence = wider ranges)
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..predictive.estimator import PredictiveEstimator

        estimator = PredictiveEstimator(db)
        confidence = estimator.get_estimation_confidence(project_id, task_type)

        stats = estimator.accuracy_store.get_type_accuracy_stats(
            project_id, task_type
        )
        sample_count = stats.get("sample_count", 0) if stats else 0

        # Generate explanation
        if confidence == "low":
            explanation = (
                f"Low confidence ({sample_count} samples). Need at least 5 similar tasks "
                "for reliable predictions."
            )
        elif confidence == "medium":
            explanation = (
                f"Medium confidence ({sample_count} samples). "
                "Predictions reasonably reliable but watch for variations."
            )
        else:  # high
            explanation = (
                f"High confidence ({sample_count} samples). "
                "Strong historical data supports these predictions."
            )

        return {
            "task_type": task_type,
            "confidence": confidence,
            "sample_count": sample_count,
            "explanation": explanation,
        }

    except Exception as e:
        return {
            "error": f"Failed to get confidence: {str(e)}",
            "task_type": task_type,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "get_estimation_confidence"
__tool_category__ = "predictive_analytics"
__tool_summary__ = "Get confidence level for estimates of a task type"
__tool_version__ = "1.0.0"
__tool_tags__ = ["estimation", "confidence", "reliability", "data-quality"]
