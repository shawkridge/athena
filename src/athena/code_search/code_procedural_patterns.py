"""Procedural pattern extraction and learning from code structure.

This module identifies and learns reusable code patterns from code analysis,
storing them in procedural memory for future pattern matching and suggestions.
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from src.athena.code_search.symbol_extractor import Symbol, SymbolType
from src.athena.code_search.code_graph_integration import (
    CodeGraphBuilder,
    CodeRelationType,
)

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of code patterns."""

    DESIGN_PATTERN = "design_pattern"  # Factory, Observer, etc.
    ARCHITECTURAL = "architectural"  # MVC, Layered, etc.
    CODING_IDIOM = "coding_idiom"  # Pythonic idioms, etc.
    ANTI_PATTERN = "anti_pattern"  # Duplicate code, etc.
    REFACTORING = "refactoring"  # Common refactorings
    CONVENTION = "convention"  # Naming, structure conventions
    OPTIMIZATION = "optimization"  # Performance patterns


class PatternCategory(Enum):
    """Categories of patterns."""

    STRUCTURAL = "structural"  # Class hierarchies, compositions
    BEHAVIORAL = "behavioral"  # Object interactions, responsibilities
    CREATIONAL = "creational"  # Object creation mechanisms
    FUNCTIONAL = "functional"  # Functional programming patterns
    CONCURRENCY = "concurrency"  # Threading, async patterns
    ERROR_HANDLING = "error_handling"  # Exception handling patterns
    TESTING = "testing"  # Test patterns
    DOCUMENTATION = "documentation"  # Doc and comment patterns


@dataclass
class CodePattern:
    """Represents a discovered code pattern."""

    name: str
    pattern_type: PatternType
    category: PatternCategory
    description: Optional[str] = None
    confidence: float = 1.0  # 0-1, how confident pattern detection is
    indicators: List[str] = field(default_factory=list)  # Indicators of pattern
    entities: List[str] = field(default_factory=list)  # Entities involved
    relationships: List[str] = field(default_factory=list)  # Rel types involved
    frequency: int = 1  # How often observed
    anti_patterns: List[str] = field(default_factory=list)  # Known issues
    improvements: List[str] = field(default_factory=list)  # Suggested improvements
    examples: Dict[str, str] = field(default_factory=dict)  # Example code snippets
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "pattern_type": self.pattern_type.value,
            "category": self.category.value,
            "description": self.description,
            "confidence": self.confidence,
            "indicators": self.indicators,
            "entities": self.entities,
            "relationships": self.relationships,
            "frequency": self.frequency,
            "anti_patterns": self.anti_patterns,
            "improvements": self.improvements,
            "examples": self.examples,
            "metadata": self.metadata,
        }


