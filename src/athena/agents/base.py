"""
Base Agent Class and Related Types

Provides the foundation for all agent types in Tier 2.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Enumeration of agent types"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    MONITOR = "monitor"
    PREDICTOR = "predictor"
    LEARNER = "learner"


class AgentStatus(str, Enum):
    """Agent operational status"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentMetrics:
    """Metrics for tracking agent health and performance"""
    decisions_made: int = 0
    decisions_successful: int = 0
    average_decision_time_ms: float = 0.0
    errors_encountered: int = 0
    last_heartbeat: int = 0
    uptime_seconds: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    message_queue_size: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0-1.0)"""
        if self.decisions_made == 0:
            return 1.0
        return self.decisions_successful / self.decisions_made

    @property
    def error_rate(self) -> float:
        """Calculate error rate (0.0-1.0)"""
        if self.decisions_made == 0:
            return 0.0
        return self.errors_encountered / self.decisions_made

    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all decisions"""
        if not self.confidence_scores:
            return 1.0
        return sum(self.confidence_scores) / len(self.confidence_scores)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "decisions_made": self.decisions_made,
            "decisions_successful": self.decisions_successful,
            "average_decision_time_ms": self.average_decision_time_ms,
            "errors_encountered": self.errors_encountered,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "average_confidence": self.average_confidence,
            "last_heartbeat": self.last_heartbeat,
            "uptime_seconds": self.uptime_seconds,
            "message_queue_size": self.message_queue_size,
        }


class BaseAgent(ABC):
    """
    Base class for all Tier 2 agents.

    Provides common functionality for:
    - Initialization and shutdown
    - Message handling
    - Metrics tracking
    - Health monitoring
    """

    def __init__(self, agent_type: AgentType, db_path: str):
        """
        Initialize agent.

        Args:
            agent_type: Type of agent (PLANNER, EXECUTOR, etc.)
            db_path: Path to memory database
        """
        self.agent_type = agent_type
        self.db_path = db_path
        self.status = AgentStatus.IDLE
        self.metrics = AgentMetrics()
        self.current_task_id: Optional[int] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.start_time = datetime.now()
        self._running = False
        self._message_handlers: Dict[str, callable] = {}

    async def initialize(self) -> None:
        """
        Initialize agent (asynchronous setup).

        Should be called before agent is used.
        """
        self._running = True
        self.metrics.last_heartbeat = int(datetime.now().timestamp())

    async def shutdown(self) -> None:
        """Graceful shutdown of agent."""
        self._running = False
        self.status = AgentStatus.SHUTDOWN

    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming message from message bus.

        Args:
            message: Message payload

        Returns:
            Response payload
        """
        pass

    @abstractmethod
    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a decision based on context.

        Args:
            context: Decision context

        Returns:
            Decision output with confidence score
        """
        pass

    async def send_message(self, message_bus, recipient: AgentType,
                          payload: Dict[str, Any], priority: float = 0.5,
                          response_expected: bool = False) -> Optional[Dict[str, Any]]:
        """
        Send message to another agent through message bus.

        Args:
            message_bus: MessageBus instance
            recipient: Target agent type
            payload: Message payload
            priority: Message priority (0.0-1.0)
            response_expected: Whether to wait for response

        Returns:
            Response if response_expected, else None
        """
        if not hasattr(message_bus, 'send_request'):
            return None

        message = {
            "sender": self.agent_type.value,
            "recipient": recipient.value,
            "payload": payload,
            "priority": priority,
            "timestamp": int(datetime.now().timestamp()),
            "response_expected": response_expected
        }

        if response_expected:
            return await message_bus.send_request(message)
        else:
            await message_bus.publish(message)
            return None

    def record_decision(self, success: bool, decision_time_ms: float,
                       confidence: float) -> None:
        """
        Record metrics for a decision made by agent.

        Args:
            success: Whether decision led to success
            decision_time_ms: Time taken to make decision
            confidence: Confidence score (0.0-1.0)
        """
        self.metrics.decisions_made += 1
        if success:
            self.metrics.decisions_successful += 1
        else:
            self.metrics.errors_encountered += 1

        # Update average decision time (rolling average)
        if self.metrics.decisions_made == 1:
            self.metrics.average_decision_time_ms = decision_time_ms
        else:
            old_avg = self.metrics.average_decision_time_ms
            new_avg = (old_avg * (self.metrics.decisions_made - 1) + decision_time_ms) / \
                     self.metrics.decisions_made
            self.metrics.average_decision_time_ms = new_avg

        self.metrics.confidence_scores.append(confidence)

        # Keep only last 100 confidence scores
        if len(self.metrics.confidence_scores) > 100:
            self.metrics.confidence_scores = self.metrics.confidence_scores[-100:]

        self.metrics.last_heartbeat = int(datetime.now().timestamp())

    async def heartbeat(self) -> Dict[str, Any]:
        """
        Generate heartbeat status report.

        Returns:
            Status report with metrics
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        self.metrics.uptime_seconds = int(uptime)

        return {
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "current_task_id": self.current_task_id,
            "metrics": self.metrics.to_dict(),
            "timestamp": int(datetime.now().timestamp())
        }

    def is_healthy(self) -> bool:
        """
        Check if agent is healthy.

        Returns:
            True if agent is healthy (low error rate, good performance)
        """
        if not self._running:
            return False

        # Consider unhealthy if error rate > 20%
        if self.metrics.error_rate > 0.2:
            return False

        # Consider unhealthy if average confidence < 50%
        if self.metrics.average_confidence < 0.5:
            return False

        return True

    def __repr__(self) -> str:
        return (
            f"Agent(type={self.agent_type.value}, status={self.status.value}, "
            f"decisions={self.metrics.decisions_made}, "
            f"success_rate={self.metrics.success_rate:.2%})"
        )
