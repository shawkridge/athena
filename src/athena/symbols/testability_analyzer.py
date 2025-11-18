"""Testability Analyzer for assessing code testability.

Provides:
- Test-friendliness scoring
- Dependency injection readiness
- Mockability assessment
- Test coverage potential analysis
- Testability recommendations
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import re

from .symbol_models import Symbol, SymbolType


class TestabilityRating(str, Enum):
    """Testability ratings."""

    HIGHLY_TESTABLE = "highly_testable"  # Easy to test
    TESTABLE = "testable"  # Can be tested with some setup
    MODERATELY_TESTABLE = "moderately_testable"  # Requires mocking/setup
    DIFFICULT = "difficult"  # Hard to test
    UNTESTABLE = "untestable"  # Nearly impossible to test


class TestabilityIssue(str, Enum):
    """Types of testability issues."""

    GLOBAL_STATE = "global_state"  # Uses global variables
    HIDDEN_DEPENDENCIES = "hidden_dependencies"  # Hard to inject dependencies
    SIDE_EFFECTS = "side_effects"  # Has side effects
    STATIC_CALLS = "static_calls"  # Calls static methods
    TIGHT_COUPLING = "tight_coupling"  # Tightly coupled code
    RANDOM_CALLS = "random_calls"  # Uses random functions
    TIME_DEPENDENCIES = "time_dependencies"  # Time-dependent code
    FILE_IO = "file_io"  # Direct file operations
    NETWORK_IO = "network_io"  # Network operations
    INSUFFICIENT_ASSERTIONS = "insufficient_assertions"  # Few return values


@dataclass
class TestabilityIssueDetail:
    """Details about a testability issue."""

    symbol: Symbol
    issue_type: TestabilityIssue
    severity: str  # low, medium, high, critical
    line_number: int
    code_snippet: str
    message: str
    suggestion: str


@dataclass
class TestabilityScore:
    """Testability score for a symbol."""

    symbol: Symbol
    overall_score: float  # 0-100
    rating: TestabilityRating

    # Component scores
    dependency_injection_score: float  # 0-100
    side_effect_score: float  # 0-100
    coupling_score: float  # 0-100
    external_dependency_score: float  # 0-100

    issues: List[TestabilityIssueDetail]
    test_coverage_potential: float  # 0-1, how much of code can be tested
    suggestions: List[str]


@dataclass
class TestabilityMetrics:
    """Testability metrics for analyzed code."""

    total_symbols: int
    highly_testable_count: int
    testable_count: int
    moderately_testable_count: int
    difficult_count: int
    untestable_count: int
    average_testability_score: float
    average_coverage_potential: float
    total_issues: int
    critical_issues: int


class TestabilityAnalyzer:
    """Analyzes code testability across multiple dimensions."""

    def __init__(self):
        """Initialize analyzer with default thresholds."""
        self.scores: List[TestabilityScore] = []
        self.metrics: Optional[TestabilityMetrics] = None

    def analyze_symbol(self, symbol: Symbol) -> Optional[TestabilityScore]:
        """Analyze testability of a single symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            TestabilityScore or None if not applicable
        """
        if symbol.symbol_type not in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.CLASS]:
            return None

        code = symbol.code if symbol.code else ""

        # Calculate component scores
        di_score = self._calculate_dependency_injection_score(symbol, code)
        side_effect_score = self._calculate_side_effect_score(symbol, code)
        coupling_score = self._calculate_coupling_score(symbol, code)
        ext_dep_score = self._calculate_external_dependency_score(symbol, code)

        # Weighted average for overall score
        overall_score = (
            di_score * 0.30
            + side_effect_score * 0.30
            + coupling_score * 0.20
            + ext_dep_score * 0.20
        )

        # Determine rating
        rating = self._get_rating(overall_score)

        # Detect issues
        issues = self._detect_issues(symbol, code)

        # Calculate test coverage potential
        coverage_potential = self._calculate_coverage_potential(symbol, code, issues)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            symbol, di_score, side_effect_score, coupling_score, ext_dep_score, issues
        )

        score = TestabilityScore(
            symbol=symbol,
            overall_score=overall_score,
            rating=rating,
            dependency_injection_score=di_score,
            side_effect_score=side_effect_score,
            coupling_score=coupling_score,
            external_dependency_score=ext_dep_score,
            issues=issues,
            test_coverage_potential=coverage_potential,
            suggestions=suggestions,
        )

        self.scores.append(score)
        return score

    def analyze_all(self, symbols: List[Symbol]) -> List[TestabilityScore]:
        """Analyze testability of multiple symbols.

        Args:
            symbols: List of symbols to analyze

        Returns:
            List of TestabilityScores
        """
        self.scores = []
        for symbol in symbols:
            score = self.analyze_symbol(symbol)
            if score:
                pass  # Already appended in analyze_symbol
        return self.scores

    def _calculate_dependency_injection_score(self, symbol: Symbol, code: str) -> float:
        """Score how well suited for dependency injection."""
        if not code:
            return 50.0

        score = 100.0

        # Penalize for direct instantiation
        instantiations = len(re.findall(r"\b\w+\s*=\s*\w+\(", code))
        if instantiations > 3:
            score -= 20

        # Penalize for accessing class attributes
        attr_access = len(re.findall(r"[A-Z]\w*\.\w+", code))
        if attr_access > 5:
            score -= 15

        # Reward for parameters
        if symbol.signature and "(" in symbol.signature:
            param_count = symbol.signature.count(",") + 1
            if param_count >= 2:
                score += 10

        return max(0, min(100, score))

    def _calculate_side_effect_score(self, symbol: Symbol, code: str) -> float:
        """Score how free of side effects code is."""
        if not code:
            return 50.0

        score = 100.0

        # Check for global variable modification
        globals_modified = len(re.findall(r"global\s+\w+|^\s*\w+\s*=", code, re.MULTILINE))
        if globals_modified > 0:
            score -= 30

        # Check for print statements
        print_count = len(re.findall(r"\bprint\(", code))
        if print_count > 0:
            score -= 10

        # Check for mutations (list.append, dict.update, etc.)
        mutations = len(re.findall(r"\.(append|extend|update|pop|clear|remove)\(", code))
        if mutations > 2:
            score -= 15

        # Check for logging
        if "log." in code or "logger." in code:
            score -= 5

        return max(0, min(100, score))

    def _calculate_coupling_score(self, symbol: Symbol, code: str) -> float:
        """Score how loosely coupled code is."""
        if not code:
            return 50.0

        score = 100.0

        # Check for hardcoded strings/values
        hardcoded = len(re.findall(r'["\'][\w\s]{10,}["\']', code))
        if hardcoded > 3:
            score -= 15

        # Check for long method calls (likely tight coupling)
        long_chains = len(re.findall(r"(\.\w+){3,}", code))
        if long_chains > 2:
            score -= 20

        # Check for deeply nested conditionals (coupling indicator)
        nesting_depth = 0
        max_nesting = 0
        for char in code:
            if char in "{[(":
                nesting_depth += 1
                max_nesting = max(max_nesting, nesting_depth)
            elif char in "}])":
                nesting_depth = max(0, nesting_depth - 1)

        if max_nesting > 4:
            score -= 15

        return max(0, min(100, score))

    def _calculate_external_dependency_score(self, symbol: Symbol, code: str) -> float:
        """Score how many external dependencies code has."""
        if not code:
            return 50.0

        score = 100.0

        # File I/O
        file_io = len(re.findall(r"open\(|close\(|read\(|write\(", code))
        if file_io > 0:
            score -= 25

        # Network I/O
        network = len(re.findall(r"requests\.|socket\.|urllib\.|http\.", code))
        if network > 0:
            score -= 25

        # Database operations
        db_ops = len(re.findall(r"query\(|execute\(|\.save\(|\.delete\(", code))
        if db_ops > 0:
            score -= 20

        # Random/time functions
        random_time = len(re.findall(r"random\.|time\.|datetime\.|uuid\.", code))
        if random_time > 1:
            score -= 15

        return max(0, min(100, score))

    def _detect_issues(self, symbol: Symbol, code: str) -> List[TestabilityIssueDetail]:
        """Detect testability issues in code."""
        issues = []

        # Check for global state
        if "global " in code:
            issues.append(
                TestabilityIssueDetail(
                    symbol=symbol,
                    issue_type=TestabilityIssue.GLOBAL_STATE,
                    severity="critical",
                    line_number=symbol.line_start,
                    code_snippet=code[:80],
                    message="Uses global state",
                    suggestion="Refactor to use dependency injection instead of global variables",
                )
            )

        # Check for hidden dependencies
        instantiations = len(re.findall(r"\b\w+\s*=\s*\w+\(", code))
        if instantiations > 3:
            issues.append(
                TestabilityIssueDetail(
                    symbol=symbol,
                    issue_type=TestabilityIssue.HIDDEN_DEPENDENCIES,
                    severity="high",
                    line_number=symbol.line_start,
                    code_snippet=code[:80],
                    message=f"Creates {instantiations} objects internally",
                    suggestion="Use dependency injection to make dependencies explicit",
                )
            )

        # Check for side effects
        if "print(" in code:
            issues.append(
                TestabilityIssueDetail(
                    symbol=symbol,
                    issue_type=TestabilityIssue.SIDE_EFFECTS,
                    severity="medium",
                    line_number=symbol.line_start,
                    code_snippet=code[:80],
                    message="Contains print statements",
                    suggestion="Use logging instead of print or inject output handler",
                )
            )

        # Check for static calls
        static_calls = len(re.findall(r"[A-Z]\w*\.\w+\(", code))
        if static_calls > 3:
            issues.append(
                TestabilityIssueDetail(
                    symbol=symbol,
                    issue_type=TestabilityIssue.STATIC_CALLS,
                    severity="high",
                    line_number=symbol.line_start,
                    code_snippet=code[:80],
                    message=f"Makes {static_calls} static method calls",
                    suggestion="Extract static calls to dependencies that can be mocked",
                )
            )

        # Check for file I/O
        if "open(" in code or ".read(" in code:
            issues.append(
                TestabilityIssueDetail(
                    symbol=symbol,
                    issue_type=TestabilityIssue.FILE_IO,
                    severity="high",
                    line_number=symbol.line_start,
                    code_snippet=code[:80],
                    message="Performs file I/O directly",
                    suggestion="Inject file operations or use test fixtures",
                )
            )

        # Check for network I/O
        if any(x in code for x in ["requests.", "socket.", "http.", "urllib."]):
            issues.append(
                TestabilityIssueDetail(
                    symbol=symbol,
                    issue_type=TestabilityIssue.NETWORK_IO,
                    severity="critical",
                    line_number=symbol.line_start,
                    code_snippet=code[:80],
                    message="Makes network calls directly",
                    suggestion="Extract network calls into injectable service",
                )
            )

        # Check for random/time dependencies
        if any(x in code for x in ["random.", "time.", "datetime."]):
            issues.append(
                TestabilityIssueDetail(
                    symbol=symbol,
                    issue_type=TestabilityIssue.TIME_DEPENDENCIES,
                    severity="medium",
                    line_number=symbol.line_start,
                    code_snippet=code[:80],
                    message="Uses random or time functions",
                    suggestion="Inject time/random providers for test control",
                )
            )

        return issues

    def _calculate_coverage_potential(
        self, symbol: Symbol, code: str, issues: List[TestabilityIssueDetail]
    ) -> float:
        """Calculate potential test coverage for symbol."""
        if not code:
            return 0.5

        potential = 1.0

        # Each critical issue reduces potential by 15%
        critical_count = len([i for i in issues if i.severity == "critical"])
        potential -= critical_count * 0.15

        # Each high issue reduces by 10%
        high_count = len([i for i in issues if i.severity == "high"])
        potential -= high_count * 0.10

        # Complexity reduces coverage potential
        branches = len(re.findall(r"\bif\b|\belse\b|\belif\b|\bfor\b|\bwhile\b", code))
        if branches > 5:
            potential -= 0.10

        return max(0.0, min(1.0, potential))

    def _generate_suggestions(
        self,
        symbol: Symbol,
        di_score: float,
        side_effect_score: float,
        coupling_score: float,
        ext_dep_score: float,
        issues: List[TestabilityIssueDetail],
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if di_score < 60:
            suggestions.append(
                "Use dependency injection to make dependencies explicit and mockable"
            )

        if side_effect_score < 60:
            suggestions.append("Reduce side effects by extracting I/O and state mutations")

        if coupling_score < 60:
            suggestions.append("Reduce coupling by using interfaces and dependency injection")

        if ext_dep_score < 60:
            suggestions.append("Extract external dependencies into injectable services")

        if len(issues) > 2:
            suggestions.append(f"Address {len(issues)} testability issues to improve test coverage")

        return suggestions

    def _get_rating(self, score: float) -> TestabilityRating:
        """Convert score to rating."""
        if score >= 80:
            return TestabilityRating.HIGHLY_TESTABLE
        elif score >= 65:
            return TestabilityRating.TESTABLE
        elif score >= 50:
            return TestabilityRating.MODERATELY_TESTABLE
        elif score >= 30:
            return TestabilityRating.DIFFICULT
        else:
            return TestabilityRating.UNTESTABLE

    def get_scores_by_rating(self, rating: TestabilityRating) -> List[TestabilityScore]:
        """Get all scores with specific rating."""
        return [s for s in self.scores if s.rating == rating]

    def get_symbols_with_issues(self) -> List[TestabilityScore]:
        """Get symbols with testability issues."""
        return [s for s in self.scores if len(s.issues) > 0]

    def get_lowest_testability(self, limit: int = 10) -> List[TestabilityScore]:
        """Get least testable symbols."""
        sorted_scores = sorted(self.scores, key=lambda s: s.overall_score)
        return sorted_scores[:limit]

    def get_testability_report(self) -> Dict:
        """Generate testability report."""
        if not self.scores:
            return {"status": "no_analysis", "message": "No symbols analyzed yet"}

        self._calculate_metrics()

        return {
            "status": "analyzed",
            "total_symbols": len(self.scores),
            "average_testability_score": self.metrics.average_testability_score,
            "average_coverage_potential": self.metrics.average_coverage_potential,
            "distribution": {
                "highly_testable": self.metrics.highly_testable_count,
                "testable": self.metrics.testable_count,
                "moderately_testable": self.metrics.moderately_testable_count,
                "difficult": self.metrics.difficult_count,
                "untestable": self.metrics.untestable_count,
            },
            "issues_summary": {
                "total_issues": self.metrics.total_issues,
                "critical_issues": self.metrics.critical_issues,
            },
            "least_testable": [
                {
                    "symbol": s.symbol.name,
                    "score": s.overall_score,
                    "rating": s.rating.value,
                    "issues": len(s.issues),
                    "coverage_potential": s.test_coverage_potential,
                }
                for s in self.get_lowest_testability(5)
            ],
        }

    def _calculate_metrics(self):
        """Calculate overall metrics."""
        if not self.scores:
            self.metrics = TestabilityMetrics(
                total_symbols=0,
                highly_testable_count=0,
                testable_count=0,
                moderately_testable_count=0,
                difficult_count=0,
                untestable_count=0,
                average_testability_score=0.0,
                average_coverage_potential=0.0,
                total_issues=0,
                critical_issues=0,
            )
            return

        avg_score = sum(s.overall_score for s in self.scores) / len(self.scores)
        avg_coverage = sum(s.test_coverage_potential for s in self.scores) / len(self.scores)

        highly_testable = len(
            [s for s in self.scores if s.rating == TestabilityRating.HIGHLY_TESTABLE]
        )
        testable = len([s for s in self.scores if s.rating == TestabilityRating.TESTABLE])
        moderately = len(
            [s for s in self.scores if s.rating == TestabilityRating.MODERATELY_TESTABLE]
        )
        difficult = len([s for s in self.scores if s.rating == TestabilityRating.DIFFICULT])
        untestable = len([s for s in self.scores if s.rating == TestabilityRating.UNTESTABLE])

        total_issues = sum(len(s.issues) for s in self.scores)
        critical_issues = sum(
            len([i for i in s.issues if i.severity == "critical"]) for s in self.scores
        )

        self.metrics = TestabilityMetrics(
            total_symbols=len(self.scores),
            highly_testable_count=highly_testable,
            testable_count=testable,
            moderately_testable_count=moderately,
            difficult_count=difficult,
            untestable_count=untestable,
            average_testability_score=avg_score,
            average_coverage_potential=avg_coverage,
            total_issues=total_issues,
            critical_issues=critical_issues,
        )
