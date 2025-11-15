"""analyze_high_variance_tasks - Identify task types that are hardest to estimate.

Part of Phase 3c: Predictive Analytics
"""

from typing import Dict, Any, Optional, List


def analyze_high_variance_tasks(
    project_id: int,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Identify task types that are hardest to estimate (high variance).

    Shows which task types have unpredictable estimates and need attention.
    These are candidates for decomposition into smaller, more predictable tasks.

    Args:
        project_id (int): Project ID
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        List of task types ranked by estimation difficulty (variance)

    Examples:
        >>> analyze_high_variance_tasks(project_id=1)
        {
            'high_variance_tasks': [
                {
                    'task_type': 'refactor',
                    'variance': 0.45,
                    'sample_count': 8,
                    'accuracy_percent': 68.0
                },
                {
                    'task_type': 'investigation',
                    'variance': 0.38,
                    'sample_count': 5,
                    'accuracy_percent': 60.0
                }
            ],
            'summary': '2 task types have high variance (hardest to estimate)',
            'recommendation': 'Consider breaking these tasks into smaller, more predictable subtasks'
        }

    High variance indicators:
        - variance > 0.3: Unpredictable (need improvement)
        - variance > 0.4: Very unpredictable (priority improvement)
        - variance < 0.2: Predictable (good estimation)

    Why high variance matters:
        1. Estimation accuracy suffers
        2. Planning becomes harder
        3. Buffer allocation becomes larger
        4. Confidence in predictions drops to "low"

    How to address high variance:
        1. Break tasks into smaller subtasks
        2. Add more detail to task description
        3. Gather more historical data (5+ samples)
        4. Apply different estimation technique
        5. Consider if task type definition is too broad

    Example improvements:
        Before: "Refactor authentication" (variance 0.45, unpredictable)
        After:  "Extract AuthService", "Update tests", "Refactor config" (variance 0.15 each)

        Before: "Investigation" (variance 0.38, very unpredictable)
        After:  "Setup test environment", "Write test case", "Find root cause" (variance 0.15-0.20)

    Variance calculation:
        - Low variance: Similar tasks take similar time
          → Estimates are reliable
          → Can plan with confidence
        - High variance: Similar tasks take very different times
          → Estimates are unreliable
          → Need wider buffers
          → Consider decomposition
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..predictive.accuracy import EstimateAccuracyStore

        store = EstimateAccuracyStore(db)
        all_stats = store.get_all_type_stats(project_id)

        if not all_stats:
            return {
                "message": "No estimation data yet. Complete several tasks first.",
                "high_variance_tasks": [],
                "next_step": "Track estimates and actual times as you complete tasks",
            }

        # Filter for high variance (>0.2)
        high_variance = sorted(
            [s for s in all_stats if s.get("variance", 0) > 0.2],
            key=lambda x: x.get("variance", 0),
            reverse=True,
        )

        if not high_variance:
            return {
                "message": "All task types have consistent estimates.",
                "high_variance_tasks": [],
                "overall_assessment": "Your estimation is well-calibrated across all task types.",
            }

        return {
            "high_variance_tasks": high_variance,
            "summary": f"{len(high_variance)} task types have high variance (hardest to estimate)",
            "recommendation": "Consider breaking these tasks into smaller, more predictable subtasks",
            "variance_explained": _explain_variance_levels(),
        }

    except Exception as e:
        return {
            "error": f"Failed to analyze high variance tasks: {str(e)}",
            "project_id": project_id,
        }


def _explain_variance_levels() -> Dict[str, str]:
    """Explain variance levels."""
    return {
        "low_variance": "variance < 0.2 (predictable, reliable estimates)",
        "medium_variance": "0.2 < variance < 0.4 (somewhat unpredictable)",
        "high_variance": "variance > 0.4 (very unpredictable, needs improvement)",
    }


# Tool metadata for filesystem discovery
__tool_name__ = "analyze_high_variance_tasks"
__tool_category__ = "predictive_analytics"
__tool_summary__ = "Identify task types that are hardest to estimate"
__tool_version__ = "1.0.0"
__tool_tags__ = ["estimation", "variance", "analysis", "improvement", "decomposition"]
