"""Core memory CRUD operations for semantic store."""

from typing import Optional
import logging
from datetime import datetime

from ..core.models import Memory, MemoryType, ConsolidationState

logger = logging.getLogger(__name__)


class MemoryOperations:
    """Memory CRUD operations (Create, Read, Update, Delete)."""

    def __init__(self, db, embedder):
        """Initialize memory operations.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    async def remember(
        self,
        content: str,
        memory_type: MemoryType | str,
        project_id: int,
        tags: Optional[list[str]] = None,
    ) -> int:
        """Store a new memory with embedding.

        Args:
            content: Memory content
            memory_type: Type of memory
            project_id: Project ID
            tags: Optional tags

        Returns:
            ID of stored memory

        Raises:
            ValueError: If content is empty or memory_type is invalid
            RuntimeError: If embedding generation or storage fails
        """
        # Validate content
        if not content or not content.strip():
            raise ValueError("Memory content cannot be empty")

        # Convert string to enum if needed
        try:
            if isinstance(memory_type, str):
                memory_type = MemoryType(memory_type)
        except ValueError as e:
            raise ValueError(f"Invalid memory type: {memory_type}") from e

        # Generate embedding with error handling
        try:
            embedding = self.embedder.embed(content)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e

        # Store in PostgreSQL with error handling
        try:
            memory_type_str = (
                memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
            )
            memory_id = await self.db.store_memory(
                project_id=project_id,
                content=content,
                embedding=embedding,
                memory_type=memory_type_str,
                tags=tags or [],
            )
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise RuntimeError(f"Memory storage failed: {e}") from e

        return memory_id

    def forget(self, memory_id: int) -> bool:
        """Delete a memory from PostgreSQL.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted, False if not found
        """
        return self.db.delete_memory(memory_id)

    def list_memories(
        self, project_id: int, limit: int = 20, sort_by: str = "useful"
    ) -> list[Memory]:
        """List memories for a project.

        Args:
            project_id: Project ID
            limit: Maximum number of memories
            sort_by: Sort order ('recent', 'useful', 'accessed')

        Returns:
            List of memories
        """
        return self.db.list_memories_sync(project_id, limit, 0, sort_by)

    def update_memory(
        self,
        memory_id: int,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        usefulness_score: Optional[float] = None,
    ) -> Optional[Memory]:
        """Update an existing memory.

        Args:
            memory_id: Memory ID to update
            content: New content (if any)
            tags: New tags (if any)
            usefulness_score: New usefulness score (if any)

        Returns:
            Updated memory or None if not found
        """
        memory = self.db.get_memory(memory_id)
        if not memory:
            return None

        # Create new version
        updates = {}
        if content is not None:
            updates["content"] = content
        if tags is not None:
            updates["tags"] = tags
        if usefulness_score is not None:
            updates["usefulness_score"] = usefulness_score

        if not updates:
            return memory

        updated = self.db.update_memory(memory_id, **updates)
        return updated
