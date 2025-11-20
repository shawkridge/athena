"""Integration of MemoryFlowRouter with EpisodicStore.

Provides a wrapper that adds flow routing to episodic event access,
so that accessing events triggers activation boost and RIF.
"""

import logging
from typing import Optional

from ..core.database import Database
from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from .router import MemoryFlowRouter

logger = logging.getLogger(__name__)


class FlowAwareEpisodicStore:
    """Episodic store wrapper that integrates memory flow routing.

    When events are accessed through this store, they trigger:
    - Activation boost
    - RIF (Retrieval-Induced Forgetting) on similar items
    - Potential promotion to working memory
    - Capacity enforcement

    This ensures that frequently accessed items stay active while
    weak memories fade, implementing natural working memory dynamics.
    """

    def __init__(self, db: Database, enable_flow_routing: bool = True):
        """Initialize flow-aware episodic store.

        Args:
            db: Database instance
            enable_flow_routing: If True, trigger flow routing on access
        """
        self.episodic = EpisodicStore(db)
        self.router = MemoryFlowRouter(db)
        self.enable_flow_routing = enable_flow_routing
        self.db = db

    async def get(self, event_id: int) -> Optional[EpisodicEvent]:
        """Get event by ID, triggering flow routing on access.

        Args:
            event_id: ID of event to retrieve

        Returns:
            EpisodicEvent instance or None
        """
        # Get the event normally
        event = await self.episodic.get(event_id)

        if event is not None and self.enable_flow_routing:
            try:
                # Record access in flow system
                # Boost based on event importance (higher importance = higher boost)
                boost = min(0.7, (event.importance_score or 0.5) * 0.5)
                await self.router.record_event_access(event_id, boost=boost)
                logger.debug(f"Recorded flow access for event {event_id}")
            except Exception as e:
                # Don't fail the get operation if flow routing fails
                logger.warning(f"Error recording flow access: {e}")

        return event

    async def list_by_session(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[EpisodicEvent]:
        """List events by session.

        Args:
            session_id: Session ID to filter by
            limit: Maximum number of events to return

        Returns:
            List of EpisodicEvent instances
        """
        return await self.episodic.list_by_session(session_id, limit)

    async def search(self, query: str, limit: int = 10) -> list[EpisodicEvent]:
        """Search events using flow-aware hot-first search.

        Uses the QueryRouter for hot-first search:
        1. Search working memory first (most active)
        2. Then session cache
        3. Finally episodic archive

        This optimizes for recency and activation.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching EpisodicEvent instances
        """
        # Use flow router's hot-first search
        results = await self.router.search_hot_first(query, limit=limit)

        if not results:
            # Fallback to regular search if flow search returns nothing
            return await self.episodic.search(query, limit)

        # Convert search results to full EpisodicEvent objects
        events = []
        for result in results:
            event = await self.episodic.get(result.get("event_id"))
            if event:
                events.append(event)

        return events

    async def store(self, event: EpisodicEvent) -> int:
        """Store a new event and initialize flow state.

        Args:
            event: EpisodicEvent instance to store

        Returns:
            Event ID
        """
        event_id = await self.episodic.store(event)

        if event_id and self.enable_flow_routing:
            try:
                # Initialize with activation based on importance
                initial_boost = min(0.7, (event.importance_score or 0.5) * 0.3)
                await self.router.record_event_access(event_id, boost=initial_boost)
                logger.debug(f"Initialized flow state for new event {event_id}")
            except Exception as e:
                # Don't fail store if flow initialization fails
                logger.warning(f"Error initializing flow state: {e}")

        return event_id

    async def update(self, event_id: int, **updates) -> bool:
        """Update an event.

        Args:
            event_id: ID of event to update
            **updates: Fields to update

        Returns:
            True if updated, False otherwise
        """
        result = await self.episodic.update(event_id, **updates)

        if result and self.enable_flow_routing:
            try:
                # Record access for the update
                await self.router.record_event_access(event_id, boost=0.2)
            except Exception as e:
                logger.warning(f"Error recording update access: {e}")

        return result

    async def get_working_memory_snapshot(self, limit: int = 7) -> list[dict]:
        """Get current working memory as full events with metadata.

        Returns working memory items along with their flow metrics.

        Args:
            limit: Maximum working memory items (default: 7±2)

        Returns:
            List of working memory event dicts with metadata
        """
        items = await self.router.get_working_memory(limit=limit)
        results = []

        for item in items:
            event = await self.episodic.get(item["event_id"])
            if event:
                results.append(
                    {
                        "event": event,
                        "activation_strength": item.get("activation_strength", 0),
                        "access_count": item.get("access_count", 0),
                        "last_access": item.get("last_access"),
                    }
                )

        return results

    async def get_consolidation_candidates(self, threshold: float = 0.7) -> list[dict]:
        """Get events ready for consolidation to semantic memory.

        Args:
            threshold: Minimum activation for consolidation

        Returns:
            List of candidate events with consolidation metadata
        """
        candidates = await self.router.get_consolidation_candidates(threshold)
        results = []

        for candidate in candidates:
            event = await self.episodic.get(candidate["event_id"])
            if event:
                results.append(
                    {
                        "event": event,
                        "consolidation_score": candidate.get("consolidation_score", 0),
                        "access_count": candidate.get("access_count", 0),
                    }
                )

        return results

    # Delegate other methods to episodic store
    async def delete(self, event_id: int) -> bool:
        """Delete an event."""
        return await self.episodic.delete(event_id)

    async def get_by_tags(self, tags: list[str]) -> list[EpisodicEvent]:
        """Get events by tags."""
        return await self.episodic.get_by_tags(tags)

    async def get_statistics(self) -> dict:
        """Get episodic store statistics."""
        return await self.episodic.get_statistics()


def wrap_episodic_store_with_flow(store: EpisodicStore, db: Database) -> FlowAwareEpisodicStore:
    """Wrap existing episodic store with flow routing.

    Useful for retrofitting existing code to use flow routing.

    Args:
        store: Existing EpisodicStore instance
        db: Database instance

    Returns:
        FlowAwareEpisodicStore wrapper
    """
    wrapper = FlowAwareEpisodicStore(db, enable_flow_routing=True)
    wrapper.episodic = store
    return wrapper
