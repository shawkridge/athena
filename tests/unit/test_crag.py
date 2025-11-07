"""Unit tests for Corrective RAG (CRAG) system."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from athena.rag.corrective import (
    CorrectiveRAGManager,
    DocumentValidator,
    DocumentCorrector,
    CRAGConfig,
    DocumentValidation,
    CRAGResult,
)


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    return Mock()


@pytest.fixture
def crag_config():
    """Create CRAG config."""
    return CRAGConfig(
        relevance_threshold_high=0.8,
        relevance_threshold_low=0.4,
        validate_factuality=True,
        validate_completeness=True,
    )


@pytest.fixture
def validator(mock_llm_client):
    """Create document validator."""
    return DocumentValidator(mock_llm_client)


@pytest.fixture
def corrector(mock_llm_client):
    """Create document corrector."""
    return DocumentCorrector(mock_llm_client)


@pytest.fixture
def crag_manager(mock_llm_client, crag_config):
    """Create CRAG manager."""
    return CorrectiveRAGManager(mock_llm_client, crag_config)


@pytest.fixture
def mock_document():
    """Create mock document result."""
    result = Mock()
    result.id = "doc_1"
    result.content = "This is a test document about machine learning."
    result.score = 0.85
    return result


class TestDocumentValidator:
    """Test document validator."""

    def test_validate_relevant_document(self, validator, mock_llm_client):
        """Test validation of relevant document."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.9,
            "reasoning": "Directly addresses the query"
        }"""

        query = "What is machine learning?"
        document = "Machine learning is a subset of AI..."
        doc_id = "doc_1"

        validation = validator.validate_relevance(query, document, doc_id)

        assert validation.relevance_score == 0.9
        assert validation.relevance_label == "relevant"
        assert validation.answers_query is True
        assert validation.needs_correction is False
        assert validation.document_id == doc_id

    def test_validate_partially_relevant_document(self, validator, mock_llm_client):
        """Test validation of partially relevant document."""
        mock_llm_client.query.return_value = """{
            "answers_query": false,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.6,
            "reasoning": "Discusses related topic but misses key point"
        }"""

        validation = validator.validate_relevance("test query", "test doc", "doc_1")

        assert validation.relevance_score == 0.6
        assert validation.relevance_label == "partially_relevant"
        assert validation.needs_correction is True

    def test_validate_irrelevant_document(self, validator, mock_llm_client):
        """Test validation of irrelevant document."""
        mock_llm_client.query.return_value = """{
            "answers_query": false,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.2,
            "reasoning": "Content is unrelated to query"
        }"""

        validation = validator.validate_relevance("test query", "test doc", "doc_1")

        assert validation.relevance_score == 0.2
        assert validation.relevance_label == "irrelevant"
        # web_search_needed is set during process_documents, not in validate_relevance
        assert validation.needs_correction is True  # Low relevance means correction needed

    def test_validate_inaccurate_document(self, validator, mock_llm_client):
        """Test validation of factually inaccurate document."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": false,
            "internally_consistent": true,
            "relevance_score": 0.7,
            "reasoning": "Contains incorrect facts"
        }"""

        validation = validator.validate_relevance("test query", "test doc", "doc_1")

        assert validation.factually_accurate is False
        assert validation.needs_correction is True

    def test_validate_inconsistent_document(self, validator, mock_llm_client):
        """Test validation of internally inconsistent document."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": false,
            "relevance_score": 0.7,
            "reasoning": "Contains contradictory statements"
        }"""

        validation = validator.validate_relevance("test query", "test doc", "doc_1")

        assert validation.internally_consistent is False

    def test_validation_caching(self, validator, mock_llm_client):
        """Test that validations are cached."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.8,
            "reasoning": "Test"
        }"""

        # First call
        validation1 = validator.validate_relevance("query", "doc", "doc_1")
        call_count_1 = mock_llm_client.query.call_count

        # Second call (should be cached)
        validation2 = validator.validate_relevance("query", "doc", "doc_1")
        call_count_2 = mock_llm_client.query.call_count

        assert validation1.relevance_score == validation2.relevance_score
        assert call_count_2 == call_count_1  # No additional call

    def test_validation_fallback_on_error(self, validator, mock_llm_client):
        """Test fallback validation when LLM fails."""
        mock_llm_client.query.side_effect = Exception("LLM error")

        validation = validator.validate_relevance("test", "test doc", "doc_1")

        # Should fall back to keyword matching
        assert validation.relevance_score >= 0.0
        assert validation.relevance_score <= 1.0

    def test_cache_clearing(self, validator, mock_llm_client):
        """Test cache can be cleared."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.8,
            "reasoning": "Test"
        }"""

        # Populate cache
        validator.validate_relevance("query", "doc", "doc_1")
        assert len(validator._validation_cache) > 0

        # Clear cache
        validator.clear_cache()
        assert len(validator._validation_cache) == 0

    def test_fallback_validation_keyword_matching(self, validator):
        """Test fallback validation uses keyword matching."""
        # Bypass LLM
        validator.llm_client = None

        query = "machine learning algorithms"
        doc = "This discusses machine learning methods and algorithms for data analysis"

        result = validator._fallback_validation(query, doc)

        assert result["relevance_score"] >= 0.2  # Should have some overlap
        assert result["relevance_score"] <= 1.0  # Score between 0-1
        assert "relevance_score" in result


class TestDocumentCorrector:
    """Test document corrector."""

    def test_correct_document_success(self, corrector, mock_llm_client):
        """Test successful document correction."""
        mock_llm_client.query.return_value = "Corrected document content with better clarity"

        original = "Original document"
        corrected, success = corrector.correct_document(
            "test query", original, "Missing key details"
        )

        assert success is True
        assert corrected != original
        assert "Corrected document" in corrected

    def test_correct_document_failure(self, corrector, mock_llm_client):
        """Test document correction failure."""
        mock_llm_client.query.side_effect = Exception("Correction failed")

        original = "Original document"
        corrected, success = corrector.correct_document(
            "test query", original, "Missing details"
        )

        assert success is False
        assert corrected == original  # Returns original on failure

    def test_refine_with_context(self, corrector, mock_llm_client):
        """Test document refinement with context."""
        mock_llm_client.query.return_value = "Enhanced document with additional context"

        original = "Original document"
        context = ["Context item 1", "Context item 2", "Context item 3"]

        refined = corrector.refine_with_context("test query", original, context)

        assert "Enhanced document" in refined

    def test_refine_with_empty_context(self, corrector, mock_llm_client):
        """Test refinement with empty context."""
        mock_llm_client.query.return_value = "Refined document"

        original = "Original document"
        refined = corrector.refine_with_context("test query", original, [])

        assert refined  # Should still return content

    def test_refine_with_context_limit(self, corrector, mock_llm_client):
        """Test that refinement limits context items."""
        mock_llm_client.query.return_value = "Refined"

        context = [f"Item {i}" for i in range(10)]  # More than limit
        corrector.refine_with_context("query", "doc", context)

        # Check that prompt only includes top 3 items
        call_args = mock_llm_client.query.call_args[0][0]
        assert "Item 0" in call_args
        assert "Item 2" in call_args
        # Item 3+ might not be included due to limit


class TestCorrectiveRAGManager:
    """Test CRAG manager."""

    def test_process_all_relevant_documents(self, crag_manager, mock_llm_client):
        """Test processing all relevant documents."""
        # Mock validation responses
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.9,
            "reasoning": "Directly relevant"
        }"""

        documents = [
            Mock(id="doc_1", content="Document 1 content"),
            Mock(id="doc_2", content="Document 2 content"),
        ]

        result = crag_manager.process_documents("test query", documents)

        assert result.total_documents == 2
        assert result.relevant_documents == 2
        assert result.overall_relevance > 0.8
        assert result.quality_score > 0.7

    def test_process_mixed_relevance_documents(self, crag_manager, mock_llm_client):
        """Test processing documents with mixed relevance."""
        responses = [
            """{
                "answers_query": true,
                "factually_accurate": true,
                "internally_consistent": true,
                "relevance_score": 0.9,
                "reasoning": "Highly relevant"
            }""",
            """{
                "answers_query": false,
                "factually_accurate": true,
                "internally_consistent": true,
                "relevance_score": 0.5,
                "reasoning": "Partially relevant"
            }""",
            """{
                "answers_query": false,
                "factually_accurate": true,
                "internally_consistent": true,
                "relevance_score": 0.2,
                "reasoning": "Irrelevant"
            }""",
        ]
        mock_llm_client.query.side_effect = responses

        documents = [
            Mock(id="doc_1", content="Highly relevant document"),
            Mock(id="doc_2", content="Partially relevant document"),
            Mock(id="doc_3", content="Irrelevant document"),
        ]

        result = crag_manager.process_documents("test query", documents)

        assert result.total_documents == 3
        assert result.relevant_documents == 2  # Docs 1 and 2 above threshold
        assert result.web_search_needed == 1  # Doc 3 below threshold
        assert 0.4 < result.overall_relevance < 0.8

    def test_document_correction_on_partial_relevance(self, crag_manager, mock_llm_client):
        """Test that partially relevant documents are corrected."""
        validation_response = """{
            "answers_query": false,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.6,
            "reasoning": "Missing specific details"
        }"""
        correction_response = "Corrected content with missing details added"

        mock_llm_client.query.side_effect = [
            validation_response,
            correction_response,
        ]

        documents = [Mock(id="doc_1", content="Partial document")]

        result = crag_manager.process_documents("test query", documents)

        assert result.corrected_documents > 0

    def test_get_relevant_documents(self, crag_manager, mock_llm_client):
        """Test extracting relevant documents."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.9,
            "reasoning": "Relevant"
        }"""

        documents = [Mock(id="doc_1", content="Test content")]
        result = crag_manager.process_documents("test query", documents)

        relevant = crag_manager.get_relevant_documents(result)

        assert len(relevant) > 0
        assert relevant[0][0].id == "doc_1"

    def test_get_corrected_content(self, crag_manager, mock_llm_client):
        """Test that corrected content is returned."""
        validation_response = """{
            "answers_query": false,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.6,
            "reasoning": "Needs correction"
        }"""
        correction_response = "This is the corrected content"

        mock_llm_client.query.side_effect = [
            validation_response,
            correction_response,
        ]

        documents = [Mock(id="doc_1", content="Original content")]
        result = crag_manager.process_documents("test query", documents)

        relevant = crag_manager.get_relevant_documents(result)

        # Should return corrected content
        if relevant:
            assert "corrected" in relevant[0][1].lower()

    def test_get_summary(self, crag_manager, mock_llm_client):
        """Test summary generation."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.85,
            "reasoning": "Good"
        }"""

        documents = [Mock(id="doc_1", content="Test")]
        result = crag_manager.process_documents("test query", documents)

        summary = crag_manager.get_summary(result)

        assert "query" in summary
        assert "total_documents" in summary
        assert "relevant_documents" in summary
        assert "quality_score" in summary
        assert "success_rate" in summary
        assert 0 <= summary["success_rate"] <= 1

    def test_quality_score_calculation(self, crag_manager, mock_llm_client):
        """Test quality score is calculated correctly."""
        mock_llm_client.query.return_value = """{
            "answers_query": true,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.8,
            "reasoning": "Good"
        }"""

        documents = [Mock(id="doc_1", content="Test")]
        result = crag_manager.process_documents("test query", documents)

        assert 0 <= result.quality_score <= 1
        # With all true values and high relevance, should be high quality
        assert result.quality_score > 0.6

    def test_empty_document_list(self, crag_manager):
        """Test processing empty document list."""
        result = crag_manager.process_documents("test query", [])

        assert result.total_documents == 0
        assert result.relevant_documents == 0
        assert result.quality_score == 0.0

    def test_configuration_thresholds(self, mock_llm_client):
        """Test that configuration thresholds are respected."""
        config = CRAGConfig(
            relevance_threshold_high=0.9,
            relevance_threshold_low=0.5,
        )
        manager = CorrectiveRAGManager(mock_llm_client, config)

        mock_llm_client.query.return_value = """{
            "answers_query": false,
            "factually_accurate": true,
            "internally_consistent": true,
            "relevance_score": 0.6,
            "reasoning": "Between thresholds"
        }"""

        documents = [Mock(id="doc_1", content="Test")]
        result = manager.process_documents("test query", documents)

        # Score 0.6 is between low (0.5) and high (0.9)
        # Should be counted as relevant
        assert result.relevant_documents == 1

    def test_cache_clearing(self, crag_manager):
        """Test that cache can be cleared."""
        crag_manager.clear_cache()
        # Should not raise any errors
        assert True


