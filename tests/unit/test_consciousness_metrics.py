"""Tests for consciousness metrics system.

Tests the main ConsciousnessMetrics interface and scoring system.
"""

import pytest
from datetime import datetime, timedelta
from athena.consciousness.metrics import ConsciousnessMetrics, ConsciousnessScore
from athena.consciousness.indicators import IndicatorScore


class TestConsciousnessScore:
    """Test ConsciousnessScore data class."""

    def test_consciousness_score_creation(self):
        """Test creating a consciousness score."""
        now = datetime.now()
        indicators = {
            "test_indicator": IndicatorScore(
                name="test_indicator", score=5.0, confidence=0.7
            )
        }
        score = ConsciousnessScore(
            timestamp=now,
            overall_score=5.0,
            indicators=indicators,
            trend="stable",
            confidence=0.7,
        )
        assert score.overall_score == 5.0
        assert score.trend == "stable"
        assert score.confidence == 0.7
        assert len(score.indicators) == 1

    def test_consciousness_score_to_dict(self):
        """Test converting score to dictionary for API."""
        indicators = {
            "test_indicator": IndicatorScore(
                name="test_indicator",
                score=5.5,
                confidence=0.8,
                components={"component1": 5.0},
                evidence=["Test evidence"],
            )
        }
        score = ConsciousnessScore(
            overall_score=5.5,
            indicators=indicators,
            trend="increasing",
            confidence=0.8,
        )
        result = score.to_dict()

        assert "timestamp" in result
        assert result["overall_score"] == 5.5
        assert result["trend"] == "increasing"
        assert result["confidence"] == 0.8
        assert "indicators" in result
        assert "test_indicator" in result["indicators"]

    def test_consciousness_score_dict_format(self):
        """Test that to_dict produces proper JSON-serializable format."""
        indicators = {
            "indicator1": IndicatorScore(
                name="indicator1",
                score=7.0,
                confidence=0.9,
                components={"comp1": 7.1, "comp2": 6.9},
                evidence=["Evidence 1", "Evidence 2"],
            )
        }
        score = ConsciousnessScore(
            overall_score=7.0,
            indicators=indicators,
            confidence=0.9,
        )
        result = score.to_dict()

        # Check rounding
        assert result["overall_score"] == 7.0
        assert result["indicators"]["indicator1"]["score"] == 7.0
        assert result["indicators"]["indicator1"]["confidence"] == 0.9

        # Check components are rounded
        comps = result["indicators"]["indicator1"]["components"]
        assert comps["comp1"] == 7.1
        assert comps["comp2"] == 6.9

        # Check evidence is preserved
        assert result["indicators"]["indicator1"]["evidence"] == [
            "Evidence 1",
            "Evidence 2",
        ]


