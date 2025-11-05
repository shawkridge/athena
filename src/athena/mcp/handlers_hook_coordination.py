"""Hook Coordination handlers: Optimized hook implementations using Phase 5-6 tools (5 operations).

These handlers expose optimized implementations of the 5 key hooks that leverage Phase 5-6
operations for improved task monitoring, planning validation, and pattern extraction.
"""

import json
import logging
from typing import Any, List
from mcp.types import TextContent

logger = logging.getLogger(__name__)


# HOOK COORDINATION: Hook Optimization Handlers (5 operations)
# These handlers coordinate complex hook behavior patterns using Phase 5-6 tools


async def handle_optimize_session_start(server: Any, args: dict) -> List[TextContent]:
    """Optimize SessionStart hook: Load context + validate active goal plans.

    Combines memory loading with Phase 6 plan validation:
    1. Load context via smart_retrieve
    2. Check cognitive load
    3. Load active goals
    4. Validate each goal's plan (structure + feasibility)
    5. Check consolidation cycle status

    Args:
        project_id: Current project ID (optional)
        validate_plans: Whether to validate goal plans (default: true)

    Returns:
        Session start state with context, load, goals, and plan issues
    """
    try:
        project_id = args.get("project_id")
        validate_plans = args.get("validate_plans", True)

        # Lazy initialization
        if not hasattr(server, '_session_optimizer'):
            from ..integration.hook_coordination import SessionStartOptimizer
            server._session_optimizer = SessionStartOptimizer(server.store.db)

        try:
            result = await server._session_optimizer.execute(
                project_id=project_id,
                validate_plans=validate_plans
            )
        except Exception as op_err:
            logger.error(f"Session start optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "context_loaded": False,
                "cognitive_load": 0,
                "active_goals": [],
                "plan_validation_issues": []
            }

        # Format response
        response = f"""**Optimized SessionStart Hook**
Status: {result.get('status', 'unknown')}
Context Loaded: {result.get('context_loaded', False)}
Cognitive Load: {result.get('cognitive_load', 0)}/7
Active Goals: {len(result.get('active_goals', []))}
Plan Issues Found: {len(result.get('plan_validation_issues', []))}

Plan Validation Details:
{_format_plan_issues(result.get('plan_validation_issues', []))}

Consolidation Status:
- Age: {result.get('consolidation_age_hours', -1)} hours
- Status: {result.get('consolidation_status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_session_start: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_session_end(server: Any, args: dict) -> List[TextContent]:
    """Optimize SessionEnd hook: Extract patterns + measure consolidation quality.

    Combines memory consolidation with Phase 6 pattern extraction:
    1. Run consolidation cycle
    2. Strengthen associations
    3. Extract planning patterns from completed tasks
    4. Measure consolidation quality (compression/recall/consistency)
    5. Record execution progress

    Args:
        session_id: Current session ID
        extract_patterns: Whether to extract patterns (default: true)
        measure_quality: Whether to measure consolidation quality (default: true)

    Returns:
        Session end state with consolidation results and pattern extraction
    """
    try:
        session_id = args.get("session_id")
        extract_patterns = args.get("extract_patterns", True)
        measure_quality = args.get("measure_quality", True)

        if not hasattr(server, '_session_end_optimizer'):
            from ..integration.hook_coordination import SessionEndOptimizer
            server._session_end_optimizer = SessionEndOptimizer(server.store.db)

        try:
            result = await server._session_end_optimizer.execute(
                session_id=session_id,
                extract_patterns=extract_patterns,
                measure_quality=measure_quality
            )
        except Exception as op_err:
            logger.error(f"Session end optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "consolidation_events": 0,
                "patterns_extracted": 0,
                "quality_score": 0
            }

        # Format response
        response = f"""**Optimized SessionEnd Hook**
Status: {result.get('status', 'unknown')}
Consolidation:
- Events Consolidated: {result.get('consolidation_events', 0)}
- Duration: {result.get('consolidation_duration_ms', 0)}ms
- Strategy Used: {result.get('consolidation_strategy', 'unknown')}

Pattern Extraction:
- Patterns Extracted: {result.get('patterns_extracted', 0)}
- Tasks Analyzed: {result.get('tasks_analyzed', 0)}

