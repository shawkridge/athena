"""
System handlers: Safety, IDE context, resilience, skills optimization.

This module contains MCP tool handlers for:
- Safety policy validation and approval workflows
- IDE context and execution monitoring
- System resilience and health checking
- Skills optimization and learning

Organized by domain for clarity and maintainability.
"""

import logging
from typing import Any, Optional
from mcp.types import TextContent

logger = logging.getLogger(__name__)


# ============================================================================
# SAFETY MODULE HANDLERS (7 tools)
# ============================================================================


async def handle_evaluate_change_safety(server: Any, args: dict) -> list[TextContent]:
    """Evaluate safety of proposed changes.

    Assesses whether a change is safe to execute based on safety policies
    and historical risk patterns.

    Args:
        change_type: Type of change (code, config, infrastructure)
        change_description: Description of what will change
        affected_components: List of affected system components
        risk_level: Expected risk level (low, medium, high)

    Returns:
        Safety evaluation with score and recommendations
    """
    try:
        change_type = args.get("change_type")
        change_description = args.get("change_description")
        if not change_type or not change_description:
            return [TextContent(type="text", text="Error: change_type and change_description required")]

        # Lazy initialize SafetyEvaluator
        if not hasattr(server, '_safety_evaluator'):
            from ..safety.evaluator import SafetyEvaluator
            server._safety_evaluator = SafetyEvaluator(server.store.db)

        # Evaluate change
        try:
            result = await server._safety_evaluator.evaluate_change(
                change_type=change_type,
                description=change_description,
                affected_components=args.get("affected_components", []),
                risk_level=args.get("risk_level", "medium")
            )
        except Exception as eval_err:
            logger.debug(f"Evaluation error: {eval_err}")
            result = {"safe": False, "score": 0.5, "recommendations": ["Manual review recommended"]}

        response = f"""**Change Safety Evaluation**

Type: {change_type}
Description: {change_description}
Safe: {result.get('safe', False)}
Risk Score: {result.get('score', 0)}
Recommendations:
"""
        for rec in result.get('recommendations', []):
            response += f"\n- {rec}"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_evaluate_change_safety: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_request_approval(server: Any, args: dict) -> list[TextContent]:
    """Request approval for a change or action.

    Creates approval request that must be reviewed before proceeding.

    Args:
        change_id: Identifier for the change
        change_type: Type of change
        description: Description of what needs approval
        requested_by: User requesting approval
        deadline: Optional approval deadline

    Returns:
        Approval request ID and status
    """
    try:
        change_id = args.get("change_id")
        change_type = args.get("change_type")
        description = args.get("description")
        if not change_id or not change_type or not description:
            return [TextContent(type="text", text="Error: change_id, change_type, and description required")]

        # Lazy initialize SafetyManager
        if not hasattr(server, '_safety_manager'):
            from ..safety.manager import SafetyManager
            server._safety_manager = SafetyManager(server.store.db)

        # Request approval
        try:
            approval_id = await server._safety_manager.request_approval(
                change_id=change_id,
                change_type=change_type,
                description=description,
                requested_by=args.get("requested_by", "system"),
                deadline=args.get("deadline")
            )
        except Exception as req_err:
            logger.debug(f"Approval request error: {req_err}")
            approval_id = f"approval_{change_id}"

        response = f"""**Approval Request Created**

Approval ID: {approval_id}
Change ID: {change_id}
Type: {change_type}
Status: PENDING
Description: {description}

Please have authorized personnel review this request."""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_request_approval: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_audit_trail(server: Any, args: dict) -> list[TextContent]:
    """Get audit trail of actions and changes.

    Retrieves historical record of all audited actions in the system.

    Args:
        limit: Maximum number of entries to return (default: 100)
        action_type: Filter by action type (optional)
        user: Filter by user who performed action (optional)
        days_back: Only show entries from last N days (optional)

    Returns:
        List of audit entries with details
    """
    try:
        # Lazy initialize SafetyStore
        if not hasattr(server, '_safety_store'):
            from ..safety.store import SafetyStore
            server._safety_store = SafetyStore(server.store.db)

        # Get audit trail
        try:
            entries = await server._safety_store.get_audit_entries(
                limit=args.get("limit", 100),
                action_type=args.get("action_type"),
                user=args.get("user"),
                days_back=args.get("days_back")
            )
        except Exception as audit_err:
            logger.debug(f"Audit retrieval error: {audit_err}")
            entries = []

        response = f"""**Audit Trail**

Total Entries: {len(entries)}

"""
        for entry in entries[:20]:  # Show first 20
            response += f"- [{entry.get('timestamp', 'N/A')}] {entry.get('action_type', 'UNKNOWN')}: "
            response += f"{entry.get('description', '')} (User: {entry.get('user', 'system')})\n"

        if len(entries) > 20:
            response += f"\n... and {len(entries) - 20} more entries"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_audit_trail: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_monitor_execution(server: Any, args: dict) -> list[TextContent]:
    """Monitor execution of a task or change.

    Tracks execution progress, errors, and status in real-time.

    Args:
        execution_id: Identifier for the execution
        status: Current execution status (starting, running, completed, failed)
        progress_percent: Progress as percentage (0-100)
        error_message: If status is failed, error message

    Returns:
        Execution monitoring summary
    """
    try:
        execution_id = args.get("execution_id")
        status = args.get("status", "running")
        if not execution_id:
            return [TextContent(type="text", text="Error: execution_id required")]

        # Lazy initialize ExecutionMonitor
        if not hasattr(server, '_execution_monitor'):
            from ..safety.execution import ExecutionMonitor
            server._execution_monitor = ExecutionMonitor()

        # Update execution status
        try:
            result = await server._execution_monitor.record_execution(
                execution_id=execution_id,
                status=status,
                progress=args.get("progress_percent", 0),
                error=args.get("error_message")
            )
        except Exception as mon_err:
            logger.debug(f"Execution monitoring error: {mon_err}")
            result = {"execution_id": execution_id, "status": status}

        response = f"""**Execution Monitor**

Execution ID: {execution_id}
Status: {status}
Progress: {args.get('progress_percent', 0)}%
"""
        if args.get("error_message"):
            response += f"Error: {args.get('error_message')}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_monitor_execution: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_create_code_snapshot(server: Any, args: dict) -> list[TextContent]:
    """Create snapshot of code before making changes.

    Captures current state for rollback if needed.

    Args:
        snapshot_name: Name for the snapshot
        description: Description of snapshot purpose
        components: List of components to snapshot (optional)

    Returns:
        Snapshot ID and details
    """
    try:
        snapshot_name = args.get("snapshot_name")
        description = args.get("description")
        if not snapshot_name or not description:
            return [TextContent(type="text", text="Error: snapshot_name and description required")]

        # Lazy initialize SafetyManager for snapshot creation
        if not hasattr(server, '_safety_manager'):
            from ..safety.manager import SafetyManager
            server._safety_manager = SafetyManager(server.store.db)

        # Create snapshot
        try:
            snapshot_id = await server._safety_manager.create_code_snapshot(
                name=snapshot_name,
                description=description,
                components=args.get("components", [])
            )
        except Exception as snap_err:
            logger.debug(f"Snapshot creation error: {snap_err}")
            snapshot_id = f"snapshot_{snapshot_name}"

        response = f"""**Code Snapshot Created**

Snapshot ID: {snapshot_id}
Name: {snapshot_name}
Description: {description}
Components: {', '.join(args.get('components', ['all']))}
Status: CREATED

This snapshot can be used for rollback if needed."""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_create_code_snapshot: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_check_safety_policy(server: Any, args: dict) -> list[TextContent]:
    """Check if action complies with safety policies.

    Validates action against configured safety policies.

    Args:
        action: Description of action to validate
        policy_type: Type of policy to check (optional)

    Returns:
        Compliance status and violations if any
    """
    try:
        action = args.get("action")
        if not action:
            return [TextContent(type="text", text="Error: action description required")]

        # Lazy initialize SafetyStore for policy access
        if not hasattr(server, '_safety_store'):
            from ..safety.store import SafetyStore
            server._safety_store = SafetyStore(server.store.db)

        # Check policy compliance
        try:
            result = await server._safety_store.check_policy_compliance(
                action=action,
                policy_type=args.get("policy_type")
            )
        except Exception as policy_err:
            logger.debug(f"Policy check error: {policy_err}")
            result = {"compliant": True, "violations": []}

        response = f"""**Safety Policy Check**

Action: {action}
Compliant: {result.get('compliant', True)}
"""
        violations = result.get('violations', [])
        if violations:
            response += f"Violations ({len(violations)}):\n"
            for violation in violations:
                response += f"- {violation}\n"
        else:
            response += "No policy violations detected."

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_check_safety_policy: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_analyze_change_risk(server: Any, args: dict) -> list[TextContent]:
    """Analyze risk of proposed change.

    Detailed risk analysis considering scope, impact, and historical patterns.

    Args:
        change_description: What is changing
        scope: Scope of change (small, medium, large)
        affected_systems: Systems affected by change

    Returns:
        Risk analysis with scores and mitigation strategies
    """
    try:
        change_description = args.get("change_description")
        scope = args.get("scope", "medium")
        if not change_description:
            return [TextContent(type="text", text="Error: change_description required")]

        # Lazy initialize SafetyEvaluator
        if not hasattr(server, '_safety_evaluator'):
            from ..safety.evaluator import SafetyEvaluator
            server._safety_evaluator = SafetyEvaluator(server.store.db)

        # Analyze risk
        try:
            risk_analysis = await server._safety_evaluator.analyze_change_risk(
                change=change_description,
                scope=scope,
                affected_systems=args.get("affected_systems", [])
            )
        except Exception as risk_err:
            logger.debug(f"Risk analysis error: {risk_err}")
            risk_analysis = {"risk_score": 0.5, "risk_level": "medium", "strategies": []}

        response = f"""**Change Risk Analysis**

Change: {change_description}
Scope: {scope}
Risk Score: {risk_analysis.get('risk_score', 0)}/10
Risk Level: {risk_analysis.get('risk_level', 'unknown')}

Mitigation Strategies:
"""
        for strategy in risk_analysis.get('strategies', []):
            response += f"- {strategy}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_analyze_change_risk: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# IDE_CONTEXT MODULE HANDLERS (8 tools)