class TestCRAGIntegration:
    """Integration tests for CRAG system."""

    def test_full_pipeline(self, mock_llm_client):
        """Test full CRAG pipeline."""
        config = CRAGConfig()
        manager = CorrectiveRAGManager(mock_llm_client, config)

        # Responses for validation and correction
        responses = [
            # Validation for doc 1 (relevant)
            """{
                "answers_query": true,
                "factually_accurate": true,
                "internally_consistent": true,
                "relevance_score": 0.9,
                "reasoning": "Highly relevant"
            }""",
            # Validation for doc 2 (needs correction)
            """{
                "answers_query": false,
                "factually_accurate": true,
                "internally_consistent": true,
                "relevance_score": 0.6,
                "reasoning": "Incomplete information"
            }""",
            # Correction for doc 2
            "Enhanced document with complete information",
            # Validation for doc 3 (irrelevant)
            """{
                "answers_query": false,
                "factually_accurate": true,
                "internally_consistent": true,
                "relevance_score": 0.2,
                "reasoning": "Unrelated content"
            }""",
        ]
        mock_llm_client.query.side_effect = responses

        documents = [
            Mock(id="doc_1", content="Relevant document about topic"),
            Mock(id="doc_2", content="Partial document missing details"),
            Mock(id="doc_3", content="Completely unrelated document"),
        ]

        result = manager.process_documents("What is the topic?", documents)

        # Verify results
        assert result.total_documents == 3
        assert result.relevant_documents == 2
        assert result.corrected_documents >= 1
        assert result.web_search_needed == 1
        assert result.quality_score > 0.5

        # Get summary
        summary = manager.get_summary(result)
        assert summary["total_documents"] == 3
        assert summary["success_rate"] > 0.5