class PatternDetector:
    """Detects patterns in code structure."""

    def __init__(self):
        """Initialize pattern detector."""
        self.detected_patterns: Dict[str, CodePattern] = {}

    def detect_singleton_pattern(
        self, symbols: List[Symbol], graph: CodeGraphBuilder
    ) -> Optional[CodePattern]:
        """Detect singleton pattern usage."""
        pattern = CodePattern(
            name="Singleton",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.CREATIONAL,
            description="Ensures a class has single instance with global access",
            confidence=0.0,
        )

        # Look for private __init__ and static get_instance method
        for symbol in symbols:
            if symbol.type == SymbolType.CLASS:
                # Check for static methods and private init
                class_methods = [s for s in symbols if s.type == SymbolType.METHOD]
                has_private_init = any(
                    s.signature
                    and "__init__" in s.signature
                    and "private" in str(s.signature).lower()
                    for s in class_methods
                )
                has_instance_method = any(
                    "instance" in m.name.lower() and "get" in m.name.lower() for m in class_methods
                )

                if has_private_init and has_instance_method:
                    pattern.confidence = 0.85
                    pattern.entities = [symbol.name]
                    pattern.indicators = ["private_init", "static_instance_method"]

        return pattern if pattern.confidence > 0.5 else None

    def detect_factory_pattern(
        self, symbols: List[Symbol], graph: CodeGraphBuilder
    ) -> Optional[CodePattern]:
        """Detect factory pattern usage."""
        pattern = CodePattern(
            name="Factory",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.CREATIONAL,
            description="Creates objects without specifying exact classes",
            confidence=0.0,
        )

        # Look for factory method creating objects
        for symbol in symbols:
            if symbol.type == SymbolType.FUNCTION:
                if any(keyword in symbol.name.lower() for keyword in ["create", "make", "build"]):
                    # Check if returns objects
                    pattern.confidence = 0.7
                    pattern.entities = [symbol.name]
                    pattern.indicators = ["factory_method_name"]

        return pattern if pattern.confidence > 0.5 else None

    def detect_observer_pattern(
        self, symbols: List[Symbol], graph: CodeGraphBuilder
    ) -> Optional[CodePattern]:
        """Detect observer pattern usage."""
        pattern = CodePattern(
            name="Observer",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.BEHAVIORAL,
            description="Defines one-to-many dependency between objects",
            confidence=0.0,
        )

        # Look for notify/subscribe methods
        method_names = [s.name for s in symbols if s.type == SymbolType.METHOD]
        has_notify = any(
            "notify" in name.lower() or "trigger" in name.lower() for name in method_names
        )
        has_subscribe = any(
            "subscribe" in name.lower() or "register" in name.lower() for name in method_names
        )

        if has_notify and has_subscribe:
            pattern.confidence = 0.8
            pattern.indicators = ["notify_method", "subscribe_method"]

        return pattern if pattern.confidence > 0.5 else None

    def detect_decorator_pattern(
        self, symbols: List[Symbol], graph: CodeGraphBuilder
    ) -> Optional[CodePattern]:
        """Detect decorator pattern usage."""
        pattern = CodePattern(
            name="Decorator",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.STRUCTURAL,
            description="Attaches additional responsibilities to objects dynamically",
            confidence=0.0,
        )

        # Look for decorator symbols
        decorators = [s for s in symbols if s.type == SymbolType.DECORATOR]
        if decorators:
            pattern.confidence = 0.9
            pattern.entities = [d.name for d in decorators]
            pattern.indicators = ["decorator_usage"]

        return pattern if pattern.confidence > 0.5 else None

    def detect_dry_violation(
        self, symbols: List[Symbol], code_content: str
    ) -> Optional[CodePattern]:
        """Detect DRY (Don't Repeat Yourself) violations."""
        pattern = CodePattern(
            name="DRY Violation",
            pattern_type=PatternType.ANTI_PATTERN,
            category=PatternCategory.STRUCTURAL,
            description="Duplicate code that should be extracted",
            confidence=0.0,
        )

        # Simple heuristic: look for similar method names or content
        method_names = [s.name for s in symbols if s.type == SymbolType.METHOD]
        similar_names = {}

        for name in method_names:
            base = name.rstrip("0123456789_")
            if base not in similar_names:
                similar_names[base] = []
            similar_names[base].append(name)

        # If multiple similar methods, likely DRY violation
        for base, names in similar_names.items():
            if len(names) > 1:
                pattern.confidence = 0.6
                pattern.entities = names
                pattern.indicators = ["similar_method_names"]
                pattern.improvements = ["Extract common functionality into base method"]

        return pattern if pattern.confidence > 0.5 else None

    def detect_high_coupling(self, graph: CodeGraphBuilder) -> Optional[CodePattern]:
        """Detect high coupling between modules."""
        pattern = CodePattern(
            name="High Coupling",
            pattern_type=PatternType.ANTI_PATTERN,
            category=PatternCategory.STRUCTURAL,
            description="Excessive dependencies between modules",
            confidence=0.0,
        )

        # Check for entities with many dependencies
        for entity_name in graph.entities.keys():
            dependencies = graph.get_related_entities(entity_name, CodeRelationType.DEPENDS_ON)
            if len(dependencies) > 5:
                pattern.confidence = 0.75
                pattern.entities.append(entity_name)
                pattern.indicators.append(f"{entity_name}_high_deps")

        return pattern if pattern.confidence > 0.5 else None

    def detect_insufficient_documentation(self, symbols: List[Symbol]) -> Optional[CodePattern]:
        """Detect lack of documentation."""
        pattern = CodePattern(
            name="Insufficient Documentation",
            pattern_type=PatternType.ANTI_PATTERN,
            category=PatternCategory.DOCUMENTATION,
            description="Public functions/classes without documentation",
            confidence=0.0,
        )

        # Look for public items without docstrings
        public_items = [
            s
            for s in symbols
            if s.type in [SymbolType.FUNCTION, SymbolType.CLASS, SymbolType.METHOD]
            and not s.name.startswith("_")
        ]

        undocumented = [s for s in public_items if not s.docstring]
        if undocumented and len(undocumented) / max(len(public_items), 1) > 0.3:
            pattern.confidence = 0.7
            pattern.entities = [s.name for s in undocumented[:5]]  # First 5
            pattern.indicators = ["missing_docstrings"]
            pattern.improvements = ["Add docstrings to all public functions/classes"]

        return pattern if pattern.confidence > 0.5 else None


