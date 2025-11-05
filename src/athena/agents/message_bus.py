"""
Message Bus for Agent Communication

Provides asynchronous, priority-based message routing between agents.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class MessageType(str, Enum):
    """Types of messages agents can send"""
    REQUEST = "request"
    RESPONSE = "response"
    ALERT = "alert"
    UPDATE = "update"
    HEARTBEAT = "heartbeat"


@dataclass
class Message:
    """
    Message passed between agents.

    Attributes:
        sender: Name of sending agent
        recipient: Name of receiving agent
        message_type: Type of message
        payload: Message content
        priority: Priority for processing (0.0-1.0)
        timestamp: When message was created
        correlation_id: ID for request/response pairing
        response_expected: Whether sender expects response
        timeout_seconds: How long to wait for response
    """
    sender: str
    recipient: str
    message_type: MessageType
    payload: Dict[str, Any]
    priority: float = 0.5
    timestamp: int = 0
    correlation_id: str = ""
    response_expected: bool = False
    timeout_seconds: int = 30

    def __post_init__(self):
        """Set defaults for timestamp and correlation_id"""
        if self.timestamp == 0:
            self.timestamp = int(datetime.now().timestamp())
        if not self.correlation_id:
            self.correlation_id = str(uuid4())

    def __lt__(self, other: "Message") -> bool:
        """
        For priority queue ordering (higher priority first).

        Args:
            other: Message to compare

        Returns:
            True if self has lower priority
        """
        return self.priority < other.priority

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "response_expected": self.response_expected,
            "timeout_seconds": self.timeout_seconds,
        }


class MessageBus:
    """
    Central message routing hub for agents.

    Features:
    - Priority-based message queue
    - Request/response pairing with timeout
    - Subscribe/publish pattern
    - Backpressure handling
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize message bus.

        Args:
            max_queue_size: Maximum messages in queue
        """
        self.message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_log: List[Dict[str, Any]] = []
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None
        self._max_log_size = 10000  # Keep last 10k messages

    async def initialize(self) -> None:
        """Start message bus processing"""
        self._running = True
        self._processing_task = asyncio.create_task(self._process_messages())

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        self._running = False
        if self._processing_task:
            try:
                await asyncio.wait_for(self._processing_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._processing_task.cancel()
        await self.message_queue.join()

    async def publish(self, message: Message) -> None:
        """
        Publish message to queue (fire and forget).

        Args:
            message: Message to publish
        """
        try:
            # Use negative priority for heap ordering (higher priority first)
            await self.message_queue.put((-message.priority, message))
            self._log_message(message, "published")
        except asyncio.QueueFull:
            self._log_message(message, "dropped_queue_full")

    async def subscribe(self, recipient: str, handler: Callable) -> None:
        """
        Subscribe to messages for a recipient.

        Args:
            recipient: Agent name to subscribe to
            handler: Async function to handle messages
        """
        if recipient not in self.subscribers:
            self.subscribers[recipient] = []
        self.subscribers[recipient].append(handler)

    async def send_request(self, message: Message) -> Dict[str, Any]:
        """
        Send request and wait for response.

        Args:
            message: Message to send

        Returns:
            Response payload or error dict if timeout

        Raises:
            TimeoutError: If response not received in time
        """
        future: asyncio.Future = asyncio.Future()
        self.pending_responses[message.correlation_id] = future

        try:
            await self.publish(message)
            response = await asyncio.wait_for(
                future,
                timeout=message.timeout_seconds
            )
            self._log_message(message, "request_completed")
            return response
        except asyncio.TimeoutError:
            error_response = {
                "status": "error",
                "error": f"Response timeout from {message.recipient}",
                "correlation_id": message.correlation_id
            }
            self._log_message(message, "request_timeout")
            return error_response
        finally:
            self.pending_responses.pop(message.correlation_id, None)

    async def send_response(self, correlation_id: str, response: Dict[str, Any]) -> None:
        """
        Send response to pending request.

        Args:
            correlation_id: ID of original request
            response: Response payload
        """
        if correlation_id in self.pending_responses:
            future = self.pending_responses[correlation_id]
            if not future.done():
                future.set_result(response)

    async def _process_messages(self) -> None:
        """Main message processing loop"""
        while self._running:
            try:
                # Wait for message with timeout
                _, message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )

                # Route to subscribers
                if message.recipient in self.subscribers:
                    handlers = self.subscribers[message.recipient]
                    for handler in handlers:
                        try:
                            if message.response_expected:
                                response = await handler(message)
                                await self.send_response(message.correlation_id, response)
                                self._log_message(message, "handled_with_response")
                            else:
                                asyncio.create_task(handler(message))
                                self._log_message(message, "handled_async")
                        except Exception as e:
                            error_response = {
                                "status": "error",
                                "error": str(e),
                                "correlation_id": message.correlation_id
                            }
                            await self.send_response(message.correlation_id, error_response)
                            self._log_message(message, "handler_error")
                else:
                    self._log_message(message, "no_subscriber")

                self.message_queue.task_done()

            except asyncio.TimeoutError:
                # Continue waiting for messages
                continue
            except Exception as e:
                # Log error but continue processing
                pass

    def _log_message(self, message: Message, status: str) -> None:
        """
        Log message for monitoring.

        Args:
            message: Message to log
            status: Status of message handling
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "correlation_id": message.correlation_id,
            "sender": message.sender,
            "recipient": message.recipient,
            "message_type": message.message_type.value,
            "priority": message.priority,
            "status": status
        }
        self.message_log.append(log_entry)

        # Trim log if too large
        if len(self.message_log) > self._max_log_size:
            self.message_log = self.message_log[-self._max_log_size:]

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get message queue statistics.

        Returns:
            Stats including queue size and pending responses
        """
        return {
            "queue_size": self.message_queue.qsize(),
            "max_queue_size": self.message_queue.maxsize,
            "pending_responses": len(self.pending_responses),
            "subscribers": len(self.subscribers),
            "message_log_size": len(self.message_log),
            "queue_utilization": self.message_queue.qsize() / self.message_queue.maxsize
        }

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent messages from log.

        Args:
            limit: Maximum messages to return

        Returns:
            List of recent message log entries
        """
        return self.message_log[-limit:]
