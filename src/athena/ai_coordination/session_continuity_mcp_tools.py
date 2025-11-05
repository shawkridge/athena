"""MCP tool handlers for SessionContinuity layer."""

from mcp.types import Tool

from ..core.database import Database
from .session_continuity_store import SessionContinuityStore


class SessionContinuityMCPTools:
    """MCP tools for SessionContinuity layer."""

    def __init__(self, db: Database):
        """Initialize tools.

        Args:
            db: Database instance
        """
        self.store = SessionContinuityStore(db)

    def get_tools(self) -> list[Tool]:
        """Get SessionContinuity tool definitions.

        Returns:
            List of Tool definitions
        """
        return [
            Tool(
                name="save_session",
                description="Save a complete session snapshot for resumption",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Unique session ID"},
                        "project_id": {"type": "string", "description": "Project identifier"},
                        "project_name": {
                            "type": "string",
                            "description": "Human-readable project name",
                        },
                        "current_phase": {
                            "type": "string",
                            "description": "Current project phase (planning, feature_development, etc.)",
                        },
                        "current_goal_id": {
                            "type": "string",
                            "description": "UUID of current goal (optional)",
                        },
                        "completed_goals": {
                            "type": "integer",
                            "description": "Number of completed goals",
                        },
                        "in_progress_goals": {
                            "type": "integer",
                            "description": "Number of in-progress goals",
                        },
                        "blocked_goals": {
                            "type": "integer",
                            "description": "Number of blocked goals",
                        },
                        "progress_percentage": {
                            "type": "number",
                            "description": "Overall progress (0.0-100.0)",
                        },
                        "active_cycle_id": {
                            "type": "integer",
                            "description": "Currently active action cycle ID (optional)",
                        },
                        "active_cycle_status": {
                            "type": "string",
                            "description": "Status of active cycle (planning, executing, learning, etc.)",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Current task UUID (optional)",
                        },
                        "relevant_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Most relevant files for current task",
                        },
                        "active_goals": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of active goal descriptions",
                        },
                        "time_in_session_seconds": {
                            "type": "integer",
                            "description": "How long this session has been running",
                        },
                        "primary_objective": {
                            "type": "string",
                            "description": "Primary objective for this session (optional)",
                        },
                        "resumption_advice": {
                            "type": "string",
                            "description": "Advice for resuming this session",
                        },
                        "notes": {
                            "type": "string",
                            "description": "User-provided context or notes (optional)",
                        },
                    },
                    "required": [
                        "session_id",
                        "project_id",
                        "project_name",
                        "current_phase",
                        "completed_goals",
                        "in_progress_goals",
                        "blocked_goals",
                        "progress_percentage",
                        "resumption_advice",
                    ],
                },
            ),
            Tool(
                name="load_session",
                description="Load a saved session snapshot to resume work",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "snapshot_id": {
                            "type": "string",
                            "description": "Unique snapshot ID to load",
                        }
                    },
                    "required": ["snapshot_id"],
                },
            ),
            Tool(
                name="get_resumption_hints",
                description="Get detailed resumption recommendations for a saved session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "snapshot_id": {
                            "type": "string",
                            "description": "Unique snapshot ID to get hints for",
                        }
                    },
                    "required": ["snapshot_id"],
                },
            ),
            Tool(
                name="list_sessions",
                description="List available saved sessions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Filter by project ID (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum sessions to return (default: 10)",
                        },
                    },
                },
            ),
            Tool(
                name="get_latest_session",
                description="Get the most recent snapshot for a session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID to get latest snapshot for",
                        }
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="mark_session_resumed",
                description="Mark a session snapshot as resumed",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "snapshot_id": {
                            "type": "string",
                            "description": "Snapshot ID that was resumed",
                        }
                    },
                    "required": ["snapshot_id"],
                },
            ),
        ]

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> dict:
        """Handle MCP tool calls.

        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters

        Returns:
            Result dictionary
        """
        if tool_name == "save_session":
            return self._handle_save_session(tool_input)
        elif tool_name == "load_session":
            return self._handle_load_session(tool_input)
        elif tool_name == "get_resumption_hints":
            return self._handle_get_resumption_hints(tool_input)
        elif tool_name == "list_sessions":
            return self._handle_list_sessions(tool_input)
        elif tool_name == "get_latest_session":
            return self._handle_get_latest_session(tool_input)
        elif tool_name == "mark_session_resumed":
            return self._handle_mark_session_resumed(tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _handle_save_session(self, tool_input: dict) -> dict:
        """Handle save_session tool call.

        Args:
            tool_input: Tool input parameters

        Returns:
            Result dictionary with snapshot ID
        """
        try:
            from .session_continuity import (
                ActionCycleSnapshot,
                CodeContextSnapshot,
                ExecutionTraceSnapshot,
                ProjectContextSnapshot,
                ResumptionRecommendation,
            )

            # Build project snapshot
            project_snapshot = ProjectContextSnapshot(
                project_id=tool_input["project_id"],
                project_name=tool_input["project_name"],
                current_phase=tool_input["current_phase"],
                current_goal_id=tool_input.get("current_goal_id"),
                completed_goals=tool_input["completed_goals"],
                in_progress_goals=tool_input["in_progress_goals"],
                blocked_goals=tool_input["blocked_goals"],
                progress_percentage=tool_input["progress_percentage"],
            )

            # Build active cycle snapshot if provided
            active_cycle_snapshot = None
            if tool_input.get("active_cycle_id"):
                from datetime import datetime

                active_cycle_snapshot = ActionCycleSnapshot(
                    cycle_id=tool_input["active_cycle_id"],
                    goal_id=tool_input.get("current_goal_id"),
                    status=tool_input.get("active_cycle_status", "executing"),
                    attempt_count=0,
                    max_attempts=5,
                    goal_description=tool_input.get("primary_objective"),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )

            # Build code context snapshot if provided
            code_context_snapshot = None
            if tool_input.get("relevant_files"):
                code_context_snapshot = CodeContextSnapshot(
                    context_id=0,  # Will be assigned by store
                    task_id=tool_input.get("task_id"),
                    relevant_files=tool_input.get("relevant_files", []),
                    file_count=len(tool_input.get("relevant_files", [])),
                )

            # Build resumption recommendation
            resumption_recommendation = ResumptionRecommendation(
                recommended_next_action=tool_input["resumption_advice"],
                reason="Session paused by user",
                blockers=[],
                context_summary=tool_input.get(
                    "notes", "Session paused - ready to resume"
                ),
            )

            # Save the snapshot
            snapshot = self.store.save_session(
                session_id=tool_input["session_id"],
                project_snapshot=project_snapshot,
                active_cycle_snapshot=active_cycle_snapshot,
                code_context_snapshot=code_context_snapshot,
                recent_executions=[],
                resumption_recommendation=resumption_recommendation,
                goals_at_snapshot=tool_input.get("active_goals", []),
                time_in_session_seconds=tool_input.get("time_in_session_seconds", 0),
                primary_objective=tool_input.get("primary_objective"),
                notes=tool_input.get("notes"),
            )

            return {
                "status": "success",
                "snapshot_id": snapshot.snapshot_id,
                "message": f"Session {tool_input['session_id']} saved successfully",
                "project": tool_input["project_name"],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_load_session(self, tool_input: dict) -> dict:
        """Handle load_session tool call.

        Args:
            tool_input: Tool input parameters

        Returns:
            Result dictionary with session data
        """
        try:
            snapshot_id = tool_input["snapshot_id"]
            snapshot = self.store.load_session(snapshot_id)
            if not snapshot:
                return {"status": "error", "error": f"Snapshot {snapshot_id} not found"}

            return {
                "status": "success",
                "snapshot_id": snapshot.snapshot_id,
                "session_id": snapshot.session_id,
                "project": snapshot.project_snapshot.project_name,
                "phase": snapshot.project_snapshot.current_phase,
                "progress": f"{snapshot.project_snapshot.progress_percentage:.1f}%",
                "goals": {
                    "completed": snapshot.project_snapshot.completed_goals,
                    "in_progress": snapshot.project_snapshot.in_progress_goals,
                    "blocked": snapshot.project_snapshot.blocked_goals,
                },
                "active_cycle_id": (
                    snapshot.active_cycle_snapshot.cycle_id
                    if snapshot.active_cycle_snapshot
                    else None
                ),
                "resumption_advice": snapshot.resumption_recommendation.recommended_next_action,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_get_resumption_hints(self, tool_input: dict) -> dict:
        """Handle get_resumption_hints tool call.

        Args:
            tool_input: Tool input parameters

        Returns:
            Result dictionary with resumption recommendations
        """
        try:
            snapshot_id = tool_input["snapshot_id"]
            hints = self.store.get_resumption_hints(snapshot_id)
            if not hints:
                return {"status": "error", "error": f"No hints found for {snapshot_id}"}

            return {
                "status": "success",
                "next_action": hints.recommended_next_action,
                "reason": hints.reason,
                "blockers": hints.blockers,
                "context": hints.context_summary,
                "estimated_time_minutes": hints.estimated_remaining_time_minutes,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_list_sessions(self, tool_input: dict) -> dict:
        """Handle list_sessions tool call.

        Args:
            tool_input: Tool input parameters

        Returns:
            Result dictionary with session list
        """
        try:
            limit = tool_input.get("limit", 10)
            project_id = tool_input.get("project_id")
            sessions = self.store.list_sessions(project_id=project_id, limit=limit)

            return {
                "status": "success",
                "count": len(sessions),
                "sessions": [
                    {
                        "snapshot_id": s.snapshot_id,
                        "project": s.project_name,
                        "status": s.status,
                        "created_at": s.created_at.isoformat(),
                        "active_goals": s.active_goal_count,
                    }
                    for s in sessions
                ],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_get_latest_session(self, tool_input: dict) -> dict:
        """Handle get_latest_session tool call.

        Args:
            tool_input: Tool input parameters

        Returns:
            Result dictionary with latest session
        """
        try:
            session_id = tool_input["session_id"]
            snapshot = self.store.get_latest_session(session_id)
            if not snapshot:
                return {"status": "error", "error": f"No sessions found for {session_id}"}

            return {
                "status": "success",
                "snapshot_id": snapshot.snapshot_id,
                "project": snapshot.project_snapshot.project_name,
                "created_at": snapshot.created_at.isoformat(),
                "resumption_advice": snapshot.resumption_recommendation.recommended_next_action,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_mark_session_resumed(self, tool_input: dict) -> dict:
        """Handle mark_session_resumed tool call.

        Args:
            tool_input: Tool input parameters

        Returns:
            Result dictionary
        """
        try:
            snapshot_id = tool_input["snapshot_id"]
            success = self.store.mark_session_resumed(snapshot_id)
            if not success:
                return {"status": "error", "error": f"Failed to mark {snapshot_id} as resumed"}

            return {
                "status": "success",
                "message": f"Session {snapshot_id} marked as resumed",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
