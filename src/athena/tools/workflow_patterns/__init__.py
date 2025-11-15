"""Phase 3b Workflow Pattern Tools - Filesystem Discoverable.

Agents can discover and use these tools to analyze workflow patterns
and get intelligent task suggestions based on historical data.

Available tools:
- analyze_workflow_patterns: Mine patterns from completed tasks
- get_typical_workflow: Get standard workflow for task type
- suggest_next_task_with_patterns: Smart suggestions based on patterns
- find_workflow_anomalies: Find unusual task sequences
- get_pattern_metrics: Get pattern statistics
- assess_workflow_risk: Risk assessment for transitions
- get_typical_workflow_steps: Get workflow step chain

Usage:
    1. Discover tools: ls /athena/tools/workflow_patterns/
    2. Read tool definition: cat /athena/tools/workflow_patterns/analyze_workflow_patterns.py
    3. Use the tool (see tool file for import path)
"""

__all__ = [
    "analyze_workflow_patterns",
    "get_typical_workflow",
    "suggest_next_task_with_patterns",
    "find_workflow_anomalies",
    "get_pattern_metrics",
    "assess_workflow_risk",
    "get_typical_workflow_steps",
]
