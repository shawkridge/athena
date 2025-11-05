"""Complexity Analyzer for code complexity metrics.

Provides:
- Cyclomatic complexity calculation
- Cognitive complexity calculation
- Essential complexity calculation
- Complexity trends and distribution
- Refactoring suggestions based on complexity
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .symbol_models import Symbol


class ComplexityCategory(str, Enum):
    """Code complexity categories."""
    SIMPLE = "simple"  # 1-5
    MODERATE = "moderate"  # 6-15
    COMPLEX = "complex"  # 16-30
    VERY_COMPLEX = "very_complex"  # 31-50
    EXTREMELY_COMPLEX = "extremely_complex"  # >50


@dataclass
class ComplexityMetric:
    """Complexity metric for a symbol."""
    symbol: Symbol
    cyclomatic_complexity: float
    cognitive_complexity: float
    essential_complexity: float
    average_complexity: float
    category: ComplexityCategory
    nesting_depth: int  # Max nesting level
    branch_count: int  # Number of branches
    loop_count: int  # Number of loops
    decision_count: int  # if/else/switch cases


@dataclass
class ComplexityStats:
    """Statistical complexity metrics."""
    metric_name: str
    count: int
    mean: float
    median: float
    min_value: float
    max_value: float
    percentile_25: float
    percentile_75: float
    high_complexity_count: int  # Count above threshold (>15)


@dataclass
class ComplexityTrend:
    """Complexity trend for a symbol."""
    symbol_name: str
    previous_complexity: float
    current_complexity: float
    change: float
    direction: str  # increasing, stable, decreasing


@dataclass
class ComplexityReport:
    """Complexity analysis report."""
    status: str
    total_symbols: int
    average_cyclomatic: float
    average_cognitive: float
    average_essential: float
    simple_count: int
    moderate_count: int
    complex_count: int
    very_complex_count: int
    extremely_complex_count: int
    high_complexity_symbols: List[Tuple[str, float]] = field(default_factory=list)
    distribution: Dict[str, int] = field(default_factory=dict)
    refactoring_targets: List[Tuple[str, float]] = field(default_factory=list)


class ComplexityAnalyzer:
    """Analyzes code complexity across symbols."""

    def __init__(self):
        """Initialize analyzer."""
        self.metrics: Dict[str, ComplexityMetric] = {}
        self.historical_metrics: List[ComplexityReport] = []

    def analyze_symbol(self, symbol: Symbol, code_structure: Dict) -> ComplexityMetric:
        """Analyze complexity of a single symbol.

        Args:
            symbol: Symbol to analyze
            code_structure: Dict with code structure info (branches, loops, nesting, etc)

        Returns:
            ComplexityMetric for the symbol
        """
        # Extract structure info
        branch_count = code_structure.get("branches", 0)
        loop_count = code_structure.get("loops", 0)
        nesting_depth = code_structure.get("nesting_depth", 0)
        decision_count = code_structure.get("decisions", 0)

        # Cyclomatic complexity: 1 + branches + loops
        cyclomatic = 1 + branch_count + loop_count

        # Cognitive complexity: branches*nesting + loops*2
        # Accounts for nested complexity
        cognitive = (branch_count * (nesting_depth + 1)) + (loop_count * 2)

        # Essential complexity: cyclomatic - structured decisions
        # Measures non-structured code
        structured_decisions = min(decision_count, branch_count + loop_count)
        essential = max(1, cyclomatic - structured_decisions)

        # Average of the three
        average = (cyclomatic + cognitive + essential) / 3

        # Categorize
        if average <= 5:
            category = ComplexityCategory.SIMPLE
        elif average <= 15:
            category = ComplexityCategory.MODERATE
        elif average <= 30:
            category = ComplexityCategory.COMPLEX
        elif average <= 50:
            category = ComplexityCategory.VERY_COMPLEX
        else:
            category = ComplexityCategory.EXTREMELY_COMPLEX

        metric = ComplexityMetric(
            symbol=symbol,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            essential_complexity=essential,
            average_complexity=average,
            category=category,
            nesting_depth=nesting_depth,
            branch_count=branch_count,
            loop_count=loop_count,
            decision_count=decision_count,
        )

        self.metrics[symbol.full_qualified_name] = metric
        return metric

    def analyze(self, symbols: Dict[str, Symbol], code_structures: Dict[str, Dict]) -> Dict[str, ComplexityMetric]:
        """Analyze complexity for multiple symbols.

        Args:
            symbols: Dict of symbol name -> Symbol
            code_structures: Dict of symbol name -> code structure info

        Returns:
            Dict of symbol name -> ComplexityMetric
        """
        self.metrics = {}

        for name, symbol in symbols.items():
            structure = code_structures.get(name, {})
            self.analyze_symbol(symbol, structure)

        return self.metrics

    def get_high_complexity_symbols(self, threshold: float = 15, limit: int = 10) -> List[Tuple[str, float]]:
        """Get symbols with high complexity.

        Args:
            threshold: Complexity threshold
            limit: Max results

        Returns:
            List of (symbol_name, complexity_score) tuples
        """
        high = [(name, m.average_complexity) for name, m in self.metrics.items()
                if m.average_complexity > threshold]
        return sorted(high, key=lambda x: x[1], reverse=True)[:limit]

    def get_complexity_distribution(self) -> Dict[str, int]:
        """Get distribution of complexity categories.

        Returns:
            Dict mapping category -> count
        """
        distribution = {
            "simple": 0,
            "moderate": 0,
            "complex": 0,
            "very_complex": 0,
            "extremely_complex": 0,
        }

        for metric in self.metrics.values():
            category = metric.category.value
            if category in distribution:
                distribution[category] += 1

        return distribution

    def get_refactoring_targets(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get symbols that should be refactored (high complexity).

        Args:
            limit: Max results

        Returns:
            List of (symbol_name, refactoring_priority) tuples
        """
        targets = []

        for name, metric in self.metrics.items():
            if metric.average_complexity > 15:  # Refactoring threshold
                # Priority = complexity * (cognitive + nesting)
                priority = metric.average_complexity * (1 + metric.nesting_depth * 0.1)
                targets.append((name, priority))

        return sorted(targets, key=lambda x: x[1], reverse=True)[:limit]

    def get_complexity_stats(self) -> ComplexityStats:
        """Get statistical summary of complexity metrics.

        Returns:
            ComplexityStats with aggregated metrics
        """
        if not self.metrics:
            return ComplexityStats(
                metric_name="cyclomatic",
                count=0,
                mean=0.0,
                median=0.0,
                min_value=0.0,
                max_value=0.0,
                percentile_25=0.0,
                percentile_75=0.0,
                high_complexity_count=0,
            )

        complexities = sorted([m.average_complexity for m in self.metrics.values()])
        count = len(complexities)

        # Calculate percentiles
        p25_idx = max(0, count // 4)
        p75_idx = max(0, 3 * count // 4)

        high_count = sum(1 for c in complexities if c > 15)

        return ComplexityStats(
            metric_name="average_complexity",
            count=count,
            mean=sum(complexities) / count if count > 0 else 0.0,
            median=complexities[count // 2] if count > 0 else 0.0,
            min_value=min(complexities) if count > 0 else 0.0,
            max_value=max(complexities) if count > 0 else 0.0,
            percentile_25=complexities[p25_idx] if count > 0 else 0.0,
            percentile_75=complexities[p75_idx] if count > 0 else 0.0,
            high_complexity_count=high_count,
        )

    def compare_complexity(self, previous_metrics: Dict[str, ComplexityMetric]) -> List[ComplexityTrend]:
        """Compare current complexity with previous metrics.

        Args:
            previous_metrics: Previous metrics for comparison

        Returns:
            List of ComplexityTrend for changed symbols
        """
        trends = []

        for name, current_metric in self.metrics.items():
            if name in previous_metrics:
                previous = previous_metrics[name]
                change = current_metric.average_complexity - previous.average_complexity

                if change > 0.5:
                    direction = "increasing"
                elif change < -0.5:
                    direction = "decreasing"
                else:
                    direction = "stable"

                trends.append(ComplexityTrend(
                    symbol_name=name,
                    previous_complexity=previous.average_complexity,
                    current_complexity=current_metric.average_complexity,
                    change=change,
                    direction=direction,
                ))

        return trends

    def get_complexity_report(self) -> ComplexityReport:
        """Generate comprehensive complexity report.

        Returns:
            ComplexityReport with detailed metrics
        """
        if not self.metrics:
            return ComplexityReport(
                status="no_analysis",
                total_symbols=0,
                average_cyclomatic=0.0,
                average_cognitive=0.0,
                average_essential=0.0,
                simple_count=0,
                moderate_count=0,
                complex_count=0,
                very_complex_count=0,
                extremely_complex_count=0,
            )

        # Calculate averages
        avg_cyclomatic = sum(m.cyclomatic_complexity for m in self.metrics.values()) / len(self.metrics)
        avg_cognitive = sum(m.cognitive_complexity for m in self.metrics.values()) / len(self.metrics)
        avg_essential = sum(m.essential_complexity for m in self.metrics.values()) / len(self.metrics)

        # Count by category
        distribution = self.get_complexity_distribution()
        high_complexity = self.get_high_complexity_symbols(threshold=15, limit=5)
        refactoring_targets = self.get_refactoring_targets(limit=5)

        return ComplexityReport(
            status="analyzed",
            total_symbols=len(self.metrics),
            average_cyclomatic=avg_cyclomatic,
            average_cognitive=avg_cognitive,
            average_essential=avg_essential,
            simple_count=distribution.get("simple", 0),
            moderate_count=distribution.get("moderate", 0),
            complex_count=distribution.get("complex", 0),
            very_complex_count=distribution.get("very_complex", 0),
            extremely_complex_count=distribution.get("extremely_complex", 0),
            high_complexity_symbols=high_complexity,
            distribution=distribution,
            refactoring_targets=refactoring_targets,
        )

    def record_metrics(self, report: ComplexityReport) -> None:
        """Record metrics for trend tracking.

        Args:
            report: ComplexityReport to record
        """
        self.historical_metrics.append(report)
