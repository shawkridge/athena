"""Agent Event System - Pub/Sub for inter-agent communication.

This module defines the event model and types for agent-to-agent communication.
Agents broadcast events about their findings, decisions, and outcomes.
Other agents subscribe to events and adapt their behavior accordingly.

Example:
    CodeAnalyzer finds an issue:
    >>> event = AgentEvent(
    ...     agent_id="code-analyzer",
    ...     event_type="finding_identified",
    ...     data={"issue": "SQL injection", "severity": 0.95},
    ...     confidence=0.95,
    ...     tags=["security", "critical"]
    ... )
    >>> await event_bus.publish(event)

    Orchestrator listens for findings:
    >>> async for event in event_bus.subscribe("finding_identified"):
    ...     if event.confidence > 0.8:
    ...         await orchestrator.adjust_routing(event)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentEventType(str, Enum):
    """Types of events agents can publish."""

    # Analysis & Findings
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETE = "analysis_complete"
    FINDING_IDENTIFIED = "finding_identified"
    PATTERN_DETECTED = "pattern_detected"

    # Planning & Strategy
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    STRATEGY_ADAPTED = "strategy_adapted"

    # Routing & Decisions
    ROUTING_DECISION_MADE = "routing_decision_made"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"

    # Health & Monitoring
    HEALTH_CHECK_COMPLETE = "health_check_complete"
    DEGRADATION_DETECTED = "degradation_detected"
    ADAPTATION_SUGGESTED = "adaptation_suggested"

    # Learning & Adaptation
    OUTCOME_RECORDED = "outcome_recorded"
    SUCCESS_RATE_UPDATED = "success_rate_updated"
    LEARNING_COMPLETE = "learning_complete"

    # Collaboration
    KNOWLEDGE_SHARED = "knowledge_shared"
    REQUEST_FOR_HELP = "request_for_help"
    CONSENSUS_REACHED = "consensus_reached"
    CONFLICT_DETECTED = "conflict_detected"

    # Error Handling
    ERROR_ENCOUNTERED = "error_encountered"
    WARNING_ISSUED = "warning_issued"


class AgentEventPriority(str, Enum):
    """Priority of events for subscriber processing."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AgentEvent(BaseModel):
    """Event published by one agent for consumption by others.

    This is the fundamental communication unit in the agent network.
    All inter-agent communication flows through these events.
    """

    # Identity
    agent_id: str = Field(..., description="ID of agent that published this event")
    event_type: AgentEventType = Field(..., description="Type of event")

    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When event occurred")
    sequence_number: int = Field(default=0, description="Sequence for ordering")

    # Data & Payload
    data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

    # Quality Metrics
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this event (0.0-1.0)",
    )
    priority: AgentEventPriority = Field(default=AgentEventPriority.NORMAL)

    # Causation Chain
    parent_event_id: Optional[str] = Field(None, description="Event that triggered this")
    session_id: Optional[str] = Field(None, description="Session this event belongs to")

    # Categorization
    tags: List[str] = Field(default_factory=list, description="Tags for filtering")
    source: str = Field(default="agent", description="Source of event")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic config."""
        use_enum_values = False

    def __str__(self) -> str:
        """String representation."""
        return f"AgentEvent({self.agent_id}/{self.event_type.value}@{self.timestamp})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"AgentEvent(agent_id='{self.agent_id}', "
            f"event_type={self.event_type.value}, "
            f"confidence={self.confidence}, "
            f"data={self.data})"
        )

    def matches_filter(
        self,
        agent_ids: Optional[List[str]] = None,
        event_types: Optional[List[AgentEventType]] = None,
        min_confidence: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Check if event matches filter criteria.

        Args:
            agent_ids: Only events from these agents
            event_types: Only these event types
            min_confidence: Only events with confidence >= this
            tags: Only events with any of these tags

        Returns:
            True if event matches all filters
        """
        if agent_ids and self.agent_id not in agent_ids:
            return False

        if event_types and self.event_type not in event_types:
            return False

        if self.confidence < min_confidence:
            return False

        if tags and not any(tag in self.tags for tag in tags):
            return False

        return True


class AgentEventBatch(BaseModel):
    """Batch of events for efficient processing."""

    events: List[AgentEvent] = Field(default_factory=list)
    batch_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def add_event(self, event: AgentEvent) -> None:
        """Add event to batch."""
        self.events.append(event)

    def get_by_agent(self, agent_id: str) -> List[AgentEvent]:
        """Get all events from specific agent."""
        return [e for e in self.events if e.agent_id == agent_id]

    def get_by_type(self, event_type: AgentEventType) -> List[AgentEvent]:
        """Get all events of specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_high_confidence(self, threshold: float = 0.8) -> List[AgentEvent]:
        """Get high-confidence events."""
        return [e for e in self.events if e.confidence >= threshold]


class EventSubscription(BaseModel):
    """Subscription to event stream."""

    subscriber_id: str = Field(..., description="ID of subscriber")
    event_types: List[AgentEventType] = Field(
        default_factory=list, description="Event types to receive"
    )
    agent_ids: Optional[List[str]] = Field(None, description="Only from these agents")
    min_confidence: float = Field(default=0.0, description="Minimum confidence")
    tags: Optional[List[str]] = Field(None, description="Only with these tags")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def matches_event(self, event: AgentEvent) -> bool:
        """Check if event matches subscription."""
        return event.matches_filter(
            agent_ids=self.agent_ids,
            event_types=self.event_types or None,
            min_confidence=self.min_confidence,
            tags=self.tags,
        )


# Event constants for common patterns
CRITICAL_FINDING = AgentEventType.FINDING_IDENTIFIED
STRATEGY_CHANGE = AgentEventType.STRATEGY_ADAPTED
TASK_ROUTING = AgentEventType.ROUTING_DECISION_MADE
SYSTEM_HEALTH = AgentEventType.HEALTH_CHECK_COMPLETE
LEARNING_UPDATE = AgentEventType.LEARNING_COMPLETE
CONSENSUS = AgentEventType.CONSENSUS_REACHED
CONFLICT = AgentEventType.CONFLICT_DETECTED
