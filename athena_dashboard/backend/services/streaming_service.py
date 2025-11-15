"""Streaming service for real-time research results from Athena MCP."""

import asyncio
import json
import logging
from typing import Callable, Optional, Any, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""

    PROGRESS = "progress"
    FINDING = "finding"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Finding:
    """A research finding."""

    id: str
    title: str
    content: str
    source: Optional[str] = None
    relevance_score: float = 0.0
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dict."""
        return asdict(self)


@dataclass
class AgentProgress:
    """Agent execution progress."""

    agent_id: str
    name: str
    status: str  # "running", "waiting", "complete"
    findings_count: int = 0
    total_findings: int = 0
    rate: float = 0.0  # findings per second
    eta_seconds: Optional[float] = None
    latency_ms: Optional[float] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dict."""
        return asdict(self)


@dataclass
class StreamingUpdate:
    """A streaming update event."""

    event_type: EventType
    timestamp: str
    data: Dict[str, Any]

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(
            {
                "type": self.event_type.value,
                "timestamp": self.timestamp,
                "data": self.data,
            }
        )


class StreamingService:
    """Service for streaming research results from Athena MCP."""

    def __init__(self, athena_url: str = "http://localhost:3000"):
        """Initialize streaming service.

        Args:
            athena_url: Base URL for Athena API (for future HTTP-based polling)
        """
        self.athena_url = athena_url
        self.active_streams: Dict[str, asyncio.Task] = {}
        self.stream_callbacks: Dict[str, List[Callable]] = {}
        self.task_data: Dict[str, Dict] = {}  # Cache of streaming data

    async def start_streaming(
        self,
        task_id: str,
        on_update: Callable[[StreamingUpdate], None],
    ) -> None:
        """Start streaming results for a research task.

        Args:
            task_id: Unique task identifier
            on_update: Callback function for each update
        """
        if task_id in self.active_streams:
            logger.warning(f"Task {task_id} already streaming")
            return

        # Register callback
        if task_id not in self.stream_callbacks:
            self.stream_callbacks[task_id] = []
        self.stream_callbacks[task_id].append(on_update)

        # Initialize task data
        self.task_data[task_id] = {
            "findings": [],
            "agents": {},
            "total_findings": 0,
            "started_at": datetime.utcnow().isoformat(),
        }

        # Create streaming task
        stream_task = asyncio.create_task(self._stream_loop(task_id))
        self.active_streams[task_id] = stream_task

        logger.info(f"Started streaming for task {task_id}")

    async def stop_streaming(self, task_id: str) -> None:
        """Stop streaming results for a research task.

        Args:
            task_id: Unique task identifier
        """
        if task_id not in self.active_streams:
            logger.warning(f"Task {task_id} not actively streaming")
            return

        # Cancel streaming task
        task = self.active_streams.pop(task_id)
        task.cancel()

        # Clear callbacks
        if task_id in self.stream_callbacks:
            del self.stream_callbacks[task_id]

        logger.info(f"Stopped streaming for task {task_id}")

    async def _stream_loop(self, task_id: str) -> None:
        """Main streaming loop for a task.

        Args:
            task_id: Unique task identifier
        """
        try:
            poll_interval = 1  # Start with 1 second
            max_retries = 3
            retry_count = 0

            while task_id in self.active_streams:
                try:
                    # Simulate polling from Athena MCP
                    # TODO: Replace with actual MCP client calls
                    # - Call stream_results(task_id)
                    # - Call agent_progress(task_id)
                    await asyncio.sleep(poll_interval)

                    # Publish simulated updates for demo
                    await self._broadcast_update(
                        task_id,
                        StreamingUpdate(
                            event_type=EventType.PROGRESS,
                            timestamp=datetime.utcnow().isoformat(),
                            data={
                                "task_id": task_id,
                                "findings_count": len(self.task_data[task_id]["findings"]),
                                "total_findings": self.task_data[task_id]["total_findings"],
                                "agents": list(self.task_data[task_id]["agents"].values()),
                            },
                        ),
                    )

                    # Reset retry counter on successful poll
                    retry_count = 0

                except asyncio.CancelledError:
                    logger.info(f"Streaming loop cancelled for task {task_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in streaming loop for task {task_id}: {e}")
                    retry_count += 1

                    if retry_count >= max_retries:
                        # Publish error and stop
                        await self._broadcast_update(
                            task_id,
                            StreamingUpdate(
                                event_type=EventType.ERROR,
                                timestamp=datetime.utcnow().isoformat(),
                                data={
                                    "task_id": task_id,
                                    "error": f"Max retries ({max_retries}) exceeded",
                                },
                            ),
                        )
                        break

                    # Exponential backoff
                    poll_interval = min(2 ** retry_count, 30)
                    logger.info(f"Retrying in {poll_interval}s... (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(poll_interval)

        finally:
            # Cleanup
            if task_id in self.active_streams:
                self.active_streams.pop(task_id, None)
            logger.info(f"Streaming loop finished for task {task_id}")

    async def add_finding(
        self,
        task_id: str,
        finding: Finding,
    ) -> None:
        """Add a finding to the streaming task.

        Args:
            task_id: Unique task identifier
            finding: Finding to add
        """
        if task_id not in self.task_data:
            logger.warning(f"Task {task_id} not found")
            return

        # Add to findings list
        self.task_data[task_id]["findings"].append(asdict(finding))

        # Publish finding event
        await self._broadcast_update(
            task_id,
            StreamingUpdate(
                event_type=EventType.FINDING,
                timestamp=datetime.utcnow().isoformat(),
                data={
                    "task_id": task_id,
                    "finding": asdict(finding),
                    "total_findings": len(self.task_data[task_id]["findings"]),
                },
            ),
        )

    async def update_agent_progress(
        self,
        task_id: str,
        agent_progress: AgentProgress,
    ) -> None:
        """Update agent progress.

        Args:
            task_id: Unique task identifier
            agent_progress: Agent progress data
        """
        if task_id not in self.task_data:
            logger.warning(f"Task {task_id} not found")
            return

        # Update agent data
        self.task_data[task_id]["agents"][agent_progress.agent_id] = asdict(
            agent_progress
        )

        # Publish progress event
        await self._broadcast_update(
            task_id,
            StreamingUpdate(
                event_type=EventType.PROGRESS,
                timestamp=datetime.utcnow().isoformat(),
                data={
                    "task_id": task_id,
                    "agent": asdict(agent_progress),
                    "all_agents": list(self.task_data[task_id]["agents"].values()),
                },
            ),
        )

    async def complete_task(self, task_id: str) -> None:
        """Mark a streaming task as complete.

        Args:
            task_id: Unique task identifier
        """
        if task_id not in self.task_data:
            logger.warning(f"Task {task_id} not found")
            return

        # Publish completion event
        task_data = self.task_data[task_id]
        await self._broadcast_update(
            task_id,
            StreamingUpdate(
                event_type=EventType.COMPLETE,
                timestamp=datetime.utcnow().isoformat(),
                data={
                    "task_id": task_id,
                    "findings_count": len(task_data["findings"]),
                    "total_findings": task_data["total_findings"],
                    "agents": list(task_data["agents"].values()),
                    "completed_at": datetime.utcnow().isoformat(),
                },
            ),
        )

        # Stop streaming
        await self.stop_streaming(task_id)

    async def _broadcast_update(
        self,
        task_id: str,
        update: StreamingUpdate,
    ) -> None:
        """Broadcast an update to all subscribers.

        Args:
            task_id: Task identifier
            update: Update to broadcast
        """
        if task_id not in self.stream_callbacks:
            return

        callbacks = self.stream_callbacks.get(task_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.error(f"Error in callback for task {task_id}: {e}")

    def get_task_data(self, task_id: str) -> Optional[Dict]:
        """Get current task data.

        Args:
            task_id: Task identifier

        Returns:
            Task data or None if not found
        """
        return self.task_data.get(task_id)

    async def cleanup(self) -> None:
        """Clean up all active streams."""
        task_ids = list(self.active_streams.keys())
        for task_id in task_ids:
            await self.stop_streaming(task_id)
        logger.info(f"Cleaned up {len(task_ids)} active streams")
