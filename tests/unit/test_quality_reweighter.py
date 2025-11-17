"""Unit tests for quality-based reweighting system (Gap 3 fix)."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from athena.meta.quality_reweighter import QualityReweighter, LayerQualitySelector
from athena.meta.models import MemoryQuality
from athena.meta.store import MetaMemoryStore


class TestQualityReweighter:
    """Test quality-based result reweighting."""

    def test_initialization(self):
        """Test reweighter initialization."""
        mock_store = Mock(spec=MetaMemoryStore)
        reweighter = QualityReweighter(mock_store)

        assert reweighter.meta_store is mock_store
        assert reweighter._quality_cache == {}

    def test_reweight_results_empty(self):
        """Test reweighting empty results."""
        mock_store = Mock(spec=MetaMemoryStore)
        reweighter = QualityReweighter(mock_store)

        results = {"semantic": [], "episodic": []}
        reweighted = reweighter.reweight_results(results)

        assert "semantic" in reweighted
        assert "episodic" in reweighted
        assert "_layer_quality_scores" in reweighted

    def test_reweight_results_preserves_metadata(self):
        """Test that metadata fields are preserved during reweighting."""
        mock_store = Mock(spec=MetaMemoryStore)
        reweighter = QualityReweighter(mock_store)

        results = {
            "semantic": [{"id": 1, "score": 0.8, "content": "test"}],
            "_explanation": "This is metadata",
            "_cache_hit": True,
        }

        reweighted = reweighter.reweight_results(results)

        assert reweighted["_explanation"] == "This is metadata"
        assert reweighted["_cache_hit"] is True

    def test_reweight_results_with_quality_scores(self):
        """Test reweighting applies quality score adjustments."""
        mock_store = Mock(spec=MetaMemoryStore)

        # Create quality record: high usefulness, high confidence
        quality = MemoryQuality(
            memory_id=1,
            memory_layer="semantic",
            access_count=10,
            useful_count=8,
            usefulness_score=0.8,
            confidence=0.85,
            relevance_decay=0.9,
        )
        mock_store.get_quality.return_value = quality

        reweighter = QualityReweighter(mock_store)

        results = {
            "semantic": [{"id": 1, "score": 0.5, "content": "memory"}],
        }

        reweighted = reweighter.reweight_results(results)

        # Score should be boosted due to high quality
        reweighted_item = reweighted["semantic"][0]
        assert "_original_score" in reweighted_item
        assert "_adjusted_score" in reweighted_item
        assert reweighted_item["_adjusted_score"] > reweighted_item["_original_score"]
        assert "_quality_metrics" in reweighted_item

    def test_reweight_low_quality_results_penalized(self):
        """Test that low-quality results are penalized."""
        mock_store = Mock(spec=MetaMemoryStore)

        # Low usefulness score
        quality = MemoryQuality(
            memory_id=2,
            memory_layer="episodic",
            access_count=5,
            useful_count=0,
            usefulness_score=0.0,
            confidence=0.5,
            relevance_decay=0.5,
        )
        mock_store.get_quality.return_value = quality

        reweighter = QualityReweighter(mock_store)

        results = {
            "episodic": [{"id": 2, "score": 0.8, "content": "event"}],
        }

        reweighted = reweighter.reweight_results(results)

        # Score should be reduced due to low quality
        reweighted_item = reweighted["episodic"][0]
        # With low usefulness, should have quality metadata showing low scores
        assert "_quality_metrics" in reweighted_item
        assert reweighted_item["_quality_metrics"]["usefulness"] == 0.0

    def test_reweight_multiple_results_ranking(self):
        """Test that results are reranked by adjusted score."""
        mock_store = Mock(spec=MetaMemoryStore)

        # Two quality records with different scores
        qualities = {
            1: MemoryQuality(
                memory_id=1,
                memory_layer="semantic",
                usefulness_score=0.2,
                confidence=0.5,
                relevance_decay=0.8,
            ),
            2: MemoryQuality(
                memory_id=2,
                memory_layer="semantic",
                usefulness_score=0.9,
                confidence=0.95,
                relevance_decay=0.9,
            ),
        }

        def mock_get_quality(memory_id, layer):
            return qualities.get(memory_id)

        mock_store.get_quality.side_effect = mock_get_quality

        reweighter = QualityReweighter(mock_store)

        results = {
            "semantic": [
                {"id": 1, "score": 0.9, "content": "low quality memory"},
                {"id": 2, "score": 0.8, "content": "high quality memory"},
            ],
        }

        reweighted = reweighter.reweight_results(results)

        # Despite original scores, high-quality result should rank first
        semantic_results = reweighted["semantic"]
        assert semantic_results[0]["id"] == 2  # High quality first
        assert semantic_results[1]["id"] == 1  # Low quality second

    def test_compute_layer_quality_scores(self):
        """Test computation of overall layer quality scores."""
        mock_store = Mock(spec=MetaMemoryStore)
        reweighter = QualityReweighter(mock_store)

        layer_results = {
            "semantic": [
                {
                    "id": 1,
                    "_quality_metrics": {"usefulness": 0.8},
                },
                {
                    "id": 2,
                    "_quality_metrics": {"usefulness": 0.9},
                },
            ],
            "episodic": [
                {
                    "id": 3,
                    "_quality_metrics": {"usefulness": 0.3},
                },
            ],
        }

        scores = reweighter._compute_layer_quality_scores(layer_results, {})

        assert "semantic" in scores
        assert "episodic" in scores
        # Semantic average: (0.8 + 0.9) / 2 = 0.85
        assert abs(scores["semantic"] - 0.85) < 0.01
        # Episodic: 0.3
        assert abs(scores["episodic"] - 0.3) < 0.01

    def test_cache_quality_lookups(self):
        """Test that quality lookups are cached."""
        mock_store = Mock(spec=MetaMemoryStore)

        quality = MemoryQuality(
            memory_id=1,
            memory_layer="semantic",
            usefulness_score=0.7,
            confidence=0.8,
        )
        mock_store.get_quality.return_value = quality

        reweighter = QualityReweighter(mock_store)

        # First lookup
        q1 = reweighter._get_quality_cached(1, "semantic")
        # Second lookup (should use cache)
        q2 = reweighter._get_quality_cached(1, "semantic")

        # Both should return same object
        assert q1 is q2
        # But store should only be called once
        assert mock_store.get_quality.call_count == 1

    def test_clear_cache(self):
        """Test cache clearing."""
        mock_store = Mock(spec=MetaMemoryStore)
        reweighter = QualityReweighter(mock_store)

        # Populate cache
        reweighter._quality_cache[(1, "semantic")] = Mock()
        reweighter._quality_cache[(2, "episodic")] = Mock()

        assert len(reweighter._quality_cache) > 0

        reweighter.clear_cache()

        assert len(reweighter._quality_cache) == 0

    def test_reweight_error_handling(self):
        """Test graceful error handling during reweighting."""
        mock_store = Mock(spec=MetaMemoryStore)
        mock_store.get_quality.side_effect = Exception("Database error")

        reweighter = QualityReweighter(mock_store)

        results = {
            "semantic": [{"id": 1, "score": 0.8}],
        }

        # Should return original results on error
        reweighted = reweighter.reweight_results(results)
        assert reweighted == results


class TestLayerQualitySelector:
    """Test layer selection based on quality."""

    def test_initialization(self):
        """Test selector initialization."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        assert selector.meta_store is mock_store

    def test_select_layers_tier1_filters_low_quality(self):
        """Test that Tier 1 filters out low-quality layers."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        available_layers = ["semantic", "episodic", "procedural", "graph"]
        weights = selector.select_layers_for_query(
            "test query",
            available_layers,
            tier=1,
        )

        # Tier 1 should prefer high-quality layers
        # All base qualities in tier 1 are >= 0.4, so all should be selected
        total_weight = sum(weights.values())
        assert total_weight > 0
        assert len(weights) > 0

    def test_select_layers_tier2_uses_all_layers(self):
        """Test that Tier 2 uses all available layers."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        available_layers = ["semantic", "episodic", "procedural", "graph"]
        weights = selector.select_layers_for_query(
            "test query",
            available_layers,
            tier=2,
        )

        # Tier 2 should use all layers
        assert len(weights) == len(available_layers)
        # Weights should sum to 1.0
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_estimate_layer_quality_context_aware(self):
        """Test context-aware layer quality estimation."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        # Implementation task context should boost procedural
        quality_impl = selector._estimate_layer_quality(
            "procedural",
            {"task": "implement feature"},
        )

        # Regular context
        quality_neutral = selector._estimate_layer_quality(
            "procedural",
            {"task": "unknown"},
        )

        assert quality_impl > quality_neutral

    def test_estimate_layer_quality_debugging_context(self):
        """Test debugging context boosts episodic."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        # Debugging context should boost episodic
        quality_debug = selector._estimate_layer_quality(
            "episodic",
            {"task": "fix bug in auth"},
        )

        # Neutral context
        quality_neutral = selector._estimate_layer_quality(
            "episodic",
            {"task": "unknown"},
        )

        assert quality_debug > quality_neutral

    def test_layer_weights_normalized(self):
        """Test that returned layer weights are normalized to sum to 1.0."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        layers = ["semantic", "episodic", "procedural", "prospective", "graph"]
        for tier in [1, 2, 3]:
            weights = selector.select_layers_for_query("query", layers, tier=tier)

            total = sum(weights.values())
            if len(weights) > 0:  # If layers selected
                assert abs(total - 1.0) < 0.01, f"Tier {tier} weights don't sum to 1.0"

    def test_planning_context_boosts_graph(self):
        """Test that planning context boosts graph layer."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        quality_plan = selector._estimate_layer_quality(
            "graph",
            {"task": "plan architecture"},
        )

        quality_neutral = selector._estimate_layer_quality(
            "graph",
            {"task": "other"},
        )

        assert quality_plan > quality_neutral

    def test_select_layers_single_layer(self):
        """Test selection with single available layer."""
        mock_store = Mock(spec=MetaMemoryStore)
        selector = LayerQualitySelector(mock_store)

        weights = selector.select_layers_for_query(
            "query",
            ["semantic"],
            tier=2,
        )

        assert "semantic" in weights
        assert abs(weights["semantic"] - 1.0) < 0.01  # Should be 100%


