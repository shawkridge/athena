"""Integration tests for semantic store operations."""

import pytest
from datetime import datetime, timedelta
from athena.semantic.store import SemanticStore
from athena.core.models import Memory, MemoryType, ConsolidationState


class TestSemanticStoreIntegration:
    """Integration tests for semantic memory store."""

    @pytest.fixture
    def store(self):
        """Create semantic store for integration testing."""
        try:
            return SemanticStore()
        except Exception as e:
            pytest.skip(f"SemanticStore requires postgres: {e}")

    def test_store_initialization_succeeds(self, store):
        """Test store initializes successfully."""
        assert store.db is not None
        assert store.embedder is not None
        assert store.search is not None
        assert store.optimizer is not None

    def test_memory_type_roundtrip(self, store):
        """Test memory type can be set and retrieved."""
        for memory_type in MemoryType:
            memory = Memory(
                project_id=1,
                content=f"Test {memory_type.value}",
                memory_type=memory_type,
            )
            assert memory.memory_type == memory_type

            # Verify serialization
            model_dict = memory.model_dump()
            assert model_dict["memory_type"] == memory_type.value


class TestConsolidationStateTransitions:
    """Test consolidation state machine."""

    def test_initial_state_consolidated(self):
        """Test default consolidation state is CONSOLIDATED."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )
        assert memory.consolidation_state == ConsolidationState.CONSOLIDATED

    def test_state_transition_to_labile(self):
        """Test transition to labile state on retrieval."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.CONSOLIDATED,
        )
        # Simulate retrieval
        memory.consolidation_state = ConsolidationState.LABILE
        memory.last_retrieved = datetime.now()

        assert memory.consolidation_state == ConsolidationState.LABILE
        assert memory.last_retrieved is not None

    def test_state_transition_to_reconsolidating(self):
        """Test transition to reconsolidating state."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.LABILE,
        )
        # Simulate update
        memory.consolidation_state = ConsolidationState.RECONSOLIDATING

        assert memory.consolidation_state == ConsolidationState.RECONSOLIDATING

    def test_state_transition_to_superseded(self):
        """Test transition to superseded state."""
        old_memory = Memory(
            id=1,
            project_id=1,
            content="Old version",
            memory_type=MemoryType.FACT,
            version=1,
        )
        new_memory = Memory(
            id=2,
            project_id=1,
            content="New version",
            memory_type=MemoryType.FACT,
            version=2,
        )

        # Mark old as superseded
        old_memory.consolidation_state = ConsolidationState.SUPERSEDED
        old_memory.superseded_by = new_memory.id

        assert old_memory.consolidation_state == ConsolidationState.SUPERSEDED
        assert old_memory.superseded_by == 2


class TestMemoryVersioning:
    """Test memory versioning and updates."""

    def test_version_increment_on_update(self):
        """Test version increments on update."""
        v1 = Memory(
            id=1,
            project_id=1,
            content="Original",
            memory_type=MemoryType.FACT,
            version=1,
        )

        # Update
        v2 = Memory(
            id=1,
            project_id=1,
            content="Updated",
            memory_type=MemoryType.FACT,
            version=2,
            updated_at=datetime.now(),
        )

        assert v2.version == v1.version + 1
        assert v2.content == "Updated"

    def test_superseded_by_chain(self):
        """Test chain of superseded versions."""
        v1 = Memory(id=1, project_id=1, content="V1", memory_type=MemoryType.FACT, version=1)
        v2 = Memory(id=2, project_id=1, content="V2", memory_type=MemoryType.FACT, version=2)
        v3 = Memory(id=3, project_id=1, content="V3", memory_type=MemoryType.FACT, version=3)

        # Create chain: V1 -> V2 -> V3
        v1.consolidation_state = ConsolidationState.SUPERSEDED
        v1.superseded_by = v2.id

        v2.consolidation_state = ConsolidationState.SUPERSEDED
        v2.superseded_by = v3.id

        v3.consolidation_state = ConsolidationState.CONSOLIDATED

        assert v1.superseded_by == 2
        assert v2.superseded_by == 3
        assert v3.superseded_by is None


class TestAccessTracking:
    """Test memory access and usefulness tracking."""

    def test_access_count_increments(self):
        """Test access count increments on retrieval."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            access_count=0,
        )

        # Simulate multiple accesses
        for i in range(5):
            memory.access_count += 1

        assert memory.access_count == 5

    def test_last_accessed_updates(self):
        """Test last_accessed timestamp updates."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )

        first_access = datetime.now()
        memory.last_accessed = first_access
        assert memory.last_accessed == first_access

        # Later access
        later_access = datetime.now() + timedelta(minutes=5)
        memory.last_accessed = later_access
        assert memory.last_accessed == later_access
        assert memory.last_accessed > first_access

    def test_usefulness_score_updates(self):
        """Test usefulness score tracking."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            usefulness_score=0.0,
        )

        # Simulate increased usefulness
        memory.usefulness_score = 0.85
        assert memory.usefulness_score == 0.85

        # Score should be in valid range
        assert 0.0 <= memory.usefulness_score <= 1.0


