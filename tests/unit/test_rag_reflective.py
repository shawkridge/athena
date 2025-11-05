"""Tests for self-reflective RAG."""

import pytest

from athena.core.models import Memory, MemorySearchResult, MemoryType
from athena.memory.search import SemanticSearch
from athena.rag.llm_client import LLMClient
from athena.rag.reflective import (
    ReflectiveRAG,
    ReflectiveRAGConfig,
    get_iteration_metrics,
)


class MockLLMClient(LLMClient):
    """Mock LLM with configurable responses."""

    def __init__(self, critique_responses: list[str] = None, refine_response: str = "refined query"):
        self.critique_responses = critique_responses or []
        self.refine_response = refine_response
        self.critique_call_count = 0
        self.refine_call_count = 0
        self.generate_calls = []

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        self.generate_calls.append(prompt)

        # Determine if this is a critique or refine call based on prompt content
        if "Evaluate whether" in prompt or "Retrieved documents" in prompt:
            # Critique call
            if self.critique_call_count < len(self.critique_responses):
                response = self.critique_responses[self.critique_call_count]
                self.critique_call_count += 1
                return response
            return "ANSWERS: no\nCONFIDENCE: 0.5\nMISSING: none"

        elif "Refine the query" in prompt or "refined query" in prompt.lower():
            # Refine call
            self.refine_call_count += 1
            return self.refine_response

        return "mock response"

    def score_relevance(self, query: str, document: str) -> float:
        return 0.5


class MockSearch:
    """Mock semantic search."""

    def __init__(self, results: list[list[MemorySearchResult]] = None):
        self.results = results or []
        self.call_count = 0
        self.recall_calls = []

    def recall(self, query, project_id, k=5, min_similarity=0.0):
        self.recall_calls.append((query, project_id, k))

        if self.call_count < len(self.results):
            results = self.results[self.call_count]
            self.call_count += 1
            return results

        return []


def create_mock_result(memory_id: int, content: str, similarity: float) -> MemorySearchResult:
    """Create mock search result."""
    memory = Memory(
        id=memory_id,
        project_id=1,
        content=content,
        memory_type=MemoryType.FACT,
        tags=[],
        embedding=[0.0] * 768,
    )
    return MemorySearchResult(memory=memory, similarity=similarity, rank=memory_id)


def test_reflective_rag_stops_on_high_confidence():
    """Test that reflective RAG stops when confidence is high."""
    # Mock: first iteration has high confidence
    critique_response = "ANSWERS: yes\nCONFIDENCE: 0.9\nMISSING: none"

    mock_llm = MockLLMClient(critique_responses=[critique_response])
    mock_search = MockSearch(
        results=[[create_mock_result(1, "doc1", 0.8), create_mock_result(2, "doc2", 0.7)]]
    )

    reflective = ReflectiveRAG(mock_search, mock_llm)
    results = reflective.retrieve("test query", project_id=1, k=2, max_iterations=3)

    # Should stop after 1 iteration
    assert mock_search.call_count == 1
    assert mock_llm.critique_call_count == 1
    assert mock_llm.refine_call_count == 0  # No refinement needed

    # Check metadata
    assert results[0].metadata["reflective_iterations"] == 1


def test_reflective_rag_refines_query():
    """Test that reflective RAG refines query when missing info."""
    # Mock: first critique says missing info, second says complete
    critiques = [
        "ANSWERS: no\nCONFIDENCE: 0.4\nMISSING: token expiry time",
        "ANSWERS: yes\nCONFIDENCE: 0.9\nMISSING: none",
    ]

    mock_llm = MockLLMClient(critique_responses=critiques, refine_response="What is JWT expiry?")
    mock_search = MockSearch(
        results=[
            [create_mock_result(1, "doc1", 0.7)],
            [create_mock_result(2, "doc2", 0.8)],
        ]
    )

    reflective = ReflectiveRAG(mock_search, mock_llm)
    results = reflective.retrieve("auth tokens", project_id=1, k=2, max_iterations=3)

    # Should do 2 iterations
    assert mock_search.call_count == 2
    assert mock_llm.critique_call_count == 2
    assert mock_llm.refine_call_count == 1

    # Check that search was called with refined query
    assert mock_search.recall_calls[1][0] == "What is JWT expiry?"

    # Check metadata
    assert results[0].metadata["reflective_iterations"] == 2


