"""Knowledge graph storage and query operations."""

from datetime import datetime
from typing import Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import Entity, EntityType, Observation, Relation, RelationType


class GraphStore(BaseStore[Entity]):
    """Manages knowledge graph storage and queries."""

    table_name = "entities"
    model_class = Entity

    def __init__(self, db: Database):
        """Initialize graph store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        # Schema is initialized centrally in database.py

    def _row_to_model(self, row: Dict[str, Any]) -> Entity:
        """Convert database row to Entity model.

        Args:
            row: Database row as dict

        Returns:
            Entity instance
        """
        return Entity(
            id=row.get("id"),
            name=row.get("name"),
            entity_type=EntityType(row.get("entity_type")) if row.get("entity_type") else None,
            project_id=row.get("project_id"),
            created_at=self.from_timestamp(row.get("created_at")),
            updated_at=self.from_timestamp(row.get("updated_at")),
            metadata=self.deserialize_json(row.get("metadata"), {}) if row.get("metadata") else {},
        )

    def _ensure_schema(self):
        """Ensure knowledge graph tables exist."""

        # For PostgreSQL async databases, skip sync schema initialization
        if not hasattr(self.db, "conn"):
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(
                f"{self.__class__.__name__}: PostgreSQL async database detected. Schema management handled by _init_schema()."
            )
            return
        cursor = self.db.get_cursor()

        # Entities table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                project_id INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                metadata TEXT,
                UNIQUE(name, entity_type, project_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """
        )

        # Relations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_relations (
                id SERIAL PRIMARY KEY,
                from_entity_id INTEGER NOT NULL,
                to_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                confidence REAL DEFAULT 1.0,
                created_at INTEGER NOT NULL,
                valid_from INTEGER,
                valid_until INTEGER,
                metadata TEXT,
                FOREIGN KEY (from_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (to_entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """
        )

        # Observations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_observations (
                id SERIAL PRIMARY KEY,
                entity_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                observation_type TEXT,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'user',
                timestamp INTEGER NOT NULL,
                superseded_by INTEGER,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (superseded_by) REFERENCES entity_observations(id) ON DELETE SET NULL
            )
        """
        )

        # Communities table (for Leiden clustering results)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS communities (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                entity_ids TEXT NOT NULL,
                level INTEGER DEFAULT 0,
                density REAL DEFAULT 0.0,
                internal_edges INTEGER DEFAULT 0,
                external_edges INTEGER DEFAULT 0,
                summary TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """
        )

        # Indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relations_from ON entity_relations(from_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relations_to ON entity_relations(to_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relations_type ON entity_relations(relation_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_observations_entity ON entity_observations(entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_communities_project ON communities(project_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_communities_level ON communities(level)")

        # commit handled by cursor context

    def create_entity(self, entity: Entity) -> int:
        """Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            ID of created entity
        """
        entity_type_str = (
            entity.entity_type.value
            if isinstance(entity.entity_type, EntityType)
            else entity.entity_type
        )

        try:
            result = self.execute(
                """
                INSERT INTO entities (name, entity_type, project_id, created_at, updated_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    entity.name,
                    entity_type_str,
                    entity.project_id,
                    int(entity.created_at.timestamp()),
                    int(entity.updated_at.timestamp()),
                    self.serialize_json(entity.metadata),
                ),
                fetch_one=True,
            )
            self.commit()
            return result[0] if result else None
        except (OSError, ValueError, TypeError):
            # Entity already exists, return its ID
            row = self.execute(
                """
                SELECT id FROM entities
                WHERE name = %s AND entity_type = %s AND project_id IS %s
            """,
                (entity.name, entity_type_str, entity.project_id),
                fetch_one=True,
            )
            return row[0] if row else None

    def create_entities(self, entities: list[Entity]) -> list[int]:
        """Create multiple entities.

        Args:
            entities: List of entities to create

        Returns:
            List of created entity IDs
        """
        return [self.create_entity(entity) for entity in entities]

    def get_entity(self, entity_id: int) -> Optional[Entity]:
        """Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        row = self.execute("SELECT * FROM entities WHERE id = %s", (entity_id,), fetch_one=True)

        if not row:
            return None

        col_names = [
            "id",
            "name",
            "entity_type",
            "project_id",
            "created_at",
            "updated_at",
            "metadata",
        ]
        return self._row_to_model(dict(zip(col_names, row)))

    def find_entity(
        self, name: str, entity_type: str, project_id: Optional[int] = None
    ) -> Optional[Entity]:
        """Find entity by name and type.

        Args:
            name: Entity name
            entity_type: Entity type
            project_id: Optional project ID

        Returns:
            Entity if found, None otherwise
        """
        row = self.execute(
            """
            SELECT * FROM entities
            WHERE name = %s AND entity_type = %s AND project_id IS %s
        """,
            (name, entity_type, project_id),
            fetch_one=True,
        )

        if not row:
            return None

        col_names = [
            "id",
            "name",
            "entity_type",
            "project_id",
            "created_at",
            "updated_at",
            "metadata",
        ]
        return self._row_to_model(dict(zip(col_names, row)))

    def delete_entity(self, entity_id: int) -> bool:
        """Delete entity and all its relations/observations.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        self.execute("DELETE FROM entities WHERE id = %s", (entity_id,))
        self.commit()
        return True

    def create_relation(self, relation: Relation) -> int:
        """Create a relation between entities.

        Args:
            relation: Relation to create

        Returns:
            ID of created relation
        """
        relation_type_str = (
            relation.relation_type.value
            if isinstance(relation.relation_type, RelationType)
            else relation.relation_type
        )

        result = self.execute(
            """
            INSERT INTO entity_relations (
                from_entity_id, to_entity_id, relation_type,
                strength, confidence, created_at, valid_from, valid_until, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                relation.from_entity_id,
                relation.to_entity_id,
                relation_type_str,
                relation.strength,
                relation.confidence,
                int(relation.created_at.timestamp()),
                int(relation.valid_from.timestamp()) if relation.valid_from else None,
                int(relation.valid_until.timestamp()) if relation.valid_until else None,
                self.serialize_json(relation.metadata),
            ),
            fetch_one=True,
        )
        self.commit()
        return result[0] if result else None

    def create_relations(self, relations: list[Relation]) -> list[int]:
        """Create multiple relations.

        Args:
            relations: List of relations to create

        Returns:
            List of created relation IDs
        """
        return [self.create_relation(relation) for relation in relations]

    def delete_relation(self, relation_id: int) -> bool:
        """Delete a relation.

        Args:
            relation_id: Relation ID

        Returns:
            True if deleted, False if not found
        """
        self.execute("DELETE FROM entity_relations WHERE id = %s", (relation_id,))
        self.commit()
        return True

    def add_observation(self, observation: Observation) -> int:
        """Add observation to an entity.

        Args:
            observation: Observation to add

        Returns:
            ID of created observation
        """
        result = self.execute(
            """
            INSERT INTO entity_observations (
                entity_id, content, observation_type,
                confidence, source, timestamp, superseded_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                observation.entity_id,
                observation.content,
                observation.observation_type,
                observation.confidence,
                observation.source,
                int(observation.timestamp.timestamp()),
                observation.superseded_by,
            ),
            fetch_one=True,
        )
        self.commit()
        return result[0] if result else None

    def add_observations(self, observations: list[Observation]) -> list[int]:
        """Add multiple observations.

        Args:
            observations: List of observations to add

        Returns:
            List of created observation IDs
        """
        return [self.add_observation(obs) for obs in observations]

    def get_entity_observations(self, entity_id: int) -> list[Observation]:
        """Get all observations for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            List of observations
        """
        rows = self.execute(
            """
            SELECT * FROM entity_observations
            WHERE entity_id = %s AND superseded_by IS NULL
            ORDER BY timestamp DESC
        """,
            (entity_id,),
            fetch_all=True,
        )

        observations = []
        for row in rows or []:
            observations.append(
                Observation(
                    id=row[0],
                    entity_id=row[1],
                    content=row[2],
                    observation_type=row[3],
                    confidence=row[4],
                    source=row[5],
                    timestamp=datetime.fromtimestamp(row[6]),
                    superseded_by=row[7],
                )
            )

        return observations

    def get_entity_relations(
        self, entity_id: int, direction: str = "both"
    ) -> list[tuple[Relation, Entity]]:
        """Get all relations for an entity.

        Args:
            entity_id: Entity ID
            direction: 'from', 'to', or 'both'

        Returns:
            List of (relation, related_entity) tuples
        """
        if direction == "from":
            query = """
                SELECT
                    r.id as rel_id, r.from_entity_id, r.to_entity_id, r.relation_type,
                    r.strength, r.confidence, r.created_at as rel_created_at,
                    r.valid_from, r.valid_until, r.metadata as rel_metadata,
                    e.id as entity_id, e.name, e.entity_type, e.project_id,
                    e.created_at as entity_created_at, e.updated_at, e.metadata as entity_metadata
                FROM entity_relations r
                JOIN entities e ON r.to_entity_id = e.id
                WHERE r.from_entity_id = %s
            """
        elif direction == "to":
            query = """
                SELECT
                    r.id as rel_id, r.from_entity_id, r.to_entity_id, r.relation_type,
                    r.strength, r.confidence, r.created_at as rel_created_at,
                    r.valid_from, r.valid_until, r.metadata as rel_metadata,
                    e.id as entity_id, e.name, e.entity_type, e.project_id,
                    e.created_at as entity_created_at, e.updated_at, e.metadata as entity_metadata
                FROM entity_relations r
                JOIN entities e ON r.from_entity_id = e.id
                WHERE r.to_entity_id = %s
            """
        else:  # both
            query = """
                SELECT
                    r.id as rel_id, r.from_entity_id, r.to_entity_id, r.relation_type,
                    r.strength, r.confidence, r.created_at as rel_created_at,
                    r.valid_from, r.valid_until, r.metadata as rel_metadata,
                    e.id as entity_id, e.name, e.entity_type, e.project_id,
                    e.created_at as entity_created_at, e.updated_at, e.metadata as entity_metadata
                FROM entity_relations r
                JOIN entities e ON (
                    (r.from_entity_id = ? AND r.to_entity_id = e.id) OR
                    (r.to_entity_id = ? AND r.from_entity_id = e.id)
                )
            """

        params = (entity_id,) if direction != "both" else (entity_id, entity_id)
        rows = self.execute(query, params, fetch_all=True)

        results = []
        for row in rows or []:
            relation = Relation(
                id=row[0],
                from_entity_id=row[1],
                to_entity_id=row[2],
                relation_type=RelationType(row[3]),
                strength=row[4],
                confidence=row[5],
                created_at=datetime.fromtimestamp(row[6]),
                metadata=self.deserialize_json(row[9], {}) if row[9] else {},
            )

            related_entity = Entity(
                id=row[10],
                name=row[11],
                entity_type=EntityType(row[12]),
                project_id=row[13],
                created_at=datetime.fromtimestamp(row[14]),
                updated_at=datetime.fromtimestamp(row[15]),
                metadata=self.deserialize_json(row[16], {}) if row[16] else {},
            )

            results.append((relation, related_entity))

        return results

    def search_entities(
        self, query: str, entity_type: Optional[str] = None, project_id: Optional[int] = None
    ) -> list[Entity]:
        """Search entities by name.

        Args:
            query: Search query
            entity_type: Optional entity type filter
            project_id: Optional project ID filter

        Returns:
            List of matching entities
        """
        sql = "SELECT * FROM entities WHERE name LIKE %s"
        params = [f"%{query}%"]

        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)

        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)

        rows = self.execute(sql, params, fetch_all=True)
        col_names = [
            "id",
            "name",
            "entity_type",
            "project_id",
            "created_at",
            "updated_at",
            "metadata",
        ]

        entities = []
        for row in rows or []:
            entities.append(self._row_to_model(dict(zip(col_names, row))))

        return entities

    def read_graph(self, project_id: Optional[int] = None) -> dict:
        """Read entire graph or project subgraph.

        Args:
            project_id: Optional project ID to filter

        Returns:
            Dictionary with entities and relations
        """
        # Get entities
        if project_id is not None:
            rows = self.execute(
                "SELECT * FROM entities WHERE project_id = %s", (project_id,), fetch_all=True
            )
        else:
            rows = self.execute("SELECT * FROM entities", fetch_all=True)

        entities = []
        entity_ids = set()
        col_names = [
            "id",
            "name",
            "entity_type",
            "project_id",
            "created_at",
            "updated_at",
            "metadata",
        ]
        for row in rows or []:
            entity = self._row_to_model(dict(zip(col_names, row)))
            entities.append(entity)
            entity_ids.add(row[0])

        # Get relations for these entities
        if entity_ids:
            placeholders = ",".join("?" * len(entity_ids))
            rel_rows = self.execute(
                f"""
                SELECT * FROM entity_relations
                WHERE from_entity_id IN ({placeholders}) OR to_entity_id IN ({placeholders})
            """,
                list(entity_ids) + list(entity_ids),
                fetch_all=True,
            )

            relations = []
            for row in rel_rows or []:
                relations.append(
                    Relation(
                        id=row[0],
                        from_entity_id=row[1],
                        to_entity_id=row[2],
                        relation_type=RelationType(row[3]),
                        strength=row[4],
                        confidence=row[5],
                        created_at=datetime.fromtimestamp(row[6]),
                        metadata=self.deserialize_json(row[9], {}) if row[9] else {},
                    )
                )
        else:
            relations = []

        return {"entities": entities, "relations": relations}

    # ==================== ASYNC WRAPPER API ====================
    # These methods provide async wrappers for operations.py compatibility
    # They maintain the operations API contract while using existing store methods

    async def add_entity(self, entity: Entity) -> int:
        """Add entity (async wrapper for create_entity).

        Args:
            entity: Entity to add

        Returns:
            Entity ID
        """
        return self.create_entity(entity)

    async def add_relationship(self, relationship: Relation) -> int:
        """Add relationship (async wrapper for create_relation).

        Args:
            relationship: Relation to add

        Returns:
            Relation ID
        """
        return self.create_relation(relationship)

    async def find_related(
        self, entity_id: int, relation_types: Optional[list[str]] = None, limit: int = 100
    ) -> list[Entity]:
        """Find entities related to a given entity.

        Args:
            entity_id: Entity ID to find relations for
            relation_types: Optional list of relation types to filter
            limit: Maximum results to return

        Returns:
            List of related entities
        """
        # Get relations for this entity
        relations = self.get_entity_relations(entity_id=entity_id, relation_type=None, limit=limit)

        # Filter by relation type if specified
        if relation_types:
            relations = [r for r in relations if r.relation_type.value in relation_types]

        # Get the related entity IDs
        related_ids = set()
        for rel in relations:
            if rel.from_entity_id == entity_id:
                related_ids.add(rel.to_entity_id)
            else:
                related_ids.add(rel.from_entity_id)

        # Fetch the related entities
        related_entities = []
        for eid in list(related_ids)[:limit]:
            entity = self.get_entity(eid)
            if entity:
                related_entities.append(entity)

        return related_entities

    async def get_communities(self, limit: int = 10) -> list[dict]:
        """Get entity communities (clusters).

        Uses a simple heuristic: entities with strong relationships form communities.

        Args:
            limit: Maximum communities to return

        Returns:
            List of community dicts with entities and relations
        """
        # Get all entities
        rows = self.execute("SELECT id FROM entities LIMIT %s", (limit * 10,), fetch_all=True)
        entity_ids = [row[0] for row in rows] if rows else []

        communities = []
        visited = set()

        # Simple community detection: group entities by their neighbors
        for entity_id in entity_ids:
            if entity_id in visited:
                continue

            # Get related entities
            related = await self.find_related(entity_id, limit=5)
            if related:
                community = {
                    "id": len(communities),
                    "members": [entity_id] + [e.id for e in related],
                    "size": len(related) + 1,
                    "strength": 0.5,  # Placeholder
                }
                communities.append(community)
                visited.add(entity_id)
                visited.update(e.id for e in related)

            if len(communities) >= limit:
                break

        return communities

    async def update_entity(self, entity: Entity) -> bool:
        """Update an entity (async wrapper).

        Args:
            entity: Entity with updated values

        Returns:
            True if updated successfully
        """
        # Update the entity in the database
        sql = """
            UPDATE entities
            SET name = %s, entity_type = %s, metadata = %s, updated_at = %s
            WHERE id = %s
        """
        try:
            self.execute(
                sql,
                (
                    entity.name,
                    entity.entity_type.value,
                    self.serialize_json(entity.metadata),
                    int(datetime.now().timestamp()),
                    entity.id,
                ),
            )
            return True
        except Exception:
            return False

    async def list_entities(self, limit: int = 100) -> list[Entity]:
        """List entities (async wrapper).

        Args:
            limit: Maximum entities to return

        Returns:
            List of entities
        """
        rows = self.execute("SELECT * FROM entities LIMIT %s", (limit,), fetch_all=True)
        if not rows:
            return []

        entities = []
        col_names = [
            "id",
            "name",
            "entity_type",
            "project_id",
            "created_at",
            "updated_at",
            "metadata",
        ]
        for row in rows:
            entity = self._row_to_model(dict(zip(col_names, row)))
            entities.append(entity)

        return entities

    async def list_relationships(self, limit: int = 100) -> list[Relation]:
        """List relationships (async wrapper).

        Args:
            limit: Maximum relationships to return

        Returns:
            List of relations
        """
        rows = self.execute("SELECT * FROM entity_relations LIMIT %s", (limit,), fetch_all=True)
        if not rows:
            return []

        relations = []
        for row in rows:
            relation = Relation(
                id=row[0],
                from_entity_id=row[1],
                to_entity_id=row[2],
                relation_type=RelationType(row[3]),
                strength=row[4],
                confidence=row[5],
                created_at=datetime.fromtimestamp(row[6]),
                metadata=self.deserialize_json(row[9], {}) if row[9] else {},
            )
            relations.append(relation)

        return relations
