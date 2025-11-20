"""Tests for semantic memory models and data structures."""

from datetime import datetime
from athena.core.models import (
    Memory,
    MemoryType,
    MemorySearchResult,
    ConsolidationState,
    Project,
)


class TestMemoryType:
    """Test MemoryType enumeration."""

    def test_memory_type_values(self):
        """Test all memory type values."""
        assert MemoryType.FACT.value == "fact"
        assert MemoryType.PATTERN.value == "pattern"
        assert MemoryType.DECISION.value == "decision"
        assert MemoryType.CONTEXT.value == "context"

    def test_memory_type_from_string(self):
        """Test creating MemoryType from string."""
        assert MemoryType("fact") == MemoryType.FACT
        assert MemoryType("pattern") == MemoryType.PATTERN


class TestConsolidationState:
    """Test ConsolidationState enumeration."""

    def test_consolidation_states(self):
        """Test all consolidation states."""
        assert ConsolidationState.UNCONSOLIDATED.value == "unconsolidated"
        assert ConsolidationState.CONSOLIDATING.value == "consolidating"
        assert ConsolidationState.CONSOLIDATED.value == "consolidated"
        assert ConsolidationState.LABILE.value == "labile"
        assert ConsolidationState.RECONSOLIDATING.value == "reconsolidating"
        assert ConsolidationState.SUPERSEDED.value == "superseded"


class TestMemory:
    """Test Memory model."""

    def test_memory_creation_minimal(self):
        """Test creating Memory with minimal fields."""
        memory = Memory(
            project_id=1,
            content="Test content",
            memory_type=MemoryType.FACT,
        )
        assert memory.id is None
        assert memory.project_id == 1
        assert memory.content == "Test content"
        assert memory.memory_type == MemoryType.FACT
        assert memory.tags == []
        assert memory.access_count == 0
        assert memory.usefulness_score == 0.0
        assert memory.consolidation_state == ConsolidationState.CONSOLIDATED

    def test_memory_creation_full(self):
        """Test creating Memory with all fields."""
        now = datetime.now()
        memory = Memory(
            id=123,
            project_id=1,
            content="Architectural decision",
            memory_type=MemoryType.DECISION,
            tags=["architecture", "database"],
            created_at=now,
            updated_at=now,
            last_accessed=now,
            last_retrieved=now,
            access_count=5,
            usefulness_score=0.85,
            embedding=[0.1, 0.2, 0.3],
            consolidation_state=ConsolidationState.CONSOLIDATED,
            superseded_by=None,
            version=2,
        )
        assert memory.id == 123
        assert memory.tags == ["architecture", "database"]
        assert memory.access_count == 5
        assert memory.usefulness_score == 0.85
        assert memory.version == 2

    def test_memory_type_enum_conversion(self):
        """Test MemoryType enum value serialization."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.PATTERN,
        )
        model_dict = memory.model_dump()
        assert model_dict["memory_type"] == "pattern"

    def test_consolidation_state_enum_conversion(self):
        """Test ConsolidationState enum value serialization."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.LABILE,
        )
        model_dict = memory.model_dump()
        assert model_dict["consolidation_state"] == "labile"

    def test_memory_defaults(self):
        """Test Memory field defaults."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )
        assert isinstance(memory.created_at, datetime)
        assert isinstance(memory.updated_at, datetime)
        assert memory.last_accessed is None
        assert memory.last_retrieved is None
        assert memory.access_count == 0
        assert memory.usefulness_score == 0.0
        assert memory.embedding is None


class TestMemorySearchResult:
    """Test MemorySearchResult model."""

    def test_search_result_creation(self):
        """Test creating search result."""
        memory = Memory(
            id=1,
            project_id=1,
            content="Test fact",
            memory_type=MemoryType.FACT,
        )
        result = MemorySearchResult(
            memory=memory,
            similarity=0.95,
            rank=1,
            metadata={"source": "embedding"},
        )
        assert result.memory == memory
        assert result.similarity == 0.95
        assert result.rank == 1
        assert result.metadata["source"] == "embedding"

    def test_search_result_without_metadata(self):
        """Test search result without metadata."""
        memory = Memory(
            id=1,
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )
        result = MemorySearchResult(
            memory=memory,
            similarity=0.8,
            rank=2,
        )
        assert result.metadata is None


class TestProject:
    """Test Project model."""

    def test_project_creation(self):
        """Test creating project."""
        project = Project(
            id=1,
            name="Test Project",
            path="/home/user/project",
            memory_count=42,
        )
        assert project.id == 1
        assert project.name == "Test Project"
        assert project.path == "/home/user/project"
        assert project.memory_count == 42

    def test_project_defaults(self):
        """Test project field defaults."""
        project = Project(
            name="New Project",
            path="/tmp/project",
        )
        assert project.id is None
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.last_accessed, datetime)
        assert project.memory_count == 0
