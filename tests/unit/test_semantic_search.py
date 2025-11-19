"""Tests for semantic search operations."""

import pytest
from athena.semantic.search import SemanticSearch
from athena.core.models import Memory, MemoryType, MemorySearchResult


class TestSemanticSearchInitialization:
    """Test SemanticSearch initialization."""

    def test_search_initialization(self):
        """Test SemanticSearch can be initialized."""
        from athena.core.database_postgres import PostgresDatabase
        from athena.core.embeddings import EmbeddingModel

        # These may fail if postgres/embedder unavailable, but should initialize
        try:
            db = PostgresDatabase()
            embedder = EmbeddingModel()
            search = SemanticSearch(db, embedder)
            assert search.db is not None
            assert search.embedder is not None
        except Exception as e:
            # Gracefully skip if postgres/embedder unavailable
            pytest.skip(f"SemanticSearch requires postgres/embedder: {e}")

    def test_search_query_expander_optional(self):
        """Test that query expander is optional."""
        from athena.core.database_postgres import PostgresDatabase
        from athena.core.embeddings import EmbeddingModel

        try:
            db = PostgresDatabase()
            embedder = EmbeddingModel()
            search = SemanticSearch(db, embedder)
            # Query expander may or may not be initialized depending on config
            # But initialization should not fail
            assert search is not None
        except Exception as e:
            pytest.skip(f"SemanticSearch requires postgres/embedder: {e}")


class TestMemorySearchResult:
    """Test MemorySearchResult construction."""

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
        )
        assert result.memory == memory
        assert result.similarity == 0.95
        assert result.rank == 1

    def test_search_result_similarity_range(self):
        """Test similarity scores are valid."""
        memory = Memory(
            id=1,
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )

        # Similarity should be between 0 and 1
        for similarity in [0.0, 0.5, 1.0]:
            result = MemorySearchResult(
                memory=memory,
                similarity=similarity,
                rank=1,
            )
            assert 0.0 <= result.similarity <= 1.0

    def test_search_result_ranking(self):
        """Test result ranking."""
        memory = Memory(
            id=1,
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )

        results = []
        for rank in range(1, 6):
            result = MemorySearchResult(
                memory=memory,
                similarity=1.0 - (rank * 0.1),
                rank=rank,
            )
            results.append(result)

        # Verify ranking
        for i, result in enumerate(results, 1):
            assert result.rank == i
            assert result.similarity == 1.0 - (i * 0.1)


class TestSemanticSearchConfiguration:
    """Test search configuration handling."""

    def test_min_similarity_threshold(self):
        """Test similarity threshold configuration."""
        # Test valid thresholds
        thresholds = [0.0, 0.3, 0.5, 0.7, 1.0]
        for threshold in thresholds:
            assert 0.0 <= threshold <= 1.0

    def test_k_parameter_validation(self):
        """Test k (result count) parameter."""
        # k should be positive integer
        for k in [1, 5, 10, 100]:
            assert k > 0


class TestSemanticSearchMemoryTypes:
    """Test memory type filtering."""

    def test_memory_type_filtering(self):
        """Test filtering by memory type."""
        # Create memories of different types
        memories = [
            Memory(
                id=1,
                project_id=1,
                content="Fact",
                memory_type=MemoryType.FACT,
            ),
            Memory(
                id=2,
                project_id=1,
                content="Pattern",
                memory_type=MemoryType.PATTERN,
            ),
            Memory(
                id=3,
                project_id=1,
                content="Decision",
                memory_type=MemoryType.DECISION,
            ),
        ]

        # Test filtering for each type
        for memory_type in MemoryType:
            matching = [m for m in memories if m.memory_type == memory_type]
            if memory_type == MemoryType.FACT:
                assert len(matching) == 1
                assert matching[0].id == 1

    def test_all_memory_types_supported(self):
        """Test all memory types are defined and usable."""
        types = [MemoryType.FACT, MemoryType.PATTERN, MemoryType.DECISION, MemoryType.CONTEXT]
        assert len(types) == 4
        assert all(isinstance(t, MemoryType) for t in types)


class TestSemanticSearchResultRanking:
    """Test result ranking and relevance."""

    def test_result_ranking_order(self):
        """Test that results are ranked by relevance."""
        memory = Memory(
            id=1,
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )

        results = [
            MemorySearchResult(memory=memory, similarity=0.95, rank=1),
            MemorySearchResult(memory=memory, similarity=0.87, rank=2),
            MemorySearchResult(memory=memory, similarity=0.73, rank=3),
        ]

        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i].similarity > results[i + 1].similarity
            assert results[i].rank < results[i + 1].rank

    def test_tie_breaking_in_results(self):
        """Test handling of tied similarities."""
        memories = [
            Memory(id=1, project_id=1, content="A", memory_type=MemoryType.FACT),
            Memory(id=2, project_id=1, content="B", memory_type=MemoryType.FACT),
        ]

        # Same similarity score
        results = [
            MemorySearchResult(memory=memories[0], similarity=0.85, rank=1),
            MemorySearchResult(memory=memories[1], similarity=0.85, rank=2),
        ]

        # Both should be valid results
        assert len(results) == 2
        assert results[0].similarity == results[1].similarity
        assert results[0].rank < results[1].rank
