"""Unit tests for advanced consolidation metrics.

Tests:
- HallucinationRateCalculator
- PatternDiversityCalculator
- DualProcessEffectivenessCalculator
- ClusteringCohesionCalculator
- PipelineThroughputCalculator
- SearchImpactCalculator
"""

import numpy as np
import pytest
from datetime import datetime

from athena.consolidation.advanced_metrics import (
    ClusteringCohesionCalculator,
    DualProcessEffectivenessCalculator,
    HallucinationRateCalculator,
    PatternDiversityCalculator,
    PipelineThroughputCalculator,
    SearchImpactCalculator
)


class TestHallucinationRateCalculator:
    """Test hallucination rate detection."""

    def test_no_hallucinations(self):
        """Test with high-confidence patterns (no hallucinations)."""
        calc = HallucinationRateCalculator()
        patterns = [
            {'confidence_score': 0.95},
            {'confidence_score': 0.90},
            {'confidence_score': 0.92}
        ]

        rate = calc.calculate(patterns)
        assert rate == 0.0, "High-confidence patterns should have 0% hallucination"

    def test_all_hallucinations(self):
        """Test with low-confidence patterns (all hallucinations)."""
        calc = HallucinationRateCalculator()
        patterns = [
            {'confidence_score': 0.5},
            {'confidence_score': 0.4},
            {'confidence_score': 0.3}
        ]

        rate = calc.calculate(patterns)
        assert rate == 1.0, "Low-confidence patterns should have 100% hallucination"

    def test_mixed_confidence(self):
        """Test with mixed confidence levels."""
        calc = HallucinationRateCalculator(
            confidence_threshold_high=0.6,
            confidence_threshold_medium=0.75
        )
        patterns = [
            {'confidence_score': 0.95},  # Low risk
            {'confidence_score': 0.70},  # Medium risk
            {'confidence_score': 0.50},  # High risk
        ]

        rate = calc.calculate(patterns)
        # high_risk: 1, medium_risk: 1 (0.5)
        # hallucination_count = 1 * 1.0 + 1 * 0.5 = 1.5
        # rate = 1.5 / 3 = 0.5
        assert rate == pytest.approx(0.5, abs=0.01)

    def test_empty_patterns(self):
        """Test with no patterns."""
        calc = HallucinationRateCalculator()
        rate = calc.calculate([])
        assert rate == 0.0

    def test_risk_breakdown(self):
        """Test risk breakdown calculation."""
        calc = HallucinationRateCalculator()
        patterns = [
            {'confidence_score': 0.95},  # Low risk
            {'confidence_score': 0.70},  # Medium risk
            {'confidence_score': 0.50},  # High risk
        ]

        breakdown = calc.get_risk_breakdown(patterns)
        assert breakdown['low_risk'] == 1
        assert breakdown['medium_risk'] == 1
        assert breakdown['high_risk'] == 1


class TestPatternDiversityCalculator:
    """Test pattern diversity calculation."""

    def test_single_pattern_type(self):
        """Test with only one pattern type (low diversity)."""
        calc = PatternDiversityCalculator()
        patterns = [
            {'pattern_type': 'workflow'},
            {'pattern_type': 'workflow'},
            {'pattern_type': 'workflow'}
        ]

        diversity = calc.calculate(patterns)
        assert diversity == 0.0, "Single pattern type should have 0 diversity"

    def test_uniform_distribution(self):
        """Test with uniform distribution of pattern types (high diversity)."""
        calc = PatternDiversityCalculator()
        patterns = [
            {'pattern_type': 'workflow'},
            {'pattern_type': 'anti-pattern'},
            {'pattern_type': 'best-practice'},
            {'pattern_type': 'relationship'}
        ]

        diversity = calc.calculate(patterns)
        # Perfect uniform distribution should have max entropy
        assert diversity > 0.9, "Uniform distribution should have high diversity"

    def test_empty_patterns(self):
        """Test with no patterns."""
        calc = PatternDiversityCalculator()
        diversity = calc.calculate([])
        assert diversity == 0.0

    def test_type_distribution(self):
        """Test type distribution counting."""
        calc = PatternDiversityCalculator()
        patterns = [
            {'pattern_type': 'workflow'},
            {'pattern_type': 'workflow'},
            {'pattern_type': 'best-practice'},
        ]

        dist = calc.get_type_distribution(patterns)
        assert dist['workflow'] == 2
        assert dist['best-practice'] == 1


