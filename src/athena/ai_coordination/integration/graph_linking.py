"""Graph linking for AI Coordination to Memory-MCP integration.

Links entities (files, functions, patterns) and their relationships
(depends_on, modifies, tests) across AI Coordination and Memory-MCP layers,
enabling entity-aware knowledge graphs.

This is part of Phase 7.2 - enables Memory-MCP to build and navigate
entity relationship graphs from AI Coordination data.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database


class EntityType(str, Enum):
    """Types of entities in the graph."""

    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    PATTERN = "pattern"
    PROCEDURE = "procedure"
    GOAL = "goal"
    TASK = "task"


class RelationType(str, Enum):
    """Types of relationships between entities."""

    DEPENDS_ON = "depends_on"
    MODIFIES = "modifies"
    TESTS = "tests"
    IMPLEMENTS = "implements"
    USES = "uses"
    EXTENDS = "extends"
    REPLACES = "replaces"
    IMPORTS = "imports"
    CALLS = "calls"
    REFERENCES = "references"


class GraphLinker:
    """Links entities and relationships in a knowledge graph.

    Purpose:
    - Create entity definitions from AI Coordination data
    - Link entities with typed relationships
    - Track relationship metadata and strength
    - Enable entity-aware memory queries
    - Support graph traversal and analysis

    This enables queries like:
    - "What files does this function depend on?"
    - "What uses this module?"
    - "What procedures implement this pattern?"
    """

    def __init__(self, db: "Database"):
        """Initialize GraphLinker.

        Args:
            db: Database connection
        """
        self.db = db

    def _ensure_schema(self):
        """Create graph entity tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Table: Graph entity refs (extended version with more details)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_entity_nodes (
                id INTEGER PRIMARY KEY,
                entity_name TEXT NOT NULL,
                entity_type TEXT NOT NULL,  -- file, function, class, module, pattern, etc
                source_layer TEXT NOT NULL, -- coordination, episodic, semantic
                source_id INTEGER,
                file_path TEXT,
                description TEXT,
                metadata TEXT,  -- JSON with entity-specific details
                created_at INTEGER NOT NULL,
                last_updated INTEGER
            )
        """
        )

        # Table: Entity relationships
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_entity_relationships (
                id INTEGER PRIMARY KEY,
                from_entity_id INTEGER NOT NULL,
                to_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,  -- depends_on, modifies, tests, etc
                strength REAL DEFAULT 1.0,    -- 0.0-1.0 relationship strength
                context TEXT,                 -- how/where relationship occurs
                metadata TEXT,                -- JSON with additional context
                created_at INTEGER NOT NULL,
                FOREIGN KEY (from_entity_id) REFERENCES graph_entity_nodes(id),
                FOREIGN KEY (to_entity_id) REFERENCES graph_entity_nodes(id)
            )
        """
        )

        # Indexes for performance
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_graph_entity_name
            ON graph_entity_nodes(entity_name, entity_type)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_graph_entity_source
            ON graph_entity_nodes(source_layer, source_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_graph_relationships_from
            ON graph_entity_relationships(from_entity_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_graph_relationships_to
            ON graph_entity_relationships(to_entity_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_graph_relationships_type
            ON graph_entity_relationships(relation_type)
        """
        )

        # commit handled by cursor context

    def create_entity(
        self,
        entity_name: str,
        entity_type: EntityType,
        source_layer: str,
        source_id: Optional[int] = None,
        file_path: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Create or get entity node.

        Args:
            entity_name: Name of entity
            entity_type: Type of entity (file, function, class, etc)
            source_layer: Layer it comes from (coordination, episodic, etc)
            source_id: ID in source system
            file_path: Optional file path
            description: Optional description
            metadata: Optional metadata dict

        Returns:
            Entity ID
        """
        cursor = self.db.get_cursor()

        # Check if entity already exists
        cursor.execute(
            """
            SELECT id FROM graph_entity_nodes
            WHERE entity_name = ? AND entity_type = ?
            LIMIT 1
        """,
            (entity_name, entity_type.value),
        )

        row = cursor.fetchone()
        if row:
            return row[0]

        # Create new entity
        now = int(datetime.now().timestamp() * 1000)
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """
            INSERT INTO graph_entity_nodes
            (entity_name, entity_type, source_layer, source_id, file_path,
             description, metadata, created_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                entity_name,
                entity_type.value,
                source_layer,
                source_id,
                file_path,
                description,
                metadata_json,
                now,
                now,
            ),
        )

        entity_id = cursor.lastrowid
        # commit handled by cursor context
        return entity_id

    def link_entities(
        self,
        from_entity_id: int,
        to_entity_id: int,
        relation_type: RelationType,
        strength: float = 1.0,
        context: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Create relationship between entities.

        Args:
            from_entity_id: Source entity ID
            to_entity_id: Target entity ID
            relation_type: Type of relationship
            strength: Relationship strength (0.0-1.0)
            context: Optional context string
            metadata: Optional metadata dict

        Returns:
            Relationship ID
        """
        # Ensure strength is in valid range
        strength = max(0.0, min(1.0, strength))

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """
            INSERT INTO graph_entity_relationships
            (from_entity_id, to_entity_id, relation_type, strength,
             context, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                from_entity_id,
                to_entity_id,
                relation_type.value,
                strength,
                context,
                metadata_json,
                now,
            ),
        )

        rel_id = cursor.lastrowid
        # commit handled by cursor context
        return rel_id

    def get_entity(self, entity_name: str, entity_type: EntityType) -> Optional[dict]:
        """Get entity by name and type.

        Args:
            entity_name: Entity name
            entity_type: Entity type

        Returns:
            Entity dict or None
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT id, entity_name, entity_type, source_layer, source_id,
                   file_path, description, metadata
            FROM graph_entity_nodes
            WHERE entity_name = ? AND entity_type = ?
            LIMIT 1
        """,
            (entity_name, entity_type.value),
        )

        row = cursor.fetchone()
        if not row:
            return None

        try:
            metadata = json.loads(row[7]) if row[7] else {}
        except json.JSONDecodeError:
            metadata = {}

        return {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "source_layer": row[3],
            "source_id": row[4],
            "file_path": row[5],
            "description": row[6],
            "metadata": metadata,
        }

    def get_relationships(
        self,
        entity_id: int,
        relation_type: Optional[RelationType] = None,
        direction: str = "both",  # both, outgoing, incoming
    ) -> list[dict]:
        """Get relationships for an entity.

        Args:
            entity_id: Entity ID
            relation_type: Optional filter by relationship type
            direction: Direction of relationships (both, outgoing, incoming)

        Returns:
            List of relationship dicts
        """
        cursor = self.db.get_cursor()
        relationships = []

        if direction in ("outgoing", "both"):
            query = """
                SELECT ger.id, ger.from_entity_id, ger.to_entity_id,
                       ger.relation_type, ger.strength, ger.context,
                       gen.entity_name, gen.entity_type
                FROM graph_entity_relationships ger
                JOIN graph_entity_nodes gen ON ger.to_entity_id = gen.id
                WHERE ger.from_entity_id = ?
            """
            params = [entity_id]

            if relation_type:
                query += " AND ger.relation_type = ?"
                params.append(relation_type.value)

            cursor.execute(query, params)

            for row in cursor.fetchall():
                relationships.append(
                    {
                        "id": row[0],
                        "direction": "outgoing",
                        "relation_type": row[3],
                        "strength": row[4],
                        "context": row[5],
                        "target_entity": {
                            "id": row[2],
                            "name": row[6],
                            "type": row[7],
                        },
                    }
                )

        if direction in ("incoming", "both"):
            query = """
                SELECT ger.id, ger.from_entity_id, ger.to_entity_id,
                       ger.relation_type, ger.strength, ger.context,
                       gen.entity_name, gen.entity_type
                FROM graph_entity_relationships ger
                JOIN graph_entity_nodes gen ON ger.from_entity_id = gen.id
                WHERE ger.to_entity_id = ?
            """
            params = [entity_id]

            if relation_type:
                query += " AND ger.relation_type = ?"
                params.append(relation_type.value)

            cursor.execute(query, params)

            for row in cursor.fetchall():
                relationships.append(
                    {
                        "id": row[0],
                        "direction": "incoming",
                        "relation_type": row[3],
                        "strength": row[4],
                        "context": row[5],
                        "source_entity": {
                            "id": row[1],
                            "name": row[6],
                            "type": row[7],
                        },
                    }
                )

        return relationships

    def traverse_graph(
        self,
        start_entity_id: int,
        max_depth: int = 3,
        relation_types: Optional[list[RelationType]] = None,
    ) -> dict:
        """Traverse graph from starting entity.

        Args:
            start_entity_id: Starting entity ID
            max_depth: Maximum traversal depth
            relation_types: Optional filter to specific relationship types

        Returns:
            Graph structure dict
        """
        visited = set()
        graph = {"nodes": {}, "edges": []}

        def traverse(entity_id: int, depth: int):
            if depth > max_depth or entity_id in visited:
                return

            visited.add(entity_id)

            # Get entity details
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT entity_name, entity_type, description
                FROM graph_entity_nodes
                WHERE id = ?
            """,
                (entity_id,),
            )

            row = cursor.fetchone()
            if row:
                graph["nodes"][entity_id] = {
                    "id": entity_id,
                    "name": row[0],
                    "type": row[1],
                    "description": row[2],
                    "depth": depth,
                }

            # Get relationships
            relationships = self.get_relationships(entity_id)
            for rel in relationships:
                if relation_types and rel["relation_type"] not in [
                    rt.value for rt in relation_types
                ]:
                    continue

                edge_data = {
                    "from": entity_id,
                    "type": rel["relation_type"],
                    "strength": rel["strength"],
                }

                if "target_entity" in rel:
                    edge_data["to"] = rel["target_entity"]["id"]
                    graph["edges"].append(edge_data)
                    traverse(rel["target_entity"]["id"], depth + 1)
                elif "source_entity" in rel:
                    edge_data["to"] = rel["source_entity"]["id"]
                    graph["edges"].append(edge_data)
                    traverse(rel["source_entity"]["id"], depth + 1)

        traverse(start_entity_id, 0)
        return graph

    def find_paths(
        self, from_entity_id: int, to_entity_id: int, max_depth: int = 5
    ) -> list[list[int]]:
        """Find paths between two entities.

        Args:
            from_entity_id: Source entity ID
            to_entity_id: Target entity ID
            max_depth: Maximum path length

        Returns:
            List of paths (each path is list of entity IDs)
        """
        paths = []

        def dfs(current_id: int, target_id: int, path: list[int], visited: set):
            if len(path) > max_depth:
                return

            if current_id == target_id:
                paths.append(path)
                return

            visited.add(current_id)

            for rel in self.get_relationships(current_id):
                if "target_entity" in rel:
                    next_id = rel["target_entity"]["id"]
                    if next_id not in visited:
                        dfs(next_id, target_id, path + [next_id], visited.copy())

        dfs(from_entity_id, to_entity_id, [from_entity_id], set())
        return paths

    def get_entity_stats(self, entity_id: int) -> dict:
        """Get statistics about an entity's relationships.

        Args:
            entity_id: Entity ID

        Returns:
            Stats dict
        """
        cursor = self.db.get_cursor()

        # Get entity details
        cursor.execute(
            """
            SELECT entity_name, entity_type, source_layer
            FROM graph_entity_nodes
            WHERE id = ?
        """,
            (entity_id,),
        )

        row = cursor.fetchone()
        if not row:
            return {}

        # Count outgoing relationships by type
        cursor.execute(
            """
            SELECT relation_type, COUNT(*), AVG(strength)
            FROM graph_entity_relationships
            WHERE from_entity_id = ?
            GROUP BY relation_type
        """,
            (entity_id,),
        )

        outgoing = {row[0]: {"count": row[1], "avg_strength": row[2]} for row in cursor.fetchall()}

        # Count incoming relationships by type
        cursor.execute(
            """
            SELECT relation_type, COUNT(*), AVG(strength)
            FROM graph_entity_relationships
            WHERE to_entity_id = ?
            GROUP BY relation_type
        """,
            (entity_id,),
        )

        incoming = {row[0]: {"count": row[1], "avg_strength": row[2]} for row in cursor.fetchall()}

        return {
            "entity_id": entity_id,
            "name": row[0],
            "type": row[1],
            "source_layer": row[2],
            "outgoing_relationships": outgoing,
            "incoming_relationships": incoming,
            "total_outgoing": sum(r["count"] for r in outgoing.values()),
            "total_incoming": sum(r["count"] for r in incoming.values()),
        }
