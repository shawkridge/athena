"""
MCP Tool handlers for Executive Function Phase 3 integration.

Exposes goal-aware decomposition, orchestration, and strategy management via MCP.
"""

from typing import Any
from mcp.types import Tool, TextContent
import json

from ..executive.models import StrategyType, GoalType, GoalStatus
from ..executive.hierarchy import GoalHierarchy
from ..executive.strategy import StrategySelector
from ..executive.conflict import ConflictResolver
from ..executive.progress import ProgressMonitor
from ..executive.agent_bridge import ExecutiveAgentBridge
from ..executive.orchestration_bridge import OrchestrationBridge
from ..executive.strategy_aware_planner import StrategyAwarePlanner


def get_executive_function_tools() -> list[Tool]:
    """Get all executive function MCP tools."""
    return [
        Tool(
            name="decompose_with_strategy",
            description="Decompose task using goal-aware strategy selection for explicit reasoning",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "integer",
                        "description": "Goal ID to decompose (optional, uses current if not provided)",
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Task or goal description for decomposition",
                    },
                    "strategy": {
                        "type": "string",
                        "enum": [s.value for s in StrategyType],
                        "description": "Strategy to guide decomposition (optional, auto-selects if not provided)",
                    },
                },
                "required": ["task_description"],
            },
        ),
        Tool(
            name="activate_goal",
            description="Activate a goal and switch workflow context with cost analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "integer",
                        "description": "Goal ID to activate",
                    },
                },
                "required": ["goal_id"],
            },
        ),
        Tool(
            name="check_goal_conflicts",
            description="Check for conflicts between active goals in a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to check (default: current project)",
                    },
                },
            },
        ),
        Tool(
            name="resolve_goal_conflicts",
            description="Automatically resolve conflicts between goals",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to resolve conflicts in",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_goal_priority_ranking",
            description="Get goals ranked by priority considering deadline, dependencies, and progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to analyze",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="recommend_next_goal",
            description="Get AI recommendation for next goal to activate based on priority",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to analyze",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="record_execution_progress",
            description="Record plan execution progress for goal-level tracking",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "integer",
                        "description": "Goal being executed",
                    },
                    "plan_id": {
                        "type": "integer",
                        "description": "Execution plan ID",
                    },
                    "steps_completed": {
                        "type": "integer",
                        "description": "Number of completed steps",
                    },
                    "total_steps": {
                        "type": "integer",
                        "description": "Total steps in plan",
                    },
                    "errors": {
                        "type": "integer",
                        "description": "Number of errors encountered",
                    },
                    "blockers": {
                        "type": "integer",
                        "description": "Number of blockers encountered",
                    },
                },
                "required": ["goal_id", "plan_id", "steps_completed", "total_steps"],
            },
        ),
        Tool(
            name="complete_goal",
            description="Mark a goal as completed with outcome recording",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "integer",
                        "description": "Goal to complete",
                    },
                    "outcome": {
                        "type": "string",
                        "enum": ["success", "partial", "failure"],
                        "description": "Result of goal execution",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Completion notes",
                    },
                },
                "required": ["goal_id", "outcome"],
            },
        ),
        Tool(
            name="get_workflow_status",
            description="Get comprehensive workflow status with active goals and metrics",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


class ExecutiveFunctionMCPHandlers:
    """Handlers for executive function MCP tools."""

    def __init__(
        self,
        orchestration_bridge: OrchestrationBridge,
        strategy_aware_planner: StrategyAwarePlanner,
        db=None,
    ):
        """Initialize handlers with bridge and planner."""
        self.orchestration = orchestration_bridge
        self.planner = strategy_aware_planner
        self.db = db  # Optional database connection for fallback queries

    async def handle_decompose_with_strategy(self, args: dict) -> list[TextContent]:
        """Handle decompose_with_strategy tool call."""
        try:
            goal_id = args.get("goal_id")
            task_description = args.get("task_description", "")
            strategy_str = args.get("strategy")

            # Get goal context
            if goal_id:
                goal = self.orchestration.hierarchy.get_goal(goal_id)
                if not goal:
                    return [TextContent(type="text", text=json.dumps({"error": f"Goal {goal_id} not found"}))]
            else:
                goal = None

            # Select strategy if not provided
            reasoning = "User-provided strategy"
            if strategy_str:
                strategy = StrategyType(strategy_str)
                reasoning = f"User selected {strategy_str} strategy"
            elif goal:
                try:
                    context = self.orchestration.prepare_goal_for_planner(goal_id)
                    strategy = StrategyType(context["strategy"])
                    reasoning = context.get("reasoning", "Goal-based strategy selection")
                except Exception:
                    strategy = StrategyType.TOP_DOWN
                    reasoning = "Goal context unavailable, defaulting to TOP_DOWN"
            else:
                strategy = StrategyType.TOP_DOWN
                reasoning = "Default strategy for new task"

            # Decompose with strategy
            result = await self.planner.decompose_with_strategy(
                task={"id": goal_id, "description": task_description},
                strategy=strategy,
                reasoning=reasoning,
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_activate_goal(self, args: dict) -> list[TextContent]:
        """Handle activate_goal tool call."""
        try:
            goal_id = args.get("goal_id")
            if not goal_id:
                return [TextContent(type="text", text=json.dumps({"error": "goal_id required"}))]

            result = self.orchestration.activate_goal(goal_id)
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_check_goal_conflicts(self, args: dict) -> list[TextContent]:
        """Handle check_goal_conflicts tool call."""
        try:
            project_id = args.get("project_id", 1)  # Default to project 1
            result = self.orchestration.check_goal_conflicts(project_id)
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_resolve_goal_conflicts(self, args: dict) -> list[TextContent]:
        """Handle resolve_goal_conflicts tool call."""
        try:
            project_id = args.get("project_id")
            if not project_id:
                return [TextContent(type="text", text=json.dumps({"error": "project_id required"}))]

            result = self.orchestration.resolve_conflicts_auto(project_id)
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_get_goal_priority_ranking(self, args: dict) -> list[TextContent]:
        """Handle get_goal_priority_ranking tool call."""
        try:
            project_id = args.get("project_id", 1)
            if not project_id:
                project_id = 1

            # Try orchestration bridge first
            ranked = self.orchestration.get_goal_priority_ranking(project_id)

            # Fallback: query active_goals table directly if empty
            if not ranked:
                try:
                    import sqlite3
                    import os

                    # Try to get db from environment or default location
                    db_path = os.environ.get("ATHENA_DB_PATH", os.path.expanduser("~/.athena/memory.db"))
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute(
                        "SELECT id, goal_text, priority FROM active_goals WHERE project_id = ? ORDER BY priority DESC LIMIT 20",
                        (project_id,)
                    )
                    rows = cursor.fetchall()
                    ranked = [
                        {"goal_id": row[0], "goal_text": row[1], "priority": row[2], "score": row[2]/10.0}
                        for row in rows
                    ]
                    conn.close()
                except Exception as fallback_error:
                    # If fallback fails, return empty (original behavior)
                    ranked = []

            return [TextContent(type="text", text=json.dumps({"goals": ranked}))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_recommend_next_goal(self, args: dict) -> list[TextContent]:
        """Handle recommend_next_goal tool call."""
        try:
            project_id = args.get("project_id", 1)
            if not project_id:
                project_id = 1

            # Try orchestration bridge first
            recommendation = self.orchestration.recommend_next_goal(project_id)

            # Fallback: get highest priority goal directly from active_goals table
            if not recommendation and self.db:
                cursor = self.db.get_cursor()
                cursor.execute(
                    "SELECT id, goal_text, priority FROM active_goals WHERE project_id = ? ORDER BY priority DESC LIMIT 1",
                    (project_id,)
                )
                row = cursor.fetchone()
                if row:
                    recommendation = {
                        "goal_id": row[0],
                        "goal_text": row[1],
                        "priority": row[2],
                        "reasoning": f"Highest priority goal (priority {row[2]}/10)"
                    }

            if recommendation:
                return [TextContent(type="text", text=json.dumps({"recommendation": recommendation}))]
            else:
                return [TextContent(type="text", text=json.dumps({"message": "No goals available"}))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_record_execution_progress(self, args: dict) -> list[TextContent]:
        """Handle record_execution_progress tool call."""
        try:
            goal_id = args.get("goal_id")
            plan_id = args.get("plan_id")
            steps_completed = args.get("steps_completed", 0)
            total_steps = args.get("total_steps", 0)
            errors = args.get("errors", 0)
            blockers = args.get("blockers", 0)

            result = self.orchestration.record_plan_execution(
                goal_id=goal_id,
                plan_id=plan_id,
                steps_completed=steps_completed,
                total_steps=total_steps,
                errors=errors,
                blockers=blockers,
            )
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_complete_goal(self, args: dict) -> list[TextContent]:
        """Handle complete_goal tool call."""
        try:
            goal_id = args.get("goal_id")
            outcome = args.get("outcome", "success")
            notes = args.get("notes", "")

            result = self.orchestration.mark_goal_completed(goal_id, outcome, notes)
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def handle_get_workflow_status(self, args: dict) -> list[TextContent]:
        """Handle get_workflow_status tool call."""
        try:
            status = self.orchestration.get_workflow_status()
            return [TextContent(type="text", text=json.dumps(status))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