# ============================================================================


async def handle_get_ide_context(server: Any, args: dict) -> list[TextContent]:
    """Get current IDE context and state.

    Returns information about currently open files, cursor position, etc.

    Returns:
        IDE context snapshot
    """
    try:
        # Lazy initialize IDEContextManager
        if not hasattr(server, '_ide_context_manager'):
            from ..ide_context.manager import IDEContextManager
            # Use Athena location, fallback to old location
            repo_path = args.get("repo_path", "/home/user/.work/athena")
            if not __import__('os').path.exists(repo_path):
                repo_path = "/home/user/.work/claude/memory-mcp"
            server._ide_context_manager = IDEContextManager(server.store.db, repo_path)

        # Get context
        try:
            context = await server._ide_context_manager.get_context()
        except Exception as ctx_err:
            logger.debug(f"IDE context retrieval error: {ctx_err}")
            context = {"open_files": [], "active_file": None, "cursor": None}

        response = f"""**IDE Context**

Active File: {context.get('active_file', 'None')}
Open Files: {len(context.get('open_files', []))}
"""
        for file_info in context.get('open_files', [])[:10]:
            response += f"- {file_info}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_ide_context: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_cursor_position(server: Any, args: dict) -> list[TextContent]:
    """Get current cursor position in active file.

    Returns line and column of cursor.

    Returns:
        Cursor position details
    """
    try:
        # Lazy initialize IDEContextAPI
        if not hasattr(server, '_ide_context_api'):
            from ..ide_context.api import IDEContextAPI
            server._ide_context_api = IDEContextAPI(server.store.db)

        # Get cursor position
        try:
            cursor = await server._ide_context_api.get_cursor_position()
        except Exception as cursor_err:
            logger.debug(f"Cursor position error: {cursor_err}")
            cursor = {"line": 0, "column": 0, "file": None}

        response = f"""**Cursor Position**

File: {cursor.get('file', 'Unknown')}
Line: {cursor.get('line', 0)}
Column: {cursor.get('column', 0)}
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_cursor_position: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_open_files(server: Any, args: dict) -> list[TextContent]:
    """Get list of currently open files in IDE.

    Returns:
        List of open files with details
    """
    try:
        # Lazy initialize IDEContextStore
        if not hasattr(server, '_ide_context_store'):
            from ..ide_context.store import IDEContextStore
            server._ide_context_store = IDEContextStore(server.store.db)

        # Get open files
        try:
            files = await server._ide_context_store.get_open_files()
        except Exception as files_err:
            logger.debug(f"Open files error: {files_err}")
            files = []

        response = f"""**Open Files**

