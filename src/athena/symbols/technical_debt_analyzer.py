"""Technical Debt Analyzer for assessing accumulated technical debt.

Provides:
- Technical debt scoring synthesizing all analyzers
- Debt categorization (security, performance, quality, testing)
- Debt prioritization and recommendations
- Refactoring roadmap suggestions
- Debt impact assessment
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

from .symbol_models import Symbol, SymbolType


class DebtCategory(str, Enum):
    """Categories of technical debt."""
    SECURITY = "security"  # Security vulnerabilities
    PERFORMANCE = "performance"  # Performance issues
    QUALITY = "quality"  # Code quality/smells
    TESTING = "testing"  # Testing gaps
    DOCUMENTATION = "documentation"  # Missing documentation
    MAINTAINABILITY = "maintainability"  # High complexity, tight coupling


class DebtSeverity(str, Enum):
    """Severity levels for debt items."""
    CRITICAL = "critical"  # Blocks deployment or causes crashes
    HIGH = "high"  # Significant issues, should fix soon
    MEDIUM = "medium"  # Moderate issues, plan to fix
    LOW = "low"  # Minor issues, nice to fix
    INFO = "info"  # Informational, no action needed


class DebtPriority(str, Enum):
    """Priority for addressing debt (based on impact + effort)."""
    CRITICAL_PATH = "critical_path"  # Highest priority
    HIGH_IMPACT = "high_impact"  # High ROI
    MEDIUM_IMPACT = "medium_impact"  # Moderate ROI
    LOW_PRIORITY = "low_priority"  # Low ROI


@dataclass
class DebtItem:
    """Individual technical debt item."""
    symbol: Symbol
    category: DebtCategory
    severity: DebtSeverity
    title: str
    description: str
    estimated_effort: float  # Hours to fix
    estimated_impact: float  # 0-1, ROI value
    priority: DebtPriority
    related_issues: List[str] = field(default_factory=list)


@dataclass
class DebtScore:
    """Technical debt score for a symbol."""
    symbol: Symbol
    overall_debt_score: float  # 0-100, higher = more debt
    debt_items: List[DebtItem]
    
    # Debt breakdown by category
    security_debt: float
    performance_debt: float
    quality_debt: float
    testing_debt: float
    documentation_debt: float
    maintainability_debt: float
    
    # Estimated effort and impact
    total_estimated_effort: float  # Hours
    total_estimated_impact: float  # Impact points
    efficiency_ratio: float  # Impact/Effort


@dataclass
class DebtMetrics:
    """Overall technical debt metrics."""
    total_symbols: int
    total_debt_items: int
    average_debt_score: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_estimated_effort: float
    average_effort_per_item: float
    most_common_debt_category: DebtCategory
    highest_priority_debt_items: int


class TechnicalDebtAnalyzer:
    """Analyzes accumulated technical debt across multiple dimensions."""

    def __init__(self):
        """Initialize analyzer."""
        self.scores: List[DebtScore] = []
        self.metrics: Optional[DebtMetrics] = None

    def analyze_symbol(self, symbol: Symbol,
                      security_issues: int = 0,
                      performance_issues: int = 0,
                      code_smells: int = 0,
                      maintainability_score: float = 50.0,
                      testability_score: float = 50.0,
                      has_docstring: bool = False) -> Optional[DebtScore]:
        """Analyze technical debt of a single symbol.
        
        Args:
            symbol: Symbol to analyze
            security_issues: Number of security issues found
            performance_issues: Number of performance issues found
            code_smells: Number of code smells found
            maintainability_score: Maintainability score (0-100)
            testability_score: Testability score (0-100)
            has_docstring: Whether symbol has documentation
            
        Returns:
            DebtScore or None if not applicable
        """
        if symbol.symbol_type not in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.CLASS]:
            return None

        # Calculate debt by category
        security_debt = self._calculate_security_debt(security_issues)
        performance_debt = self._calculate_performance_debt(performance_issues)
        quality_debt = self._calculate_quality_debt(code_smells)
        testing_debt = self._calculate_testing_debt(testability_score)
        documentation_debt = self._calculate_documentation_debt(has_docstring)
        maintainability_debt = self._calculate_maintainability_debt(maintainability_score)

        # Weighted overall score
        overall_debt_score = (
            security_debt * 0.25 +
            performance_debt * 0.20 +
            quality_debt * 0.15 +
            testing_debt * 0.15 +
            documentation_debt * 0.10 +
            maintainability_debt * 0.15
        )

        # Detect debt items
        debt_items = self._detect_debt_items(
            symbol, security_issues, performance_issues, code_smells,
            maintainability_score, testability_score, has_docstring
        )

        # Calculate effort and impact
        total_effort = sum(item.estimated_effort for item in debt_items)
        total_impact = sum(item.estimated_impact for item in debt_items)
        efficiency_ratio = total_impact / total_effort if total_effort > 0 else 0.0

        score = DebtScore(
            symbol=symbol,
            overall_debt_score=overall_debt_score,
            debt_items=debt_items,
            security_debt=security_debt,
            performance_debt=performance_debt,
            quality_debt=quality_debt,
            testing_debt=testing_debt,
            documentation_debt=documentation_debt,
            maintainability_debt=maintainability_debt,
            total_estimated_effort=total_effort,
            total_estimated_impact=total_impact,
            efficiency_ratio=efficiency_ratio
        )

        self.scores.append(score)
        return score

    def analyze_all(self, symbols_with_issues: List[Tuple]) -> List[DebtScore]:
        """Analyze debt for multiple symbols.
        
        Args:
            symbols_with_issues: List of (symbol, security, performance, smells, maint, test, doc) tuples
            
        Returns:
            List of DebtScores
        """
        self.scores = []
        for item in symbols_with_issues:
            symbol = item[0]
            security = item[1] if len(item) > 1 else 0
            performance = item[2] if len(item) > 2 else 0
            smells = item[3] if len(item) > 3 else 0
            maint = item[4] if len(item) > 4 else 50.0
            test = item[5] if len(item) > 5 else 50.0
            doc = item[6] if len(item) > 6 else False
            
            score = self.analyze_symbol(symbol, security, performance, smells, maint, test, doc)
            if score:
                pass  # Already appended
        return self.scores

    def _calculate_security_debt(self, security_issues: int) -> float:
        """Calculate security debt (0-100)."""
        # Each security issue adds significant debt
        if security_issues == 0:
            return 0.0
        elif security_issues == 1:
            return 30.0
        elif security_issues == 2:
            return 60.0
        else:
            return min(100.0, 30.0 + security_issues * 15.0)

    def _calculate_performance_debt(self, performance_issues: int) -> float:
        """Calculate performance debt (0-100)."""
        if performance_issues == 0:
            return 0.0
        elif performance_issues == 1:
            return 25.0
        elif performance_issues == 2:
            return 50.0
        else:
            return min(100.0, 25.0 + performance_issues * 12.0)

    def _calculate_quality_debt(self, code_smells: int) -> float:
        """Calculate quality debt from code smells (0-100)."""
        if code_smells == 0:
            return 0.0
        elif code_smells == 1:
            return 15.0
        elif code_smells <= 3:
            return 30.0
        elif code_smells <= 5:
            return 50.0
        else:
            return min(100.0, 50.0 + code_smells * 5.0)

    def _calculate_testing_debt(self, testability_score: float) -> float:
        """Calculate testing debt from testability score."""
        # Lower testability = higher debt
        # Score 0-100 maps to debt 100-0
        testing_debt = 100.0 - testability_score
        return max(0.0, min(100.0, testing_debt))

    def _calculate_documentation_debt(self, has_docstring: bool) -> float:
        """Calculate documentation debt."""
        return 0.0 if has_docstring else 50.0

    def _calculate_maintainability_debt(self, maintainability_score: float) -> float:
        """Calculate maintainability debt."""
        # Lower maintainability = higher debt
        maintainability_debt = 100.0 - maintainability_score
        return max(0.0, min(100.0, maintainability_debt))

    def _detect_debt_items(self, symbol: Symbol,
                          security_issues: int,
                          performance_issues: int,
                          code_smells: int,
                          maintainability_score: float,
                          testability_score: float,
                          has_docstring: bool) -> List[DebtItem]:
        """Detect individual debt items."""
        items = []

        # Security debt items
        if security_issues > 0:
            for i in range(min(security_issues, 3)):  # Cap at 3 items
                items.append(DebtItem(
                    symbol=symbol,
                    category=DebtCategory.SECURITY,
                    severity=DebtSeverity.CRITICAL,
                    title=f"Security vulnerability #{i+1}",
                    description="Fix identified security vulnerability",
                    estimated_effort=8.0,
                    estimated_impact=0.9,
                    priority=DebtPriority.CRITICAL_PATH,
                    related_issues=[]
                ))

        # Performance debt items
        if performance_issues > 0:
            for i in range(min(performance_issues, 2)):
                items.append(DebtItem(
                    symbol=symbol,
                    category=DebtCategory.PERFORMANCE,
                    severity=DebtSeverity.HIGH,
                    title=f"Performance issue #{i+1}",
                    description="Optimize performance bottleneck",
                    estimated_effort=6.0,
                    estimated_impact=0.7,
                    priority=DebtPriority.HIGH_IMPACT,
                    related_issues=[]
                ))

        # Quality debt items (code smells)
        if code_smells > 0:
            for i in range(min(code_smells, 2)):
                items.append(DebtItem(
                    symbol=symbol,
                    category=DebtCategory.QUALITY,
                    severity=DebtSeverity.MEDIUM,
                    title=f"Code smell #{i+1}",
                    description="Refactor to eliminate code smell",
                    estimated_effort=4.0,
                    estimated_impact=0.5,
                    priority=DebtPriority.MEDIUM_IMPACT,
                    related_issues=[]
                ))

        # Testing debt item
        if testability_score < 60:
            items.append(DebtItem(
                symbol=symbol,
                category=DebtCategory.TESTING,
                severity=DebtSeverity.MEDIUM,
                title="Poor testability",
                description=f"Improve testability (score: {testability_score:.0f})",
                estimated_effort=5.0,
                estimated_impact=0.6,
                priority=DebtPriority.MEDIUM_IMPACT,
                related_issues=[]
            ))

        # Documentation debt item
        if not has_docstring:
            items.append(DebtItem(
                symbol=symbol,
                category=DebtCategory.DOCUMENTATION,
                severity=DebtSeverity.LOW,
                title="Missing documentation",
                description="Add comprehensive documentation",
                estimated_effort=2.0,
                estimated_impact=0.3,
                priority=DebtPriority.LOW_PRIORITY,
                related_issues=[]
            ))

        # Maintainability debt item
        if maintainability_score < 60:
            items.append(DebtItem(
                symbol=symbol,
                category=DebtCategory.MAINTAINABILITY,
                severity=DebtSeverity.MEDIUM if maintainability_score > 40 else DebtSeverity.HIGH,
                title="Low maintainability",
                description=f"Improve maintainability (score: {maintainability_score:.0f})",
                estimated_effort=8.0,
                estimated_impact=0.7,
                priority=DebtPriority.MEDIUM_IMPACT,
                related_issues=[]
            ))

        return items

    def get_debt_by_category(self, category: DebtCategory) -> List[DebtScore]:
        """Get scores with debt in specific category."""
        return [s for s in self.scores if any(item.category == category for item in s.debt_items)]

    def get_critical_debt(self) -> List[DebtItem]:
        """Get all critical debt items."""
        critical = []
        for score in self.scores:
            critical.extend([item for item in score.debt_items if item.severity == DebtSeverity.CRITICAL])
        return critical

    def get_highest_debt_symbols(self, limit: int = 10) -> List[DebtScore]:
        """Get symbols with highest debt."""
        sorted_scores = sorted(self.scores, key=lambda s: s.overall_debt_score, reverse=True)
        return sorted_scores[:limit]

    def get_best_roi_debt_items(self, limit: int = 10) -> List[DebtItem]:
        """Get debt items with highest effort/impact ratio (best ROI)."""
        all_items = []
        for score in self.scores:
            all_items.extend(score.debt_items)
        
        # Sort by impact/effort ratio (highest = best ROI)
        sorted_items = sorted(all_items, key=lambda i: i.estimated_impact / max(0.1, i.estimated_effort), reverse=True)
        return sorted_items[:limit]

    def get_debt_report(self) -> Dict:
        """Generate comprehensive debt report."""
        if not self.scores:
            return {
                "status": "no_analysis",
                "message": "No symbols analyzed yet"
            }

        self._calculate_metrics()

        return {
            "status": "analyzed",
            "total_symbols": len(self.scores),
            "average_debt_score": self.metrics.average_debt_score,
            "severity_breakdown": {
                "critical": self.metrics.critical_count,
                "high": self.metrics.high_count,
                "medium": self.metrics.medium_count,
                "low": self.metrics.low_count
            },
            "total_debt_items": self.metrics.total_debt_items,
            "total_estimated_effort": self.metrics.total_estimated_effort,
            "average_effort_per_item": self.metrics.average_effort_per_item,
            "most_common_category": self.metrics.most_common_debt_category.value,
            "critical_path_items": self.metrics.highest_priority_debt_items,
            "highest_debt_symbols": [
                {
                    "symbol": s.symbol.name,
                    "debt_score": s.overall_debt_score,
                    "item_count": len(s.debt_items),
                    "estimated_effort": s.total_estimated_effort
                }
                for s in self.get_highest_debt_symbols(5)
            ],
            "best_roi_items": [
                {
                    "symbol": item.symbol.name,
                    "category": item.category.value,
                    "title": item.title,
                    "effort": item.estimated_effort,
                    "impact": item.estimated_impact,
                    "roi": item.estimated_impact / max(0.1, item.estimated_effort)
                }
                for item in self.get_best_roi_debt_items(5)
            ]
        }

    def _calculate_metrics(self):
        """Calculate overall metrics."""
        if not self.scores:
            self.metrics = DebtMetrics(
                total_symbols=0,
                total_debt_items=0,
                average_debt_score=0.0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                total_estimated_effort=0.0,
                average_effort_per_item=0.0,
                most_common_debt_category=DebtCategory.QUALITY,
                highest_priority_debt_items=0
            )
            return

        avg_score = sum(s.overall_debt_score for s in self.scores) / len(self.scores)
        
        # Count all debt items and by severity
        all_items = []
        for score in self.scores:
            all_items.extend(score.debt_items)
        
        critical = len([i for i in all_items if i.severity == DebtSeverity.CRITICAL])
        high = len([i for i in all_items if i.severity == DebtSeverity.HIGH])
        medium = len([i for i in all_items if i.severity == DebtSeverity.MEDIUM])
        low = len([i for i in all_items if i.severity == DebtSeverity.LOW])
        
        # Most common category
        category_counts = {}
        for item in all_items:
            category_counts[item.category] = category_counts.get(item.category, 0) + 1
        
        most_common = max(category_counts, key=category_counts.get) if category_counts else DebtCategory.QUALITY
        
        # Critical path items (high priority)
        critical_path = len([i for i in all_items if i.priority == DebtPriority.CRITICAL_PATH])
        
        # Total effort
        total_effort = sum(i.estimated_effort for i in all_items)
        avg_effort = total_effort / len(all_items) if all_items else 0.0

        self.metrics = DebtMetrics(
            total_symbols=len(self.scores),
            total_debt_items=len(all_items),
            average_debt_score=avg_score,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            total_estimated_effort=total_effort,
            average_effort_per_item=avg_effort,
            most_common_debt_category=most_common,
            highest_priority_debt_items=critical_path
        )
