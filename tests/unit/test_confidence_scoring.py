"""Unit tests for confidence scoring module."""

import pytest
from datetime import datetime, timedelta

from athena.core.confidence_scoring import ConfidenceScorer, ConfidenceFilter
from athena.core.result_models import ConfidenceScores, ConfidenceLevel


class TestConfidenceScorer:
    """Test ConfidenceScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a ConfidenceScorer instance."""
        return ConfidenceScorer()

    def test_score_with_all_factors(self, scorer):
        """Test scoring with all confidence factors."""
        memory = {
            "id": "test_1",
            "content": "Test content",
            "type": "episodic",
            "created_at": datetime.now().isoformat(),
            "is_consistent": True,
        }

        scores = scorer.score(
            memory=memory,
            source_layer="episodic",
            semantic_score=0.8,
        )

        assert isinstance(scores, ConfidenceScores)
        assert 0 <= scores.semantic_relevance <= 1
        assert 0 <= scores.source_quality <= 1
        assert 0 <= scores.recency <= 1
        assert 0 <= scores.consistency <= 1
        assert 0 <= scores.completeness <= 1

    def test_score_missing_timestamp(self, scorer):
        """Test scoring with missing timestamp."""
        memory = {
            "id": "test_2",
            "content": "Test content",
            "type": "semantic",
        }

        scores = scorer.score(
            memory=memory,
            source_layer="semantic",
            semantic_score=0.7,
        )

        # Should still return valid scores
        assert isinstance(scores, ConfidenceScores)
        assert 0 <= scores.recency <= 1

    def test_aggregate_confidence(self, scorer):
        """Test aggregating confidence scores."""
        scores = ConfidenceScores(
            semantic_relevance=0.8,
            source_quality=0.9,
            recency=0.7,
            consistency=0.8,
            completeness=0.85,
        )

        overall = scorer.aggregate_confidence(scores)

        assert 0 <= overall <= 1
        # Should be weighted average close to mean
        assert 0.75 < overall < 0.9

    def test_aggregate_with_custom_weights(self, scorer):
        """Test aggregating with custom weights."""
        scores = ConfidenceScores(
            semantic_relevance=1.0,
            source_quality=0.0,
            recency=0.0,
            consistency=0.0,
            completeness=0.0,
        )

        weights = {
            "semantic_relevance": 1.0,  # All weight on semantic
            "source_quality": 0.0,
            "recency": 0.0,
            "consistency": 0.0,
            "completeness": 0.0,
        }

        overall = scorer.aggregate_confidence(scores, weights=weights)

        assert overall == 1.0  # Should be 100% semantic

    def test_recency_scoring_fresh(self, scorer):
        """Test recency scoring for fresh memories."""
        memory = {
            "created_at": datetime.now().isoformat(),
        }

        recency = scorer._compute_recency(memory)

        assert recency >= 0.9  # Very recent should be high

    def test_recency_scoring_old(self, scorer):
        """Test recency scoring for old memories."""
        old_date = (datetime.now() - timedelta(days=30)).isoformat()
        memory = {
            "created_at": old_date,
        }

        recency = scorer._compute_recency(memory)

        assert 0 <= recency < 0.3  # Very old should be low

    def test_completeness_scoring(self, scorer):
        """Test completeness scoring."""
        complete_memory = {
            "content": "Full content",
            "type": "semantic",
            "docstring": "Documentation",
            "tags": ["important"],
        }

        completeness = scorer._compute_completeness(complete_memory)

        assert 0.5 <= completeness <= 1.0

    def test_layer_quality_differences(self, scorer):
        """Test that different layers have different quality scores."""
        memory = {
            "content": "Test",
            "type": "test",
        }

        episodic_quality = scorer._compute_source_quality(memory, "episodic")
        semantic_quality = scorer._compute_source_quality(memory, "semantic")

        # Different layers should have different baseline quality
        assert episodic_quality > semantic_quality  # Episodic more trustworthy


