"""Code Quality Scorer for comprehensive code quality assessment.

Provides:
- Unified quality score synthesizing all analyzers
- Component quality scores and ratings
- Quality health checks and recommendations
- Improvement priorities and roadmap
- Quality trends and progression tracking
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .symbol_models import Symbol
from .security_analyzer import SecurityAnalyzer
from .performance_analyzer import PerformanceAnalyzer
from .code_smell_detector import CodeSmellDetector
from .maintainability_analyzer import MaintainabilityAnalyzer
from .testability_analyzer import TestabilityAnalyzer
from .technical_debt_analyzer import TechnicalDebtAnalyzer


class QualityRating(str, Enum):
    """Overall quality rating."""

    EXCELLENT = "excellent"  # 85-100
    GOOD = "good"  # 70-84
    FAIR = "fair"  # 55-69
    POOR = "poor"  # 40-54
    CRITICAL = "critical"  # <40


class QualityMetric(str, Enum):
    """Individual quality metric."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    MAINTAINABILITY = "maintainability"
    TESTABILITY = "testability"
    DOCUMENTATION = "documentation"
    DEBT_HEALTH = "debt_health"


@dataclass
class ComponentScore:
    """Score for a quality component."""

    metric: QualityMetric
    score: float  # 0-100
    rating: QualityRating
    weight: float  # How much this contributes to overall score
    issues_count: int
    critical_count: int
    status: str  # "healthy", "warning", "critical"


@dataclass
class HealthCheck:
    """Result of a quality health check."""

    check_name: str
    passed: bool
    score: float  # 0-1
    details: str
    recommendation: str
    severity: str  # low, medium, high, critical


@dataclass
class QualityImprovement:
    """Single quality improvement recommendation."""

    priority: int  # 1-based, lower = higher priority
    title: str
    description: str
    estimated_effort: str  # e.g., "2-4 hours", "1 day"
    expected_impact: str  # e.g., "+15 quality score", "reduce issues by 30%"
    category: str  # security, performance, quality, maintainability, testability, documentation


@dataclass
class QualityTrend:
    """Quality metric trend over time."""

    metric: QualityMetric
    previous_score: float
    current_score: float
    change: float  # positive = improvement
    status: str  # "improving", "stable", "declining"


@dataclass
class CodeQualityScore:
    """Comprehensive code quality score."""

    symbol: Symbol
    overall_score: float  # 0-100
    overall_rating: QualityRating

    # Component scores
    component_scores: List[ComponentScore]

    # Issues summary
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int

    # Health checks
    health_checks: List[HealthCheck]

    # Recommendations
    improvements: List[QualityImprovement]

    # Trends (if historical data available)
    trends: List[QualityTrend] = field(default_factory=list)

    # Quality details
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


