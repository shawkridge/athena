"""Event handlers for Phase 5-8 automation.

Routes task lifecycle events to AutomationOrchestrator for automated actions.
Events are triggered from:
- MCP tools (task creation, completion, status changes)
- Hooks (periodic monitoring, health checks)
- Manual triggers (resource conflict detection)
"""

import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
from dataclasses import dataclass

from ..core.database import Database
from .orchestrator import AutomationOrchestrator, AutomationEvent

logger = logging.getLogger(__name__)


@dataclass
class EventListener:
    """Listener registered for event types."""

    event_type: str
    handler: Callable
    name: str
    priority: int = 0  # Higher priority runs first


class EventHandlers:
    """Central event routing system for automation.

    Coordinates:
    - Event registration and listener management
    - Event triggering and routing
    - Async handler execution
    - Event history tracking
    """

    def __init__(self, db: Database, orchestrator: AutomationOrchestrator):
        """Initialize event handlers.

        Args:
            db: Database connection
            orchestrator: AutomationOrchestrator instance for handling events
        """
        self.db = db
        self.orchestrator = orchestrator

        # Event listeners by type
        self._listeners: Dict[str, List[EventListener]] = {
            "task_created": [],
            "task_completed": [],
            "task_status_changed": [],
            "resource_conflict_detected": [],
            "health_degraded": [],
        }

        # Event history for debugging
        self._event_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000

        # Register built-in handlers
        self._register_builtin_handlers()

        logger.info("EventHandlers initialized with built-in handlers")

    def _register_builtin_handlers(self):
        """Register default handlers that route to orchestrator."""
        self.register_listener(
            "task_created",
            self._handle_task_created,
            name="orchestrator_task_created",
            priority=100,
        )
        self.register_listener(
            "task_completed",
            self._handle_task_completed,
            name="orchestrator_task_completed",
            priority=100,
        )
        self.register_listener(
            "task_status_changed",
            self._handle_task_status_changed,
            name="orchestrator_task_status_changed",
            priority=100,
        )
        self.register_listener(
            "resource_conflict_detected",
            self._handle_resource_conflict,
            name="orchestrator_resource_conflict",
            priority=100,
        )
        self.register_listener(
            "health_degraded",
            self._handle_health_degraded,
            name="orchestrator_health_degraded",
            priority=100,
        )

    def register_listener(
        self,
        event_type: str,
        handler: Callable,
        name: str,
        priority: int = 0,
    ):
        """Register event listener.

        Args:
            event_type: Event type to listen for
            handler: Async handler function
            name: Listener name (for logging/debugging)
            priority: Handler priority (higher runs first)
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []

        listener = EventListener(
            event_type=event_type,
            handler=handler,
            name=name,
            priority=priority,
        )

        self._listeners[event_type].append(listener)
        # Sort by priority (highest first)
        self._listeners[event_type].sort(key=lambda l: l.priority, reverse=True)

        logger.info(f"Registered listener: {name} for {event_type} (priority={priority})")

    def unregister_listener(self, event_type: str, name: str) -> bool:
        """Unregister event listener.

        Args:
            event_type: Event type
            name: Listener name

        Returns:
            True if removed, False if not found
        """
        if event_type not in self._listeners:
            return False

        initial_count = len(self._listeners[event_type])
        self._listeners[event_type] = [l for l in self._listeners[event_type] if l.name != name]

        removed = len(self._listeners[event_type]) < initial_count
        if removed:
            logger.info(f"Unregistered listener: {name} from {event_type}")

        return removed

    async def trigger_event(
        self,
        event_type: str,
        entity_id: int,
        entity_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Trigger an event and invoke all registered listeners.

        Args:
            event_type: Type of event
            entity_id: Entity ID (task_id, project_id, etc.)
            entity_type: Entity type (task, project, etc.)
            metadata: Additional event metadata

        Returns:
            Dictionary with event handling results
        """
        event = AutomationEvent(
            event_type=event_type,
            entity_id=entity_id,
            entity_type=entity_type,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
        )

        logger.info(f"Triggering event: {event_type} on {entity_type} {entity_id}")

        # Record in history
        self._record_event_history(event)

        # Invoke all listeners for this event type
        if event_type not in self._listeners:
            logger.warning(f"No listeners registered for event type: {event_type}")
            return {
                "event_type": event_type,
                "status": "no_listeners",
                "results": [],
            }

        results = []
        listeners = self._listeners[event_type]

        for listener in listeners:
            try:
                logger.debug(f"Invoking listener: {listener.name}")
                if asyncio.iscoroutinefunction(listener.handler):
                    result = await listener.handler(event)
                else:
                    result = listener.handler(event)

                results.append(
                    {
                        "listener": listener.name,
                        "status": "success",
                        "result": result,
                    }
                )
            except Exception as e:
                logger.error(f"Error in listener {listener.name}: {e}")
                results.append(
                    {
                        "listener": listener.name,
                        "status": "error",
                        "error": str(e),
                    }
                )

        return {
            "event_type": event_type,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "status": "processed",
            "listener_count": len(listeners),
            "results": results,
        }

    async def _handle_task_created(self, event: AutomationEvent) -> Dict[str, Any]:
        """Handle task_created event.

        Routes to orchestrator for plan optimization.
        """
        return await self.orchestrator.handle_event(event)

    async def _handle_task_completed(self, event: AutomationEvent) -> Dict[str, Any]:
        """Handle task_completed event.

        Routes to orchestrator for analytics and pattern extraction.
        """
        return await self.orchestrator.handle_event(event)

    async def _handle_task_status_changed(self, event: AutomationEvent) -> Dict[str, Any]:
        """Handle task_status_changed event.

        Routes to orchestrator for health checks and alerts.
        """
        return await self.orchestrator.handle_event(event)

    async def _handle_resource_conflict(self, event: AutomationEvent) -> Dict[str, Any]:
        """Handle resource_conflict_detected event.

        Routes to orchestrator for conflict alerting.
        """
        return await self.orchestrator.handle_event(event)

    async def _handle_health_degraded(self, event: AutomationEvent) -> Dict[str, Any]:
        """Handle health_degraded event.

        Routes to orchestrator for optimization and escalation.
        """
        return await self.orchestrator.handle_event(event)

    def _record_event_history(self, event: AutomationEvent):
        """Record event in history for debugging.

        Args:
            event: Event to record
        """
        history_entry = {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "entity_id": event.entity_id,
            "entity_type": event.entity_type,
            "metadata": event.metadata,
        }

        self._event_history.append(history_entry)

        # Keep history size bounded
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size :]

    def get_event_history(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get event history.

        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return

        Returns:
            List of event history entries
        """
        history = self._event_history
        if event_type:
            history = [e for e in history if e["event_type"] == event_type]

        return history[-limit:]

    def get_listener_info(self) -> Dict[str, Any]:
        """Get information about registered listeners.

        Returns:
            Dictionary with listener counts and details
        """
        info = {
            "total_event_types": len(self._listeners),
            "by_type": {},
        }

        for event_type, listeners in self._listeners.items():
            info["by_type"][event_type] = {
                "listener_count": len(listeners),
                "listeners": [
                    {
                        "name": l.name,
                        "priority": l.priority,
                        "order": i + 1,
                    }
                    for i, l in enumerate(listeners)
                ],
            }

        return info

    # Public event triggering methods for convenience

    async def on_task_created(
        self, task_id: int, project_id: int, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trigger task_created event.

        Args:
            task_id: Task ID
            project_id: Project ID
            metadata: Additional metadata

        Returns:
            Event handling result
        """
        return await self.trigger_event(
            "task_created",
            task_id,
            "task",
            metadata={**(metadata or {}), "project_id": project_id},
        )

    async def on_task_completed(
        self, task_id: int, project_id: int, actual_duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Trigger task_completed event.

        Args:
            task_id: Task ID
            project_id: Project ID
            actual_duration: Actual duration in minutes

        Returns:
            Event handling result
        """
        return await self.trigger_event(
            "task_completed",
            task_id,
            "task",
            metadata={
                "project_id": project_id,
                "actual_duration": actual_duration,
            },
        )

    async def on_task_status_changed(
        self,
        task_id: int,
        project_id: int,
        new_status: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger task_status_changed event.

        Args:
            task_id: Task ID
            project_id: Project ID
            new_status: New task status
            reason: Reason for status change

        Returns:
            Event handling result
        """
        return await self.trigger_event(
            "task_status_changed",
            task_id,
            "task",
            metadata={
                "project_id": project_id,
                "new_status": new_status,
                "reason": reason or "",
            },
        )

    async def on_resource_conflict(
        self, project_ids: List[int], conflict_type: str, details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trigger resource_conflict_detected event.

        Args:
            project_ids: List of project IDs involved in conflict
            conflict_type: Type of conflict (person, tool, dependency)
            details: Conflict details

        Returns:
            Event handling result
        """
        return await self.trigger_event(
            "resource_conflict_detected",
            project_ids[0] if project_ids else 0,
            "projects",
            metadata={
                "project_ids": project_ids,
                "conflict_type": conflict_type,
                "details": details or {},
            },
        )

    async def on_health_degraded(
        self,
        task_id: int,
        project_id: int,
        health_score: float,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger health_degraded event.

        Args:
            task_id: Task ID
            project_id: Project ID
            health_score: New health score
            reason: Reason for degradation

        Returns:
            Event handling result
        """
        return await self.trigger_event(
            "health_degraded",
            task_id,
            "task",
            metadata={
                "project_id": project_id,
                "health_score": health_score,
                "reason": reason or "",
            },
        )