class TestConfidenceFilter:
    """Test ConfidenceFilter class."""

    def test_filter_by_confidence(self):
        """Test filtering results by confidence threshold."""
        results = [
            {"id": "1", "confidence": 0.9},
            {"id": "2", "confidence": 0.5},
            {"id": "3", "confidence": 0.3},
        ]

        filtered = ConfidenceFilter.filter_by_confidence(
            results,
            min_confidence=0.6,
        )

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_rank_by_confidence(self):
        """Test ranking results by confidence."""
        results = [
            {"id": "1", "confidence": 0.5},
            {"id": "2", "confidence": 0.9},
            {"id": "3", "confidence": 0.3},
        ]

        ranked = ConfidenceFilter.rank_by_confidence(results)

        assert ranked[0]["confidence"] == 0.9
        assert ranked[1]["confidence"] == 0.5
        assert ranked[2]["confidence"] == 0.3

    def test_confidence_summary_empty(self):
        """Test confidence summary with empty results."""
        summary = ConfidenceFilter.get_confidence_summary([])

        assert summary["count"] == 0
        assert summary["average"] == 0.0
        assert summary["max"] == 0.0
        assert summary["min"] == 0.0

    def test_confidence_summary_with_results(self):
        """Test confidence summary with results."""
        results = [
            {"confidence": 0.9},
            {"confidence": 0.7},
            {"confidence": 0.5},
        ]

        summary = ConfidenceFilter.get_confidence_summary(results)

        assert summary["count"] == 3
        assert summary["average"] == pytest.approx(0.7, abs=0.01)
        assert summary["max"] == 0.9
        assert summary["min"] == 0.5


class TestConfidenceLevel:
    """Test ConfidenceLevel determination."""

    def test_very_high_level(self):
        """Test VERY_HIGH confidence level."""
        scores = ConfidenceScores(
            semantic_relevance=0.95,
            source_quality=0.95,
            recency=0.95,
            consistency=0.95,
            completeness=0.95,
        )

        level = scores.level()
        assert level == ConfidenceLevel.VERY_HIGH

    def test_high_level(self):
        """Test HIGH confidence level."""
        scores = ConfidenceScores(
            semantic_relevance=0.8,
            source_quality=0.8,
            recency=0.8,
            consistency=0.8,
            completeness=0.8,
        )

        level = scores.level()
        assert level == ConfidenceLevel.HIGH

    def test_medium_level(self):
        """Test MEDIUM confidence level."""
        scores = ConfidenceScores(
            semantic_relevance=0.6,
            source_quality=0.6,
            recency=0.6,
            consistency=0.6,
            completeness=0.6,
        )

        level = scores.level()
        assert level == ConfidenceLevel.MEDIUM

    def test_low_level(self):
        """Test LOW confidence level."""
        scores = ConfidenceScores(
            semantic_relevance=0.4,
            source_quality=0.4,
            recency=0.4,
            consistency=0.4,
            completeness=0.4,
        )

        level = scores.level()
        assert level == ConfidenceLevel.LOW

    def test_very_low_level(self):
        """Test VERY_LOW confidence level."""
        scores = ConfidenceScores(
            semantic_relevance=0.1,
            source_quality=0.1,
            recency=0.1,
            consistency=0.1,
            completeness=0.1,
        )

        level = scores.level()
        assert level == ConfidenceLevel.VERY_LOW


class TestConfidenceAveraging:
    """Test confidence score averaging."""

    def test_average_score_calculation(self):
        """Test averaging of confidence scores."""
        scores = ConfidenceScores(
            semantic_relevance=0.5,
            source_quality=0.6,
            recency=0.7,
            consistency=0.8,
            completeness=0.9,
        )

        average = scores.average()

        expected = (0.5 + 0.6 + 0.7 + 0.8 + 0.9) / 5
        assert average == pytest.approx(expected, abs=0.01)

    def test_average_all_same(self):
        """Test averaging when all scores are the same."""
        scores = ConfidenceScores(
            semantic_relevance=0.75,
            source_quality=0.75,
            recency=0.75,
            consistency=0.75,
            completeness=0.75,
        )

        average = scores.average()

        assert average == 0.75
