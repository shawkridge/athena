"""MCP tool handlers for LearningIntegration layer."""

from mcp.types import Tool

from ..core.database import Database
from .learning_integration_store import LearningIntegrationStore


class LearningIntegrationMCPTools:
    """MCP tools for LearningIntegration layer."""

    def __init__(self, db: Database):
        """Initialize tools.

        Args:
            db: Database instance
        """
        self.store = LearningIntegrationStore(db)

    def get_tools(self) -> list[Tool]:
        """Get LearningIntegration tool definitions.

        Returns:
            List of Tool definitions
        """
        return [
            Tool(
                name="create_procedure_from_lesson",
                description="Create a reusable procedure from a single lesson",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lesson_id": {"type": "integer", "description": "Lesson ID"},
                        "lesson_text": {
                            "type": "string",
                            "description": "The lesson learned",
                        },
                        "procedure_name": {
                            "type": "string",
                            "description": "Proposed procedure name",
                        },
                        "procedure_steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Implementation steps",
                        },
                        "pattern_type": {
                            "type": "string",
                            "description": "error_recovery, optimization, design, workflow, testing",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence 0.0-1.0",
                        },
                    },
                    "required": [
                        "lesson_id",
                        "lesson_text",
                        "procedure_name",
                        "procedure_steps",
                    ],
                },
            ),
            Tool(
                name="find_procedure_candidates",
                description="Find clusters of similar lessons ready for procedures",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "min_confidence": {
                            "type": "number",
                            "description": "Minimum confidence threshold (default: 0.7)",
                        },
                        "min_frequency": {
                            "type": "integer",
                            "description": "Minimum number of similar lessons (default: 2)",
                        },
                    },
                },
            ),
            Tool(
                name="apply_feedback_to_project",
                description="Apply feedback update to ProjectContext based on learning",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "feedback_type": {
                            "type": "string",
                            "description": "error_pattern, decision, lesson, recommendation",
                        },
                        "action": {
                            "type": "string",
                            "description": "update, deprecate, replace, add",
                        },
                        "target_id": {
                            "type": "string",
                            "description": "Which item to update (optional)",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why this feedback",
                        },
                        "new_data": {
                            "type": "object",
                            "description": "What to update with",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence 0.0-1.0",
                        },
                    },
                    "required": ["feedback_type", "action", "reason"],
                },
            ),
            Tool(
                name="get_learning_effectiveness",
                description="Get aggregated learning metrics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Period in days (default: 7)",
                        }
                    },
                },
            ),
            Tool(
                name="consolidate_similar_lessons",
                description="Group similar lessons and suggest consolidation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern_type": {
                            "type": "string",
                            "description": "Filter by pattern type (optional)",
                        },
                        "min_confidence": {
                            "type": "number",
                            "description": "Minimum confidence (default: 0.7)",
                        },
                    },
                },
            ),
            Tool(
                name="suggest_process_improvements",
                description="Get AI-generated suggestions for process improvements",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "focus_area": {
                            "type": "string",
                            "description": "Focus area (e.g., testing, error_recovery)",
                        }
                    },
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
        if tool_name == "create_procedure_from_lesson":
            return self._handle_create_procedure(tool_input)
        elif tool_name == "find_procedure_candidates":
            return self._handle_find_candidates(tool_input)
        elif tool_name == "apply_feedback_to_project":
            return self._handle_apply_feedback(tool_input)
        elif tool_name == "get_learning_effectiveness":
            return self._handle_get_metrics(tool_input)
        elif tool_name == "consolidate_similar_lessons":
            return self._handle_consolidate_lessons(tool_input)
        elif tool_name == "suggest_process_improvements":
            return self._handle_suggest_improvements(tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _handle_create_procedure(self, tool_input: dict) -> dict:
        """Handle create_procedure_from_lesson tool call."""
        try:
            lesson = self.store.create_lesson_to_procedure(
                lesson_id=tool_input["lesson_id"],
                lesson_text=tool_input["lesson_text"],
                confidence=tool_input.get("confidence", 0.7),
                pattern_type=tool_input.get("pattern_type", "optimization"),
                procedure_steps=tool_input.get("procedure_steps", []),
            )

            return {
                "status": "success",
                "lesson_id": lesson.id,
                "lesson_text": lesson.lesson_text,
                "can_create_procedure": lesson.can_create_procedure,
                "confidence": lesson.confidence,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_find_candidates(self, tool_input: dict) -> dict:
        """Handle find_procedure_candidates tool call."""
        try:
            min_conf = tool_input.get("min_confidence", 0.7)
            min_freq = tool_input.get("min_frequency", 2)

            candidates = self.store.find_procedure_candidates(
                min_confidence=min_conf, min_frequency=min_freq
            )

            return {
                "status": "success",
                "count": len(candidates),
                "candidates": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "confidence": c.confidence,
                        "frequency": c.frequency,
                        "success_rate": c.success_rate,
                        "ready_for_creation": c.ready_for_creation,
                    }
                    for c in candidates
                ],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_apply_feedback(self, tool_input: dict) -> dict:
        """Handle apply_feedback_to_project tool call."""
        try:
            feedback = self.store.create_feedback_update(
                update_type=tool_input["feedback_type"],
                action=tool_input["action"],
                reason=tool_input["reason"],
                new_data=tool_input.get("new_data"),
                target_id=tool_input.get("target_id"),
                confidence=tool_input.get("confidence", 0.5),
            )

            return {
                "status": "success",
                "feedback_id": feedback.id,
                "update_type": feedback.update_type,
                "action": feedback.action,
                "confidence": feedback.confidence,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_get_metrics(self, tool_input: dict) -> dict:
        """Handle get_learning_effectiveness tool call."""
        try:
            days = tool_input.get("days", 7)
            metrics = self.store.get_learning_metrics(days=days)

            return {
                "status": "success",
                "period_days": metrics.period_days,
                "lessons_extracted": metrics.total_lessons_extracted,
                "procedures_created": metrics.total_procedures_created,
                "feedback_applied": metrics.total_feedback_applied,
                "avg_confidence": f"{metrics.average_lesson_confidence:.2f}",
                "procedure_success_rate": f"{metrics.procedure_success_rate:.2f}",
                "time_saved_hours": f"{metrics.estimated_time_saved_hours:.1f}",
                "error_reduction_percent": f"{metrics.estimated_error_reduction_percent:.1f}%",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_consolidate_lessons(self, tool_input: dict) -> dict:
        """Handle consolidate_similar_lessons tool call."""
        try:
            min_conf = tool_input.get("min_confidence", 0.7)
            high_conf_lessons = self.store.get_lessons_by_confidence(
                min_confidence=min_conf
            )

            # Group by pattern type if specified
            pattern_type = tool_input.get("pattern_type")
            if pattern_type:
                high_conf_lessons = [
                    l for l in high_conf_lessons if l.pattern_type == pattern_type
                ]

            return {
                "status": "success",
                "lessons_found": len(high_conf_lessons),
                "pattern_type": pattern_type or "all",
                "min_confidence": min_conf,
                "top_lessons": [
                    {
                        "id": l.id,
                        "text": l.lesson_text[:100] + "...",
                        "confidence": l.confidence,
                        "pattern": l.pattern_type,
                    }
                    for l in high_conf_lessons[:5]
                ],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _handle_suggest_improvements(self, tool_input: dict) -> dict:
        """Handle suggest_process_improvements tool call."""
        try:
            focus_area = tool_input.get("focus_area", "general")

            # Get high-confidence lessons for suggestions
            high_conf = self.store.get_lessons_by_confidence(min_confidence=0.8)

            suggestions = [
                {
                    "area": l.pattern_type,
                    "lesson": l.lesson_text,
                    "suggested_action": f"Apply learned pattern: {l.suggested_procedure_name or 'TBD'}",
                    "confidence": l.confidence,
                }
                for l in high_conf[:5]
            ]

            return {
                "status": "success",
                "focus_area": focus_area,
                "suggestion_count": len(suggestions),
                "suggestions": suggestions,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
