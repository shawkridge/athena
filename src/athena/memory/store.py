"""Memory storage and retrieval operations."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union
import logging

from ..core.database import Database
from ..core.database_factory import get_database, DatabaseFactory
from ..core.base_store import BaseStore
from ..core.embeddings import EmbeddingModel
from ..core.models import Memory, MemorySearchResult, MemoryType, Project
from ..core import config
from ..core.async_utils import run_async
from .optimize import MemoryOptimizer
from .search import SemanticSearch

# Qdrant support is deprecated - we use PostgreSQL + pgvector instead
# QdrantAdapter import removed as part of host-based refactor

logger = logging.getLogger(__name__)


class MemoryStore(BaseStore):
    """High-level memory operations."""

    table_name = "memories"
    model_class = Memory

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        embedding_model: Optional[str] = None,
        use_qdrant: bool = False,
        backend: Optional[str] = None,
    ):
        """Initialize memory store with PostgreSQL + pgvector.

        Uses PostgreSQL exclusively for both storage and vector operations.
        For host-based development, uses PostgreSQL with pgvector extension.

        Args:
            db_path: Ignored (kept for backwards compatibility)
            embedding_model: Model name/path for embeddings (default: from config/provider)
            use_qdrant: Deprecated - always disabled. Use PostgreSQL + pgvector instead.
            backend: Force backend ('postgres' recommended, 'sqlite' discouraged)
        """
        # Force PostgreSQL for host-based development
        # We use PostgreSQL + pgvector exclusively, not Qdrant or SQLite
        logger.info("Initializing MemoryStore with PostgreSQL + pgvector backend")
        self.db = get_database(backend='postgres')

        super().__init__(self.db)
        # EmbeddingModel will use config provider (llamacpp at localhost:8001)
        self.embedder = EmbeddingModel(embedding_model)

        # Qdrant is deprecated - we use PostgreSQL pgvector instead
        self.qdrant = None
        if use_qdrant:
            logger.warning("Qdrant support is deprecated. Using PostgreSQL + pgvector instead.")

        # SemanticSearch will use PostgreSQL pgvector for vector operations
        self.search = SemanticSearch(self.db, self.embedder, qdrant=None)
        self.optimizer = MemoryOptimizer(self.db)

    @staticmethod
    def _should_use_postgres() -> bool:
        """Check if PostgreSQL should be used based on environment variables.

        Returns:
            True if PostgreSQL environment variables are configured
        """
        import os
        # Check for key PostgreSQL environment variables
        pg_vars = ['ATHENA_POSTGRES_HOST', 'DATABASE_URL', 'POSTGRES_HOST']
        return any(os.environ.get(var) for var in pg_vars)

    def _row_to_model(self, row: dict) -> Memory:
        """Convert database row to Memory model.

        Args:
            row: Database row as dict

        Returns:
            Memory instance
        """
        import json
        return Memory(
            id=row.get('id'),
            project_id=row.get('project_id'),
            content=row.get('content'),
            memory_type=MemoryType(row.get('memory_type')) if row.get('memory_type') else None,
            tags=json.loads(row.get('tags', '[]')) if row.get('tags') else [],
            embedding=row.get('embedding'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )

    async def remember(
        self,
        content: str,
        memory_type: MemoryType | str,
        project_id: int,
        tags: Optional[list[str]] = None,
    ) -> int:
        """Store a new memory with embedding.

        Implements dual-write pattern:
        - SQLite: Metadata (content, tags, timestamps)
        - Qdrant: Embeddings for semantic search

        Args:
            content: Memory content
            memory_type: Type of memory
            project_id: Project ID
            tags: Optional tags

        Returns:
            ID of stored memory
        """
        # Convert string to enum if needed
        if isinstance(memory_type, str):
            memory_type = MemoryType(memory_type)

        # Generate embedding
        embedding = self.embedder.embed(content)

        # Store in PostgreSQL with correct signature
        # PostgreSQL expects: store_memory(project_id, content, embedding, memory_type, ...)
        memory_type_str = memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
        memory_id = await self.db.store_memory(
            project_id=project_id,
            content=content,
            embedding=embedding,
            memory_type=memory_type_str,
            tags=tags or [],
        )

        # Store embedding in Qdrant if available
        if self.qdrant:
            try:
                self.qdrant.add_memory(
                    memory_id=memory_id,
                    content=content,
                    embedding=embedding,
                    metadata={
                        "project_id": project_id,
                        "memory_type": memory_type.value,
                        "tags": tags or [],
                    }
                )
                logger.debug(f"Stored embedding in Qdrant: memory_id={memory_id}")
            except Exception as e:
                logger.error(f"Failed to store embedding in Qdrant for memory {memory_id}: {e}")
                # Continue - metadata is already in SQLite

        return memory_id

    def forget(self, memory_id: int) -> bool:
        """Delete a memory from both SQLite and Qdrant.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted from SQLite, False if not found
        """
        # Delete from Qdrant first (non-blocking failure)
        if self.qdrant:
            try:
                self.qdrant.delete_memory(memory_id)
                logger.debug(f"Deleted memory {memory_id} from Qdrant")
            except Exception as e:
                logger.warning(f"Failed to delete memory {memory_id} from Qdrant: {e}")

        # Delete from SQLite (authoritative)
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
        return self.db.list_memories(project_id, limit, sort_by)

    def create_project(self, name: str, path: str) -> Project:
        """Create a new project.

        Args:
            name: Project name
            path: Project directory path

        Returns:
            Created project
        """
        return self.db.create_project(name, path)

    async def get_project_by_path(self, path: str) -> Optional[Project]:
        """Find project by path.

        Args:
            path: Directory path

        Returns:
            Project if found, None otherwise
        """
        return await self.db.get_project_by_path(path)

    def recall(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        memory_types: Optional[list[MemoryType]] = None,
    ) -> list[MemorySearchResult]:
        """Search for relevant memories semantically.

        Args:
            query: Search query
            project_id: Project ID
            k: Number of results
            memory_types: Optional filter by types

        Returns:
            List of search results with similarity scores
        """
        return self.search.recall(query, project_id, k, memory_types)

    def recall_with_reranking(
        self, query: str, project_id: int, k: int = 5
    ) -> list[MemorySearchResult]:
        """Search with composite scoring (similarity + recency + usefulness).

        Args:
            query: Search query
            project_id: Project ID
            k: Number of results

        Returns:
            Reranked search results
        """
        return self.search.recall_with_reranking(query, project_id, k)

    def search_across_projects(
        self, query: str, exclude_project_id: Optional[int] = None, k: int = 5
    ) -> list[MemorySearchResult]:
        """Search across all projects.

        Args:
            query: Search query
            exclude_project_id: Project to exclude
            k: Number of results

        Returns:
            Search results from all projects
        """
        return self.search.search_across_projects(query, exclude_project_id, k)

    def optimize(self, project_id: int, dry_run: bool = False) -> dict:
        """Run optimization: update scores and prune low-value memories.

        Args:
            project_id: Project ID
            dry_run: If True, don't actually delete

        Returns:
            Optimization statistics
        """
        return self.optimizer.optimize(project_id, dry_run)

    def update_memory(
        self,
        memory_id: int,
        new_content: str,
        update_reason: str,
        confidence: float = 1.0
    ) -> int:
        """Update memory during reconsolidation window.

        Based on neuroscience research (Nader & Hardt 2009): memories become
        labile when retrieved and can be modified during this window.

        Args:
            memory_id: Memory to update
            new_content: Updated content
            update_reason: Why this memory is being updated
            confidence: Confidence in update (0-1)

        Returns:
            New memory ID (superseding version)

        Raises:
            ValueError: If memory not found or not in labile state
        """
        import json

        # Get original memory
        original = self.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,),
            fetch_one=True
        )

        if not original:
            raise ValueError(f"Memory {memory_id} not found")

        # Create new version with same metadata
        new_id = self.remember(
            content=new_content,
            memory_type=MemoryType(original['memory_type']),
            project_id=original['project_id'],
            tags=json.loads(original['tags']) if original['tags'] else []
        )

        # Mark original as superseded
        now_ts = self.now_timestamp()
        self.execute("""
            UPDATE memories
            SET superseded_by = ?,
                consolidation_state = 'superseded',
                updated_at = ?
            WHERE id = ?
        """, (new_id, now_ts, memory_id))

        # Increment version number
        try:
            old_version = original['version'] if 'version' in original.keys() else 1
        except (KeyError, TypeError):
            old_version = 1

        self.execute("""
            UPDATE memories SET version = ? WHERE id = ?
        """, (old_version + 1, new_id))

        # Record reconsolidation event
        self.execute("""
            INSERT INTO memory_updates (
                original_id, updated_id, update_reason, confidence, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        """, (memory_id, new_id, update_reason, confidence, now_ts))

        self.commit()

        return new_id

    def mark_memory_labile(self, memory_id: int, window_minutes: int = 5):
        """Mark memory as labile (open for modification) after retrieval.

        Implements reconsolidation window from neuroscience: retrieved memories
        become temporarily unstable and can be modified.

        Args:
            memory_id: Memory ID
            window_minutes: How long memory remains labile (default 5 min)
        """
        now_ts = self.now_timestamp()
        self.execute("""
            UPDATE memories
            SET consolidation_state = 'labile',
                last_retrieved = ?
            WHERE id = ?
        """, (now_ts, memory_id))
        self.commit()

    def is_in_reconsolidation_window(self, memory_id: int, window_minutes: int = 5) -> bool:
        """Check if memory is in reconsolidation window (can be modified).

        Args:
            memory_id: Memory ID
            window_minutes: Duration of window (default 5 min)

        Returns:
            True if memory can be modified
        """
        from datetime import timedelta

        row = self.execute("""
            SELECT last_retrieved, consolidation_state
            FROM memories WHERE id = ?
        """, (memory_id,), fetch_one=True)

        if not row or not row['last_retrieved']:
            return False

        last_retrieved = self.from_timestamp(row['last_retrieved'])
        window_end = last_retrieved + timedelta(minutes=window_minutes)

        is_labile = row['consolidation_state'] == 'labile'
        in_time_window = datetime.now() < window_end

        return is_labile and in_time_window

    def get_memory_history(self, memory_id: int) -> list[dict]:
        """Get full update history for a memory.

        Args:
            memory_id: Memory ID (can be any version)

        Returns:
            List of memory versions (oldest first) with update metadata
        """
        # Follow chain backwards to find root
        history = []
        current_id = memory_id

        while current_id:
            mem = self.execute(
                "SELECT * FROM memories WHERE id = ?",
                (current_id,),
                fetch_one=True
            )

            if not mem:
                break

            # Get update info if this was an update
            update_info = self.execute("""
                SELECT update_reason, confidence, timestamp
                FROM memory_updates
                WHERE updated_id = ?
            """, (current_id,), fetch_one=True)

            # Helper to safely get value from Row
            def safe_get(row, key, default=None):
                try:
                    return row[key] if key in row.keys() else default
                except (KeyError, TypeError):
                    return default

            history.append({
                'id': mem['id'],
                'content': mem['content'],
                'version': safe_get(mem, 'version', 1),
                'created_at': self.from_timestamp(mem['created_at']),
                'consolidation_state': safe_get(mem, 'consolidation_state', 'consolidated'),
                'update_reason': update_info['update_reason'] if update_info else None,
                'update_confidence': update_info['confidence'] if update_info else None,
                'superseded_by': safe_get(mem, 'superseded_by')
            })

            # Check if this supersedes an older version
            previous = self.execute("""
                SELECT original_id FROM memory_updates
                WHERE updated_id = ?
            """, (current_id,), fetch_one=True)

            current_id = previous['original_id'] if previous else None

        # Return oldest first
        return list(reversed(history))

    async def create_task(self, task):
        """Create a new task in the database.

        Args:
            task: ProspectiveTask instance

        Returns:
            Saved task with ID
        """
        return await self.db.create_task(task)

    async def get_connection(self, source_id: int):
        """Get external data source connection.

        Args:
            source_id: Data source ID

        Returns:
            Connection object or None
        """
        # This delegates to database implementation if it exists
        if hasattr(self.db, 'get_external_connection'):
            return await self.db.get_external_connection(source_id)
        return None

    async def create_sync_log(self, sync_log):
        """Create a sync log entry.

        Args:
            sync_log: SyncLog instance

        Returns:
            Created sync log with ID
        """
        if hasattr(self.db, 'create_sync_log'):
            return await self.db.create_sync_log(sync_log)
        return sync_log

    async def get_sync_history(self, source_id: int, limit: int = 5):
        """Get sync history for a source.

        Args:
            source_id: Data source ID
            limit: Maximum number of records

        Returns:
            List of sync logs
        """
        if hasattr(self.db, 'get_sync_history'):
            return await self.db.get_sync_history(source_id, limit)
        return []

    async def create_data_mapping(self, mapping):
        """Create a data mapping entry.

        Args:
            mapping: DataMapping instance

        Returns:
            Created mapping with ID
        """
        if hasattr(self.db, 'create_data_mapping'):
            return await self.db.create_data_mapping(mapping)
        return mapping

    # Sync wrappers for async methods (Phase 2: Executable Procedures)
    def remember_sync(
        self,
        content: str,
        memory_type: MemoryType | str,
        project_id: int,
        tags: Optional[list[str]] = None,
    ) -> int:
        """Synchronous wrapper for remember().

        Store a new memory with embedding in a sync context.

        Args:
            content: Memory content
            memory_type: Type of memory
            project_id: Project ID
            tags: Optional tags

        Returns:
            ID of stored memory
        """
        coro = self.remember(content, memory_type, project_id, tags)
        return run_async(coro)

    def get_project_by_path_sync(self, path: str) -> Optional[Project]:
        """Synchronous wrapper for get_project_by_path().

        Find project by path in a sync context.

        Args:
            path: Directory path

        Returns:
            Project if found, None otherwise
        """
        coro = self.get_project_by_path(path)
        return run_async(coro)

    def close(self):
        """Close database connection."""
        self.db.close()
