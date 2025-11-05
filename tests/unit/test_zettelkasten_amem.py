"""Tests for A-MEM Zettelkasten memory evolution system."""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from athena.core.database import Database
from athena.associations.zettelkasten import (
    ZettelkastenEvolution,
    MemoryVersion,
    MemoryAttribute,
    HierarchicalIndex,
)


@pytest.fixture
def db():
    """Create temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = Database(str(db_path))

        # Create required tables
        with database.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memories (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER,
                    content TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed INTEGER,
                    created_at INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS association_links (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER,
                    from_memory_id INTEGER,
                    to_memory_id INTEGER,
                    from_layer TEXT,
                    to_layer TEXT
                )
            """)
            conn.commit()

        yield database


class TestMemoryVersioning:
    """Test memory versioning functionality."""

    def test_create_first_version(self, db):
        """Test creating first version of a memory."""
        # Create semantic memory first
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (project_id, content, created_at)
                VALUES (1, 'Original content', ?)
            """, (int(datetime.now().timestamp()),))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)
        version = zettel.create_memory_version(memory_id, "Original content")

        assert version.memory_id == memory_id
        assert version.version == 1
        assert version.content == "Original content"
        assert version.hash is not None

    def test_create_multiple_versions(self, db):
        """Test creating multiple versions of same memory."""
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (project_id, content, created_at)
                VALUES (1, 'v1', ?)
            """, (int(datetime.now().timestamp()),))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)

        v1 = zettel.create_memory_version(memory_id, "Version 1")
        v2 = zettel.create_memory_version(memory_id, "Version 2 with changes")
        v3 = zettel.create_memory_version(memory_id, "Version 3 with more changes")

        assert v1.version == 1
        assert v2.version == 2
        assert v3.version == 3
        assert v1.hash != v2.hash
        assert v2.hash != v3.hash

    def test_get_evolution_history(self, db):
        """Test retrieving evolution history."""
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (project_id, content, created_at)
                VALUES (1, 'v1', ?)
            """, (int(datetime.now().timestamp()),))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)

        for i in range(1, 4):
            zettel.create_memory_version(memory_id, f"Version {i}")

        history = zettel.get_memory_evolution_history(memory_id)

        assert len(history) == 3
        assert history[0].version == 1
        assert history[-1].version == 3


class TestMemoryAttributes:
    """Test auto-generated memory attributes."""

    def test_compute_attributes_nascent(self, db):
        """Test computing attributes for new memory (nascent stage)."""
        now_ts = int(datetime.now().timestamp())
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (
                    project_id, content, access_count, last_accessed, created_at
                ) VALUES (1, 'Test content', 0, ?, ?)
            """, (now_ts, now_ts))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)
        attr = zettel.compute_memory_attributes(memory_id)

        assert attr.memory_id == memory_id
        assert attr.evolution_stage == "nascent"
        assert 0.0 <= attr.importance_score <= 1.0
        assert isinstance(attr.context_tags, list)
        assert attr.related_count == 0

    def test_compute_attributes_developing(self, db):
        """Test attributes for memory with multiple versions."""
        now_ts = int(datetime.now().timestamp())
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (
                    project_id, content, access_count, last_accessed, created_at
                ) VALUES (1, 'Test content', 5, ?, ?)
            """, (now_ts, now_ts))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)

        # Create versions to move it to developing stage
        for i in range(2):
            zettel.create_memory_version(memory_id, f"Version {i+1}")

        attr = zettel.compute_memory_attributes(memory_id)

        assert attr.evolution_stage == "developing"
        assert attr.related_count >= 0

    def test_importance_score_calculation(self, db):
        """Test importance score reflects access patterns."""
        now_ts = int(datetime.now().timestamp())

        # Create two memories with different access patterns
        with db.get_connection() as conn:
            # Frequently accessed
            conn.execute("""
                INSERT INTO semantic_memories (
                    project_id, content, access_count, last_accessed, created_at
                ) VALUES (1, 'Popular content', 50, ?, ?)
            """, (now_ts, now_ts))
            conn.commit()
            memory_popular = conn.lastrowid

            # Rarely accessed
            conn.execute("""
                INSERT INTO semantic_memories (
                    project_id, content, access_count, last_accessed, created_at
                ) VALUES (1, 'Unpopular content', 1, ?, ?)
            """, (now_ts - 86400*90, now_ts - 86400*90))  # 90 days old
            conn.commit()
            memory_old = conn.lastrowid

        zettel = ZettelkastenEvolution(db)

        attr_popular = zettel.compute_memory_attributes(memory_popular)
        attr_old = zettel.compute_memory_attributes(memory_old)

        # Popular should have higher importance
        assert attr_popular.importance_score > attr_old.importance_score

    def test_context_tags_extraction(self, db):
        """Test extraction of context tags from content."""
        now_ts = int(datetime.now().timestamp())
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (
                    project_id, content, access_count, created_at
                ) VALUES (1, 'Authentication JWT Token Security Implementation', 0, ?)
            """, (now_ts,))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)
        attr = zettel.compute_memory_attributes(memory_id)

        assert len(attr.context_tags) > 0
        assert any(tag in attr.context_tags for tag in ["authentication", "jwt", "token", "security"])


