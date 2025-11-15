"""analyze_workflow_patterns - Mine patterns from completed task sequences.

Part of Phase 3b: Workflow Pattern Mining
"""

from typing import Dict, Any, Optional


def analyze_workflow_patterns(
    project_id: int,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Analyze completed task sequences to discover implicit workflow patterns.

    Mines completed tasks to find typical task sequences and patterns.
    Calculates confidence scores based on frequency and consistency.

    Args:
        project_id (int): Project ID
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with patterns discovered, statistics, and process maturity

    Examples:
        >>> analyze_workflow_patterns(project_id=1)
        {
            'patterns_found': 45,
            'task_types': 8,
            'statistics': {
                'avg_confidence': 0.74,
                'high_confidence': 22,
                'anomalies': 3
            },
            'process_maturity': 'high'
        }

    Key metrics returned:
        - patterns_found: Number of task transitions discovered
        - task_types: How many different types of tasks
        - avg_confidence: Average confidence across all patterns
        - high_confidence: Count of high-confidence patterns (>70%)
        - anomalies: Unusual transitions detected
        - process_maturity: Assessment of workflow consistency

    Use this to:
        - Understand typical workflow for your project
        - Identify standard task sequences
        - Detect unusual patterns that need investigation
        - Measure process maturity and consistency
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..workflow.analyzer import TaskSequenceAnalyzer

        analyzer = TaskSequenceAnalyzer(db)
        result = analyzer.analyze_completed_sequences(project_id)

        if "error" in result:
            return result

        # Add statistics
        stats = analyzer.get_pattern_statistics(project_id)
        if stats:
            result["statistics"] = stats

        return result

    except Exception as e:
        return {
            "error": f"Failed to analyze workflow patterns: {str(e)}",
            "project_id": project_id,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "analyze_workflow_patterns"
__tool_category__ = "workflow_patterns"
__tool_summary__ = "Mine patterns from completed task sequences"
__tool_version__ = "1.0.0"
__tool_tags__ = ["workflow", "patterns", "analysis", "mining", "learning"]
