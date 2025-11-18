"""get_bias_recommendations - Get adjustment recommendations based on bias.

Part of Phase 3c: Predictive Analytics
"""

from typing import Dict, Any, Optional


def get_bias_recommendations(
    project_id: int,
    task_type: str,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get adjustment recommendations based on estimation bias.

    Shows if you systematically over or under-estimate a task type,
    and provides specific recommendations to improve accuracy.

    Args:
        project_id (int): Project ID
        task_type (str): Task type (e.g., 'feature', 'bugfix')
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with bias factor and specific adjustment recommendation

    Examples:
        >>> get_bias_recommendations(project_id=1, task_type='feature')
        {
            'task_type': 'feature',
            'bias_factor': 1.15,
            'confidence': 'high',
            'sample_count': 25,
            'recommendation': 'Multiply estimates by 1.15x to account for 15% underestimation'
        }

    Recommendations generated:
        - If bias_factor > 1.05: "Multiply by X to account for underestimation"
        - If bias_factor < 0.95: "Reduce by X to account for overestimation"
        - If -0.05 < bias < 0.05: "Estimates are well-calibrated. Keep current approach."
        - If sample_count < 5: "Gather more data before adjusting estimates"
        - If variance > 0.3: "Small bias detected. Monitor for trends."

    Bias Factor explained:
        - 1.15 = Actual time is 115% of estimate
          → You underestimate by 15%
          → Apply: multiply estimates by 1.15
        - 0.90 = Actual time is 90% of estimate
          → You overestimate by 10%
          → Apply: multiply estimates by 0.90 (or reduce by 10%)
        - 1.00 = Perfect calibration
          → Your estimates are accurate
          → No adjustment needed

    How to use recommendations:
        1. Get recommendation for task type
        2. Apply factor to future estimates
        3. After 10+ more tasks, re-check
        4. Adjust if bias changes
    """

    try:
        if db is None:
            from ..core.database import Database

            db = Database()

        from ..predictive.accuracy import EstimateAccuracyStore

        store = EstimateAccuracyStore(db)
        stats = store.get_type_accuracy_stats(project_id, task_type)

        if not stats:
            return {
                "message": f"No data yet for {task_type}. Complete 5+ tasks to get recommendations.",
                "task_type": task_type,
                "next_step": "Track estimates and actual times for future tasks",
            }

        bias_factor = stats.get("bias_factor", 1.0)
        confidence = stats.get("confidence", "low")
        sample_count = stats.get("sample_count", 0)
        recommendation = stats.get("recommendation", "Gather more data")

        return {
            "task_type": task_type,
            "bias_factor": round(bias_factor, 2),
            "confidence": confidence,
            "sample_count": sample_count,
            "recommendation": recommendation,
            "how_to_apply": _explain_how_to_apply(bias_factor),
        }

    except Exception as e:
        return {
            "error": f"Failed to get recommendations: {str(e)}",
            "task_type": task_type,
        }


def _explain_how_to_apply(bias_factor: float) -> str:
    """Explain how to apply the bias factor."""
    if bias_factor > 1.05:
        return f"Multiply future estimates by {bias_factor:.2f} to account for underestimation"
    elif bias_factor < 0.95:
        return f"Multiply future estimates by {bias_factor:.2f} to account for overestimation"
    else:
        return "Your estimates are well-calibrated. No adjustment needed."


# Tool metadata for filesystem discovery
__tool_name__ = "get_bias_recommendations"
__tool_category__ = "predictive_analytics"
__tool_summary__ = "Get adjustment recommendations based on estimation bias"
__tool_version__ = "1.0.0"
__tool_tags__ = ["estimation", "bias", "recommendations", "improvement"]
