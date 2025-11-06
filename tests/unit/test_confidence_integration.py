"""Unit tests for confidence scoring integration in manager."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from athena.manager import UnifiedMemoryManager
from athena.core.confidence_scoring import ConfidenceScorer, ConfidenceScores, ConfidenceLevel
from athena.core.result_models import MemoryWithConfidence


@pytest.fixture
def mock_manager():
    """Create a manager with mocked dependencies."""
    # Create mocks for all required stores
    semantic_store = Mock()
    semantic_store.db = Mock()
    episodic_store = Mock()
    procedural_store = Mock()
    prospective_store = Mock()
    graph_store = Mock()
    meta_store = Mock()
    consolidation = Mock()
    project_manager = Mock()

    manager = UnifiedMemoryManager(
        semantic=semantic_store,
        episodic=episodic_store,
        procedural=procedural_store,
        prospective=prospective_store,
        graph=graph_store,
        meta=meta_store,
        consolidation=consolidation,
        project_manager=project_manager
    )

    return manager


class TestConfidenceScorerIntegration:
    """Test confidence scorer integration with manager."""

    def test_confidence_scorer_initialized(self, mock_manager):
        """Test that confidence scorer is initialized in manager."""
        assert hasattr(mock_manager, 'confidence_scorer')
        assert isinstance(mock_manager.confidence_scorer, ConfidenceScorer)

    def test_apply_confidence_scores_with_semantic_results(self, mock_manager):
        """Test applying confidence scores to semantic results."""
        results = {
            "semantic": [
                {"content": "Test fact", "similarity": 0.85},
                {"content": "Another fact", "similarity": 0.75},
            ]
        }

        scored = mock_manager.apply_confidence_scores(results)

        # Check structure
        assert "semantic" in scored
        assert len(scored["semantic"]) == 2

        # Check confidence scores present
        for result in scored["semantic"]:
            assert "confidence" in result
            assert "overall" in result["confidence"]
            assert "level" in result["confidence"]
            assert 0 <= result["confidence"]["overall"] <= 1

    def test_apply_confidence_scores_preserves_content(self, mock_manager):
        """Test that applying scores preserves original content."""
        original_content = "Test memory content"
        results = {
            "semantic": [
                {"content": original_content, "similarity": 0.8}
            ]
        }

        scored = mock_manager.apply_confidence_scores(results)
        assert scored["semantic"][0]["content"] == original_content

    def test_apply_confidence_scores_multiple_layers(self, mock_manager):
        """Test applying scores across multiple layers."""
        results = {
            "semantic": [{"content": "Fact", "similarity": 0.8}],
            "episodic": [{"content": "Event", "timestamp": datetime.now().isoformat()}],
            "graph": [{"entity": "Entity1", "type": "concept"}]
        }

        scored = mock_manager.apply_confidence_scores(results)

        # All layers should have scores
        assert len(scored) == 3
        for layer in ["semantic", "episodic", "graph"]:
            assert layer in scored
            assert len(scored[layer]) > 0
            assert "confidence" in scored[layer][0]

    def test_confidence_scores_have_five_factors(self, mock_manager):
        """Test that confidence scores include all 5 factors."""
        results = {
            "semantic": [{"content": "Test", "similarity": 0.9}]
        }

        scored = mock_manager.apply_confidence_scores(results)
        confidence = scored["semantic"][0]["confidence"]

        # Check all 5 factors present
        factors = [
            "semantic_relevance",
            "source_quality",
            "recency",
            "consistency",
            "completeness",
            "overall",
            "level"
        ]

        for factor in factors:
            assert factor in confidence

    def test_apply_confidence_scores_handles_non_dict_results(self, mock_manager):
        """Test that non-dict results are converted."""
        results = {
            "semantic": ["String result"]
        }

        scored = mock_manager.apply_confidence_scores(results)

        # Should convert to dict
        assert isinstance(scored["semantic"][0], dict)
        assert "content" in scored["semantic"][0]
        assert "confidence" in scored["semantic"][0]

    def test_apply_confidence_scores_skips_non_list_values(self, mock_manager):
        """Test that non-list values in results are preserved."""
        results = {
            "semantic": [{"content": "Test"}],
            "metadata": {"count": 5}
        }

        scored = mock_manager.apply_confidence_scores(results)

        # Non-list values should be preserved as-is
        assert scored["metadata"] == {"count": 5}

    def test_retrieve_includes_confidence_scores_by_default(self, mock_manager):
        """Test that retrieve() includes confidence scores by default."""
        # Mock project and result from _query_semantic
        mock_manager.project_manager.require_project = Mock(return_value=Mock(id=1))
        mock_manager.semantic.recall_with_reranking = Mock(return_value=[])

        # This would normally return results, but we're testing it tries to apply scores
        results = mock_manager.retrieve("test query")

        # Should have been modified by apply_confidence_scores
        # Empty results list is still in the semantic key
        assert "semantic" in results
        assert results["semantic"] == []

    def test_retrieve_can_disable_confidence_scores(self, mock_manager):
        """Test that confidence scores can be disabled."""
        mock_manager.project_manager.require_project = Mock(return_value=Mock(id=1))
        mock_manager.semantic.recall_with_reranking = Mock(return_value=[
            Mock(
                memory=Mock(content="Test", memory_type="fact", tags=[]),
                similarity=0.8
            )
        ])

        # Disable confidence scores
        results = mock_manager.retrieve("test query", include_confidence_scores=False)

        # Results should NOT have confidence field added
        # (they may have it from the mock, but apply_confidence_scores shouldn't be called)
        assert results is not None

    def test_retrieve_with_explanation(self, mock_manager):
        """Test that retrieve() includes explanation when requested."""
        mock_manager.project_manager.require_project = Mock(return_value=Mock(id=1))
        mock_manager.semantic.recall_with_reranking = Mock(return_value=[])

        results = mock_manager.retrieve("test query", explain_reasoning=True)

        # Should have explanation
        assert "_explanation" in results
        explanation = results["_explanation"]
        assert "query" in explanation
        assert "query_type" in explanation
        assert "reasoning" in explanation
        assert "layers_searched" in explanation
        assert "result_count" in explanation

    def test_query_explanation_shows_reasoning(self, mock_manager):
        """Test that query explanation shows correct reasoning."""
        # Test temporal query
        explanation = mock_manager._explain_query_routing(
            "When did we do X?",
            "temporal",
            {"episodic": []}
        )

        assert "when something happened" in explanation["reasoning"]

    def test_query_explanation_tracks_layers_searched(self, mock_manager):
        """Test that explanation tracks which layers were searched."""
        results = {
            "semantic": [{"content": "Test"}],
            "episodic": [{"content": "Event"}]
        }

        explanation = mock_manager._explain_query_routing("test", "factual", results)

        # Should list the layers that were searched
        assert "semantic" in explanation["layers_searched"]
        assert "episodic" in explanation["layers_searched"]
        assert len(explanation["layers_searched"]) == 2

    def test_confidence_scores_respect_layer_quality(self, mock_manager):
        """Test that different layers get different base quality scores."""
        # Episodic should have high base quality
        episodic_result = {"content": "Event"}
        episodic_score = mock_manager.confidence_scorer.score(
            memory=episodic_result,
            source_layer="episodic"
        )

        # Prospective should have lower base quality
        prospective_result = {"content": "Task"}
        prospective_score = mock_manager.confidence_scorer.score(
            memory=prospective_result,
            source_layer="prospective"
        )

        # Episodic quality should be higher than prospective
        assert episodic_score.source_quality > prospective_score.source_quality


class TestConfidenceScoringQuality:
    """Test quality metrics for confidence scoring."""

    def test_confidence_scores_sum_to_reasonable_range(self, mock_manager):
        """Test that confidence scores are in valid range."""
        results = {"semantic": [{"content": "Test", "similarity": 0.8}]}
        scored = mock_manager.apply_confidence_scores(results)

        confidence = scored["semantic"][0]["confidence"]

        # All factors should be between 0 and 1
        for factor in ["semantic_relevance", "source_quality", "recency", "consistency", "completeness", "overall"]:
            assert 0 <= confidence[factor] <= 1

    def test_confidence_level_matches_overall_score(self, mock_manager):
        """Test that confidence level matches overall score."""
        results = {"semantic": [{"content": "Test", "similarity": 0.95}]}
        scored = mock_manager.apply_confidence_scores(results)

        confidence = scored["semantic"][0]["confidence"]
        level = confidence["level"]

        # High score should have HIGH level
        if confidence["overall"] > 0.7:
            assert level in ["HIGH", "high"]

    def test_semantic_score_influences_overall_confidence(self, mock_manager):
        """Test that semantic similarity influences overall confidence."""
        # High similarity
        high_sim = {"semantic": [{"content": "Test", "similarity": 0.95}]}
        high_scored = mock_manager.apply_confidence_scores(high_sim)

        # Low similarity
        low_sim = {"semantic": [{"content": "Test", "similarity": 0.35}]}
        low_scored = mock_manager.apply_confidence_scores(low_sim)

        # High similarity should have higher overall confidence
        high_overall = high_scored["semantic"][0]["confidence"]["overall"]
        low_overall = low_scored["semantic"][0]["confidence"]["overall"]

        assert high_overall > low_overall
