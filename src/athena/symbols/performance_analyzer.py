"""Performance Pattern Analyzer for detecting code performance anti-patterns.

Provides:
- N+1 query detection
- Inefficient loop detection
- Memory leak pattern detection
- Blocking operation detection
- Missing cache opportunity detection
- Inefficient algorithm detection
- Resource leak detection
- Performance anti-pattern reporting
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from .symbol_models import Symbol, SymbolType


class PerformanceIssueType(str, Enum):
    """Types of performance issues."""

    N_PLUS_ONE = "n_plus_one"  # Database N+1 queries
    INEFFICIENT_LOOP = "inefficient_loop"  # Nested loops or repeated work
    MEMORY_LEAK = "memory_leak"  # Potential memory leak patterns
    BLOCKING_OPERATION = "blocking_operation"  # Blocking calls in async
    MISSING_CACHE = "missing_cache"  # Missing caching opportunity
    INEFFICIENT_ALGORITHM = "inefficient_algorithm"  # Inefficient algorithm
    RESOURCE_LEAK = "resource_leak"  # Resource not properly closed
    EXCESSIVE_ALLOCATION = "excessive_allocation"  # Excessive memory allocation


class PerformanceSeverity(str, Enum):
    """Severity levels for performance issues."""

    INFO = "info"  # Informational
    LOW = "low"  # Minor performance impact
    MEDIUM = "medium"  # Moderate performance impact
    HIGH = "high"  # Significant performance impact
    CRITICAL = "critical"  # Critical performance impact


@dataclass
class PerformanceIssue:
    """A detected performance issue."""

    symbol: Symbol
    issue_type: PerformanceIssueType
    severity: PerformanceSeverity
    line_number: int
    code_snippet: str
    message: str
    recommendation: str
    estimated_impact: float  # 0.0-1.0 scale


@dataclass
class PerformanceMetrics:
    """Performance metrics for analyzed code."""

    total_symbols: int
    symbols_with_issues: int
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    average_impact: float


class PerformanceAnalyzer:
    """Analyzes code for performance anti-patterns."""

    def __init__(self):
        """Initialize the performance analyzer."""
        self.issues: List[PerformanceIssue] = []
        self.metrics: Optional[PerformanceMetrics] = None

    def analyze_symbol(self, symbol: Symbol, code: str) -> List[PerformanceIssue]:
        """Analyze a symbol for performance issues.

        Args:
            symbol: Symbol to analyze
            code: Source code content

        Returns:
            List of detected performance issues
        """
        issues = []

        # Skip non-function/method symbols
        if symbol.symbol_type not in [
            SymbolType.FUNCTION,
            SymbolType.METHOD,
            SymbolType.ASYNC_FUNCTION,
        ]:
            return issues

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # N+1 query patterns
            n_plus_one_issues = self._check_n_plus_one(symbol, line, line_num)
            issues.extend(n_plus_one_issues)

            # Inefficient loop patterns
            loop_issues = self._check_inefficient_loops(symbol, line, line_num)
            issues.extend(loop_issues)

            # Memory leak patterns
            memory_issues = self._check_memory_leaks(symbol, line, line_num)
            issues.extend(memory_issues)

            # Blocking operations in async
            blocking_issues = self._check_blocking_operations(symbol, line, line_num)
            issues.extend(blocking_issues)

            # Missing cache opportunities
            cache_issues = self._check_missing_cache(symbol, line, line_num)
            issues.extend(cache_issues)

            # Inefficient algorithms
            algo_issues = self._check_inefficient_algorithms(symbol, line, line_num)
            issues.extend(algo_issues)

            # Resource leaks
            resource_issues = self._check_resource_leaks(symbol, line, line_num)
            issues.extend(resource_issues)

            # Excessive allocation
            alloc_issues = self._check_excessive_allocation(symbol, line, line_num)
            issues.extend(alloc_issues)

        self.issues.extend(issues)
        return issues

    def _check_n_plus_one(self, symbol: Symbol, line: str, line_num: int) -> List[PerformanceIssue]:
        """Check for N+1 query patterns."""
        issues = []

        patterns = [
            (r"for\s+\w+\s+in\s+\w+.*:\s*.*query\(", "Loop with query inside - potential N+1"),
            (r"\.query\(\).*for\s+\w+", "Query in loop detected - N+1 pattern"),
            (r"for.*\bselect\b.*\bfrom\b", "SQL query in loop - N+1 pattern"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.N_PLUS_ONE,
                        severity=PerformanceSeverity.HIGH,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Use batch queries or eager loading instead of querying in loops. Consider using JOIN or fetch strategies.",
                        estimated_impact=0.8,
                    )
                )

        return issues

    def _check_inefficient_loops(
        self, symbol: Symbol, line: str, line_num: int
    ) -> List[PerformanceIssue]:
        """Check for inefficient loop patterns."""
        issues = []

        patterns = [
            (r"for\s+\w+\s+in\s+\w+.*:\s*for\s+\w+\s+in", "Nested loops detected"),
            (r"for.*:\s*.*\+=.*\.append\(", "String concatenation in loop"),
            (r"while\s+True:", "Infinite loop pattern"),
            (r"for\s+\w+\s+in\s+range\(.*range", "Multiple nested range loops"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.INEFFICIENT_LOOP,
                        severity=PerformanceSeverity.MEDIUM,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Optimize loop structure. Consider using set operations, list comprehensions, or algorithmic improvements.",
                        estimated_impact=0.6,
                    )
                )

        return issues

    def _check_memory_leaks(
        self, symbol: Symbol, line: str, line_num: int
    ) -> List[PerformanceIssue]:
        """Check for memory leak patterns."""
        issues = []

        patterns = [
            (r"while.*True.*:\s*.*append\(", "Unbounded list growth in loop"),
            (r"def\s+\w+.*:\s*.*global\s+\w+", "Global mutable state - memory leak risk"),
            (r"self\.\w+\s*=\s*\[\].*while", "Growing list without bounds"),
            (r"cache\s*=\s*\{.*\}.*while\s+True", "Unbounded cache growth"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.MEMORY_LEAK,
                        severity=PerformanceSeverity.HIGH,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Add size limits or cleanup mechanisms. Use weak references for caches or implement LRU eviction.",
                        estimated_impact=0.7,
                    )
                )

        return issues

    def _check_blocking_operations(
        self, symbol: Symbol, line: str, line_num: int
    ) -> List[PerformanceIssue]:
        """Check for blocking operations in async code."""
        issues = []

        if "async def" not in symbol.signature:
            return issues

        patterns = [
            (r"time\.sleep\(", "Blocking sleep in async function"),
            (r"requests\.\w+\(", "Blocking HTTP request in async"),
            (r"\.read\(\)", "Blocking file read in async"),
            (r"\.write\(\)", "Blocking file write in async"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.BLOCKING_OPERATION,
                        severity=PerformanceSeverity.HIGH,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Use async alternatives: asyncio.sleep(), aiohttp, aiofiles instead of blocking calls.",
                        estimated_impact=0.8,
                    )
                )

        return issues

    def _check_missing_cache(
        self, symbol: Symbol, line: str, line_num: int
    ) -> List[PerformanceIssue]:
        """Check for missing cache opportunities."""
        issues = []

        patterns = [
            (r"expensive_function\(\)", "Expensive function called without caching"),
            (r"def\s+\w+.*:\s*return\s+.*\.join\(", "String joining without memoization"),
            (r"fibonacci\(", "Recursive algorithm without memoization"),
            (r"factorial\(", "Factorial calculation without caching"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.MISSING_CACHE,
                        severity=PerformanceSeverity.MEDIUM,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Use @lru_cache, @cache decorators or memoization pattern for expensive repeated computations.",
                        estimated_impact=0.5,
                    )
                )

        return issues

    def _check_inefficient_algorithms(
        self, symbol: Symbol, line: str, line_num: int
    ) -> List[PerformanceIssue]:
        """Check for inefficient algorithm patterns."""
        issues = []

        patterns = [
            (r"\.sort\(\).*\.sort\(\)", "Multiple sorts of same data"),
            (r"in\s+\w+.*in\s+\w+", "Multiple linear searches in list"),
            (r"list\(set\(", "Converting to set and back to list"),
            (r"\[.*for.*in.*for.*in.*\]", "Complex list comprehension - consider clarity"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.INEFFICIENT_ALGORITHM,
                        severity=PerformanceSeverity.MEDIUM,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Review algorithm complexity. Use appropriate data structures (set for O(1) lookup, heap for priority, etc).",
                        estimated_impact=0.5,
                    )
                )

        return issues

    def _check_resource_leaks(
        self, symbol: Symbol, line: str, line_num: int
    ) -> List[PerformanceIssue]:
        """Check for resource leak patterns."""
        issues = []

        patterns = [
            (r'open\(["\'].*["\'](?!.*with)', "File opened without context manager"),
            (r"socket\.socket\(\)(?!.*with)", "Socket created without context manager"),
            (r"\.connect\(\)(?!.*finally)", "Connection without finally clause"),
            (r"lock\s*=.*acquire\(\)(?!.*release)", "Lock acquired but not released"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.RESOURCE_LEAK,
                        severity=PerformanceSeverity.HIGH,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Use context managers (with statement) or try/finally blocks to ensure resources are properly released.",
                        estimated_impact=0.7,
                    )
                )

        return issues

    def _check_excessive_allocation(
        self, symbol: Symbol, line: str, line_num: int
    ) -> List[PerformanceIssue]:
        """Check for excessive memory allocation."""
        issues = []

        patterns = [
            (r"\[\s*\w+\s*for.*\]", "Large list comprehension - verify necessity"),
            (r"\{.*:.*for.*\}", "Large dict comprehension - verify necessity"),
            (r"bytearray\([0-9]{7,}", "Very large bytearray allocation"),
            (r"\*\s*[0-9]{6,}", "Large array/list multiplication"),
        ]

        for pattern, msg in patterns:
            if re.search(pattern, line):
                issues.append(
                    PerformanceIssue(
                        symbol=symbol,
                        issue_type=PerformanceIssueType.EXCESSIVE_ALLOCATION,
                        severity=PerformanceSeverity.LOW,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        message=msg,
                        recommendation="Consider streaming/iterating instead of allocating entire structures. Use generators for large datasets.",
                        estimated_impact=0.3,
                    )
                )

        return issues

    def analyze_all(self, symbols_with_code: List[Tuple[Symbol, str]]) -> List[PerformanceIssue]:
        """Analyze multiple symbols for performance issues.

        Args:
            symbols_with_code: List of (symbol, code) tuples

        Returns:
            List of all detected issues
        """
        self.issues = []

        for symbol, code in symbols_with_code:
            self.analyze_symbol(symbol, code)

        self._calculate_metrics(symbols_with_code)

        return self.issues

    def _calculate_metrics(self, symbols_with_code: List[Tuple[Symbol, str]]) -> None:
        """Calculate performance metrics."""
        symbols_with_issues = set()
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        info_count = 0
        total_impact = 0.0

        for issue in self.issues:
            symbols_with_issues.add(issue.symbol.name)
            total_impact += issue.estimated_impact

            if issue.severity == PerformanceSeverity.CRITICAL:
                critical_count += 1
            elif issue.severity == PerformanceSeverity.HIGH:
                high_count += 1
            elif issue.severity == PerformanceSeverity.MEDIUM:
                medium_count += 1
            elif issue.severity == PerformanceSeverity.LOW:
                low_count += 1
            elif issue.severity == PerformanceSeverity.INFO:
                info_count += 1

        average_impact = total_impact / len(self.issues) if self.issues else 0.0

        self.metrics = PerformanceMetrics(
            total_symbols=len(symbols_with_code),
            symbols_with_issues=len(symbols_with_issues),
            total_issues=len(self.issues),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            info_count=info_count,
            average_impact=average_impact,
        )

    def get_issues(self, severity: Optional[PerformanceSeverity] = None) -> List[PerformanceIssue]:
        """Get issues, optionally filtered by severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of issues
        """
        if severity:
            return [i for i in self.issues if i.severity == severity]
        return self.issues

    def get_issues_for_symbol(self, symbol: Symbol) -> List[PerformanceIssue]:
        """Get issues for a specific symbol.

        Args:
            symbol: Symbol to get issues for

        Returns:
            List of issues for the symbol
        """
        return [i for i in self.issues if i.symbol.name == symbol.name]

    def get_critical_issues(self) -> List[PerformanceIssue]:
        """Get all critical severity issues.

        Returns:
            List of critical issues
        """
        return self.get_issues(PerformanceSeverity.CRITICAL)

    def get_issues_by_type(self, issue_type: PerformanceIssueType) -> List[PerformanceIssue]:
        """Get issues of a specific type.

        Args:
            issue_type: Type of issue to filter by

        Returns:
            List of issues of that type
        """
        return [i for i in self.issues if i.issue_type == issue_type]

    def get_highest_impact_issues(self, limit: int = 10) -> List[PerformanceIssue]:
        """Get issues ranked by estimated impact.

        Args:
            limit: Maximum number of results

        Returns:
            List of highest impact issues
        """
        return sorted(self.issues, key=lambda x: x.estimated_impact, reverse=True)[:limit]

    def get_metrics(self) -> Optional[PerformanceMetrics]:
        """Get performance metrics.

        Returns:
            PerformanceMetrics or None
        """
        return self.metrics

    def get_performance_report(self) -> str:
        """Generate a human-readable performance report.

        Returns:
            Formatted report string
        """
        if not self.metrics:
            return "No performance analysis performed. Call analyze_all() first."

        report = "═" * 70 + "\n"
        report += "                  PERFORMANCE ANALYSIS REPORT\n"
        report += "═" * 70 + "\n\n"

        report += f"Total Symbols:              {self.metrics.total_symbols}\n"
        report += f"Symbols with Issues:        {self.metrics.symbols_with_issues}\n"
        report += f"Total Issues:               {self.metrics.total_issues}\n"
        report += f"Average Impact Score:       {self.metrics.average_impact:.2f}\n\n"

        report += "Severity Breakdown:\n"
        report += f"  Critical:  {self.metrics.critical_count}\n"
        report += f"  High:      {self.metrics.high_count}\n"
        report += f"  Medium:    {self.metrics.medium_count}\n"
        report += f"  Low:       {self.metrics.low_count}\n"
        report += f"  Info:      {self.metrics.info_count}\n\n"

        # Critical issues
        critical = self.get_critical_issues()
        if critical:
            report += "─" * 70 + "\n"
            report += "CRITICAL PERFORMANCE ISSUES:\n"
            report += "─" * 70 + "\n"
            for issue in critical[:5]:
                report += f"\n{issue.symbol.name} (Line {issue.line_number})\n"
                report += f"  Type: {issue.issue_type.value}\n"
                report += f"  Issue: {issue.message}\n"
                report += f"  Impact: {issue.estimated_impact:.1%}\n"

        # Highest impact
        highest = self.get_highest_impact_issues(limit=5)
        if highest:
            report += "\n" + "─" * 70 + "\n"
            report += "HIGHEST IMPACT ISSUES:\n"
            report += "─" * 70 + "\n"
            for issue in highest:
                report += (
                    f"{issue.symbol.name}: {issue.message} (Impact: {issue.estimated_impact:.1%})\n"
                )

        return report

    def suggest_optimization(self, issue: PerformanceIssue) -> str:
        """Suggest optimization for a performance issue.

        Args:
            issue: PerformanceIssue to optimize

        Returns:
            Detailed optimization suggestion
        """
        suggestion = f"Optimize {issue.issue_type.value} in {issue.symbol.name}:\n"
        suggestion += f"\nProblem: {issue.message}\n"
        suggestion += f"Location: Line {issue.line_number}\n"
        suggestion += f"Code: {issue.code_snippet}\n"
        suggestion += f"Estimated Impact: {issue.estimated_impact:.1%}\n"
        suggestion += f"\nRecommendation:\n{issue.recommendation}\n"

        # Add specific optimization based on type
        if issue.issue_type == PerformanceIssueType.N_PLUS_ONE:
            suggestion += "\nSpecific Optimization:\n"
            suggestion += "1. Use eager loading (prefetch_related, select_related in Django ORM)\n"
            suggestion += "2. Use batch operations or bulk updates\n"
            suggestion += "3. Combine queries with JOINs instead of separate queries\n"

        elif issue.issue_type == PerformanceIssueType.INEFFICIENT_LOOP:
            suggestion += "\nSpecific Optimization:\n"
            suggestion += "1. Use list comprehensions instead of nested loops where possible\n"
            suggestion += "2. Consider set operations for membership tests\n"
            suggestion += "3. Use generators for memory efficiency\n"

        elif issue.issue_type == PerformanceIssueType.MISSING_CACHE:
            suggestion += "\nSpecific Optimization:\n"
            suggestion += "1. Add @functools.lru_cache decorator for pure functions\n"
            suggestion += "2. Use @cache for Python 3.9+\n"
            suggestion += "3. Implement memoization pattern for recursive functions\n"

        return suggestion
