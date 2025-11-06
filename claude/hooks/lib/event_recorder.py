"""Event recording for episodic memory integration."""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class EventRecorder:
    """Record episodic events from tool execution and user interactions."""

    def __init__(self, log_dir: Optional[str] = None):
        """Initialize event recorder.

        Args:
            log_dir: Directory for event logs. Defaults to ~/.claude/hooks/logs
        """
        if log_dir is None:
            log_dir = str(Path.home() / ".claude" / "hooks" / "logs")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def record_tool_execution(
        self,
        tool_name: str,
        status: str,
        duration_ms: int,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a tool execution event.

        Args:
            tool_name: Name of the tool that executed
            status: Execution status (success, failure, timeout)
            duration_ms: Execution time in milliseconds
            parameters: Tool parameters (optional)
            result: Tool result data (optional)
            error_message: Error message if failed (optional)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "tool_execution",
            "tool_name": tool_name,
            "status": status,
            "duration_ms": duration_ms,
            "parameters": parameters or {},
            "result": result or {},
            "error_message": error_message,
        }

        self._write_event(event)

    def record_task_start(
        self,
        task_id: str,
        task_name: str,
        estimated_duration_minutes: Optional[int] = None,
    ) -> None:
        """Record task start event.

        Args:
            task_id: Unique task identifier
            task_name: Human-readable task name
            estimated_duration_minutes: Estimated duration (optional)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "task_start",
            "task_id": task_id,
            "task_name": task_name,
            "estimated_duration_minutes": estimated_duration_minutes,
        }

        self._write_event(event)

    def record_task_completion(
        self,
        task_id: str,
        status: str,
        actual_duration_minutes: int,
        quality_score: float,
        learnings: Optional[list] = None,
    ) -> None:
        """Record task completion event.

        Args:
            task_id: Task identifier
            status: Completion status (success, partial, failure)
            actual_duration_minutes: Actual duration
            quality_score: Quality assessment (0.0-1.0)
            learnings: List of learnings extracted (optional)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "task_completion",
            "task_id": task_id,
            "status": status,
            "actual_duration_minutes": actual_duration_minutes,
            "quality_score": quality_score,
            "learnings": learnings or [],
        }

        self._write_event(event)

    def record_goal_progress(
        self,
        goal_id: str,
        progress_percent: int,
        milestone: Optional[str] = None,
    ) -> None:
        """Record goal progress update.

        Args:
            goal_id: Goal identifier
            progress_percent: Progress percentage (0-100)
            milestone: Completed milestone name (optional)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "goal_progress",
            "goal_id": goal_id,
            "progress_percent": progress_percent,
            "milestone": milestone,
        }

        self._write_event(event)

    def record_memory_consolidation(
        self,
        event_count: int,
        new_memories: int,
        procedures_extracted: int,
        quality_metrics: Dict[str, float],
    ) -> None:
        """Record consolidation event.

        Args:
            event_count: Number of episodic events processed
            new_memories: Number of new semantic memories created
            procedures_extracted: Number of procedures extracted
            quality_metrics: Quality measurement dictionary
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "consolidation",
            "event_count": event_count,
            "new_memories": new_memories,
            "procedures_extracted": procedures_extracted,
            "quality_metrics": quality_metrics,
        }

        self._write_event(event)

    def _write_event(self, event: Dict[str, Any]) -> None:
        """Write event to log file.

        Args:
            event: Event dictionary
        """
        # Use session-based log file
        session_date = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"events-{session_date}.jsonl"

        # Append event as JSON line
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def get_session_events(self, date: Optional[str] = None) -> list:
        """Get all events from a session.

        Args:
            date: Session date (YYYY-MM-DD format). Defaults to today.

        Returns:
            List of event dictionaries
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        log_file = self.log_dir / f"events-{date}.jsonl"

        if not log_file.exists():
            return []

        events = []
        with open(log_file, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        return events
