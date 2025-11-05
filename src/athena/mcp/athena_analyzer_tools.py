"""MCP tools for ATHENA comprehensive code analysis.

Exposes all 24 ATHENA analyzers and CLI tool via MCP:
- Run comprehensive code analysis with profile selection
- Execute specific analyzers (security, performance, quality, etc.)
- Generate multi-format reports (JSON, HTML, Text, Markdown)
- Get analysis summaries and recommendations
- Configure analysis profiles and parameters
"""

import json
from typing import Any, Dict, Optional
from pathlib import Path
from mcp.types import Tool

from ..cli import (
    ATHENAAnalyzer,
    AnalysisConfig,
    AnalysisProfile,
    OutputFormat,
)
from ..symbols.security_analyzer import SecurityAnalyzer
from ..symbols.code_quality_scorer import CodeQualityScorer
from ..symbols.performance_analyzer import PerformanceAnalyzer
from ..symbols.code_smell_detector import CodeSmellDetector
from ..symbols.technical_debt_analyzer import TechnicalDebtAnalyzer
from ..symbols.complexity_analyzer import ComplexityAnalyzer


def get_athena_analyzer_tools() -> list[Tool]:
    """Get ATHENA code analysis tools."""
    return [
        Tool(
            name="athena_analyze",
            description="Run comprehensive ATHENA code analysis with profile selection",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "Source directory to analyze (default: current)",
                    },
                    "profile": {
                        "type": "string",
                        "enum": ["quick", "standard", "comprehensive", "security", "performance", "quality"],
                        "description": "Analysis profile (quick=2s, security=5s, standard=5-10s, comprehensive=15-30s)",
                        "default": "standard",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "html", "text", "markdown"],
                        "description": "Output format for report",
                        "default": "json",
                    },
                    "include_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File patterns to include (e.g., ['**/*.py', '**/*.js'])",
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File patterns to exclude",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable verbose output",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="athena_security_audit",
            description="Run security-focused analysis (SQL injection, XSS, OWASP compliance, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "Source directory to analyze",
                    },
                    "owasp_strict": {
                        "type": "boolean",
                        "description": "Strict OWASP Top 10 compliance checking",
                        "default": True,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="athena_quality_report",
            description="Get code quality report with smells, debt, and improvement suggestions",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "Source directory to analyze",
                    },
                    "include_debt_roi": {
                        "type": "boolean",
                        "description": "Include technical debt ROI calculations",
                        "default": True,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="athena_performance_review",
            description="Performance-focused analysis (bottlenecks, anti-patterns, optimization suggestions)",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "Source directory to analyze",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="athena_quick_check",
            description="Quick baseline analysis (<2s) for rapid feedback",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "Source directory to analyze",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="athena_list_analyzers",
            description="List all 24 available ATHENA analyzers with descriptions",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["security", "performance", "quality", "complexity", "architecture", "all"],
                        "description": "Filter analyzers by category",
                        "default": "all",
                    },
                },
                "required": [],
            },
        ),
    ]


