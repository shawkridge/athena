"""Qdrant vector database adapter for semantic memory storage.

This module provides a clean interface to Qdrant for storing and retrieving
semantic memories with embeddings. Handles collection management, indexing,
and search operations.
"""

import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)

logger = logging.getLogger(__name__)


@dataclass
class SemanticMemory:
    """Semantic memory record."""
    id: int
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    score: Optional[float] = None


class QdrantAdapter:
    """Adapter for Qdrant vector database operations.

    Provides high-level interface for semantic memory storage and retrieval.
    Handles collection initialization, embedding storage, and similarity search.
    """

    DEFAULT_COLLECTION = "semantic_memories"
    EMBEDDING_DIM = 768  # Default for Ollama nomic-embed-text

    def __init__(
        self,
        url: Optional[str] = None,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_dim: int = EMBEDDING_DIM,
    ):
        """Initialize Qdrant adapter.

        Args:
            url: Qdrant server URL (default: from env QDRANT_URL or localhost)
            collection_name: Name of collection for semantic memories
            embedding_dim: Dimension of embedding vectors
        """
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        # Initialize client
        self.client = QdrantClient(url=self.url)

        # Ensure collection exists
        self._ensure_collection()

        logger.info(f"Initialized QdrantAdapter: {self.url}/{self.collection_name}")

    def _ensure_collection(self):
        """Ensure the collection exists, create if not."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            logger.info(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Collection created: {self.collection_name}")
        else:
            logger.debug(f"Collection exists: {self.collection_name}")

    def add_memory(
        self,
        memory_id: int,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a single semantic memory.

        Args:
            memory_id: Unique memory ID (from SQLite)
            content: Memory content text
            embedding: Embedding vector
            metadata: Additional metadata (tags, importance, etc.)

        Returns:
            True if added successfully
        """
        metadata = metadata or {}
        metadata["content"] = content  # Store content in payload

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=memory_id,
                        vector=embedding,
                        payload=metadata,
                    )
                ],
            )
            logger.debug(f"Added memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add memory {memory_id}: {e}")
            return False

    def add_memories_batch(
        self,
        memories: List[Dict[str, Any]],
    ) -> int:
        """Add multiple memories in batch.

        Args:
            memories: List of dicts with keys: id, content, embedding, metadata

        Returns:
            Number of memories added successfully
        """
        points = []
        for mem in memories:
            metadata = mem.get("metadata", {})
            metadata["content"] = mem["content"]

            points.append(
                PointStruct(
                    id=mem["id"],
                    vector=mem["embedding"],
                    payload=metadata,
                )
            )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            logger.info(f"Added {len(points)} memories in batch")
            return len(points)
        except Exception as e:
            logger.error(f"Batch add failed: {e}")
            return 0

    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SemanticMemory]:
        """Search for similar memories.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filters: Metadata filters (e.g., {"tags": ["python"]})

        Returns:
            List of matching SemanticMemory objects
        """
        # Build filter if provided
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    # Match any value in list
                    for v in value:
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=v))
                        )
                else:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )

            if conditions:
                qdrant_filter = Filter(must=conditions)

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
            )

            memories = []
            for hit in results:
                memories.append(
                    SemanticMemory(
                        id=hit.id,
                        content=hit.payload.get("content", ""),
                        embedding=[],  # Don't return embedding by default
                        metadata={k: v for k, v in hit.payload.items() if k != "content"},
                        score=hit.score,
                    )
                )

            logger.debug(f"Found {len(memories)} memories (threshold={score_threshold})")
            return memories

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[memory_id],
            )
            logger.debug(f"Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    def get_memory(self, memory_id: int) -> Optional[SemanticMemory]:
        """Retrieve a single memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            SemanticMemory if found, None otherwise
        """
        try:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[memory_id],
                with_vectors=False,
            )

            if results:
                hit = results[0]
                return SemanticMemory(
                    id=hit.id,
                    content=hit.payload.get("content", ""),
                    embedding=[],
                    metadata={k: v for k, v in hit.payload.items() if k != "content"},
                )

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    def count(self) -> int:
        """Get total number of memories.

        Returns:
            Count of memories in collection
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            return 0

    def health_check(self) -> bool:
        """Check if Qdrant is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def clear_collection(self) -> bool:
        """Delete all memories from collection (DANGEROUS).

        Returns:
            True if cleared successfully
        """
        try:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()  # Recreate empty
            logger.warning(f"Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
