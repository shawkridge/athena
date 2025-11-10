"""Specialized review agents for domain-specific code and design review."""

import logging
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReviewIssue:
    """A review issue found by a reviewer."""
    issue_id: str
    severity: IssueSeverity
    title: str
    description: str
    location: Optional[str] = None  # File:line for code issues
    suggestion: Optional[str] = None
    example: Optional[str] = None


@dataclass
class ReviewResult:
    """Result of a review."""
    reviewer_name: str
    issues: List[ReviewIssue]
    summary: str
    score: float  # 0.0-1.0
    recommendations: List[str]


class ReviewAgent(ABC):
    """Base class for specialized review agents."""

    def __init__(self, name: str, domain: str):
        """Initialize review agent.

        Args:
            name: Name of the agent
            domain: Domain the agent reviews (style, security, architecture, etc.)
        """
        self.name = name
        self.domain = domain

    @abstractmethod
    async def review(self, content: str, context: Dict[str, Any] = None) -> ReviewResult:
        """Review content in the agent's domain.

        Args:
            content: Content to review (code, design, etc.)
            context: Additional context for review

        Returns:
            ReviewResult with issues and recommendations
        """
        pass

    def _create_issue(
        self,
        severity: IssueSeverity,
        title: str,
        description: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> ReviewIssue:
        """Helper to create a review issue."""
        return ReviewIssue(
            issue_id=f"{self.name}_{len(title)}",
            severity=severity,
            title=title,
            description=description,
            location=location,
            suggestion=suggestion,
        )


class StyleReviewAgent(ReviewAgent):
    """Reviews code style, formatting, and naming conventions."""

    def __init__(self):
        super().__init__("style-reviewer", "style")

    async def review(self, content: str, context: Dict[str, Any] = None) -> ReviewResult:
        """Review code style and formatting."""
        issues = []

        # Check naming conventions
        if "def my_var" in content or "def MY_VAR" in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.MEDIUM,
                    "Inconsistent naming convention",
                    "Variable names should use snake_case in Python",
                    suggestion="Use snake_case for all variables",
                )
            )

        # Check line length
        for i, line in enumerate(content.split("\n"), 1):
            if len(line) > 100:
                issues.append(
                    self._create_issue(
                        IssueSeverity.LOW,
                        f"Line too long (line {i})",
                        f"Line exceeds 100 characters ({len(line)} chars)",
                        location=f"line {i}",
                        suggestion="Break line or shorten variable names",
                    )
                )

        # Check for missing docstrings
        if "def " in content and '"""' not in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.MEDIUM,
                    "Missing docstrings",
                    "Functions should have docstrings",
                    suggestion='Add docstrings describing function purpose',
                )
            )

        # Check spacing
        if "def(" in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.LOW,
                    "Spacing issue",
                    "Missing space between 'def' and '('",
                    suggestion="Use 'def function(' instead of 'def('",
                )
            )

        # Calculate score
        score = max(0, 1.0 - (len(issues) * 0.1))

        recommendations = [
            "Use consistent naming conventions",
            "Keep lines under 100 characters",
            "Add docstrings to all functions",
            "Follow PEP 8 style guide",
        ]

        return ReviewResult(
            reviewer_name=self.name,
            issues=issues,
            summary=f"Found {len(issues)} style issues",
            score=score,
            recommendations=recommendations,
        )


class SecurityReviewAgent(ReviewAgent):
    """Reviews code for security vulnerabilities and best practices."""

    def __init__(self):
        super().__init__("security-reviewer", "security")

    async def review(self, content: str, context: Dict[str, Any] = None) -> ReviewResult:
        """Review code for security issues."""
        issues = []

        # Check for common security issues
        security_patterns = {
            "eval(": ("Use of eval()", "eval() can execute arbitrary code", IssueSeverity.CRITICAL),
            "exec(": ("Use of exec()", "exec() can execute arbitrary code", IssueSeverity.CRITICAL),
            "pickle": ("Use of pickle", "Pickle is unsafe with untrusted data", IssueSeverity.HIGH),
            "TODO: validate": ("Missing validation", "User input must be validated", IssueSeverity.HIGH),
            "password": ("Hardcoded credential", "Credentials should not be in code", IssueSeverity.CRITICAL),
            "sql_query = f": ("SQL injection risk", "Use parameterized queries", IssueSeverity.CRITICAL),
        }

        for pattern, (title, desc, severity) in security_patterns.items():
            if pattern in content.lower():
                issues.append(
                    self._create_issue(
                        severity,
                        title,
                        desc,
                        suggestion="See OWASP guidelines",
                    )
                )

        # Check for error handling
        if "try:" in content and "except Exception:" in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.MEDIUM,
                    "Broad exception handling",
                    "Catching all exceptions can hide errors",
                    suggestion="Catch specific exception types",
                )
            )

        # Calculate score
        critical = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
        score = max(0, 1.0 - (critical * 0.5 + len(issues) * 0.1))

        recommendations = [
            "Never use eval() or exec()",
            "Use parameterized queries for SQL",
            "Validate all user input",
            "Never hardcode credentials",
            "Use specific exception types",
        ]

        return ReviewResult(
            reviewer_name=self.name,
            issues=issues,
            summary=f"Found {len(issues)} security issues ({critical} critical)",
            score=score,
            recommendations=recommendations,
        )


