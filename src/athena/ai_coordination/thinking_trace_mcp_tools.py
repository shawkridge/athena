"""MCP tool handlers for ThinkingTraces layer."""

from mcp.types import Tool, TextContent

from ..core.database import Database
from .thinking_traces import ProblemType, ReasoningPattern, ReasoningStep, ThinkingTrace
from .thinking_trace_store import ThinkingTraceStore


class ThinkingTraceMCPTools:
    """MCP tools for ThinkingTraces layer."""

    def __init__(self, db: Database):
        """Initialize tools.

        Args:
            db: Database instance
        """
        self.store = ThinkingTraceStore(db)

    def get_tools(self) -> list[Tool]:
        """Get ThinkingTraces tools definitions.

        Returns:
            List of Tool definitions
        """
        return [
            Tool(
                name="record_reasoning",
                description="Record an AI reasoning process for solving a problem",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "problem": {
                            "type": "string",
                            "description": "Problem being reasoned about"
                        },
                        "problem_type": {
                            "type": "string",
                            "enum": ["architecture", "debugging", "optimization", "refactoring", "feature_design", "integration", "testing"],
                            "description": "Type of problem"
                        },
                        "problem_complexity": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Complexity level (1-10)"
                        },
                        "reasoning_steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step_number": {"type": "integer"},
                                    "thought": {"type": "string"},
                                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                    "decision_point": {"type": "boolean"},
                                    "decision_made": {"type": "string"},
                                    "rationale": {"type": "string"}
                                }
                            },
                            "description": "Reasoning steps taken"
                        },
                        "conclusion": {
                            "type": "string",
                            "description": "Final conclusion from reasoning"
                        },
                        "reasoning_quality": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Quality of reasoning (0.0-1.0)"
                        },
                        "primary_pattern": {
                            "type": "string",
                            "enum": ["decomposition", "analogy", "first_principles", "empirical", "heuristic", "deductive", "abductive"],
                            "description": "Primary reasoning pattern used"
                        },
                        "secondary_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Secondary reasoning patterns used"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID"
                        },
                        "duration_seconds": {
                            "type": "integer",
                            "description": "Time spent reasoning"
                        },
                        "ai_model_used": {
                            "type": "string",
                            "description": "Which AI model generated this reasoning"
                        }
                    },
                    "required": ["problem", "problem_type", "conclusion", "session_id"]
                }
            ),
            Tool(
                name="link_reasoning_to_execution",
                description="Link a reasoning trace to an execution outcome to track correctness",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "thinking_id": {
                            "type": "integer",
                            "description": "ID of thinking trace"
                        },
                        "execution_id": {
                            "type": "string",
                            "description": "UUID of ExecutionTrace this thinking led to"
                        },
                        "was_correct": {
                            "type": "boolean",
                            "description": "Whether the reasoning proved correct"
                        },
                        "outcome_quality": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Quality of execution outcome (0.0-1.0)"
                        }
                    },
                    "required": ["thinking_id", "execution_id", "was_correct", "outcome_quality"]
                }
            ),
            Tool(
                name="get_reasoning_patterns_effectiveness",
                description="Analyze which reasoning patterns are most effective",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="get_correctness_analysis",
                description="Analyze correctness of reasoning vs actual execution outcomes",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="get_thinking_by_pattern",
                description="Retrieve thinking traces that used a specific reasoning pattern",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "enum": ["decomposition", "analogy", "first_principles", "empirical", "heuristic", "deductive", "abductive"],
                            "description": "Reasoning pattern to filter by"
                        },
                        "min_effectiveness": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Minimum effectiveness threshold (0.0-1.0)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number to return"
                        }
                    },
                    "required": ["pattern"]
                }
            ),
            Tool(
                name="get_recent_reasoning",
                description="Get most recent reasoning traces",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number to return (default: 10)"
                        }
                    }
                }
            ),
            Tool(
                name="analyze_reasoning_quality",
                description="Analyze overall quality and effectiveness of reasoning across sessions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Optional: limit analysis to specific session"
                        }
                    }
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
            if name == "record_reasoning":
                return self._record_reasoning(**arguments)
            elif name == "link_reasoning_to_execution":
                return self._link_reasoning_to_execution(**arguments)
            elif name == "get_reasoning_patterns_effectiveness":
                return self._get_reasoning_patterns_effectiveness()
            elif name == "get_correctness_analysis":
                return self._get_correctness_analysis()
            elif name == "get_thinking_by_pattern":
                return self._get_thinking_by_pattern(**arguments)
            elif name == "get_recent_reasoning":
                return self._get_recent_reasoning(**arguments)
            elif name == "analyze_reasoning_quality":
                return self._analyze_reasoning_quality(**arguments)
            else:
                return '{"error": "Unknown tool"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _record_reasoning(
        self,
        problem: str,
        problem_type: str,
        conclusion: str,
        session_id: str,
        problem_complexity: int = 5,
        reasoning_steps: list[dict] = None,
        reasoning_quality: float = 0.5,
        primary_pattern: str = None,
        secondary_patterns: list[str] = None,
        duration_seconds: int = 0,
        ai_model_used: str = None,
    ) -> str:
        """Record a reasoning process.

        Args:
            problem: Problem being reasoned about
            problem_type: Type of problem
            conclusion: Final conclusion
            session_id: Session ID
            **kwargs: Other optional fields

        Returns:
            JSON with thinking_id and status
        """
        try:
            # Parse reasoning steps
            steps = []
            if reasoning_steps:
                for step_data in reasoning_steps:
                    steps.append(ReasoningStep(**step_data))

            # Parse secondary patterns
            secondary = []
            if secondary_patterns:
                for pattern_str in secondary_patterns:
                    try:
                        secondary.append(ReasoningPattern(pattern_str))
                    except ValueError:
                        pass

            trace = ThinkingTrace(
                problem=problem,
                problem_type=ProblemType(problem_type),
                problem_complexity=problem_complexity,
                reasoning_steps=steps,
                conclusion=conclusion,
                reasoning_quality=reasoning_quality,
                primary_pattern=ReasoningPattern(primary_pattern) if primary_pattern else None,
                secondary_patterns=secondary,
                session_id=session_id,
                duration_seconds=duration_seconds,
                ai_model_used=ai_model_used,
            )

            thinking_id = self.store.record_thinking(trace)
            return f'{{"status": "recorded", "thinking_id": {thinking_id}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _link_reasoning_to_execution(
        self,
        thinking_id: int,
        execution_id: str,
        was_correct: bool,
        outcome_quality: float,
    ) -> str:
        """Link reasoning to execution outcome.

        Args:
            thinking_id: Thinking trace ID
            execution_id: ExecutionTrace ID
            was_correct: Whether reasoning was correct
            outcome_quality: Quality of execution

        Returns:
            JSON with status
        """
        try:
            self.store.link_thinking_to_execution(
                thinking_id, execution_id, was_correct, outcome_quality
            )
            return '{"status": "linked"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_reasoning_patterns_effectiveness(self) -> str:
        """Get effectiveness analysis of reasoning patterns.

        Returns:
            JSON with pattern effectiveness data
        """
        try:
            analysis = self.store.get_reasoning_effectiveness()
            return str(analysis).replace("'", '"')
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_correctness_analysis(self) -> str:
        """Get correctness analysis.

        Returns:
            JSON with correctness metrics
        """
        try:
            analysis = self.store.get_correctness_analysis()
            return str(analysis).replace("'", '"')
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_thinking_by_pattern(
        self,
        pattern: str,
        min_effectiveness: float = 0.0,
        limit: int = 10,
    ) -> str:
        """Get thinking traces by pattern.

        Args:
            pattern: Reasoning pattern
            min_effectiveness: Minimum effectiveness
            limit: Max results

        Returns:
            JSON with thinking traces
        """
        try:
            results = self.store.get_thinking_by_pattern(
                ReasoningPattern(pattern), min_effectiveness
            )
            # Limit results
            results = results[:limit]
            return f'{{"count": {len(results)}, "results": "See detailed output"}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_recent_reasoning(self, limit: int = 10) -> str:
        """Get recent reasoning traces.

        Args:
            limit: Max results

        Returns:
            JSON with recent thinking
        """
        try:
            results = self.store.get_recent_thinking(limit=limit)
            return f'{{"count": {len(results)}, "recent": "See detailed output"}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _analyze_reasoning_quality(self, session_id: str = None) -> str:
        """Analyze reasoning quality.

        Args:
            session_id: Optional session filter

        Returns:
            JSON with quality metrics
        """
        try:
            if session_id:
                results = self.store.get_thinking_for_session(session_id)
            else:
                results = self.store.get_recent_thinking(limit=100)

            if not results:
                return '{"message": "No reasoning traces found"}'

            avg_quality = sum(t.reasoning_quality for t in results) / len(results)
            linked_count = sum(1 for t in results if t.linked_execution_id)
            correctness = sum(1 for t in results if t.was_reasoning_correct) / linked_count if linked_count > 0 else 0

            return f'''{{
                "total_traces": {len(results)},
                "avg_reasoning_quality": {avg_quality:.2f},
                "linked_to_executions": {linked_count},
                "correctness_rate": {correctness:.2f}
            }}'''
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'
