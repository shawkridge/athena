"""Code pattern models for refactoring and bug-fix learning.

Defines structures for:
- Refactoring patterns (Extract method, Rename, etc)
- Bug-fix patterns (Common bug types and solutions)
- Code smell patterns
- Architectural improvement patterns
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PatternType(str, Enum):
    """Types of code patterns."""

    REFACTORING = "refactoring"  # Code structure improvement
    BUG_FIX = "bug_fix"  # Fix for a specific bug type
    CODE_SMELL = "code_smell"  # Anti-pattern detection
    ARCHITECTURAL = "architectural"  # Architecture improvement
    PERFORMANCE = "performance"  # Performance optimization
    SECURITY = "security"  # Security vulnerability fix


class RefactoringType(str, Enum):
    """Common refactoring patterns."""

    EXTRACT_METHOD = "extract_method"  # Break method into smaller pieces
    EXTRACT_CLASS = "extract_class"  # Move code to new class
    EXTRACT_INTERFACE = "extract_interface"  # Create interface from class
    RENAME = "rename"  # Rename variable/method/class
    INLINE = "inline"  # Inline method/variable
    MOVE_METHOD = "move_method"  # Move method to different class
    CONSOLIDATE_CONDITIONAL = "consolidate_conditional"  # Simplify if/else
    SIMPLIFY_LOOP = "simplify_loop"  # Use list comprehension, for-each
    REMOVE_DUPLICATION = "remove_duplication"  # DRY principle
    PARAMETER_OBJECT = "parameter_object"  # Group parameters
    INTRODUCE_PARAMETER_OBJECT = "introduce_parameter_object"  # Grouping
    REPLACE_EXCEPTION_WITH_TEST = "replace_exception_with_test"  # Validation
    DECOMPOSE_CONDITIONAL = "decompose_conditional"  # Complex conditions
    CONSOLIDATE_DUPLICATE_CODE = "consolidate_duplicate_code"  # DRY


class BugFixType(str, Enum):
    """Common bug patterns and fixes."""

    NULL_POINTER = "null_pointer"  # Null reference handling
    INDEX_OUT_OF_BOUNDS = "index_out_of_bounds"  # Array bounds
    TYPE_MISMATCH = "type_mismatch"  # Type conversion issues
    RACE_CONDITION = "race_condition"  # Concurrency issues
    MEMORY_LEAK = "memory_leak"  # Resource not released
    INFINITE_LOOP = "infinite_loop"  # Loop termination
    OFF_BY_ONE = "off_by_one"  # Loop boundary errors
    LOGIC_ERROR = "logic_error"  # Incorrect conditional
    API_MISUSE = "api_misuse"  # Wrong API usage
    TIMEOUT = "timeout"  # Performance/deadlock
    ENCODING = "encoding"  # Character encoding issues
    FLOAT_PRECISION = "float_precision"  # Floating-point errors
    PATH_TRAVERSAL = "path_traversal"  # Security vulnerability
    INJECTION = "injection"  # SQL/command injection


class CodeSmellType(str, Enum):
    """Code smells that indicate problems."""

    LONG_METHOD = "long_method"  # Method too large
    LONG_CLASS = "long_class"  # Class has too many responsibilities
    DUPLICATE_CODE = "duplicate_code"  # Code repetition
    DEAD_CODE = "dead_code"  # Unused code
    MAGIC_NUMBER = "magic_number"  # Hardcoded values
    LONG_PARAMETER_LIST = "long_parameter_list"  # Too many parameters
    PRIMITIVE_OBSESSION = "primitive_obsession"  # Overuse of primitives
    SWITCH_STATEMENTS = "switch_statements"  # Multiple similar switches
    SPECULATIVE_GENERALITY = "speculative_generality"  # Unused abstraction
    TEMPORARY_FIELDS = "temporary_fields"  # Fields used rarely
    MESSAGE_CHAINS = "message_chains"  # Long chains of calls
    MIDDLE_MAN = "middle_man"  # Unnecessary delegation


@dataclass
class CodeMetrics:
    """Metrics about a code change."""

    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: int = 0
    functions_modified: int = 0
    classes_modified: int = 0
    cyclomatic_complexity_before: Optional[float] = None
    cyclomatic_complexity_after: Optional[float] = None
    test_coverage_before: Optional[float] = None
    test_coverage_after: Optional[float] = None
    performance_impact: Optional[str] = None  # "improved", "degraded", "neutral"

    def __post_init__(self):
        """Validate metrics."""
        if self.lines_added < 0:
            raise ValueError("lines_added must be >= 0")
        if self.lines_deleted < 0:
            raise ValueError("lines_deleted must be >= 0")


@dataclass
class CodeChange:
    """A specific code change (file + location)."""

    file_path: str
    language: str  # python, javascript, go, etc
    line_number_start: int
    line_number_end: Optional[int] = None
    symbol_name: Optional[str] = None  # function/class name
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    change_type: str = "modification"  # "add", "remove", "modify"

    def __post_init__(self):
        """Validate change."""
        if not self.file_path:
            raise ValueError("file_path required")
        if self.line_number_start < 1:
            raise ValueError("line_number_start must be >= 1")


@dataclass
class RefactoringPattern:
    """A refactoring pattern learned from code changes."""

    id: Optional[int] = None
    refactoring_type: RefactoringType = RefactoringType.EXTRACT_METHOD
    description: str = ""
    before_pattern: Optional[str] = None  # Regex or code snippet
    after_pattern: Optional[str] = None  # Expected result
    code_changes: list[CodeChange] = field(default_factory=list)
    metrics: CodeMetrics = field(default_factory=CodeMetrics)
    language: str = "python"
    frequency: int = 0  # How many times seen
    effectiveness: float = 0.5  # 0-1, how well it solved the issue
    last_applied: Optional[datetime] = None
    learned_from_commits: list[str] = field(default_factory=list)  # Commit hashes
    is_template: bool = False  # Can be reused as template
    template_name: Optional[str] = None

    def __post_init__(self):
        """Validate pattern."""
        if not self.description:
            raise ValueError("description required")
        if not (0.0 <= self.effectiveness <= 1.0):
            raise ValueError(f"effectiveness must be [0-1], got {self.effectiveness}")


@dataclass
class BugFixPattern:
    """A bug-fix pattern learned from regressions."""

    id: Optional[int] = None
    bug_type: BugFixType = BugFixType.NULL_POINTER
    description: str = ""
    symptoms: list[str] = field(default_factory=list)  # What to look for
    root_causes: list[str] = field(default_factory=list)  # Why it happens
    solution: str = ""  # How to fix it
    code_examples: list[CodeChange] = field(default_factory=list)
    prevention_steps: list[str] = field(default_factory=list)
    language: str = "python"
    frequency: int = 0  # How many times seen
    confidence: float = 0.5  # 0-1, confidence in pattern
    last_applied: Optional[datetime] = None
    learned_from_regressions: list[int] = field(default_factory=list)  # Regression IDs
    time_to_fix_minutes: Optional[int] = None
    is_critical: bool = False

    def __post_init__(self):
        """Validate pattern."""
        if not self.description:
            raise ValueError("description required")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be [0-1], got {self.confidence}")


@dataclass
class CodeSmellPattern:
    """A code smell that indicates potential problems."""

    id: Optional[int] = None
    smell_type: CodeSmellType = CodeSmellType.LONG_METHOD
    description: str = ""
    detection_rule: str = ""  # How to identify it
    severity: str = "warning"  # "info", "warning", "critical"
    affected_file: Optional[str] = None
    affected_symbol: Optional[str] = None
    suggested_fixes: list[str] = field(default_factory=list)
    frequency_in_codebase: int = 0
    priority: int = 5  # 1-10, higher = fix first

    def __post_init__(self):
        """Validate smell."""
        if not self.description:
            raise ValueError("description required")
        if self.severity not in ("info", "warning", "critical"):
            raise ValueError(f"Invalid severity: {self.severity}")
        if not (1 <= self.priority <= 10):
            raise ValueError(f"priority must be [1-10], got {self.priority}")


@dataclass
class PatternApplication:
    """Record of applying a pattern to code."""

    id: Optional[int] = None
    pattern_id: int = 0
    pattern_type: PatternType = PatternType.REFACTORING
    commit_hash: str = ""
    author: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    metrics_before: CodeMetrics = field(default_factory=CodeMetrics)
    metrics_after: CodeMetrics = field(default_factory=CodeMetrics)
    feedback: Optional[str] = None  # User feedback on pattern
    outcome: str = "success"  # "success", "partial", "failed"

    def __post_init__(self):
        """Validate application."""
        if not self.commit_hash:
            raise ValueError("commit_hash required")
        if not self.author:
            raise ValueError("author required")


@dataclass
class ArchitecturalPattern:
    """Architectural improvement pattern."""

    id: Optional[int] = None
    name: str = ""  # e.g., "MVC", "Factory", "Observer"
    description: str = ""
    benefits: list[str] = field(default_factory=list)
    drawbacks: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)  # Involved classes/modules
    implementation_effort: str = "medium"  # "low", "medium", "high"
    risk_level: str = "low"  # "low", "medium", "high"
    example_commits: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    frequency_applied: int = 0

    def __post_init__(self):
        """Validate pattern."""
        if not self.name:
            raise ValueError("name required")
        if not self.description:
            raise ValueError("description required")


@dataclass
class PatternSuggestion:
    """Suggestion to apply a pattern to current code."""

    id: Optional[int] = None
    pattern_id: int = 0
    pattern_type: PatternType = PatternType.REFACTORING
    file_path: str = ""
    location: str = ""  # Line number or symbol name
    confidence: float = 0.5  # 0-1, how confident in suggestion
    reason: str = ""  # Why suggest this pattern
    impact: str = "low"  # "low", "medium", "high"
    effort: str = "medium"  # "low", "medium", "high"
    created_at: datetime = field(default_factory=datetime.now)
    dismissed: bool = False
    applied: bool = False
    feedback: Optional[str] = None

    def __post_init__(self):
        """Validate suggestion."""
        if not self.file_path:
            raise ValueError("file_path required")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be [0-1], got {self.confidence}")
