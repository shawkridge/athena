"""Phase 2 Results Analysis and Reporting.

Comprehensive analysis of Phase 2 validation results with:
- Metric aggregation and statistical analysis
- Comparison with baselines
- Component contribution analysis
- Improvement tracking
- Production readiness assessment
"""

import json
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class MetricSummary:
    """Summary of a single metric."""
    name: str
    value: float
    target: float
    achieved_percentage: float
    status: str  # "exceeded", "met", "below"


@dataclass
class ComponentContribution:
    """Component contribution to overall performance."""
    component: str
    baseline_f1: float
    with_component_f1: float
    improvement_percentage: float
    contribution_rank: int
    critical: bool  # Is component critical for performance


@dataclass
class BenchmarkComparison:
    """Comparison of two systems."""
    system_a: str
    system_b: str
    metric: str
    value_a: float
    value_b: float
    difference_percentage: float
    winner: str


@dataclass
class Phase2AnalysisReport:
    """Comprehensive Phase 2 analysis report."""
    run_id: str
    timestamp: datetime

    # Metric summaries
    metric_summaries: List[MetricSummary]

    # Component analysis
    component_contributions: List[ComponentContribution]

    # Comparisons
    competitive_comparisons: List[BenchmarkComparison]

    # Overall assessment
    production_readiness_level: str  # "prototype", "beta", "production", "enterprise"
    key_strengths: List[str]
    areas_for_improvement: List[str]
    recommendations: List[str]

    # Timeline
    estimated_production_ready: str  # e.g., "Ready Now" or "Ready in X weeks"