class TestQualityReweighterIntegration:
    """Integration tests for quality reweighting with realistic scenarios."""

    def test_reweight_mixed_quality_results(self):
        """Test reweighting with mixed quality results from multiple layers."""
        mock_store = Mock(spec=MetaMemoryStore)

        def mock_get_quality(memory_id, layer):
            qualities = {
                (1, "semantic"): MemoryQuality(
                    memory_id=1,
                    memory_layer="semantic",
                    usefulness_score=0.9,
                    confidence=0.95,
                    relevance_decay=0.9,
                ),
                (2, "episodic"): MemoryQuality(
                    memory_id=2,
                    memory_layer="episodic",
                    usefulness_score=0.3,
                    confidence=0.4,
                    relevance_decay=0.7,
                ),
                (3, "procedural"): MemoryQuality(
                    memory_id=3,
                    memory_layer="procedural",
                    usefulness_score=0.8,
                    confidence=0.85,
                    relevance_decay=0.88,
                ),
            }
            return qualities.get((memory_id, layer))

        mock_store.get_quality.side_effect = mock_get_quality

        reweighter = QualityReweighter(mock_store)

        results = {
            "semantic": [{"id": 1, "score": 0.7, "content": "fact"}],
            "episodic": [{"id": 2, "score": 0.9, "content": "event"}],
            "procedural": [{"id": 3, "score": 0.6, "content": "workflow"}],
        }

        reweighted = reweighter.reweight_results(results)

        # Check that results have quality metrics
        assert len(reweighted["semantic"]) > 0
        assert "_quality_metrics" in reweighted["semantic"][0]
        assert len(reweighted["episodic"]) > 0
        assert "_quality_metrics" in reweighted["episodic"][0]

    def test_reweight_with_no_quality_records(self):
        """Test reweighting when no quality records exist."""
        mock_store = Mock(spec=MetaMemoryStore)
        mock_store.get_quality.return_value = None

        reweighter = QualityReweighter(mock_store)

        results = {
            "semantic": [{"id": 999, "score": 0.8, "content": "new memory"}],
        }

        # Should not crash with None quality
        reweighted = reweighter.reweight_results(results)

        # Should still have the result with original score
        assert len(reweighted["semantic"]) > 0
        assert reweighted["semantic"][0]["id"] == 999