Quality Metrics:
- Overall Score: {result.get('quality_score', 0):.2f}
- Compression: {result.get('compression_ratio', 0):.2f}
- Recall: {result.get('recall_score', 0):.2f}
- Consistency: {result.get('consistency_score', 0):.2f}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_session_end: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_user_prompt_submit(server: Any, args: dict) -> List[TextContent]:
    """Optimize UserPromptSubmit hook: Monitor task health + suggest improvements.

    Adds real-time task monitoring to user prompt handling:
    1. Detect knowledge gaps
    2. Manage attention focus
    3. Monitor active task health
    4. Trigger replanning if health degraded
    5. Analyze project patterns for improvements

    Args:
        project_id: Current project ID
        monitor_health: Whether to monitor task health (default: true)

    Returns:
        Prompt analysis with gaps, health status, and improvement suggestions
    """
    try:
        project_id = args.get("project_id")
        monitor_health = args.get("monitor_health", True)

        if not hasattr(server, '_prompt_optimizer'):
            from ..integration.hook_coordination import UserPromptOptimizer
            server._prompt_optimizer = UserPromptOptimizer(server.store.db)

        try:
            result = await server._prompt_optimizer.execute(
                project_id=project_id,
                monitor_health=monitor_health
            )
        except Exception as op_err:
            logger.error(f"User prompt optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "gaps_detected": 0,
                "tasks_monitored": 0,
                "health_warnings": []
            }

        # Format response
        response = f"""**Optimized UserPromptSubmit Hook**
Status: {result.get('status', 'unknown')}

Knowledge Gaps:
- Gaps Detected: {len(result.get('gaps_detected', []))}
{_format_gaps(result.get('gaps_detected', []))}

Task Health Monitoring:
- Tasks Analyzed: {result.get('tasks_monitored', 0)}
- Health Warnings: {len(result.get('health_warnings', []))}
{_format_health_warnings(result.get('health_warnings', []))}

Improvement Opportunities:
- Suggestions: {len(result.get('improvement_suggestions', []))}
{_format_suggestions(result.get('improvement_suggestions', []))}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_user_prompt_submit: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_post_tool_use(server: Any, args: dict) -> List[TextContent]:
    """Optimize PostToolUse hook: Track performance + update task progress.

    Adds Phase 5 performance analytics to tool execution:
    1. Record tool execution event
    2. Track consolidation performance metrics
    3. Track planning validation performance
    4. Auto-update task progress
    5. Log performance metrics

    Args:
        tool_name: Name of tool that was executed
        execution_time_ms: How long tool took (int, milliseconds)
        tool_result: Result status (success/error)
        task_id: Optional task ID to update progress

    Returns:
        Performance analytics and task progress update
    """
    try:
        tool_name = args.get("tool_name")
        execution_time_ms = args.get("execution_time_ms", 0)
        tool_result = args.get("tool_result", "unknown")
        task_id = args.get("task_id")

        if not hasattr(server, '_post_tool_optimizer'):
            from ..integration.hook_coordination import PostToolOptimizer
            server._post_tool_optimizer = PostToolOptimizer(server.store.db)

        try:
            result = await server._post_tool_optimizer.execute(
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                tool_result=tool_result,
                task_id=task_id
            )
        except Exception as op_err:
            logger.error(f"Post tool optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "performance_logged": False,
                "task_updated": False
            }

        # Format response
        response = f"""**Optimized PostToolUse Hook**
Status: {result.get('status', 'unknown')}

Performance Metrics:
- Tool: {tool_name}
- Duration: {execution_time_ms}ms
- Result: {tool_result}
- Target Met: {result.get('target_met', False)}

Performance Analysis:
- Consolidation Throughput: {result.get('consolidation_throughput', 'N/A')} events/sec
- Planning Duration: {result.get('planning_duration', 'N/A')}ms
- Performance Status: {result.get('performance_status', 'unknown')}

