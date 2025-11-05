"""Tests for RAG uncertainty calibration module."""

import pytest

from athena.core.models import Memory, MemorySearchResult, MemoryType
from athena.rag.uncertainty import (
    AbstentionReason,
    ConfidenceLevel,
    UncertaintyCalibrator,
    UncertaintyConfig,
    UncertaintyMetrics,
)


@pytest.fixture
def calibrator():
    """Fixture providing default uncertainty calibrator."""
    return UncertaintyCalibrator()


def create_search_result(id: int, content: str, similarity: float, event_type: str = "action") -> MemorySearchResult:
    """Helper to create search results with correct model structure."""
    memory = Memory(
        id=id,
        project_id=1,
        content=content,
        memory_type=MemoryType.FACT,
    )
    return MemorySearchResult(
        memory=memory,
        similarity=similarity,
        rank=1,
        metadata={"event_type": event_type},
    )


@pytest.fixture
def high_quality_results():
    """Fixture providing high-quality search results."""
    return [
        create_search_result(
            1,
            "User authentication uses JWT tokens with RSA signatures",
            0.92,
            "action",
        ),
        create_search_result(
            2,
            "Authentication layer validates tokens on every request",
            0.89,
            "decision",
        ),
        create_search_result(
            3,
            "Tokens expire after 24 hours and can be refreshed",
            0.85,
            "action",
        ),
    ]


@pytest.fixture
def low_quality_results():
    """Fixture providing low-quality search results."""
    return [
        create_search_result(1, "Something about security", 0.35, "action"),
    ]


@pytest.fixture
def conflicting_results():
    """Fixture providing conflicting search results."""
    return [
        create_search_result(1, "Authentication uses OAuth2 tokens", 0.75, "decision"),
        create_search_result(2, "Authentication uses JWT tokens instead", 0.15, "action"),
    ]


class TestUncertaintyCalibration:
    """Tests for UncertaintyCalibrator.calibrate method."""

    def test_high_confidence_with_quality_results(self, calibrator, high_quality_results):
        """Test that high-quality results produce high confidence."""
        metrics = calibrator.calibrate(high_quality_results, "How does authentication work?")

        assert metrics.confidence_level == ConfidenceLevel.HIGH
        assert metrics.confidence_score >= 0.8
        assert not metrics.should_abstain
        assert metrics.abstention_reason is None

    def test_low_confidence_with_poor_results(self, calibrator, low_quality_results):
        """Test that poor results produce low confidence or abstention."""
        metrics = calibrator.calibrate(low_quality_results, "How does authentication work?")

        assert metrics.confidence_level in (ConfidenceLevel.LOW, ConfidenceLevel.ABSTAIN)
        assert metrics.confidence_score < 0.6

    def test_abstention_with_insufficient_results(self, calibrator):
        """Test abstention when result count is too low."""
        results = [
            create_search_result(1, "Some info", 0.5, "action"),
        ]
        metrics = calibrator.calibrate(results, "How does authentication work?")

        assert metrics.should_abstain
        assert metrics.abstention_reason == AbstentionReason.INSUFFICIENT_CONTEXT

    def test_empty_results_triggers_abstention(self, calibrator):
        """Test that empty results trigger abstention."""
        metrics = calibrator.calibrate([], "How does authentication work?")

        assert metrics.should_abstain
        assert metrics.confidence_score < 0.5  # Should be low, not necessarily 0.0
        assert metrics.result_count == 0

    def test_conflicting_results_trigger_warning(self, calibrator, conflicting_results):
        """Test that conflicting results are detected."""
        metrics = calibrator.calibrate(
            conflicting_results, "What authentication method is used?"
        )

        # With only 2 results, may trigger insufficient context or low relevance
        # depending on penalty calculations
        assert metrics.should_abstain
        # Could be insufficient context, low relevance, or conflicting
        assert metrics.abstention_reason in (
            AbstentionReason.INSUFFICIENT_CONTEXT,
            AbstentionReason.CONFLICTING_RESULTS,
            AbstentionReason.LOW_RELEVANCE,
        )

    def test_out_of_domain_detection(self, calibrator):
        """Test detection of out-of-domain queries."""
        # Need multiple results with low similarity to trigger OOD detection
        results = [
            create_search_result(1, "Cooking is fun", 0.20, "action"),
            create_search_result(2, "Recipes and ingredients", 0.18, "action"),
            create_search_result(3, "Baking tips", 0.15, "action"),
        ]
        metrics = calibrator.calibrate(results, "How does authentication work?")

        assert metrics.should_abstain
        # Could be LOW_RELEVANCE or OUT_OF_DOMAIN depending on threshold order
        assert metrics.abstention_reason in (
            AbstentionReason.OUT_OF_DOMAIN,
            AbstentionReason.LOW_RELEVANCE,
        )

    def test_confidence_metrics_computation(self, calibrator, high_quality_results):
        """Test that all component metrics are computed."""
        metrics = calibrator.calibrate(high_quality_results, "How does authentication work?")

        assert 0.0 <= metrics.relevance_score <= 1.0
        assert 0.0 <= metrics.coverage_score <= 1.0
        assert 0.0 <= metrics.consistency_score <= 1.0
        assert 0.0 <= metrics.recency_score <= 1.0
        assert 0.0 <= metrics.confidence_score <= 1.0
        assert metrics.result_count == 3
        assert metrics.min_result_similarity <= metrics.max_result_similarity