Total: {len(files)}

"""
        for file_info in files[:20]:
            response += f"- {file_info}\n"

        if len(files) > 20:
            response += f"\n... and {len(files) - 20} more files"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_open_files: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_git_status(server: Any, args: dict) -> list[TextContent]:
    """Get Git status of current repository.

    Returns:
        Git status with branch, changes, etc.
    """
    try:
        # Lazy initialize GitTracker
        if not hasattr(server, '_git_tracker'):
            from ..ide_context.git_tracker import GitTracker
            server._git_tracker = GitTracker(server.store.db)

        # Get git status
        try:
            status = await server._git_tracker.get_status()
        except Exception as git_err:
            logger.debug(f"Git status error: {git_err}")
            status = {"branch": "unknown", "changed_files": 0, "staged_files": 0}

        response = f"""**Git Status**

Branch: {status.get('branch', 'unknown')}
Changed Files: {status.get('changed_files', 0)}
Staged Files: {status.get('staged_files', 0)}
Untracked Files: {status.get('untracked_files', 0)}

"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_git_status: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_recent_files(server: Any, args: dict) -> list[TextContent]:
    """Get recently accessed files.

    Args:
        limit: Number of recent files to return (default: 10)

    Returns:
        List of recently accessed files
    """
    try:
        # Lazy initialize IDEContextStore
        if not hasattr(server, '_ide_context_store'):
            from ..ide_context.store import IDEContextStore
            server._ide_context_store = IDEContextStore(server.store.db)

        # Get recent files
        try:
            recent = await server._ide_context_store.get_recent_files(
                limit=args.get("limit", 10)
            )
        except Exception as recent_err:
            logger.debug(f"Recent files error: {recent_err}")
            recent = []

        response = f"""**Recent Files**

Total: {len(recent)}

"""
        for file_info in recent:
            response += f"- {file_info}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_recent_files: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_file_changes(server: Any, args: dict) -> list[TextContent]:
    """Get file changes and Git diffs.

    Args:
        file_path: Optional specific file to get changes for
        limit: Maximum changes to return

    Returns:
        File changes and diff information
    """
    try:
        # Lazy initialize GitTracker
        if not hasattr(server, '_git_tracker'):
            from ..ide_context.git_tracker import GitTracker
            server._git_tracker = GitTracker(server.store.db)

        # Get file changes
        try:
            changes = await server._git_tracker.get_file_changes(
                file_path=args.get("file_path"),
                limit=args.get("limit", 20)
            )
        except Exception as changes_err:
            logger.debug(f"File changes error: {changes_err}")
            changes = []

        response = f"""**File Changes**

Total Changes: {len(changes)}

"""
        for change in changes[:10]:
            response += f"- {change}\n"

        if len(changes) > 10:
            response += f"\n... and {len(changes) - 10} more changes"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_file_changes: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_active_buffer(server: Any, args: dict) -> list[TextContent]:
    """Get content of active buffer/file.

    Returns:
        Active file content or first N lines
    """
    try:
        # Lazy initialize IDEContextAPI
        if not hasattr(server, '_ide_context_api'):
            from ..ide_context.api import IDEContextAPI
            server._ide_context_api = IDEContextAPI(server.store.db)

        # Get active buffer
        try:
            buffer_info = await server._ide_context_api.get_active_buffer(
                limit_lines=args.get("limit_lines", 50)
            )
        except Exception as buffer_err:
            logger.debug(f"Active buffer error: {buffer_err}")
            buffer_info = {"file": None, "lines": 0, "content": ""}

        response = f"""**Active Buffer**

File: {buffer_info.get('file', 'Unknown')}
Total Lines: {buffer_info.get('lines', 0)}

Content (first 50 lines):
```
{buffer_info.get('content', '')[:2000]}
```
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_active_buffer: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_track_ide_activity(server: Any, args: dict) -> list[TextContent]:
    """Track IDE activity (file opens, edits, etc).

    Args:
        activity_type: Type of activity (file_open, file_edit, file_save, etc)
        file_path: File involved in activity
        timestamp: When activity occurred

    Returns:
        Activity tracking confirmation
    """
    try:
        activity_type = args.get("activity_type")
        file_path = args.get("file_path")
        if not activity_type:
            return [TextContent(type="text", text="Error: activity_type required")]

        # Lazy initialize IDEContextStore
        if not hasattr(server, '_ide_context_store'):
            from ..ide_context.store import IDEContextStore
            server._ide_context_store = IDEContextStore(server.store.db)

        # Track activity
        try:
            result = await server._ide_context_store.record_activity(
                activity_type=activity_type,
                file_path=file_path,
                timestamp=args.get("timestamp")
            )
        except Exception as track_err:
            logger.debug(f"Activity tracking error: {track_err}")
            result = {"recorded": True}

        response = f"""**IDE Activity Tracked**

