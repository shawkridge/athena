"""Unit tests for community summarization module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from athena.core.database import Database
from athena.graph.summarization import CommunitySummarizer, SummaryMetadata


@pytest.fixture
def test_db():
    """Create a test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))

        # Create necessary tables
        cursor = db.conn.cursor()

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        # Entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                project_id INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                metadata TEXT,
                UNIQUE(name, entity_type, project_id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Entity relations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity_id INTEGER NOT NULL,
                to_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                confidence REAL DEFAULT 1.0,
                created_at INTEGER NOT NULL,
                valid_from INTEGER,
                valid_until INTEGER,
                metadata TEXT,
                FOREIGN KEY (from_entity_id) REFERENCES entities(id),
                FOREIGN KEY (to_entity_id) REFERENCES entities(id)
            )
        """)

        # Communities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                entity_ids TEXT NOT NULL,
                level INTEGER DEFAULT 0,
                density REAL DEFAULT 0.0,
                internal_edges INTEGER DEFAULT 0,
                external_edges INTEGER DEFAULT 0,
                summary TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        db.conn.commit()
        yield db
        db.conn.close()


@pytest.fixture
def summarizer(test_db):
    """Create a test summarizer."""
    return CommunitySummarizer(test_db)


@pytest.fixture
def test_project(test_db):
    """Create a test project."""
    cursor = test_db.conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, path, created_at) VALUES (?, ?, ?)",
        ("test_project", "/tmp/test", int(datetime.now().timestamp()))
    )
    test_db.conn.commit()

    result = cursor.execute("SELECT last_insert_rowid()").fetchone()
    return result[0]


@pytest.fixture
def test_entities(test_db, test_project):
    """Create test entities."""
    cursor = test_db.conn.cursor()

    entity_names = ["Entity A", "Entity B", "Entity C", "Entity D", "Entity E"]
    entity_ids = []

    for name in entity_names:
        cursor.execute(
            """INSERT INTO entities (name, entity_type, project_id, created_at, updated_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, "concept", test_project, int(datetime.now().timestamp()),
             int(datetime.now().timestamp()), "{}")
        )
        result = cursor.execute("SELECT last_insert_rowid()").fetchone()
        entity_ids.append(result[0])

    test_db.conn.commit()
    return entity_ids