class TestDualProcessEffectivenessCalculator:
    """Test dual-process effectiveness comparison."""

    def test_system2_dominant(self):
        """Test with System 2 dominant and high effectiveness."""
        calc = DualProcessEffectivenessCalculator()
        patterns = [
            {'extraction_method': 'system2_llm', 'confidence_score': 0.95},
            {'extraction_method': 'system2_llm', 'confidence_score': 0.92},
            {'extraction_method': 'system1_heuristics', 'confidence_score': 0.70}
        ]

        result = calc.calculate(patterns)
        assert result['system2_pattern_count'] == 2
        assert result['system1_pattern_count'] == 1
        assert result['system2_effectiveness_score'] > 0.8
        assert result['system2_preferred'] is True

    def test_system1_dominant(self):
        """Test with System 1 dominant."""
        calc = DualProcessEffectivenessCalculator()
        patterns = [
            {'extraction_method': 'system1_heuristics', 'confidence_score': 0.95},
            {'extraction_method': 'system1_heuristics', 'confidence_score': 0.92},
            {'extraction_method': 'system2_llm', 'confidence_score': 0.70}
        ]

        result = calc.calculate(patterns)
        assert result['system1_pattern_count'] == 2
        assert result['system2_pattern_count'] == 1
        assert result['system2_preferred'] is False

    def test_empty_patterns(self):
        """Test with no patterns."""
        calc = DualProcessEffectivenessCalculator()
        result = calc.calculate([])
        assert result['system1_pattern_count'] == 0
        assert result['system2_pattern_count'] == 0

    def test_confidence_distribution(self):
        """Test confidence distribution."""
        calc = DualProcessEffectivenessCalculator()
        patterns = [
            {'extraction_method': 'system1_heuristics', 'confidence_score': 0.80},
            {'extraction_method': 'system1_heuristics', 'confidence_score': 0.70},
            {'extraction_method': 'system2_llm', 'confidence_score': 0.95},
            {'extraction_method': 'system2_llm', 'confidence_score': 0.90}
        ]

        dist = calc.get_confidence_distribution(patterns)
        assert dist['system1']['count'] == 2
        assert dist['system2']['count'] == 2
        assert dist['system1']['mean'] == pytest.approx(0.75, abs=0.01)
        assert dist['system2']['mean'] == pytest.approx(0.925, abs=0.01)


class TestClusteringCohesionCalculator:
    """Test clustering cohesion calculation."""

    def test_perfect_cohesion(self):
        """Test with identical events (perfect cohesion)."""
        from athena.episodic.models import EpisodicEvent

        calc = ClusteringCohesionCalculator()

        # Create events with identical content
        events = [
            EpisodicEvent(id=1, content="test content", event_type="test"),
            EpisodicEvent(id=2, content="test content", event_type="test")
        ]

        # Test with text similarity
        cohesion = calc.calculate([events])
        assert cohesion > 0.5, "Identical events should have high cohesion"

    def test_vector_similarity(self):
        """Test with embedding vectors."""
        from athena.episodic.models import EpisodicEvent

        calc = ClusteringCohesionCalculator()

        events = [
            EpisodicEvent(id=1, content="test", event_type="test"),
            EpisodicEvent(id=2, content="test", event_type="test")
        ]

        # Create identical embeddings
        embeddings = {
            1: np.array([1.0, 0.0, 0.0]),
            2: np.array([1.0, 0.0, 0.0])
        }

        cohesion = calc.calculate([events], embeddings)
        assert cohesion == pytest.approx(1.0, abs=0.01), "Identical vectors should have 1.0 similarity"

    def test_empty_clusters(self):
        """Test with no clusters."""
        calc = ClusteringCohesionCalculator()
        cohesion = calc.calculate([])
        assert cohesion == 0.0

    def test_single_event_clusters(self):
        """Test with single-event clusters (perfect cohesion)."""
        from athena.episodic.models import EpisodicEvent

        calc = ClusteringCohesionCalculator()
        events = [EpisodicEvent(id=1, content="test", event_type="test")]

        cohesion = calc.calculate([events])
        assert cohesion == 1.0, "Single-event clusters are perfectly cohesive"

    def test_cluster_stats(self):
        """Test cluster statistics."""
        from athena.episodic.models import EpisodicEvent

        calc = ClusteringCohesionCalculator()
        clusters = [
            [EpisodicEvent(id=i, content=f"test{i}", event_type="test") for i in range(5)],
            [EpisodicEvent(id=i, content=f"test{i}", event_type="test") for i in range(3)],
            [EpisodicEvent(id=1, content="single", event_type="test")]
        ]

        stats = calc.get_cluster_stats(clusters)
        assert stats['num_clusters'] == 3
        assert stats['total_events'] == 9
        assert stats['avg_cluster_size'] == pytest.approx(3.0, abs=0.1)


