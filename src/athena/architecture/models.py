"""Architecture layer models for design decisions, patterns, and constraints.

This module provides the core data models for tracking architectural decisions,
design patterns, constraints, and trade-offs across projects.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DecisionStatus(str, Enum):
    """Status of an architectural decision."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class PatternType(str, Enum):
    """Type of design pattern."""
    CREATIONAL = "creational"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    ARCHITECTURAL = "architectural"
    CONCURRENCY = "concurrency"
    DATA_ACCESS = "data_access"
    INTEGRATION = "integration"


class ConstraintType(str, Enum):
    """Type of architectural constraint."""
    PERFORMANCE = "performance"
    SECURITY = "security"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"
    COST = "cost"
    REGULATORY = "regulatory"
    TECHNICAL = "technical"


class TradeOffDimension(str, Enum):
    """Dimensions for trade-off analysis."""
    COMPLEXITY = "complexity"
    PERFORMANCE = "performance"
    SCALABILITY = "scalability"
    MAINTAINABILITY = "maintainability"
    COST = "cost"
    TIME_TO_MARKET = "time_to_market"
    SECURITY = "security"
    FLEXIBILITY = "flexibility"


class ArchitecturalDecisionRecord(BaseModel):
    """Architecture Decision Record (ADR) - documents important architectural decisions.

    ADRs capture the context, decision, alternatives considered, and consequences
    of architectural choices, providing a historical record of why systems are
    built the way they are.
    """
    id: Optional[int] = None
    project_id: int
    title: str = Field(..., description="Short descriptive title of the decision")
    status: DecisionStatus = Field(default=DecisionStatus.PROPOSED)

    # Context and decision
    context: str = Field(..., description="The context or problem that led to this decision")
    decision: str = Field(..., description="The decision that was made")
    rationale: str = Field(..., description="Why this decision was made")

    # Alternatives and consequences
    alternatives: List[str] = Field(default_factory=list, description="Alternatives considered")
    consequences: List[str] = Field(default_factory=list, description="Positive and negative consequences")

    # Metadata
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    superseded_by: Optional[int] = Field(None, description="ADR ID that supersedes this one")

    # Related information
    related_patterns: List[str] = Field(default_factory=list, description="Related design patterns")
    related_constraints: List[int] = Field(default_factory=list, description="Related constraint IDs")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Tracking
    implementation_status: str = Field(default="not_started", description="Implementation progress")
    effectiveness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="How well this decision worked (0-1)")

    model_config = ConfigDict(use_enum_values=True)


class DesignPattern(BaseModel):
    """Design pattern with usage tracking and effectiveness metrics.

    Tracks reusable design patterns, their usage across projects, and how
    effective they've been in practice.
    """
    id: Optional[int] = None
    name: str = Field(..., description="Pattern name (e.g., 'Repository Pattern')")
    type: PatternType

    # Pattern description
    problem: str = Field(..., description="What problem does this pattern solve?")
    solution: str = Field(..., description="How does this pattern solve it?")
    context: str = Field(..., description="When should you use this pattern?")

    # Structure and implementation
    structure: Optional[str] = Field(None, description="UML or textual description of structure")
    code_example: Optional[str] = Field(None, description="Code example implementing pattern")

    # Usage tracking
    usage_count: int = Field(default=0, description="How many times used across projects")
    projects: List[int] = Field(default_factory=list, description="Project IDs using this pattern")

    # Effectiveness metrics
    effectiveness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Success rate (0-1)")
    success_count: int = Field(default=0, description="Successful implementations")
    failure_count: int = Field(default=0, description="Failed implementations")

    # Related information
    related_patterns: List[str] = Field(default_factory=list, description="Related or similar patterns")
    anti_patterns: List[str] = Field(default_factory=list, description="Anti-patterns to avoid")
    tags: List[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)


class ArchitecturalConstraint(BaseModel):
    """Architectural constraint that must be satisfied.

    Constraints define boundaries and requirements that architectural decisions
    must respect (e.g., "must support 10,000 concurrent users", "must comply with GDPR").
    """
    id: Optional[int] = None
    project_id: int
    type: ConstraintType

    # Constraint details
    description: str = Field(..., description="What is the constraint?")
    rationale: str = Field(..., description="Why does this constraint exist?")

    # Validation
    validation_criteria: str = Field(..., description="How to verify this constraint is met")
    is_hard_constraint: bool = Field(default=True, description="Must satisfy (True) vs. should satisfy (False)")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")

    # Scope
    applies_to: List[str] = Field(default_factory=list, description="Components/layers this applies to")

    # Status
    is_satisfied: bool = Field(default=False)
    verification_date: Optional[datetime] = None
    verification_notes: Optional[str] = None

    # Related
    related_adrs: List[int] = Field(default_factory=list, description="ADRs addressing this constraint")
    tags: List[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)


