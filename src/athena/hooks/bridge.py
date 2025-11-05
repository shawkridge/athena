"""Bridge between HookDispatcher and EventHandlers for unified hook system.

This module connects the conversation/session lifecycle hooks (HookDispatcher)
with the task automation events (EventHandlers), creating a unified event system
that spans both conversation context and task execution.
"""

import asyncio
import logging
from typing import Optional, Callable
from ..hooks.dispatcher import HookDispatcher
from ..automation.event_handlers import EventHandlers

logger = logging.getLogger(__name__)


class HookEventBridge:
    """Bridges HookDispatcher with EventHandlers for unified event propagation.

    Architecture:
    - HookDispatcher: Session/conversation/task lifecycle hooks
    - EventHandlers: Task automation events (task_created, task_completed, etc.)
    - HookEventBridge: Routes hook events to automation event system

    This creates a unified system where:
    1. Hooks capture conversation context
    2. Events trigger automation actions
    3. Both feed into episodic memory consolidation
    """

    def __init__(self, hook_dispatcher: HookDispatcher, event_handlers: EventHandlers):
        """Initialize bridge between hooks and events.

        Args:
            hook_dispatcher: HookDispatcher instance
            event_handlers: EventHandlers instance
        """
        self.hook_dispatcher = hook_dispatcher
        self.event_handlers = event_handlers
        self._is_enabled = True
        self._event_mapping_count = 0

        logger.info("HookEventBridge initialized")

    async def on_task_started(
        self, task_id: str, task_description: str, goal: Optional[str] = None
    ) -> None:
        """Route task started hook to task_created event.

        Args:
            task_id: Task identifier
            task_description: Task description
            goal: Optional goal
        """
        if not self._is_enabled:
            return

        try:
            # Trigger task_created event for automation
            await self.event_handlers.trigger_event(
                event_type="task_created",
                entity_id=task_id,
                entity_type="task",
                metadata={
                    "description": task_description,
                    "goal": goal,
                    "session_id": self.hook_dispatcher.get_active_session_id(),
                },
            )
            self._event_mapping_count += 1
        except Exception as e:
            logger.error(f"Error triggering task_created event: {e}")

    async def on_task_completed(self, task_id: str, outcome: str) -> None:
        """Route task completed hook to task_completed event.

        Args:
            task_id: Task identifier
            outcome: Task outcome (SUCCESS, FAILURE, PARTIAL)
        """
        if not self._is_enabled:
            return

        try:
            # Trigger task_completed event for automation
            await self.event_handlers.trigger_event(
                event_type="task_completed",
                entity_id=task_id,
                entity_type="task",
                metadata={
                    "outcome": outcome,
                    "session_id": self.hook_dispatcher.get_active_session_id(),
                },
            )
            self._event_mapping_count += 1
        except Exception as e:
            logger.error(f"Error triggering task_completed event: {e}")

    async def on_consolidation_start(self, event_count: int) -> None:
        """Route consolidation start to automation event.

        Args:
            event_count: Number of events being consolidated
        """
        if not self._is_enabled:
            return

        try:
            # Trigger custom consolidation event
            await self.event_handlers.trigger_event(
                event_type="task_status_changed",
                entity_id="consolidation",
                entity_type="system",
                metadata={
                    "status": "consolidating",
                    "event_count": event_count,
                    "session_id": self.hook_dispatcher.get_active_session_id(),
                },
            )
            self._event_mapping_count += 1
        except Exception as e:
            logger.error(f"Error triggering consolidation event: {e}")

    async def on_error_occurred(
        self, error_type: str, error_message: str, context_str: Optional[str] = None
    ) -> None:
        """Route error hook to health_degraded event.

        Args:
            error_type: Type of error
            error_message: Error message
            context_str: Optional context
        """
        if not self._is_enabled:
            return

        try:
            # Trigger health_degraded event for automation
            await self.event_handlers.trigger_event(
                event_type="health_degraded",
                entity_id="error",
                entity_type="error",
                metadata={
                    "error_type": error_type,
                    "error_message": error_message,
                    "context": context_str,
                    "session_id": self.hook_dispatcher.get_active_session_id(),
                },
            )
            self._event_mapping_count += 1
        except Exception as e:
            logger.error(f"Error triggering health_degraded event: {e}")

    def enable_bridging(self) -> None:
        """Enable event bridging."""
        self._is_enabled = True
        logger.info("Hook-Event bridge enabled")

    def disable_bridging(self) -> None:
        """Disable event bridging."""
        self._is_enabled = False
        logger.info("Hook-Event bridge disabled")

    def is_enabled(self) -> bool:
        """Check if bridging is enabled."""
        return self._is_enabled

    def get_bridge_stats(self) -> dict:
        """Get bridging statistics.

        Returns:
            Dict with bridging metrics
        """
        return {
            "enabled": self._is_enabled,
            "events_routed": self._event_mapping_count,
            "hook_dispatcher_stats": self.hook_dispatcher.get_all_hook_stats(),
            "listener_info": self.event_handlers.get_listener_info(),
        }

    def reset_stats(self) -> None:
        """Reset bridging statistics."""
        self._event_mapping_count = 0


class UnifiedHookSystem:
    """Unified hook system combining HookDispatcher and EventHandlers.

    Provides a single interface for managing both:
    1. Conversation/session lifecycle hooks
    2. Task automation events

    This creates a complete event pipeline:
    Hook -> Event -> Automation -> Episodic Memory -> Consolidation -> Semantic Memory
    """

    def __init__(
        self, hook_dispatcher: HookDispatcher, event_handlers: EventHandlers
    ):
        """Initialize unified hook system.

        Args:
            hook_dispatcher: HookDispatcher instance
            event_handlers: EventHandlers instance
        """
        self.hooks = hook_dispatcher
        self.events = event_handlers
        self.bridge = HookEventBridge(hook_dispatcher, event_handlers)

        logger.info("UnifiedHookSystem initialized")

    def get_system_status(self) -> dict:
        """Get comprehensive status of unified system.

        Returns:
            Dict with hooks, events, and bridge status
        """
        return {
            "hooks": {
                "registry": self.hooks.get_hook_registry(),
                "stats": self.hooks.get_all_hook_stats(),
                "safety": self.hooks.get_safety_stats(),
            },
            "events": {
                "listeners": self.events.get_listener_info(),
                "history_size": len(self.events._event_history),
            },
            "bridge": self.bridge.get_bridge_stats(),
        }

    def enable_all(self) -> None:
        """Enable all hooks and events."""
        for hook_id in self.hooks.get_hook_registry():
            self.hooks.enable_hook(hook_id)
        self.bridge.enable_bridging()
        logger.info("All hooks and events enabled")

    def disable_all(self) -> None:
        """Disable all hooks and events."""
        for hook_id in self.hooks.get_hook_registry():
            self.hooks.disable_hook(hook_id)
        self.bridge.disable_bridging()
        logger.info("All hooks and events disabled")

    def reset_all_stats(self) -> None:
        """Reset all statistics."""
        self.hooks.reset_hook_stats()
        self.bridge.reset_stats()
        logger.info("All statistics reset")