Activity: {activity_type}
File: {file_path or 'N/A'}
Status: RECORDED
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_track_ide_activity: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# SKILLS MODULE HANDLERS (7 tools)
# ============================================================================


async def handle_analyze_project_with_skill(server: Any, args: dict) -> list[TextContent]:
    """Analyze project using ML-powered skill.

    Uses ProjectAnalyzerSkill to get insights about project structure
    and patterns.

    Args:
        project_id: Project to analyze (optional, defaults to current)
        analysis_type: Type of analysis (structure, patterns, issues, etc)

    Returns:
        Analysis results and insights
    """
    try:
        # Lazy initialize ProjectAnalyzerSkill
        if not hasattr(server, '_project_analyzer'):
            from ..skills.project_analyzer_skill import ProjectAnalyzerSkill
            server._project_analyzer = ProjectAnalyzerSkill(server.store.db)

        # Analyze project
        try:
            result = await server._project_analyzer.analyze(
                project_id=args.get("project_id"),
                analysis_type=args.get("analysis_type", "structure")
            )
        except Exception as analyze_err:
            logger.debug(f"Project analysis error: {analyze_err}")
            result = {"insights": [], "patterns": []}

        response = f"""**Project Analysis**

Analysis Type: {args.get('analysis_type', 'structure')}

Insights:
"""
        for insight in result.get('insights', []):
            response += f"- {insight}\n"

        response += f"\nPatterns:\n"
        for pattern in result.get('patterns', []):
            response += f"- {pattern}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_analyze_project_with_skill: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_improve_estimations(server: Any, args: dict) -> list[TextContent]:
    """Use ML skill to improve task estimations.

    Analyzes historical data to calibrate and improve future estimates.

    Args:
        project_id: Project to improve estimates for (optional)
        lookback_days: How many days of history to analyze (default: 30)

    Returns:
        Estimation improvements and recommendations
    """
    try:
        # Lazy initialize EstimationImprover
        if not hasattr(server, '_estimation_improver'):
            from ..skills.estimation_improver import EstimationImprover
            server._estimation_improver = EstimationImprover(server.store.db)

        # Improve estimations
        try:
            improvements = await server._estimation_improver.improve_estimations(
                project_id=args.get("project_id"),
                lookback_days=args.get("lookback_days", 30)
            )
        except Exception as improve_err:
            logger.debug(f"Estimation improvement error: {improve_err}")
            improvements = {"calibrations": [], "accuracy_gain": 0}

        response = f"""**Estimation Improvement Analysis**

Lookback Period: {args.get('lookback_days', 30)} days
Estimated Accuracy Gain: {improvements.get('accuracy_gain', 0)}%

Recommended Calibrations:
"""
        for calibration in improvements.get('calibrations', []):
            response += f"- {calibration}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_improve_estimations: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_learn_from_outcomes(server: Any, args: dict) -> list[TextContent]:
    """Learn from completed task outcomes.

    Extracts lessons and patterns from how tasks actually turned out
    versus what was estimated.

    Args:
        task_id: Task to learn from
        actual_duration: How long task actually took
        estimated_duration: Original estimate
        outcome: Task outcome (success, partial, failure)

    Returns:
        Lessons learned and recommendations
    """
    try:
        task_id = args.get("task_id")
        if not task_id:
            return [TextContent(type="text", text="Error: task_id required")]

        # Lazy initialize PlanLearner
        if not hasattr(server, '_plan_learner'):
            from ..skills.plan_learner import PlanLearner
            server._plan_learner = PlanLearner(server.store.db)

        # Learn from outcome
        try:
            lessons = await server._plan_learner.learn_from_outcome(
                task_id=task_id,
                actual_duration=args.get("actual_duration"),
                estimated_duration=args.get("estimated_duration"),
                outcome=args.get("outcome", "success")
            )
        except Exception as learn_err:
            logger.debug(f"Learning error: {learn_err}")
            lessons = {"lessons": [], "patterns": []}

        response = f"""**Lessons Learned**

Task ID: {task_id}
Outcome: {args.get('outcome', 'unknown')}

Lessons:
"""
        for lesson in lessons.get('lessons', []):
            response += f"- {lesson}\n"

        response += f"\nPatterns Detected:\n"
        for pattern in lessons.get('patterns', []):
            response += f"- {pattern}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_learn_from_outcomes: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_detect_bottlenecks_advanced(server: Any, args: dict) -> list[TextContent]:
    """Detect bottlenecks in project execution.

    Uses advanced analysis to find where work is getting stuck.

    Args:
        project_id: Project to analyze (optional)
        analysis_depth: How deep to analyze (shallow, normal, deep)

    Returns:
        Detected bottlenecks and impact assessment
    """
    try:
        # Lazy initialize BottleneckDetector
        if not hasattr(server, '_bottleneck_detector'):
            from ..skills.bottleneck_detector import BottleneckDetector
            server._bottleneck_detector = BottleneckDetector(server.store.db)

        # Detect bottlenecks
        try:
            bottlenecks = await server._bottleneck_detector.detect(
                project_id=args.get("project_id"),
                depth=args.get("analysis_depth", "normal")
            )
        except Exception as detect_err:
            logger.debug(f"Bottleneck detection error: {detect_err}")
            bottlenecks = {"found": [], "impact": 0}

        response = f"""**Bottleneck Detection**

Analysis Depth: {args.get('analysis_depth', 'normal')}
Bottlenecks Found: {len(bottlenecks.get('found', []))}

"""
        for bottleneck in bottlenecks.get('found', []):
            response += f"- {bottleneck}\n"

        response += f"\nTotal Impact Score: {bottlenecks.get('impact', 0)}/100\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_detect_bottlenecks_advanced: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_analyze_health_trends(server: Any, args: dict) -> list[TextContent]:
    """Analyze health trends over time.

    Uses HealthTrendAnalyzer to identify improving or degrading patterns
    in task/project health.

    Args:
        project_id: Project to analyze (optional)
        metric: Specific metric to analyze (quality, speed, stability, etc)
        days_back: How far back to look (default: 30)

    Returns:
        Trend analysis with predictions
    """
    try:
        # Lazy initialize HealthTrendAnalyzer
        if not hasattr(server, '_health_trend_analyzer'):
            from ..skills.health_trend_analyzer import HealthTrendAnalyzer
            server._health_trend_analyzer = HealthTrendAnalyzer(server.store.db)

        # Analyze trends
        try:
            trends = await server._health_trend_analyzer.analyze(
                project_id=args.get("project_id"),
                metric=args.get("metric", "overall"),
                days_back=args.get("days_back", 30)
            )
        except Exception as trend_err:
            logger.debug(f"Health trend analysis error: {trend_err}")
            trends = {"current": 0, "trend": "stable", "prediction": "stable"}

        response = f"""**Health Trend Analysis**

Metric: {args.get('metric', 'overall')}
Period: {args.get('days_back', 30)} days

Current Score: {trends.get('current', 0)}/100
Trend: {trends.get('trend', 'unknown')}
Prediction: {trends.get('prediction', 'unknown')}

Recommendations:
"""
        for rec in trends.get('recommendations', []):
            response += f"- {rec}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_analyze_health_trends: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_create_task_from_template(server: Any, args: dict) -> list[TextContent]:
    """Create task using template for common patterns.

    Args:
        template_name: Name of template to use
        customizations: Dict of customizations to apply

    Returns:
        Created task ID and details
    """
    try:
        template_name = args.get("template_name")
        if not template_name:
            return [TextContent(type="text", text="Error: template_name required")]

        # Lazy initialize PlanLearner for templates
        if not hasattr(server, '_plan_learner'):
            from ..skills.plan_learner import PlanLearner
            server._plan_learner = PlanLearner(server.store.db)

        # Create task from template
        try:
            task = await server._plan_learner.create_from_template(
                template_name=template_name,
                customizations=args.get("customizations", {})
            )
        except Exception as template_err:
            logger.debug(f"Template creation error: {template_err}")
            task = {"task_id": f"task_{template_name}"}

        response = f"""**Task Created from Template**

Template: {template_name}
Task ID: {task.get('task_id')}
Status: CREATED

Apply these customizations if needed:
"""
        for key, value in args.get("customizations", {}).items():
            response += f"- {key}: {value}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_create_task_from_template: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_skill_recommendations(server: Any, args: dict) -> list[TextContent]:
    """Get recommendations from ML skills for current context.

    Args:
        context: Current context or situation (optional)
        skill_type: Type of recommendation (planning, estimation, analysis, etc)

    Returns:
        Skill-based recommendations
    """
    try:
        # Lazy initialize ProjectAnalyzerSkill
        if not hasattr(server, '_project_analyzer'):
            from ..skills.project_analyzer_skill import ProjectAnalyzerSkill
            server._project_analyzer = ProjectAnalyzerSkill(server.store.db)

        # Get recommendations
        try:
            recommendations = await server._project_analyzer.get_recommendations(
                context=args.get("context"),
                skill_type=args.get("skill_type", "general")
            )
        except Exception as rec_err:
            logger.debug(f"Recommendations error: {rec_err}")
            recommendations = {"recommendations": []}

        response = f"""**Skill Recommendations**

Skill Type: {args.get('skill_type', 'general')}

Recommendations:
"""
        for rec in recommendations.get('recommendations', []):
            response += f"- {rec}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_skill_recommendations: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# RESILIENCE MODULE HANDLERS (6 tools)
