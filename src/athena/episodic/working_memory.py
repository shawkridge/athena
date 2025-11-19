"""Working memory API with capacity management and consolidation triggers.

This module implements Baddeley's 7±2 working memory model with automatic
consolidation triggers when capacity is exceeded. Working memory acts as a
buffer between episodic events and semantic memory consolidation.

Architecture:
- Capacity: 7±2 items (configurable)
- Auto-consolidation when capacity exceeded
- Async/sync dual interface
- Item scoring for prioritization (recency, importance, distinctiveness)
"""

import logging
from datetime import datetime
from typing import Callable, Optional

from pydantic import BaseModel, Field

from ..consolidation.models import ConsolidationType
from ..core.async_utils import run_async
from ..core.database import Database
from .models import EpisodicEvent
from .store import EpisodicStore

logger = logging.getLogger(__name__)

# Baddeley's working memory capacity
DEFAULT_CAPACITY = 7
CAPACITY_THRESHOLD_LOW = 5  # Trigger consolidation at 5/7
CAPACITY_THRESHOLD_HIGH = 9  # Force consolidation at 9/7


class WorkingMemoryItem(BaseModel):
    """An item in working memory with metadata."""

    event_id: int
    event: EpisodicEvent
    added_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    recency_score: float = 1.0  # Higher = more recent
    importance_score: float = 0.5  # User-provided importance (0-1)
    distinctiveness_score: float = 0.5  # Novelty/distinctiveness