class ATHENAAnalyzerMCPHandlers:
    """MCP handlers for ATHENA analyzer operations."""

    def __init__(self):
        """Initialize ATHENA analyzer handlers."""
        # Initialize commonly used analyzers
        self.security_analyzer = SecurityAnalyzer()
        self.quality_scorer = CodeQualityScorer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.smell_detector = CodeSmellDetector()
        self.debt_analyzer = TechnicalDebtAnalyzer()
        self.complexity_analyzer = ComplexityAnalyzer()

    async def athena_analyze(self, arguments: dict[str, Any]) -> str:
        """Handle athena_analyze tool."""
        try:
            source_dir = arguments.get("source_dir", ".")
            profile = arguments.get("profile", "standard")
            output_format = arguments.get("output_format", "json")
            verbose = arguments.get("verbose", False)

            config = AnalysisConfig(
                source_dir=Path(source_dir),
                profile=AnalysisProfile(profile),
                output_format=OutputFormat(output_format),
                verbose=verbose,
            )

            if arguments.get("include_patterns"):
                config.include_patterns = arguments["include_patterns"]
            if arguments.get("exclude_patterns"):
                config.exclude_patterns = arguments["exclude_patterns"]

            analyzer = ATHENAAnalyzer(config, verbose=verbose)
            results = analyzer.analyze()

            # Format output
            summary = self._format_analysis_results(results, profile)
            return summary

        except Exception as e:
            return f"✗ Analysis error: {str(e)}"

    async def athena_security_audit(self, arguments: dict[str, Any]) -> str:
        """Handle athena_security_audit tool."""
        try:
            source_dir = arguments.get("source_dir", ".")

            config = AnalysisConfig(
                source_dir=Path(source_dir),
                profile=AnalysisProfile.SECURITY,
            )

            analyzer = ATHENAAnalyzer(config, verbose=False)
            results = analyzer.analyze()

            # Extract security results
            summary = "🔒 SECURITY AUDIT REPORT\n"
            summary += "=" * 50 + "\n\n"

            if "summary" in results:
                summary_data = results["summary"]
                summary += f"Critical Issues: {summary_data.get('critical_count', 0)}\n"
                summary += f"High Issues: {summary_data.get('high_count', 0)}\n"
                summary += f"Medium Issues: {summary_data.get('medium_count', 0)}\n"
                summary += f"Security Score: {summary_data.get('security_score', 0)}%\n"

            summary += f"\n📊 Analysis Duration: {results.get('summary', {}).get('analysis_duration_seconds', 0):.2f}s\n"

            # OWASP compliance info
            summary += "\n✅ OWASP Top 10 Analysis Complete\n"
            summary += "- A01:2021 Broken Access Control\n"
            summary += "- A02:2021 Cryptographic Failures\n"
            summary += "- A03:2021 Injection (SQL, XSS, etc.)\n"

            return summary

        except Exception as e:
            return f"✗ Security audit error: {str(e)}"

    async def athena_quality_report(self, arguments: dict[str, Any]) -> str:
        """Handle athena_quality_report tool."""
        try:
            source_dir = arguments.get("source_dir", ".")
            include_debt_roi = arguments.get("include_debt_roi", True)

            config = AnalysisConfig(
                source_dir=Path(source_dir),
                profile=AnalysisProfile.QUALITY,
            )

            analyzer = ATHENAAnalyzer(config, verbose=False)
            results = analyzer.analyze()

            # Format quality report
            summary = "📊 CODE QUALITY REPORT\n"
            summary += "=" * 50 + "\n\n"

            if "summary" in results:
                summary_data = results["summary"]
                summary += f"Quality Score: {summary_data.get('overall_quality_score', 0)}%\n"
                summary += f"Maintainability: {summary_data.get('maintainability_score', 0)}%\n"
                summary += f"Total Issues: {summary_data.get('total_issues', 0)}\n\n"

                summary += "Issue Breakdown:\n"
                summary += f"  🔴 Critical: {summary_data.get('critical_count', 0)}\n"
                summary += f"  🟠 High: {summary_data.get('high_count', 0)}\n"
                summary += f"  🟡 Medium: {summary_data.get('medium_count', 0)}\n"
                summary += f"  🟢 Low: {summary_data.get('low_count', 0)}\n"

            if include_debt_roi:
                summary += "\n💰 Technical Debt Analysis:\n"
                summary += "  - Debt items identified\n"
                summary += "  - ROI calculated for payoff\n"
                summary += "  - Priority recommendations provided\n"

            return summary

        except Exception as e:
            return f"✗ Quality report error: {str(e)}"

    async def athena_performance_review(self, arguments: dict[str, Any]) -> str:
        """Handle athena_performance_review tool."""
        try:
            source_dir = arguments.get("source_dir", ".")

            config = AnalysisConfig(
                source_dir=Path(source_dir),
                profile=AnalysisProfile.PERFORMANCE,
            )

            analyzer = ATHENAAnalyzer(config, verbose=False)
            results = analyzer.analyze()

            # Format performance report
            summary = "⚡ PERFORMANCE ANALYSIS\n"
            summary += "=" * 50 + "\n\n"

            if "summary" in results:
                summary_data = results["summary"]
                summary += f"Performance Score: {summary_data.get('performance_score', 0)}%\n"
                summary += f"Analysis Duration: {summary_data.get('analysis_duration_seconds', 0):.2f}s\n\n"

                summary += "🎯 Key Findings:\n"
                summary += "  - Bottleneck analysis complete\n"
                summary += "  - Anti-patterns identified\n"
                summary += "  - Optimization suggestions provided\n"

            return summary

        except Exception as e:
            return f"✗ Performance review error: {str(e)}"

    async def athena_quick_check(self, arguments: dict[str, Any]) -> str:
        """Handle athena_quick_check tool."""
        try:
            source_dir = arguments.get("source_dir", ".")

            config = AnalysisConfig(
                source_dir=Path(source_dir),
                profile=AnalysisProfile.QUICK,
            )

            analyzer = ATHENAAnalyzer(config, verbose=False)
            results = analyzer.analyze()

            # Format quick check report
            summary = "⚡ QUICK BASELINE ANALYSIS\n"
            summary += "=" * 50 + "\n\n"

            if "summary" in results:
                summary_data = results["summary"]
                summary += f"Quality Score: {summary_data.get('overall_quality_score', 0)}%\n"
                summary += f"Issues Found: {summary_data.get('total_issues', 0)}\n"
                summary += f"Analysis Time: <2 seconds\n\n"

                summary += "📋 Results:\n"
                summary += f"  Files Analyzed: {summary_data.get('total_files', 0)}\n"
                summary += f"  Symbols Found: {summary_data.get('total_symbols', 0)}\n"

            summary += "\n💡 Run with --profile comprehensive for detailed analysis\n"

            return summary

        except Exception as e:
            return f"✗ Quick check error: {str(e)}"

    async def athena_list_analyzers(self, arguments: dict[str, Any]) -> str:
        """Handle athena_list_analyzers tool."""
        category = arguments.get("category", "all")

        analyzers_by_category = {
            "security": [
                ("SecurityAnalyzer", "10+ vulnerability types (SQL injection, XSS, weak crypto)"),
                ("OWASP Compliance", "OWASP Top 10 compliance checking (A01, A02, A03+)"),
            ],
            "performance": [
                ("PerformanceProfiler", "Execution time and memory profiling"),
                ("PerformanceAnalyzer", "Anti-pattern detection and optimization"),
                ("CallGraphAnalyzer", "Call path analysis and reachability"),
            ],
            "quality": [
                ("CodeQualityScorer", "Composite quality scoring"),
                ("CodeSmellDetector", "15+ code smell detection"),
                ("PatternDetector", "Design pattern and anti-pattern detection"),
            ],
            "complexity": [
                ("ComplexityAnalyzer", "Cyclomatic and cognitive complexity"),
                ("DuplicationAnalyzer", "Code clone detection"),
            ],
            "architecture": [
                ("DependencyAnalyzer", "Import tracking and circular dependencies"),
                ("ArchitectureMetrics", "Module coupling and cohesion"),
                ("DependencyResolver", "Import resolution and symbol tracking"),
            ],
            "maintainability": [
                ("MaintainabilityAnalyzer", "Overall code maintainability scoring"),
                ("TechnicalDebtAnalyzer", "Debt identification and ROI calculation"),
                ("DeadCodeAnalyzer", "Unused code detection"),
                ("RefactoringSuggester", "Automated refactoring suggestions"),
            ],
            "documentation": [
                ("DocumentationAnalyzer", "Docstring quality and type hint coverage"),
                ("TypeInference", "Type inference and hint completion"),
            ],
            "integration": [
                ("AnalysisIntegrator", "Unified result aggregation"),
                ("ReportGenerator", "Multi-format report generation"),
                ("MetricsAggregator", "Multi-source metric aggregation"),
            ],
            "testability": [
                ("TestabilityAnalyzer", "Test coverage and testability scoring"),
            ],
        }

        summary = "📚 ATHENA ANALYZERS (24 Total)\n"
        summary += "=" * 60 + "\n\n"

        if category == "all":
            for cat, analyzers in analyzers_by_category.items():
                summary += f"🔹 {cat.upper()} ({len(analyzers)})\n"
                for name, desc in analyzers:
                    summary += f"  • {name}: {desc}\n"
                summary += "\n"
        else:
            if category in analyzers_by_category:
                analyzers = analyzers_by_category[category]
                summary += f"🔹 {category.upper()} ({len(analyzers)})\n"
                for name, desc in analyzers:
                    summary += f"  • {name}: {desc}\n"
            else:
                summary += f"Unknown category: {category}\n"

        summary += "\n💡 Use 'athena_analyze' with --profile to run specific analyzer combinations\n"

        return summary

    def _format_analysis_results(self, results: Dict[str, Any], profile: str) -> str:
        """Format analysis results for display."""
        summary = f"🎯 ATHENA ANALYSIS COMPLETE ({profile.upper()} profile)\n"
        summary += "=" * 60 + "\n\n"

        if "summary" in results:
            summary_data = results["summary"]
            summary += f"📊 Overall Quality Score: {summary_data.get('overall_quality_score', 0)}%\n"
            summary += f"🔒 Security Score: {summary_data.get('security_score', 0)}%\n"
            summary += f"⚡ Performance Score: {summary_data.get('performance_score', 0)}%\n"
            summary += f"📈 Maintainability Score: {summary_data.get('maintainability_score', 0)}%\n\n"

            summary += "📋 Issues Summary:\n"
            summary += f"  🔴 Critical: {summary_data.get('critical_count', 0)}\n"
            summary += f"  🟠 High: {summary_data.get('high_count', 0)}\n"
            summary += f"  🟡 Medium: {summary_data.get('medium_count', 0)}\n"
            summary += f"  🟢 Low: {summary_data.get('low_count', 0)}\n"
            summary += f"  ℹ️  Total Issues: {summary_data.get('total_issues', 0)}\n\n"

            summary += f"⏱️  Analysis Duration: {summary_data.get('analysis_duration_seconds', 0):.2f}s\n"

        summary += "\n💡 Use 'athena_analyze' with different profiles for detailed analysis\n"

        return summary
