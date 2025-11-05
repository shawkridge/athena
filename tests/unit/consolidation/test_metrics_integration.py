"""Unit tests for metrics integration and validation.

Tests:
- ConsolidationMetricsCollector
- MetricsValidator
- MetricsAnalyzer
"""

import pytest
from datetime import datetime

from athena.consolidation.metrics_integration import (
    ConsolidationMetrics,
    ConsolidationMetricsCollector,
    MetricsAnalyzer,
    MetricsTargets,
    MetricsValidator
)


class TestConsolidationMetrics:
    """Test ConsolidationMetrics data model."""

    def test_metrics_creation(self):
        """Test creating metrics object."""
        metrics = ConsolidationMetrics(
            compression_ratio=0.75,
            recall_at_5=0.85,
            pattern_consistency=0.80,
            information_density=0.75,
            hallucination_rate=0.05,
            pattern_diversity_score=0.90,
            system2_effectiveness_score=0.88,
            clustering_cohesion_score=0.82,
            throughput_patterns_per_sec=75.0,
            search_impact_avg=0.18
        )

        assert metrics.compression_ratio == 0.75
        assert metrics.recall_at_5 == 0.85
        assert metrics.created_at is not None

    def test_metrics_defaults(self):
        """Test metrics with default values."""
        metrics = ConsolidationMetrics(
            compression_ratio=0.75,
            recall_at_5=0.85,
            pattern_consistency=0.80,
            information_density=0.75,
            hallucination_rate=0.05,
            pattern_diversity_score=0.90,
            system2_effectiveness_score=0.88,
            clustering_cohesion_score=0.82,
            throughput_patterns_per_sec=75.0,
            search_impact_avg=0.18
        )

        assert metrics.consolidation_run_id is None
        assert metrics.metric_details == {}
        assert isinstance(metrics.created_at, datetime)


class TestMetricsValidator:
    """Test metrics validation against targets."""

    def test_all_metrics_pass(self):
        """Test with all metrics passing targets."""
        validator = MetricsValidator()
        metrics = ConsolidationMetrics(
            compression_ratio=0.75,  # In range [0.70, 0.85]
            recall_at_5=0.85,        # In range [0.80, 1.0]
            pattern_consistency=0.80,  # >= 0.75
            information_density=0.75,  # >= 0.70
            hallucination_rate=0.05,   # <= 0.10
            pattern_diversity_score=0.90,  # >= 0.85
            system2_effectiveness_score=0.88,  # >= 0.85
            clustering_cohesion_score=0.85,    # >= 0.80
            throughput_patterns_per_sec=75.0,  # >= 50.0
            search_impact_avg=0.17  # In range [0.15, 0.20]
        )

        results = validator.validate(metrics)
        assert results['overall_status'] == 'pass'
        assert results['metrics_failed'] == 0
        assert results['metrics_passed'] > 0

    def test_compression_fails(self):
        """Test with low compression ratio."""
        validator = MetricsValidator()
        metrics = ConsolidationMetrics(
            compression_ratio=0.60,  # Below 0.70 threshold
            recall_at_5=0.85,
            pattern_consistency=0.80,
            information_density=0.75,
            hallucination_rate=0.05,
            pattern_diversity_score=0.90,
            system2_effectiveness_score=0.88,
            clustering_cohesion_score=0.85,
            throughput_patterns_per_sec=75.0,
            search_impact_avg=0.17
        )

        results = validator.validate(metrics)
        assert results['overall_status'] == 'fail'
        assert 'compression_ratio' in results['failed_metrics']

    def test_hallucination_fails(self):
        """Test with high hallucination rate."""
        validator = MetricsValidator()
        metrics = ConsolidationMetrics(
            compression_ratio=0.75,
            recall_at_5=0.85,
            pattern_consistency=0.80,
            information_density=0.75,
            hallucination_rate=0.15,  # Above 0.10 threshold
            pattern_diversity_score=0.90,
            system2_effectiveness_score=0.88,
            clustering_cohesion_score=0.85,
            throughput_patterns_per_sec=75.0,
            search_impact_avg=0.17
        )

        results = validator.validate(metrics)
        assert 'hallucination_rate' in results['failed_metrics']

    def test_custom_targets(self):
        """Test with custom metric targets."""
        targets = MetricsTargets(
            compression_ratio_min=0.80,  # Stricter than default 0.70
            recall_at_5_min=0.90         # Stricter than default 0.80
        )
        validator = MetricsValidator(targets)

        metrics = ConsolidationMetrics(
            compression_ratio=0.75,  # Fails new stricter target
            recall_at_5=0.85,        # Fails new stricter target
            pattern_consistency=0.80,
            information_density=0.75,
            hallucination_rate=0.05,
            pattern_diversity_score=0.90,
            system2_effectiveness_score=0.88,
            clustering_cohesion_score=0.85,
            throughput_patterns_per_sec=75.0,
            search_impact_avg=0.17
        )

        results = validator.validate(metrics)
        assert 'compression_ratio' in results['failed_metrics']
        assert 'recall_at_5' in results['failed_metrics']

    def test_validation_message_format(self):
        """Test that validation messages are informative."""
        validator = MetricsValidator()
        metrics = ConsolidationMetrics(
            compression_ratio=0.60,  # Fails
            recall_at_5=0.85,
            pattern_consistency=0.80,
            information_density=0.75,
            hallucination_rate=0.05,
            pattern_diversity_score=0.90,
            system2_effectiveness_score=0.88,
            clustering_cohesion_score=0.85,
            throughput_patterns_per_sec=75.0,
            search_impact_avg=0.17
        )

        results = validator.validate(metrics)
        assert len(results['issues']) > 0
        assert 'compression' in results['issues'][0].lower()