class TestHierarchicalIndexing:
    """Test hierarchical indexing (Luhmann numbering)."""

    def test_create_root_index(self, db):
        """Test creating root (level 0) index."""
        zettel = ZettelkastenEvolution(db)
        index = zettel.create_hierarchical_index(
            project_id=1,
            parent_id=None,
            label="Main Topics"
        )

        assert index.index_id == "1"
        assert index.parent_id is None
        assert index.depth == 0
        assert index.label == "Main Topics"

    def test_create_nested_indices(self, db):
        """Test creating nested indices."""
        zettel = ZettelkastenEvolution(db)

        root = zettel.create_hierarchical_index(1, None, "Root")
        child1 = zettel.create_hierarchical_index(1, root.index_id, "Child 1")
        child2 = zettel.create_hierarchical_index(1, root.index_id, "Child 2")
        grandchild = zettel.create_hierarchical_index(1, child1.index_id, "Grandchild")

        assert root.index_id == "1"
        assert child1.index_id == "1.1"
        assert child2.index_id == "1.2"
        assert grandchild.index_id == "1.1.1"
        assert grandchild.depth == 2

    def test_assign_memory_to_index(self, db):
        """Test assigning memories to index positions."""
        now_ts = int(datetime.now().timestamp())
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (project_id, content, created_at)
                VALUES (1, 'Test note', ?)
            """, (now_ts,))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)
        index = zettel.create_hierarchical_index(1, None, "Notes")
        zettel.assign_memory_to_index(memory_id, index.index_id)

        # Verify assignment
        with db.get_connection() as conn:
            result = conn.execute(
                "SELECT memory_ids FROM hierarchical_index WHERE index_id = ?",
                (index.index_id,)
            ).fetchone()

        import json
        memory_ids = json.loads(result["memory_ids"])
        assert memory_id in memory_ids

    def test_luhmann_numbering_sequence(self, db):
        """Test Luhmann numbering system."""
        zettel = ZettelkastenEvolution(db)

        # Create multiple roots
        indices = []
        for i in range(3):
            idx = zettel.create_hierarchical_index(1, None, f"Root {i+1}")
            indices.append(idx)

        assert indices[0].index_id == "1"
        assert indices[1].index_id == "2"
        assert indices[2].index_id == "3"


class TestMemoryEvolution:
    """Test memory evolution triggering."""

    def test_version_change_triggers_update(self, db):
        """Test that changing a memory triggers evolution update."""
        now_ts = int(datetime.now().timestamp())
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (project_id, content, created_at)
                VALUES (1, 'Original', ?)
            """, (now_ts,))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)
        v1 = zettel.create_memory_version(memory_id, "Original")
        v2 = zettel.create_memory_version(memory_id, "Updated content")

        # Different hashes indicate change
        assert v1.hash != v2.hash

    def test_attribute_update_on_version_change(self, db):
        """Test that attributes update when memory changes."""
        now_ts = int(datetime.now().timestamp())
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (
                    project_id, content, access_count, created_at
                ) VALUES (1, 'Original content', 1, ?)
            """, (now_ts,))
            conn.commit()
            memory_id = conn.lastrowid

        zettel = ZettelkastenEvolution(db)

        # Create initial version
        zettel.create_memory_version(memory_id, "Original content")
        attr1 = zettel.compute_memory_attributes(memory_id)

        # Create new version
        zettel.create_memory_version(memory_id, "Updated with new information")
        attr2 = zettel.compute_memory_attributes(memory_id)

        # Evolution stage should progress
        assert attr2.evolution_stage == "developing"


class TestIntegration:
    """Integration tests for full Zettelkasten workflow."""

    def test_complete_workflow(self, db):
        """Test complete A-MEM workflow."""
        now_ts = int(datetime.now().timestamp())

        # Create semantic memories
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_memories (project_id, content, created_at)
                VALUES (1, 'Authentication patterns', ?)
            """, (now_ts,))
            conn.commit()
            memory1 = conn.lastrowid

            conn.execute("""
                INSERT INTO semantic_memories (project_id, content, created_at)
                VALUES (1, 'JWT implementation', ?)
            """, (now_ts,))
            conn.commit()
            memory2 = conn.lastrowid

            # Create association
            conn.execute("""
                INSERT INTO association_links (
                    project_id, from_memory_id, to_memory_id, from_layer, to_layer
                ) VALUES (1, ?, ?, 'semantic', 'semantic')
            """, (memory1, memory2))
            conn.commit()

        zettel = ZettelkastenEvolution(db)

        # Create hierarchical index
        root = zettel.create_hierarchical_index(1, None, "Security Patterns")
        auth_index = zettel.create_hierarchical_index(1, root.index_id, "Authentication")

        # Assign memories
        zettel.assign_memory_to_index(memory1, auth_index.index_id)
        zettel.assign_memory_to_index(memory2, auth_index.index_id)

        # Create versions
        v1 = zettel.create_memory_version(memory1, "Authentication patterns: OAuth, JWT, Sessions")
        v2 = zettel.create_memory_version(memory1, "Authentication patterns: OAuth2, JWT (RS256), Sessions (httpOnly)")

        # Get attributes
        attr = zettel.compute_memory_attributes(memory1)
        history = zettel.get_memory_evolution_history(memory1)

        assert len(history) == 2
        assert attr.evolution_stage == "developing"
        assert attr.related_count == 1
        assert len(attr.context_tags) > 0