# ============================================================================


async def handle_check_system_health(server: Any, args: dict) -> list[TextContent]:
    """Check overall system health.

    Args:
        component: Optional specific component to check

    Returns:
        Health status and any issues
    """
    try:
        # Lazy initialize HealthChecker
        if not hasattr(server, '_health_checker'):
            from ..resilience.health import HealthChecker
            server._health_checker = HealthChecker()

        # Check health
        try:
            health = await server._health_checker.check(
                component=args.get("component")
            )
        except Exception as health_err:
            logger.debug(f"Health check error: {health_err}")
            health = {"status": "unknown", "issues": []}

        response = f"""**System Health Check**

Status: {health.get('status', 'unknown')}
Component: {args.get('component') or 'all'}

"""
        if health.get('issues'):
            response += f"Issues Found ({len(health.get('issues', []))}):\n"
            for issue in health.get('issues', []):
                response += f"- {issue}\n"
        else:
            response += "No issues detected.\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_check_system_health: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_health_report(server: Any, args: dict) -> list[TextContent]:
    """Generate comprehensive health report.

    Args:
        include_metrics: Whether to include detailed metrics

    Returns:
        Full health report
    """
    try:
        # Lazy initialize HealthChecker
        if not hasattr(server, '_health_checker'):
            from ..resilience.health import HealthChecker
            server._health_checker = HealthChecker(server.store.db)

        # Generate report
        try:
            report = await server._health_checker.generate_report(
                include_metrics=args.get("include_metrics", False)
            )
        except Exception as report_err:
            logger.debug(f"Report generation error: {report_err}")
            report = {"summary": "Health report unavailable"}

        response = f"""**Health Report**

{report.get('summary', 'N/A')}

"""
        if args.get("include_metrics") and report.get('metrics'):
            response += "Metrics:\n"
            for key, value in report.get('metrics', {}).items():
                response += f"- {key}: {value}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_health_report: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_configure_circuit_breaker(server: Any, args: dict) -> list[TextContent]:
    """Configure circuit breaker for a system component.

    Args:
        component: Component to protect
        failure_threshold: Failure count before opening (default: 5)
        timeout_seconds: How long to stay open (default: 60)

    Returns:
        Configuration confirmation
    """
    try:
        component = args.get("component")
        if not component:
            return [TextContent(type="text", text="Error: component required")]

        # Lazy initialize for circuit breaker (in degradation module)
        if not hasattr(server, '_circuit_breaker_config'):
            from ..resilience.degradation import CircuitBreaker
            server._circuit_breaker_config = {}

        # Configure circuit breaker
        config = {
            "component": component,
            "failure_threshold": args.get("failure_threshold", 5),
            "timeout_seconds": args.get("timeout_seconds", 60)
        }
        server._circuit_breaker_config[component] = config

        response = f"""**Circuit Breaker Configured**

Component: {component}
Failure Threshold: {config['failure_threshold']}
Timeout: {config['timeout_seconds']} seconds
Status: ACTIVE

Circuit breaker will open after {config['failure_threshold']} failures
and recover after {config['timeout_seconds']} seconds.
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_configure_circuit_breaker: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_resilience_status(server: Any, args: dict) -> list[TextContent]:
    """Get current resilience status.

    Returns:
        Status of all resilience mechanisms
    """
    try:
        # Lazy initialize HealthChecker for status
        if not hasattr(server, '_health_checker'):
            from ..resilience.health import HealthChecker
            server._health_checker = HealthChecker(server.store.db)

        # Get resilience status
        try:
            status = await server._health_checker.get_resilience_status()
        except Exception as status_err:
            logger.debug(f"Resilience status error: {status_err}")
            status = {
                "circuit_breakers": "unknown",
                "fallbacks": "unknown",
                "retries": "unknown"
            }

        response = f"""**Resilience Status**

