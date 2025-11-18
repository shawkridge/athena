"""Maintainability Analyzer for assessing code maintainability.

Provides:
- Maintainability index calculation
- Code quality scoring
- Maintenance risk assessment
- Improvement recommendations
- Synthesis of all previous analyzers
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import re

from .symbol_models import Symbol, SymbolType


class MaintainabilityRating(str, Enum):
    """Maintainability ratings."""

    EXCELLENT = "excellent"  # 80+
    GOOD = "good"  # 60-79
    FAIR = "fair"  # 40-59
    POOR = "poor"  # 20-39
    CRITICAL = "critical"  # <20


class RiskLevel(str, Enum):
    """Risk levels for maintenance."""

    LOW = "low"  # Easy to maintain
    MEDIUM = "medium"  # Moderate maintenance effort
    HIGH = "high"  # High maintenance effort
    CRITICAL = "critical"  # Very difficult to maintain


@dataclass
class MaintainabilityScore:
    """Maintainability score for a symbol."""

    symbol: Symbol
    overall_score: float  # 0-100
    rating: MaintainabilityRating
    risk_level: RiskLevel

    # Component scores
    complexity_score: float  # 0-100
    documentation_score: float  # 0-100
    size_score: float  # 0-100
    duplication_score: float  # 0-100
    style_score: float  # 0-100

    factors: Dict[str, float] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class MaintainabilityMetrics:
    """Overall maintainability metrics."""

    total_symbols: int
    average_score: float
    excellent_count: int
    good_count: int
    fair_count: int
    poor_count: int
    critical_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    code_health_percentage: float  # % of symbols with good+ rating


class MaintainabilityAnalyzer:
    """Analyzes code maintainability across multiple dimensions."""

    def __init__(self):
        """Initialize analyzer with default thresholds."""
        self.scores: List[MaintainabilityScore] = []
        self.metrics: Optional[MaintainabilityMetrics] = None

        # Thresholds for component scoring
        self.complexity_threshold = 10  # Max acceptable cyclomatic complexity
        self.lines_threshold = 50  # Max acceptable lines per method
        self.params_threshold = 5  # Max acceptable parameters
        self.doc_threshold = 80  # Min acceptable documentation percentage
        self.duplication_threshold = 10  # Max acceptable duplication percentage

    def analyze_symbol(self, symbol: Symbol) -> MaintainabilityScore:
        """Analyze maintainability of a single symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            MaintainabilityScore with overall rating
        """
        if symbol.symbol_type not in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.CLASS]:
            return None

        # Calculate component scores
        complexity_score = self._calculate_complexity_score(symbol)
        documentation_score = self._calculate_documentation_score(symbol)
        size_score = self._calculate_size_score(symbol)
        duplication_score = self._calculate_duplication_score(symbol)
        style_score = self._calculate_style_score(symbol)

        # Weighted average for overall score
        overall_score = (
            complexity_score * 0.25
            + documentation_score * 0.25
            + size_score * 0.20
            + duplication_score * 0.15
            + style_score * 0.15
        )

        # Determine rating and risk
        rating = self._get_rating(overall_score)
        risk_level = self._get_risk_level(overall_score)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            symbol,
            complexity_score,
            documentation_score,
            size_score,
            duplication_score,
            style_score,
        )

        score = MaintainabilityScore(
            symbol=symbol,
            overall_score=overall_score,
            rating=rating,
            risk_level=risk_level,
            complexity_score=complexity_score,
            documentation_score=documentation_score,
            size_score=size_score,
            duplication_score=duplication_score,
            style_score=style_score,
            factors={
                "cyclomatic_complexity": (
                    symbol.metrics.cyclomatic_complexity if symbol.metrics else 0
                ),
                "lines_of_code": symbol.line_end - symbol.line_start + 1,
                "parameters": len(symbol.signature.split(",")) if symbol.signature else 0,
                "has_docstring": bool(symbol.docstring and symbol.docstring.strip()),
                "is_async": symbol.is_async,
            },
            suggestions=suggestions,
        )

        self.scores.append(score)
        return score

    def analyze_all(self, symbols: List[Symbol]) -> List[MaintainabilityScore]:
        """Analyze maintainability of multiple symbols.

        Args:
            symbols: List of symbols to analyze

        Returns:
            List of MaintainabilityScores
        """
        self.scores = []
        for symbol in symbols:
            score = self.analyze_symbol(symbol)
            if score:
                pass  # Already appended in analyze_symbol
        return self.scores

    def _calculate_complexity_score(self, symbol: Symbol) -> float:
        """Calculate complexity component score (0-100)."""
        if not symbol.metrics:
            return 50.0

        cc = symbol.metrics.cyclomatic_complexity
        # Higher complexity = lower score
        # threshold=10 gives score 50
        score = max(0, 100 - (cc / self.complexity_threshold * 100))
        return min(100, score)

    def _calculate_documentation_score(self, symbol: Symbol) -> float:
        """Calculate documentation component score (0-100)."""
        if not symbol.docstring or symbol.docstring.strip() == "":
            return 0.0

        # Check docstring quality/completeness
        doc = symbol.docstring.lower()
        quality_points = 0
        max_points = 100

        # Check for description
        if len(doc) > 10:
            quality_points += 40

        # Check for parameter documentation
        if "arg" in doc or "param" in doc or "parameter" in doc:
            quality_points += 30

        # Check for return documentation
        if "return" in doc or "returns" in doc:
            quality_points += 20

        # Check for exception documentation
        if "raise" in doc or "except" in doc or "error" in doc:
            quality_points += 10

        return min(100, quality_points)

    def _calculate_size_score(self, symbol: Symbol) -> float:
        """Calculate size/length component score (0-100)."""
        loc = symbol.line_end - symbol.line_start + 1

        # Score based on lines of code
        if loc <= 20:
            return 100.0
        elif loc <= 50:
            return 80.0
        elif loc <= 100:
            return 60.0
        elif loc <= 200:
            return 40.0
        else:
            return 20.0

    def _calculate_duplication_score(self, symbol: Symbol) -> float:
        """Calculate duplication component score (0-100)."""
        if not symbol.code:
            return 50.0

        # Estimate duplication risk based on code patterns
        code_lower = symbol.code.lower()

        # Check for repeated patterns
        repeated_patterns = 0
        patterns = [
            r"if\s+\w+\s*[=!<>]+",  # Repeated conditions
            r"for\s+\w+\s+in",  # Repeated loops
            r'\w+\s*=\s*["\']',  # Repeated assignments
        ]

        for pattern in patterns:
            matches = len(re.findall(pattern, code_lower))
            if matches > 3:
                repeated_patterns += 1

        # Score based on duplication risk
        duplication_risk = repeated_patterns / 3.0 * 100
        return max(0, 100 - duplication_risk)

    def _calculate_style_score(self, symbol: Symbol) -> float:
        """Calculate style/consistency component score (0-100)."""
        score = 100.0

        if not symbol.code:
            return 50.0

        code = symbol.code

        # Check naming conventions
        if not re.match(r"^[a-z_][a-z0-9_]*$", symbol.name):
            score -= 10

        # Check for magic strings/numbers
        magic_count = len(re.findall(r'["\'].*?["\']|[0-9]{3,}', code))
        if magic_count > 5:
            score -= 15

        # Check for TODO/FIXME comments
        if "todo" in code.lower() or "fixme" in code.lower():
            score -= 10

        # Check for mixed indentation
        lines = code.split("\n")
        indent_types = set()
        for line in lines:
            if line and (line[0] == " " or line[0] == "\t"):
                if line[0] == " ":
                    indent_types.add("space")
                else:
                    indent_types.add("tab")

        if len(indent_types) > 1:
            score -= 10

        return max(0, min(100, score))

    def _get_rating(self, score: float) -> MaintainabilityRating:
        """Convert score to rating."""
        if score >= 80:
            return MaintainabilityRating.EXCELLENT
        elif score >= 60:
            return MaintainabilityRating.GOOD
        elif score >= 40:
            return MaintainabilityRating.FAIR
        elif score >= 20:
            return MaintainabilityRating.POOR
        else:
            return MaintainabilityRating.CRITICAL

    def _get_risk_level(self, score: float) -> RiskLevel:
        """Convert score to risk level."""
        if score >= 70:
            return RiskLevel.LOW
        elif score >= 50:
            return RiskLevel.MEDIUM
        elif score >= 30:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_suggestions(
        self,
        symbol: Symbol,
        complexity_score: float,
        documentation_score: float,
        size_score: float,
        duplication_score: float,
        style_score: float,
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if complexity_score < 50:
            suggestions.append("Reduce cyclomatic complexity by breaking into smaller functions")

        if documentation_score < 50:
            suggestions.append(
                "Add comprehensive documentation with parameter and return descriptions"
            )

        if size_score < 60:
            loc = symbol.line_end - symbol.line_start + 1
            if loc > 100:
                suggestions.append(f"Function is too long ({loc} lines). Break into smaller units.")
            else:
                suggestions.append("Consider extracting some logic into separate methods")

        if duplication_score < 70:
            suggestions.append("Reduce code duplication by extracting common patterns")

        if style_score < 80:
            suggestions.append("Improve code style and naming consistency")

        return suggestions

    def get_scores_by_rating(self, rating: MaintainabilityRating) -> List[MaintainabilityScore]:
        """Get all scores with specific rating."""
        return [s for s in self.scores if s.rating == rating]

    def get_scores_by_risk(self, risk: RiskLevel) -> List[MaintainabilityScore]:
        """Get all scores with specific risk level."""
        return [s for s in self.scores if s.risk_level == risk]

    def get_lowest_scoring_symbols(self, limit: int = 10) -> List[MaintainabilityScore]:
        """Get lowest scoring symbols."""
        sorted_scores = sorted(self.scores, key=lambda s: s.overall_score)
        return sorted_scores[:limit]

    def get_maintainability_report(self) -> Dict:
        """Generate comprehensive maintainability report."""
        if not self.scores:
            return {"status": "no_analysis", "message": "No symbols analyzed yet"}

        self._calculate_metrics()

        excellent = len([s for s in self.scores if s.rating == MaintainabilityRating.EXCELLENT])
        good = len([s for s in self.scores if s.rating == MaintainabilityRating.GOOD])
        fair = len([s for s in self.scores if s.rating == MaintainabilityRating.FAIR])
        poor = len([s for s in self.scores if s.rating == MaintainabilityRating.POOR])
        critical = len([s for s in self.scores if s.rating == MaintainabilityRating.CRITICAL])

        return {
            "status": "analyzed",
            "total_symbols": len(self.scores),
            "average_score": self.metrics.average_score,
            "code_health_percentage": self.metrics.code_health_percentage,
            "distribution": {
                "excellent": excellent,
                "good": good,
                "fair": fair,
                "poor": poor,
                "critical": critical,
            },
            "risk_distribution": {
                "low": self.metrics.low_risk_count,
                "medium": self.metrics.medium_risk_count,
                "high": self.metrics.high_risk_count,
                "critical": self.metrics.critical_count,
            },
            "worst_offenders": [
                {
                    "symbol": s.symbol.name,
                    "score": s.overall_score,
                    "rating": s.rating.value,
                    "suggestions": s.suggestions,
                }
                for s in self.get_lowest_scoring_symbols(5)
            ],
        }

    def _calculate_metrics(self):
        """Calculate overall metrics."""
        if not self.scores:
            self.metrics = MaintainabilityMetrics(
                total_symbols=0,
                average_score=0,
                excellent_count=0,
                good_count=0,
                fair_count=0,
                poor_count=0,
                critical_count=0,
                high_risk_count=0,
                medium_risk_count=0,
                low_risk_count=0,
                code_health_percentage=0.0,
            )
            return

        avg_score = sum(s.overall_score for s in self.scores) / len(self.scores)

        excellent = len([s for s in self.scores if s.rating == MaintainabilityRating.EXCELLENT])
        good = len([s for s in self.scores if s.rating == MaintainabilityRating.GOOD])
        fair = len([s for s in self.scores if s.rating == MaintainabilityRating.FAIR])
        poor = len([s for s in self.scores if s.rating == MaintainabilityRating.POOR])
        critical = len([s for s in self.scores if s.rating == MaintainabilityRating.CRITICAL])

        low_risk = len([s for s in self.scores if s.risk_level == RiskLevel.LOW])
        medium_risk = len([s for s in self.scores if s.risk_level == RiskLevel.MEDIUM])
        high_risk = len([s for s in self.scores if s.risk_level == RiskLevel.HIGH])
        critical_risk = len([s for s in self.scores if s.risk_level == RiskLevel.CRITICAL])

        # Code health = % of symbols with GOOD or EXCELLENT rating
        health_count = excellent + good
        health_percentage = (health_count / len(self.scores) * 100) if self.scores else 0

        self.metrics = MaintainabilityMetrics(
            total_symbols=len(self.scores),
            average_score=avg_score,
            excellent_count=excellent,
            good_count=good,
            fair_count=fair,
            poor_count=poor,
            critical_count=critical,
            high_risk_count=high_risk,
            medium_risk_count=medium_risk,
            low_risk_count=low_risk,
            code_health_percentage=health_percentage,
        )
