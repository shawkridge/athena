"""Data models for procedural memory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ProcedureCategory(str, Enum):
    """Categories of procedures."""

    GIT = "git"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"


class ParameterType(str, Enum):
    """Parameter types for procedures."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    FILE = "file"
    DIRECTORY = "directory"
    LIST = "list"


class ProcedureParameter(BaseModel):
    """Parameter for a procedure."""

    id: Optional[int] = None
    procedure_id: int
    param_name: str
    param_type: ParameterType
    required: bool = True
    default_value: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class Procedure(BaseModel):
    """Executable workflow template."""

    id: Optional[int] = None
    name: str
    category: ProcedureCategory
    description: Optional[str] = None

    # When to use
    trigger_pattern: Optional[str] = None  # Regex or condition
    applicable_contexts: list[str] = Field(default_factory=list)  # e.g., ["react", "typescript"]

    # The procedure
    template: str  # Template with {{variables}}
    steps: list[dict] = Field(default_factory=list)  # Step-by-step instructions
    examples: list[dict] = Field(default_factory=list)  # Example usages

    # Learning metrics
    success_rate: float = 0.0
    usage_count: int = 0
    avg_completion_time_ms: Optional[int] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    created_by: str = "user"  # user|learned|imported

    model_config = ConfigDict(use_enum_values=True)


class ProcedureExecution(BaseModel):
    """Record of procedure execution."""

    id: Optional[int] = None
    procedure_id: int
    project_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
    outcome: str  # success|failure|partial
    duration_ms: Optional[int] = None
    variables: dict = Field(default_factory=dict)  # Variable values used
    learned: Optional[str] = None  # What we learned