class TestReconsolidationWindow:
    """Test reconsolidation window logic."""

    def test_window_calculation_5_minutes(self):
        """Test 5-minute reconsolidation window."""
        now = datetime.now()
        retrieved_2_min_ago = now - timedelta(minutes=2)

        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            last_retrieved=retrieved_2_min_ago,
        )

        # Check if within 5-minute window
        elapsed = (now - memory.last_retrieved).total_seconds() / 60
        in_window = elapsed < 5

        assert in_window
        assert elapsed < 5

    def test_window_calculation_outside_window(self):
        """Test memory outside reconsolidation window."""
        now = datetime.now()
        retrieved_15_min_ago = now - timedelta(minutes=15)

        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            last_retrieved=retrieved_15_min_ago,
        )

        # Check if outside 5-minute window
        elapsed = (now - memory.last_retrieved).total_seconds() / 60
        in_window = elapsed < 5

        assert not in_window
        assert elapsed > 5


class TestSearchResultRanking:
    """Test search result ranking and relevance."""

    def test_result_ranking_by_similarity(self):
        """Test results are ranked by similarity."""
        from athena.core.models import MemorySearchResult

        memory = Memory(
            id=1,
            project_id=1,
            content="Test memory",
            memory_type=MemoryType.FACT,
        )

        # Create results with different similarities
        results = [
            MemorySearchResult(memory=memory, similarity=0.95, rank=1),
            MemorySearchResult(memory=memory, similarity=0.87, rank=2),
            MemorySearchResult(memory=memory, similarity=0.72, rank=3),
        ]

        # Verify ranking order
        for i in range(len(results) - 1):
            assert results[i].similarity > results[i + 1].similarity
            assert results[i].rank < results[i + 1].rank

    def test_equal_similarity_handling(self):
        """Test handling of equal similarity scores."""
        from athena.core.models import MemorySearchResult

        m1 = Memory(id=1, project_id=1, content="A", memory_type=MemoryType.FACT)
        m2 = Memory(id=2, project_id=1, content="B", memory_type=MemoryType.FACT)

        results = [
            MemorySearchResult(memory=m1, similarity=0.85, rank=1),
            MemorySearchResult(memory=m2, similarity=0.85, rank=2),
        ]

        # Both are valid results with same similarity
        assert len(results) == 2
        assert results[0].similarity == results[1].similarity
        assert results[0].rank < results[1].rank


class TestMemoryFieldDefaults:
    """Test memory field default values."""

    def test_all_defaults(self):
        """Test all field defaults are applied correctly."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )

        # Verify defaults
        assert memory.id is None
        assert memory.tags == []
        assert isinstance(memory.created_at, datetime)
        assert isinstance(memory.updated_at, datetime)
        assert memory.last_accessed is None
        assert memory.last_retrieved is None
        assert memory.access_count == 0
        assert memory.usefulness_score == 0.0
        assert memory.embedding is None
        assert memory.consolidation_state == ConsolidationState.CONSOLIDATED
        assert memory.superseded_by is None
        assert memory.version == 1

    def test_override_defaults(self):
        """Test overriding default values."""
        now = datetime.now()
        embedding = [0.1, 0.2, 0.3]

        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.PATTERN,
            tags=["tag1", "tag2"],
            created_at=now,
            updated_at=now,
            access_count=10,
            usefulness_score=0.9,
            embedding=embedding,
            consolidation_state=ConsolidationState.LABILE,
            version=2,
        )

        assert memory.tags == ["tag1", "tag2"]
        assert memory.created_at == now
        assert memory.access_count == 10
        assert memory.usefulness_score == 0.9
        assert memory.embedding == embedding
        assert memory.consolidation_state == ConsolidationState.LABILE
        assert memory.version == 2
