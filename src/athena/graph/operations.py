"""Knowledge Graph Operations - Direct Python API

This module provides clean async functions for knowledge graph operations.
The knowledge graph stores entities, relationships, and inferred knowledge.

Functions can be imported and called directly by agents:
  from athena.graph.operations import add_entity, find_related
  entity_id = await add_entity("concept_name", entity_type="concept")
  related = await find_related("concept_name", limit=10)

No MCP protocol, no wrapper overhead. Just Python async functions.
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.database import Database
from .store import GraphStore
from .models import Entity, Relationship

logger = logging.getLogger(__name__)


class GraphOperations:
    """Encapsulates all knowledge graph operations.

    This class is instantiated with a database and graph store,
    providing all operations as methods.
    """

    def __init__(self, db: Database, store: GraphStore):
        """Initialize with database and graph store.

        Args:
            db: Database instance
            store: GraphStore instance
        """
        self.db = db
        self.store = store
        self.logger = logger

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        description: str = "",
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        """Add an entity to the knowledge graph.

        Args:
            name: Entity name
            entity_type: Type of entity (concept, person, place, thing, etc.)
            description: Optional description
            metadata: Optional metadata dictionary

        Returns:
            Entity ID
        """
        if not name or not entity_type:
            raise ValueError("name and entity_type are required")

        entity = Entity(
            name=name,
            entity_type=entity_type,
            description=description,
            metadata=metadata or {},
            importance=0.5,
        )

        return await self.store.add_entity(entity)

    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 0.5,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        """Add a relationship between entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            strength: Relationship strength (0.0-1.0)
            metadata: Optional metadata

        Returns:
            Relationship ID
        """
        if not source_id or not target_id or not relationship_type:
            raise ValueError("source_id, target_id, and relationship_type are required")

        strength = max(0.0, min(1.0, strength))

        relationship = Relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            strength=strength,
            metadata=metadata or {},
        )

        return await self.store.add_relationship(relationship)

    async def find_entity(self, entity_id: str) -> Optional[Entity]:
        """Find an entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity object or None if not found
        """
        return await self.store.get_entity(entity_id)

    async def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 10,
    ) -> List[Entity]:
        """Search entities by name or description.

        Args:
            query: Search query
            entity_type: Optional entity type filter
            limit: Maximum results

        Returns:
            Matching entities
        """
        if not query:
            return []

        return await self.store.search_entities(query, entity_type=entity_type, limit=limit)

    async def find_related(
        self,
        entity_id: str,
        relationship_type: str | None = None,
        limit: int = 10,
        depth: int = 1,
    ) -> List[Entity]:
        """Find entities related to a given entity.

        Args:
            entity_id: Source entity ID
            relationship_type: Optional filter by relationship type
            limit: Maximum results
            depth: Search depth (1 = direct only, 2 = 2 hops, etc.)

        Returns:
            Related entities
        """
        return await self.store.find_related(
            entity_id=entity_id,
            relationship_type=relationship_type,
            limit=limit,
            depth=depth,
        )

    async def get_communities(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get detected entity communities (clusters).

        Args:
            limit: Maximum communities to return

        Returns:
            List of community summaries
        """
        return await self.store.get_communities(limit=limit)

    async def update_entity_importance(
        self,
        entity_id: str,
        importance: float,
    ) -> bool:
        """Update entity importance score.

        Args:
            entity_id: Entity ID
            importance: New importance (0.0-1.0)

        Returns:
            True if updated successfully
        """
        entity = await self.store.get_entity(entity_id)
        if not entity:
            return False

        entity.importance = max(0.0, min(1.0, importance))
        await self.store.update_entity(entity)
        return True

    async def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics.

        Returns:
            Dictionary with graph statistics
        """
        entities = await self.store.list_entities(limit=10000)
        relationships = await self.store.list_relationships(limit=10000)

        entity_types = {}
        for entity in entities:
            entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1

        relationship_types = {}
        for rel in relationships:
            relationship_types[rel.relationship_type] = (
                relationship_types.get(rel.relationship_type, 0) + 1
            )

        return {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "entity_types": entity_types,
            "relationship_types": relationship_types,
            "avg_importance": sum(e.importance for e in entities) / len(entities)
            if entities
            else 0.0,
        }


# Global singleton instance (lazy-initialized by manager)
_operations: GraphOperations | None = None


def initialize(db: Database, store: GraphStore) -> None:
    """Initialize the global graph operations instance.

    Called by UnifiedMemoryManager during setup.

    Args:
        db: Database instance
        store: GraphStore instance
    """
    global _operations
    _operations = GraphOperations(db, store)


def get_operations() -> GraphOperations:
    """Get the global graph operations instance.

    Returns:
        GraphOperations instance

    Raises:
        RuntimeError: If not initialized
    """
    if _operations is None:
        raise RuntimeError("Graph operations not initialized. Call initialize(db, store) first.")
    return _operations


# Convenience functions that delegate to global instance
async def add_entity(
    name: str,
    entity_type: str,
    description: str = "",
    metadata: Dict[str, Any] | None = None,
) -> str:
    """Add entity. See GraphOperations.add_entity for details."""
    ops = get_operations()
    return await ops.add_entity(name=name, entity_type=entity_type, description=description, metadata=metadata)


async def add_relationship(
    source_id: str,
    target_id: str,
    relationship_type: str,
    strength: float = 0.5,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """Add relationship. See GraphOperations.add_relationship for details."""
    ops = get_operations()
    return await ops.add_relationship(
        source_id=source_id,
        target_id=target_id,
        relationship_type=relationship_type,
        strength=strength,
        metadata=metadata,
    )


async def find_entity(entity_id: str) -> Optional[Entity]:
    """Find entity. See GraphOperations.find_entity for details."""
    ops = get_operations()
    return await ops.find_entity(entity_id)


async def search_entities(
    query: str,
    entity_type: str | None = None,
    limit: int = 10,
) -> List[Entity]:
    """Search entities. See GraphOperations.search_entities for details."""
    ops = get_operations()
    return await ops.search_entities(query=query, entity_type=entity_type, limit=limit)


async def find_related(
    entity_id: str,
    relationship_type: str | None = None,
    limit: int = 10,
    depth: int = 1,
) -> List[Entity]:
    """Find related entities. See GraphOperations.find_related for details."""
    ops = get_operations()
    return await ops.find_related(
        entity_id=entity_id, relationship_type=relationship_type, limit=limit, depth=depth
    )


async def get_communities(limit: int = 10) -> List[Dict[str, Any]]:
    """Get communities. See GraphOperations.get_communities for details."""
    ops = get_operations()
    return await ops.get_communities(limit=limit)


async def update_entity_importance(entity_id: str, importance: float) -> bool:
    """Update entity importance. See GraphOperations.update_entity_importance for details."""
    ops = get_operations()
    return await ops.update_entity_importance(entity_id=entity_id, importance=importance)


async def get_statistics() -> Dict[str, Any]:
    """Get graph statistics. See GraphOperations.get_statistics for details."""
    ops = get_operations()
    return await ops.get_statistics()