def test_reflective_rag_max_iterations():
    """Test that reflective RAG respects max iterations."""
    # Mock: always low confidence
    low_confidence = "ANSWERS: no\nCONFIDENCE: 0.3\nMISSING: more info needed"

    mock_llm = MockLLMClient(critique_responses=[low_confidence] * 5)
    mock_search = MockSearch(results=[[create_mock_result(i, f"doc{i}", 0.5)] for i in range(5)])

    reflective = ReflectiveRAG(mock_search, mock_llm)
    results = reflective.retrieve("test", project_id=1, k=2, max_iterations=3)

    # Should stop at max iterations
    assert mock_search.call_count == 3
    assert mock_llm.critique_call_count == 3

    # Check metadata
    assert results[0].metadata["reflective_iterations"] == 3


def test_reflective_rag_deduplication():
    """Test that reflective RAG deduplicates results across iterations."""
    critique = "ANSWERS: no\nCONFIDENCE: 0.5\nMISSING: more info"

    mock_llm = MockLLMClient(critique_responses=[critique, critique])
    mock_search = MockSearch(
        results=[
            [create_mock_result(1, "doc1", 0.8), create_mock_result(2, "doc2", 0.7)],
            [create_mock_result(1, "doc1", 0.9), create_mock_result(3, "doc3", 0.6)],  # doc1 duplicate
        ]
    )

    reflective = ReflectiveRAG(mock_search, mock_llm)
    results = reflective.retrieve("test", project_id=1, k=5, max_iterations=2)

    # Should have 3 unique results (doc1, doc2, doc3)
    unique_ids = {r.memory.id for r in results}
    assert len(unique_ids) == 3
    assert unique_ids == {1, 2, 3}


def test_reflective_rag_returns_top_k():
    """Test that reflective RAG returns only top-k results."""
    critique = "ANSWERS: yes\nCONFIDENCE: 0.9\nMISSING: none"

    mock_llm = MockLLMClient(critique_responses=[critique])
    mock_search = MockSearch(
        results=[[create_mock_result(i, f"doc{i}", 0.9 - i * 0.1) for i in range(10)]]
    )

    reflective = ReflectiveRAG(mock_search, mock_llm)
    results = reflective.retrieve("test", project_id=1, k=3)

    # Should return only 3 results
    assert len(results) == 3

    # Should be highest similarity (doc0, doc1, doc2)
    assert results[0].memory.id == 0
    assert results[1].memory.id == 1
    assert results[2].memory.id == 2


def test_parse_critique_response():
    """Test critique response parsing."""
    reflective = ReflectiveRAG(MockSearch(), MockLLMClient())

    # Test valid response
    response = "ANSWERS: yes\nCONFIDENCE: 0.85\nMISSING: none"
    critique = reflective._parse_critique_response(response)

    assert critique["should_stop"] is True  # yes + high confidence
    assert critique["confidence"] == 0.85
    assert critique["missing_info"] is None


def test_parse_critique_missing_info():
    """Test parsing critique with missing info."""
    reflective = ReflectiveRAG(MockSearch(), MockLLMClient())

    response = "ANSWERS: no\nCONFIDENCE: 0.4\nMISSING: JWT token expiry details"
    critique = reflective._parse_critique_response(response)

    assert critique["should_stop"] is False
    assert critique["confidence"] == 0.4
    assert critique["missing_info"] == "JWT token expiry details"


def test_parse_critique_malformed():
    """Test parsing handles malformed responses."""
    reflective = ReflectiveRAG(MockSearch(), MockLLMClient())

    # Malformed response
    response = "This is not the expected format"
    critique = reflective._parse_critique_response(response)

    # Should have fallback values
    assert isinstance(critique["confidence"], float)
    assert isinstance(critique["should_stop"], bool)


def test_reflective_rag_empty_results():
    """Test handling of empty search results."""
    critique = "ANSWERS: no\nCONFIDENCE: 0.0\nMISSING: No documents found"

    mock_llm = MockLLMClient(critique_responses=[critique])
    mock_search = MockSearch(results=[[]])  # Empty results

    reflective = ReflectiveRAG(mock_search, mock_llm)
    results = reflective.retrieve("test", project_id=1, k=5)

    # Should still return (empty)
    assert results == []


