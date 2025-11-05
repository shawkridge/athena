"""MCP tool handlers for ProjectContext layer."""

import json
from typing import Any

from mcp.types import Tool, TextContent

from ..core.database import Database
from .project_context import Decision, ErrorPattern, ProjectPhase
from .project_context_store import ProjectContextStore


class ProjectContextMCPTools:
    """MCP tools for ProjectContext layer."""

    def __init__(self, db: Database):
        """Initialize tools.

        Args:
            db: Database instance
        """
        self.store = ProjectContextStore(db)
        self.current_project_id: str = "default"  # Will be set by server

    def get_tools(self) -> list[Tool]:
        """Get ProjectContext tools definitions.

        Returns:
            List of Tool definitions
        """
        return [
            Tool(
                name="get_project_context",
                description="Get full project understanding (phase, goals, architecture, decisions, error patterns)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    }
                }
            ),
            Tool(
                name="update_project_phase",
                description="Update project phase (planning, feature_development, debugging, refactoring, testing, deployment)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "phase": {
                            "type": "string",
                            "enum": ["planning", "feature_development", "debugging", "refactoring", "testing", "deployment"],
                            "description": "New project phase"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    },
                    "required": ["phase"]
                }
            ),
            Tool(
                name="update_current_goal",
                description="Set or clear the current goal being worked on",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "string",
                            "description": "UUID of goal to make current, or null to clear"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    },
                    "required": ["goal_id"]
                }
            ),
            Tool(
                name="update_progress",
                description="Update count of completed, in-progress, and blocked goals",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "completed": {
                            "type": "integer",
                            "description": "Number of completed goals"
                        },
                        "in_progress": {
                            "type": "integer",
                            "description": "Number of in-progress goals"
                        },
                        "blocked": {
                            "type": "integer",
                            "description": "Number of blocked goals"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    }
                }
            ),
            Tool(
                name="record_decision",
                description="Record an architectural or technical decision",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "description": "The decision made"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why this decision was made"
                        },
                        "alternatives": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Alternatives that were considered"
                        },
                        "impact": {
                            "type": "string",
                            "enum": ["positive", "negative", "neutral"],
                            "description": "Impact of this decision"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    },
                    "required": ["decision", "reasoning", "impact"]
                }
            ),
            Tool(
                name="get_decisions",
                description="Get recent decisions for the project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum decisions to return (default: 20)"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    }
                }
            ),
            Tool(
                name="track_error",
                description="Track a recurring error pattern in the project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "error_type": {
                            "type": "string",
                            "description": "Type of error (e.g., 'type_mismatch', 'async_deadlock')"
                        },
                        "mitigation": {
                            "type": "string",
                            "description": "How to fix or prevent this error"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    },
                    "required": ["error_type"]
                }
            ),
            Tool(
                name="get_error_patterns",
                description="Get error patterns for the project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "unresolved_only": {
                            "type": "boolean",
                            "description": "Only return unresolved errors (default: true)"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (defaults to current project)"
                        }
                    }
                }
            ),
        ]

    async def handle_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Handle a tool call.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Result as list of TextContent
        """
        project_id = arguments.get("project_id", self.current_project_id)

        if name == "get_project_context":
            return await self._handle_get_project_context(project_id)
        elif name == "update_project_phase":
            return await self._handle_update_project_phase(project_id, arguments)
        elif name == "update_current_goal":
            return await self._handle_update_current_goal(project_id, arguments)
        elif name == "update_progress":
            return await self._handle_update_progress(project_id, arguments)
        elif name == "record_decision":
            return await self._handle_record_decision(project_id, arguments)
        elif name == "get_decisions":
            return await self._handle_get_decisions(project_id, arguments)
        elif name == "track_error":
            return await self._handle_track_error(project_id, arguments)
        elif name == "get_error_patterns":
            return await self._handle_get_error_patterns(project_id, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def _handle_get_project_context(self, project_id: str) -> list[TextContent]:
        """Get project context."""
        context = self.store.get_context(project_id)

        if not context:
            return [TextContent(type="text", text=f"Project '{project_id}' not found")]

        result = {
            "project_id": context.project_id,
            "name": context.name,
            "description": context.description,
            "phase": context.current_phase,
            "current_goal_id": context.current_goal_id,
            "architecture": context.architecture,
            "progress": {
                "completed": context.completed_goal_count,
                "in_progress": context.in_progress_goal_count,
                "blocked": context.blocked_goal_count,
                "total": context.completed_goal_count + context.in_progress_goal_count + context.blocked_goal_count
            },
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _handle_update_project_phase(self, project_id: str, arguments: dict) -> list[TextContent]:
        """Update project phase."""
        # Create project if doesn't exist
        self.store.get_or_create(project_id, f"Project {project_id}")

        phase_str = arguments.get("phase")
        try:
            phase = ProjectPhase(phase_str)
            self.store.update_phase(project_id, phase)
            return [TextContent(type="text", text=f"✅ Project phase updated to: {phase_str}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"❌ Invalid phase: {e}")]

    async def _handle_update_current_goal(self, project_id: str, arguments: dict) -> list[TextContent]:
        """Update current goal."""
        # Create project if doesn't exist
        self.store.get_or_create(project_id, f"Project {project_id}")

        goal_id = arguments.get("goal_id")
        self.store.update_goal(project_id, goal_id)

        if goal_id:
            return [TextContent(type="text", text=f"✅ Current goal updated to: {goal_id}")]
        else:
            return [TextContent(type="text", text="✅ Current goal cleared")]

    async def _handle_update_progress(self, project_id: str, arguments: dict) -> list[TextContent]:
        """Update progress."""
        # Create project if doesn't exist
        self.store.get_or_create(project_id, f"Project {project_id}")

        self.store.update_progress(
            project_id,
            completed=arguments.get("completed"),
            in_progress=arguments.get("in_progress"),
            blocked=arguments.get("blocked"),
        )

        context = self.store.get_context(project_id)
        result = f"✅ Progress updated:\n- Completed: {context.completed_goal_count}\n- In Progress: {context.in_progress_goal_count}\n- Blocked: {context.blocked_goal_count}"

        return [TextContent(type="text", text=result)]

    async def _handle_record_decision(self, project_id: str, arguments: dict) -> list[TextContent]:
        """Record a decision."""
        # Create project if doesn't exist
        self.store.get_or_create(project_id, f"Project {project_id}")

        decision = Decision(
            project_id=project_id,
            decision=arguments.get("decision"),
            reasoning=arguments.get("reasoning"),
            alternatives_considered=arguments.get("alternatives", []),
            impact=arguments.get("impact"),
        )

        decision_id = self.store.add_decision(decision)
        return [TextContent(type="text", text=f"✅ Decision recorded (ID: {decision_id})")]

    async def _handle_get_decisions(self, project_id: str, arguments: dict) -> list[TextContent]:
        """Get decisions."""
        limit = arguments.get("limit", 20)
        decisions = self.store.get_decisions(project_id, limit=limit)

        if not decisions:
            return [TextContent(type="text", text="No decisions found")]

        result = f"Found {len(decisions)} decisions:\n\n"
        for decision in decisions:
            result += f"- ({decision.id}) {decision.decision}\n"
            result += f"  Reasoning: {decision.reasoning}\n"
            result += f"  Impact: {decision.impact}\n\n"

        return [TextContent(type="text", text=result)]

    async def _handle_track_error(self, project_id: str, arguments: dict) -> list[TextContent]:
        """Track an error."""
        # Create project if doesn't exist
        self.store.get_or_create(project_id, f"Project {project_id}")

        error = ErrorPattern(
            project_id=project_id,
            error_type=arguments.get("error_type"),
            mitigation=arguments.get("mitigation"),
            resolved=False,
        )

        self.store.track_error(error)
        return [TextContent(type="text", text=f"✅ Error pattern tracked: {arguments.get('error_type')}")]

    async def _handle_get_error_patterns(self, project_id: str, arguments: dict) -> list[TextContent]:
        """Get error patterns."""
        unresolved_only = arguments.get("unresolved_only", True)
        errors = self.store.get_error_patterns(project_id, unresolved_only=unresolved_only)

        if not errors:
            status = "Unresolved" if unresolved_only else "All"
            return [TextContent(type="text", text=f"No {status} error patterns found")]

        result = f"Found {len(errors)} error patterns:\n\n"
        for error in errors:
            status = "✅ RESOLVED" if error.resolved else "⚠️ OPEN"
            result += f"{status} {error.error_type} (frequency: {error.frequency})\n"
            if error.mitigation:
                result += f"  Mitigation: {error.mitigation}\n"
            result += "\n"

        return [TextContent(type="text", text=result)]