class TestConsciousnessMetrics:
    """Test ConsciousnessMetrics system."""

    def test_consciousness_metrics_creation(self):
        """Test creating consciousness metrics system."""
        metrics = ConsciousnessMetrics()
        assert metrics is not None
        assert metrics.history == []
        assert metrics.last_score is None
        assert metrics.history_limit == 100

    def test_consciousness_metrics_with_custom_limit(self):
        """Test creating metrics with custom history limit."""
        metrics = ConsciousnessMetrics(history_limit=50)
        assert metrics.history_limit == 50

    @pytest.mark.asyncio
    async def test_measure_consciousness(self):
        """Test measuring consciousness."""
        metrics = ConsciousnessMetrics()
        score = await metrics.measure_consciousness()

        assert isinstance(score, ConsciousnessScore)
        assert 0 <= score.overall_score <= 10
        assert score.trend in ["increasing", "decreasing", "stable"]
        assert 0 <= score.confidence <= 1
        assert len(score.indicators) == 6

    @pytest.mark.asyncio
    async def test_measurement_added_to_history(self):
        """Test that measurements are added to history."""
        metrics = ConsciousnessMetrics()
        assert len(metrics.history) == 0

        await metrics.measure_consciousness()
        assert len(metrics.history) == 1

        await metrics.measure_consciousness()
        assert len(metrics.history) == 2

    @pytest.mark.asyncio
    async def test_last_score_updated(self):
        """Test that last_score is updated on measurement."""
        metrics = ConsciousnessMetrics()
        assert metrics.last_score is None

        score1 = await metrics.measure_consciousness()
        assert metrics.last_score == score1

        score2 = await metrics.measure_consciousness()
        assert metrics.last_score == score2
        assert metrics.last_score != score1

    @pytest.mark.asyncio
    async def test_history_limit_respected(self):
        """Test that history respects size limit."""
        metrics = ConsciousnessMetrics(history_limit=5)

        # Add 10 measurements
        for _ in range(10):
            await metrics.measure_consciousness()

        # Should only keep last 5
        assert len(metrics.history) == 5

    @pytest.mark.asyncio
    async def test_trend_calculation_stable(self):
        """Test trend calculation for stable scores."""
        metrics = ConsciousnessMetrics()

        # Measure multiple times - should be relatively stable
        for _ in range(3):
            score = await metrics.measure_consciousness()

        # Last score should be stable (small change)
        assert metrics.last_score.trend in ["stable", "increasing", "decreasing"]

    @pytest.mark.asyncio
    async def test_trend_calculation_with_history(self):
        """Test trend calculation uses previous measurements."""
        metrics = ConsciousnessMetrics()

        # Manually add history (need at least 2 items for trend calculation)
        score1 = ConsciousnessScore(overall_score=5.0)
        score2 = ConsciousnessScore(overall_score=5.2)
        metrics.history.append(score1)
        metrics.history.append(score2)

        # Calculate trend
        trend = metrics._calculate_trend(7.5)  # Increase of 2.3 from last (5.2)
        assert trend == "increasing"

        # Decrease
        trend = metrics._calculate_trend(3.5)  # Decrease of 1.7 from last (5.2)
        assert trend == "decreasing"

        # Stable (small change < 0.5 threshold)
        trend = metrics._calculate_trend(5.3)  # Change of 0.1
        assert trend == "stable"

    def test_get_history_all(self):
        """Test getting full history."""
        metrics = ConsciousnessMetrics()

        # Manually add some scores
        for i in range(3):
            score = ConsciousnessScore(overall_score=float(i))
            metrics.history.append(score)

        history = metrics.get_history()
        assert len(history) == 3
        # Should be a copy, not reference
        assert history is not metrics.history

    def test_get_history_limited(self):
        """Test getting limited history."""
        metrics = ConsciousnessMetrics()

        # Add 10 scores
        for i in range(10):
            score = ConsciousnessScore(overall_score=float(i))
            metrics.history.append(score)

        # Get last 3
        history = metrics.get_history(limit=3)
        assert len(history) == 3
        assert history[0].overall_score == 7.0
        assert history[-1].overall_score == 9.0

    def test_get_history_limit_exceeds_available(self):
        """Test get_history when limit > available history."""
        metrics = ConsciousnessMetrics()

        for i in range(3):
            score = ConsciousnessScore(overall_score=float(i))
            metrics.history.append(score)

        history = metrics.get_history(limit=10)
        assert len(history) == 3

    def test_get_statistics_empty(self):
        """Test statistics with no history."""
        metrics = ConsciousnessMetrics()
        stats = metrics.get_statistics()

        assert stats["measurements"] == 0
        assert stats["average_score"] == 0.0
        assert stats["min_score"] == 0.0
        assert stats["max_score"] == 0.0
        assert stats["current_score"] == 0.0
        assert stats["trend"] == "stable"

    def test_get_statistics_with_history(self):
        """Test statistics calculation with history."""
        metrics = ConsciousnessMetrics()

        # Add measurements
        scores = [3.0, 5.0, 7.0, 6.0, 4.0]
        for s in scores:
            score = ConsciousnessScore(overall_score=s)
            metrics.history.append(score)
            metrics.last_score = score

        stats = metrics.get_statistics()
        assert stats["measurements"] == 5
        assert stats["average_score"] == 5.0
        assert stats["min_score"] == 3.0
        assert stats["max_score"] == 7.0
        assert stats["current_score"] == 4.0
        assert "first_measurement" in stats
        assert "last_measurement" in stats

    def test_compare_indicators_empty(self):
        """Test indicator comparison with no history."""
        metrics = ConsciousnessMetrics()
        comparison = metrics.compare_indicators()

        assert comparison["measurements"] == 0
        assert comparison["indicators"] == {}

    @pytest.mark.asyncio
    async def test_compare_indicators_with_history(self):
        """Test indicator comparison with measurements."""
        metrics = ConsciousnessMetrics()

        # Add some measurements
        for _ in range(3):
            await metrics.measure_consciousness()

        comparison = metrics.compare_indicators(window_size=10)

        assert comparison["window_size"] == 3
        assert len(comparison["indicators"]) == 6
        assert "period" in comparison

        # Each indicator should have min/max/avg/current
        for indicator_name, data in comparison["indicators"].items():
            assert "average" in data
            assert "min" in data
            assert "max" in data
            assert "current" in data

    def test_reset_history(self):
        """Test resetting history."""
        metrics = ConsciousnessMetrics()

        # Add some scores
        for i in range(5):
            score = ConsciousnessScore(overall_score=float(i))
            metrics.history.append(score)
            metrics.last_score = score

        assert len(metrics.history) == 5
        assert metrics.last_score is not None

        # Reset
        metrics.reset_history()
        assert len(metrics.history) == 0
        assert metrics.last_score is None

    def test_as_dict_no_measurement(self):
        """Test as_dict when no measurement has been made."""
        metrics = ConsciousnessMetrics()
        result = metrics.as_dict()

        assert result["status"] == "not_measured"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_as_dict_with_measurement(self):
        """Test as_dict after measurement."""
        metrics = ConsciousnessMetrics()
        await metrics.measure_consciousness()

        result = metrics.as_dict()
        assert result != {"status": "not_measured", "message": "No consciousness measurements yet"}
        assert "timestamp" in result
        assert "overall_score" in result
        assert "indicators" in result

    def test_repr(self):
        """Test string representation."""
        metrics = ConsciousnessMetrics()
        assert "ConsciousnessMetrics(not_measured)" in repr(metrics)

    @pytest.mark.asyncio
    async def test_repr_with_measurement(self):
        """Test repr after measurement."""
        metrics = ConsciousnessMetrics()
        await metrics.measure_consciousness()

        repr_str = repr(metrics)
        assert "ConsciousnessMetrics(" in repr_str
        assert "score=" in repr_str
        assert "trend=" in repr_str
        assert "measurements=" in repr_str


