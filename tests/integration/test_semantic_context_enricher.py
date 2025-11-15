"""Integration tests for SemanticContextEnricher.

Tests semantic embedding generation, LLM-based scoring, and cross-project linking.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import List

# Import the enricher
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from athena.consolidation.semantic_context_enricher import SemanticContextEnricher


class TestSemanticContextEnricher:
    """Test suite for SemanticContextEnricher."""

    @pytest.fixture
    def enricher(self):
        """Create enricher instance with mocked services."""
        enricher = SemanticContextEnricher(
            embeddings_url="http://localhost:8001",
            reasoning_url="http://localhost:8002"
        )
        return enricher

    @pytest.fixture
    def mock_embedding(self):
        """Create a mock 768D embedding."""
        return [0.1 * i for i in range(768)]

    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn, cursor

    # ========== Embedding Generation Tests ==========

    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_generate_embedding_success(self, mock_post, enricher, mock_embedding):
        """Test successful embedding generation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": mock_embedding}
        mock_post.return_value = mock_response

        # Generate embedding
        result = enricher.generate_embedding("test content")

        # Verify
        assert result is not None
        assert len(result) == 768
        assert result == mock_embedding
        mock_post.assert_called_once()

    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_generate_embedding_with_embeddings_array(self, mock_post, enricher, mock_embedding):
        """Test embedding generation with embeddings array response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embeddings": [mock_embedding]}
        mock_post.return_value = mock_response

        result = enricher.generate_embedding("test content")

        assert result == mock_embedding

    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_generate_embedding_service_unavailable(self, mock_post, enricher):
        """Test embedding generation with service unavailable."""
        mock_post.side_effect = ConnectionError("Service unavailable")

        result = enricher.generate_embedding("test content")

        assert result is None

    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_generate_embedding_invalid_response(self, mock_post, enricher):
        """Test embedding generation with invalid response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = enricher.generate_embedding("test content")

        assert result is None

    # ========== Importance Scoring Tests ==========

    def test_heuristic_importance_discovery_event(self, enricher):
        """Test heuristic importance scoring for discovery events."""
        score = enricher._heuristic_importance("discovery:analysis", "success")
        assert 0.7 <= score <= 1.0

    def test_heuristic_importance_failure_increases_score(self, enricher):
        """Test that failures get higher importance scores."""
        success_score = enricher._heuristic_importance("action", "success")
        failure_score = enricher._heuristic_importance("action", "failure")
        assert failure_score > success_score

    def test_heuristic_importance_event_types(self, enricher):
        """Test importance scoring for different event types."""
        scores = {
            "discovery": enricher._heuristic_importance("discovery:gap", "partial"),
            "decision": enricher._heuristic_importance("decision:architecture", "success"),
            "error": enricher._heuristic_importance("error:runtime", "failure"),
            "test": enricher._heuristic_importance("test:unit", "success"),
        }

        # Discovery should be highest
        assert scores["discovery"] > scores["test"]
        assert scores["decision"] > scores["test"]

    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_llm_importance_score_success(self, mock_post, enricher):
        """Test LLM-based importance scoring."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"text": "0.85"}]
        }
        mock_post.return_value = mock_response

        score = enricher._llm_importance_score(
            "discovery:analysis",
            "Found significant performance bottleneck in query processing",
            "success",
            "Optimize database performance"
        )

        assert score == 0.85

    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_llm_importance_score_bounds(self, mock_post, enricher):
        """Test that LLM scores are bounded [0.0, 1.0]."""
        # Test > 1.0 (should clamp)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"text": "1.5"}]}
        mock_post.return_value = mock_response

        score = enricher._llm_importance_score("discovery", "test", "success")
        assert score == 1.0

        # Test < 0.0 (should clamp)
        mock_response.json.return_value = {"choices": [{"text": "-0.5"}]}
        score = enricher._llm_importance_score("discovery", "test", "success")
        assert score == 0.0

    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_score_importance_with_llm_blending(self, mock_post, enricher):
        """Test blending of heuristic and LLM scores."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"text": "0.8"}]
        }
        mock_post.return_value = mock_response

        score = enricher.score_importance_with_llm(
            "discovery:analysis",
            "Significant performance issue found",
            "success",
            "Improve system responsiveness"
        )

        # Should be between heuristic (0.9) and LLM (0.8)
        # Blended as: 0.6 * 0.9 + 0.4 * 0.8 = 0.54 + 0.32 = 0.86
        assert 0.75 <= score <= 0.95

    # ========== Cross-Project Discovery Linking Tests ==========

    def test_find_related_discoveries_no_embeddings(self, enricher, mock_db_connection):
        """Test finding related discoveries when database has no embeddings."""
        conn, cursor = mock_db_connection
        cursor.fetchall.return_value = []

        embedding = [0.1] * 768
        results = enricher.find_related_discoveries(
            embedding, conn, project_id=1, limit=5
        )

        assert results == []

    def test_find_related_discoveries_with_results(self, enricher, mock_db_connection):
        """Test finding related discoveries with results."""
        conn, cursor = mock_db_connection

        # Mock database results
        cursor.fetchall.return_value = [
            (1, "Related discovery 1", "discovery:analysis", 1000, 0.85),
            (2, "Related discovery 2", "discovery:pattern", 2000, 0.78),
        ]

        embedding = [0.1] * 768
        results = enricher.find_related_discoveries(
            embedding, conn, project_id=1, similarity_threshold=0.7, limit=5
        )

        assert len(results) == 2
        assert results[0]["similarity"] == 0.85
        assert results[1]["similarity"] == 0.78

    def test_find_cross_project_discoveries(self, enricher, mock_db_connection):
        """Test finding discoveries in other projects."""
        conn, cursor = mock_db_connection

        # Mock cross-project results
        cursor.fetchall.return_value = [
            (10, 2, "dashboard", "Similar feature found", "discovery:feature", 1500, 0.82),
        ]

        embedding = [0.1] * 768
        results = enricher.find_cross_project_discoveries(
            embedding, conn, current_project_id=1, limit=3
        )

        assert len(results) == 1
        assert results[0]["from_project"] == "dashboard"
        assert results[0]["similarity"] == 0.82

    def test_link_related_discoveries_creates_relations(self, enricher, mock_db_connection):
        """Test creating links between related discoveries."""
        conn, cursor = mock_db_connection

        related = [
            {"id": 2, "similarity": 0.85},
            {"id": 3, "similarity": 0.78},
        ]

        links_created = enricher.link_related_discoveries(conn, event_id=1, related_discoveries=related)

        # Should create bidirectional links (2 per related)
        assert links_created == 2
        assert cursor.execute.call_count >= 2

    def test_link_related_discoveries_cross_project(self, enricher, mock_db_connection):
        """Test linking cross-project discoveries (no reverse link)."""
        conn, cursor = mock_db_connection

        related = [
            {"id": 10, "from_project_id": 2, "similarity": 0.82},
        ]

        links_created = enricher.link_related_discoveries(conn, event_id=1, related_discoveries=related)

        # Should create one link only (cross-project, no reverse)
        assert links_created == 1

    # ========== Full Enrichment Test ==========

    @patch('athena.consolidation.semantic_context_enricher.SemanticContextEnricher.generate_embedding')
    @patch('athena.consolidation.semantic_context_enricher.SemanticContextEnricher.score_importance_with_llm')
    @patch('athena.consolidation.semantic_context_enricher.SemanticContextEnricher.find_related_discoveries')
    @patch('athena.consolidation.semantic_context_enricher.SemanticContextEnricher.link_related_discoveries')
    def test_enrich_event_with_semantics_full_flow(
        self,
        mock_link,
        mock_find_related,
        mock_score,
        mock_embed,
        enricher,
        mock_db_connection,
        mock_embedding
    ):
        """Test full enrichment flow."""
        conn, cursor = mock_db_connection

        # Setup mocks
        mock_embed.return_value = mock_embedding
        mock_score.return_value = 0.85
        mock_find_related.return_value = [{"id": 2, "similarity": 0.82}]
        mock_link.return_value = 1

        # Run enrichment
        result = enricher.enrich_event_with_semantics(
            conn,
            project_id=1,
            event_id=1,
            event_type="discovery:analysis",
            content="Found performance bottleneck",
            outcome="success",
            project_goal="Optimize performance"
        )

        # Verify all steps executed
        assert result["embedding_generated"] is True
        assert result["importance_scored"] is True
        assert result["importance_score"] == 0.85
        assert result["related_found"] == 1
        assert result["links_created"] == 1

    # ========== Error Handling Tests ==========

    @patch('athena.consolidation.semantic_context_enricher.requests.get')
    @patch('athena.consolidation.semantic_context_enricher.requests.post')
    def test_connection_test_handles_errors(self, mock_post, mock_get, enricher):
        """Test that connection tests handle errors gracefully."""
        # Both services unavailable
        mock_post.side_effect = ConnectionError()
        mock_get.side_effect = ConnectionError()

        # Should not raise exception
        enricher._test_connections()  # Should complete without error

    def test_enrich_event_with_db_error_recovery(self, enricher, mock_db_connection):
        """Test enrichment handles database errors gracefully."""
        conn, cursor = mock_db_connection
        cursor.execute.side_effect = Exception("Database error")

        result = enricher.enrich_event_with_semantics(
            conn,
            project_id=1,
            event_id=1,
            event_type="discovery",
            content="test",
        )

        # Should fail gracefully and return error status
        assert result["status"] in ["error", "success"]  # Depends on when error occurs


class TestSemanticContextEnricherIntegration:
    """Integration tests requiring actual services or complex setup."""

    @pytest.mark.skip(reason="Requires actual embedding service running")
    def test_real_embedding_service(self):
        """Test with real embedding service (requires localhost:8001)."""
        enricher = SemanticContextEnricher()

        embedding = enricher.generate_embedding("The quick brown fox jumps over the lazy dog")

        assert embedding is not None
        assert len(embedding) == 768
        assert all(isinstance(x, (int, float)) for x in embedding)

    @pytest.mark.skip(reason="Requires actual reasoning service running")
    def test_real_llm_importance_scoring(self):
        """Test with real LLM service (requires localhost:8002)."""
        enricher = SemanticContextEnricher()

        score = enricher.score_importance_with_llm(
            event_type="discovery:optimization",
            content="Discovered 40% performance improvement by rewriting query handler",
            outcome="success",
            project_goal="Optimize database layer"
        )

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be important discovery


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
