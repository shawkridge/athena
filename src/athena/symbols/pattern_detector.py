"""Advanced Pattern Detector for code patterns and anti-patterns.

Provides:
- Design pattern detection
- Anti-pattern identification
- Pattern metrics and statistics
- Pattern-based recommendations
- Pattern evolution tracking
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .symbol_models import Symbol


class PatternType(str, Enum):
    """Types of code patterns."""

    SINGLETON = "singleton"
    FACTORY = "factory"
    OBSERVER = "observer"
    STRATEGY = "strategy"
    DECORATOR = "decorator"
    ADAPTER = "adapter"
    BUILDER = "builder"
    CHAIN_OF_RESPONSIBILITY = "chain_of_responsibility"


class AntiPatternType(str, Enum):
    """Types of anti-patterns (code smells)."""

    GOD_OBJECT = "god_object"
    LONG_METHOD = "long_method"
    DUPLICATE_CODE = "duplicate_code"
    LARGE_CLASS = "large_class"
    LONG_PARAMETER_LIST = "long_parameter_list"
    FEATURE_ENVY = "feature_envy"
    DATA_CLUMPS = "data_clumps"
    SWITCH_STATEMENTS = "switch_statements"
    PRIMITIVE_OBSESSION = "primitive_obsession"
    LAZY_CLASS = "lazy_class"


@dataclass
class Pattern:
    """Detected code pattern."""

    symbol_name: str
    pattern_type: PatternType
    confidence: float  # 0-1
    indicators: List[str]
    benefits: List[str]


@dataclass
class AntiPattern:
    """Detected anti-pattern."""

    symbol_name: str
    anti_pattern_type: AntiPatternType
    severity: str  # low, medium, high, critical
    severity_score: float  # 0-1
    indicators: List[str]
    remediation: List[str]


@dataclass
class PatternMetrics:
    """Metrics for patterns in a symbol."""

    symbol_name: str
    detected_patterns: List[Pattern]
    detected_anti_patterns: List[AntiPattern]
    pattern_score: float  # 0-1, how well patterns are used
    smell_score: float  # 0-1, severity of smells (0 is clean)
    design_quality: str  # excellent, good, fair, poor, critical


class PatternDetector:
    """Detects design patterns and anti-patterns in code."""

    def __init__(self):
        """Initialize detector."""
        self.detected_patterns: Dict[str, List[Pattern]] = {}
        self.detected_anti_patterns: Dict[str, List[AntiPattern]] = {}
        self.metrics: Dict[str, PatternMetrics] = {}

    def analyze_symbol(self, symbol: Symbol, metrics: Dict) -> PatternMetrics:
        """Analyze a symbol for patterns and anti-patterns.

        Args:
            symbol: Symbol to analyze
            metrics: Code metrics for the symbol

        Returns:
            PatternMetrics
        """
        patterns = self._detect_patterns(symbol, metrics)
        anti_patterns = self._detect_anti_patterns(symbol, metrics)

        # Calculate scores
        pattern_score = self._calculate_pattern_score(patterns)
        smell_score = self._calculate_smell_score(anti_patterns)
        design_quality = self._determine_design_quality(pattern_score, smell_score)

        metric = PatternMetrics(
            symbol_name=symbol.name,
            detected_patterns=patterns,
            detected_anti_patterns=anti_patterns,
            pattern_score=pattern_score,
            smell_score=smell_score,
            design_quality=design_quality,
        )

        self.metrics[symbol.full_qualified_name] = metric
        if patterns:
            self.detected_patterns[symbol.full_qualified_name] = patterns
        if anti_patterns:
            self.detected_anti_patterns[symbol.full_qualified_name] = anti_patterns

        return metric

    def _detect_patterns(self, symbol: Symbol, metrics: Dict) -> List[Pattern]:
        """Detect design patterns in symbol.

        Args:
            symbol: Symbol to analyze
            metrics: Code metrics

        Returns:
            List of detected patterns
        """
        patterns = []

        # Check for Singleton pattern
        if self._looks_like_singleton(symbol, metrics):
            patterns.append(
                Pattern(
                    symbol_name=symbol.name,
                    pattern_type=PatternType.SINGLETON,
                    confidence=0.7,
                    indicators=["private constructor", "static instance", "getInstance()"],
                    benefits=["single instance", "global access", "lazy initialization"],
                )
            )

        # Check for Factory pattern
        if self._looks_like_factory(symbol, metrics):
            patterns.append(
                Pattern(
                    symbol_name=symbol.name,
                    pattern_type=PatternType.FACTORY,
                    confidence=0.75,
                    indicators=["creation methods", "type parameters", "object instantiation"],
                    benefits=["loose coupling", "object creation abstraction", "flexibility"],
                )
            )

        # Check for Builder pattern
        if self._looks_like_builder(symbol, metrics):
            patterns.append(
                Pattern(
                    symbol_name=symbol.name,
                    pattern_type=PatternType.BUILDER,
                    confidence=0.8,
                    indicators=["fluent interface", "chained methods", "build()"],
                    benefits=["complex objects", "readable construction", "immutability"],
                )
            )

        return patterns

    def _detect_anti_patterns(self, symbol: Symbol, metrics: Dict) -> List[AntiPattern]:
        """Detect anti-patterns in symbol.

        Args:
            symbol: Symbol to analyze
            metrics: Code metrics

        Returns:
            List of detected anti-patterns
        """
        anti_patterns = []

        # Check for God Object
        if metrics.get("incoming_count", 0) > 20 or metrics.get("methods", 0) > 50:
            anti_patterns.append(
                AntiPattern(
                    symbol_name=symbol.name,
                    anti_pattern_type=AntiPatternType.GOD_OBJECT,
                    severity="high",
                    severity_score=0.8,
                    indicators=["too many responsibilities", "high coupling", "many methods"],
                    remediation=[
                        "break into smaller classes",
                        "single responsibility",
                        "extract methods",
                    ],
                )
            )

        # Check for Long Method
        if metrics.get("lines", 0) > 50:
            anti_patterns.append(
                AntiPattern(
                    symbol_name=symbol.name,
                    anti_pattern_type=AntiPatternType.LONG_METHOD,
                    severity="medium",
                    severity_score=0.6,
                    indicators=["method too long", "low cohesion", "multiple responsibilities"],
                    remediation=["extract methods", "reduce complexity", "improve readability"],
                )
            )

        # Check for Large Class
        if metrics.get("lines", 0) > 200:
            anti_patterns.append(
                AntiPattern(
                    symbol_name=symbol.name,
                    anti_pattern_type=AntiPatternType.LARGE_CLASS,
                    severity="medium",
                    severity_score=0.65,
                    indicators=["class too large", "many attributes", "many methods"],
                    remediation=["split class", "extract responsibilities", "refactor"],
                )
            )

        return anti_patterns

    def _looks_like_singleton(self, symbol: Symbol, metrics: Dict) -> bool:
        """Check if symbol looks like Singleton pattern."""
        code = symbol.code.lower() if symbol.code else ""
        return ("private" in code and "static" in code and "instance" in code) or (
            "getinstance" in code or "get_instance" in code
        )

    def _looks_like_factory(self, symbol: Symbol, metrics: Dict) -> bool:
        """Check if symbol looks like Factory pattern."""
        code = symbol.code.lower() if symbol.code else ""
        return ("create" in code or "make" in code) and "new" in code

    def _looks_like_builder(self, symbol: Symbol, metrics: Dict) -> bool:
        """Check if symbol looks like Builder pattern."""
        methods = metrics.get("methods", 0)
        # Handle both list and int types for methods
        method_count = len(methods) if isinstance(methods, list) else methods
        code = symbol.code.lower() if symbol.code else ""
        return ("build" in code or method_count > 3) and (
            "return self" in code or "return this" in code
        )

    def _calculate_pattern_score(self, patterns: List[Pattern]) -> float:
        """Calculate score based on detected patterns.

        Args:
            patterns: List of detected patterns

        Returns:
            Score 0-1
        """
        if not patterns:
            return 0.5

        avg_confidence = sum(p.confidence for p in patterns) / len(patterns)
        return min(1.0, 0.5 + (avg_confidence * 0.5))

    def _calculate_smell_score(self, anti_patterns: List[AntiPattern]) -> float:
        """Calculate smell score based on anti-patterns.

        Args:
            anti_patterns: List of detected anti-patterns

        Returns:
            Score 0-1 (0 = clean, 1 = smelly)
        """
        if not anti_patterns:
            return 0.0

        avg_severity = sum(ap.severity_score for ap in anti_patterns) / len(anti_patterns)
        return min(1.0, avg_severity)

    def _determine_design_quality(self, pattern_score: float, smell_score: float) -> str:
        """Determine overall design quality.

        Args:
            pattern_score: Pattern detection score (0-1, quality of patterns used)
            smell_score: Anti-pattern severity score (0-1, amount of code smell)

        Returns:
            Quality rating string
        """
        # Combined score: reward clean code + reward good patterns
        # Clean code (low smell_score) is worth 40%, good patterns worth 60%
        combined = (pattern_score * 0.6) + ((1.0 - smell_score) * 0.4)

        if combined >= 0.85:
            return "excellent"
        elif combined >= 0.7:
            return "good"
        elif combined >= 0.55:
            return "fair"
        elif combined >= 0.4:
            return "poor"
        else:
            return "critical"

    def get_pattern_summary(self) -> Dict:
        """Get summary of all detected patterns.

        Returns:
            Summary dict
        """
        all_patterns = []
        all_anti_patterns = []

        for patterns in self.detected_patterns.values():
            all_patterns.extend(patterns)

        for anti_patterns in self.detected_anti_patterns.values():
            all_anti_patterns.extend(anti_patterns)

        pattern_counts = {}
        for pattern in all_patterns:
            pattern_type = pattern.pattern_type.value
            pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1

        anti_pattern_counts = {}
        for anti_pattern in all_anti_patterns:
            ap_type = anti_pattern.anti_pattern_type.value
            anti_pattern_counts[ap_type] = anti_pattern_counts.get(ap_type, 0) + 1

        return {
            "total_patterns": len(all_patterns),
            "total_anti_patterns": len(all_anti_patterns),
            "pattern_distribution": pattern_counts,
            "anti_pattern_distribution": anti_pattern_counts,
            "symbols_with_patterns": len(self.detected_patterns),
            "symbols_with_smells": len(self.detected_anti_patterns),
        }

    def get_worst_smells(self, limit: int = 10) -> List[Tuple[str, AntiPattern]]:
        """Get symbols with worst code smells.

        Args:
            limit: Max results

        Returns:
            List of (symbol_name, anti_pattern) tuples
        """
        all_smells = []

        for symbol_name, anti_patterns in self.detected_anti_patterns.items():
            for anti_pattern in anti_patterns:
                all_smells.append((symbol_name, anti_pattern))

        return sorted(all_smells, key=lambda x: x[1].severity_score, reverse=True)[:limit]

    def get_best_patterns(self, limit: int = 10) -> List[Tuple[str, Pattern]]:
        """Get symbols with best design patterns.

        Args:
            limit: Max results

        Returns:
            List of (symbol_name, pattern) tuples
        """
        all_patterns = []

        for symbol_name, patterns in self.detected_patterns.items():
            for pattern in patterns:
                all_patterns.append((symbol_name, pattern))

        return sorted(all_patterns, key=lambda x: x[1].confidence, reverse=True)[:limit]

    def get_refactoring_recommendations(self) -> List[Dict]:
        """Get refactoring recommendations based on smells.

        Returns:
            List of recommendation dicts
        """
        recommendations = []
        worst_smells = self.get_worst_smells(5)

        for symbol_name, smell in worst_smells:
            recommendations.append(
                {
                    "symbol": symbol_name,
                    "issue": smell.anti_pattern_type.value,
                    "severity": smell.severity,
                    "remediation": smell.remediation,
                    "priority": "high" if smell.severity == "critical" else "medium",
                }
            )

        return recommendations
