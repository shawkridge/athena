"""Data models for project context - centralized project state."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProjectPhase(str, Enum):
    """Current phase of project development."""

    PLANNING = "planning"
    FEATURE_DEVELOPMENT = "feature_development"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class ProjectContext(BaseModel):
    """Centralized project state - single source of truth.

    Answers questions like:
    - "What are we building?"
    - "What's the current status?"
    - "What mistakes do we keep making?"
    - "Why did we choose X?"
    """

    id: Optional[int] = None
    project_id: str  # UUID as string for database compatibility
    name: str
    description: str

    # Current state
    current_phase: ProjectPhase = ProjectPhase.PLANNING
    current_goal_id: Optional[str] = None  # UUID as string

    # Architecture understanding
    architecture: Optional[dict] = None  # modules, entry_points, dependencies, known_patterns

    # Progress tracking
    completed_goal_count: int = 0
    in_progress_goal_count: int = 0
    blocked_goal_count: int = 0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class Decision(BaseModel):
    """Architectural or technical decision made in the project."""

    id: Optional[int] = None
    project_id: str  # UUID as string
    decision: str  # The decision made
    reasoning: str  # Why we made this choice
    alternatives_considered: list[str] = Field(default_factory=list)  # Alternatives we rejected
    impact: str  # "positive", "negative", "neutral"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ErrorPattern(BaseModel):
    """Recurring error pattern in the project.

    Used to track:
    - What types of errors we encounter
    - How frequently they occur
    - What mitigations work
    - Status (open, resolved, investigating)
    """

    id: Optional[int] = None
    project_id: str  # UUID as string
    error_type: str  # Type of error (e.g., "type_mismatch_in_service", "async_deadlock")
    frequency: int = 1  # How many times we've seen this
    last_seen: datetime = Field(default_factory=datetime.now)  # When we last encountered it
    mitigation: Optional[str] = None  # How to fix it
    resolved: bool = False  # Is this error pattern resolved?

    class Config:
        use_enum_values = True
