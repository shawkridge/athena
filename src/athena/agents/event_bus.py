"""Event Bus - In-memory pub/sub for agent communication.

Agents publish events about their findings and decisions.
Other agents subscribe to events and adapt accordingly.

This implementation uses an in-memory event bus for fast, local communication.
Events are also stored in Athena memory for persistence and replay.
"""

import logging
from typing import AsyncIterator, Callable, Dict, List, Optional, Set
from asyncio import Queue, Event
from datetime import datetime
from uuid import uuid4

from .agent_events import (
    AgentEvent,
    AgentEventType,
    EventSubscription,
    AgentEventPriority,
)

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory event bus for inter-agent communication.

    Features:
    - Pub/Sub pattern (agents broadcast, others listen)
    - Event filtering (agents get only events they care about)
    - Event history (recent events can be replayed)
    - Sequence numbering (ordered event processing)
    """

    def __init__(self, max_history: int = 1000):
        """Initialize event bus.

        Args:
            max_history: Maximum number of events to keep in memory
        """
        self.max_history = max_history
        self.event_history: List[AgentEvent] = []

        # Subscriptions: event_type -> list of subscriber_ids
        self.subscriptions: Dict[str, List[str]] = {}

        # Queues for each subscription
        self.subscriber_queues: Dict[str, Queue] = {}

        # Subscription details by subscriber_id
        self.subscription_details: Dict[str, EventSubscription] = {}

        # Event counters for sequencing
        self.event_counter = 0

        # Shutdown event
        self.shutdown = Event()

    async def publish(self, event: AgentEvent) -> None:
        """Publish an event to all interested subscribers.

        Args:
            event: Event to publish
        """
        # Assign sequence number
        self.event_counter += 1
        event.sequence_number = self.event_counter

        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        logger.debug(f"EventBus: Published {event}")

        # Route to subscribers based on event type
        event_type_key = event.event_type.value
        if event_type_key in self.subscriptions:
            for subscriber_id in self.subscriptions[event_type_key]:
                queue = self.subscriber_queues.get(subscriber_id)
                if queue:
                    await queue.put(event)

        # Also route to "any_event" subscribers
        if "*" in self.subscriptions:
            for subscriber_id in self.subscriptions["*"]:
                queue = self.subscriber_queues.get(subscriber_id)
                if queue:
                    await queue.put(event)

    async def subscribe(
        self,
        subscriber_id: str,
        event_types: Optional[List[AgentEventType]] = None,
        agent_ids: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> AsyncIterator[AgentEvent]:
        """Subscribe to events matching criteria.

        Yields events that match the subscription filters.

        Args:
            subscriber_id: ID of subscribing agent
            event_types: Only these event types (None = all)
            agent_ids: Only from these agents
            min_confidence: Minimum confidence threshold
            tags: Only events with any of these tags

        Yields:
            Events matching subscription criteria
        """
        # Create subscription
        sub = EventSubscription(
            subscriber_id=subscriber_id,
            event_types=event_types or [],
            agent_ids=agent_ids,
            min_confidence=min_confidence,
            tags=tags,
        )

        # Create queue for this subscriber
        queue = Queue()
        self.subscriber_queues[subscriber_id] = queue

        # Register subscription for each event type
        event_type_keys = (
            [et.value for et in event_types] if event_types else ["*"]
        )
        for event_type_key in event_type_keys:
            if event_type_key not in self.subscriptions:
                self.subscriptions[event_type_key] = []
            if subscriber_id not in self.subscriptions[event_type_key]:
                self.subscriptions[event_type_key].append(subscriber_id)

        # Store subscription details
        self.subscription_details[subscriber_id] = sub

        logger.info(f"EventBus: {subscriber_id} subscribed to {event_type_keys}")

        try:
            while not self.shutdown.is_set():
                # Get event from queue with timeout
                try:
                    event = await queue.get()

                    # Apply filters
                    if sub.matches_event(event):
                        yield event

                except Exception as e:
                    logger.error(f"Error in subscriber {subscriber_id}: {e}")
                    break

        finally:
            # Cleanup
            for event_type_key in event_type_keys:
                if event_type_key in self.subscriptions:
                    try:
                        self.subscriptions[event_type_key].remove(subscriber_id)
                    except ValueError:
                        pass
            if subscriber_id in self.subscriber_queues:
                del self.subscriber_queues[subscriber_id]
            if subscriber_id in self.subscription_details:
                del self.subscription_details[subscriber_id]

            logger.info(f"EventBus: {subscriber_id} unsubscribed")

    async def get_events(
        self,
        event_type: Optional[AgentEventType] = None,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AgentEvent]:
        """Get events from history matching criteria.

        Args:
            event_type: Filter by event type
            agent_id: Filter by agent ID
            since: Only events after this datetime
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        results = []

        for event in reversed(self.event_history):
            if event_type and event.event_type != event_type:
                continue

            if agent_id and event.agent_id != agent_id:
                continue

            if since and event.timestamp < since:
                continue

            results.append(event)

            if len(results) >= limit:
                break

        return list(reversed(results))

    def get_stats(self) -> Dict[str, int]:
        """Get event bus statistics.

        Returns:
            Dict with stats
        """
        total_events = len(self.event_history)
        total_subscribers = len(self.subscriber_queues)
        event_counts = {}

        for event in self.event_history:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "total_events": total_events,
            "total_subscribers": total_subscribers,
            "event_counts": event_counts,
        }

    async def shutdown_bus(self) -> None:
        """Shutdown event bus gracefully."""
        logger.info("EventBus: Shutting down")
        self.shutdown.set()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def initialize_event_bus(max_history: int = 1000) -> EventBus:
    """Initialize global event bus.

    Args:
        max_history: Maximum events to keep

    Returns:
        Initialized event bus
    """
    global _event_bus
    _event_bus = EventBus(max_history=max_history)
    logger.info("EventBus: Initialized")
    return _event_bus


def get_event_bus() -> EventBus:
    """Get global event bus instance.

    Returns:
        Event bus (creates if needed)
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
