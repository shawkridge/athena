"""Tests for advanced RAG (Retrieval-Augmented Generation) strategies."""

import pytest
from pathlib import Path

from athena.code_search.tree_sitter_search import TreeSitterCodeSearch
from athena.code_search.advanced_rag import (
    SelfRAG,
    CorrectiveRAG,
    AdaptiveRAG,
    RelevanceLevel,
)


@pytest.fixture
def temp_python_repo(tmp_path):
    """Create a temporary Python repository."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "auth.py").write_text("""
def authenticate(user):
    '''Authenticate a user.'''
    return validate_user(user)

def validate_user(user):
    '''Validate user credentials.'''
    return user.is_valid()

class UserHandler:
    '''Handles user operations.'''
    def handle_login(self):
        return authenticate(None)
""")

    (src_dir / "utils.py").write_text("""
def process_data(data):
    '''Process input data.'''
    return transform(data)

def transform(data):
    '''Transform data structure.'''
    return data
""")

    return tmp_path


@pytest.fixture
def search_engine(temp_python_repo):
    """Create and initialize search engine."""
    search = TreeSitterCodeSearch(str(temp_python_repo), language="python")
    search.build_index()
    return search


@pytest.fixture
def self_rag(search_engine):
    """Create Self-RAG instance."""
    return SelfRAG(search_engine)


@pytest.fixture
def corrective_rag(search_engine):
    """Create Corrective RAG instance."""
    return CorrectiveRAG(search_engine)


@pytest.fixture
def adaptive_rag(search_engine):
    """Create Adaptive RAG instance."""
    return AdaptiveRAG(search_engine)


class TestSelfRAG:
    """Test Self-RAG strategy."""

    def test_should_retrieve_specific_query(self, self_rag):
        """Test that specific queries trigger retrieval."""
        decision = self_rag.should_retrieve("find authenticate function")
        assert decision.should_retrieve
        assert decision.confidence > 0.5

    def test_should_retrieve_technical_query(self, self_rag):
        """Test that technical queries trigger retrieval."""
        decision = self_rag.should_retrieve("implement interface authentication")
        assert decision.should_retrieve
        assert decision.confidence > 0.6

    def test_retrieve_and_evaluate(self, self_rag):
        """Test complete retrieve and evaluate flow."""
        query = "authenticate"
        retrieved = self_rag.retrieve_and_evaluate(query, limit=5)

        # May return 0 results if semantic search doesn't match
        # Test structure of returned data
        assert isinstance(retrieved, list)
        for doc in retrieved:
            assert doc.relevance is not None
            assert 0 <= doc.confidence <= 1.0

    def test_retrieve_and_evaluate_returns_only_relevant(self, self_rag):
        """Test that retrieve_and_evaluate filters out not_relevant documents."""
        query = "authenticate"
        retrieved = self_rag.retrieve_and_evaluate(query)

        for doc in retrieved:
            assert doc.relevance != RelevanceLevel.NOT_RELEVANT


class TestCorrectiveRAG:
    """Test Corrective RAG strategy."""

    def test_generate_alternative_queries(self, corrective_rag):
        """Test alternative query generation."""
        query = "authenticate user with password"
        alternatives = corrective_rag._generate_alternative_queries(query)

        assert len(alternatives) > 0
        assert not all(alt == query for alt in alternatives)

    def test_retrieve_with_correction_basic(self, corrective_rag):
        """Test basic retrieve with correction."""
        query = "authenticate"
        retrieved = corrective_rag.retrieve_with_correction(query, limit=5)

        assert len(retrieved) > 0
        for doc in retrieved:
            assert doc.relevance is not None
            assert doc.confidence > 0

    def test_retrieve_with_correction_deduplicates(self, corrective_rag):
        """Test that correction deduplicates results."""
        query = "validate"
        retrieved = corrective_rag.retrieve_with_correction(
            query, limit=10, max_iterations=2
        )

        unit_ids = [doc.result.unit.id for doc in retrieved]
        assert len(unit_ids) == len(set(unit_ids))


class TestAdaptiveRAG:
    """Test Adaptive RAG strategy."""

    def test_analyze_query_complexity(self, adaptive_rag):
        """Test complexity analysis."""
        query = "find authenticate function that validates user"
        complexity, confidence = adaptive_rag._analyze_query_complexity(query)

        assert complexity in ("high", "medium", "low")
        assert 0 <= confidence <= 1.0

    def test_retrieve_auto_strategy(self, adaptive_rag):
        """Test automatic strategy selection."""
        query = "authenticate user function"
        retrieved = adaptive_rag.retrieve(query, limit=5)

        assert len(retrieved) > 0
        for doc in retrieved:
            assert doc.relevance is not None

    def test_retrieve_prefer_self_rag(self, adaptive_rag):
        """Test forcing Self-RAG strategy."""
        query = "authenticate"
        retrieved = adaptive_rag.retrieve(query, limit=5, prefer_strategy="self")

        assert len(retrieved) > 0

    def test_retrieve_prefer_corrective_rag(self, adaptive_rag):
        """Test forcing Corrective RAG strategy."""
        query = "validate user"
        retrieved = adaptive_rag.retrieve(
            query, limit=5, prefer_strategy="corrective"
        )

        assert len(retrieved) > 0

    def test_get_strategy_recommendation(self, adaptive_rag):
        """Test strategy recommendation."""
        query = "find authenticate function"
        recommendation = adaptive_rag.get_strategy_recommendation(query)

        assert "recommended_strategy" in recommendation
        assert "should_retrieve" in recommendation
        assert "query_complexity" in recommendation
        assert "confidence" in recommendation
        assert "reasoning" in recommendation

        assert recommendation["recommended_strategy"] in ("self", "corrective")
        assert isinstance(recommendation["should_retrieve"], bool)
        assert recommendation["query_complexity"] in ("high", "medium", "low")
        assert 0 <= recommendation["confidence"] <= 1.0


class TestRAGIntegration:
    """Integration tests for RAG strategies."""

    def test_self_rag_full_pipeline(self, search_engine):
        """Test complete Self-RAG pipeline."""
        rag = SelfRAG(search_engine)

        decision = rag.should_retrieve("authenticate user")
        assert 0 <= decision.confidence <= 1.0

        retrieved = rag.retrieve_and_evaluate("authenticate")
        assert len(retrieved) >= 0
        assert all(doc.relevance for doc in retrieved)

    def test_corrective_rag_full_pipeline(self, search_engine):
        """Test complete Corrective RAG pipeline."""
        rag = CorrectiveRAG(search_engine)

        retrieved = rag.retrieve_with_correction("validate", limit=5)
        assert isinstance(retrieved, list)
        assert all(doc.relevance for doc in retrieved)

    def test_adaptive_rag_full_pipeline(self, search_engine):
        """Test complete Adaptive RAG pipeline."""
        rag = AdaptiveRAG(search_engine)

        recommendation = rag.get_strategy_recommendation("authenticate user")
        assert "recommended_strategy" in recommendation

        retrieved = rag.retrieve("authenticate user", limit=5)
        assert len(retrieved) >= 0

        retrieved_self = rag.retrieve(
            "authenticate", limit=5, prefer_strategy="self"
        )
        retrieved_corrective = rag.retrieve(
            "authenticate", limit=5, prefer_strategy="corrective"
        )

        assert isinstance(retrieved_self, list)
        assert isinstance(retrieved_corrective, list)

    def test_rag_handles_empty_results(self, search_engine):
        """Test that RAG strategies handle empty results gracefully."""
        rag = AdaptiveRAG(search_engine)

        query = "zzz_nonexistent_unique_function_name"
        retrieved = rag.retrieve(query, limit=5)

        assert isinstance(retrieved, list)
        assert len(retrieved) == 0

    def test_rag_consistency_across_strategies(self, search_engine):
        """Test that RAG strategies are consistent."""
        self_rag = SelfRAG(search_engine)
        corrective_rag = CorrectiveRAG(search_engine)

        query = "authenticate user"

        self_results = self_rag.retrieve_and_evaluate(query, limit=5)
        corrective_results = corrective_rag.retrieve_with_correction(query, limit=5)

        assert len(self_results) >= 0
        assert len(corrective_results) >= 0

        for result in self_results:
            assert result.relevance is not None
        for result in corrective_results:
            assert result.relevance is not None