class TradeOffAnalysis(BaseModel):
    """Trade-off analysis comparing architectural options.

    Systematically evaluates different architectural approaches across multiple
    dimensions to support decision-making.
    """
    id: Optional[int] = None
    project_id: int

    # What's being compared
    decision_context: str = Field(..., description="What decision is being made?")
    options: List[str] = Field(..., min_length=2, description="Options being compared")

    # Dimensions and scores
    dimensions: List[TradeOffDimension] = Field(..., description="Dimensions to evaluate")
    scores: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Scores for each option on each dimension (option -> dimension -> score 0-1)"
    )

    # Weighting
    dimension_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Importance weight for each dimension (0-1)"
    )

    # Results
    recommended_option: Optional[str] = Field(None, description="Recommended choice")
    recommendation_rationale: Optional[str] = Field(None, description="Why this option?")
    total_scores: Dict[str, float] = Field(default_factory=dict, description="Weighted total scores")

    # Related
    related_adr_id: Optional[int] = Field(None, description="ADR documenting this decision")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    analyst: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class ArchitectureEvolution(BaseModel):
    """Track how architecture evolves over time.

    Records significant architectural changes, migrations, and transformations
    to understand the evolution of the system.
    """
    id: Optional[int] = None
    project_id: int

    # Change details
    change_type: str = Field(..., description="Type of change (e.g., 'layer_added', 'migration', 'refactoring')")
    description: str = Field(..., description="What changed?")

    # Before and after
    before_state: Optional[str] = Field(None, description="Architecture before change")
    after_state: Optional[str] = Field(None, description="Architecture after change")

    # Why and how
    motivation: str = Field(..., description="Why was this change made?")
    approach: Optional[str] = Field(None, description="How was the change implemented?")

    # Impact
    components_affected: List[str] = Field(default_factory=list)
    breaking_changes: bool = Field(default=False)
    impact_assessment: Optional[str] = None

    # Results
    outcome: Optional[str] = Field(None, description="How did the change work out?")
    lessons_learned: Optional[str] = None

    # Related
    related_adr_id: Optional[int] = None
    related_patterns: List[str] = Field(default_factory=list)

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    author: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class SystemBoundary(BaseModel):
    """Define system and bounded context boundaries.

    Maps the boundaries between different systems, services, or bounded contexts
    to understand integration points and dependencies.
    """
    id: Optional[int] = None
    project_id: int

    # Boundary definition
    name: str = Field(..., description="Name of this system/context")
    type: str = Field(..., description="Type (e.g., 'bounded_context', 'microservice', 'layer')")
    description: str = Field(..., description="What is this boundary?")

    # Scope
    components: List[str] = Field(default_factory=list, description="Components within this boundary")
    responsibilities: List[str] = Field(default_factory=list, description="What is this responsible for?")

    # Integration
    interfaces: List[str] = Field(default_factory=list, description="APIs/interfaces exposed")
    dependencies: List[str] = Field(default_factory=list, description="Other boundaries this depends on")
    integration_patterns: List[str] = Field(default_factory=list, description="How it integrates with others")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)


class SpecType(str, Enum):
    """Type of specification."""
    MARKDOWN = "markdown"  # General markdown specs
    OPENAPI = "openapi"  # OpenAPI/Swagger specs
    GRAPHQL = "graphql"  # GraphQL schemas
    PROTO = "proto"  # Protocol Buffer definitions
    ASYNCAPI = "asyncapi"  # AsyncAPI event specs
    TLAP = "tla+"  # TLA+ formal specifications
    ALLOY = "alloy"  # Alloy structural models
    PRISMA = "prisma"  # Prisma schema
    SQL = "sql"  # SQL schema definitions
    JSONSCHEMA = "jsonschema"  # JSON Schema


class SpecStatus(str, Enum):
    """Status of a specification."""
    DRAFT = "draft"  # Work in progress
    ACTIVE = "active"  # Current specification
    DEPRECATED = "deprecated"  # No longer recommended
    SUPERSEDED = "superseded"  # Replaced by newer spec


class Specification(BaseModel):
    """Specification defining system behavior (WHAT system should do).

    Specifications are the source of truth in spec-driven development,
    serving as the contract from which code is derived. Supports multiple
    formats including OpenAPI, TLA+, Alloy, Prisma, and markdown.
    """
    id: Optional[int] = None
    project_id: int

    # Basic metadata
    name: str = Field(..., description="Specification name (e.g., 'User Authentication API')")
    spec_type: SpecType = Field(..., description="Type of specification")
    version: str = Field(..., description="Version (SemVer or date)")
    status: SpecStatus = Field(default=SpecStatus.DRAFT)

    # Content
    content: str = Field(..., description="Specification content (format depends on spec_type)")
    file_path: Optional[str] = Field(None, description="Path to spec file in git (e.g., specs/auth.yaml)")
    description: Optional[str] = Field(None, description="Human-readable description")

    # Relationships to architecture layer
    related_adr_ids: List[int] = Field(default_factory=list, description="ADRs addressing WHY decisions")
    implements_constraint_ids: List[int] = Field(default_factory=list, description="Constraints this spec satisfies")
    uses_pattern_ids: List[str] = Field(default_factory=list, description="Design patterns used")

    # Validation
    validation_status: Optional[str] = Field(None, description="Last validation result (valid/invalid/warning)")
    validated_at: Optional[datetime] = Field(None, description="When last validated")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors/warnings")

    # Code generation
    generated_code_path: Optional[str] = Field(None, description="Path to generated code from spec")
    generation_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0, description="How well generated code matches spec (0-1)")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)
