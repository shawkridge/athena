"""MCP tool handlers for ActionCycle layer."""

from mcp.types import Tool

from ..core.database import Database
from .action_cycle_store import ActionCycleStore
from .action_cycles import CycleStatus, PlanAssumption


class ActionCycleMCPTools:
    """MCP tools for ActionCycle layer."""

    def __init__(self, db: Database):
        """Initialize tools.

        Args:
            db: Database instance
        """
        self.store = ActionCycleStore(db)

    def get_tools(self) -> list[Tool]:
        """Get ActionCycle tools definitions.

        Returns:
            List of Tool definitions
        """
        return [
            Tool(
                name="create_action_cycle",
                description="Create a new action cycle for a goal",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "goal_description": {
                            "type": "string",
                            "description": "What goal are we trying to achieve?"
                        },
                        "plan_description": {
                            "type": "string",
                            "description": "What is the plan to achieve it?"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID"
                        },
                        "goal_id": {
                            "type": "string",
                            "description": "UUID of goal this cycle is for"
                        },
                        "goal_priority": {
                            "type": "number",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Goal priority (1-10)"
                        },
                        "plan_quality": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Estimated plan quality (0.0-1.0)"
                        },
                        "max_attempts": {
                            "type": "integer",
                            "description": "Maximum retry attempts (default: 5)"
                        }
                    },
                    "required": ["goal_description", "plan_description", "session_id"]
                }
            ),
            Tool(
                name="start_cycle_execution",
                description="Mark action cycle as starting execution phase",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        }
                    },
                    "required": ["cycle_id"]
                }
            ),
            Tool(
                name="record_execution_result",
                description="Record result of an execution attempt",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        },
                        "attempt_number": {
                            "type": "integer",
                            "description": "Which attempt (1-based)"
                        },
                        "outcome": {
                            "type": "string",
                            "enum": ["success", "failure", "partial"],
                            "description": "Execution outcome"
                        },
                        "execution_id": {
                            "type": "string",
                            "description": "UUID of ExecutionTrace"
                        },
                        "duration_seconds": {
                            "type": "integer",
                            "description": "How long did execution take?"
                        },
                        "code_changes_count": {
                            "type": "integer",
                            "description": "Number of code changes"
                        },
                        "errors_encountered": {
                            "type": "integer",
                            "description": "Number of errors"
                        }
                    },
                    "required": ["cycle_id", "attempt_number", "outcome"]
                }
            ),
            Tool(
                name="check_if_replan_needed",
                description="Check if replanning is needed based on execution results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        }
                    },
                    "required": ["cycle_id"]
                }
            ),
            Tool(
                name="trigger_replanning",
                description="Trigger replanning with a new plan",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        },
                        "new_plan": {
                            "type": "string",
                            "description": "New plan description"
                        },
                        "plan_quality": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Quality of new plan"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why replanning was triggered"
                        }
                    },
                    "required": ["cycle_id", "new_plan"]
                }
            ),
            Tool(
                name="add_lesson_learned",
                description="Add a lesson learned from execution",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        },
                        "lesson": {
                            "type": "string",
                            "description": "What was learned?"
                        },
                        "source_attempt": {
                            "type": "integer",
                            "description": "Which attempt yielded this?"
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Confidence in lesson (0.0-1.0)"
                        },
                        "can_create_procedure": {
                            "type": "boolean",
                            "description": "Can this become a reusable procedure?"
                        }
                    },
                    "required": ["cycle_id", "lesson", "source_attempt"]
                }
            ),
            Tool(
                name="complete_action_cycle",
                description="Complete an action cycle",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["completed", "abandoned"],
                            "description": "Final status"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason if abandoned"
                        }
                    },
                    "required": ["cycle_id", "status"]
                }
            ),
            Tool(
                name="get_action_cycle",
                description="Retrieve an action cycle",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        }
                    },
                    "required": ["cycle_id"]
                }
            ),
            Tool(
                name="get_active_cycle",
                description="Get active cycle for a goal",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "string",
                            "description": "Goal ID (UUID)"
                        }
                    },
                    "required": ["goal_id"]
                }
            ),
            Tool(
                name="get_cycle_summary",
                description="Get execution summary for a cycle",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cycle_id": {
                            "type": "integer",
                            "description": "Cycle ID"
                        }
                    },
                    "required": ["cycle_id"]
                }
            ),
            Tool(
                name="get_active_cycles",
                description="Get all active cycles in a session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
        ]

    async def handle_tool_call(self, name: str, arguments: dict) -> str:
        """Handle a tool call.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            JSON string with results
        """
        try:
            if name == "create_action_cycle":
                return self._create_action_cycle(**arguments)
            elif name == "start_cycle_execution":
                return self._start_cycle_execution(**arguments)
            elif name == "record_execution_result":
                return self._record_execution_result(**arguments)
            elif name == "check_if_replan_needed":
                return self._check_if_replan_needed(**arguments)
            elif name == "trigger_replanning":
                return self._trigger_replanning(**arguments)
            elif name == "add_lesson_learned":
                return self._add_lesson_learned(**arguments)
            elif name == "complete_action_cycle":
                return self._complete_action_cycle(**arguments)
            elif name == "get_action_cycle":
                return self._get_action_cycle(**arguments)
            elif name == "get_active_cycle":
                return self._get_active_cycle(**arguments)
            elif name == "get_cycle_summary":
                return self._get_cycle_summary(**arguments)
            elif name == "get_active_cycles":
                return self._get_active_cycles(**arguments)
            else:
                return '{"error": "Unknown tool"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _create_action_cycle(
        self,
        goal_description: str,
        plan_description: str,
        session_id: str,
        goal_id: str = None,
        goal_priority: float = 5.0,
        plan_quality: float = 0.5,
        max_attempts: int = 5,
    ) -> str:
        """Create action cycle."""
        try:
            cycle_id = self.store.create_cycle(
                goal_description=goal_description,
                plan_description=plan_description,
                session_id=session_id,
                goal_id=goal_id,
                goal_priority=goal_priority,
                plan_quality=plan_quality,
                max_attempts=max_attempts,
            )
            return f'{{"status": "created", "cycle_id": {cycle_id}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _start_cycle_execution(self, cycle_id: int) -> str:
        """Start execution phase."""
        try:
            self.store.start_execution(cycle_id)
            return '{"status": "execution_started"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _record_execution_result(
        self,
        cycle_id: int,
        attempt_number: int,
        outcome: str,
        execution_id: str = None,
        duration_seconds: int = 0,
        code_changes_count: int = 0,
        errors_encountered: int = 0,
    ) -> str:
        """Record execution result."""
        try:
            exec_id = self.store.record_execution_result(
                cycle_id=cycle_id,
                attempt_number=attempt_number,
                outcome=outcome,
                execution_id=execution_id,
                duration_seconds=duration_seconds,
                code_changes_count=code_changes_count,
                errors_encountered=errors_encountered,
            )
            return f'{{"status": "recorded", "execution_id": {exec_id}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _check_if_replan_needed(self, cycle_id: int) -> str:
        """Check if replanning is needed."""
        try:
            should_replan = self.store.should_replan(cycle_id)
            return f'{{"should_replan": {str(should_replan).lower()}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _trigger_replanning(
        self,
        cycle_id: int,
        new_plan: str,
        plan_quality: float = 0.5,
        reason: str = None,
    ) -> str:
        """Trigger replanning."""
        try:
            self.store.trigger_replan(
                cycle_id,
                new_plan_description=new_plan,
                new_plan_quality=plan_quality,
                reason=reason or "Replanning triggered",
            )
            return '{"status": "replanned"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _add_lesson_learned(
        self,
        cycle_id: int,
        lesson: str,
        source_attempt: int,
        confidence: float = 0.5,
        can_create_procedure: bool = False,
    ) -> str:
        """Add lesson learned."""
        try:
            self.store.add_lesson(
                cycle_id,
                lesson=lesson,
                source_attempt=source_attempt,
                confidence=confidence,
                can_create_procedure=can_create_procedure,
            )
            return '{"status": "lesson_added"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _complete_action_cycle(
        self,
        cycle_id: int,
        status: str,
        reason: str = None,
    ) -> str:
        """Complete cycle."""
        try:
            self.store.complete_cycle(
                cycle_id,
                final_status=status,
                reason_if_abandoned=reason,
            )
            return f'{{"status": "{status}"}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_action_cycle(self, cycle_id: int) -> str:
        """Get cycle."""
        try:
            cycle = self.store.get_cycle(cycle_id)
            if not cycle:
                return '{"error": "Cycle not found"}'
            return f'{{"status": "{cycle.status}", "success_rate": {cycle.success_rate}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_active_cycle(self, goal_id: str) -> str:
        """Get active cycle for goal."""
        try:
            cycle = self.store.get_active_cycle(goal_id)
            if not cycle:
                return '{"status": "no_active_cycle"}'
            return f'{{"status": "active", "cycle_id": {cycle.id}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_cycle_summary(self, cycle_id: int) -> str:
        """Get cycle summary."""
        try:
            summary = self.store.get_execution_summary(cycle_id)
            return str(summary).replace("'", '"')
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_active_cycles(self, session_id: str) -> str:
        """Get active cycles."""
        try:
            cycles = self.store.get_active_cycles(session_id)
            return f'{{"count": {len(cycles)}, "active_cycles": {len(cycles)}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'
