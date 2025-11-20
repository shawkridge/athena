"""Integration with Athena hooks for periodic memory flow management.

Provides handlers for:
- SessionStart: Initialize working memory state
- SessionEnd: Run consolidation cycle (sleep-like processing)
- PostToolUse: Record event access and apply RIF
- Periodic: Hourly decay cycle (background task)
"""

import logging
from datetime import datetime
from typing import Optional

from ..core.database import Database
from .router import MemoryFlowRouter

logger = logging.getLogger(__name__)


class FlowHooksHandler:
    """Handles memory flow events from Athena hooks."""

    def __init__(self, db: Optional[Database] = None):
        """Initialize hooks handler.

        Args:
            db: Database instance (if None, will be created on first use)
        """
        self.db = db
        self.router: Optional[MemoryFlowRouter] = None

    async def _get_router(self) -> MemoryFlowRouter:
        """Lazy-load router instance."""
        if self.router is None:
            if self.db is None:
                self.db = Database()
                await self.db.initialize()
            self.router = MemoryFlowRouter(self.db)
        return self.router

    async def on_session_start(self) -> dict:
        """Handle session start event.

        Initialize working memory with high-priority items from last session.

        Called by: SessionStart hook
        Returns: Dict with initialization stats
        """
        try:
            router = await self._get_router()

            # Get current working memory state
            items = await router.get_working_memory(limit=7)

            # Get health metrics for session awareness
            health = await router.get_flow_health()

            logger.info(f"Session started with {len(items)} working memory items")
            logger.debug(f"Memory health: {health}")

            return {
                "status": "success",
                "working_memory_items": len(items),
                "health": health,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error in on_session_start: {e}")
            return {"status": "error", "error": str(e)}

    async def on_session_end(self) -> dict:
        """Handle session end event.

        Run consolidation cycles (sleep-like processing):
        - Decay weak items
        - Promote strong items to semantic
        - Temporal clustering
        - Update statistics

        Called by: SessionEnd hook (before context is cleared)
        Returns: Dict with consolidation stats
        """
        try:
            router = await self._get_router()

            logger.info("Running sleep-like consolidation cycles...")

            # Run all consolidation in sequence
            decay_stats = await router.process_decay()
            consolidation_stats = await router.run_consolidation_cycle()
            clustering_stats = await router.run_temporal_clustering(promote_all=False)

            # Get final statistics
            final_health = await router.get_flow_health()

            stats = {
                "status": "success",
                "decay": decay_stats,
                "consolidation": consolidation_stats,
                "clustering": clustering_stats,
                "final_health": final_health,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Consolidation complete: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error in on_session_end: {e}")
            return {"status": "error", "error": str(e)}

    async def on_tool_use(self, tool_name: str, result: dict) -> dict:
        """Handle tool use event.

        Extract relevant event IDs from tool results and record access.
        This triggers activation boost and RIF for related items.

        Called by: PostToolUse hook
        Args:
            tool_name: Name of tool that was used
            result: Result from tool execution

        Returns: Dict with routing stats
        """
        try:
            # Only process if episodic event was created
            if "event_id" not in result:
                return {"status": "skipped", "reason": "no_event_id"}

            router = await self._get_router()
            event_id = result.get("event_id")

            # Record access with moderate boost (this was a recent activity)
            await router.record_event_access(event_id, boost=0.3)

            logger.debug(f"Recorded access for event {event_id} from tool {tool_name}")

            return {
                "status": "success",
                "event_id": event_id,
                "tool": tool_name,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error in on_tool_use: {e}")
            return {"status": "error", "error": str(e)}

    async def periodic_decay_cycle(self, interval_hours: int = 1) -> dict:
        """Run periodic decay cycle (can be called hourly/daily).

        Applies temporal decay to all items and enforces capacity limits.
        Designed to run as a background task at regular intervals.

        Args:
            interval_hours: How many hours since last decay

        Returns: Dict with decay stats
        """
        try:
            router = await self._get_router()

            # Update decay rates if custom interval
            if interval_hours != 1:
                # Scale decay rate for interval
                # Default: 0.01/hour → adjust for custom interval
                router.activation.decay_rate = 0.01 * interval_hours

            logger.info(f"Running {interval_hours}h decay cycle...")

            stats = await router.process_decay()

            logger.info(f"Decay cycle complete: {stats}")
            return {
                "status": "success",
                "stats": stats,
                "interval_hours": interval_hours,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error in periodic_decay_cycle: {e}")
            return {"status": "error", "error": str(e)}


# Singleton instance for hook integration
_handler: Optional[FlowHooksHandler] = None


def get_flow_hooks_handler(db: Optional[Database] = None) -> FlowHooksHandler:
    """Get or create singleton hooks handler.

    Args:
        db: Database instance (optional)

    Returns:
        FlowHooksHandler singleton
    """
    global _handler
    if _handler is None:
        _handler = FlowHooksHandler(db)
    return _handler


# Export hook handler functions for ~/.claude/hooks to import
async def handle_session_start() -> dict:
    """Hook: SessionStart event handler."""
    handler = get_flow_hooks_handler()
    return await handler.on_session_start()


async def handle_session_end() -> dict:
    """Hook: SessionEnd event handler."""
    handler = get_flow_hooks_handler()
    return await handler.on_session_end()


async def handle_tool_use(tool_name: str, result: dict) -> dict:
    """Hook: PostToolUse event handler."""
    handler = get_flow_hooks_handler()
    return await handler.on_tool_use(tool_name, result)


async def handle_periodic_decay(hours: int = 1) -> dict:
    """Hook: Periodic decay cycle handler."""
    handler = get_flow_hooks_handler()
    return await handler.periodic_decay_cycle(hours)
