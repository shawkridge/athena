"""Tests for consciousness indicators.

Tests all 6 consciousness indicators:
1. Global Workspace
2. Information Integration
3. Selective Attention
4. Working Memory
5. Meta-Cognition
6. Temporal Continuity
"""

import pytest
from datetime import datetime, timedelta
from athena.consciousness.indicators import (
    IndicatorScore,
    GlobalWorkspaceIndicator,
    InformationIntegrationIndicator,
    SelectiveAttentionIndicator,
    WorkingMemoryIndicator,
    MetaCognitionIndicator,
    TemporalContinuityIndicator,
    ConsciousnessIndicators,
)


class TestIndicatorScore:
    """Test IndicatorScore data structure."""

    def test_indicator_score_creation(self):
        """Test creating an indicator score."""
        score = IndicatorScore(
            name="test_indicator",
            score=5.0,
            confidence=0.8,
            evidence=["Test evidence"],
        )
        assert score.name == "test_indicator"
        assert score.score == 5.0
        assert score.confidence == 0.8
        assert score.evidence == ["Test evidence"]
        assert isinstance(score.timestamp, datetime)

    def test_indicator_score_validation_clamps_high(self):
        """Test that scores > 10 are clamped to 10."""
        score = IndicatorScore(name="test", score=15.0)
        assert score.score == 10.0

    def test_indicator_score_validation_clamps_low(self):
        """Test that scores < 0 are clamped to 0."""
        score = IndicatorScore(name="test", score=-5.0)
        assert score.score == 0.0

    def test_indicator_score_components(self):
        """Test components field."""
        components = {"component1": 4.5, "component2": 5.5}
        score = IndicatorScore(
            name="test", score=5.0, components=components
        )
        assert score.components == components

    def test_indicator_score_default_values(self):
        """Test default values."""
        score = IndicatorScore(name="test", score=5.0)
        assert score.confidence == 0.5
        assert score.evidence == []
        assert isinstance(score.timestamp, datetime)


class TestGlobalWorkspaceIndicator:
    """Test Global Workspace Theory indicator."""

    @pytest.mark.asyncio
    async def test_global_workspace_creation(self):
        """Test creating Global Workspace indicator."""
        indicator = GlobalWorkspaceIndicator()
        assert indicator is not None

    @pytest.mark.asyncio
    async def test_global_workspace_measure(self):
        """Test measuring global workspace."""
        indicator = GlobalWorkspaceIndicator()
        score = await indicator.measure()
        assert isinstance(score, IndicatorScore)
        assert score.name == "global_workspace"
        assert 0 <= score.score <= 10
        assert 0 <= score.confidence <= 1
        assert len(score.evidence) > 0

    @pytest.mark.asyncio
    async def test_global_workspace_components(self):
        """Test that global workspace has sub-components."""
        indicator = GlobalWorkspaceIndicator()
        score = await indicator.measure()
        # Should have components like saturation, broadcasting, competition
        assert "components" in score.__dict__
        assert isinstance(score.components, dict)


class TestInformationIntegrationIndicator:
    """Test Information Integration indicator."""

    @pytest.mark.asyncio
    async def test_information_integration_creation(self):
        """Test creating Information Integration indicator."""
        indicator = InformationIntegrationIndicator()
        assert indicator is not None

    @pytest.mark.asyncio
    async def test_information_integration_measure(self):
        """Test measuring information integration."""
        indicator = InformationIntegrationIndicator()
        score = await indicator.measure()
        assert isinstance(score, IndicatorScore)
        assert score.name == "information_integration"
        assert 0 <= score.score <= 10
        assert 0 <= score.confidence <= 1


class TestSelectiveAttentionIndicator:
    """Test Selective Attention indicator."""

    @pytest.mark.asyncio
    async def test_selective_attention_creation(self):
        """Test creating Selective Attention indicator."""
        indicator = SelectiveAttentionIndicator()
        assert indicator is not None

    @pytest.mark.asyncio
    async def test_selective_attention_measure(self):
        """Test measuring selective attention."""
        indicator = SelectiveAttentionIndicator()
        score = await indicator.measure()
        assert isinstance(score, IndicatorScore)
        assert score.name == "selective_attention"
        assert 0 <= score.score <= 10
        assert 0 <= score.confidence <= 1


class TestWorkingMemoryIndicator:
    """Test Working Memory indicator."""

    @pytest.mark.asyncio
    async def test_working_memory_creation(self):
        """Test creating Working Memory indicator."""
        indicator = WorkingMemoryIndicator()
        assert indicator is not None

    @pytest.mark.asyncio
    async def test_working_memory_measure(self):
        """Test measuring working memory."""
        indicator = WorkingMemoryIndicator()
        score = await indicator.measure()
        assert isinstance(score, IndicatorScore)
        assert score.name == "working_memory"
        assert 0 <= score.score <= 10
        assert 0 <= score.confidence <= 1