class TestMetricsAnalyzer:
    """Test metrics analysis and trending."""

    def test_trend_improving(self):
        """Test detection of improving metric trend."""
        analyzer = MetricsAnalyzer()

        # Add metrics showing improving compression ratio
        analyzer.add_metrics(ConsolidationMetrics(
            compression_ratio=0.60,
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        ))

        analyzer.add_metrics(ConsolidationMetrics(
            compression_ratio=0.75,  # Improved
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        ))

        trend = analyzer.get_trend('compression_ratio')
        assert trend['trend'] == 'improving'
        assert trend['change_percent'] > 0

    def test_trend_degrading(self):
        """Test detection of degrading metric trend."""
        analyzer = MetricsAnalyzer()

        analyzer.add_metrics(ConsolidationMetrics(
            compression_ratio=0.80,
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        ))

        analyzer.add_metrics(ConsolidationMetrics(
            compression_ratio=0.70,  # Degraded
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        ))

        trend = analyzer.get_trend('compression_ratio')
        assert trend['trend'] == 'degrading'
        assert trend['change_percent'] < 0

    def test_trend_stable(self):
        """Test detection of stable metric trend."""
        analyzer = MetricsAnalyzer()

        analyzer.add_metrics(ConsolidationMetrics(
            compression_ratio=0.75,
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        ))

        analyzer.add_metrics(ConsolidationMetrics(
            compression_ratio=0.76,  # Minimal change
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        ))

        trend = analyzer.get_trend('compression_ratio')
        assert trend['trend'] == 'stable'

    def test_baseline_comparison(self):
        """Test comparison to baseline."""
        baseline = ConsolidationMetrics(
            compression_ratio=0.70,
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        )

        analyzer = MetricsAnalyzer(baseline=baseline)

        current = ConsolidationMetrics(
            compression_ratio=0.80,  # 14% better than baseline
            recall_at_5=0.85, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.10,
            pattern_diversity_score=0.85, system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=50.0,
            search_impact_avg=0.10
        )

        comparison = analyzer.compare_to_baseline(current)
        assert comparison['baseline_available'] is True
        assert 'compression_ratio' in comparison['comparisons']
        assert comparison['comparisons']['compression_ratio']['better'] is True

    def test_recommendations(self):
        """Test recommendation generation."""
        analyzer = MetricsAnalyzer()

        metrics = ConsolidationMetrics(
            compression_ratio=0.60,  # Low compression
            recall_at_5=0.80, pattern_consistency=0.75,
            information_density=0.70, hallucination_rate=0.15,  # High hallucination
            pattern_diversity_score=0.80,  # Low diversity
            system2_effectiveness_score=0.85,
            clustering_cohesion_score=0.80, throughput_patterns_per_sec=40.0,  # Low throughput
            search_impact_avg=0.10
        )

        validation_results = {'failed_metrics': ['compression_ratio', 'hallucination_rate']}
        recommendations = analyzer.get_recommendations(metrics, validation_results)

        assert len(recommendations) > 0
        # Check for recommendations about the failing metrics
        rec_text = ' '.join(recommendations).lower()
        assert 'compression' in rec_text or 'hallucination' in rec_text or 'throughput' in rec_text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
