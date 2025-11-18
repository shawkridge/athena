"""Report Generator for comprehensive code analysis reports.

Provides:
- Multi-format report generation (JSON, HTML, text)
- Executive summary generation
- Detailed metrics visualization
- Trend analysis reporting
- Recommendations and action items
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

from .symbol_models import Symbol


@dataclass
class ReportSection:
    """Single section of a report."""

    title: str
    content: str
    subsections: List["ReportSection"] = None


@dataclass
class AnalysisReport:
    """Comprehensive analysis report."""

    title: str
    generated_at: str
    symbols_analyzed: int
    quality_score: float
    health_score: float
    status: str  # excellent, good, fair, poor, critical

    # Sections
    executive_summary: str
    findings: List[str]
    recommendations: List[str]

    # Metrics
    metrics: Dict[str, Any]

    # Details
    high_risk_items: List[Dict]
    improvement_opportunities: List[Dict]

    # Trends
    trends: List[Dict] = None


class ReportGenerator:
    """Generates comprehensive analysis reports."""

    def __init__(self, project_name: str = "Code Analysis"):
        """Initialize report generator.

        Args:
            project_name: Name of project being analyzed
        """
        self.project_name = project_name
        self.report: Optional[AnalysisReport] = None

    def generate_report(
        self,
        symbols: Dict[str, Symbol],
        quality_metrics: Dict,
        complexity_metrics: Dict,
        dependency_metrics: Dict,
        violations: List,
    ) -> AnalysisReport:
        """Generate comprehensive analysis report.

        Args:
            symbols: Dict of analyzed symbols
            quality_metrics: Quality analysis metrics
            complexity_metrics: Complexity analysis metrics
            dependency_metrics: Dependency analysis metrics
            violations: Rule violations

        Returns:
            AnalysisReport
        """
        symbols_analyzed = len(symbols)

        # Calculate overall scores
        quality_score = quality_metrics.get("overall_score", 0.0)
        health_score = quality_metrics.get("health_score", 0.0)
        status = self._determine_status(quality_score)

        # Generate sections
        executive_summary = self._generate_executive_summary(
            symbols_analyzed, quality_score, health_score
        )
        findings = self._generate_findings(quality_metrics, complexity_metrics, violations)
        recommendations = self._generate_recommendations(
            quality_metrics, complexity_metrics, violations
        )

        # Collect metrics
        metrics = self._collect_metrics(quality_metrics, complexity_metrics, dependency_metrics)

        # Identify issues
        high_risk = self._identify_high_risk_items(violations)
        improvements = self._identify_improvements(quality_metrics, complexity_metrics)

        self.report = AnalysisReport(
            title=f"{self.project_name} - Code Analysis Report",
            generated_at=datetime.now().isoformat(),
            symbols_analyzed=symbols_analyzed,
            quality_score=quality_score,
            health_score=health_score,
            status=status,
            executive_summary=executive_summary,
            findings=findings,
            recommendations=recommendations,
            metrics=metrics,
            high_risk_items=high_risk,
            improvement_opportunities=improvements,
        )

        return self.report

    def _determine_status(self, quality_score: float) -> str:
        """Determine overall status from quality score.

        Args:
            quality_score: Quality score (0-100)

        Returns:
            Status string
        """
        if quality_score >= 85:
            return "excellent"
        elif quality_score >= 70:
            return "good"
        elif quality_score >= 55:
            return "fair"
        elif quality_score >= 40:
            return "poor"
        else:
            return "critical"

    def _generate_executive_summary(self, symbols: int, quality: float, health: float) -> str:
        """Generate executive summary.

        Args:
            symbols: Number of symbols analyzed
            quality: Quality score
            health: Health score

        Returns:
            Summary text
        """
        status = self._determine_status(quality)
        return (
            f"Analysis of {symbols} code symbols indicates a {status} codebase. "
            f"Overall quality score: {quality:.1f}/100. "
            f"Project health: {health:.1%}. "
            f"See recommendations section for improvement opportunities."
        )

    def _generate_findings(self, quality: Dict, complexity: Dict, violations: List) -> List[str]:
        """Generate key findings.

        Args:
            quality: Quality metrics
            complexity: Complexity metrics
            violations: Violations

        Returns:
            List of finding strings
        """
        findings = []

        # Quality findings
        issues = quality.get("total_issues", 0)
        if issues > 0:
            findings.append(f"Found {issues} quality issues across the codebase")

        # Complexity findings
        complex_count = complexity.get("complex_count", 0)
        if complex_count > 0:
            findings.append(f"Identified {complex_count} symbols with high complexity")

        # Violation findings
        if violations:
            findings.append(f"Rule enforcement found {len(violations)} violations")

        # Health findings
        health = quality.get("health_score", 0)
        if health < 0.5:
            findings.append("Project health is below acceptable threshold")

        if not findings:
            findings.append("Codebase analysis complete with no critical findings")

        return findings

    def _generate_recommendations(
        self, quality: Dict, complexity: Dict, violations: List
    ) -> List[str]:
        """Generate recommendations.

        Args:
            quality: Quality metrics
            complexity: Complexity metrics
            violations: Violations

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Priority: Critical issues
        critical = quality.get("critical_issues", 0)
        if critical > 0:
            recommendations.append(f"URGENT: Address {critical} critical issues immediately")

        # Priority: High complexity refactoring
        complex_count = complexity.get("complex_count", 0)
        if complex_count > 0:
            recommendations.append(
                f"Refactor {complex_count} high-complexity symbols to improve maintainability"
            )

        # Priority: Documentation
        if not quality.get("documentation_stats", {}).get("mean", 0) > 0.5:
            recommendations.append("Improve code documentation coverage")

        # Priority: Testing
        testability = quality.get("testability_stats", {}).get("mean", 0)
        if testability < 0.6:
            recommendations.append("Increase test coverage and testability")

        # General
        if not recommendations:
            recommendations.append("Continue current development practices")

        return recommendations

    def _collect_metrics(self, quality: Dict, complexity: Dict, dependency: Dict) -> Dict:
        """Collect all metrics.

        Args:
            quality: Quality metrics
            complexity: Complexity metrics
            dependency: Dependency metrics

        Returns:
            Collected metrics dict
        """
        return {
            "quality": quality,
            "complexity": complexity,
            "dependency": dependency,
            "summary": {
                "quality_score": quality.get("overall_score", 0),
                "health_score": quality.get("health_score", 0),
                "complex_symbols": complexity.get("complex_count", 0),
                "violations": len(quality.get("violations", [])),
                "hotspot_symbols": len(dependency.get("hotspots", [])),
            },
        }

    def _identify_high_risk_items(self, violations: List) -> List[Dict]:
        """Identify high-risk items from violations.

        Args:
            violations: List of violations

        Returns:
            List of high-risk items
        """
        high_risk = []

        for violation in violations[:10]:  # Top 10
            if isinstance(violation, dict):
                if violation.get("severity") in ["error", "critical"]:
                    high_risk.append(
                        {
                            "symbol": violation.get("symbol", "unknown"),
                            "issue": violation.get("message", ""),
                            "severity": violation.get("severity", ""),
                        }
                    )

        return high_risk

    def _identify_improvements(self, quality: Dict, complexity: Dict) -> List[Dict]:
        """Identify improvement opportunities.

        Args:
            quality: Quality metrics
            complexity: Complexity metrics

        Returns:
            List of improvement opportunities
        """
        improvements = []

        # Improvement: Security
        if quality.get("security_stats", {}).get("mean", 0) < 0.7:
            improvements.append(
                {
                    "area": "Security",
                    "current": quality.get("security_stats", {}).get("mean", 0),
                    "target": 0.85,
                    "impact": "high",
                }
            )

        # Improvement: Complexity
        avg_complexity = complexity.get("average_complexity", 0)
        if avg_complexity > 15:
            improvements.append(
                {
                    "area": "Code Complexity",
                    "current": avg_complexity,
                    "target": 10,
                    "impact": "high",
                }
            )

        # Improvement: Documentation
        if quality.get("documentation_stats", {}).get("mean", 0) < 0.7:
            improvements.append(
                {
                    "area": "Documentation",
                    "current": quality.get("documentation_stats", {}).get("mean", 0),
                    "target": 0.85,
                    "impact": "medium",
                }
            )

        return improvements

    def to_json(self) -> str:
        """Convert report to JSON format.

        Returns:
            JSON string
        """
        if not self.report:
            return "{}"

        report_dict = {
            "title": self.report.title,
            "generated_at": self.report.generated_at,
            "symbols_analyzed": self.report.symbols_analyzed,
            "quality_score": self.report.quality_score,
            "health_score": self.report.health_score,
            "status": self.report.status,
            "executive_summary": self.report.executive_summary,
            "findings": self.report.findings,
            "recommendations": self.report.recommendations,
            "metrics": self.report.metrics,
            "high_risk_items": self.report.high_risk_items,
            "improvement_opportunities": self.report.improvement_opportunities,
        }

        return json.dumps(report_dict, indent=2)

    def to_text(self) -> str:
        """Convert report to text format.

        Returns:
            Formatted text
        """
        if not self.report:
            return "No report generated"

        lines = []
        lines.append("=" * 80)
        lines.append(self.report.title)
        lines.append("=" * 80)
        lines.append("")

        lines.append(f"Generated: {self.report.generated_at}")
        lines.append(f"Symbols Analyzed: {self.report.symbols_analyzed}")
        lines.append(f"Quality Score: {self.report.quality_score:.1f}/100")
        lines.append(f"Health Score: {self.report.health_score:.1%}")
        lines.append(f"Status: {self.report.status.upper()}")
        lines.append("")

        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(self.report.executive_summary)
        lines.append("")

        lines.append("KEY FINDINGS")
        lines.append("-" * 80)
        for finding in self.report.findings:
            lines.append(f"• {finding}")
        lines.append("")

        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        for rec in self.report.recommendations:
            lines.append(f"• {rec}")
        lines.append("")

        lines.append("HIGH-RISK ITEMS")
        lines.append("-" * 80)
        if self.report.high_risk_items:
            for item in self.report.high_risk_items[:5]:
                lines.append(f"• {item.get('symbol', 'unknown')}: {item.get('issue', '')}")
        else:
            lines.append("No high-risk items identified")
        lines.append("")

        lines.append("IMPROVEMENT OPPORTUNITIES")
        lines.append("-" * 80)
        for opp in self.report.improvement_opportunities:
            lines.append(
                f"• {opp.get('area', '')}: {opp.get('current', 0):.2f} → {opp.get('target', 0):.2f}"
            )
        lines.append("")

        return "\n".join(lines)

    def to_html(self) -> str:
        """Convert report to HTML format.

        Returns:
            HTML string
        """
        if not self.report:
            return "<html><body>No report generated</body></html>"

        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{self.report.title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "h2 { color: #666; border-bottom: 2px solid #ccc; padding-bottom: 5px; }",
            ".status { padding: 10px; border-radius: 5px; }",
            ".status.excellent { background-color: #4CAF50; color: white; }",
            ".status.good { background-color: #8BC34A; color: white; }",
            ".status.fair { background-color: #FFC107; color: black; }",
            ".status.poor { background-color: #FF9800; color: white; }",
            ".status.critical { background-color: #F44336; color: white; }",
            ".metric { margin: 10px 0; }",
            ".recommendation { background-color: #e3f2fd; padding: 10px; margin: 5px 0; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{self.report.title}</h1>",
            f"<p>Generated: {self.report.generated_at}</p>",
            f"<div class='status {self.report.status}'><strong>Status: {self.report.status.upper()}</strong></div>",
            f"<div class='metric'>Quality Score: {self.report.quality_score:.1f}/100</div>",
            f"<div class='metric'>Health Score: {self.report.health_score:.1%}</div>",
            f"<div class='metric'>Symbols Analyzed: {self.report.symbols_analyzed}</div>",
            "<h2>Executive Summary</h2>",
            f"<p>{self.report.executive_summary}</p>",
            "<h2>Key Findings</h2>",
            "<ul>",
        ]

        for finding in self.report.findings:
            html_parts.append(f"<li>{finding}</li>")

        html_parts.extend(
            [
                "</ul>",
                "<h2>Recommendations</h2>",
            ]
        )

        for rec in self.report.recommendations:
            html_parts.append(f"<div class='recommendation'>{rec}</div>")

        html_parts.extend(
            [
                "</body>",
                "</html>",
            ]
        )

        return "\n".join(html_parts)

    def save_report(self, filepath: str, format: str = "json") -> bool:
        """Save report to file.

        Args:
            filepath: Path to save to
            format: Format (json, text, html)

        Returns:
            True if successful
        """
        try:
            if format == "json":
                content = self.to_json()
            elif format == "text":
                content = self.to_text()
            elif format == "html":
                content = self.to_html()
            else:
                return False

            with open(filepath, "w") as f:
                f.write(content)

            return True
        except (OSError, ValueError, TypeError, KeyError):
            return False
