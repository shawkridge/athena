"""get_estimation_trends - Get estimation accuracy trends over time.

Part of Phase 3c: Predictive Analytics
"""

from typing import Dict, Any, Optional


def get_estimation_trends(
    project_id: int,
    task_type: str,
    days_back: int = 90,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get estimation accuracy trends over time.

    Shows if you're getting better or worse at estimating a task type.
    Helps identify if process changes have improved accuracy.

    Args:
        project_id (int): Project ID
        task_type (str): Task type (e.g., 'feature', 'bugfix')
        days_back (int, optional): Number of days to analyze (default: 90)
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with trend direction and improvement percentage

    Examples:
        >>> get_estimation_trends(project_id=1, task_type='feature', days_back=90)
        {
            'task_type': 'feature',
            'trend': 'improving',
            'accuracy_90days_ago': 0.75,
            'accuracy_today': 0.87,
            'improvement': 0.12,
            'data_points': 12,
            'message': "Great! Your improving by 12%. Keep refining estimates."
        }

    Trend directions:
        - improving: +5% or more improvement in accuracy
          → "Great! Your improving by X%. Keep refining estimates."
        - degrading: -5% or more degradation in accuracy
          → "Caution: Estimates degrading by X%. Review estimation approach."
        - stable: Change within ±5%
          → "Estimates are stable. No significant trend detected."

    Why trends matter:
        - Learning signal: Shows if you're improving your estimation skills
        - Process impact: Detects if process changes helped or hurt
        - Regression detection: Warns if accuracy is getting worse
        - Confidence boost: Confirms if your new approach is working

    How trends are measured:
        1. Collect accuracy measurements over time period
        2. Compare first vs last measurement
        3. Calculate percentage improvement/degradation
        4. Classify as improving/stable/degrading
        5. Generate contextual message

    What to do:
        - Improving: "Keep current approach. You're learning."
        - Stable: "Monitor. Look for opportunities to improve."
        - Degrading: "Review recent changes. What changed?"
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..predictive.estimator import PredictiveEstimator

        estimator = PredictiveEstimator(db)
        trends = estimator.get_estimation_trends(project_id, task_type, days_back)

        if not trends:
            return {
                "message": f"Not enough historical data to determine trends for {task_type}",
                "task_type": task_type,
                "next_step": f"Complete more tasks and check back after {days_back} days",
            }

        return trends

    except Exception as e:
        return {
            "error": f"Failed to get trends: {str(e)}",
            "task_type": task_type,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "get_estimation_trends"
__tool_category__ = "predictive_analytics"
__tool_summary__ = "Get estimation accuracy trends over time"
__tool_version__ = "1.0.0"
__tool_tags__ = ["estimation", "trends", "improvement", "learning", "analytics"]