def test_reflective_rag_critique_error_fallback():
    """Test that critique errors don't crash the system."""

    class FailingLLM(LLMClient):
        def generate(self, prompt, max_tokens=500, temperature=0.7):
            raise Exception("LLM error")

        def score_relevance(self, query, document):
            return 0.5

    mock_search = MockSearch(results=[[create_mock_result(1, "doc1", 0.8)]])

    reflective = ReflectiveRAG(mock_search, FailingLLM())
    results = reflective.retrieve("test", project_id=1, k=2)

    # Should still return results from first iteration
    assert len(results) > 0


def test_reflective_rag_config():
    """Test configuration object."""
    config = ReflectiveRAGConfig(max_iterations=5, confidence_threshold=0.9)

    assert config.max_iterations == 5
    assert config.confidence_threshold == 0.9
    assert config.enabled is True


def test_reflective_rag_config_invalid_option(caplog):
    """Test config warns on invalid options."""
    config = ReflectiveRAGConfig(invalid_option=True)

    assert "Unknown reflective RAG config option" in caplog.text


def test_get_iteration_metrics():
    """Test extracting iteration metrics from results."""
    # Create result with metadata
    result = create_mock_result(1, "doc1", 0.8)
    result.metadata = {
        "reflective_iterations": 2,
        "iteration_info": [
            {"query": "query1", "confidence": 0.5},
            {"query": "query2", "confidence": 0.9},
        ],
    }

    metrics = get_iteration_metrics([result])

    assert metrics is not None
    assert metrics["total_iterations"] == 2
    assert metrics["final_confidence"] == 0.9
    assert len(metrics["queries_used"]) == 2


def test_get_iteration_metrics_no_metadata():
    """Test metrics extraction with no metadata."""
    result = create_mock_result(1, "doc1", 0.8)
    metrics = get_iteration_metrics([result])

    assert metrics is None


def test_reflective_rag_confidence_threshold():
    """Test custom confidence threshold."""
    # Mock: confidence with missing info (so it can continue iterating)
    critique_medium = "ANSWERS: no\nCONFIDENCE: 0.85\nMISSING: more details needed"

    # Test with confidence 0.85 and threshold 0.8 (should stop)
    mock_llm1 = MockLLMClient(critique_responses=[critique_medium])
    mock_search1 = MockSearch(results=[[create_mock_result(1, "doc1", 0.8)]])
    reflective1 = ReflectiveRAG(mock_search1, mock_llm1)

    results = reflective1.retrieve("test", project_id=1, k=2, confidence_threshold=0.8, max_iterations=2)
    # Should stop after 1 iteration (confidence 0.85 >= 0.8)
    assert mock_search1.call_count == 1

    # Test with confidence 0.85 but threshold 0.9 (should continue)
    mock_llm2 = MockLLMClient(critique_responses=[critique_medium, critique_medium])
    mock_search2 = MockSearch(results=[[create_mock_result(1, "doc1", 0.8)], [create_mock_result(2, "doc2", 0.7)]])
    reflective2 = ReflectiveRAG(mock_search2, mock_llm2)

    results = reflective2.retrieve("test", project_id=1, k=2, confidence_threshold=0.9, max_iterations=2)
    # Should continue to iteration 2 (confidence 0.85 < 0.9 and has missing info)
    assert mock_search2.call_count == 2


def test_refine_query_error_fallback():
    """Test query refinement falls back to original on error."""

    class FailingRefiner(LLMClient):
        def generate(self, prompt, max_tokens=500, temperature=0.7):
            if "Refine" in prompt:
                raise Exception("Refinement failed")
            return "ANSWERS: no\nCONFIDENCE: 0.3\nMISSING: info"

        def score_relevance(self, query, document):
            return 0.5

    mock_search = MockSearch(results=[[create_mock_result(1, "doc1", 0.7)]])

    reflective = ReflectiveRAG(mock_search, FailingRefiner())
    results = reflective.retrieve("original query", project_id=1, k=2, max_iterations=2)

    # Should use original query for iteration 2
    assert mock_search.recall_calls[1][0] == "original query"
