"""Tests for semantic search functionality."""

import pytest
from datetime import datetime, timedelta
from athena.api.marketplace_store import MarketplaceStore
from athena.api.semantic_search import SemanticProcedureSearch
from athena.api.marketplace import (
    ProcedureMetadata,
    MarketplaceProcedure,
    ProcedureQuality,
    UseCaseCategory,
    ProcedureReview,
    ProcedureInstallation,
)
from athena.core.database import Database


class MockEmbeddingModel:
    """Mock embedding model for testing."""

    def embed(self, text: str):
        """Generate a simple embedding based on text hash."""
        # Return a deterministic vector based on text
        hash_val = hash(text)
        return [
            (hash_val >> (i * 8)) % 256 / 256.0
            for i in range(8)
        ]


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def marketplace_store(db):
    """Create marketplace store."""
    return MarketplaceStore(db)


@pytest.fixture
def semantic_search(marketplace_store):
    """Create semantic search with mock embedding model."""
    return SemanticProcedureSearch(marketplace_store, MockEmbeddingModel())


@pytest.fixture
def sample_procedures(marketplace_store):
    """Create sample procedures for testing."""
    procedures = [
        {
            "id": "proc-data-1",
            "name": "CSV Data Loader",
            "description": "Load and parse CSV files efficiently",
            "tags": ["data", "csv", "loading"],
            "category": UseCaseCategory.DATA_PROCESSING,
        },
        {
            "id": "proc-data-2",
            "name": "JSON Parser",
            "description": "Parse and validate JSON data",
            "tags": ["data", "json", "parsing"],
            "category": UseCaseCategory.DATA_PROCESSING,
        },
        {
            "id": "proc-analysis-1",
            "name": "Statistical Analysis",
            "description": "Perform statistical analysis on datasets",
            "tags": ["analysis", "statistics", "data"],
            "category": UseCaseCategory.ANALYSIS,
        },
        {
            "id": "proc-util-1",
            "name": "String Formatter",
            "description": "Format and transform strings",
            "tags": ["utility", "string", "formatting"],
            "category": UseCaseCategory.UTILITY,
        },
    ]

    for proc in procedures:
        meta = ProcedureMetadata(
            procedure_id=proc["id"],
            name=proc["name"],
            description=proc["description"],
            author="test-author",
            version="1.0.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=proc["category"],
            tags=proc["tags"],
        )
        marketplace_store.store_procedure(meta, f"code-{proc['id']}", f"doc-{proc['id']}")

    return procedures


class TestSemanticSearch:
    """Test semantic search functionality."""

    def test_search_by_semantic_similarity(self, semantic_search, sample_procedures):
        """Test semantic similarity search."""
        # Search for data-related procedures
        results = semantic_search.search_by_semantic_similarity("data loading", limit=5)

        assert len(results) > 0
        # Results should be tuples of (procedure, similarity_score)
        for proc, score in results:
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_search_by_use_case(self, semantic_search, sample_procedures):
        """Test searching by use case description."""
        # Search for data processing procedures
        results = semantic_search.search_by_use_case("I need to load CSV files")

        assert len(results) > 0
        for proc in results:
            assert hasattr(proc, "metadata")

    def test_search_related_procedures(self, semantic_search, sample_procedures):
        """Test finding related procedures."""
        # Find procedures related to CSV loader
        results = semantic_search.search_related_procedures("proc-data-1", limit=3)

        # Should not include the original procedure
        proc_ids = [p.metadata.procedure_id for p, _ in results]
        assert "proc-data-1" not in proc_ids
        assert len(results) <= 3

    def test_search_by_tags_semantic(self, semantic_search, sample_procedures):
        """Test semantic tag-based search."""
        results = semantic_search.search_by_tags_semantic(["data"], limit=5)

        # Semantic search should return related procedures even if not exact match
        assert len(results) > 0
        # Most results should be data-related
        data_procs = [p for p in results if "data" in p.metadata.tags or "data" in p.metadata.description.lower()]
        assert len(data_procs) >= len(results) // 2

    def test_get_trending_procedures(self, semantic_search, marketplace_store, sample_procedures):
        """Test getting trending procedures."""
        # Record some installations for proc-data-1
        for i in range(5):
            installation = ProcedureInstallation(
                procedure_id="proc-data-1",
                installed_at=datetime.now(),
                version="1.0.0",
                installed_by=f"user-{i}",
            )
            marketplace_store.record_installation(installation)

        # Add some ratings
        for i in range(3):
            review = ProcedureReview(
                procedure_id="proc-data-1",
                reviewer_id=f"reviewer-{i}",
                rating=4.5,
                comment="Good",
            )
            marketplace_store.add_review(review)

        trending = semantic_search.get_trending_procedures(limit=5)
        assert len(trending) > 0

        # Most trending should be proc-data-1
        if trending:
            top_proc, trend_score = trending[0]
            assert trend_score > 0

    def test_get_quality_recommendations(self, semantic_search, marketplace_store):
        """Test getting quality recommendations."""
        # Create production-quality procedure
        meta_prod = ProcedureMetadata(
            procedure_id="proc-prod",
            name="Production Procedure",
            description="Production ready",
            author="author",
            version="1.0.0",
            quality_level=ProcedureQuality.PRODUCTION,
            use_case=UseCaseCategory.UTILITY,
            tags=["production"],
        )
        marketplace_store.store_procedure(meta_prod, "code", "doc")

        # Create experimental procedure
        meta_exp = ProcedureMetadata(
            procedure_id="proc-exp",
            name="Experimental Procedure",
            description="Experimental",
            author="author",
            version="0.1.0",
            quality_level=ProcedureQuality.EXPERIMENTAL,
            use_case=UseCaseCategory.UTILITY,
            tags=["experimental"],
        )
        marketplace_store.store_procedure(meta_exp, "code", "doc")

        # Get stable+ recommendations
        recommendations = semantic_search.get_quality_recommendations("stable", limit=10)

        # Should include production but not experimental
        proc_ids = [p.metadata.procedure_id for p in recommendations]
        assert "proc-prod" in proc_ids
        assert "proc-exp" not in proc_ids


