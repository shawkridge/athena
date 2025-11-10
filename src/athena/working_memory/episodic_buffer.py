"""
Episodic Buffer: Integration layer between Working Memory and Long-Term Memory.

Purpose:
- Bind information from multiple sources (phonological, visuospatial, LTM)
- Create integrated multimodal representations
- Interface between working memory and episodic/semantic LTM
- Enable chunking of related information

Key Features:
- Multimodal integration (verbal + spatial + episodic context)
- Limited capacity (4±1 chunks - Baddeley 2000)
- Binds temporal and spatial information
- Links to episodic memories for context
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from ..core.database import Database
from ..core.embeddings import EmbeddingModel, cosine_similarity
from .models import WorkingMemoryItem, Component, ContentType
from .utils import serialize_embedding, deserialize_embedding


class EpisodicBuffer:
    """
    Episodic Buffer component of Baddeley's Working Memory model.

    Integrates information from phonological loop, visuospatial sketchpad,
    and long-term episodic memory into coherent multimodal representations.
    """

    def __init__(self, db: Database | str, embedder: EmbeddingModel):
        # Accept either Database instance or path string
        if isinstance(db, str):
            self.db = Database(db)
        else:
            # Already a database object (SQLite or Postgres)
            self.db = db
        self.embedder = embedder
        self.max_capacity = 4  # 4±1 chunks (Baddeley, 2000)
        self.component = Component.EPISODIC_BUFFER

    # ========================================================================
    # Simple Item Operations (Test Interface)
    # ========================================================================

    def add_item(
        self,
        project_id: int,
        content: str,
        sources: Optional[Dict[str, Any]] = None,
        importance: float = 0.7
    ) -> int:
        """
        Add item to episodic buffer with source tracking.

        Args:
            project_id: Project identifier
            content: Item content
            sources: Dict mapping source types to IDs (e.g., {"phonological": 123})
            importance: Importance score (0.0-1.0)

        Returns:
            ID of created item
        """
        # Check capacity
        current_count = self._get_item_count(project_id)
        if current_count >= self.max_capacity:
            self._remove_oldest(project_id)

        # Generate embedding
        embedding = self.embedder.embed(content)
        embedding_bytes = serialize_embedding(embedding)

        # Store sources in metadata
        metadata = {
            'sources': sources or {},
            'created_timestamp': datetime.now().isoformat()
        }

        # Insert
        with self.db.conn:
            cursor = self.db.conn.execute("""
                INSERT INTO working_memory
                (project_id, content, content_type, component,
                 importance_score, embedding, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                content,
                ContentType.EPISODIC.value,
                self.component.value,
                importance,
                embedding_bytes,
                json.dumps(metadata)
            ))

            return cursor.lastrowid

    def get_items(self, project_id: int) -> List[WorkingMemoryItem]:
        """
        Get all items in episodic buffer as WorkingMemoryItem objects.

        Returns:
            List of WorkingMemoryItem objects
        """
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM working_memory
                WHERE project_id = ? AND component = ?
                ORDER BY last_accessed DESC
            """, (project_id, self.component.value)).fetchall()

            items = []
            for row in rows:
                item = self._row_to_item(row)
                items.append(item)

            return items

    def get_item(self, item_id: int) -> Optional[WorkingMemoryItem]:
        """Get single item by ID as WorkingMemoryItem object."""
        with self.db.conn:
            row = self.db.conn.execute("""
                SELECT * FROM working_memory WHERE id = ?
            """, (item_id,)).fetchone()

            if not row or row['component'] != self.component.value:
                return None

            return self._row_to_item(row)

    def get_chunks(self, project_id: int) -> List[WorkingMemoryItem]:
        """
        Get all chunks (items with chunk_size metadata).

        Returns:
            List of WorkingMemoryItem objects that are chunks
        """
        items = self.get_items(project_id)
        chunks = []
        for item in items:
            # Check if metadata has chunk_size
            if item.metadata and 'chunk_size' in item.metadata:
                # Add chunk_size as attribute for test compatibility
                item.chunk_size = item.metadata['chunk_size']
                chunks.append(item)

        return chunks

    def bind_items(
        self,
        project_id: int,
        phonological_id: Optional[int] = None,
        visuospatial_id: Optional[int] = None,
        binding_content: str = ""
    ) -> int:
        """
        Bind phonological and visuospatial items.

        Args:
            project_id: Project identifier
            phonological_id: ID of phonological loop item
            visuospatial_id: ID of visuospatial sketchpad item
            binding_content: Content describing the binding

        Returns:
            ID of created binding item
        """
        sources = {}
        if phonological_id:
            sources['phonological'] = phonological_id
        if visuospatial_id:
            sources['visuospatial'] = visuospatial_id

        return self.add_item(project_id, binding_content, sources=sources)

    def get_items_by_source(self, project_id: int, source_type: str) -> List[WorkingMemoryItem]:
        """
        Get items filtered by source type.

        Args:
            project_id: Project identifier
            source_type: Source type (e.g., "phonological", "visuospatial")

        Returns:
            List of items with that source type
        """
        items = self.get_items(project_id)
        filtered = []

        for item in items:
            if item.metadata and 'sources' in item.metadata:
                sources = item.metadata['sources']
                if source_type in sources:
                    filtered.append(item)

        return filtered

    def search(
        self,
        project_id: int,
        query: str,
        k: int = 5
    ) -> List[WorkingMemoryItem]:
        """
        Semantic search within episodic buffer.

        Args:
            project_id: Project identifier
            query: Search query
            k: Number of results

        Returns:
            Top-k most similar items
        """
        # Generate query embedding
        query_embedding = self.embedder.embed(query)

        # Get all items
        items = self.get_items(project_id)

        # Calculate similarities
        scored_items = []
        for item in items:
            if item.embedding:
                item_embedding = deserialize_embedding(item.embedding)
                similarity = cosine_similarity(query_embedding, item_embedding)

                # Weight by activation
                score = similarity * 0.7 + item.activation_level * 0.3

                scored_items.append((score, item))

        # Sort and return top-k
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored_items[:k]]

    # ========================================================================
    # Integration Operations
    # ========================================================================

    def create_integrated_memory(
        self,
        project_id: int,
        verbal_content: Optional[str] = None,
        verbal_item_ids: Optional[List[int]] = None,
        spatial_content: Optional[str] = None,
        spatial_item_ids: Optional[List[int]] = None,
        episodic_event_id: Optional[int] = None,
        description: Optional[str] = None,
        importance: float = 0.8
    ) -> int:
        """
        Create integrated memory binding multiple sources.

        Args:
            project_id: Project identifier
            verbal_content: Verbal/linguistic content
            verbal_item_ids: IDs of phonological loop items to integrate
            spatial_content: Spatial/visual content
            spatial_item_ids: IDs of visuospatial items to integrate
            episodic_event_id: ID of episodic memory event for context
            description: High-level description of integration
            importance: Importance score (default 0.8 - integrations are important)

        Returns:
            ID of created integrated memory
        """
        # Check capacity
        current_count = self._get_item_count(project_id)
        if current_count >= self.max_capacity:
            self._remove_oldest(project_id)

        # Fetch referenced items
        verbal_items = []
        if verbal_item_ids:
            verbal_items = self._get_items_by_ids(verbal_item_ids)

        spatial_items = []
        if spatial_item_ids:
            spatial_items = self._get_items_by_ids(spatial_item_ids)

        # Build integrated content
        content_parts = []

        if description:
            content_parts.append(f"Integration: {description}")

        if verbal_content:
            content_parts.append(f"Verbal: {verbal_content}")

        if verbal_items:
            verbal_text = " | ".join([item['content'] for item in verbal_items])
            content_parts.append(f"From Phonological Loop: {verbal_text}")

        if spatial_content:
            content_parts.append(f"Spatial: {spatial_content}")

        if spatial_items:
            spatial_text = " | ".join([item['content'] for item in spatial_items])
            content_parts.append(f"From Visuospatial Sketchpad: {spatial_text}")

        if episodic_event_id:
            content_parts.append(f"Episodic Context: Event #{episodic_event_id}")

        integrated_content = "\n".join(content_parts)

        # Create metadata
        metadata = {
            'verbal_content': verbal_content,
            'verbal_item_ids': verbal_item_ids or [],
            'spatial_content': spatial_content,
            'spatial_item_ids': spatial_item_ids or [],
            'episodic_event_id': episodic_event_id,
            'description': description,
            'integration_type': self._infer_integration_type(
                verbal_content, spatial_content, episodic_event_id
            ),
            'created_timestamp': datetime.now().isoformat()
        }

        # Insert
        with self.db.conn:
            cursor = self.db.conn.execute("""
                INSERT INTO working_memory
                (project_id, content, content_type, component,
                 importance_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                integrated_content,
                ContentType.EPISODIC.value,
                self.component.value,
                importance,
                json.dumps(metadata)
            ))

            return cursor.lastrowid

    def create_chunk(
        self,
        project_id: int,
        items: List[str],
        importance: float = 0.7
    ) -> int:
        """
        Create chunk from list of related items (strings).

        Chunking allows multiple related items to be treated as single unit,
        effectively increasing capacity. Enforces 4±1 capacity limit.

        Args:
            project_id: Project identifier
            items: List of item strings to chunk together (max 5)
            importance: Importance score

        Returns:
            ID of created chunk
        """
        # Enforce 4±1 capacity (max 5 items per chunk)
        chunk_items = items[:5]

        # Build chunk content
        chunk_content = " | ".join(chunk_items)

        # Generate embedding
        embedding = self.embedder.embed(chunk_content)
        embedding_bytes = serialize_embedding(embedding)

        # Store chunk_size in metadata
        metadata = {
            'chunk_size': len(chunk_items),
            'chunk_items': chunk_items,
            'created_timestamp': datetime.now().isoformat()
        }

        # Insert
        with self.db.conn:
            cursor = self.db.conn.execute("""
                INSERT INTO working_memory
                (project_id, content, content_type, component,
                 importance_score, embedding, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                chunk_content,
                ContentType.EPISODIC.value,
                self.component.value,
                importance,
                embedding_bytes,
                json.dumps(metadata)
            ))

            return cursor.lastrowid

    # ========================================================================
    # Retrieval and Access
    # ========================================================================

    def get_integrated_memories(
        self,
        project_id: int
    ) -> List[Dict]:
        """
        Get all integrated memories in buffer.

        Returns:
            List of integrated memory dicts with metadata
        """
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM working_memory
                WHERE project_id = ? AND component = ?
                ORDER BY last_accessed DESC
            """, (project_id, self.component.value)).fetchall()

            memories = []
            for row in rows:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                memories.append({
                    'id': row['id'],
                    'content': row['content'],
                    'description': metadata.get('description'),
                    'integration_type': metadata.get('integration_type'),
                    'verbal_item_ids': metadata.get('verbal_item_ids', []),
                    'spatial_item_ids': metadata.get('spatial_item_ids', []),
                    'episodic_event_id': metadata.get('episodic_event_id'),
                    'importance': row['importance_score'],
                    'created_at': row['created_at'],
                    'last_accessed': row['last_accessed']
                })

            return memories

    def get_memory(self, memory_id: int) -> Optional[Dict]:
        """Get single integrated memory by ID."""
        with self.db.conn:
            row = self.db.conn.execute("""
                SELECT * FROM working_memory WHERE id = ?
            """, (memory_id,)).fetchone()

            if not row or row['component'] != self.component.value:
                return None

            metadata = json.loads(row['metadata']) if row['metadata'] else {}

            return {
                'id': row['id'],
                'content': row['content'],
                'description': metadata.get('description'),
                'integration_type': metadata.get('integration_type'),
                'verbal_item_ids': metadata.get('verbal_item_ids', []),
                'spatial_item_ids': metadata.get('spatial_item_ids', []),
                'episodic_event_id': metadata.get('episodic_event_id'),
                'importance': row['importance_score'],
                'activation': row['activation_level'],
                'metadata': metadata
            }

    def find_by_episodic_event(
        self,
        project_id: int,
        event_id: int
    ) -> List[Dict]:
        """Find integrated memories linked to specific episodic event."""
        memories = self.get_integrated_memories(project_id)
        return [m for m in memories if m['episodic_event_id'] == event_id]

    def find_by_integration_type(
        self,
        project_id: int,
        integration_type: str
    ) -> List[Dict]:
        """Find integrated memories by type."""
        memories = self.get_integrated_memories(project_id)
        return [m for m in memories if m['integration_type'] == integration_type]

    # ========================================================================
    # Source Item Retrieval
    # ========================================================================

    def get_source_items(self, memory_id: int) -> Dict:
        """
        Get all source items that contributed to integration.

        Returns:
            Dict with verbal_items, spatial_items, and episodic_context
        """
        memory = self.get_memory(memory_id)
        if not memory:
            return {'verbal_items': [], 'spatial_items': [], 'episodic_context': None}

        verbal_ids = memory['verbal_item_ids']
        spatial_ids = memory['spatial_item_ids']
        episodic_id = memory['episodic_event_id']

        verbal_items = self._get_items_by_ids(verbal_ids) if verbal_ids else []
        spatial_items = self._get_items_by_ids(spatial_ids) if spatial_ids else []

        episodic_context = None
        if episodic_id:
            # Fetch from episodic_events table
            with self.db.conn:
                row = self.db.conn.execute("""
                    SELECT * FROM episodic_events WHERE id = ?
                """, (episodic_id,)).fetchone()

                if row:
                    episodic_context = dict(row)

        return {
            'verbal_items': verbal_items,
            'spatial_items': spatial_items,
            'episodic_context': episodic_context
        }

    def expand_integration(self, memory_id: int) -> Dict:
        """
        Fully expand integrated memory showing all sources.

        Useful for understanding what was integrated.
        """
        memory = self.get_memory(memory_id)
        if not memory:
            return {}

        sources = self.get_source_items(memory_id)

        return {
            'integration': memory,
            'sources': sources,
            'expansion': {
                'verbal_count': len(sources['verbal_items']),
                'spatial_count': len(sources['spatial_items']),
                'has_episodic_context': sources['episodic_context'] is not None
            }
        }

    # ========================================================================
    # Capacity Management
    # ========================================================================

    def clear(self, project_id: int):
        """Clear all integrated memories."""
        with self.db.conn:
            self.db.conn.execute("""
                DELETE FROM working_memory
                WHERE project_id = ? AND component = ?
            """, (project_id, self.component.value))

    def _get_item_count(self, project_id: int) -> int:
        """Get current item count."""
        with self.db.conn:
            result = self.db.conn.execute("""
                SELECT COUNT(*) as count FROM working_memory
                WHERE project_id = ? AND component = ?
            """, (project_id, self.component.value)).fetchone()

            return result['count']

    def _remove_oldest(self, project_id: int, count: int = 1):
        """Remove oldest items to make space."""
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT id FROM working_memory
                WHERE project_id = ? AND component = ?
                ORDER BY last_accessed ASC
                LIMIT ?
            """, (project_id, self.component.value, count)).fetchall()

            for row in rows:
                self.db.conn.execute("""
                    DELETE FROM working_memory WHERE id = ?
                """, (row['id'],))

    def get_capacity_status(self, project_id: int) -> Dict:
        """Get capacity status."""
        count = self._get_item_count(project_id)

        if count >= self.max_capacity:
            status = 'full'
        elif count >= self.max_capacity - 1:
            status = 'near_full'
        else:
            status = 'available'

        return {
            'count': count,
            'max_capacity': self.max_capacity,
            'available_slots': self.max_capacity - count,
            'status': status
        }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_items_by_ids(self, item_ids: List[int]) -> List[Dict]:
        """Fetch multiple working memory items by IDs."""
        if not item_ids:
            return []

        with self.db.conn:
            placeholders = ','.join('?' * len(item_ids))
            query = f"""
                SELECT * FROM working_memory
                WHERE id IN ({placeholders})
            """
            rows = self.db.conn.execute(query, item_ids).fetchall()

            return [dict(row) for row in rows]

    def _infer_integration_type(
        self,
        verbal_content: Optional[str],
        spatial_content: Optional[str],
        episodic_event_id: Optional[int]
    ) -> str:
        """Infer type of integration based on sources."""
        has_verbal = verbal_content is not None
        has_spatial = spatial_content is not None
        has_episodic = episodic_event_id is not None

        if has_verbal and has_spatial and has_episodic:
            return 'multimodal_with_context'
        elif has_verbal and has_spatial:
            return 'multimodal'
        elif has_verbal and has_episodic:
            return 'verbal_with_context'
        elif has_spatial and has_episodic:
            return 'spatial_with_context'
        elif has_episodic:
            return 'episodic_binding'
        elif has_verbal:
            return 'verbal_only'
        elif has_spatial:
            return 'spatial_only'
        else:
            return 'unknown'

    def get_statistics(self, project_id: int) -> Dict:
        """Get episodic buffer statistics."""
        memories = self.get_integrated_memories(project_id)

        if not memories:
            return {
                'count': 0,
                'capacity_used': 0.0,
                'integration_types': {}
            }

        # Count integration types
        type_counts = {}
        for memory in memories:
            int_type = memory['integration_type']
            type_counts[int_type] = type_counts.get(int_type, 0) + 1

        # Count source references
        total_verbal_refs = sum(len(m['verbal_item_ids']) for m in memories)
        total_spatial_refs = sum(len(m['spatial_item_ids']) for m in memories)
        episodic_refs = sum(1 for m in memories if m['episodic_event_id'])

        return {
            'count': len(memories),
            'max_capacity': self.max_capacity,
            'capacity_used': len(memories) / self.max_capacity,
            'integration_types': type_counts,
            'source_references': {
                'verbal': total_verbal_refs,
                'spatial': total_spatial_refs,
                'episodic': episodic_refs
            },
            'avg_sources_per_integration': (
                total_verbal_refs + total_spatial_refs + episodic_refs
            ) / len(memories) if memories else 0
        }

    def _row_to_item(self, row) -> WorkingMemoryItem:
        """Convert database row to WorkingMemoryItem."""
        item = WorkingMemoryItem.from_db_row(row)

        # Add sources as attribute for test compatibility
        if item.metadata and 'sources' in item.metadata:
            item.sources = item.metadata['sources']
            item.source_items = item.metadata['sources']

        return item


