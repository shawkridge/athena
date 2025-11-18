"""Data models for procedural memory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, validator


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

    # Phase 2: Executable code fields
    code: Optional[str] = None  # Executable Python code (NEW)
    code_version: str = "1.0"  # Version of code (NEW)
    code_generated: Optional[datetime] = None  # When code was generated (NEW)
    code_language: str = "python"  # Programming language (NEW)
    code_confidence: float = 0.0  # Confidence score for generated code (0.0-1.0) (NEW)
    code_git_hash: Optional[str] = None  # Git commit hash for versioning (NEW)

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


class ProcedureVersion(BaseModel):
    """Version history entry for a procedure.

    Tracks changes to procedures stored in git with full audit trail.
    """

    id: Optional[int] = None
    procedure_id: int
    version: str  # Semantic version: 1.0.0
    code_hash: str  # Git commit hash
    code_content: str  # Full code at this version
    commit_message: str  # Git commit message
    author: str  # Author of the change
    created_at: datetime = Field(default_factory=datetime.now)

    # Change metadata
    lines_added: int = 0
    lines_removed: int = 0
    is_breaking_change: bool = False
    rollback_hash: Optional[str] = None  # Points to previous version hash

    model_config = ConfigDict(use_enum_values=True)


class ExecutableProcedure(BaseModel):
    """Phase 2: Executable procedure with code generation support.

    Extends Procedure with executable Python code, versioning, and validation.
    Stored in git with full history and rollback support.
    """

    id: Optional[int] = None
    procedure_id: int  # Reference to base Procedure
    name: str
    category: ProcedureCategory

    # Code generation metadata
    code: str  # Executable Python code (required for Phase 2)
    code_version: str = "1.0.0"  # Semantic version
    code_language: str = "python"
    code_generated_at: datetime = Field(default_factory=datetime.now)
    code_generation_confidence: float  # 0.0-1.0 confidence in generated code
    code_git_hash: Optional[str] = None  # Git commit hash

    # Code validation
    syntax_valid: bool = True
    imports_validated: bool = False
    safety_checks_passed: bool = False
    code_issues: list[str] = Field(default_factory=list)  # List of issues found

    # Versioning
    current_version: str = "1.0.0"
    version_history: list[ProcedureVersion] = Field(default_factory=list)
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: str = "system"

    # Execution tracking
    execution_count: int = 0
    success_rate: float = 0.0
    avg_execution_time_ms: Optional[int] = None
    last_executed: Optional[datetime] = None

    # Documentation
    description: Optional[str] = None
    parameters: list[ProcedureParameter] = Field(default_factory=list)
    returns: Optional[str] = None  # Description of return value
    examples: list[str] = Field(default_factory=list)  # Usage examples
    preconditions: list[str] = Field(default_factory=list)  # Must be true before execution
    postconditions: list[str] = Field(default_factory=list)  # Should be true after execution

    model_config = ConfigDict(use_enum_values=True)

    @validator("code_generation_confidence")
    def validate_confidence(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @validator("current_version")
    def validate_version(cls, v):
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be in semantic format: X.Y.Z")
        try:
            [int(p) for p in parts]
        except ValueError:
            raise ValueError("Version components must be integers")
        return v

    def add_version(
        self, new_code: str, git_hash: str, commit_message: str, author: str = "system"
    ) -> "ExecutableProcedure":
        """Create a new version of this procedure.

        Args:
            new_code: New code content
            git_hash: Git commit hash
            commit_message: Commit message
            author: Author of the change

        Returns:
            Updated ExecutableProcedure with new version
        """
        # Calculate version bump
        parts = [int(p) for p in self.current_version.split(".")]
        parts[2] += 1  # Patch version
        new_version = ".".join(str(p) for p in parts)

        # Create version entry
        version_entry = ProcedureVersion(
            procedure_id=self.procedure_id or 0,
            version=new_version,
            code_hash=git_hash,
            code_content=new_code,
            commit_message=commit_message,
            author=author,
        )

        # Update procedure
        self.version_history.append(version_entry)
        self.code = new_code
        self.current_version = new_version
        self.code_git_hash = git_hash
        self.last_modified = datetime.now()
        self.last_modified_by = author

        return self

    def get_version(self, version: str) -> Optional[str]:
        """Retrieve code for a specific version.

        Args:
            version: Semantic version string

        Returns:
            Code content for that version, or None if not found
        """
        for v in self.version_history:
            if v.version == version:
                return v.code_content
        return None

    def rollback_to_version(self, version: str) -> bool:
        """Rollback to a specific version.

        Args:
            version: Semantic version string to rollback to

        Returns:
            True if rollback successful, False if version not found
        """
        code = self.get_version(version)
        if not code:
            return False

        self.code = code
        self.current_version = version
        self.last_modified = datetime.now()
        self.last_modified_by = "system:rollback"

        return True