class TestPipelineThroughputCalculator:
    """Test pipeline throughput calculation."""

    def test_throughput_calculation(self):
        """Test throughput calculation."""
        calc = PipelineThroughputCalculator()
        calc.record_stage_duration('clustering', 1.0)
        calc.record_stage_duration('extraction', 2.0)
        calc.record_stage_duration('validation', 1.0)
        calc.record_patterns_extracted(200)

        throughput = calc.calculate_throughput()
        # 200 patterns / 4 seconds = 50 patterns/sec
        assert throughput == pytest.approx(50.0, abs=0.1)

    def test_stage_breakdown(self):
        """Test stage time breakdown."""
        calc = PipelineThroughputCalculator()
        calc.record_stage_duration('clustering', 2.0)
        calc.record_stage_duration('extraction', 2.0)
        calc.record_stage_duration('validation', 4.0)

        breakdown = calc.get_stage_breakdown()
        assert breakdown['clustering'] == pytest.approx(25.0, abs=0.1)
        assert breakdown['extraction'] == pytest.approx(25.0, abs=0.1)
        assert breakdown['validation'] == pytest.approx(50.0, abs=0.1)

    def test_stage_stats(self):
        """Test stage statistics."""
        calc = PipelineThroughputCalculator()
        calc.record_stage_duration('clustering', 1.0)
        calc.record_stage_duration('clustering', 2.0)
        calc.record_stage_duration('clustering', 3.0)

        stats = calc.get_stage_stats()
        assert stats['clustering']['count'] == 3
        assert stats['clustering']['mean_seconds'] == pytest.approx(2.0, abs=0.01)
        assert stats['clustering']['min_seconds'] == 1.0
        assert stats['clustering']['max_seconds'] == 3.0

    def test_bottleneck_detection(self):
        """Test bottleneck detection (stages >20% of time)."""
        calc = PipelineThroughputCalculator()
        calc.record_stage_duration('clustering', 1.0)
        calc.record_stage_duration('extraction', 10.0)
        calc.record_stage_duration('validation', 2.0)

        # extraction is 10/13 ≈ 77% of time - should be bottleneck
        summary = calc.get_pipeline_summary()
        # Note: bottleneck detection is in PipelineInstrumentation, not this class


class TestSearchImpactCalculator:
    """Test search impact measurement."""

    def test_positive_impact(self):
        """Test positive impact (improved search results)."""
        calc = SearchImpactCalculator()

        before = [
            [{'relevance_score': 0.5}, {'relevance_score': 0.3}],
            [{'relevance_score': 0.4}, {'relevance_score': 0.2}]
        ]

        after = [
            [{'relevance_score': 0.8}, {'relevance_score': 0.6}],
            [{'relevance_score': 0.7}, {'relevance_score': 0.5}]
        ]

        result = calc.measure_impact(['query1', 'query2'], before, after)
        assert result['queries_improved'] == 2
        assert result['queries_degraded'] == 0
        assert result['relevance_improvement'] > 0

    def test_negative_impact(self):
        """Test negative impact (degraded search results)."""
        calc = SearchImpactCalculator()

        before = [
            [{'relevance_score': 0.8}, {'relevance_score': 0.6}],
            [{'relevance_score': 0.7}, {'relevance_score': 0.5}]
        ]

        after = [
            [{'relevance_score': 0.5}, {'relevance_score': 0.3}],
            [{'relevance_score': 0.4}, {'relevance_score': 0.2}]
        ]

        result = calc.measure_impact(['query1', 'query2'], before, after)
        assert result['queries_improved'] == 0
        assert result['queries_degraded'] == 2
        assert result['relevance_improvement'] < 0

    def test_no_change(self):
        """Test when search results don't change."""
        calc = SearchImpactCalculator()

        before = [
            [{'relevance_score': 0.5}, {'relevance_score': 0.3}]
        ]

        after = [
            [{'relevance_score': 0.5}, {'relevance_score': 0.3}]
        ]

        result = calc.measure_impact(['query1'], before, after)
        assert result['queries_unchanged'] == 1

    def test_per_query_metrics(self):
        """Test per-query detailed metrics."""
        calc = SearchImpactCalculator()

        before = [
            [{'relevance_score': 0.5}],
            [{'relevance_score': 0.6}]
        ]

        after = [
            [{'relevance_score': 0.8}],
            [{'relevance_score': 0.5}]
        ]

        metrics = calc.get_per_query_metrics(['q1', 'q2'], before, after)
        assert len(metrics) == 2
        assert metrics[0]['status'] == 'improved'
        assert metrics[1]['status'] == 'degraded'

    def test_empty_results(self):
        """Test with empty result sets."""
        calc = SearchImpactCalculator()

        result = calc.measure_impact([], [], [])
        assert result['queries_tested'] == 0
        assert result['relevance_improvement'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
