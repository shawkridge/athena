"""get_pattern_metrics - Get statistics on discovered patterns.

Part of Phase 3b: Workflow Pattern Mining
"""

from typing import Dict, Any, Optional


def get_pattern_metrics(
    project_id: int,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get detailed statistics on discovered workflow patterns.

    Returns metrics about pattern quality, consistency, and maturity.

    Args:
        project_id (int): Project ID
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with pattern metrics and maturity assessment

    Examples:
        >>> get_pattern_metrics(project_id=1)
        {
            'total_patterns': 45,
            'avg_confidence': 0.74,
            'high_confidence_patterns': 22,
            'medium_confidence_patterns': 18,
            'low_confidence_patterns': 5,
            'process_maturity': 'high',
            'consistency_score': 0.85,
            'anomaly_count': 3,
            'data_quality': 'good'
        }

    Metrics explained:
        - avg_confidence: How reliable are patterns? (0-1)
        - process_maturity: High/Medium/Low based on consistency
        - consistency_score: How predictable is your workflow? (0-1)
        - data_quality: Good/Fair/Poor based on sample size

    Use this to:
        - Assess workflow maturity
        - Understand pattern reliability
        - Identify process improvement areas
        - Gauge data quality for predictions
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..workflow.analyzer import TaskSequenceAnalyzer

        analyzer = TaskSequenceAnalyzer(db)

        # Get pattern statistics
        stats = analyzer.get_pattern_statistics(project_id)

        if not stats:
            return {
                "message": "No pattern data available",
                "project_id": project_id,
                "next_step": "Complete 10+ tasks to generate pattern statistics",
            }

        return stats

    except Exception as e:
        return {
            "error": f"Failed to get pattern metrics: {str(e)}",
            "project_id": project_id,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "get_pattern_metrics"
__tool_category__ = "workflow_patterns"
__tool_summary__ = "Get statistics on discovered patterns"
__tool_version__ = "1.0.0"
__tool_tags__ = ["workflow", "patterns", "metrics", "statistics", "maturity"]