class PatternAnalyzer:
    """Analyzes and learns patterns for procedural memory."""

    def __init__(self, detector: Optional[PatternDetector] = None):
        """Initialize analyzer."""
        self.detector = detector or PatternDetector()
        self.learned_patterns: Dict[str, CodePattern] = {}
        self.pattern_frequency: Dict[str, int] = {}

    def analyze_code(
        self,
        symbols: List[Symbol],
        graph: CodeGraphBuilder,
        code_content: str = "",
    ) -> List[CodePattern]:
        """Analyze code for patterns."""
        patterns = []

        # Run pattern detectors
        design_patterns = [
            self.detector.detect_singleton_pattern(symbols, graph),
            self.detector.detect_factory_pattern(symbols, graph),
            self.detector.detect_observer_pattern(symbols, graph),
            self.detector.detect_decorator_pattern(symbols, graph),
        ]

        anti_patterns = [
            self.detector.detect_dry_violation(symbols, code_content),
            self.detector.detect_high_coupling(graph),
            self.detector.detect_insufficient_documentation(symbols),
        ]

        # Filter and collect patterns
        all_patterns = design_patterns + anti_patterns
        for pattern in all_patterns:
            if pattern and pattern.confidence > 0.5:
                patterns.append(pattern)
                self._update_pattern_frequency(pattern)

        return patterns

    def learn_pattern(self, pattern: CodePattern):
        """Learn a pattern for future use."""
        key = f"{pattern.pattern_type.value}:{pattern.name}"

        if key not in self.learned_patterns:
            self.learned_patterns[key] = pattern
            self.pattern_frequency[key] = 1
        else:
            # Update frequency and merge metadata
            self.pattern_frequency[key] += 1
            self.learned_patterns[key].frequency += 1

        logger.info(f"Learned pattern: {pattern.name} (frequency: {self.pattern_frequency[key]})")

    def get_learned_patterns(self) -> List[CodePattern]:
        """Get all learned patterns."""
        return list(self.learned_patterns.values())

    def get_patterns_by_type(self, pattern_type: PatternType) -> List[CodePattern]:
        """Get patterns by type."""
        return [p for p in self.learned_patterns.values() if p.pattern_type == pattern_type]

    def get_patterns_by_category(self, category: PatternCategory) -> List[CodePattern]:
        """Get patterns by category."""
        return [p for p in self.learned_patterns.values() if p.category == category]

    def suggest_improvements(self, patterns: List[CodePattern]) -> Dict[str, List[str]]:
        """Suggest improvements based on detected patterns."""
        improvements = {}

        for pattern in patterns:
            if pattern.improvements:
                if pattern.name not in improvements:
                    improvements[pattern.name] = []
                improvements[pattern.name].extend(pattern.improvements)

        return improvements

    def calculate_code_quality_score(self, patterns: List[CodePattern]) -> float:
        """Calculate code quality based on patterns."""
        if not patterns:
            return 1.0

        anti_patterns = [p for p in patterns if p.pattern_type == PatternType.ANTI_PATTERN]
        design_patterns = [p for p in patterns if p.pattern_type == PatternType.DESIGN_PATTERN]

        # Quality score: 1.0 - (anti_patterns * 0.1) + (design_patterns * 0.05)
        score = 1.0
        score -= len(anti_patterns) * 0.15  # Penalize anti-patterns
        score += len(design_patterns) * 0.05  # Reward design patterns
        score = max(0.0, min(1.0, score))  # Clamp 0-1

        return score

    def generate_pattern_report(self, patterns: List[CodePattern]) -> str:
        """Generate human-readable pattern report."""
        if not patterns:
            return "No patterns detected."

        report = f"Detected {len(patterns)} patterns:\n"

        # Group by type
        by_type = {}
        for pattern in patterns:
            type_name = pattern.pattern_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(pattern)

        for type_name, type_patterns in by_type.items():
            report += f"\n{type_name.upper()}:\n"
            for pattern in type_patterns:
                report += f"  - {pattern.name} (confidence: {pattern.confidence:.0%})\n"
                if pattern.description:
                    report += f"    {pattern.description}\n"
                if pattern.improvements:
                    report += f"    Improvements: {', '.join(pattern.improvements)}\n"

        quality = self.calculate_code_quality_score(patterns)
        report += f"\nOverall Quality Score: {quality:.0%}\n"

        return report

    def _update_pattern_frequency(self, pattern: CodePattern):
        """Update pattern frequency tracking."""
        key = f"{pattern.pattern_type.value}:{pattern.name}"
        self.pattern_frequency[key] = self.pattern_frequency.get(key, 0) + 1


