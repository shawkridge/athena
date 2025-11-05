"""Memory migration and copying between projects."""

import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

from ..core.database import Database

logger = logging.getLogger(__name__)


class MemoryMigrationManager:
    """Migrate memories between projects or from one database to another."""

    def __init__(self, source_db: Database, target_db: Database):
        """Initialize migration manager.

        Args:
            source_db: Source database
            target_db: Target database
        """
        self.source_db = source_db
        self.target_db = target_db

        # Mapping tables (old_id -> new_id)
        self.memory_id_map: Dict[int, int] = {}
        self.event_id_map: Dict[int, int] = {}
        self.entity_id_map: Dict[int, int] = {}
        self.relation_id_map: Dict[int, int] = {}

    def migrate_project_memories(
        self,
        source_project_id: int,
        target_project_id: int,
        include_episodic: bool = True,
        include_semantic: bool = True,
        include_procedural: bool = True,
        include_prospective: bool = True,
        include_graph: bool = True,
        include_associations: bool = True,
    ) -> Dict[str, int]:
        """Migrate all memories from source project to target project.

        Args:
            source_project_id: Source project ID
            target_project_id: Target project ID
            include_*: Whether to migrate each memory layer

        Returns:
            Dictionary with counts: {"semantic": 5, "episodic": 10, ...}
        """
        counts = {
            "semantic": 0,
            "episodic": 0,
            "procedural": 0,
            "prospective": 0,
            "entities": 0,
            "relations": 0,
            "associations": 0,
        }

        logger.info(
            f"Starting memory migration from project {source_project_id} "
            f"to project {target_project_id}"
        )

        # Migrate in order (graph before associations)
        if include_graph:
            counts["entities"] = self._migrate_graph_entities(
                source_project_id, target_project_id
            )
            counts["relations"] = self._migrate_graph_relations(
                source_project_id, target_project_id
            )

        if include_semantic:
            counts["semantic"] = self._migrate_semantic_memories(
                source_project_id, target_project_id
            )

        if include_episodic:
            counts["episodic"] = self._migrate_episodic_events(
                source_project_id, target_project_id
            )

        if include_procedural:
            counts["procedural"] = self._migrate_procedures(
                source_project_id, target_project_id
            )

        if include_prospective:
            counts["prospective"] = self._migrate_tasks(
                source_project_id, target_project_id
            )

        if include_associations:
            counts["associations"] = self._migrate_associations(
                source_project_id, target_project_id
            )

        logger.info(
            f"Migration complete. Migrated: {counts['semantic']} semantic, "
            f"{counts['episodic']} episodic, {counts['procedural']} procedural, "
            f"{counts['prospective']} prospective, {counts['entities']} entities"
        )

        return counts

    def _migrate_semantic_memories(
        self, source_project_id: int, target_project_id: int
    ) -> int:
        """Migrate semantic memories."""
        with self.source_db.get_connection() as source_conn:
            memories = source_conn.execute("""
                SELECT id, content, access_count, last_accessed, created_at
                FROM semantic_memories
                WHERE project_id = ?
            """, (source_project_id,)).fetchall()

        count = 0
        for mem in memories:
            with self.target_db.get_connection() as target_conn:
                target_conn.execute("""
                    INSERT INTO semantic_memories (
                        project_id, content, access_count, last_accessed, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    target_project_id,
                    mem["content"],
                    mem["access_count"] or 0,
                    mem["last_accessed"],
                    mem["created_at"],
                ))
                target_conn.commit()
                new_id = target_conn.lastrowid
                self.memory_id_map[mem["id"]] = new_id
                count += 1

        logger.info(f"Migrated {count} semantic memories")
        return count

    def _migrate_episodic_events(
        self, source_project_id: int, target_project_id: int
    ) -> int:
        """Migrate episodic events."""
        with self.source_db.get_connection() as source_conn:
            events = source_conn.execute("""
                SELECT id, session_id, timestamp, event_type, outcome, content, metadata
                FROM episodic_events
                WHERE project_id = ?
                ORDER BY timestamp
            """, (source_project_id,)).fetchall()

        count = 0
        for event in events:
            with self.target_db.get_connection() as target_conn:
                target_conn.execute("""
                    INSERT INTO episodic_events (
                        project_id, session_id, timestamp, event_type, outcome, content, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    target_project_id,
                    event["session_id"],
                    event["timestamp"],
                    event["event_type"],
                    event["outcome"],
                    event["content"],
                    event["metadata"],
                ))
                target_conn.commit()
                new_id = target_conn.lastrowid
                self.event_id_map[event["id"]] = new_id
                count += 1

        logger.info(f"Migrated {count} episodic events")
        return count

    def _migrate_procedures(
        self, source_project_id: int, target_project_id: int
    ) -> int:
        """Migrate procedural memories (procedures)."""
        with self.source_db.get_connection() as source_conn:
            procedures = source_conn.execute("""
                SELECT id, name, description, category, success_rate, confidence, created_at
                FROM procedures
                WHERE project_id = ?
            """, (source_project_id,)).fetchall()

        count = 0
        for proc in procedures:
            with self.target_db.get_connection() as target_conn:
                target_conn.execute("""
                    INSERT INTO procedures (
                        project_id, name, description, category, success_rate, confidence, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    target_project_id,
                    proc["name"],
                    proc["description"],
                    proc["category"],
                    proc["success_rate"],
                    proc["confidence"],
                    proc["created_at"],
                ))
                target_conn.commit()
                count += 1

        logger.info(f"Migrated {count} procedures")
        return count

    def _migrate_tasks(
        self, source_project_id: int, target_project_id: int
    ) -> int:
        """Migrate prospective tasks."""
        with self.source_db.get_connection() as source_conn:
            tasks = source_conn.execute("""
                SELECT id, content, status, priority, created_at
                FROM prospective_tasks
                WHERE project_id = ?
            """, (source_project_id,)).fetchall()

        count = 0
        for task in tasks:
            with self.target_db.get_connection() as target_conn:
                target_conn.execute("""
                    INSERT INTO prospective_tasks (
                        project_id, content, status, priority, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    target_project_id,
                    task["content"],
                    task["status"],
                    task["priority"],
                    task["created_at"],
                ))
                target_conn.commit()
                count += 1

        logger.info(f"Migrated {count} prospective tasks")
        return count

    def _migrate_graph_entities(
        self, source_project_id: int, target_project_id: int
    ) -> int:
        """Migrate knowledge graph entities."""
        with self.source_db.get_connection() as source_conn:
            entities = source_conn.execute("""
                SELECT id, name, entity_type, description, created_at
                FROM graph_entities
                WHERE project_id = ?
            """, (source_project_id,)).fetchall()

        count = 0
        for entity in entities:
            with self.target_db.get_connection() as target_conn:
                target_conn.execute("""
                    INSERT INTO graph_entities (
                        project_id, name, entity_type, description, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    target_project_id,
                    entity["name"],
                    entity["entity_type"],
                    entity["description"],
                    entity["created_at"],
                ))
                target_conn.commit()
                new_id = target_conn.lastrowid
                self.entity_id_map[entity["id"]] = new_id
                count += 1

        logger.info(f"Migrated {count} graph entities")
        return count

    def _migrate_graph_relations(
        self, source_project_id: int, target_project_id: int
    ) -> int:
        """Migrate knowledge graph relations."""
        with self.source_db.get_connection() as source_conn:
            relations = source_conn.execute("""
                SELECT id, from_entity_id, to_entity_id, relation_type, strength, confidence, created_at
                FROM graph_relations
                WHERE project_id = ?
            """, (source_project_id,)).fetchall()

        count = 0
        for rel in relations:
            # Map old entity IDs to new ones
            from_id = self.entity_id_map.get(rel["from_entity_id"])
            to_id = self.entity_id_map.get(rel["to_entity_id"])

            if from_id and to_id:
                with self.target_db.get_connection() as target_conn:
                    target_conn.execute("""
                        INSERT INTO graph_relations (
                            project_id, from_entity_id, to_entity_id, relation_type,
                            strength, confidence, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        target_project_id,
                        from_id,
                        to_id,
                        rel["relation_type"],
                        rel["strength"],
                        rel["confidence"],
                        rel["created_at"],
                    ))
                    target_conn.commit()
                    count += 1

        logger.info(f"Migrated {count} graph relations")
        return count

    def _migrate_associations(
        self, source_project_id: int, target_project_id: int
    ) -> int:
        """Migrate association links between memories."""
        with self.source_db.get_connection() as source_conn:
            links = source_conn.execute("""
                SELECT id, from_memory_id, to_memory_id, from_layer, to_layer,
                       link_strength, link_type, co_occurrence_count
                FROM association_links
                WHERE project_id = ?
            """, (source_project_id,)).fetchall()

        count = 0
        for link in links:
            # Map old memory IDs to new ones
            from_id = self.memory_id_map.get(link["from_memory_id"])
            to_id = self.memory_id_map.get(link["to_memory_id"])

            if from_id and to_id:
                with self.target_db.get_connection() as target_conn:
                    target_conn.execute("""
                        INSERT INTO association_links (
                            project_id, from_memory_id, to_memory_id, from_layer, to_layer,
                            link_strength, link_type, co_occurrence_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        target_project_id,
                        from_id,
                        to_id,
                        link["from_layer"],
                        link["to_layer"],
                        link["link_strength"],
                        link["link_type"],
                        link["co_occurrence_count"],
                    ))
                    target_conn.commit()
                    count += 1

        logger.info(f"Migrated {count} association links")
        return count

    def migrate_global_to_project(
        self,
        target_project_id: int,
        memory_ids: Optional[List[int]] = None,
    ) -> Dict[str, int]:
        """Migrate specific memories from global (project_id=1) to target project.

        This is useful for sharing discovered patterns across projects.

        Args:
            target_project_id: Target project ID
            memory_ids: Specific memory IDs to migrate (None = all)

        Returns:
            Counts of migrated memories
        """
        source_project_id = 1  # Global project
        return self.migrate_project_memories(
            source_project_id,
            target_project_id,
            include_episodic=False,  # Only semantic patterns
        )

    def get_migration_stats(
        self, source_project_id: int
    ) -> Dict[str, int]:
        """Get statistics on what would be migrated."""
        with self.source_db.get_connection() as conn:
            stats = {}

            # Count each layer
            result = conn.execute(
                "SELECT COUNT(*) as count FROM semantic_memories WHERE project_id = ?",
                (source_project_id,)
            ).fetchone()
            stats["semantic"] = result["count"] or 0

            result = conn.execute(
                "SELECT COUNT(*) as count FROM episodic_events WHERE project_id = ?",
                (source_project_id,)
            ).fetchone()
            stats["episodic"] = result["count"] or 0

            result = conn.execute(
                "SELECT COUNT(*) as count FROM procedures WHERE project_id = ?",
                (source_project_id,)
            ).fetchone()
            stats["procedural"] = result["count"] or 0

            result = conn.execute(
                "SELECT COUNT(*) as count FROM prospective_tasks WHERE project_id = ?",
                (source_project_id,)
            ).fetchone()
            stats["prospective"] = result["count"] or 0

            result = conn.execute(
                "SELECT COUNT(*) as count FROM graph_entities WHERE project_id = ?",
                (source_project_id,)
            ).fetchone()
            stats["entities"] = result["count"] or 0

            result = conn.execute(
                "SELECT COUNT(*) as count FROM graph_relations WHERE project_id = ?",
                (source_project_id,)
            ).fetchone()
            stats["relations"] = result["count"] or 0

        return stats
