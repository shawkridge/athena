"""Tests for LLM reranker."""

import pytest

from athena.core.models import Memory, MemorySearchResult, MemoryType
from athena.rag.llm_client import LLMClient
from athena.rag.reranker import (
    LLMReranker,
    RerankerConfig,
    analyze_reranking_impact,
)


class MockLLMClient(LLMClient):
    """Mock LLM that returns predictable scores."""

    def __init__(self, scores: dict[str, float] = None):
        """Initialize with predefined scores."""
        self.scores = scores or {}
        self.score_calls = []

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        return "Mock response"

    def score_relevance(self, query: str, document: str) -> float:
        """Return predefined score or default."""
        self.score_calls.append((query, document))
        # Use document content as key
        return self.scores.get(document, 0.5)


def create_mock_result(memory_id: int, content: str, similarity: float) -> MemorySearchResult:
    """Create mock search result."""
    memory = Memory(
        id=memory_id,
        project_id=1,
        content=content,
        memory_type=MemoryType.FACT,
        tags=[],
        embedding=[0.0] * 768,  # Mock embedding
    )
    return MemorySearchResult(memory=memory, similarity=similarity, rank=memory_id)


def test_reranker_basic():
    """Test basic reranking functionality."""
    # Create mock results
    results = [
        create_mock_result(1, "doc1", 0.9),
        create_mock_result(2, "doc2", 0.8),
        create_mock_result(3, "doc3", 0.7),
    ]

    # Mock LLM gives different scores (reverses order)
    mock_llm = MockLLMClient(scores={"doc1": 0.3, "doc2": 0.6, "doc3": 0.9})

    reranker = LLMReranker(mock_llm)
    reranked = reranker.rerank("test query", results, k=3)

    # Check LLM was called for each result
    assert len(mock_llm.score_calls) == 3

    # Check reranking changed order (doc3 should be first now)
    assert reranked[0].memory.id == 3  # Highest LLM score
    assert reranked[1].memory.id == 2
    assert reranked[2].memory.id == 1  # Lowest LLM score

    # Check ranks updated
    assert reranked[0].rank == 1
    assert reranked[1].rank == 2
    assert reranked[2].rank == 3


def test_reranker_weights():
    """Test weight combination."""
    results = [create_mock_result(1, "doc1", 0.9)]

    mock_llm = MockLLMClient(scores={"doc1": 0.5})

    reranker = LLMReranker(mock_llm)
    reranked = reranker.rerank(
        "test", results, k=1, llm_weight=0.7, vector_weight=0.3
    )

    # Expected score: 0.7 * 0.5 + 0.3 * 0.9 = 0.35 + 0.27 = 0.62
    expected_score = 0.7 * 0.5 + 0.3 * 0.9
    assert abs(reranked[0].similarity - expected_score) < 0.01


def test_reranker_metadata():
    """Test metadata is stored correctly."""
    results = [create_mock_result(1, "doc1", 0.8)]
    mock_llm = MockLLMClient(scores={"doc1": 0.6})

    reranker = LLMReranker(mock_llm)
    reranked = reranker.rerank("test", results, k=1)

    # Check metadata
    assert reranked[0].metadata is not None
    assert reranked[0].metadata["reranking_applied"] is True
    assert reranked[0].metadata["llm_score"] == 0.6
    assert reranked[0].metadata["vector_similarity"] == 0.8
    assert "final_score" in reranked[0].metadata


def test_reranker_empty_candidates():
    """Test reranker handles empty input."""
    mock_llm = MockLLMClient()
    reranker = LLMReranker(mock_llm)

    reranked = reranker.rerank("test", [], k=5)
    assert len(reranked) == 0


def test_reranker_k_limit():
    """Test reranker returns at most k results."""
    results = [create_mock_result(i, f"doc{i}", 0.5) for i in range(10)]
    mock_llm = MockLLMClient()

    reranker = LLMReranker(mock_llm)
    reranked = reranker.rerank("test", results, k=3)

    assert len(reranked) == 3


def test_reranker_invalid_weights():
    """Test reranker validates weights."""
    mock_llm = MockLLMClient()
    reranker = LLMReranker(mock_llm)
    results = [create_mock_result(1, "doc1", 0.8)]

    with pytest.raises(ValueError, match="Weights must be between 0 and 1"):
        reranker.rerank("test", results, k=1, llm_weight=1.5)


def test_reranker_weight_normalization(caplog):
    """Test reranker normalizes weights that don't sum to 1."""
    mock_llm = MockLLMClient(scores={"doc1": 0.5})
    reranker = LLMReranker(mock_llm)
    results = [create_mock_result(1, "doc1", 0.9)]

    # Weights sum to 0.8, should be normalized
    reranked = reranker.rerank("test", results, k=1, llm_weight=0.5, vector_weight=0.3)

    assert "Normalizing" in caplog.text
    # Result should still be computed correctly
    assert len(reranked) == 1


def test_reranker_error_fallback():
    """Test reranker handles LLM errors gracefully."""

    class FailingLLM(LLMClient):
        def generate(self, prompt, max_tokens=500, temperature=0.7):
            return "test"

        def score_relevance(self, query, document):
            raise Exception("LLM error")

    reranker = LLMReranker(FailingLLM())
    results = [create_mock_result(1, "doc1", 0.8)]

    # Should not crash, should fall back to vector similarity
    reranked = reranker.rerank("test", results, k=1)
    assert len(reranked) == 1
    assert reranked[0].similarity == 0.8  # Falls back to vector score


def test_analyze_reranking_impact():
    """Test reranking impact analysis."""
    original = [
        create_mock_result(1, "doc1", 0.9),
        create_mock_result(2, "doc2", 0.8),
        create_mock_result(3, "doc3", 0.7),
    ]

    # Simulate reranking that changes order
    reranked = [
        create_mock_result(3, "doc3", 0.95),
        create_mock_result(1, "doc1", 0.85),
        create_mock_result(2, "doc2", 0.75),
    ]
    reranked[0].rank = 1
    reranked[1].rank = 2
    reranked[2].rank = 3

    impact = analyze_reranking_impact(original, reranked)

    assert impact["total_candidates"] == 3
    assert impact["avg_rank_change"] > 0  # Order changed
    assert impact["max_rank_change"] == 2  # doc3 moved from rank 3 to 1
    assert impact["top_3_overlap"] == 1.0  # All 3 docs still in top 3, just reordered


def test_reranker_config():
    """Test reranker configuration."""
    config = RerankerConfig(llm_weight=0.8, vector_weight=0.2)

    assert config.llm_weight == 0.8
    assert config.vector_weight == 0.2
    assert config.enabled is True


def test_reranker_config_invalid_option(caplog):
    """Test config warns on invalid options."""
    config = RerankerConfig(invalid_option=True)

    assert "Unknown reranker config option" in caplog.text


def test_reranker_batch():
    """Test batch reranking."""
    mock_llm = MockLLMClient()
    reranker = LLMReranker(mock_llm)

    queries = ["query1", "query2"]
    candidates_list = [
        [create_mock_result(1, "doc1", 0.8)],
        [create_mock_result(2, "doc2", 0.7)],
    ]

    results = reranker.rerank_batch(queries, candidates_list, k=1)

    assert len(results) == 2
    assert len(results[0]) == 1
    assert len(results[1]) == 1


def test_reranker_batch_length_mismatch():
    """Test batch reranking validates input lengths."""
    mock_llm = MockLLMClient()
    reranker = LLMReranker(mock_llm)

    with pytest.raises(ValueError, match="Number of queries must match"):
        reranker.rerank_batch(["q1"], [[], []], k=1)
