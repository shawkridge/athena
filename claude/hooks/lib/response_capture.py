"""Response capture system for recording Claude's responses and tool execution results.

Enables complete conversation context for resume functionality:
- Records Claude's response turns
- Links to user questions
- Captures tool execution results
- Threads conversation flow for resume context
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ResponseTurn:
    """A Claude response turn in conversation."""

    turn_id: str
    user_question_id: str  # Links to user prompt
    response_content: str
    response_length: int
    tools_used: List[str]  # Tool names invoked (Read, Write, Task, etc.)
    tool_results: List[Dict]  # Results from tools
    timestamp: str
    response_time_ms: Optional[float] = None  # How long Claude took to respond

    def to_episodic_event(self) -> Dict:
        """Convert to episodic event format for storage."""
        tools_summary = ", ".join(self.tools_used) if self.tools_used else "none"
        success_indicators = sum(
            1 for r in self.tool_results if r.get("success", False)
        )

        return {
            "event_type": "claude_response",
            "content": f"Response to question {self.user_question_id[:8]}: {self.response_content[:200]}",
            "metadata": {
                "turn_id": self.turn_id,
                "question_id": self.user_question_id,
                "response_length": self.response_length,
                "tools_used": self.tools_used,
                "tools_successful": success_indicators,
                "tools_total": len(self.tool_results),
                "response_time_ms": self.response_time_ms,
            },
            "timestamp": self.timestamp,
        }


@dataclass
class ToolExecution:
    """Record of a single tool execution."""

    tool_name: str
    tool_input: Dict  # What was passed to tool
    tool_output: str  # Result/output
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class ResponseCapture:
    """Capture Claude response turns for conversation threading."""

    def __init__(self):
        """Initialize response capture."""
        self.current_turn: Optional[ResponseTurn] = None
        self.tool_executions: List[ToolExecution] = []

    def start_turn(self, user_question_id: str) -> str:
        """Start recording a new response turn.

        Args:
            user_question_id: ID of the user question being answered

        Returns:
            Turn ID for reference
        """
        turn_id = hashlib.md5(
            f"{user_question_id}_{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:8]

        self.current_turn = ResponseTurn(
            turn_id=turn_id,
            user_question_id=user_question_id,
            response_content="",
            response_length=0,
            tools_used=[],
            tool_results=[],
            timestamp=datetime.utcnow().isoformat(),
        )

        self.tool_executions = []
        logger.debug(f"Started response turn {turn_id}")
        return turn_id

    def record_response(self, response_text: str, response_time_ms: Optional[float] = None):
        """Record the response content.

        Args:
            response_text: Claude's response text
            response_time_ms: How long the response took (optional)
        """
        if not self.current_turn:
            logger.warning("No active turn to record response to")
            return

        self.current_turn.response_content = response_text
        self.current_turn.response_length = len(response_text)
        self.current_turn.response_time_ms = response_time_ms

    def record_tool_use(self, tool_name: str):
        """Record that a tool was used in this turn.

        Args:
            tool_name: Name of tool (Read, Write, Bash, Task, etc.)
        """
        if not self.current_turn:
            logger.warning("No active turn to record tool use to")
            return

        if tool_name not in self.current_turn.tools_used:
            self.current_turn.tools_used.append(tool_name)

    def record_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict,
        tool_output: str,
        execution_time_ms: float,
        success: bool,
        error_message: Optional[str] = None,
    ):
        """Record a tool execution result.

        Args:
            tool_name: Name of tool executed
            tool_input: Input provided to tool
            tool_output: Output/result from tool
            execution_time_ms: Execution time in milliseconds
            success: Whether execution succeeded
            error_message: Error message if failed
        """
        execution = ToolExecution(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output[:500],  # Truncate large outputs
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
        )

        self.tool_executions.append(execution)

        if self.current_turn:
            self.record_tool_use(tool_name)
            self.current_turn.tool_results.append(asdict(execution))

    def end_turn(self) -> Optional[ResponseTurn]:
        """End current turn and return the turn record.

        Returns:
            Completed ResponseTurn or None if no active turn
        """
        if not self.current_turn:
            return None

        turn = self.current_turn
        self.current_turn = None
        logger.debug(
            f"Ended turn {turn.turn_id}: {len(turn.tools_used)} tools, "
            f"{turn.response_length} chars"
        )
        return turn

    def get_turn_summary(self, turn: ResponseTurn) -> str:
        """Get human-readable summary of a turn.

        Args:
            turn: ResponseTurn to summarize

        Returns:
            Summary string
        """
        tools_summary = f"used {len(turn.tools_used)} tools" if turn.tools_used else "no tools"
        return (
            f"Response ({turn.response_length} chars, {tools_summary}): "
            f"{turn.response_content[:100]}..."
        )


class ConversationThreader:
    """Thread together user Q → Claude A → Tool Results for resume context."""

    def __init__(self):
        """Initialize conversation threader."""
        self.threads: List[Dict] = []  # Conversation threads
        self.current_thread: Optional[Dict] = None

    def start_thread(self, user_question_id: str, user_question: str) -> str:
        """Start a new conversation thread.

        Args:
            user_question_id: ID of user question
            user_question: The question text

        Returns:
            Thread ID
        """
        thread_id = user_question_id

        self.current_thread = {
            "thread_id": thread_id,
            "user_question_id": user_question_id,
            "user_question": user_question,
            "started_at": datetime.utcnow().isoformat(),
            "response_turns": [],
            "tools_executed": [],
            "outcome": None,
            "completed": False,
        }

        self.threads.append(self.current_thread)
        return thread_id

    def add_response_to_thread(self, turn: ResponseTurn):
        """Add a response turn to current thread.

        Args:
            turn: ResponseTurn to add
        """
        if not self.current_thread:
            logger.warning("No active thread to add response to")
            return

        self.current_thread["response_turns"].append(asdict(turn))

    def set_thread_outcome(
        self, outcome: str, completed: bool = True, result_summary: str = ""
    ):
        """Set outcome of thread (what was accomplished).

        Args:
            outcome: Brief outcome description (e.g., "code written", "bug fixed")
            completed: Whether thread concluded
            result_summary: Detailed summary of outcome
        """
        if not self.current_thread:
            return

        self.current_thread["outcome"] = outcome
        self.current_thread["completed"] = completed
        self.current_thread["result_summary"] = result_summary
        self.current_thread["ended_at"] = datetime.utcnow().isoformat()

    def get_thread_for_resume(self, thread_id: str, max_chars: int = 500) -> Optional[Dict]:
        """Get thread formatted for resume context.

        Args:
            thread_id: Thread to retrieve
            max_chars: Maximum characters to include

        Returns:
            Formatted thread dict or None
        """
        thread = next((t for t in self.threads if t["thread_id"] == thread_id), None)
        if not thread:
            return None

        # Format for resume
        resume_format = {
            "question": thread["user_question"][:100],
            "outcome": thread.get("outcome", "ongoing"),
            "tools_used": [],
            "key_results": [],
        }

        # Extract tool summaries
        for turn in thread.get("response_turns", []):
            resume_format["tools_used"].extend(turn.get("tools_used", []))
            # Add first successful tool result
            for result in turn.get("tool_results", []):
                if result.get("success"):
                    resume_format["key_results"].append(
                        f"{result.get('tool_name')}: success"
                    )

        # Deduplicate tools
        resume_format["tools_used"] = list(set(resume_format["tools_used"]))

        return resume_format

    def get_recent_threads(self, limit: int = 5) -> List[Dict]:
        """Get recent conversation threads for resume.

        Args:
            limit: Maximum threads to return

        Returns:
            List of threads (most recent first)
        """
        # Sort by start time, newest first
        sorted_threads = sorted(
            self.threads, key=lambda t: t["started_at"], reverse=True
        )

        # Format for resume
        resume_threads = []
        for thread in sorted_threads[:limit]:
            resume_threads.append(
                {
                    "question": thread["user_question"][:80],
                    "outcome": thread.get("outcome", "ongoing"),
                    "tools": list(set([t.get("tool_name") for turn in thread.get("response_turns", []) for t in turn.get("tool_results", [])])),
                }
            )

        return resume_threads


class ConversationMemoryBridge:
    """Bridge between conversation threading and episodic memory storage."""

    def __init__(self):
        """Initialize bridge."""
        self.capture = ResponseCapture()
        self.threader = ConversationThreader()

    def process_turn(
        self,
        user_question_id: str,
        user_question: str,
        response_text: str,
        tools_used: List[str],
        tool_results: List[Dict],
        response_time_ms: Optional[float] = None,
    ) -> Dict:
        """Process a complete conversation turn.

        Args:
            user_question_id: ID of user question
            user_question: The question text
            response_text: Claude's response
            tools_used: List of tools used
            tool_results: Results from tools
            response_time_ms: Response time in ms

        Returns:
            Conversation thread record
        """
        # Start thread if new question
        thread_id = self.threader.start_thread(user_question_id, user_question)

        # Start response turn
        turn_id = self.capture.start_turn(user_question_id)
        self.capture.record_response(response_text, response_time_ms)

        # Record tools
        for tool_name in tools_used:
            self.capture.record_tool_use(tool_name)

        for result in tool_results:
            self.capture.record_tool_execution(
                tool_name=result.get("tool_name", "unknown"),
                tool_input=result.get("input", {}),
                tool_output=result.get("output", ""),
                execution_time_ms=result.get("execution_time_ms", 0),
                success=result.get("success", False),
                error_message=result.get("error_message"),
            )

        # End turn and add to thread
        turn = self.capture.end_turn()
        if turn:
            self.threader.add_response_to_thread(turn)

        return self.threader.current_thread or {}

    def format_for_resume(self, max_threads: int = 3) -> str:
        """Format conversation threads for resume context injection.

        Args:
            max_threads: Maximum threads to include

        Returns:
            Formatted resume context string
        """
        recent_threads = self.threader.get_recent_threads(limit=max_threads)

        if not recent_threads:
            return ""

        lines = ["## Recent Work"]
        for thread in recent_threads:
            tools_str = ", ".join(thread.get("tools", [])[:3]) or "none"
            lines.append(f"- {thread['question'][:60]}")
            lines.append(f"  Outcome: {thread['outcome']}, Tools: {tools_str}")

        return "\n".join(lines)

    def get_memory_events(self, threads: List[Dict]) -> List[Dict]:
        """Convert threads to episodic events for storage.

        Args:
            threads: List of threads to convert

        Returns:
            List of episodic event records
        """
        events = []

        for thread in threads:
            # Create event for thread outcome
            if thread.get("outcome"):
                event = {
                    "event_type": "conversation_thread",
                    "content": f"Q: {thread['user_question'][:100]} → A: {thread['outcome']}",
                    "metadata": {
                        "thread_id": thread["thread_id"],
                        "tools_used": list(
                            set(
                                [
                                    t.get("tool_name")
                                    for turn in thread.get("response_turns", [])
                                    for t in turn.get("tool_results", [])
                                ]
                            )
                        ),
                        "turns": len(thread.get("response_turns", [])),
                    },
                    "timestamp": thread.get("ended_at", datetime.utcnow().isoformat()),
                }
                events.append(event)

        return events
