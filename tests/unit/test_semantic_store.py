"""Tests for semantic memory storage operations."""

import pytest
from datetime import datetime
from athena.semantic.store import SemanticStore
from athena.core.models import Memory, MemoryType, ConsolidationState


class TestSemanticStoreRowToModel:
    """Test database row to Memory model conversion."""

    @pytest.fixture
    def store(self):
        """Create semantic store for testing."""
        # Use in-memory or test database
        return SemanticStore(db_path=":memory:")

    def test_row_to_model_with_all_fields(self, store):
        """Test converting row with all fields populated."""
        now = datetime.now()
        row = {
            "id": 1,
            "project_id": 1,
            "content": "Python is dynamically typed",
            "memory_type": "fact",
            "tags": '["python", "typing"]',
            "created_at": now,
            "updated_at": now,
            "last_accessed": now,
            "last_retrieved": now,
            "access_count": 3,
            "usefulness_score": 0.9,
            "embedding": [0.1, 0.2, 0.3],
            "consolidation_state": "consolidated",
            "superseded_by": None,
            "version": 1,
        }

        memory = store._row_to_model(row)

        assert memory.id == 1
        assert memory.project_id == 1
        assert memory.content == "Python is dynamically typed"
        assert memory.memory_type == MemoryType.FACT
        assert memory.tags == ["python", "typing"]
        assert memory.access_count == 3
        assert memory.usefulness_score == 0.9
        assert memory.consolidation_state == ConsolidationState.CONSOLIDATED

    def test_row_to_model_with_minimal_fields(self, store):
        """Test converting row with minimal fields."""
        row = {
            "id": 1,
            "project_id": 1,
            "content": "Test fact",
            "memory_type": "fact",
            "tags": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        memory = store._row_to_model(row)

        assert memory.id == 1
        assert memory.content == "Test fact"
        assert memory.tags == []
        assert memory.access_count == 0
        assert memory.usefulness_score == 0.0

    def test_row_to_model_all_memory_types(self, store):
        """Test conversion with all memory types."""
        base_row = {
            "id": 1,
            "project_id": 1,
            "content": "Test",
            "tags": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        for memory_type in ["fact", "pattern", "decision", "context"]:
            row = {**base_row, "memory_type": memory_type}
            memory = store._row_to_model(row)
            assert memory.memory_type == MemoryType(memory_type)

    def test_row_to_model_all_consolidation_states(self, store):
        """Test conversion with all consolidation states."""
        base_row = {
            "id": 1,
            "project_id": 1,
            "content": "Test",
            "memory_type": "fact",
            "tags": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        states = [
            "unconsolidated",
            "consolidating",
            "consolidated",
            "labile",
            "reconsolidating",
            "superseded",
        ]

        for state in states:
            row = {**base_row, "consolidation_state": state}
            memory = store._row_to_model(row)
            assert memory.consolidation_state == ConsolidationState(state)

    def test_row_to_model_json_tags_parsing(self, store):
        """Test JSON tag parsing."""
        row = {
            "id": 1,
            "project_id": 1,
            "content": "Test",
            "memory_type": "fact",
            "tags": '["tag1", "tag2", "tag3"]',
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        memory = store._row_to_model(row)
        assert memory.tags == ["tag1", "tag2", "tag3"]

    def test_row_to_model_empty_tags(self, store):
        """Test empty tags handling."""
        row = {
            "id": 1,
            "project_id": 1,
            "content": "Test",
            "memory_type": "fact",
            "tags": "[]",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        memory = store._row_to_model(row)
        assert memory.tags == []

    def test_row_to_model_with_embedding(self, store):
        """Test embedding preservation."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        row = {
            "id": 1,
            "project_id": 1,
            "content": "Test",
            "memory_type": "fact",
            "tags": None,
            "embedding": embedding,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        memory = store._row_to_model(row)
        assert memory.embedding == embedding

    def test_row_to_model_with_superseded_by(self, store):
        """Test superseded_by field."""
        row = {
            "id": 1,
            "project_id": 1,
            "content": "Old fact",
            "memory_type": "fact",
            "tags": None,
            "consolidation_state": "superseded",
            "superseded_by": 2,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        memory = store._row_to_model(row)
        assert memory.superseded_by == 2
        assert memory.consolidation_state == ConsolidationState.SUPERSEDED

    def test_row_to_model_version_tracking(self, store):
        """Test version field."""
        row = {
            "id": 1,
            "project_id": 1,
            "content": "Test",
            "memory_type": "fact",
            "tags": None,
            "version": 3,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        memory = store._row_to_model(row)
        assert memory.version == 3


class TestSemanticStoreInitialization:
    """Test SemanticStore initialization."""

    def test_store_initialization(self):
        """Test basic store initialization."""
        store = SemanticStore()
        assert store.db is not None
        assert store.embedder is not None
        assert store.search is not None
        assert store.optimizer is not None

    def test_store_with_db_path_ignored(self):
        """Test that db_path is ignored (backward compat)."""
        # Should not raise error even with db_path (ignored for postgres)
        store = SemanticStore(db_path="/tmp/ignored")
        assert store.db is not None

    def test_store_postgres_detection(self):
        """Test PostgreSQL detection method."""
        # Should detect if postgres env vars are set
        result = SemanticStore._should_use_postgres()
        assert isinstance(result, bool)


class TestSemanticStoreOperations:
    """Test semantic store operations."""

    @pytest.fixture
    def store(self):
        """Create test store."""
        return SemanticStore()

    def test_memory_type_validation(self, store):
        """Test memory type validation."""
        # Valid type
        memory_type = MemoryType.FACT
        assert memory_type == MemoryType.FACT

        # Type conversion from string
        converted = MemoryType("pattern")
        assert converted == MemoryType.PATTERN

    def test_consolidation_state_defaults(self, store):
        """Test consolidation state defaults."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )
        # Default should be CONSOLIDATED
        assert memory.consolidation_state == ConsolidationState.CONSOLIDATED

    def test_project_creation_fields(self, store):
        """Test project field requirements."""
        # Name and path are required
        from athena.core.models import Project

        project = Project(name="Test", path="/test/path")
        assert project.name == "Test"
        assert project.path == "/test/path"