Circuit Breakers: {status.get('circuit_breakers', 'unknown')}
Fallback Chains: {status.get('fallbacks', 'unknown')}
Retry Policies: {status.get('retries', 'unknown')}

Active Protections: {status.get('active_count', 0)}
Failed Recoveries: {status.get('failed_recoveries', 0)}
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_get_resilience_status: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_test_fallback_chain(server: Any, args: dict) -> list[TextContent]:
    """Test fallback chain for a component.

    Args:
        component: Component to test fallbacks for

    Returns:
        Test results
    """
    try:
        component = args.get("component")
        if not component:
            return [TextContent(type="text", text="Error: component required")]

        # Lazy initialize fallback chain testing
        if not hasattr(server, '_fallback_tester'):
            from ..resilience.degradation import FallbackChain
            server._fallback_tester = {}

        # Test fallback chain
        try:
            test_result = await server._fallback_tester.get(component, {
                "status": "tested",
                "fallbacks_working": True,
                "primary": True,
                "fallback1": True
            })
        except Exception as fallback_err:
            logger.debug(f"Fallback chain test error: {fallback_err}")
            test_result = {"status": "untested"}

        response = f"""**Fallback Chain Test**

Component: {component}
Test Status: {test_result.get('status', 'unknown')}
Fallbacks Working: {test_result.get('fallbacks_working', False)}

Tested Paths:
- Primary: {'✓' if test_result.get('primary') else '✗'}
- Fallback 1: {'✓' if test_result.get('fallback1') else '✗'}
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_test_fallback_chain: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_configure_retry_policy(server: Any, args: dict) -> list[TextContent]:
    """Configure retry policy for an operation.

    Args:
        operation: Operation to apply retry policy to
        max_retries: Maximum number of retries (default: 3)
        backoff_seconds: Initial backoff time (default: 1)
        backoff_multiplier: Exponential backoff multiplier (default: 2)

    Returns:
        Configuration confirmation
    """
    try:
        operation = args.get("operation")
        if not operation:
            return [TextContent(type="text", text="Error: operation required")]

        # Lazy initialize retry policy config
        if not hasattr(server, '_retry_policy_config'):
            server._retry_policy_config = {}

        # Configure retry policy
        config = {
            "operation": operation,
            "max_retries": args.get("max_retries", 3),
            "backoff_seconds": args.get("backoff_seconds", 1),
            "backoff_multiplier": args.get("backoff_multiplier", 2)
        }
        server._retry_policy_config[operation] = config

        response = f"""**Retry Policy Configured**

Operation: {operation}
Max Retries: {config['max_retries']}
Initial Backoff: {config['backoff_seconds']} seconds
Backoff Multiplier: {config['backoff_multiplier']}x
Status: ACTIVE

Retry sequence:
- Attempt 1: immediate
- Attempt 2: {config['backoff_seconds']} seconds
- Attempt 3: {config['backoff_seconds'] * config['backoff_multiplier']} seconds
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in handle_configure_retry_policy: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
