"""
Enhanced Knowledge Graph Traversal for Memory Retrieval.

Implements multi-hop graph traversal to enrich memory context with
related entities and relationships. Complements vector search with
semantic relationship exploration.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass, field
from collections import deque

from athena.core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class GraphEntity:
    """Entity in knowledge graph."""

    entity_id: int
    name: str
    entity_type: str
    observations: List[str] = field(default_factory=list)
    relevance_score: float = 0.5


@dataclass
class GraphRelation:
    """Relationship between entities."""

    from_entity_id: int
    to_entity_id: int
    relation_type: str
    strength: float = 0.5


@dataclass
class TraversalResult:
    """Result of graph traversal."""

    root_entity: Optional[GraphEntity] = None
    related_entities: List[GraphEntity] = field(default_factory=list)
    relations: List[GraphRelation] = field(default_factory=list)
    context_summary: str = ""
    richness_score: float = 0.0


class GraphTraversal:
    """Multi-hop knowledge graph traversal for enhanced memory context."""

    def __init__(self, db: Database, max_depth: int = 3, max_results: int = 20):
        """Initialize graph traversal.

        Args:
            db: Database connection
            max_depth: Maximum traversal depth (hops)
            max_results: Maximum entities to return
        """
        self.db = db
        self.max_depth = max_depth
        self.max_results = max_results

    async def find_related_context(
        self,
        entity_name: str,
        relation_types: Optional[List[str]] = None,
        depth: int = 2,
    ) -> TraversalResult:
        """Find all related entities and context for given entity.

        Uses breadth-first search to explore graph relationships.

        Args:
            entity_name: Starting entity name
            relation_types: Filter by specific relation types
            depth: Max traversal depth

        Returns:
            TraversalResult with all related entities and relations
        """
        try:
            # Find root entity
            root = self._find_entity(entity_name)
            if not root:
                logger.debug(f"Entity not found: {entity_name}")
                return TraversalResult()

            # BFS traversal
            related = self._bfs_traverse(
                root.entity_id,
                relation_types=relation_types,
                max_depth=min(depth, self.max_depth),
            )

            # Extract relations
            relations = self._extract_relations(root.entity_id, related)

            # Build summary
            summary = self._build_context_summary(root, related, relations)

            # Calculate richness score
            richness = self._calculate_richness(root, related, relations)

            return TraversalResult(
                root_entity=root,
                related_entities=related[: self.max_results],
                relations=relations,
                context_summary=summary,
                richness_score=richness,
            )

        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            return TraversalResult()

    def _find_entity(self, entity_name: str) -> Optional[GraphEntity]:
        """Find entity by name in knowledge graph.

        Args:
            entity_name: Entity name to find

        Returns:
            GraphEntity if found, None otherwise
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT id, name, entity_type FROM graph_entities
                WHERE name LIKE ? OR name = ?
                LIMIT 1
                """,
                (f"%{entity_name}%", entity_name),
            )
            row = cursor.fetchone()

            if not row:
                return None

            entity_id, name, entity_type = row

            # Get observations
            cursor.execute(
                """
                SELECT observation FROM graph_observations
                WHERE entity_id = ?
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (entity_id,),
            )
            observations = [r[0] for r in cursor.fetchall()]

            return GraphEntity(
                entity_id=entity_id,
                name=name,
                entity_type=entity_type,
                observations=observations,
                relevance_score=1.0,  # Root entity has max relevance
            )

        except Exception as e:
            logger.debug(f"Entity lookup failed: {e}")
            return None

    def _bfs_traverse(
        self,
        root_id: int,
        relation_types: Optional[List[str]] = None,
        max_depth: int = 2,
    ) -> List[GraphEntity]:
        """Breadth-first traversal from root entity.

        Args:
            root_id: Starting entity ID
            relation_types: Filter by relation types
            max_depth: Maximum depth

        Returns:
            List of related entities, ordered by relevance
        """
        visited = {root_id}
        queue = deque([(root_id, 0)])  # (entity_id, depth)
        entities_by_depth = {}

        cursor = self.db.get_cursor()

        while queue:
            current_id, depth = queue.popleft()

            if depth > max_depth:
                continue

            # Find related entities
            query = """
                SELECT to_entity_id, relation_type FROM graph_relations
                WHERE from_entity_id = ?
            """
            params = [current_id]

            if relation_types:
                placeholders = ",".join("?" * len(relation_types))
                query += f" AND relation_type IN ({placeholders})"
                params.extend(relation_types)

            cursor.execute(query, params)
            relations = cursor.fetchall()

            for related_id, rel_type in relations:
                if related_id in visited:
                    continue

                visited.add(related_id)

                # Get entity details
                entity = self._get_entity_by_id(related_id)
                if entity:
                    # Boost relevance by inverse of depth (closer = more relevant)
                    entity.relevance_score = 1.0 - (depth * 0.1)

                    if depth not in entities_by_depth:
                        entities_by_depth[depth] = []
                    entities_by_depth[depth].append(entity)

                    # Continue traversal
                    if depth < max_depth:
                        queue.append((related_id, depth + 1))

        # Flatten and sort by relevance
        all_entities = []
        for depth in sorted(entities_by_depth.keys()):
            all_entities.extend(entities_by_depth[depth])

        all_entities.sort(key=lambda e: e.relevance_score, reverse=True)
        return all_entities

    def _get_entity_by_id(self, entity_id: int) -> Optional[GraphEntity]:
        """Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            GraphEntity if found
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT id, name, entity_type FROM graph_entities
                WHERE id = ?
                """,
                (entity_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            ent_id, name, entity_type = row

            # Get observations
            cursor.execute(
                """
                SELECT observation FROM graph_observations
                WHERE entity_id = ?
                ORDER BY created_at DESC
                LIMIT 3
                """,
                (entity_id,),
            )
            observations = [r[0] for r in cursor.fetchall()]

            return GraphEntity(
                entity_id=ent_id,
                name=name,
                entity_type=entity_type,
                observations=observations,
            )

        except Exception as e:
            logger.debug(f"Entity by ID lookup failed: {e}")
            return None

    def _extract_relations(
        self,
        root_id: int,
        related_entities: List[GraphEntity],
    ) -> List[GraphRelation]:
        """Extract relations between root and related entities.

        Args:
            root_id: Root entity ID
            related_entities: List of related entities

        Returns:
            List of GraphRelation objects
        """
        relations = []
        related_ids = {e.entity_id for e in related_entities}

        try:
            cursor = self.db.get_cursor()

            # Get relations from root to related
            for rel_id in related_ids:
                cursor.execute(
                    """
                    SELECT relation_type, strength FROM graph_relations
                    WHERE from_entity_id = ? AND to_entity_id = ?
                    """,
                    (root_id, rel_id),
                )
                row = cursor.fetchone()

                if row:
                    rel_type, strength = row
                    strength = float(strength) if strength else 0.5
                else:
                    rel_type = "related"
                    strength = 0.5

                relations.append(
                    GraphRelation(
                        from_entity_id=root_id,
                        to_entity_id=rel_id,
                        relation_type=rel_type,
                        strength=strength,
                    )
                )

        except Exception as e:
            logger.debug(f"Relation extraction failed: {e}")

        return relations

    def _build_context_summary(
        self,
        root: GraphEntity,
        related: List[GraphEntity],
        relations: List[GraphRelation],
    ) -> str:
        """Build natural language summary of graph context.

        Args:
            root: Root entity
            related: Related entities
            relations: Relations

        Returns:
            Context summary string
        """
        if not root:
            return ""

        lines = [f"📌 {root.name} ({root.entity_type})"]

        if root.observations:
            lines.append("Observations:")
            for obs in root.observations[:2]:
                lines.append(f"  • {obs}")

        if related:
            lines.append(f"\nRelated ({len(related)} entities):")
            for entity in related[:5]:
                rel_type = next(
                    (r.relation_type for r in relations if r.to_entity_id == entity.entity_id),
                    "related to",
                )
                lines.append(f"  • {entity.name} ({rel_type})")

                if entity.observations:
                    lines.append(f"    - {entity.observations[0]}")

        return "\n".join(lines)

    def _calculate_richness(
        self,
        root: Optional[GraphEntity],
        related: List[GraphEntity],
        relations: List[GraphRelation],
    ) -> float:
        """Calculate richness score of traversal result.

        Measures how much context was found (0.0-1.0).

        Args:
            root: Root entity
            related: Related entities
            relations: Relations

        Returns:
            Richness score (0.0-1.0)
        """
        if not root:
            return 0.0

        # Components of richness
        entity_richness = min(1.0, len(related) / 5)  # 5+ entities = max
        relation_richness = min(1.0, len(relations) / 5)  # 5+ relations = max
        depth_richness = 0.5 if len(related) > 0 else 0.0  # Has any depth

        # Weighted average
        richness = 0.4 * entity_richness + 0.4 * relation_richness + 0.2 * depth_richness

        return min(1.0, richness)

    async def find_similar_entities(
        self,
        entity_type: str,
        limit: int = 10,
    ) -> List[GraphEntity]:
        """Find other entities of same type.

        Useful for "show me similar to X" queries.

        Args:
            entity_type: Entity type to find
            limit: Maximum results

        Returns:
            List of similar entities
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT id, name, entity_type FROM graph_entities
                WHERE entity_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (entity_type, limit),
            )
            rows = cursor.fetchall()

            entities = []
            for ent_id, name, ent_type in rows:
                entity = self._get_entity_by_id(ent_id)
                if entity:
                    entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"Similar entity search failed: {e}")
            return []