class WorkingMemoryAPI:
    """Working memory manager with capacity-based consolidation.

    Provides async/sync methods for managing working memory items and
    triggering consolidation when capacity is exceeded.

    Usage:
        api = WorkingMemoryAPI(db, episodic_store, consolidation_callback)

        # Async
        await api.push_async(event)
        items = await api.list_async()

        # Sync
        api.push(event)
        items = api.list()
    """

    def __init__(
        self,
        db: Database,
        episodic_store: EpisodicStore,
        consolidation_callback: Optional[Callable] = None,
        capacity: int = DEFAULT_CAPACITY,
    ):
        """Initialize working memory API.

        Args:
            db: Database instance
            episodic_store: Episodic store for event retrieval
            consolidation_callback: Async callback(events) to consolidate
            capacity: Working memory capacity (default 7)
        """
        self.db = db
        self.episodic_store = episodic_store
        self.consolidation_callback = consolidation_callback
        self.capacity = capacity

        # In-memory working memory buffer
        self._items: dict[int, WorkingMemoryItem] = {}

    # ==================== Async Methods ====================

    async def push_async(
        self,
        event: EpisodicEvent,
        importance: float = 0.5,
        distinctiveness: float = 0.5,
    ) -> dict:
        """Add event to working memory (async).

        Triggers consolidation if capacity exceeded.

        Args:
            event: Episodic event to add
            importance: Importance score 0-1
            distinctiveness: Distinctiveness score 0-1

        Returns:
            Dict with status and consolidation info
        """
        logger.debug(f"Adding event {event.id} to working memory")

        # Insert into database
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO working_memory
            (project_id, event_id, recency_score, importance_score, distinctiveness_score)
            VALUES (?, ?, ?, ?, ?)
        """,
            (event.project_id, event.id, 1.0, importance, distinctiveness),
        )

        self.db.commit()

        # Update in-memory buffer
        if event.id:
            self._items[event.id] = WorkingMemoryItem(
                event_id=event.id,
                event=event,
                importance_score=importance,
                distinctiveness_score=distinctiveness,
            )

        # Check capacity and trigger consolidation if needed
        size = await self._get_size_async()
        result = {
            "event_id": event.id,
            "working_memory_size": size,
            "capacity": self.capacity,
            "consolidation_triggered": False,
            "consolidation_run_id": None,
        }

        if size >= self.capacity:
            logger.info(
                f"Working memory capacity reached ({size}/{self.capacity}), "
                "triggering consolidation"
            )
            consolidation_run_id = await self._trigger_consolidation_async(
                event.project_id,
                trigger_type="capacity_threshold",
                consolidation_type=ConsolidationType.WORKING_MEMORY,
            )
            result["consolidation_triggered"] = True
            result["consolidation_run_id"] = consolidation_run_id

        return result

    async def list_async(
        self, project_id: int, sort_by: str = "recency"
    ) -> list[WorkingMemoryItem]:
        """List working memory items (async).

        Args:
            project_id: Project ID to filter
            sort_by: Sort key ('recency', 'importance', 'distinctiveness')

        Returns:
            List of working memory items, sorted
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM working_memory WHERE project_id = ?
            ORDER BY last_accessed DESC
        """,
            (project_id,),
        )

        rows = cursor.fetchall()
        items = []

        for row in rows:
            event = await self.episodic_store.get_async(row["event_id"])
            if event:
                item = WorkingMemoryItem(
                    event_id=row["event_id"],
                    event=event,
                    added_at=datetime.fromisoformat(row["added_at"]),
                    last_accessed=datetime.fromisoformat(row["last_accessed"]),
                    recency_score=row["recency_score"],
                    importance_score=row["importance_score"],
                    distinctiveness_score=row["distinctiveness_score"],
                )
                items.append(item)

        # Sort by specified key
        if sort_by == "importance":
            items.sort(key=lambda x: x.importance_score, reverse=True)
        elif sort_by == "distinctiveness":
            items.sort(key=lambda x: x.distinctiveness_score, reverse=True)
        else:  # recency (default)
            items.sort(key=lambda x: x.last_accessed, reverse=True)

        return items

    async def pop_async(self, event_id: int, project_id: int) -> Optional[EpisodicEvent]:
        """Remove and return event from working memory (async).

        Args:
            event_id: Event ID to remove
            project_id: Project ID for validation

        Returns:
            Removed event or None if not found
        """
        logger.debug(f"Removing event {event_id} from working memory")

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT event_id FROM working_memory
            WHERE event_id = ? AND project_id = ?
        """,
            (event_id, project_id),
        )

        row = cursor.fetchone()
        if not row:
            return None

        # Get event before deletion
        event = await self.episodic_store.get_async(event_id)

        # Delete from database
        cursor.execute(
            """
            DELETE FROM working_memory
            WHERE event_id = ? AND project_id = ?
        """,
            (event_id, project_id),
        )

        self.db.commit()

        # Remove from in-memory buffer
        if event_id in self._items:
            del self._items[event_id]

        return event

    async def clear_async(self, project_id: int) -> int:
        """Clear all working memory items for project (async).

        Args:
            project_id: Project ID to clear

        Returns:
            Number of items cleared
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM working_memory WHERE project_id = ?", (project_id,)
        )
        count = cursor.fetchone()["count"]

        cursor.execute("DELETE FROM working_memory WHERE project_id = ?", (project_id,))
        self.db.commit()

        # Clear in-memory buffer
        self._items.clear()

        logger.info(f"Cleared {count} items from working memory for project {project_id}")
        return count

    async def _get_size_async(self) -> int:
        """Get current working memory size (async)."""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT COUNT(*) as count FROM working_memory")
        return cursor.fetchone()["count"]

    async def _trigger_consolidation_async(
        self,
        project_id: int,
        trigger_type: str,
        consolidation_type: ConsolidationType,
    ) -> Optional[int]:
        """Trigger consolidation and log trigger event (async).

        Args:
            project_id: Project ID
            trigger_type: Type of trigger (e.g., 'capacity_threshold')
            consolidation_type: Consolidation type to run

        Returns:
            Consolidation run ID or None if callback not set
        """
        if not self.consolidation_callback:
            logger.warning("No consolidation callback set, skipping consolidation")
            return None

        # Get current working memory size
        size = await self._get_size_async()

        # Call consolidation callback
        try:
            consolidation_run_id = await self.consolidation_callback(
                project_id=project_id,
                consolidation_type=consolidation_type,
                max_events=size,
            )
        except Exception as e:
            logger.error(f"Consolidation callback failed: {e}")
            consolidation_run_id = None

        # Log trigger event
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO consolidation_triggers
            (project_id, trigger_type, working_memory_size, capacity,
             consolidation_type, consolidation_run_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                trigger_type,
                size,
                self.capacity,
                consolidation_type.value if consolidation_type else None,
                consolidation_run_id,
            ),
        )

        self.db.commit()

        return consolidation_run_id

    async def update_scores_async(
        self,
        event_id: int,
        importance: Optional[float] = None,
        distinctiveness: Optional[float] = None,
    ) -> bool:
        """Update scores for a working memory item (async).

        Args:
            event_id: Event ID to update
            importance: New importance score (0-1)
            distinctiveness: New distinctiveness score (0-1)

        Returns:
            True if updated, False if not found
        """
        cursor = self.db.get_cursor()

        # Build update query
        updates = ["last_accessed = CURRENT_TIMESTAMP"]
        params = []

        if importance is not None:
            updates.append("importance_score = ?")
            params.append(max(0, min(1, importance)))

        if distinctiveness is not None:
            updates.append("distinctiveness_score = ?")
            params.append(max(0, min(1, distinctiveness)))

        params.append(event_id)

        cursor.execute(
            f"""
            UPDATE working_memory
            SET {', '.join(updates)}
            WHERE event_id = ?
        """,
            params,
        )

        self.db.commit()
        affected = cursor.rowcount

        # Update in-memory buffer
        if event_id in self._items:
            if importance is not None:
                self._items[event_id].importance_score = importance
            if distinctiveness is not None:
                self._items[event_id].distinctiveness_score = distinctiveness
            self._items[event_id].last_accessed = datetime.now()

        return affected > 0

    # ==================== Sync Methods ====================

    def push(
        self,
        event: EpisodicEvent,
        importance: float = 0.5,
        distinctiveness: float = 0.5,
    ) -> dict:
        """Add event to working memory (sync).

        Triggers consolidation if capacity exceeded.

        Args:
            event: Episodic event to add
            importance: Importance score 0-1
            distinctiveness: Distinctiveness score 0-1

        Returns:
            Dict with status and consolidation info
        """
        return run_async(self.push_async(event, importance, distinctiveness))

    def list(self, project_id: int, sort_by: str = "recency") -> list[WorkingMemoryItem]:
        """List working memory items (sync).

        Args:
            project_id: Project ID to filter
            sort_by: Sort key ('recency', 'importance', 'distinctiveness')

        Returns:
            List of working memory items, sorted
        """
        return run_async(self.list_async(project_id, sort_by))

    def pop(self, event_id: int, project_id: int) -> Optional[EpisodicEvent]:
        """Remove and return event from working memory (sync).

        Args:
            event_id: Event ID to remove
            project_id: Project ID for validation

        Returns:
            Removed event or None if not found
        """
        return run_async(self.pop_async(event_id, project_id))

    def clear(self, project_id: int) -> int:
        """Clear all working memory items for project (sync).

        Args:
            project_id: Project ID to clear

        Returns:
            Number of items cleared
        """
        return run_async(self.clear_async(project_id))

    def get_size(self) -> int:
        """Get current working memory size (sync)."""
        return run_async(self._get_size_async())

    def update_scores(
        self,
        event_id: int,
        importance: Optional[float] = None,
        distinctiveness: Optional[float] = None,
    ) -> bool:
        """Update scores for a working memory item (sync).

        Args:
            event_id: Event ID to update
            importance: New importance score (0-1)
            distinctiveness: New distinctiveness score (0-1)

        Returns:
            True if updated, False if not found
        """
        return run_async(self.update_scores_async(event_id, importance, distinctiveness))
