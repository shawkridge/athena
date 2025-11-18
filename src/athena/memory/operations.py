"""Semantic Memory Operations - Direct Python API

Functions for storing and searching semantic knowledge.
Semantic memory is for general knowledge and facts, not time-bound events.

Usage:
  from athena.memory.operations import store, search
  id = await store("Python is a programming language", topics=["programming"])
  results = await search("programming", limit=5)
"""

import logging
from typing import Any, Dict, List

from ..core.database import Database
from .store import MemoryStore

logger = logging.getLogger(__name__)


class SemanticOperations:
    """Semantic memory operations."""

    def __init__(self, db: Database, store: MemoryStore):
        self.db = db
        self.store = store
        self.logger = logger

    async def store(
        self,
        content: str,
        topics: List[str] | None = None,
        confidence: float = 0.8,
        source: str = "agent",
    ) -> str:
        """Store a fact or knowledge item."""
        if not content:
            raise ValueError("content is required")

        confidence = max(0.0, min(1.0, confidence))

        result = await self.store.store(
            content=content, topics=topics or [], confidence=confidence, metadata={"source": source}
        )
        return result

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.5,
        topics: List[str] | None = None,
    ) -> List[Dict[str, Any]]:
        """Search semantic memories."""
        if not query:
            return []

        return await self.store.search(
            query=query, limit=limit, min_confidence=min_confidence, topics=topics
        )


_operations: SemanticOperations | None = None


def initialize(db: Database, store: MemoryStore) -> None:
    """Initialize semantic operations."""
    global _operations
    _operations = SemanticOperations(db, store)


def get_operations() -> SemanticOperations:
    """Get semantic operations instance."""
    if _operations is None:
        raise RuntimeError("Semantic operations not initialized")
    return _operations


async def store(
    content: str,
    topics: List[str] | None = None,
    confidence: float = 0.8,
    source: str = "agent",
) -> str:
    """Store a semantic memory."""
    ops = get_operations()
    return await ops.store(content=content, topics=topics, confidence=confidence, source=source)


async def search(
    query: str,
    limit: int = 10,
    min_confidence: float = 0.5,
    topics: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Search semantic memories."""
    ops = get_operations()
    return await ops.search(query=query, limit=limit, min_confidence=min_confidence, topics=topics)