class TestConsciousnessMetricsIntegration:
    """Integration tests for consciousness metrics."""

    @pytest.mark.asyncio
    async def test_full_measurement_workflow(self):
        """Test complete measurement workflow."""
        metrics = ConsciousnessMetrics()

        # Take multiple measurements
        for i in range(5):
            score = await metrics.measure_consciousness()
            assert isinstance(score, ConsciousnessScore)

        # Check history
        assert len(metrics.history) == 5

        # Get statistics
        stats = metrics.get_statistics()
        assert stats["measurements"] == 5

        # Get history
        history = metrics.get_history(limit=3)
        assert len(history) == 3

        # Compare indicators
        comparison = metrics.compare_indicators(window_size=5)
        assert len(comparison["indicators"]) == 6

    @pytest.mark.asyncio
    async def test_consciousness_score_serialization(self):
        """Test that consciousness scores can be serialized to dict."""
        metrics = ConsciousnessMetrics()
        score = await metrics.measure_consciousness()

        # Convert to dict
        result = score.to_dict()

        # Verify structure
        assert isinstance(result, dict)
        assert "overall_score" in result
        assert "indicators" in result
        assert "timestamp" in result
        assert "confidence" in result
        assert "trend" in result

    @pytest.mark.asyncio
    async def test_consciousness_metrics_consistency(self):
        """Test that repeated measurements are reasonably consistent."""
        metrics = ConsciousnessMetrics()

        # Take measurements in quick succession
        scores = []
        for _ in range(3):
            score = await metrics.measure_consciousness()
            scores.append(score.overall_score)

        # Scores should be relatively close (within 3 points)
        for i in range(len(scores) - 1):
            assert abs(scores[i] - scores[i + 1]) <= 3.0
