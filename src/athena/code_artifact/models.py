"""Data models for code artifact analysis, complexity metrics, and code understanding."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of code entities."""

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    IMPORT = "import"
    CONSTANT = "constant"
    VARIABLE = "variable"


class ComplexityLevel(str, Enum):
    """Complexity assessment levels."""

    LOW = "low"  # Cyclomatic: 1-2
    MEDIUM = "medium"  # Cyclomatic: 3-10
    HIGH = "high"  # Cyclomatic: 11-30
    VERY_HIGH = "very_high"  # Cyclomatic: > 30


class CodeEntity(BaseModel):
    """Base model for code artifacts (functions, classes, modules)."""

    id: Optional[int] = None
    project_id: int

    # Identity
    name: str = Field(..., description="Entity name (function/class/module name)")
    entity_type: EntityType = Field(..., description="Type of code entity")
    file_path: str = Field(..., description="Path to file containing entity")

    # Location
    start_line: int = Field(..., description="Starting line number")
    end_line: int = Field(..., description="Ending line number")
    column_offset: int = Field(default=0, description="Column where entity starts")

    # Metadata
    docstring: Optional[str] = Field(None, description="Entity docstring/documentation")
    is_public: bool = Field(default=True, description="Is this entity publicly exported?")
    is_deprecated: bool = Field(default=False, description="Is this entity deprecated?")

    # Relationships
    parent_entity_id: Optional[int] = Field(
        None, description="ID of parent entity (class for methods)"
    )
    module_id: Optional[int] = Field(None, description="ID of containing module")

    # Metrics
    cyclomatic_complexity: int = Field(default=1, ge=1, description="Cyclomatic complexity")
    cognitive_complexity: int = Field(default=0, ge=0, description="Cognitive complexity")
    lines_of_code: int = Field(default=1, ge=1, description="Lines of code in entity")

    # Tracking
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_modified_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class TypeSignature(BaseModel):
    """Type information for function parameters and return types."""

    id: Optional[int] = None
    entity_id: int = Field(..., description="ID of function/method")

    # Function signature
    parameters: list[dict] = Field(
        default_factory=list,
        description="List of {name, type_annotation, default_value}",
    )
    return_type: Optional[str] = Field(None, description="Return type annotation")
    is_async: bool = Field(default=False, description="Is async function?")
    is_classmethod: bool = Field(default=False, description="Is classmethod?")
    is_staticmethod: bool = Field(default=False, description="Is staticmethod?")

    # Generics
    type_parameters: list[str] = Field(
        default_factory=list, description="Generic type parameters (e.g., [T, U])"
    )

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class Dependency(BaseModel):
    """Code dependency relationship between entities."""

    id: Optional[int] = None
    project_id: int

    # Relationship
    from_entity_id: int = Field(..., description="ID of entity that depends on something")
    to_entity_id: int = Field(..., description="ID of entity being depended on")
    dependency_type: str = Field(
        default="calls",
        description="Type: calls, imports, inherits, uses_type, references",
    )

    # Context
    line_number: Optional[int] = Field(None, description="Line where dependency occurs")
    file_path: str = Field(..., description="File where dependency is declared")

    # External dependencies
    external_module: Optional[str] = Field(
        None, description="External module name if depends on external"
    )
    external_entity: Optional[str] = Field(None, description="External entity name")

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ComplexityMetrics(BaseModel):
    """Comprehensive complexity analysis for code entities."""

    id: Optional[int] = None
    entity_id: int = Field(..., description="ID of analyzed entity")

    # Cyclomatic complexity
    cyclomatic_complexity: int = Field(ge=1, description="McCabe cyclomatic complexity")
    cyclomatic_level: ComplexityLevel

    # Cognitive complexity
    cognitive_complexity: int = Field(ge=0, description="Cognitive complexity (incremental)")
    cognitive_level: ComplexityLevel

    # Lines metrics
    lines_of_code: int = Field(ge=1, description="Total lines of code")
    logical_lines: int = Field(ge=1, description="Logical lines (no blanks/comments)")
    comment_lines: int = Field(ge=0, description="Lines with comments")

    # Halstead metrics
    distinct_operators: int = Field(ge=0, description="Number of distinct operators")
    distinct_operands: int = Field(ge=0, description="Number of distinct operands")
    total_operators: int = Field(ge=0, description="Total operator count")
    total_operands: int = Field(ge=0, description="Total operand count")
    halstead_difficulty: float = Field(ge=0.0, description="Halstead difficulty metric")
    halstead_volume: float = Field(ge=0.0, description="Halstead volume metric")

    # Maintainability
    maintainability_index: float = Field(
        ge=0.0, le=100.0, description="Maintainability index (0-100, higher is better)"
    )

    # Nesting
    max_nesting_depth: int = Field(ge=0, description="Maximum nesting depth")
    avg_nesting_depth: float = Field(ge=0.0, description="Average nesting depth")

    # Function metrics
    parameter_count: int = Field(ge=0, description="Number of parameters")
    return_statements: int = Field(ge=0, description="Number of return statements")

    analyzed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class CodeDiff(BaseModel):
    """Track code changes and diffs between versions."""

    id: Optional[int] = None
    project_id: int
    entity_id: Optional[int] = Field(None, description="ID of changed entity (if applicable)")

    # File info
    file_path: str = Field(..., description="Path to changed file")

    # Change details
    change_type: str = Field(default="modified", description="added, modified, deleted, renamed")

    # Diff content
    old_content: Optional[str] = Field(None, description="Previous content")
    new_content: Optional[str] = Field(None, description="Current content")

    # Line-level changes
    lines_added: int = Field(default=0, ge=0, description="Number of lines added")
    lines_deleted: int = Field(default=0, ge=0, description="Number of lines deleted")
    lines_modified: int = Field(default=0, ge=0, description="Number of lines modified")

    # Context
    git_commit_hash: Optional[str] = Field(None, description="Git commit hash")
    git_author: Optional[str] = Field(None, description="Git author")
    agent_id: Optional[str] = Field(None, description="Which agent made the change?")

    # Impact analysis
    complexity_delta: Optional[int] = Field(None, description="Change in cyclomatic complexity")
    test_coverage_delta: Optional[float] = Field(None, description="Change in test coverage %")
    affected_entities: list[int] = Field(
        default_factory=list, description="IDs of entities affected by this change"
    )

    # Semantic analysis
    breaking_change: bool = Field(default=False, description="Does this break API/contracts?")
    breaking_reason: Optional[str] = Field(None, description="Why is it breaking?")

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class CodeDependencyGraph(BaseModel):
    """Snapshot of the code dependency graph."""

    id: Optional[int] = None
    project_id: int

    # Graph stats
    total_entities: int = Field(ge=0, description="Total code entities")
    total_dependencies: int = Field(ge=0, description="Total dependencies")

    # Connectivity
    circular_dependencies: int = Field(ge=0, description="Number of circular dependency cycles")
    orphaned_entities: int = Field(ge=0, description="Entities with no dependencies")
    highly_coupled_pairs: list[tuple[int, int]] = Field(
        default_factory=list, description="Pairs of highly interdependent entities"
    )

    # Structure
    average_fan_in: float = Field(ge=0.0, description="Average incoming dependencies per entity")
    average_fan_out: float = Field(ge=0.0, description="Average outgoing dependencies per entity")
    modularity_score: float = Field(ge=0.0, le=1.0, description="Modularity metric (0-1)")

    # External coupling
    external_dependencies_count: int = Field(ge=0, description="Number of external dependencies")
    external_modules: list[str] = Field(
        default_factory=list, description="List of external modules used"
    )

    analyzed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class TestCoverage(BaseModel):
    """Test coverage information for code entities."""

    id: Optional[int] = None
    entity_id: int = Field(..., description="ID of entity with coverage info")

    # Coverage metrics
    lines_covered: int = Field(ge=0, description="Number of covered lines")
    lines_total: int = Field(ge=1, description="Total lines in entity")
    coverage_percentage: float = Field(ge=0.0, le=100.0, description="Coverage percentage")

    # Test info
    test_count: int = Field(ge=0, description="Number of tests covering this entity")
    test_file_paths: list[str] = Field(default_factory=list, description="Paths to test files")

    # Branch coverage
    branches_covered: int = Field(ge=0, description="Number of covered branches")
    branches_total: int = Field(ge=0, description="Total branches")

    measured_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class CodeQualityIssue(BaseModel):
    """Code quality issues detected (style, smells, violations)."""

    id: Optional[int] = None
    project_id: int
    entity_id: Optional[int] = Field(None, description="ID of affected entity")

    # Issue details
    issue_type: str = Field(description="smell, style_violation, type_error, complexity")
    severity: str = Field(description="info, warning, error, critical")

    # Location
    file_path: str
    line_number: int
    column_number: Optional[int] = None

    # Description
    message: str = Field(..., description="Human-readable issue description")
    rule_id: Optional[str] = Field(None, description="Linter/analyzer rule ID")

    # Remediation
    fix_suggestion: Optional[str] = Field(None, description="Suggested fix")
    documentation_url: Optional[str] = Field(None, description="Link to documentation")

    # Resolution
    resolved: bool = Field(default=False, description="Has this issue been addressed?")
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    detected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True