class TestSemanticSearchFallback:
    """Test fallback search without embedding model."""

    def test_keyword_search_fallback(self, marketplace_store, sample_procedures):
        """Test keyword search fallback when no embedding model."""
        semantic_search = SemanticProcedureSearch(marketplace_store, embedding_model=None)

        # Should fall back to keyword search
        results = semantic_search.search_by_semantic_similarity("CSV", limit=5)

        assert len(results) > 0
        # First result should have CSV in name or description
        first_proc, _ = results[0]
        text = f"{first_proc.metadata.name} {first_proc.metadata.description}".lower()
        assert "csv" in text

    def test_keyword_fallback_on_embedding_error(self, marketplace_store, sample_procedures):
        """Test fallback when embedding model raises error."""

        class FailingEmbeddingModel:
            def embed(self, text):
                raise ValueError("Embedding failed")

        semantic_search = SemanticProcedureSearch(marketplace_store, FailingEmbeddingModel())

        # Should fall back to keyword search without crashing
        results = semantic_search.search_by_semantic_similarity("data", limit=5)

        assert len(results) > 0


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors(self, semantic_search):
        """Test similarity of identical vectors."""
        vec = [1.0, 0.0, 0.0]
        similarity = semantic_search._cosine_similarity(vec, vec)

        assert abs(similarity - 1.0) < 0.0001  # Should be 1.0

    def test_orthogonal_vectors(self, semantic_search):
        """Test similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = semantic_search._cosine_similarity(vec1, vec2)

        assert abs(similarity - 0.0) < 0.0001  # Should be 0.0

    def test_opposite_vectors(self, semantic_search):
        """Test similarity of opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = semantic_search._cosine_similarity(vec1, vec2)

        assert abs(similarity - (-1.0)) < 0.0001  # Should be -1.0

    def test_empty_vectors(self, semantic_search):
        """Test similarity with empty vectors."""
        similarity = semantic_search._cosine_similarity([], [])
        assert similarity == 0.0

    def test_mismatched_dimensions(self, semantic_search):
        """Test similarity with mismatched dimensions."""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = semantic_search._cosine_similarity(vec1, vec2)
        assert similarity == 0.0


class TestSemanticSearchCaching:
    """Test embedding cache functionality."""

    def test_cache_embedding(self, semantic_search, marketplace_store, sample_procedures):
        """Test that embeddings are cached."""
        # Clear cache
        semantic_search.clear_cache()
        assert len(semantic_search.procedure_cache) == 0

        # Do a search to populate cache
        semantic_search.search_by_semantic_similarity("data", limit=5)

        # Cache should have entries
        assert len(semantic_search.procedure_cache) > 0

    def test_clear_cache(self, semantic_search):
        """Test clearing cache."""
        # Add something to cache manually
        semantic_search.procedure_cache["test"] = [1.0, 0.0]
        assert len(semantic_search.procedure_cache) == 1

        # Clear
        semantic_search.clear_cache()
        assert len(semantic_search.procedure_cache) == 0


class TestSemanticSearchThreshold:
    """Test similarity threshold filtering."""

    def test_similarity_threshold(self, semantic_search, sample_procedures):
        """Test filtering results by similarity threshold."""
        # Search with high threshold
        results_strict = semantic_search.search_by_semantic_similarity(
            "data loading",
            limit=10,
            similarity_threshold=0.8,
        )

        # Search with low threshold
        results_loose = semantic_search.search_by_semantic_similarity(
            "data loading",
            limit=10,
            similarity_threshold=0.2,
        )

        # Lower threshold should have more or equal results
        assert len(results_loose) >= len(results_strict)

        # All results should meet their respective thresholds
        for _, score in results_strict:
            assert score >= 0.8

        for _, score in results_loose:
            assert score >= 0.2
