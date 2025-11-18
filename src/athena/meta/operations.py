"""Meta-Memory Operations - Direct Python API

This module provides clean async functions for meta-memory operations.
Meta-memory tracks quality, confidence, expertise, and cognitive load.

Functions can be imported and called directly by agents:
  from athena.meta.operations import rate_memory, get_expertise
  await rate_memory("memory_id", quality=0.8, confidence=0.9)
  expertise = await get_expertise(topic="coding")

No MCP protocol, no wrapper overhead. Just Python async functions.
"""

import logging
from typing import Any, Dict

from ..core.database import Database
from .store import MetaMemoryStore

logger = logging.getLogger(__name__)


class MetaOperations:
    """Encapsulates all meta-memory operations.

    This class is instantiated with a database and meta-memory store,
    providing all operations as methods.
    """

    def __init__(self, db: Database, store: MetaMemoryStore):
        """Initialize with database and meta-memory store.

        Args:
            db: Database instance
            store: MetaMemoryStore instance
        """
        self.db = db
        self.store = store
        self.logger = logger

    async def rate_memory(
        self,
        memory_id: str,
        quality: float | None = None,
        confidence: float | None = None,
        usefulness: float | None = None,
    ) -> bool:
        """Rate a memory on quality, confidence, usefulness.

        Args:
            memory_id: Memory ID to rate
            quality: Quality score (0.0-1.0)
            confidence: Confidence score (0.0-1.0)
            usefulness: Usefulness score (0.0-1.0)

        Returns:
            True if rating was stored
        """
        if not memory_id:
            return False

        scores = {}
        if quality is not None:
            scores["quality"] = max(0.0, min(1.0, quality))
        if confidence is not None:
            scores["confidence"] = max(0.0, min(1.0, confidence))
        if usefulness is not None:
            scores["usefulness"] = max(0.0, min(1.0, usefulness))

        if not scores:
            return False

        return await self.store.rate_memory(memory_id, scores)

    async def get_expertise(
        self,
        topic: str | None = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get expertise scores for a topic or all topics.

        Args:
            topic: Optional topic filter
            limit: Maximum results

        Returns:
            Expertise scores
        """
        return await self.store.get_expertise(topic=topic, limit=limit)

    async def get_memory_quality(self, memory_id: str) -> Dict[str, float] | None:
        """Get quality metrics for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Quality scores or None if not found
        """
        return await self.store.get_memory_quality(memory_id)

    async def get_cognitive_load(self) -> Dict[str, Any]:
        """Get current cognitive load metrics.

        Returns:
            Cognitive load information
        """
        return await self.store.get_cognitive_load()

    async def update_cognitive_load(
        self,
        working_memory_items: int,
        active_tasks: int,
        recent_accuracy: float,
    ) -> bool:
        """Update cognitive load metrics.

        Args:
            working_memory_items: Number of items in working memory
            active_tasks: Number of active tasks
            recent_accuracy: Recent accuracy score (0.0-1.0)

        Returns:
            True if updated successfully
        """
        return await self.store.update_cognitive_load(
            working_memory_items=working_memory_items,
            active_tasks=active_tasks,
            recent_accuracy=max(0.0, min(1.0, recent_accuracy)),
        )

    async def get_statistics(self) -> Dict[str, Any]:
        """Get meta-memory statistics.

        Returns:
            Dictionary with meta-statistics
        """
        return await self.store.get_statistics()


# Global singleton instance (lazy-initialized by manager)
_operations: MetaOperations | None = None


def initialize(db: Database, store: MetaMemoryStore) -> None:
    """Initialize the global meta operations instance.

    Called by UnifiedMemoryManager during setup.

    Args:
        db: Database instance
        store: MetaMemoryStore instance
    """
    global _operations
    _operations = MetaOperations(db, store)


def get_operations() -> MetaOperations:
    """Get the global meta operations instance.

    Returns:
        MetaOperations instance

    Raises:
        RuntimeError: If not initialized
    """
    if _operations is None:
        raise RuntimeError("Meta operations not initialized. Call initialize(db, store) first.")
    return _operations


# Convenience functions that delegate to global instance
async def rate_memory(
    memory_id: str,
    quality: float | None = None,
    confidence: float | None = None,
    usefulness: float | None = None,
) -> bool:
    """Rate memory. See MetaOperations.rate_memory for details."""
    ops = get_operations()
    return await ops.rate_memory(
        memory_id=memory_id, quality=quality, confidence=confidence, usefulness=usefulness
    )


async def get_expertise(topic: str | None = None, limit: int = 10) -> Dict[str, Any]:
    """Get expertise. See MetaOperations.get_expertise for details."""
    ops = get_operations()
    return await ops.get_expertise(topic=topic, limit=limit)


async def get_memory_quality(memory_id: str) -> Dict[str, float] | None:
    """Get memory quality. See MetaOperations.get_memory_quality for details."""
    ops = get_operations()
    return await ops.get_memory_quality(memory_id)


async def get_cognitive_load() -> Dict[str, Any]:
    """Get cognitive load. See MetaOperations.get_cognitive_load for details."""
    ops = get_operations()
    return await ops.get_cognitive_load()


async def update_cognitive_load(
    working_memory_items: int,
    active_tasks: int,
    recent_accuracy: float,
) -> bool:
    """Update cognitive load. See MetaOperations.update_cognitive_load for details."""
    ops = get_operations()
    return await ops.update_cognitive_load(
        working_memory_items=working_memory_items,
        active_tasks=active_tasks,
        recent_accuracy=recent_accuracy,
    )


async def get_statistics() -> Dict[str, Any]:
    """Get meta statistics. See MetaOperations.get_statistics for details."""
    ops = get_operations()
    return await ops.get_statistics()