class ProceduralMemoryIntegration:
    """Integration between code patterns and procedural memory."""

    def __init__(self):
        """Initialize integration."""
        self.analyzer = PatternAnalyzer()
        self.pattern_memory: Dict[str, CodePattern] = {}

    def record_code_patterns(
        self,
        symbols: List[Symbol],
        graph: CodeGraphBuilder,
        code_content: str = "",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record code patterns for procedural memory."""
        patterns = self.analyzer.analyze_code(symbols, graph, code_content)

        # Learn each pattern
        for pattern in patterns:
            self.analyzer.learn_pattern(pattern)
            key = f"{pattern.pattern_type.value}:{pattern.name}"
            self.pattern_memory[key] = pattern

        return {
            "patterns_detected": len(patterns),
            "patterns": [p.to_dict() for p in patterns],
            "quality_score": self.analyzer.calculate_code_quality_score(patterns),
            "improvements": self.analyzer.suggest_improvements(patterns),
            "session_id": session_id,
        }

    def get_pattern_insights(self) -> Dict[str, Any]:
        """Get insights from learned patterns."""
        all_patterns = self.analyzer.get_learned_patterns()

        return {
            "total_patterns_learned": len(all_patterns),
            "by_type": {
                "design_patterns": len(
                    self.analyzer.get_patterns_by_type(PatternType.DESIGN_PATTERN)
                ),
                "anti_patterns": len(self.analyzer.get_patterns_by_type(PatternType.ANTI_PATTERN)),
                "idioms": len(self.analyzer.get_patterns_by_type(PatternType.CODING_IDIOM)),
            },
            "by_category": {
                cat.value: len(self.analyzer.get_patterns_by_category(cat))
                for cat in PatternCategory
            },
            "most_common": sorted(
                self.analyzer.pattern_frequency.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }

    def suggest_refactorings(self) -> List[Dict[str, Any]]:
        """Suggest refactorings based on learned patterns."""
        refactoring_patterns = self.analyzer.get_patterns_by_type(PatternType.ANTI_PATTERN)

        suggestions = []
        for pattern in refactoring_patterns:
            suggestions.append(
                {
                    "pattern": pattern.name,
                    "affected_entities": pattern.entities,
                    "improvements": pattern.improvements,
                    "priority": "high" if pattern.confidence > 0.8 else "medium",
                }
            )

        return suggestions
