"""
MCP Handlers for Goal Decomposition (Phase 4)

Implements Anthropic's progressive disclosure pattern:
- Agents discover tools by reading from filesystem-like structure
- Load only tool definitions needed for current task
- Return summarized results, keep large data in execution environment
- No upfront registration of all tools
"""

import logging
import json
from typing import Any, Dict, Optional
from pathlib import Path

from athena.planning.goal_decomposition import GoalDecompositionService
from athena.planning.models import Goal, DecomposedGoal

logger = logging.getLogger(__name__)


class GoalDecompositionHandlersMixin:
    """Mixin providing goal decomposition MCP handlers with progressive disclosure."""

    def __init__(self, db=None):
        """Initialize goal decomposition service.

        Args:
            db: Optional Database instance for prospective memory integration
        """
        self.decomposition_service = GoalDecompositionService(db)
        self.db = db
        # Store completed decompositions in memory (agents can query these)
        self.decomposition_cache: Dict[str, DecomposedGoal] = {}
        self.integration_results: Dict[str, Dict] = {}

    # ========================================================================
    # TOOL DISCOVERY & SCHEMA (Progressive Disclosure)
    # ========================================================================

    @property
    def decomposition_tools_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Return index of available decomposition tools.

        Agents use this to discover what's available without loading full definitions.
        Follows Anthropic's pattern: read small index, load only what's needed.
        """
        tools = {
            "decompose_goal": {
                "description": "Break down a complex goal into a structured task hierarchy",
                "schema": "decompose_goal.json",
                "category": "planning",
                "complexity": "high",
            },
            "decompose_and_store_goal": {
                "description": "Decompose a goal AND save tasks to prospective memory for tracking",
                "schema": "decompose_and_store_goal.json",
                "category": "planning",
                "complexity": "high",
                "requires_database": True,
            },
            "refine_decomposition": {
                "description": "Iteratively refine a previously generated decomposition",
                "schema": "refine_decomposition.json",
                "category": "planning",
                "complexity": "medium",
            },
            "get_decomposition": {
                "description": "Retrieve a previously stored decomposition by ID",
                "schema": "get_decomposition.json",
                "category": "retrieval",
                "complexity": "low",
            },
            "list_decompositions": {
                "description": "List all completed decompositions with summaries",
                "schema": "list_decompositions.json",
                "category": "retrieval",
                "complexity": "low",
            },
        }
        return tools

    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Return detailed schema for a specific tool.

        Agents request only the schemas they need, reducing token usage.
        Progressive disclosure: read index first, then fetch specific schemas.
        """
        schemas = {
            "decompose_goal": {
                "name": "decompose_goal",
                "description": "Decompose a complex goal into a structured task hierarchy with dependencies, effort estimates, and complexity scores.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "string",
                            "description": "Unique identifier for this goal",
                        },
                        "title": {
                            "type": "string",
                            "description": "Goal title (e.g., 'Build real-time notification system')",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed goal description",
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context for decomposition (optional)",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum task nesting depth (default: 3)",
                            "default": 3,
                        },
                        "target_chunk_size": {
                            "type": "integer",
                            "description": "Target effort size for leaf tasks in minutes (default: 30)",
                            "default": 30,
                        },
                    },
                    "required": ["goal_id", "title", "description"],
                },
                "output": "DecomposedGoal with task hierarchy, dependencies, and metrics",
            },
            "decompose_and_store_goal": {
                "name": "decompose_and_store_goal",
                "description": "Decompose a complex goal AND save all tasks to prospective memory for tracking and management",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "string",
                            "description": "Unique identifier for this goal",
                        },
                        "title": {
                            "type": "string",
                            "description": "Goal title (e.g., 'Build real-time notification system')",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed goal description",
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context for decomposition (optional)",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum task nesting depth (default: 3)",
                            "default": 3,
                        },
                        "target_chunk_size": {
                            "type": "integer",
                            "description": "Target effort size for leaf tasks in minutes (default: 30)",
                            "default": 30,
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Project context ID (optional)",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Who will execute these tasks (default: 'claude')",
                            "default": "claude",
                        },
                    },
                    "required": ["goal_id", "title", "description"],
                },
                "output": "DecomposedGoal summary with task IDs created in prospective memory",
            },
            "refine_decomposition": {
                "name": "refine_decomposition",
                "description": "Refine an existing decomposition based on feedback",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "decomposition_id": {
                            "type": "string",
                            "description": "ID of decomposition to refine",
                        },
                        "feedback": {
                            "type": "string",
                            "description": "Feedback on decomposition (missing tasks, wrong dependencies, etc.)",
                        },
                    },
                    "required": ["decomposition_id", "feedback"],
                },
                "output": "Refined DecomposedGoal",
            },
            "get_decomposition": {
                "name": "get_decomposition",
                "description": "Get a previously generated decomposition",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "decomposition_id": {
                            "type": "string",
                            "description": "ID of decomposition to retrieve",
                        },
                    },
                    "required": ["decomposition_id"],
                },
                "output": "DecomposedGoal with all task details",
            },
            "list_decompositions": {
                "name": "list_decompositions",
                "description": "List all completed decompositions with summaries",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number to return (default: 10)",
                            "default": 10,
                        },
                    },
                },
                "output": "List of decomposition summaries (limited data to save tokens)",
            },
        }

        return schemas.get(tool_name, {})

    # ========================================================================
    # DECOMPOSITION OPERATIONS
    # ========================================================================

    def decompose_goal(
        self,
        goal_id: str,
        title: str,
        description: str,
        context: Optional[str] = None,
        max_depth: int = 3,
        target_chunk_size: int = 30,
    ) -> Dict[str, Any]:
        """
        Decompose a goal into tasks.

        Returns summarized result (full decomposition stored, only summary returned).
        Follows Anthropic pattern: keep large datasets in execution environment.
        """
        try:
            goal = Goal(
                id=goal_id,
                title=title,
                description=description,
                context=context,
            )

            # Run decomposition (blocking, but necessary)
            result = self.decomposition_service.decompose_goal(goal, max_depth, target_chunk_size)

            if not result.success:
                return {
                    "success": False,
                    "error": result.error_message,
                    "warnings": result.warnings,
                }

            # Store full decomposition in cache (execution environment)
            decomposed = result.decomposed_goal
            self.decomposition_cache[goal_id] = decomposed

            # Return SUMMARY ONLY (not full task list)
            # This keeps token usage down while allowing agents to query full data
            return {
                "success": True,
                "decomposition_id": goal_id,
                "summary": {
                    "goal_title": decomposed.goal_title,
                    "num_tasks": decomposed.num_tasks,
                    "num_subtasks": decomposed.num_subtasks,
                    "max_depth": decomposed.max_depth,
                    "total_estimated_effort": decomposed.total_estimated_effort,
                    "avg_complexity": round(decomposed.avg_complexity, 1),
                    "critical_path_length": decomposed.critical_path_length,
                    "completeness_score": round(decomposed.completeness_score, 2),
                    "clarity_score": round(decomposed.clarity_score, 2),
                    "feasibility_score": round(decomposed.feasibility_score, 2),
                },
                "next_action": "Call 'get_decomposition' to see full task hierarchy",
                "execution_time_seconds": result.execution_time_seconds,
                "warnings": result.warnings,
            }

        except Exception as e:
            logger.error(f"Error decomposing goal: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_decomposition(self, decomposition_id: str) -> Dict[str, Any]:
        """
        Retrieve full decomposition from execution environment.

        Agents call this only when they need the full task hierarchy.
        Progressive disclosure: start with summary, get details on demand.
        """
        if decomposition_id not in self.decomposition_cache:
            return {"error": f"Decomposition '{decomposition_id}' not found"}

        decomposed = self.decomposition_cache[decomposition_id]

        # Return structured hierarchy (agents can further filter in their code)
        return {
            "goal_id": decomposed.goal_id,
            "goal_title": decomposed.goal_title,
            "root_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "estimated_effort_minutes": t.estimated_effort_minutes,
                    "estimated_complexity": t.estimated_complexity,
                    "subtask_ids": t.subtask_ids,
                    "critical_path": t.critical_path,
                }
                for t in decomposed.root_tasks
            ],
            "task_count": decomposed.num_tasks,
            "total_effort": decomposed.total_estimated_effort,
        }

    def list_decompositions(self, limit: int = 10) -> Dict[str, Any]:
        """
        List completed decompositions with minimal data.

        Agents use this to browse without loading full hierarchies.
        Returns only summary metrics, keeping full data in execution environment.
        """
        summaries = [
            {
                "id": gid,
                "title": decomp.goal_title,
                "num_tasks": decomp.num_tasks,
                "total_effort": decomp.total_estimated_effort,
                "avg_complexity": round(decomp.avg_complexity, 1),
                "completeness": round(decomp.completeness_score, 2),
            }
            for gid, decomp in list(self.decomposition_cache.items())[:limit]
        ]

        return {
            "total_count": len(self.decomposition_cache),
            "returned_count": len(summaries),
            "decompositions": summaries,
            "instruction": "Use 'get_decomposition' to retrieve full details for any ID",
        }

    async def decompose_and_store_goal(
        self,
        goal_id: str,
        title: str,
        description: str,
        context: Optional[str] = None,
        max_depth: int = 3,
        target_chunk_size: int = 30,
        project_id: Optional[int] = None,
        assignee: str = "claude",
    ) -> Dict[str, Any]:
        """
        Decompose a goal and save results to prospective memory.

        This integrates goal decomposition with the prospective memory system,
        allowing decomposed tasks to be tracked and managed.

        Args:
            goal_id: Unique identifier for this goal
            title: Goal title
            description: Detailed goal description
            context: Additional context (optional)
            max_depth: Maximum nesting depth
            target_chunk_size: Target leaf task size in minutes
            project_id: Project context (optional)
            assignee: Who will execute tasks

        Returns:
            Dictionary with decomposition results and storage information
        """
        if not self.db:
            return {
                "success": False,
                "error": "Database not initialized. Cannot store to prospective memory.",
                "note": "Use decompose_goal() instead for decomposition without storage.",
            }

        try:
            # Create Goal model
            goal = Goal(
                id=goal_id,
                title=title,
                description=description,
                context=context,
                project_id=project_id,
            )

            # Decompose and store
            result = await self.decomposition_service.decompose_and_store_goal(
                goal,
                max_depth=max_depth,
                target_chunk_size_minutes=target_chunk_size,
                project_id=project_id,
                assignee=assignee,
            )

            if not result.get("success"):
                return result

            # Store result for future reference
            self.integration_results[goal_id] = result

            # Also cache the decomposition
            decomposition_result = self.decomposition_service.decompose_goal(
                goal, max_depth, target_chunk_size
            )
            if decomposition_result.success:
                self.decomposition_cache[goal_id] = decomposition_result.decomposed_goal

            return {
                "success": True,
                "goal_id": goal_id,
                "summary": {
                    "num_tasks_created": len(result.get("task_ids", [])),
                    "total_effort_minutes": result["decomposition"]["total_effort_minutes"],
                    "complexity_score": result["decomposition"]["complexity_score"],
                    "critical_path_length": result["decomposition"]["critical_path_length"],
                },
                "task_ids": result.get("task_ids"),
                "dependencies_created": result.get("dependencies_created"),
                "warnings": result.get("warnings", []),
                "next_action": "Tasks are now in prospective memory. Use prospective_*  tools to manage them.",
            }

        except Exception as e:
            logger.error(f"Error decomposing and storing goal: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def refine_decomposition(
        self,
        decomposition_id: str,
        feedback: str,
    ) -> Dict[str, Any]:
        """
        Refine a decomposition based on feedback.

        Takes user feedback on an existing decomposition and re-runs the
        decomposition with the feedback incorporated as additional context.

        Args:
            decomposition_id: ID of decomposition to refine
            feedback: User feedback describing desired changes

        Returns:
            Refined decomposition summary
        """
        if decomposition_id not in self.decomposition_cache:
            return {"error": f"Decomposition '{decomposition_id}' not found"}

        try:
            # Get the original decomposition
            original = self.decomposition_cache[decomposition_id]

            # Re-run decomposition with feedback incorporated as context
            goal = Goal(
                id=decomposition_id,
                title=original.goal_title,
                description=original.goal_description,
                context=f"{original.goal_context or ''}\n\nRefinement feedback: {feedback}",
            )

            logger.info(f"Refining decomposition {decomposition_id} with feedback: {feedback[:100]}...")

            # Re-decompose with feedback in context
            result = self.decomposition_service.decompose_goal(
                goal,
                max_depth=original.max_depth,
                target_chunk_size=30
            )

            if not result.success:
                return {
                    "success": False,
                    "error": result.error_message,
                    "warnings": result.warnings,
                }

            # Store refined decomposition in cache (overwrites old version)
            decomposed = result.decomposed_goal
            self.decomposition_cache[decomposition_id] = decomposed

            logger.info(f"Successfully refined decomposition {decomposition_id}")

            # Return summary of refined decomposition
            return {
                "success": True,
                "decomposition_id": decomposition_id,
                "refined": True,
                "feedback_applied": feedback,
                "summary": {
                    "goal_title": decomposed.goal_title,
                    "num_tasks": decomposed.num_tasks,
                    "num_subtasks": decomposed.num_subtasks,
                    "max_depth": decomposed.max_depth,
                    "total_estimated_effort": decomposed.total_estimated_effort,
                    "avg_complexity": round(decomposed.avg_complexity, 1),
                    "critical_path_length": decomposed.critical_path_length,
                    "completeness_score": round(decomposed.completeness_score, 2),
                    "clarity_score": round(decomposed.clarity_score, 2),
                    "feasibility_score": round(decomposed.feasibility_score, 2),
                },
                "changes": {
                    "previous_task_count": original.num_tasks,
                    "new_task_count": decomposed.num_tasks,
                    "task_change": decomposed.num_tasks - original.num_tasks,
                    "complexity_change": round(decomposed.avg_complexity - original.avg_complexity, 2),
                },
                "next_action": "Call 'get_decomposition' to see full updated task hierarchy",
                "execution_time_seconds": result.execution_time_seconds,
                "warnings": result.warnings,
            }

        except Exception as e:
            logger.error(f"Error refining decomposition {decomposition_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "decomposition_id": decomposition_id,
            }

    # ========================================================================
    # HELPER: Convert to MCP Tool Calls (if server doesn't use mixin directly)
    # ========================================================================

    def register_decomposition_tools(self, server):
        """
        Register decomposition tools with MCP server.

        Call this if server doesn't inherit from mixin.
        Each tool returns summarized data following Anthropic pattern.
        """
        # Tool 1: Tool Discovery Index
        @server.list_resources()
        async def list_decomposition_resources():
            return [
                {
                    "uri": "decomposition://tools/index",
                    "name": "Goal Decomposition Tools",
                    "description": "Index of available goal decomposition tools",
                    "mimeType": "application/json",
                }
            ]

        # Tool 2: Get Tool Schema (on-demand)
        @server.read_resource()
        async def read_decomposition_resource(uri: str):
            if uri == "decomposition://tools/index":
                return json.dumps(self.decomposition_tools_index, indent=2)
            elif uri.startswith("decomposition://tools/"):
                tool_name = uri.split("/")[-1].replace(".json", "")
                return json.dumps(self.get_tool_schema(tool_name), indent=2)
            return None

        # Tool 3: decompose_goal (returns summary)
        @server.call_tool()
        async def handle_decompose_goal(
            goal_id: str,
            title: str,
            description: str,
            context: Optional[str] = None,
            max_depth: int = 3,
            target_chunk_size: int = 30,
        ):
            return self.decompose_goal(
                goal_id, title, description, context, max_depth, target_chunk_size
            )

        # Tool 4: get_decomposition (full data)
        @server.call_tool()
        async def handle_get_decomposition(decomposition_id: str):
            return self.get_decomposition(decomposition_id)

        # Tool 5: list_decompositions (summaries only)
        @server.call_tool()
        async def handle_list_decompositions(limit: int = 10):
            return self.list_decompositions(limit)
