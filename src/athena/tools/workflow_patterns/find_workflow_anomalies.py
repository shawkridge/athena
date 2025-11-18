"""find_workflow_anomalies - Find unusual task sequences.

Part of Phase 3b: Workflow Pattern Mining
"""

from typing import Dict, Any, Optional


def find_workflow_anomalies(
    project_id: int,
    confidence_threshold: float = 0.1,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Find unusual task sequences in workflow history.

    Identifies task transitions that deviate from typical patterns.
    Useful for detecting process deviations or unexpected workflows.

    Args:
        project_id (int): Project ID
        confidence_threshold (float): Anomaly threshold (default: 0.1 = 10% frequency)
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with anomalies and risk assessment

    Examples:
        >>> find_workflow_anomalies(project_id=1, confidence_threshold=0.1)
        {
            'anomalies': [
                {
                    'from_type': 'feature',
                    'to_type': 'deploy',
                    'frequency': 2,
                    'confidence': 0.08,
                    'risk': 'medium',
                    'message': 'Feature deployed without testing (8% of time)'
                }
            ],
            'total_anomalies': 1,
            'risk_level': 'low'
        }

    Anomaly classifications:
        - Rare (<5%): Very unusual, investigate
        - Unusual (5-10%): Possible risk, monitor
        - Occasional (10-20%): Normal variation
        - Common (>20%): Part of standard workflow

    Use this to:
        - Detect process deviations
        - Identify skipped steps (e.g., no testing)
        - Find risky shortcuts
        - Assess workflow consistency
    """

    try:
        if db is None:
            from ..core.database import Database

            db = Database()

        from ..workflow.analyzer import TaskSequenceAnalyzer

        analyzer = TaskSequenceAnalyzer(db)

        # Get all patterns and identify anomalies
        result = analyzer.analyze_completed_sequences(project_id)

        if "error" in result:
            return result

        # Look for low-confidence patterns (anomalies)
        anomalies = []
        if "patterns" in result:
            for pattern in result.get("patterns", []):
                confidence = pattern.get("confidence", 1.0)
                if confidence < confidence_threshold:
                    anomalies.append(
                        {
                            "from_type": pattern.get("from_type"),
                            "to_type": pattern.get("to_type"),
                            "confidence": confidence,
                            "frequency": pattern.get("frequency", 0),
                            "risk": _classify_risk(confidence),
                        }
                    )

        return {
            "anomalies": sorted(anomalies, key=lambda x: x.get("confidence", 1.0)),
            "total_anomalies": len(anomalies),
            "risk_level": _overall_risk_level(anomalies),
        }

    except Exception as e:
        return {
            "error": f"Failed to find anomalies: {str(e)}",
            "project_id": project_id,
        }


def _classify_risk(confidence: float) -> str:
    """Classify risk based on anomaly frequency."""
    if confidence < 0.05:
        return "high"
    elif confidence < 0.10:
        return "medium"
    else:
        return "low"


def _overall_risk_level(anomalies: list) -> str:
    """Calculate overall risk from anomalies."""
    if not anomalies:
        return "low"
    high_risk = sum(1 for a in anomalies if a.get("risk") == "high")
    if high_risk > 2:
        return "high"
    elif high_risk > 0:
        return "medium"
    return "low"


# Tool metadata for filesystem discovery
__tool_name__ = "find_workflow_anomalies"
__tool_category__ = "workflow_patterns"
__tool_summary__ = "Find unusual task sequences"
__tool_version__ = "1.0.0"
__tool_tags__ = ["workflow", "anomalies", "risk", "deviation", "detection"]
