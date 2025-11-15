"""assess_workflow_risk - Assess risk of a task transition.

Part of Phase 3b: Workflow Pattern Mining
"""

from typing import Dict, Any, Optional


def assess_workflow_risk(
    project_id: int,
    from_task_type: str,
    to_task_type: str,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Assess risk level of a proposed task transition.

    Evaluates whether a task sequence is on-track or anomalous.
    Helps identify risky shortcuts or unusual workflows.

    Args:
        project_id (int): Project ID
        from_task_type (str): Current task type
        to_task_type (str): Proposed next task type
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with risk assessment and recommendations

    Examples:
        >>> assess_workflow_risk(project_id=1, from_task_type='implement', to_task_type='deploy')
        {
            'from_type': 'implement',
            'to_type': 'deploy',
            'risk_level': 'high',
            'confidence': 0.08,
            'frequency': 2,
            'message': 'Skipping test step is unusual (only 8% do this)',
            'recommendation': 'Consider adding testing before deployment'
        }

    Risk levels:
        - low: Normal workflow (>20% frequency)
        - medium: Possible concern (5-20% frequency)
        - high: Unusual workflow (<5% frequency)

    Use this to:
        - Validate task sequences
        - Catch risky shortcuts
        - Ensure process compliance
        - Flag unusual workflows for review
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..workflow.suggestions import PatternSuggestionEngine

        engine = PatternSuggestionEngine(db)

        # Get risk assessment for this transition
        risk = engine.get_risk_assessment(project_id, from_task_type, to_task_type)

        if not risk:
            return {
                "from_type": from_task_type,
                "to_type": to_task_type,
                "risk_level": "unknown",
                "message": "No historical data for this transition",
                "recommendation": "Continue; assess risk once more data available",
            }

        return risk

    except Exception as e:
        return {
            "error": f"Failed to assess workflow risk: {str(e)}",
            "from_type": from_task_type,
            "to_type": to_task_type,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "assess_workflow_risk"
__tool_category__ = "workflow_patterns"
__tool_summary__ = "Assess risk of a task transition"
__tool_version__ = "1.0.0"
__tool_tags__ = ["workflow", "risk", "assessment", "validation", "quality"]