class CodeQualityScorer:
    """Comprehensive code quality assessment system."""

    def __init__(self):
        """Initialize scorer."""
        self.scores: List[CodeQualityScore] = []
        self.security_analyzer = SecurityAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.smell_detector = CodeSmellDetector()
        self.maintainability_analyzer = MaintainabilityAnalyzer()
        self.testability_analyzer = TestabilityAnalyzer()
        self.debt_analyzer = TechnicalDebtAnalyzer()

    def score_symbol(
        self,
        symbol: Symbol,
        security_issues: int = 0,
        performance_issues: int = 0,
        code_smells: int = 0,
        maintainability_score: float = 50.0,
        testability_score: float = 50.0,
        has_docstring: bool = False,
    ) -> CodeQualityScore:
        """Score code quality of a single symbol.

        Args:
            symbol: Symbol to score
            security_issues: Number of security issues
            performance_issues: Number of performance issues
            code_smells: Number of code smells
            maintainability_score: Maintainability score (0-100)
            testability_score: Testability score (0-100)
            has_docstring: Whether symbol has documentation

        Returns:
            CodeQualityScore with comprehensive assessment
        """
        # Get component scores from all analyzers
        security_debt = self._calculate_security_component(security_issues)
        performance_debt = self._calculate_performance_component(performance_issues)
        quality_debt = self._calculate_quality_component(code_smells)
        documentation_debt = self._calculate_documentation_component(has_docstring)
        maintainability_debt = self._calculate_maintainability_component(maintainability_score)
        testability_debt = self._calculate_testability_component(testability_score)

        # Create component scores (convert debt to quality)
        component_scores = [
            ComponentScore(
                metric=QualityMetric.SECURITY,
                score=100.0 - security_debt,
                rating=self._debt_to_rating(security_debt),
                weight=0.25,
                issues_count=security_issues,
                critical_count=min(security_issues, 2),
                status=(
                    "critical"
                    if security_debt > 70
                    else "warning" if security_debt > 40 else "healthy"
                ),
            ),
            ComponentScore(
                metric=QualityMetric.PERFORMANCE,
                score=100.0 - performance_debt,
                rating=self._debt_to_rating(performance_debt),
                weight=0.15,
                issues_count=performance_issues,
                critical_count=max(0, performance_issues - 2),
                status=(
                    "critical"
                    if performance_debt > 70
                    else "warning" if performance_debt > 40 else "healthy"
                ),
            ),
            ComponentScore(
                metric=QualityMetric.QUALITY,
                score=100.0 - quality_debt,
                rating=self._debt_to_rating(quality_debt),
                weight=0.15,
                issues_count=code_smells,
                critical_count=max(0, code_smells - 3),
                status=(
                    "critical"
                    if quality_debt > 70
                    else "warning" if quality_debt > 40 else "healthy"
                ),
            ),
            ComponentScore(
                metric=QualityMetric.DOCUMENTATION,
                score=100.0 - documentation_debt,
                rating=self._debt_to_rating(documentation_debt),
                weight=0.10,
                issues_count=0 if has_docstring else 1,
                critical_count=0 if has_docstring else 0,
                status="healthy" if has_docstring else "warning",
            ),
            ComponentScore(
                metric=QualityMetric.MAINTAINABILITY,
                score=maintainability_score,
                rating=self._score_to_rating(maintainability_score),
                weight=0.20,
                issues_count=0 if maintainability_score > 70 else 1,
                critical_count=0 if maintainability_score > 40 else 1,
                status=(
                    "critical"
                    if maintainability_score < 40
                    else "warning" if maintainability_score < 60 else "healthy"
                ),
            ),
            ComponentScore(
                metric=QualityMetric.TESTABILITY,
                score=testability_score,
                rating=self._score_to_rating(testability_score),
                weight=0.15,
                issues_count=0 if testability_score > 65 else 1,
                critical_count=0 if testability_score > 30 else 1,
                status=(
                    "critical"
                    if testability_score < 30
                    else "warning" if testability_score < 65 else "healthy"
                ),
            ),
        ]

        # Calculate weighted overall score
        overall_score = sum(cs.score * cs.weight for cs in component_scores)

        # Count issues by severity
        total_issues = (
            security_issues + performance_issues + code_smells + (0 if has_docstring else 1)
        )
        critical_issues = sum(cs.critical_count for cs in component_scores)
        high_issues = (
            max(0, security_issues - 1) + max(0, performance_issues - 1) + max(0, code_smells - 2)
        )
        medium_issues = max(0, (security_issues - 1) - max(0, security_issues - 2))
        low_issues = max(0, total_issues - critical_issues - high_issues - medium_issues)

        # Perform health checks
        health_checks = self._perform_health_checks(
            symbol,
            security_issues,
            performance_issues,
            code_smells,
            maintainability_score,
            testability_score,
            has_docstring,
        )

        # Generate improvements
        improvements = self._generate_improvements(
            component_scores,
            security_issues,
            performance_issues,
            code_smells,
            maintainability_score,
            testability_score,
            has_docstring,
        )

        # Identify strengths and weaknesses
        strengths = [cs.metric.value for cs in component_scores if cs.score >= 75]
        weaknesses = [cs.metric.value for cs in component_scores if cs.score < 60]

        # Overall rating
        overall_rating = self._score_to_rating(overall_score)

        score = CodeQualityScore(
            symbol=symbol,
            overall_score=overall_score,
            overall_rating=overall_rating,
            component_scores=component_scores,
            total_issues=total_issues,
            critical_issues=critical_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            health_checks=health_checks,
            improvements=improvements,
            strengths=strengths,
            weaknesses=weaknesses,
        )

        self.scores.append(score)
        return score

    def _calculate_security_component(self, issues: int) -> float:
        """Convert security issues to debt score."""
        if issues == 0:
            return 0.0
        elif issues == 1:
            return 30.0
        elif issues == 2:
            return 60.0
        else:
            return min(100.0, 30.0 + issues * 15.0)

    def _calculate_performance_component(self, issues: int) -> float:
        """Convert performance issues to debt score."""
        if issues == 0:
            return 0.0
        elif issues == 1:
            return 25.0
        elif issues == 2:
            return 50.0
        else:
            return min(100.0, 25.0 + issues * 12.0)

    def _calculate_quality_component(self, smells: int) -> float:
        """Convert code smells to debt score."""
        if smells == 0:
            return 0.0
        elif smells == 1:
            return 15.0
        elif smells <= 3:
            return 30.0
        elif smells <= 5:
            return 50.0
        else:
            return min(100.0, 50.0 + smells * 5.0)

    def _calculate_documentation_component(self, has_docstring: bool) -> float:
        """Convert documentation to debt score."""
        return 0.0 if has_docstring else 50.0

    def _calculate_maintainability_component(self, score: float) -> float:
        """Convert maintainability to debt score."""
        return max(0.0, min(100.0, 100.0 - score))

    def _calculate_testability_component(self, score: float) -> float:
        """Convert testability to debt score."""
        return max(0.0, min(100.0, 100.0 - score))

    def _debt_to_rating(self, debt_score: float) -> QualityRating:
        """Convert debt score to quality rating."""
        quality = 100.0 - debt_score
        if quality >= 85:
            return QualityRating.EXCELLENT
        elif quality >= 70:
            return QualityRating.GOOD
        elif quality >= 55:
            return QualityRating.FAIR
        elif quality >= 40:
            return QualityRating.POOR
        else:
            return QualityRating.CRITICAL

    def _score_to_rating(self, score: float) -> QualityRating:
        """Convert quality score to rating."""
        if score >= 85:
            return QualityRating.EXCELLENT
        elif score >= 70:
            return QualityRating.GOOD
        elif score >= 55:
            return QualityRating.FAIR
        elif score >= 40:
            return QualityRating.POOR
        else:
            return QualityRating.CRITICAL

    def _perform_health_checks(
        self,
        symbol: Symbol,
        security_issues: int,
        performance_issues: int,
        code_smells: int,
        maintainability_score: float,
        testability_score: float,
        has_docstring: bool,
    ) -> List[HealthCheck]:
        """Perform quality health checks."""
        checks = []

        # Security check
        if security_issues == 0:
            checks.append(
                HealthCheck(
                    check_name="Security",
                    passed=True,
                    score=1.0,
                    details="No security issues detected",
                    recommendation="Continue security best practices",
                    severity="low",
                )
            )
        elif security_issues <= 1:
            checks.append(
                HealthCheck(
                    check_name="Security",
                    passed=False,
                    score=0.7,
                    details=f"{security_issues} security issue(s) detected",
                    recommendation="Address security vulnerabilities immediately",
                    severity="high",
                )
            )
        else:
            checks.append(
                HealthCheck(
                    check_name="Security",
                    passed=False,
                    score=max(0.0, 1.0 - security_issues * 0.2),
                    details=f"{security_issues} security issues detected",
                    recommendation="Critical: Audit and fix all security issues",
                    severity="critical",
                )
            )

        # Performance check
        if performance_issues == 0:
            checks.append(
                HealthCheck(
                    check_name="Performance",
                    passed=True,
                    score=1.0,
                    details="No performance issues detected",
                    recommendation="Monitor performance metrics",
                    severity="low",
                )
            )
        else:
            checks.append(
                HealthCheck(
                    check_name="Performance",
                    passed=False,
                    score=max(0.0, 1.0 - performance_issues * 0.2),
                    details=f"{performance_issues} performance issue(s) detected",
                    recommendation="Optimize performance bottlenecks",
                    severity="medium" if performance_issues <= 2 else "high",
                )
            )

        # Code quality check
        if code_smells <= 2:
            checks.append(
                HealthCheck(
                    check_name="Code Quality",
                    passed=code_smells == 0,
                    score=1.0 - code_smells * 0.2,
                    details=(
                        f"{code_smells} code smell(s) detected"
                        if code_smells > 0
                        else "Code quality is good"
                    ),
                    recommendation=(
                        "Refactor to eliminate remaining smells"
                        if code_smells > 0
                        else "Maintain current quality"
                    ),
                    severity="low" if code_smells <= 1 else "medium",
                )
            )
        else:
            checks.append(
                HealthCheck(
                    check_name="Code Quality",
                    passed=False,
                    score=max(0.0, 1.0 - code_smells * 0.15),
                    details=f"{code_smells} code smells detected",
                    recommendation="Significant refactoring needed",
                    severity="high",
                )
            )

        # Maintainability check
        if maintainability_score >= 70:
            checks.append(
                HealthCheck(
                    check_name="Maintainability",
                    passed=True,
                    score=maintainability_score / 100.0,
                    details="Code is well-structured and maintainable",
                    recommendation="Continue good practices",
                    severity="low",
                )
            )
        elif maintainability_score >= 55:
            checks.append(
                HealthCheck(
                    check_name="Maintainability",
                    passed=False,
                    score=maintainability_score / 100.0,
                    details="Maintainability could be improved",
                    recommendation="Refactor for better structure",
                    severity="medium",
                )
            )
        else:
            checks.append(
                HealthCheck(
                    check_name="Maintainability",
                    passed=False,
                    score=maintainability_score / 100.0,
                    details="Code is difficult to maintain",
                    recommendation="Critical: Refactor to improve maintainability",
                    severity="critical",
                )
            )

        # Testability check
        if testability_score >= 70:
            checks.append(
                HealthCheck(
                    check_name="Testability",
                    passed=True,
                    score=testability_score / 100.0,
                    details="Code is highly testable",
                    recommendation="Maintain good testability practices",
                    severity="low",
                )
            )
        else:
            checks.append(
                HealthCheck(
                    check_name="Testability",
                    passed=False,
                    score=testability_score / 100.0,
                    details="Code could be more testable",
                    recommendation="Improve dependency injection and reduce side effects",
                    severity="medium" if testability_score >= 50 else "high",
                )
            )

        # Documentation check
        if has_docstring:
            checks.append(
                HealthCheck(
                    check_name="Documentation",
                    passed=True,
                    score=1.0,
                    details="Code is documented",
                    recommendation="Keep documentation up-to-date",
                    severity="low",
                )
            )
        else:
            checks.append(
                HealthCheck(
                    check_name="Documentation",
                    passed=False,
                    score=0.0,
                    details="Code lacks documentation",
                    recommendation="Add comprehensive docstring",
                    severity="medium",
                )
            )

        return checks

    def _generate_improvements(
        self,
        component_scores: List[ComponentScore],
        security_issues: int,
        performance_issues: int,
        code_smells: int,
        maintainability_score: float,
        testability_score: float,
        has_docstring: bool,
    ) -> List[QualityImprovement]:
        """Generate quality improvement recommendations."""
        improvements = []
        priority = 1

        # Security improvements
        if security_issues > 0:
            improvements.append(
                QualityImprovement(
                    priority=priority,
                    title="Fix Security Vulnerabilities",
                    description=f"Address {security_issues} security issue(s)",
                    estimated_effort="4-8 hours",
                    expected_impact=f"Eliminate security debt, +{security_issues * 10}-{security_issues * 20} quality score",
                    category="security",
                )
            )
            priority += 1

        # Maintainability improvements
        if maintainability_score < 60:
            improvements.append(
                QualityImprovement(
                    priority=priority,
                    title="Improve Maintainability",
                    description="Refactor code structure and reduce complexity",
                    estimated_effort="1-3 days",
                    expected_impact=f"+{min(40, 100 - maintainability_score)} to maintainability score",
                    category="maintainability",
                )
            )
            priority += 1

        # Performance improvements
        if performance_issues > 0:
            improvements.append(
                QualityImprovement(
                    priority=priority,
                    title="Optimize Performance",
                    description=f"Fix {performance_issues} performance issue(s)",
                    estimated_effort="6-12 hours",
                    expected_impact="+15-30% performance improvement",
                    category="performance",
                )
            )
            priority += 1

        # Code quality improvements
        if code_smells > 0:
            improvements.append(
                QualityImprovement(
                    priority=priority,
                    title="Eliminate Code Smells",
                    description=f"Refactor to remove {code_smells} code smell(s)",
                    estimated_effort="4-8 hours",
                    expected_impact=f"Reduce smells by 100%, +{code_smells * 5}-{code_smells * 15} quality score",
                    category="quality",
                )
            )
            priority += 1

        # Testability improvements
        if testability_score < 65:
            improvements.append(
                QualityImprovement(
                    priority=priority,
                    title="Improve Testability",
                    description="Refactor for better dependency injection and fewer side effects",
                    estimated_effort="1-2 days",
                    expected_impact=f"+{min(35, 100 - testability_score)} to testability score",
                    category="testability",
                )
            )
            priority += 1

        # Documentation improvements
        if not has_docstring:
            improvements.append(
                QualityImprovement(
                    priority=priority,
                    title="Add Documentation",
                    description="Write comprehensive docstring and examples",
                    estimated_effort="1-2 hours",
                    expected_impact="+10-20 to documentation score",
                    category="documentation",
                )
            )
            priority += 1

        return improvements

    def score_all(self, symbols_with_metrics: List[Tuple]) -> List[CodeQualityScore]:
        """Score multiple symbols.

        Args:
            symbols_with_metrics: List of (symbol, security, performance, smells, maint, test, doc) tuples

        Returns:
            List of CodeQualityScores
        """
        self.scores = []
        for item in symbols_with_metrics:
            symbol = item[0]
            security = item[1] if len(item) > 1 else 0
            performance = item[2] if len(item) > 2 else 0
            smells = item[3] if len(item) > 3 else 0
            maint = item[4] if len(item) > 4 else 50.0
            test = item[5] if len(item) > 5 else 50.0
            doc = item[6] if len(item) > 6 else False

            score = self.score_symbol(symbol, security, performance, smells, maint, test, doc)
            if score:
                pass  # Already appended

        return self.scores

    def get_quality_report(self) -> Dict:
        """Generate comprehensive quality report."""
        if not self.scores:
            return {"status": "no_assessment", "message": "No code quality assessments available"}

        avg_score = sum(s.overall_score for s in self.scores) / len(self.scores)
        avg_rating = self._score_to_rating(avg_score)
        total_issues = sum(s.total_issues for s in self.scores)
        critical_issues = sum(s.critical_issues for s in self.scores)

        return {
            "status": "assessed",
            "total_symbols": len(self.scores),
            "average_quality_score": avg_score,
            "average_quality_rating": avg_rating.value,
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "highest_quality": [
                {
                    "symbol": s.symbol.name,
                    "score": s.overall_score,
                    "rating": s.overall_rating.value,
                }
                for s in sorted(self.scores, key=lambda s: s.overall_score, reverse=True)[:5]
            ],
            "lowest_quality": [
                {
                    "symbol": s.symbol.name,
                    "score": s.overall_score,
                    "rating": s.overall_rating.value,
                    "critical_count": s.critical_issues,
                }
                for s in sorted(self.scores, key=lambda s: s.overall_score)[:5]
            ],
            "top_improvements": self._get_top_improvements(),
            "quality_breakdown": self._get_quality_breakdown(),
        }

    def _get_top_improvements(self, limit: int = 10) -> List[Dict]:
        """Get top improvement recommendations across all symbols."""
        all_improvements = []
        for score in self.scores:
            all_improvements.extend(score.improvements)

        # Sort by priority and deduplicate by category
        seen_categories = set()
        top = []
        for imp in sorted(all_improvements, key=lambda x: x.priority):
            if imp.category not in seen_categories and len(top) < limit:
                top.append(
                    {
                        "title": imp.title,
                        "category": imp.category,
                        "effort": imp.estimated_effort,
                        "impact": imp.expected_impact,
                    }
                )
                seen_categories.add(imp.category)

        return top

    def _get_quality_breakdown(self) -> Dict[str, int]:
        """Get breakdown of quality ratings."""
        ratings = {rating.value: 0 for rating in QualityRating}
        for score in self.scores:
            ratings[score.overall_rating.value] += 1
        return ratings
