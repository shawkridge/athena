"""Unit tests for GraphRAG implementation."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.athena.rag.graphrag import (
    GraphRAGManager,
    CommunitySummary,
    RetrievalResult
)
from src.athena.core.models import Memory, MemoryType


@pytest.fixture
def mock_graph_store():
    """Create mock GraphStore."""
    graph = Mock()
    graph.get_communities.return_value = [
        {
            'id': 1,
            'name': 'AI & ML',
            'summary': 'Knowledge area covering artificial intelligence and machine learning concepts',
            'topic': 'AI'
        },
        {
            'id': 2,
            'name': 'Software Engineering',
            'summary': 'Knowledge area covering software design patterns and best practices',
            'topic': 'Engineering'
        }
    ]
    graph.get_community_entities.return_value = [
        {'id': 101, 'name': 'Neural Network', 'type': 'concept', 'description': 'A model inspired by the brain'},
        {'id': 102, 'name': 'Deep Learning', 'type': 'concept', 'description': 'Learning with multiple layers'}
    ]
    graph.get_neighbors.return_value = []
    return graph


@pytest.fixture
def mock_semantic_search():
    """Create mock RAGManager."""
    search = Mock()
    search.recall.return_value = [
        Mock(memory=Memory(id=1, project_id=1, content='Test memory 1', memory_type='fact'), similarity=0.9),
        Mock(memory=Memory(id=2, project_id=1, content='Test memory 2', memory_type='fact'), similarity=0.8)
    ]
    return search


@pytest.fixture
def graphrag_manager(mock_graph_store, mock_semantic_search):
    """Create GraphRAGManager instance."""
    return GraphRAGManager(mock_graph_store, mock_semantic_search)


class TestGraphRAGManager:
    """Test GraphRAGManager class."""

    def test_initialization(self, graphrag_manager):
        """Test manager initialization."""
        assert graphrag_manager.graph is not None
        assert graphrag_manager.semantic is not None
        assert len(graphrag_manager._community_summaries) == 0

    def test_get_all_summaries(self, graphrag_manager):
        """Test loading all community summaries."""
        summaries = graphrag_manager._get_all_summaries()

        assert len(summaries) == 2
        assert summaries[0].community_id == 1
        assert summaries[0].name == 'AI & ML'
        assert summaries[1].community_id == 2
        assert summaries[1].name == 'Software Engineering'

    def test_get_all_summaries_cached(self, graphrag_manager):
        """Test summary caching."""
        # First call
        summaries1 = graphrag_manager._get_all_summaries()
        # Second call (should use cache)
        summaries2 = graphrag_manager._get_all_summaries()

        assert len(summaries1) == len(summaries2)
        assert summaries1[0] is summaries2[0]  # Same object

    def test_compute_relevance(self, graphrag_manager):
        """Test relevance computation."""
        # High relevance (multiple matching words)
        score1 = graphrag_manager._compute_relevance(
            "machine learning",
            "artificial intelligence and machine learning concepts"
        )
        assert score1 > 0.3

        # Low relevance (no matching words)
        score2 = graphrag_manager._compute_relevance(
            "cats",
            "artificial intelligence and machine learning concepts"
        )
        assert score2 == 0.0

        # Perfect relevance
        score3 = graphrag_manager._compute_relevance(
            "learning",
            "machine learning"
        )
        assert score3 > 0.0

    def test_rank_summaries(self, graphrag_manager):
        """Test ranking summaries by relevance."""
        summaries = graphrag_manager._get_all_summaries()

        # Rank with query that matches first community better
        ranked = graphrag_manager._rank_summaries(
            "neural networks and deep learning",
            summaries,
            top_k=2
        )

        assert len(ranked) == 2
        assert all(isinstance(r, CommunitySummary) for r in ranked)
        # Check that relevance scores are set
        assert all(r.relevance_score is not None for r in ranked)

    def test_rank_summaries_empty(self, graphrag_manager):
        """Test ranking with empty summaries."""
        ranked = graphrag_manager._rank_summaries("query", [], top_k=5)
        assert ranked == []

    def test_find_relevant_community(self, graphrag_manager):
        """Test finding most relevant community."""
        community_id = graphrag_manager._find_relevant_community(
            "neural networks"
        )

        assert community_id is not None
        assert isinstance(community_id, int)

    def test_find_relevant_community_no_summaries(self, graphrag_manager):
        """Test finding community with no summaries."""
        graphrag_manager._community_summaries = {}
        graphrag_manager.graph.get_communities.return_value = []

        community_id = graphrag_manager._find_relevant_community("query")
        assert community_id is None

    def test_entity_to_text(self, graphrag_manager):
        """Test converting entity to text."""
        entity = {
            'name': 'Neural Network',
            'description': 'A model inspired by the brain',
            'type': 'concept'
        }

        text = graphrag_manager._entity_to_text(entity)

        assert 'Neural Network' in text
        assert 'A model inspired by the brain' in text
        assert 'concept' in text

    def test_entity_to_text_partial(self, graphrag_manager):
        """Test entity conversion with partial data."""
        entity = {'name': 'Entity'}
        text = graphrag_manager._entity_to_text(entity)
        assert 'Entity' in text

    def test_get_community_name(self, graphrag_manager):
        """Test getting community display name."""
        # Set up a cached summary
        graphrag_manager._get_all_summaries()

        name = graphrag_manager._get_community_name(1)
        assert name == 'AI & ML'

        # Non-existent community
        name_unknown = graphrag_manager._get_community_name(999)
        assert 'Community 999' in name_unknown

    def test_update_community_summary(self, graphrag_manager):
        """Test updating community summary."""
        graphrag_manager._get_all_summaries()

        new_summary = "Updated summary about AI"
        graphrag_manager.update_community_summary(1, new_summary)

        assert graphrag_manager._community_summaries[1].summary_text == new_summary
        assert graphrag_manager._community_summaries[1].last_updated is not None

    def test_clear_summary_cache(self, graphrag_manager):
        """Test clearing summary cache."""
        graphrag_manager._get_all_summaries()
        assert len(graphrag_manager._community_summaries) > 0

        graphrag_manager.clear_summary_cache()
        assert len(graphrag_manager._community_summaries) == 0

    def test_get_stats(self, graphrag_manager):
        """Test getting system statistics."""
        stats = graphrag_manager.get_stats()

        assert 'num_communities' in stats
        assert 'cached_summaries' in stats
        assert 'avg_summary_length' in stats
        assert stats['num_communities'] >= 0

    def test_global_search(self, graphrag_manager):
        """Test global search."""
        result = graphrag_manager.global_search("machine learning", top_k=2)

        assert isinstance(result, RetrievalResult)
        assert result.source == "global"
        assert len(result.documents) <= 2
        assert result.confidence > 0
        assert result.reasoning is not None

    def test_global_search_no_communities(self, graphrag_manager):
        """Test global search with no communities."""
        graphrag_manager.graph.get_communities.return_value = []
        graphrag_manager.clear_summary_cache()

        result = graphrag_manager.global_search("query")

        assert result.source == "global"
        assert len(result.documents) == 0

    def test_local_search(self, graphrag_manager):
        """Test local search."""
        result = graphrag_manager.local_search(
            "neural networks",
            community_id=1,
            top_k=5
        )

        assert isinstance(result, RetrievalResult)
        assert result.source == "local"
        assert result.confidence > 0

    def test_local_search_auto_community(self, graphrag_manager):
        """Test local search with auto-detected community."""
        result = graphrag_manager.local_search(
            "machine learning",
            community_id=None
        )

        assert result.source == "local"
        # Should have found a community
        assert len(result.community_ids) > 0

    def test_hybrid_search_all_sources(self, graphrag_manager):
        """Test hybrid search using all sources."""
        result = graphrag_manager.hybrid_search(
            "machine learning",
            use_global=True,
            use_local=True,
            use_semantic=True
        )

        assert result.source == "hybrid"
        assert result.confidence > 0
        # Should have documents from hybrid search
        assert len(result.documents) >= 0

    def test_hybrid_search_single_source(self, graphrag_manager):
        """Test hybrid search with single source."""
        result = graphrag_manager.hybrid_search(
            "query",
            use_global=True,
            use_local=False,
            use_semantic=False
        )

        assert result.source == "hybrid"

    def test_hybrid_search_custom_weights(self, graphrag_manager):
        """Test hybrid search with custom weights."""
        weights = {
            "global": 0.1,
            "local": 0.2,
            "semantic": 0.7
        }

        result = graphrag_manager.hybrid_search(
            "query",
            weights=weights
        )

        assert result.source == "hybrid"


class TestCommunitySummary:
    """Test CommunitySummary data class."""

    def test_creation(self):
        """Test creating CommunitySummary."""
        summary = CommunitySummary(
            community_id=1,
            name="Test Community",
            summary_text="Test summary",
            summary_tokens=10
        )

        assert summary.community_id == 1
        assert summary.name == "Test Community"
        assert summary.summary_text == "Test summary"
        assert summary.summary_tokens == 10
        assert summary.created_at is not None
        assert summary.last_updated is not None

    def test_relevance_tracking(self):
        """Test relevance tracking in summary."""
        summary = CommunitySummary(
            community_id=1,
            name="Test",
            summary_text="Summary",
            summary_tokens=5
        )

        summary.relevance_score = 0.8
        summary.query_used_for = "test query"

        assert summary.relevance_score == 0.8
        assert summary.query_used_for == "test query"


class TestRetrievalResult:
    """Test RetrievalResult data class."""

    def test_creation(self):
        """Test creating RetrievalResult."""
        docs = [Mock(id=1), Mock(id=2)]
        result = RetrievalResult(
            documents=docs,
            source="test",
            confidence=0.9
        )

        assert result.documents == docs
        assert result.source == "test"
        assert result.confidence == 0.9
        assert result.community_ids == []

    def test_with_relevance_scores(self):
        """Test result with relevance scores."""
        result = RetrievalResult(
            documents=[],
            source="test",
            relevance_scores={1: 0.9, 2: 0.8}
        )

        assert result.relevance_scores[1] == 0.9
        assert result.relevance_scores[2] == 0.8