class Phase2ResultsAnalyzer:
    """Analyzer for Phase 2 validation results."""

    def __init__(self):
        self.results = None
        self.metrics: Dict[str, float] = {}
        self.components: List[Dict] = []
        self.comparisons: List[Dict] = []

    def load_results(self, results_path: str) -> dict:
        """Load Phase 2 results from JSON file.

        Args:
            results_path: Path to JSON results file

        Returns:
            Loaded results dictionary
        """
        with open(results_path, 'r') as f:
            self.results = json.load(f)
        return self.results

    def analyze_metrics(self) -> List[MetricSummary]:
        """Analyze all metrics against targets.

        Returns:
            List of MetricSummary objects
        """
        summaries = []

        # Define targets and baselines
        targets = {
            'reasoning_dialogue_avg_accuracy': 0.85,
            'reasoning_dialogue_avg_quality': 0.82,
            'context_retention_success_rate': 92.0,
            'causal_inference_f1': 0.79,
            'production_readiness_score': 0.85,
        }

        baselines = {
            'reasoning_dialogue_avg_accuracy': 0.60,
            'reasoning_dialogue_avg_quality': 0.55,
            'context_retention_success_rate': 45.0,
            'causal_inference_f1': 0.47,
            'production_readiness_score': 0.50,
        }

        for metric_name, target in targets.items():
            if metric_name in self.results:
                value = self.results[metric_name]
                baseline = baselines.get(metric_name, target * 0.6)

                # Calculate achievement
                achieved_pct = ((value - baseline) / (target - baseline) * 100) if target > baseline else 100

                # Determine status
                if value >= target:
                    status = "exceeded"
                elif value >= baseline + (target - baseline) * 0.8:
                    status = "met"
                else:
                    status = "below"

                summary = MetricSummary(
                    name=metric_name,
                    value=value,
                    target=target,
                    achieved_percentage=min(100, achieved_pct),
                    status=status
                )
                summaries.append(summary)

        return summaries

    def analyze_components(self) -> List[ComponentContribution]:
        """Analyze component contributions.

        Returns:
            List of ComponentContribution objects
        """
        contributions = []

        if 'ablation_results' not in self.results:
            return contributions

        for ablation in self.results['ablation_results']:
            baseline = ablation.get('baseline_f1', 0.0)
            with_component = ablation.get('f1_with_component', 0.0)

            improvement_pct = ((with_component - baseline) / baseline * 100) if baseline > 0 else 0

            # Determine if critical (major impact on performance)
            critical = improvement_pct > 5.0

            contribution = ComponentContribution(
                component=ablation['component'],
                baseline_f1=baseline,
                with_component_f1=with_component,
                improvement_percentage=improvement_pct,
                contribution_rank=ablation.get('contribution_rank', 0),
                critical=critical
            )
            contributions.append(contribution)

        return sorted(contributions, key=lambda c: c.contribution_rank)

    def analyze_competitive_position(self) -> List[BenchmarkComparison]:
        """Analyze competitive positioning.

        Returns:
            List of BenchmarkComparison objects
        """
        comparisons = []

        if 'competitive_comparisons' not in self.results:
            return comparisons

        memory_mcp = None
        others = []

        for comp in self.results['competitive_comparisons']:
            if "Memory MCP" in comp['system_name']:
                memory_mcp = comp
            else:
                others.append(comp)

        if not memory_mcp:
            return comparisons

        # Compare Memory MCP vs each other system
        for other in others:
            metrics = ['reasoning_f1', 'context_retention_percent', 'causal_inference_f1']

            for metric in metrics:
                value_a = memory_mcp.get(metric, 0)
                value_b = other.get(metric, 0)
                diff_pct = ((value_a - value_b) / value_b * 100) if value_b > 0 else 0

                comparison = BenchmarkComparison(
                    system_a="Memory MCP",
                    system_b=other['system_name'],
                    metric=metric,
                    value_a=value_a,
                    value_b=value_b,
                    difference_percentage=diff_pct,
                    winner="Memory MCP" if value_a > value_b else other['system_name']
                )
                comparisons.append(comparison)

        return comparisons

    def assess_production_readiness(self, metric_summaries: List[MetricSummary]) -> str:
        """Assess production readiness level.

        Args:
            metric_summaries: List of MetricSummary objects

        Returns:
            Production readiness level
        """
        # Count metrics by status
        exceeded = sum(1 for m in metric_summaries if m.status == "exceeded")
        met = sum(1 for m in metric_summaries if m.status == "met")
        total = len(metric_summaries)

        success_rate = (exceeded + met) / total if total > 0 else 0

        if success_rate >= 0.9 and exceeded >= total * 0.5:
            return "production"
        elif success_rate >= 0.7:
            return "beta"
        elif success_rate >= 0.5:
            return "prototype"
        else:
            return "research"

    def identify_strengths(self, metric_summaries: List[MetricSummary],
                          components: List[ComponentContribution]) -> List[str]:
        """Identify key strengths from analysis.

        Args:
            metric_summaries: List of MetricSummary objects
            components: List of ComponentContribution objects

        Returns:
            List of strength descriptions
        """
        strengths = []

        # Check metrics
        exceeded_metrics = [m.name for m in metric_summaries if m.status == "exceeded"]
        if exceeded_metrics:
            strengths.append(f"Exceeded targets in {len(exceeded_metrics)} metrics")

        # Check components
        critical_components = [c.component for c in components if c.critical]
        if critical_components:
            strengths.append(f"Strong component design ({len(critical_components)} critical components)")

        # Check specific areas
        reasoning_metrics = [m for m in metric_summaries if 'reasoning' in m.name]
        if all(m.status in ["exceeded", "met"] for m in reasoning_metrics):
            strengths.append("Excellent reasoning dialogue capability")

        context_metrics = [m for m in metric_summaries if 'context' in m.name]
        if all(m.status in ["exceeded", "met"] for m in context_metrics):
            strengths.append("Superior context retention and retrieval")

        causal_metrics = [m for m in metric_summaries if 'causal' in m.name]
        if all(m.status in ["exceeded", "met"] for m in causal_metrics):
            strengths.append("Strong causal inference capabilities")

        return strengths

    def identify_improvements(self, metric_summaries: List[MetricSummary]) -> List[str]:
        """Identify areas for improvement.

        Args:
            metric_summaries: List of MetricSummary objects

        Returns:
            List of improvement areas
        """
        improvements = []

        below_metrics = [m for m in metric_summaries if m.status == "below"]

        for metric in below_metrics:
            gap = metric.target - metric.value
            gap_pct = (gap / metric.target * 100) if metric.target > 0 else 0
            improvements.append(f"Improve {metric.name} by {gap_pct:.1f}% "
                              f"(target: {metric.target}, current: {metric.value})")

        return improvements

    def generate_recommendations(self, metric_summaries: List[MetricSummary],
                                 components: List[ComponentContribution]) -> List[str]:
        """Generate recommendations for next steps.

        Args:
            metric_summaries: List of MetricSummary objects
            components: List of ComponentContribution objects

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check production readiness
        level = self.assess_production_readiness(metric_summaries)

        if level == "production":
            recommendations.append("✓ Ready for production deployment")
            recommendations.append("Consider implementing monitoring for production metrics")
            recommendations.append("Plan Phase 3 for enterprise features")

        elif level == "beta":
            recommendations.append("Ready for beta testing with select users")
            recommendations.append("Fix below-target metrics before production")
            recommendations.append("Implement feedback loop from beta users")

        elif level == "prototype":
            recommendations.append("Continue development and refinement")
            recommendations.append("Focus on critical metric improvements")
            recommendations.append("Conduct additional testing in controlled environments")

        else:
            recommendations.append("Significant work needed before production")
            recommendations.append("Review fundamental design assumptions")
            recommendations.append("Consider alternative approaches for weak areas")

        # Component-specific recommendations
        weak_components = [c for c in components if not c.critical and c.improvement_percentage < 0]
        if weak_components:
            recommendations.append(f"Review {len(weak_components)} underperforming components")

        return recommendations

    def generate_analysis_report(self) -> Phase2AnalysisReport:
        """Generate complete analysis report.

        Returns:
            Phase2AnalysisReport
        """
        # Analyze all aspects
        metric_summaries = self.analyze_metrics()
        components = self.analyze_components()
        comparisons = self.analyze_competitive_position()

        # Assess readiness
        readiness_level = self.assess_production_readiness(metric_summaries)

        # Identify insights
        strengths = self.identify_strengths(metric_summaries, components)
        improvements = self.identify_improvements(metric_summaries)
        recommendations = self.generate_recommendations(metric_summaries, components)

        # Estimate timeline
        if readiness_level == "production":
            estimated_ready = "Ready Now"
        elif readiness_level == "beta":
            estimated_ready = "Ready in 1-2 weeks"
        elif readiness_level == "prototype":
            estimated_ready = "Ready in 2-4 weeks"
        else:
            estimated_ready = "Ready in 4+ weeks"

        report = Phase2AnalysisReport(
            run_id=self.results.get('run_id', 'unknown'),
            timestamp=datetime.fromisoformat(self.results.get('timestamp', datetime.now().isoformat())),
            metric_summaries=metric_summaries,
            component_contributions=components,
            competitive_comparisons=comparisons,
            production_readiness_level=readiness_level,
            key_strengths=strengths,
            areas_for_improvement=improvements,
            recommendations=recommendations,
            estimated_production_ready=estimated_ready,
        )

        return report


def print_analysis_report(report: Phase2AnalysisReport) -> None:
    """Print analysis report to console.

    Args:
        report: Phase2AnalysisReport
    """
    print("\n" + "=" * 80)
    print("PHASE 2 ANALYSIS REPORT")
    print("=" * 80)

    print(f"\nRun ID: {report.run_id}")
    print(f"Timestamp: {report.timestamp.isoformat()}")

    print("\n📊 PRODUCTION READINESS ASSESSMENT")
    print(f"  Level: {report.production_readiness_level.upper()}")
    print(f"  Timeline: {report.estimated_production_ready}")

    print("\n✨ KEY STRENGTHS:")
    for i, strength in enumerate(report.key_strengths, 1):
        print(f"  {i}. {strength}")

    if report.areas_for_improvement:
        print("\n⚠️  AREAS FOR IMPROVEMENT:")
        for i, improvement in enumerate(report.areas_for_improvement, 1):
            print(f"  {i}. {improvement}")

    print("\n💡 RECOMMENDATIONS:")
    for i, recommendation in enumerate(report.recommendations, 1):
        print(f"  {i}. {recommendation}")

    print("\n📈 METRIC SUMMARY:")
    print("  Metric Name                        | Value | Target | Status")
    print("  " + "-" * 75)
    for summary in report.metric_summaries:
        status_symbol = "✓" if summary.status in ["exceeded", "met"] else "✗"
        print(f"  {summary.name:34} | {summary.value:5.1f} | {summary.target:6.1f} | {status_symbol} {summary.status}")

    if report.component_contributions:
        print("\n🔧 COMPONENT CONTRIBUTIONS (Top 3):")
        for contrib in report.component_contributions[:3]:
            print(f"  {contrib.contribution_rank}. {contrib.component}: "
                  f"{contrib.improvement_percentage:+.1f}% "
                  f"({'critical' if contrib.critical else 'supporting'})")

    print("\n🏆 COMPETITIVE POSITIONING:")
    if report.competitive_comparisons:
        # Show summary of Memory MCP vs others
        memory_mcp_wins = sum(1 for c in report.competitive_comparisons if c.winner == "Memory MCP")
        total = len(report.competitive_comparisons)
        print(f"  Memory MCP wins: {memory_mcp_wins}/{total} comparisons")

        # Show top advantages
        sorted_comps = sorted(report.competitive_comparisons,
                            key=lambda c: c.difference_percentage,
                            reverse=True)
        for comp in sorted_comps[:3]:
            if comp.winner == "Memory MCP":
                print(f"  • {comp.metric}: +{comp.difference_percentage:.1f}% vs {comp.system_b}")

    print("\n" + "=" * 80)


def save_analysis_report(report: Phase2AnalysisReport, output_path: str) -> None:
    """Save analysis report to JSON.

    Args:
        report: Phase2AnalysisReport
        output_path: Path to save JSON
    """
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    data = {
        'run_id': report.run_id,
        'timestamp': report.timestamp.isoformat(),
        'production_readiness_level': report.production_readiness_level,
        'estimated_production_ready': report.estimated_production_ready,
        'metric_summaries': [asdict(m) for m in report.metric_summaries],
        'component_contributions': [asdict(c) for c in report.component_contributions],
        'competitive_comparisons': [asdict(c) for c in report.competitive_comparisons],
        'key_strengths': report.key_strengths,
        'areas_for_improvement': report.areas_for_improvement,
        'recommendations': report.recommendations,
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"✓ Analysis report saved to {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python phase2_results_analysis.py <results_json_path>")
        sys.exit(1)

    results_path = sys.argv[1]

    analyzer = Phase2ResultsAnalyzer()
    analyzer.load_results(results_path)
    report = analyzer.generate_analysis_report()

    print_analysis_report(report)

    # Save analysis
    analysis_path = results_path.replace('.json', '_analysis.json')
    save_analysis_report(report, analysis_path)
