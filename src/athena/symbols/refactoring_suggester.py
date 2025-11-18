"""Refactoring Suggester for actionable refactoring recommendations.

Provides:
- Concrete refactoring steps based on debt items
- Effort and impact estimation per refactoring
- Refactoring roadmap prioritization
- Risk assessment and dependencies
- Before/after metric projections
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .symbol_models import Symbol
from .technical_debt_analyzer import (
    DebtItem,
    DebtCategory,
    DebtSeverity,
)


class RefactoringType(str, Enum):
    """Types of refactoring actions."""

    EXTRACT_METHOD = "extract_method"  # Break down large functions
    EXTRACT_CLASS = "extract_class"  # Split responsibility
    RENAME = "rename"  # Improve naming clarity
    SIMPLIFY_LOGIC = "simplify_logic"  # Reduce complexity
    ADD_TESTS = "add_tests"  # Improve test coverage
    ADD_DOCUMENTATION = "add_documentation"  # Improve docs
    REMOVE_DUPLICATION = "remove_duplication"  # DRY principle
    REDUCE_COUPLING = "reduce_coupling"  # Loose coupling
    IMPROVE_DEPENDENCY_INJECTION = "improve_dependency_injection"  # Better testability
    FIX_SECURITY_ISSUE = "fix_security_issue"  # Security fixes
    OPTIMIZE_PERFORMANCE = "optimize_performance"  # Performance optimization
    REFACTOR_FOR_TESTING = "refactor_for_testing"  # Improve testability


class RefactoringImpact(str, Enum):
    """Impact level of refactoring."""

    MINIMAL = "minimal"  # Low risk, isolated change
    LOCAL = "local"  # Affects single function/class
    MODERATE = "moderate"  # Affects related components
    SIGNIFICANT = "significant"  # Affects multiple modules
    MAJOR = "major"  # Architectural change


@dataclass
class RefactoringStep:
    """Single refactoring step."""

    step_number: int
    description: str
    refactoring_type: RefactoringType
    detailed_instructions: str
    effort_hours: float
    estimated_impact: float  # 0-1, improvement to metrics
    risk_level: str  # low, medium, high
    dependencies: List[int] = field(default_factory=list)  # Step numbers this depends on


@dataclass
class RefactoringSuggestion:
    """Complete refactoring suggestion for a symbol."""

    symbol: Symbol
    debt_item: DebtItem
    refactoring_type: RefactoringType
    title: str
    description: str
    steps: List[RefactoringStep]
    total_effort: float  # Hours
    total_impact: float  # 0-1
    impact_category: RefactoringImpact
    priority_score: float  # 0-100, higher = more important
    estimated_risk: str  # low, medium, high

    # Before/after projections
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    related_issues: List[str] = field(default_factory=list)


@dataclass
class RefactoringRoadmap:
    """Prioritized refactoring plan for multiple symbols."""

    suggestions: List[RefactoringSuggestion]
    total_effort: float  # Hours
    total_impact: float  # 0-1
    estimated_timeline: str  # e.g., "4 weeks", "2 sprints"
    critical_path: List[RefactoringSuggestion] = field(default_factory=list)


class RefactoringSuggester:
    """Generates concrete refactoring suggestions from technical debt."""

    def __init__(self):
        """Initialize suggester."""
        self.suggestions: List[RefactoringSuggestion] = []
        self.roadmap: Optional[RefactoringRoadmap] = None

    def suggest_from_debt(self, debt_item: DebtItem) -> Optional[RefactoringSuggestion]:
        """Generate refactoring suggestion from debt item.

        Args:
            debt_item: Technical debt item to address

        Returns:
            RefactoringSuggestion or None
        """
        # Map debt category to refactoring type
        refactoring_type = self._map_debt_to_refactoring(debt_item.category)
        if not refactoring_type:
            return None

        # Generate steps based on category and severity
        steps = self._generate_steps(debt_item, refactoring_type)

        # Calculate metrics
        total_effort = sum(s.effort_hours for s in steps)
        total_impact = min(1.0, sum(s.estimated_impact for s in steps) / max(1, len(steps)))

        # Determine impact category
        if total_effort < 4:
            impact_category = RefactoringImpact.MINIMAL
        elif total_effort < 8:
            impact_category = RefactoringImpact.LOCAL
        elif total_effort < 16:
            impact_category = RefactoringImpact.MODERATE
        elif total_effort < 32:
            impact_category = RefactoringImpact.SIGNIFICANT
        else:
            impact_category = RefactoringImpact.MAJOR

        # Calculate priority score
        severity_weight = {
            DebtSeverity.CRITICAL: 40,
            DebtSeverity.HIGH: 30,
            DebtSeverity.MEDIUM: 20,
            DebtSeverity.LOW: 10,
            DebtSeverity.INFO: 5,
        }
        severity_score = severity_weight.get(debt_item.severity, 0)
        roi_score = (total_impact / max(0.1, total_effort)) * 20
        priority_score = severity_score + roi_score

        # Estimate risk level
        risk_level = self._estimate_risk_level(debt_item.severity, len(steps))

        # Generate before/after metrics
        before_metrics = self._generate_before_metrics(debt_item)
        after_metrics = self._generate_after_metrics(debt_item, total_impact)

        suggestion = RefactoringSuggestion(
            symbol=debt_item.symbol,
            debt_item=debt_item,
            refactoring_type=refactoring_type,
            title=f"{refactoring_type.value}: {debt_item.title}",
            description=debt_item.description,
            steps=steps,
            total_effort=total_effort,
            total_impact=total_impact,
            impact_category=impact_category,
            priority_score=priority_score,
            estimated_risk=risk_level,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
        )

        self.suggestions.append(suggestion)
        return suggestion

    def suggest_all(self, debt_items: List[DebtItem]) -> List[RefactoringSuggestion]:
        """Generate refactoring suggestions for multiple debt items.

        Args:
            debt_items: List of technical debt items

        Returns:
            List of RefactoringSuggestions
        """
        self.suggestions = []
        for item in debt_items:
            suggestion = self.suggest_from_debt(item)
            if suggestion:
                pass  # Already appended
        return self.suggestions

    def _map_debt_to_refactoring(self, category: DebtCategory) -> Optional[RefactoringType]:
        """Map debt category to refactoring type."""
        mapping = {
            DebtCategory.SECURITY: RefactoringType.FIX_SECURITY_ISSUE,
            DebtCategory.PERFORMANCE: RefactoringType.OPTIMIZE_PERFORMANCE,
            DebtCategory.QUALITY: RefactoringType.SIMPLIFY_LOGIC,
            DebtCategory.TESTING: RefactoringType.REFACTOR_FOR_TESTING,
            DebtCategory.DOCUMENTATION: RefactoringType.ADD_DOCUMENTATION,
            DebtCategory.MAINTAINABILITY: RefactoringType.EXTRACT_METHOD,
        }
        return mapping.get(category)

    def _generate_steps(
        self, debt_item: DebtItem, refactoring_type: RefactoringType
    ) -> List[RefactoringStep]:
        """Generate concrete refactoring steps."""
        steps = []

        if refactoring_type == RefactoringType.EXTRACT_METHOD:
            steps.extend(
                [
                    RefactoringStep(
                        step_number=1,
                        description="Identify cohesive code blocks",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Review the function and mark sections that perform a single task",
                        effort_hours=1.0,
                        estimated_impact=0.2,
                        risk_level="low",
                    ),
                    RefactoringStep(
                        step_number=2,
                        description="Extract first method",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Create new method with extracted code, verify it works",
                        effort_hours=1.5,
                        estimated_impact=0.3,
                        risk_level="medium",
                        dependencies=[1],
                    ),
                    RefactoringStep(
                        step_number=3,
                        description="Add unit tests",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Write tests for extracted method covering happy path and edge cases",
                        effort_hours=2.0,
                        estimated_impact=0.3,
                        risk_level="low",
                        dependencies=[2],
                    ),
                ]
            )

        elif refactoring_type == RefactoringType.SIMPLIFY_LOGIC:
            steps.extend(
                [
                    RefactoringStep(
                        step_number=1,
                        description="Analyze complex logic",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Document the current logic flow and identify simplification opportunities",
                        effort_hours=1.0,
                        estimated_impact=0.2,
                        risk_level="low",
                    ),
                    RefactoringStep(
                        step_number=2,
                        description="Apply simplification patterns",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Remove redundant conditions, merge branches, apply design patterns",
                        effort_hours=2.0,
                        estimated_impact=0.4,
                        risk_level="medium",
                        dependencies=[1],
                    ),
                    RefactoringStep(
                        step_number=3,
                        description="Verify behavior unchanged",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Run existing tests, add new tests for edge cases",
                        effort_hours=1.5,
                        estimated_impact=0.2,
                        risk_level="low",
                        dependencies=[2],
                    ),
                ]
            )

        elif refactoring_type == RefactoringType.ADD_TESTS:
            steps.extend(
                [
                    RefactoringStep(
                        step_number=1,
                        description="Analyze code paths",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Map all code paths and branch conditions",
                        effort_hours=1.0,
                        estimated_impact=0.2,
                        risk_level="low",
                    ),
                    RefactoringStep(
                        step_number=2,
                        description="Write unit tests",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Add tests for happy path, edge cases, error conditions",
                        effort_hours=3.0,
                        estimated_impact=0.4,
                        risk_level="low",
                        dependencies=[1],
                    ),
                    RefactoringStep(
                        step_number=3,
                        description="Achieve target coverage",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Run coverage tool and add missing tests",
                        effort_hours=2.0,
                        estimated_impact=0.3,
                        risk_level="low",
                        dependencies=[2],
                    ),
                ]
            )

        elif refactoring_type == RefactoringType.ADD_DOCUMENTATION:
            steps.extend(
                [
                    RefactoringStep(
                        step_number=1,
                        description="Document purpose",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Add docstring explaining what the function does",
                        effort_hours=0.5,
                        estimated_impact=0.2,
                        risk_level="low",
                    ),
                    RefactoringStep(
                        step_number=2,
                        description="Document parameters",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Document all parameters with types and descriptions",
                        effort_hours=0.5,
                        estimated_impact=0.2,
                        risk_level="low",
                        dependencies=[1],
                    ),
                    RefactoringStep(
                        step_number=3,
                        description="Document return value",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Document return type and value semantics",
                        effort_hours=0.5,
                        estimated_impact=0.2,
                        risk_level="low",
                        dependencies=[2],
                    ),
                    RefactoringStep(
                        step_number=4,
                        description="Add examples",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Add usage examples in docstring",
                        effort_hours=1.0,
                        estimated_impact=0.2,
                        risk_level="low",
                        dependencies=[3],
                    ),
                ]
            )

        elif refactoring_type == RefactoringType.FIX_SECURITY_ISSUE:
            steps.extend(
                [
                    RefactoringStep(
                        step_number=1,
                        description="Understand vulnerability",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Document the security issue and attack vector",
                        effort_hours=1.0,
                        estimated_impact=0.2,
                        risk_level="low",
                    ),
                    RefactoringStep(
                        step_number=2,
                        description="Apply security fix",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Implement the security patch or use secure library",
                        effort_hours=2.0,
                        estimated_impact=0.6,
                        risk_level="medium",
                        dependencies=[1],
                    ),
                    RefactoringStep(
                        step_number=3,
                        description="Add security tests",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Write tests that would fail with vulnerable code",
                        effort_hours=1.5,
                        estimated_impact=0.2,
                        risk_level="low",
                        dependencies=[2],
                    ),
                ]
            )

        elif refactoring_type == RefactoringType.OPTIMIZE_PERFORMANCE:
            steps.extend(
                [
                    RefactoringStep(
                        step_number=1,
                        description="Profile code",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Run profiler to identify hotspots and bottlenecks",
                        effort_hours=1.5,
                        estimated_impact=0.1,
                        risk_level="low",
                    ),
                    RefactoringStep(
                        step_number=2,
                        description="Apply optimization",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Implement algorithmic improvement or caching strategy",
                        effort_hours=3.0,
                        estimated_impact=0.5,
                        risk_level="medium",
                        dependencies=[1],
                    ),
                    RefactoringStep(
                        step_number=3,
                        description="Verify improvement",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Re-profile and measure performance gain vs baseline",
                        effort_hours=1.0,
                        estimated_impact=0.2,
                        risk_level="low",
                        dependencies=[2],
                    ),
                ]
            )

        elif refactoring_type == RefactoringType.REFACTOR_FOR_TESTING:
            steps.extend(
                [
                    RefactoringStep(
                        step_number=1,
                        description="Identify testability barriers",
                        refactoring_type=refactoring_type,
                        detailed_instructions="List global state, hard-coded dependencies, side effects",
                        effort_hours=1.0,
                        estimated_impact=0.2,
                        risk_level="low",
                    ),
                    RefactoringStep(
                        step_number=2,
                        description="Introduce dependency injection",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Convert hard-coded dependencies to parameters",
                        effort_hours=2.5,
                        estimated_impact=0.4,
                        risk_level="medium",
                        dependencies=[1],
                    ),
                    RefactoringStep(
                        step_number=3,
                        description="Remove side effects",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Extract I/O and mutation to separate methods",
                        effort_hours=2.0,
                        estimated_impact=0.3,
                        risk_level="medium",
                        dependencies=[2],
                    ),
                    RefactoringStep(
                        step_number=4,
                        description="Write comprehensive tests",
                        refactoring_type=refactoring_type,
                        detailed_instructions="Add unit tests leveraging new test-friendly structure",
                        effort_hours=2.0,
                        estimated_impact=0.3,
                        risk_level="low",
                        dependencies=[3],
                    ),
                ]
            )

        else:
            # Default steps for other refactoring types
            steps.append(
                RefactoringStep(
                    step_number=1,
                    description="Plan refactoring",
                    refactoring_type=refactoring_type,
                    detailed_instructions="Document the refactoring approach and acceptance criteria",
                    effort_hours=1.0,
                    estimated_impact=0.2,
                    risk_level="low",
                )
            )
            steps.append(
                RefactoringStep(
                    step_number=2,
                    description="Execute refactoring",
                    refactoring_type=refactoring_type,
                    detailed_instructions="Apply the refactoring changes",
                    effort_hours=2.0,
                    estimated_impact=0.5,
                    risk_level="medium",
                    dependencies=[1],
                )
            )
            steps.append(
                RefactoringStep(
                    step_number=3,
                    description="Verify quality",
                    refactoring_type=refactoring_type,
                    detailed_instructions="Run tests, linters, and manual review",
                    effort_hours=1.0,
                    estimated_impact=0.3,
                    risk_level="low",
                    dependencies=[2],
                )
            )

        return steps

    def _estimate_risk_level(self, severity: DebtSeverity, num_steps: int) -> str:
        """Estimate risk level of refactoring."""
        if severity == DebtSeverity.CRITICAL:
            return "high"
        elif severity == DebtSeverity.HIGH and num_steps > 4:
            return "high"
        elif severity == DebtSeverity.MEDIUM and num_steps > 5:
            return "medium"
        else:
            return "low"

    def _generate_before_metrics(self, debt_item: DebtItem) -> Dict[str, float]:
        """Generate estimated before metrics."""
        return {
            "debt_score": 50.0,
            "complexity": 15.0,
            "test_coverage": 60.0,
            "maintainability": 40.0,
        }

    def _generate_after_metrics(self, debt_item: DebtItem, impact: float) -> Dict[str, float]:
        """Generate estimated after metrics."""
        improvement_factor = impact * 100
        return {
            "debt_score": max(10.0, 50.0 - improvement_factor),
            "complexity": max(5.0, 15.0 - (improvement_factor * 0.3)),
            "test_coverage": min(100.0, 60.0 + (improvement_factor * 0.4)),
            "maintainability": min(100.0, 40.0 + improvement_factor),
        }

    def get_suggestions_by_priority(self, limit: int = 10) -> List[RefactoringSuggestion]:
        """Get suggestions sorted by priority."""
        sorted_suggestions = sorted(self.suggestions, key=lambda s: s.priority_score, reverse=True)
        return sorted_suggestions[:limit]

    def get_critical_path_suggestions(self) -> List[RefactoringSuggestion]:
        """Get critical path refactorings (blocking others)."""
        # Critical path items are high effort, high impact, high severity
        critical = []
        for suggestion in self.suggestions:
            if (
                suggestion.debt_item.severity in [DebtSeverity.CRITICAL, DebtSeverity.HIGH]
                and suggestion.total_effort > 8.0
                and suggestion.total_impact > 0.5
            ):
                critical.append(suggestion)
        return sorted(critical, key=lambda s: s.total_effort, reverse=True)

    def generate_roadmap(
        self, suggestions: Optional[List[RefactoringSuggestion]] = None
    ) -> RefactoringRoadmap:
        """Generate prioritized refactoring roadmap.

        Args:
            suggestions: List of suggestions to include (default: all)

        Returns:
            RefactoringRoadmap with prioritized plan
        """
        if suggestions is None:
            suggestions = self.suggestions

        # Sort by priority
        sorted_suggestions = sorted(suggestions, key=lambda s: s.priority_score, reverse=True)

        # Calculate totals
        total_effort = sum(s.total_effort for s in sorted_suggestions)
        total_impact = min(
            1.0, sum(s.total_impact for s in sorted_suggestions) / max(1, len(sorted_suggestions))
        )

        # Estimate timeline (assuming 40 hours/week development)
        weeks = total_effort / 40.0
        if weeks < 1:
            timeline = f"{int(weeks * 5)} days"
        elif weeks < 4:
            timeline = f"{int(weeks)} week{'s' if weeks > 1 else ''}"
        else:
            timeline = f"{int(weeks / 4)} sprint{'s' if weeks > 4 else ''}"

        # Get critical path
        critical_path = self.get_critical_path_suggestions()

        roadmap = RefactoringRoadmap(
            suggestions=sorted_suggestions,
            total_effort=total_effort,
            total_impact=total_impact,
            estimated_timeline=timeline,
            critical_path=critical_path,
        )

        self.roadmap = roadmap
        return roadmap

    def get_refactoring_report(self) -> Dict:
        """Generate comprehensive refactoring report."""
        if not self.suggestions:
            return {"status": "no_suggestions", "message": "No refactoring suggestions available"}

        roadmap = self.roadmap or self.generate_roadmap()

        return {
            "status": "ready",
            "total_suggestions": len(self.suggestions),
            "total_effort_hours": roadmap.total_effort,
            "estimated_impact": roadmap.total_impact,
            "estimated_timeline": roadmap.estimated_timeline,
            "critical_path_count": len(roadmap.critical_path),
            "high_priority": [
                {
                    "symbol": s.symbol.name,
                    "refactoring_type": s.refactoring_type.value,
                    "priority_score": s.priority_score,
                    "effort_hours": s.total_effort,
                    "estimated_impact": s.total_impact,
                    "risk_level": s.estimated_risk,
                }
                for s in roadmap.suggestions[:5]
            ],
            "critical_path": [
                {
                    "symbol": s.symbol.name,
                    "effort_hours": s.total_effort,
                    "impact": s.total_impact,
                    "risk": s.estimated_risk,
                }
                for s in roadmap.critical_path
            ],
        }