class ArchitectureReviewAgent(ReviewAgent):
    """Reviews code architecture, design patterns, and structure."""

    def __init__(self):
        super().__init__("architecture-reviewer", "architecture")

    async def review(self, content: str, context: Dict[str, Any] = None) -> ReviewResult:
        """Review code architecture and design."""
        issues = []

        # Check for large functions
        lines = content.split("\n")
        func_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("def "):
                func_start = i
            if func_start is not None and i - func_start > 50:
                issues.append(
                    self._create_issue(
                        IssueSeverity.MEDIUM,
                        f"Large function (lines {func_start}-{i})",
                        "Function is too large and should be split",
                        location=f"line {func_start}",
                        suggestion="Break function into smaller, focused functions",
                    )
                )
                func_start = None

        # Check for missing abstraction
        if "hardcoded" in content.lower() or "magic number" in content.lower():
            issues.append(
                self._create_issue(
                    IssueSeverity.MEDIUM,
                    "Magic numbers/hardcoded values",
                    "Values should be extracted to named constants",
                    suggestion="Define constants at module level",
                )
            )

        # Check for dependency issues
        if "import *" in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.HIGH,
                    "Wildcard import",
                    "Wildcard imports pollute namespace and hide dependencies",
                    suggestion="Import only needed symbols",
                )
            )

        # Calculate score
        score = max(0, 1.0 - (len(issues) * 0.15))

        recommendations = [
            "Keep functions focused and small (<50 lines)",
            "Extract magic numbers to named constants",
            "Use dependency injection",
            "Avoid circular dependencies",
            "Follow single responsibility principle",
        ]

        return ReviewResult(
            reviewer_name=self.name,
            issues=issues,
            summary=f"Found {len(issues)} architecture issues",
            score=score,
            recommendations=recommendations,
        )


class PerformanceReviewAgent(ReviewAgent):
    """Reviews code for performance bottlenecks and optimization opportunities."""

    def __init__(self):
        super().__init__("performance-reviewer", "performance")

    async def review(self, content: str, context: Dict[str, Any] = None) -> ReviewResult:
        """Review code for performance issues."""
        issues = []

        # Check for common performance anti-patterns
        if "for " in content and "database" in content.lower():
            issues.append(
                self._create_issue(
                    IssueSeverity.HIGH,
                    "Database query in loop",
                    "Querying database inside loop causes N+1 queries",
                    suggestion="Use batch queries or eager loading",
                )
            )

        if ".append(" in content and "list(" not in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.LOW,
                    "List operations in loop",
                    "Repeated list operations can be slow",
                    suggestion="Use list comprehensions or pre-allocate",
                )
            )

        # Check for blocking operations
        if "time.sleep" in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.MEDIUM,
                    "Blocking sleep in code",
                    "time.sleep() blocks execution",
                    suggestion="Use async sleep or timers for delays",
                )
            )

        # Check for string concatenation in loop
        if "+" in content and "for " in content and '"' in content:
            issues.append(
                self._create_issue(
                    IssueSeverity.MEDIUM,
                    "String concatenation in loop",
                    "Repeated string concatenation is inefficient",
                    suggestion="Use str.join() or StringIO",
                )
            )

        # Calculate score
        score = max(0, 1.0 - (len(issues) * 0.2))

        recommendations = [
            "Avoid N+1 database queries",
            "Batch operations when possible",
            "Use appropriate data structures",
            "Profile before optimizing",
            "Consider async for I/O operations",
        ]

        return ReviewResult(
            reviewer_name=self.name,
            issues=issues,
            summary=f"Found {len(issues)} performance concerns",
            score=score,
            recommendations=recommendations,
        )


class AccessibilityReviewAgent(ReviewAgent):
    """Reviews code/design for accessibility and usability."""

    def __init__(self):
        super().__init__("accessibility-reviewer", "accessibility")

    async def review(self, content: str, context: Dict[str, Any] = None) -> ReviewResult:
        """Review code for accessibility issues."""
        issues = []

        # Check for user-facing features
        if ("print(" in content or "return " in content) and len(content) > 100:
            # Check if there's user-facing output
            if "error" in content.lower() or "message" in content.lower():
                issues.append(
                    self._create_issue(
                        IssueSeverity.MEDIUM,
                        "User-facing errors lack context",
                        "Error messages should be clear and actionable",
                        suggestion="Include context and suggestions in error messages",
                    )
                )

        # Check for input validation messages
        if "ValueError" in content and "invalid" not in content.lower():
            issues.append(
                self._create_issue(
                    IssueSeverity.LOW,
                    "Generic error message",
                    "Error messages should guide users to fix issues",
                    suggestion="Provide specific, actionable error messages",
                )
            )

        # Check for internationalization
        if "hardcoded" in content.lower() or '"""' in content:
            # Check if strings are hardcoded
            if any(word in content for word in ["Hello", "Welcome", "Error:", "Success"]):
                issues.append(
                    self._create_issue(
                        IssueSeverity.LOW,
                        "Hardcoded user-facing strings",
                        "Strings should be internationalized",
                        suggestion="Use i18n library for user-facing strings",
                    )
                )

        # Calculate score
        score = max(0, 1.0 - (len(issues) * 0.15))

        recommendations = [
            "Provide clear, actionable error messages",
            "Internationalize user-facing strings",
            "Support keyboard navigation",
            "Ensure color is not the only indicator",
            "Test with users of varying abilities",
        ]

        return ReviewResult(
            reviewer_name=self.name,
            issues=issues,
            summary=f"Found {len(issues)} accessibility concerns",
            score=score,
            recommendations=recommendations,
        )


# Registry of all review agents
REVIEW_AGENTS = {
    "style-reviewer": StyleReviewAgent,
    "security-reviewer": SecurityReviewAgent,
    "architecture-reviewer": ArchitectureReviewAgent,
    "performance-reviewer": PerformanceReviewAgent,
    "accessibility-reviewer": AccessibilityReviewAgent,
}