class TestMetaCognitionIndicator:
    """Test Meta-Cognition indicator."""

    @pytest.mark.asyncio
    async def test_meta_cognition_creation(self):
        """Test creating Meta-Cognition indicator."""
        indicator = MetaCognitionIndicator()
        assert indicator is not None

    @pytest.mark.asyncio
    async def test_meta_cognition_measure(self):
        """Test measuring meta-cognition."""
        indicator = MetaCognitionIndicator()
        score = await indicator.measure()
        assert isinstance(score, IndicatorScore)
        assert score.name == "meta_cognition"
        assert 0 <= score.score <= 10
        assert 0 <= score.confidence <= 1


class TestTemporalContinuityIndicator:
    """Test Temporal Continuity indicator."""

    @pytest.mark.asyncio
    async def test_temporal_continuity_creation(self):
        """Test creating Temporal Continuity indicator."""
        indicator = TemporalContinuityIndicator()
        assert indicator is not None

    @pytest.mark.asyncio
    async def test_temporal_continuity_measure(self):
        """Test measuring temporal continuity."""
        indicator = TemporalContinuityIndicator()
        score = await indicator.measure()
        assert isinstance(score, IndicatorScore)
        assert score.name == "temporal_continuity"
        assert 0 <= score.score <= 10
        assert 0 <= score.confidence <= 1


class TestConsciousnessIndicators:
    """Test the unified ConsciousnessIndicators system."""

    @pytest.mark.asyncio
    async def test_consciousness_indicators_creation(self):
        """Test creating consciousness indicators system."""
        indicators = ConsciousnessIndicators()
        assert indicators is not None

    @pytest.mark.asyncio
    async def test_measure_all_indicators(self):
        """Test measuring all 6 indicators at once."""
        indicators = ConsciousnessIndicators()
        results = await indicators.measure_all()

        # Should have all 6 indicators
        assert len(results) == 6
        expected_names = {
            "global_workspace",
            "information_integration",
            "selective_attention",
            "working_memory",
            "meta_cognition",
            "temporal_continuity",
        }
        assert set(results.keys()) == expected_names

        # Each should be a valid IndicatorScore
        for name, score in results.items():
            assert isinstance(score, IndicatorScore)
            assert score.name == name
            assert 0 <= score.score <= 10
            assert 0 <= score.confidence <= 1

    @pytest.mark.asyncio
    async def test_overall_score(self):
        """Test calculating overall consciousness score."""
        indicators = ConsciousnessIndicators()
        overall = await indicators.overall_score()
        assert 0 <= overall <= 10

    @pytest.mark.asyncio
    async def test_measure_global_workspace_directly(self):
        """Test measuring global workspace indicator directly."""
        indicators = ConsciousnessIndicators()
        score = await indicators.global_workspace.measure()
        assert isinstance(score, IndicatorScore)
        assert score.name == "global_workspace"

    @pytest.mark.asyncio
    async def test_access_all_indicators(self):
        """Test accessing individual indicator objects."""
        indicators = ConsciousnessIndicators()

        # Check all indicators are accessible
        assert hasattr(indicators, "global_workspace")
        assert hasattr(indicators, "information_integration")
        assert hasattr(indicators, "selective_attention")
        assert hasattr(indicators, "working_memory")
        assert hasattr(indicators, "meta_cognition")
        assert hasattr(indicators, "temporal_continuity")

    @pytest.mark.asyncio
    async def test_indicator_consistency(self):
        """Test that repeated measurements are consistent."""
        indicators = ConsciousnessIndicators()

        # Measure global workspace twice
        score1 = await indicators.global_workspace.measure()
        score2 = await indicators.global_workspace.measure()

        # Should have same name
        assert score1.name == score2.name

        # Should be reasonably close (within 2 points due to stochasticity)
        assert abs(score1.score - score2.score) <= 2.0

    @pytest.mark.asyncio
    async def test_all_indicators_produce_valid_evidence(self):
        """Test that all indicators produce evidence for their scores."""
        indicators = ConsciousnessIndicators()
        results = await indicators.measure_all()

        for name, score in results.items():
            assert len(score.evidence) > 0, f"{name} should have evidence"
            assert all(isinstance(e, str) for e in score.evidence)

    @pytest.mark.asyncio
    async def test_indicators_have_components(self):
        """Test that indicators have detailed components."""
        indicators = ConsciousnessIndicators()
        results = await indicators.measure_all()

        for name, score in results.items():
            # Most indicators should have components for detailed analysis
            if name in ["global_workspace", "information_integration", "working_memory"]:
                assert len(score.components) > 0, f"{name} should have components"
