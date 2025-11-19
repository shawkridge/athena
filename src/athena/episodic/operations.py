"""Episodic Memory Operations - Direct Python API

This module provides clean async functions for episodic memory operations.
These are extracted from MCP handlers and wrapped for direct use.

Functions can be imported and called directly by agents:
  from athena.episodic.operations import remember, recall
  event_id = await remember("User asked about timeline", tags=["meeting"])
  results = await recall("timeline", limit=5)

No MCP protocol, no wrapper overhead. Just Python async functions.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..core.database import Database
from .store import EpisodicStore
from .models import EpisodicEvent, EventType, EventContext, EventOutcome

logger = logging.getLogger(__name__)


class EpisodicOperations:
    """Encapsulates all episodic memory operations.

    This class is instantiated with a database and episodic store,
    providing all operations as methods.
    """

    def __init__(self, db: Database, store: EpisodicStore):
        """Initialize with database and episodic store.

        Args:
            db: Database instance
            store: EpisodicStore instance
        """
        self.db = db
        self.store = store
        self.logger = logger

    async def remember(
        self,
        content: str,
        context: Dict[str, Any] | None = None,
        tags: List[str] | None = None,
        source: str = "agent",
        importance: float = 0.5,
        session_id: str = "default",
        spatial_context: str = "/",
        project_id: int = 1,
    ) -> str:
        """Store an episodic event.

        Args:
            content: Event description
            context: Additional context information
            tags: Tags for categorization
            source: Source identifier (e.g., "agent", "user", "system")
            importance: Importance score (0.0-1.0)
            session_id: Session identifier
            spatial_context: File path or spatial location
            project_id: Project identifier (default: 1)

        Returns:
            Memory ID of stored event

        Raises:
            ValueError: If content is empty
        """
        if not content or not isinstance(content, str):
            raise ValueError("content is required and must be a string")

        importance = max(0.0, min(1.0, importance))

        event = EpisodicEvent(
            project_id=project_id,
            timestamp=datetime.now(),
            content=content,
            event_type=EventType.ACTION,
            context=EventContext(cwd=spatial_context),
            outcome=EventOutcome.SUCCESS,
            session_id=session_id,
            importance_score=importance,
        )

        await self.db.initialize()  # Ensure schema
        event_id = self.store.record_event(event)
        return str(event_id)

    async def recall(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.5,
        time_range: Dict[str, datetime] | None = None,
        tags: List[str] | None = None,
        session_id: str | None = None,
        project_id: int = 1,
    ) -> List[EpisodicEvent]:
        """Search episodic memories.

        Args:
            query: Search query string
            limit: Maximum results to return
            min_confidence: Minimum confidence threshold (0.0-1.0), filters by importance
            time_range: Optional time range with 'start' and 'end' keys
            tags: Optional tag filters
            session_id: Optional session filter
            project_id: Project identifier (default: 1)

        Returns:
            List of matching episodic events
        """
        if not query:
            return []

        # Use store's search_events with all filters (delegated to database level)
        results = self.store.search_events(
            project_id=project_id,
            query=query,
            limit=limit,
            min_importance=min_confidence,
            time_range=time_range,
            tags=tags,
            session_id=session_id,
        )

        return results

    async def recall_recent(
        self,
        limit: int = 5,
        session_id: str | None = None,
    ) -> List[EpisodicEvent]:
        """Get most recent episodic events.

        Args:
            limit: Number of events to return
            session_id: Optional session filter

        Returns:
            List of recent events, most recent first
        """
        filters = {"limit": limit, "order_by": "timestamp DESC"}
        if session_id:
            filters["session_id"] = session_id

        return await self.store.list(**filters)

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        project_id: int = 1,
    ) -> List[EpisodicEvent]:
        """Get all events from a session.

        Args:
            session_id: Session identifier
            limit: Maximum events to return
            project_id: Project identifier (default: 1)

        Returns:
            List of events from session
        """
        # Get all events for the project and filter by session
        all_events = self.store.list_events(
            project_id=project_id, limit=limit, order_by="timestamp DESC"
        )
        # Filter by session_id client-side
        return [e for e in all_events if e.session_id == session_id]

    async def get_by_tags(
        self,
        tags: List[str],
        limit: int = 100,
        project_id: int = 1,
    ) -> List[EpisodicEvent]:
        """Get events matching tags.

        Args:
            tags: Tags to search for
            limit: Maximum events to return
            project_id: Project identifier (default: 1)

        Returns:
            List of matching events
        """
        if not tags:
            return []

        # Use search_events to find events matching tags
        query = " OR ".join(tags)
        return self.store.search_events(project_id, query, limit=limit)

    async def get_by_time_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> List[EpisodicEvent]:
        """Get events within time range.

        Args:
            start: Start datetime
            end: End datetime
            limit: Maximum events to return

        Returns:
            List of events in time range
        """
        return await self.store.list(
            filters={
                "start_time": start,
                "end_time": end,
            },
            limit=limit,
            order_by="timestamp DESC",
        )

    async def delete_old(
        self,
        days: int = 30,
        batch_size: int = 100,
    ) -> int:
        """Delete events older than N days.

        Args:
            days: Delete events older than this many days
            batch_size: Number of events to delete per batch

        Returns:
            Number of events deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted = 0

        # Get events to delete in batches
        while True:
            events = await self.store.list(
                filters={"end_time": cutoff_date}, limit=batch_size, order_by="timestamp ASC"
            )

            if not events:
                break

            for event in events:
                await self.store.delete(event.id)
                deleted += 1

        return deleted

    async def get_statistics(
        self,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        """Get statistics about episodic memories.

        Args:
            session_id: Optional session filter

        Returns:
            Dictionary with statistics
        """
        filters = {}
        if session_id:
            filters["session_id"] = session_id

        all_events = await self.store.list(filters=filters, limit=10000)

        if not all_events:
            return {
                "total_events": 0,
                "quality_score": 0.0,
                "time_span_days": 0,
            }

        # Use confidence instead of non-existent 'importance' field
        confidences = [e.confidence for e in all_events if e.confidence is not None]
        timestamps = [e.timestamp for e in all_events if e.timestamp]

        return {
            "total_events": len(all_events),
            "quality_score": sum(confidences) / len(confidences) if confidences else 0.0,
            "min_quality": min(confidences) if confidences else 0.0,
            "max_quality": max(confidences) if confidences else 0.0,
            "earliest": min(timestamps).isoformat() if timestamps else None,
            "latest": max(timestamps).isoformat() if timestamps else None,
            "time_span_days": (
                (max(timestamps) - min(timestamps)).days if len(timestamps) > 1 else 0
            ),
        }


# Global singleton instance (lazy-initialized by manager)
_operations: EpisodicOperations | None = None


def initialize(db: Database, store: EpisodicStore) -> None:
    """Initialize the global episodic operations instance.

    Called by UnifiedMemoryManager during setup.

    Args:
        db: Database instance
        store: EpisodicStore instance
    """
    global _operations
    _operations = EpisodicOperations(db, store)


def get_operations() -> EpisodicOperations:
    """Get the global episodic operations instance.

    Returns:
        EpisodicOperations instance

    Raises:
        RuntimeError: If not initialized
    """
    if _operations is None:
        raise RuntimeError(
            "Episodic operations not initialized. " "Call initialize(db, store) first."
        )
    return _operations


# Convenience functions that delegate to global instance
async def remember(
    content: str,
    context: Dict[str, Any] | None = None,
    tags: List[str] | None = None,
    source: str = "agent",
    importance: float = 0.5,
    session_id: str = "default",
    spatial_context: str = "/",
) -> str:
    """Store an episodic event. See EpisodicOperations.remember for details."""
    ops = get_operations()
    return await ops.remember(
        content=content,
        context=context,
        tags=tags,
        source=source,
        importance=importance,
        session_id=session_id,
        spatial_context=spatial_context,
    )


async def recall(
    query: str,
    limit: int = 10,
    min_confidence: float = 0.5,
    time_range: Dict[str, datetime] | None = None,
    tags: List[str] | None = None,
    session_id: str | None = None,
) -> List[EpisodicEvent]:
    """Search episodic memories. See EpisodicOperations.recall for details."""
    ops = get_operations()
    return await ops.recall(
        query=query,
        limit=limit,
        min_confidence=min_confidence,
        time_range=time_range,
        tags=tags,
        session_id=session_id,
    )


async def recall_recent(
    limit: int = 5,
    session_id: str | None = None,
) -> List[EpisodicEvent]:
    """Get most recent events. See EpisodicOperations.recall_recent for details."""
    ops = get_operations()
    return await ops.recall_recent(limit=limit, session_id=session_id)


async def get_by_session(
    session_id: str,
    limit: int = 100,
) -> List[EpisodicEvent]:
    """Get all events from session. See EpisodicOperations.get_by_session for details."""
    ops = get_operations()
    return await ops.get_by_session(session_id=session_id, limit=limit)


async def get_by_tags(
    tags: List[str],
    limit: int = 100,
) -> List[EpisodicEvent]:
    """Get events by tags. See EpisodicOperations.get_by_tags for details."""
    ops = get_operations()
    return await ops.get_by_tags(tags=tags, limit=limit)


async def get_by_time_range(
    start: datetime,
    end: datetime,
    limit: int = 100,
) -> List[EpisodicEvent]:
    """Get events in time range. See EpisodicOperations.get_by_time_range for details."""
    ops = get_operations()
    return await ops.get_by_time_range(start=start, end=end, limit=limit)


async def delete_old(
    days: int = 30,
    batch_size: int = 100,
) -> int:
    """Delete old events. See EpisodicOperations.delete_old for details."""
    ops = get_operations()
    return await ops.delete_old(days=days, batch_size=batch_size)


async def get_statistics(
    session_id: str | None = None,
) -> Dict[str, Any]:
    """Get statistics. See EpisodicOperations.get_statistics for details."""
    ops = get_operations()
    return await ops.get_statistics(session_id=session_id)