Task Progress:
- Task Updated: {result.get('task_updated', False)}
- Progress Increment: {result.get('progress_increment', 0)}
- New Total: {result.get('new_progress_total', 0)}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_post_tool_use: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_pre_execution(server: Any, args: dict) -> List[TextContent]:
    """Optimize PreExecution hook: Comprehensive plan validation + simulation.

    Adds comprehensive validation before task execution:
    1. Check goal state
    2. Comprehensive 3-level plan validation
    3. Q* formal property verification
    4. Scenario stress testing (for complex tasks)
    5. Risk assessment with recommendations

    Args:
        task_id: ID of task to validate
        strict_mode: Whether to enforce strict validation (default: false)
        run_scenarios: Whether to run scenario simulation (default: auto)

    Returns:
        Validation results with property scores, scenarios, and execution readiness
    """
    try:
        task_id = args.get("task_id")
        strict_mode = args.get("strict_mode", False)
        run_scenarios = args.get("run_scenarios", "auto")

        if not hasattr(server, '_execution_optimizer'):
            from ..integration.hook_coordination import PreExecutionOptimizer
            server._execution_optimizer = PreExecutionOptimizer(server.store.db)

        try:
            result = await server._execution_optimizer.execute(
                task_id=task_id,
                strict_mode=strict_mode,
                run_scenarios=run_scenarios
            )
        except Exception as op_err:
            logger.error(f"Pre-execution optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "ready_for_execution": False,
                "issues": []
            }

        # Format response
        response = f"""**Optimized PreExecution Hook**
Task ID: {task_id}
Status: {result.get('status', 'unknown')}
Ready for Execution: {result.get('ready_for_execution', False)}

Validation Results:
- Structure Valid: {result.get('structure_valid', False)}
- Feasibility Valid: {result.get('feasibility_valid', False)}
- Rules Valid: {result.get('rules_valid', False)}
- Issues: {len(result.get('issues', []))}

Q* Formal Properties:
- Overall Score: {result.get('properties_overall_score', 0):.2f}
- Optimality: {result.get('property_optimality', 0):.2f}
- Completeness: {result.get('property_completeness', 0):.2f}
- Consistency: {result.get('property_consistency', 0):.2f}
- Soundness: {result.get('property_soundness', 0):.2f}
- Minimality: {result.get('property_minimality', 0):.2f}

Scenario Simulation Results:
- Best Case Duration: {result.get('scenario_best_duration', 'N/A')}
- Worst Case Duration: {result.get('scenario_worst_duration', 'N/A')}
- Likely Case Duration: {result.get('scenario_likely_duration', 'N/A')}
- Success Probability: {result.get('scenario_success_prob', 'N/A')}
- Critical Path: {result.get('scenario_critical_path', 'N/A')}

Recommendations:
{_format_recommendations(result.get('recommendations', []))}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_pre_execution: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# Helper formatting functions

def _format_plan_issues(issues: list) -> str:
    """Format plan validation issues."""
    if not issues:
        return "  ✓ No issues detected"

    formatted = []
    for issue in issues[:5]:  # Show first 5
        formatted.append(f"  - {issue.get('goal_name', 'Unknown')}: {issue.get('issue_count', 0)} issues")

    if len(issues) > 5:
        formatted.append(f"  ... and {len(issues) - 5} more goals")

    return "\n".join(formatted)


def _format_gaps(gaps: list) -> str:
    """Format detected knowledge gaps."""
    if not gaps:
        return "  ✓ No gaps detected"

    formatted = []
    for gap in gaps[:3]:  # Show first 3
        formatted.append(f"  - {gap.get('type', 'unknown')}: {gap.get('description', '')}")

    if len(gaps) > 3:
        formatted.append(f"  ... and {len(gaps) - 3} more gaps")

    return "\n".join(formatted)


def _format_health_warnings(warnings: list) -> str:
    """Format task health warnings."""
    if not warnings:
        return "  ✓ All tasks healthy"

    formatted = []
    for warning in warnings[:3]:  # Show first 3
        severity = warning.get('severity', 'unknown').upper()
        formatted.append(f"  - {severity}: {warning.get('task_name', 'Unknown')} (health: {warning.get('health_score', 0):.2f})")

    if len(warnings) > 3:
        formatted.append(f"  ... and {len(warnings) - 3} more warnings")

    return "\n".join(formatted)


def _format_suggestions(suggestions: list) -> str:
    """Format improvement suggestions."""
    if not suggestions:
        return "  ✓ No improvements needed"

    formatted = []
    for suggestion in suggestions[:3]:  # Show first 3
        formatted.append(f"  - {suggestion.get('category', 'unknown')}: {suggestion.get('description', '')}")

    if len(suggestions) > 3:
        formatted.append(f"  ... and {len(suggestions) - 3} more suggestions")

    return "\n".join(formatted)


def _format_recommendations(recommendations: list) -> str:
    """Format execution recommendations."""
    if not recommendations:
        return "  ✓ No special recommendations"

    formatted = []
    for rec in recommendations[:3]:  # Show first 3
        formatted.append(f"  - {rec.get('type', 'unknown')}: {rec.get('description', '')}")

    if len(recommendations) > 3:
        formatted.append(f"  ... and {len(recommendations) - 3} more recommendations")

    return "\n".join(formatted)
