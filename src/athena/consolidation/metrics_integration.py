"""Metrics Integration - Unified interface for all consolidation metrics.

Brings together:
- Core metrics (compression, recall, consistency, density)
- Advanced metrics (hallucination, diversity, dual-process, clustering, throughput, search impact)
- Pipeline instrumentation
- Historical tracking and trending

This module provides:
1. ConsolidationMetricsCollector - Collects all metrics during consolidation
2. MetricsValidator - Validates metrics against targets
3. MetricsAnalyzer - Analyzes trends and generates recommendations
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .advanced_metrics import (
    ClusteringCohesionCalculator,
    DualProcessEffectivenessCalculator,
    HallucinationRateCalculator,
    PatternDiversityCalculator,
    PipelineThroughputCalculator,
    SearchImpactCalculator,
)
from .pipeline_instrumentation import PipelineInstrumentation
from .quality_metrics import ConsolidationQualityMetrics


@dataclass
class ConsolidationMetrics:
    """Complete consolidation metrics for a single run."""

    # Core metrics (4)
    compression_ratio: float
    recall_at_5: float
    pattern_consistency: float
    information_density: float

    # Advanced metrics (6)
    hallucination_rate: float
    pattern_diversity_score: float
    system2_effectiveness_score: float
    clustering_cohesion_score: float
    throughput_patterns_per_sec: float
    search_impact_avg: float

    # Metadata
    consolidation_run_id: Optional[int] = None
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metric_details: Dict = field(default_factory=dict)


@dataclass
class MetricsTargets:
    """Target values for all metrics."""

    # Core metrics
    compression_ratio_min: float = 0.70
    compression_ratio_max: float = 0.85
    recall_at_5_min: float = 0.80
    recall_at_5_max: float = 1.0
    pattern_consistency_min: float = 0.75
    pattern_consistency_max: float = 1.0
    information_density_min: float = 0.70
    information_density_max: float = 1.0

    # Advanced metrics
    hallucination_rate_min: float = 0.0
    hallucination_rate_max: float = 0.10
    pattern_diversity_min: float = 0.85
    pattern_diversity_max: float = 1.0
    system2_effectiveness_min: float = 0.85
    system2_effectiveness_max: float = 1.0
    clustering_cohesion_min: float = 0.80
    clustering_cohesion_max: float = 1.0
    throughput_min: float = 50.0  # patterns/sec
    throughput_max: Optional[float] = None
    search_impact_min: float = 0.15  # 15% improvement
    search_impact_max: float = 0.20  # 20% improvement


class ConsolidationMetricsCollector:
    """Collect all consolidation metrics during a consolidation run.

    Integrates with the consolidation pipeline to gather:
    - Core quality metrics
    - Advanced performance metrics
    - Pipeline timing information
    """

    def __init__(
        self, quality_metrics: ConsolidationQualityMetrics, targets: Optional[MetricsTargets] = None
    ):
        """Initialize metrics collector.

        Args:
            quality_metrics: Core quality metrics calculator
            targets: Optional custom metric targets
        """
        self.quality_metrics = quality_metrics
        self.targets = targets or MetricsTargets()
        self.instrumentation = PipelineInstrumentation()

        # Advanced metric calculators
        self.hallucination_calc = HallucinationRateCalculator()
        self.diversity_calc = PatternDiversityCalculator()
        self.dual_process_calc = DualProcessEffectivenessCalculator()
        self.clustering_calc = ClusteringCohesionCalculator()
        self.throughput_calc = PipelineThroughputCalculator()
        self.search_impact_calc = SearchImpactCalculator()

    def collect_all_metrics(
        self,
        session_id: str,
        patterns: List[Dict],
        clusters: Optional[List] = None,
        test_queries: Optional[List[str]] = None,
        before_results: Optional[List[List[Dict]]] = None,
        after_results: Optional[List[List[Dict]]] = None,
    ) -> ConsolidationMetrics:
        """Collect all metrics for a consolidation run.

        Args:
            session_id: Session being consolidated
            patterns: Extracted patterns with all metadata
            clusters: Event clusters (for cohesion calculation)
            test_queries: Optional test queries for search impact
            before_results: Search results before consolidation
            after_results: Search results after consolidation

        Returns:
            ConsolidationMetrics with all 10 metrics
        """
        # Core metrics
        compression = self.quality_metrics.measure_compression_ratio(session_id)
        recall_dict = self.quality_metrics.measure_retrieval_recall(session_id)
        recall_at_5 = recall_dict.get("relative_recall", 0.0)
        consistency = self.quality_metrics.measure_pattern_consistency(session_id)
        density = self.quality_metrics.measure_information_density(session_id)

        # Advanced metrics
        hallucination = self.hallucination_calc.calculate(patterns)
        diversity = self.diversity_calc.calculate(patterns)

        dual_process = self.dual_process_calc.calculate(patterns)
        system2_effectiveness = dual_process.get("system2_effectiveness_score", 0.0)

        clustering_cohesion = 0.0
        if clusters:
            clustering_cohesion = self.clustering_calc.calculate(clusters)

        throughput = self.throughput_calc.calculate_throughput()

        search_impact = 0.0
        if test_queries and before_results and after_results:
            search_impact_dict = self.search_impact_calc.measure_impact(
                test_queries, before_results, after_results
            )
            search_impact = search_impact_dict.get("relevance_improvement", 0.0)

        # Create metrics object
        metrics = ConsolidationMetrics(
            compression_ratio=compression,
            recall_at_5=recall_at_5,
            pattern_consistency=consistency,
            information_density=density,
            hallucination_rate=hallucination,
            pattern_diversity_score=diversity,
            system2_effectiveness_score=system2_effectiveness,
            clustering_cohesion_score=clustering_cohesion,
            throughput_patterns_per_sec=throughput,
            search_impact_avg=search_impact,
            session_id=session_id,
            metric_details={
                "recall_details": recall_dict,
                "dual_process_details": dual_process,
                "hallucination_breakdown": self.hallucination_calc.get_risk_breakdown(patterns),
                "pattern_type_distribution": self.diversity_calc.get_type_distribution(patterns),
                "clustering_stats": (
                    self.clustering_calc.get_cluster_stats(clusters) if clusters else {}
                ),
                "throughput_stats": self.throughput_calc.get_stage_stats(),
            },
        )

        return metrics


class MetricsValidator:
    """Validate metrics against targets and generate reports.

    Checks each metric against targets and provides:
    - Pass/fail status
    - Which metrics meet targets
    - Recommendations for improvement
    """

    def __init__(self, targets: Optional[MetricsTargets] = None):
        """Initialize validator.

        Args:
            targets: Optional custom metric targets
        """
        self.targets = targets or MetricsTargets()

    def validate(self, metrics: ConsolidationMetrics) -> Dict:
        """Validate all metrics against targets.

        Args:
            metrics: Consolidation metrics to validate

        Returns:
            Dict with validation results
        """
        results = {
            "overall_status": "pass",
            "metric_results": {},
            "passed_metrics": [],
            "failed_metrics": [],
            "issues": [],
        }

        # Validate compression ratio
        comp_pass = (
            self.targets.compression_ratio_min
            <= metrics.compression_ratio
            <= self.targets.compression_ratio_max
        )
        results["metric_results"]["compression_ratio"] = comp_pass
        if comp_pass:
            results["passed_metrics"].append("compression_ratio")
        else:
            results["failed_metrics"].append("compression_ratio")
            results["issues"].append(
                f"Compression ratio {metrics.compression_ratio:.2%} outside target "
                f"[{self.targets.compression_ratio_min:.0%}, {self.targets.compression_ratio_max:.0%}]"
            )

        # Validate recall
        recall_pass = (
            self.targets.recall_at_5_min <= metrics.recall_at_5 <= self.targets.recall_at_5_max
        )
        results["metric_results"]["recall_at_5"] = recall_pass
        if recall_pass:
            results["passed_metrics"].append("recall_at_5")
        else:
            results["failed_metrics"].append("recall_at_5")
            results["issues"].append(
                f"Recall@5 {metrics.recall_at_5:.2%} below target minimum {self.targets.recall_at_5_min:.0%}"
            )

        # Validate pattern consistency
        cons_pass = self.targets.pattern_consistency_min <= metrics.pattern_consistency
        results["metric_results"]["pattern_consistency"] = cons_pass
        if cons_pass:
            results["passed_metrics"].append("pattern_consistency")
        else:
            results["failed_metrics"].append("pattern_consistency")
            results["issues"].append(
                f"Pattern consistency {metrics.pattern_consistency:.2%} below target minimum {self.targets.pattern_consistency_min:.0%}"
            )

        # Validate information density
        density_pass = self.targets.information_density_min <= metrics.information_density
        results["metric_results"]["information_density"] = density_pass
        if density_pass:
            results["passed_metrics"].append("information_density")
        else:
            results["failed_metrics"].append("information_density")
            results["issues"].append(
                f"Information density {metrics.information_density:.2%} below target minimum {self.targets.information_density_min:.0%}"
            )

        # Validate hallucination rate
        hall_pass = metrics.hallucination_rate <= self.targets.hallucination_rate_max
        results["metric_results"]["hallucination_rate"] = hall_pass
        if hall_pass:
            results["passed_metrics"].append("hallucination_rate")
        else:
            results["failed_metrics"].append("hallucination_rate")
            results["issues"].append(
                f"Hallucination rate {metrics.hallucination_rate:.2%} above target maximum {self.targets.hallucination_rate_max:.0%}"
            )

        # Validate pattern diversity
        div_pass = self.targets.pattern_diversity_min <= metrics.pattern_diversity_score
        results["metric_results"]["pattern_diversity"] = div_pass
        if div_pass:
            results["passed_metrics"].append("pattern_diversity")
        else:
            results["failed_metrics"].append("pattern_diversity")
            results["issues"].append(
                f"Pattern diversity {metrics.pattern_diversity_score:.2f} below target minimum {self.targets.pattern_diversity_min:.2f}"
            )

        # Validate system 2 effectiveness
        s2_pass = self.targets.system2_effectiveness_min <= metrics.system2_effectiveness_score
        results["metric_results"]["system2_effectiveness"] = s2_pass
        if s2_pass:
            results["passed_metrics"].append("system2_effectiveness")
        else:
            results["failed_metrics"].append("system2_effectiveness")
            results["issues"].append(
                f"System 2 effectiveness {metrics.system2_effectiveness_score:.2%} below target minimum {self.targets.system2_effectiveness_min:.0%}"
            )

        # Validate clustering cohesion
        clust_pass = self.targets.clustering_cohesion_min <= metrics.clustering_cohesion_score
        results["metric_results"]["clustering_cohesion"] = clust_pass
        if clust_pass:
            results["passed_metrics"].append("clustering_cohesion")
        else:
            results["failed_metrics"].append("clustering_cohesion")
            results["issues"].append(
                f"Clustering cohesion {metrics.clustering_cohesion_score:.2f} below target minimum {self.targets.clustering_cohesion_min:.2f}"
            )

        # Validate throughput
        through_pass = metrics.throughput_patterns_per_sec >= self.targets.throughput_min
        results["metric_results"]["throughput"] = through_pass
        if through_pass:
            results["passed_metrics"].append("throughput")
        else:
            results["failed_metrics"].append("throughput")
            results["issues"].append(
                f"Throughput {metrics.throughput_patterns_per_sec:.1f} patterns/sec below target minimum {self.targets.throughput_min:.1f}"
            )

        # Validate search impact
        search_pass = (
            self.targets.search_impact_min
            <= metrics.search_impact_avg
            <= self.targets.search_impact_max
        )
        results["metric_results"]["search_impact"] = search_pass
        if search_pass and metrics.search_impact_avg > 0:
            results["passed_metrics"].append("search_impact")
        elif metrics.search_impact_avg > 0:
            results["failed_metrics"].append("search_impact")
            results["issues"].append(
                f"Search impact {metrics.search_impact_avg:.2%} outside target "
                f"[{self.targets.search_impact_min:.0%}, {self.targets.search_impact_max:.0%}]"
            )

        # Set overall status
        results["overall_status"] = "pass" if not results["failed_metrics"] else "fail"
        results["metrics_passed"] = len(results["passed_metrics"])
        results["metrics_failed"] = len(results["failed_metrics"])
        results["total_metrics"] = results["metrics_passed"] + results["metrics_failed"]

        return results


class MetricsAnalyzer:
    """Analyze consolidation metrics trends and patterns.

    Provides:
    - Trend analysis (improving/degrading metrics)
    - Benchmark comparison
    - Optimization recommendations
    """

    def __init__(self, baseline: Optional[ConsolidationMetrics] = None):
        """Initialize analyzer.

        Args:
            baseline: Optional baseline metrics for comparison (e.g., MIRIX)
        """
        self.baseline = baseline
        self.history: List[ConsolidationMetrics] = []

    def add_metrics(self, metrics: ConsolidationMetrics):
        """Add metrics to history.

        Args:
            metrics: Metrics to add
        """
        self.history.append(metrics)

    def get_trend(self, metric_name: str, window: int = 5) -> Dict:
        """Analyze trend for a metric.

        Args:
            metric_name: Name of metric (e.g., 'compression_ratio')
            window: Number of recent values to analyze

        Returns:
            Dict with trend information
        """
        if not self.history:
            return {"trend": "no_data"}

        # Get metric values
        values = []
        for m in self.history[-window:]:
            val = getattr(m, metric_name, None)
            if val is not None:
                values.append(val)

        if len(values) < 2:
            return {"trend": "no_trend", "values": values}

        # Calculate trend
        recent = values[-1]
        previous = values[0]
        change = (recent - previous) / abs(previous) if previous != 0 else 0

        trend = "improving" if change > 0.05 else ("degrading" if change < -0.05 else "stable")

        return {
            "trend": trend,
            "change_percent": change * 100,
            "previous": previous,
            "recent": recent,
            "values": values,
        }

    def compare_to_baseline(self, metrics: ConsolidationMetrics) -> Dict:
        """Compare metrics to baseline (e.g., MIRIX).

        Args:
            metrics: Current metrics

        Returns:
            Dict with comparison results
        """
        if not self.baseline:
            return {"baseline_available": False}

        comparisons = {}

        # Compare each metric
        for attr in [
            "compression_ratio",
            "recall_at_5",
            "pattern_consistency",
            "information_density",
            "hallucination_rate",
            "pattern_diversity_score",
            "system2_effectiveness_score",
            "clustering_cohesion_score",
            "throughput_patterns_per_sec",
            "search_impact_avg",
        ]:
            current = getattr(metrics, attr, None)
            baseline = getattr(self.baseline, attr, None)

            if current is not None and baseline is not None and baseline != 0:
                delta = (current - baseline) / abs(baseline)
                comparisons[attr] = {
                    "current": current,
                    "baseline": baseline,
                    "delta_percent": delta * 100,
                    "better": delta > 0,
                }

        return {"baseline_available": True, "comparisons": comparisons}

    def get_recommendations(
        self, metrics: ConsolidationMetrics, validation_results: Dict
    ) -> List[str]:
        """Generate optimization recommendations.

        Args:
            metrics: Current metrics
            validation_results: Results from MetricsValidator

        Returns:
            List of recommendations
        """
        recommendations = []

        # Low compression
        if metrics.compression_ratio < 0.70:
            recommendations.append(
                "Low compression ratio. Try longer consolidation windows or more aggressive pruning."
            )

        # Low recall
        if metrics.recall_at_5 < 0.80:
            recommendations.append(
                "Low retrieval recall. Improve pattern quality or enhance indexing strategy."
            )

        # High hallucination
        if metrics.hallucination_rate > 0.10:
            recommendations.append(
                "High hallucination rate. Increase confidence thresholds or improve grounding validation."
            )

        # Low diversity
        if metrics.pattern_diversity_score < 0.85:
            recommendations.append(
                "Low pattern diversity. Patterns are concentrated in few types. Improve extraction strategy."
            )

        # Low throughput
        if metrics.throughput_patterns_per_sec < 50:
            recommendations.append(
                f"Low throughput ({metrics.throughput_patterns_per_sec:.1f} patterns/sec). "
                "Consider batch processing or parallelization."
            )

        # Check trends
        if self.history:
            trend = self.get_trend("compression_ratio")
            if trend["trend"] == "degrading":
                recommendations.append(
                    "Compression ratio degrading. Review recent input changes or model updates."
                )

        return (
            recommendations
            if recommendations
            else ["Metrics are healthy. Consider enhancing pattern extraction."]
        )