@pytest.fixture
def test_relations(test_db, test_entities):
    """Create test relations between entities."""
    cursor = test_db.conn.cursor()

    # Create relations between entities
    relation_pairs = [
        (test_entities[0], test_entities[1]),
        (test_entities[1], test_entities[2]),
        (test_entities[2], test_entities[3]),
        (test_entities[3], test_entities[4]),
        (test_entities[0], test_entities[4]),
    ]

    for from_id, to_id in relation_pairs:
        cursor.execute(
            """INSERT INTO entity_relations
               (from_entity_id, to_entity_id, relation_type, strength, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (from_id, to_id, "relates_to", 0.8, 0.9, int(datetime.now().timestamp()))
        )

    test_db.conn.commit()
    return relation_pairs


class TestSummaryMetadata:
    """Test SummaryMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating metadata."""
        metadata = SummaryMetadata(
            community_id=1,
            entity_count=5,
            relation_count=10,
            summary_tokens=150,
            model_used="claude-3-haiku",
            created_at=datetime.now(),
            confidence=0.85,
        )

        assert metadata.community_id == 1
        assert metadata.entity_count == 5
        assert metadata.relation_count == 10
        assert metadata.summary_tokens == 150
        assert metadata.confidence == 0.85

    def test_metadata_confidence_range(self):
        """Test that confidence is in valid range."""
        metadata = SummaryMetadata(
            community_id=1,
            entity_count=5,
            relation_count=10,
            summary_tokens=150,
            model_used="test",
            created_at=datetime.now(),
            confidence=0.9,
        )

        assert 0 <= metadata.confidence <= 1


class TestCommunitySummarizerInitialization:
    """Test CommunitySummarizer initialization."""

    def test_init_with_database(self, test_db):
        """Test initializing summarizer with database."""
        summarizer = CommunitySummarizer(test_db)

        assert summarizer.db is test_db
        assert summarizer._summary_cache == {}
        assert summarizer._metadata_cache == {}

    def test_init_with_embedding_model(self, test_db):
        """Test initializing with embedding model."""
        summarizer = CommunitySummarizer(test_db, embedding_model="mock")

        assert summarizer.embedder is not None
        assert summarizer.db is test_db


class TestGetCommunityRelations:
    """Test _get_community_relations helper method."""

    def test_get_relations_empty_list(self, summarizer):
        """Test with empty entity list."""
        relations = summarizer._get_community_relations([])

        assert relations == []


class TestIdentifyCentralEntities:
    """Test _identify_central_entities helper method."""

    def test_identify_central_single_entity(self, summarizer):
        """Test with single entity."""
        central = summarizer._identify_central_entities([1], [])

        assert len(central) > 0
        assert 1 in central


class TestBuildSummaryContext:
    """Test _build_summary_context helper method."""

    def test_build_context_with_empty_relations(self, summarizer):
        """Test building context with no relations."""
        context = summarizer._build_summary_context(
            ["Entity A"], [1], [], max_tokens=200
        )

        assert "Entities in community" in context
        assert "Entity A" in context


class TestCreateFallbackSummary:
    """Test _create_fallback_summary helper method."""

    def test_fallback_with_entities(self, summarizer):
        """Test creating fallback summary with entities."""
        entity_names = ["Entity A", "Entity B", "Entity C"]

        summary = summarizer._create_fallback_summary(entity_names)

        assert "Entity A" in summary
        assert "Entity B" in summary
        assert "Entity C" in summary
        assert "3 entities" in summary

    def test_fallback_without_entities(self, summarizer):
        """Test fallback summary with no entities."""
        summary = summarizer._create_fallback_summary([])

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "entities" in summary.lower()

    def test_fallback_with_single_entity(self, summarizer):
        """Test fallback with single entity."""
        summary = summarizer._create_fallback_summary(["OnlyEntity"])

        assert "OnlyEntity" in summary


class TestCalculateConfidence:
    """Test _calculate_confidence helper method."""

    def test_confidence_single_entity(self, summarizer):
        """Test confidence with single entity."""
        confidence = summarizer._calculate_confidence([1], [])

        assert confidence == 0.3  # Low confidence for single entity

    def test_confidence_empty_list(self, summarizer):
        """Test confidence with empty entity list."""
        confidence = summarizer._calculate_confidence([], [])

        assert confidence == 0.3


class TestIsSummarized:
    """Test _is_summarized helper method."""

    def test_is_summarized_false(self, summarizer):
        """Test with community that does not exist."""
        # Non-existent community should return False
        assert not summarizer._is_summarized(99999)


class TestCaching:
    """Test caching functionality."""

    def test_cache_summary(self, summarizer):
        """Test summary caching."""
        # Manually add to cache
        summarizer._summary_cache[1] = "Test summary"
        metadata = SummaryMetadata(
            community_id=1, entity_count=5, relation_count=10,
            summary_tokens=20, model_used="test", created_at=datetime.now(),
            confidence=0.8
        )
        summarizer._metadata_cache[1] = metadata

        # Verify cache
        assert summarizer.get_summary(1) == "Test summary"
        assert summarizer.get_summary_stats(1) == metadata

    def test_get_summary_from_cache(self, summarizer):
        """Test retrieving from cache."""
        summarizer._summary_cache[1] = "Cached summary"

        summary = summarizer.get_summary(1)
        assert summary == "Cached summary"

    def test_clear_cache(self, summarizer):
        """Test clearing cache."""
        summarizer._summary_cache[1] = "Summary"
        summarizer._metadata_cache[1] = SummaryMetadata(
            community_id=1, entity_count=5, relation_count=10,
            summary_tokens=20, model_used="test", created_at=datetime.now(),
            confidence=0.8
        )

        summarizer.clear_cache()

        assert len(summarizer._summary_cache) == 0
        assert len(summarizer._metadata_cache) == 0


class TestUpdateCommunitySummary:
    """Test updating community summaries."""

    def test_update_nonexistent_community(self, summarizer):
        """Test updating non-existent community."""
        # This should fail gracefully
        result = summarizer.update_community_summary(99999, "Summary")

        assert result is False


class TestGetSummary:
    """Test get_summary method."""

    def test_get_summary_from_cache(self, summarizer):
        """Test getting summary from cache."""
        summarizer._summary_cache[1] = "Cached summary"

        summary = summarizer.get_summary(1)
        assert summary == "Cached summary"

    def test_get_summary_nonexistent(self, summarizer):
        """Test getting non-existent summary."""
        summary = summarizer.get_summary(99999)

        assert summary is None

    def test_get_summary_stats(self, summarizer):
        """Test getting summary stats."""
        metadata = SummaryMetadata(
            community_id=1, entity_count=5, relation_count=10,
            summary_tokens=20, model_used="test", created_at=datetime.now(),
            confidence=0.8
        )
        summarizer._metadata_cache[1] = metadata

        stats = summarizer.get_summary_stats(1)
        assert stats == metadata

    def test_get_summary_stats_nonexistent(self, summarizer):
        """Test getting stats for non-existent community."""
        stats = summarizer.get_summary_stats(99999)

        assert stats is None


class TestBatchSummarizeIntegration:
    """Test batch summarization integration."""

    def test_batch_summarize_no_communities(self, summarizer, test_db):
        """Test batch summarization with no communities."""
        results = summarizer.batch_summarize_communities(999)  # Non-existent project

        assert isinstance(results, dict)
        assert len(results) == 0

    def test_summarize_community_basic(self, summarizer):
        """Test basic community summarization."""
        entity_ids = [1, 2, 3, 4, 5]
        entity_names = [f"Entity {i}" for i in range(5)]

        summary, metadata = summarizer.summarize_community(
            community_id=1,
            entity_ids=entity_ids,
            entity_names=entity_names,
            max_tokens=200
        )

        assert isinstance(summary, str)
        assert metadata.community_id == 1
        assert metadata.entity_count == 5
        assert metadata.summary_tokens >= 0  # May be 0 if LLM fails
        assert 0 <= metadata.confidence <= 1

    def test_summarize_community_caching(self, summarizer):
        """Test that summarization results are cached."""
        entity_ids = [1, 2, 3, 4, 5]
        entity_names = [f"Entity {i}" for i in range(5)]

        # First call
        summary1, _ = summarizer.summarize_community(
            community_id=1,
            entity_ids=entity_ids,
            entity_names=entity_names
        )

        # Second call should use cache
        summary2, _ = summarizer.summarize_community(
            community_id=1,
            entity_ids=entity_ids,
            entity_names=entity_names
        )

        assert summary1 == summary2
        assert 1 in summarizer._summary_cache