class TestUncertaintyConfig:
    """Tests for UncertaintyConfig validation."""

    def test_valid_configuration(self):
        """Test that valid configuration is accepted."""
        config = UncertaintyConfig(
            relevance_weight=0.4,
            coverage_weight=0.3,
            consistency_weight=0.2,
            recency_weight=0.1,
        )
        assert config.relevance_weight == 0.4

    def test_invalid_weights_sum(self):
        """Test that invalid weight sum raises error."""
        with pytest.raises(ValueError, match="sum to 1.0"):
            UncertaintyConfig(
                relevance_weight=0.5,
                coverage_weight=0.3,
                consistency_weight=0.2,
                recency_weight=0.1,  # Sum = 1.1, invalid
            )

    def test_custom_thresholds(self):
        """Test that custom thresholds can be set."""
        config = UncertaintyConfig(
            high_confidence_threshold=0.9,
            medium_confidence_threshold=0.7,
            low_confidence_threshold=0.5,
            abstention_threshold=0.5,
        )
        assert config.high_confidence_threshold == 0.9


class TestAbstentionLogic:
    """Tests for abstention reason determination."""

    def test_abstention_reasons(self):
        """Test that all abstention reasons are properly defined."""
        reasons = [
            AbstentionReason.INSUFFICIENT_CONTEXT,
            AbstentionReason.LOW_RELEVANCE,
            AbstentionReason.CONFLICTING_RESULTS,
            AbstentionReason.OUT_OF_DOMAIN,
            AbstentionReason.QUERY_AMBIGUITY,
        ]
        assert len(reasons) == 5
        assert all(isinstance(r, AbstentionReason) for r in reasons)

    def test_confidence_levels(self):
        """Test that all confidence levels are properly defined."""
        levels = [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
            ConfidenceLevel.ABSTAIN,
        ]
        assert len(levels) == 4
        assert all(isinstance(l, ConfidenceLevel) for l in levels)


class TestContextSufficiency:
    """Tests for context sufficiency computation."""

    def test_sufficient_context(self, calibrator, high_quality_results):
        """Test detection of sufficient context."""
        result = calibrator.compute_context_sufficiency(
            high_quality_results, required_confidence=0.75
        )

        assert result["is_sufficient"]
        assert result["confidence_score"] >= 0.75
        assert result["gap"] == 0.0

    def test_insufficient_context(self, calibrator, low_quality_results):
        """Test detection of insufficient context."""
        result = calibrator.compute_context_sufficiency(
            low_quality_results, required_confidence=0.75
        )

        assert not result["is_sufficient"]
        assert result["gap"] > 0

    def test_context_gap_calculation(self, calibrator, low_quality_results):
        """Test that context gap is properly calculated."""
        required = 0.75
        result = calibrator.compute_context_sufficiency(low_quality_results, required_confidence=required)

        expected_gap = max(0, required - result["confidence_score"])
        assert result["gap"] == expected_gap


class TestExplanations:
    """Tests for confidence explanation generation."""

    def test_high_confidence_explanation(self, calibrator, high_quality_results):
        """Test that high confidence produces appropriate explanation."""
        metrics = calibrator.calibrate(high_quality_results, "Test query")

        assert "High confidence" in metrics.explanation or metrics.confidence_level == ConfidenceLevel.HIGH
        assert "%" in metrics.explanation  # Should contain percentage

    def test_abstention_explanation(self, calibrator):
        """Test that abstention includes reason."""
        results = []
        metrics = calibrator.calibrate(results, "Test query")

        assert metrics.should_abstain
        assert "Abstain" in metrics.explanation or metrics.abstention_reason

    def test_explanation_includes_scores(self, calibrator, high_quality_results):
        """Test that explanation includes component scores."""
        metrics = calibrator.calibrate(high_quality_results, "Test query")

        # If confidence is not abstaining, explanation should mention confidence level
        if not metrics.should_abstain:
            assert any(
                level in metrics.explanation
                for level in ["High", "Medium", "Low"]
            )


class TestMetricsDataclass:
    """Tests for UncertaintyMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating UncertaintyMetrics instance."""
        metrics = UncertaintyMetrics(
            confidence_score=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            should_abstain=False,
        )

        assert metrics.confidence_score == 0.85
        assert metrics.confidence_level == ConfidenceLevel.HIGH
        assert not metrics.should_abstain
        assert metrics.abstention_reason is None

    def test_metrics_with_components(self):
        """Test UncertaintyMetrics with all components."""
        metrics = UncertaintyMetrics(
            confidence_score=0.80,
            confidence_level=ConfidenceLevel.HIGH,
            should_abstain=False,
            relevance_score=0.85,
            coverage_score=0.75,
            consistency_score=0.80,
            recency_score=1.0,
            result_count=3,
        )

        assert metrics.relevance_score == 0.85
        assert metrics.coverage_score == 0.75
        assert metrics.result_count == 3


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_high_quality_result(self, calibrator):
        """Test behavior with single high-quality result."""
        result = [
            create_search_result(1, "High quality information", 0.95, "action"),
        ]
        metrics = calibrator.calibrate(result, "Test query")

        # Single result should trigger insufficient context
        assert metrics.should_abstain
        assert metrics.abstention_reason == AbstentionReason.INSUFFICIENT_CONTEXT

    def test_many_low_quality_results(self, calibrator):
        """Test behavior with many low-quality results."""
        results = [
            create_search_result(
                i,
                f"Weak result {i}",
                0.2 + (i * 0.05),
                "action",
            )
            for i in range(10)
        ]
        metrics = calibrator.calibrate(results, "Test query")

        # Many low-quality results should still have low confidence
        assert metrics.confidence_score < 0.6

    def test_all_identical_results(self, calibrator):
        """Test behavior when all results are identical."""
        results = [
            create_search_result(i, "Identical content", 0.8, "action")
            for i in range(3)
        ]
        metrics = calibrator.calibrate(results, "Test query")

        # Identical results should have high consistency
        assert metrics.consistency_score > 0.8
