"""Data models for code context - task-scoped code management.

Stores the code context relevant to a task, including:
- Which files are relevant and why
- Dependencies between files
- Recent changes to those files
- Known issues and their status
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class FileRole(str, Enum):
    """Role of a file in the task context."""

    IMPLEMENTATION = "implementation"  # Primary file being modified
    DEPENDENCY = "dependency"  # Required by implementation
    TEST = "test"  # Test file for implementation
    CONFIGURATION = "configuration"  # Config file
    DOCUMENTATION = "documentation"  # Related docs
    REFERENCE = "reference"  # Reference only


class DependencyType(str, Enum):
    """Type of dependency between files."""

    IMPORT = "import"  # Direct import
    REFERENCE = "reference"  # Code reference
    CONFIG = "config"  # Configuration dependency
    TESTING = "testing"  # Testing dependency
    BUILD = "build"  # Build system dependency


class IssueSeverity(str, Enum):
    """Severity of a known issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, Enum):
    """Status of a known issue."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class FileInfo(BaseModel):
    """Information about a relevant file."""

    path: str  # Relative file path
    relevance: float = 0.5  # 0.0-1.0: How relevant to task?
    role: FileRole = FileRole.IMPLEMENTATION
    lines_changed: int = 0  # Lines changed in this task
    last_modified: Optional[datetime] = None


class FileDependency(BaseModel):
    """Dependency between two files."""

    from_file: str  # Source file path
    to_file: str  # Target file path
    dependency_type: DependencyType
    description: Optional[str] = None  # Why are they related?
    strength: float = 0.5  # 0.0-1.0: How strong is dependency?


class RecentChange(BaseModel):
    """Recent change to a file."""

    file_path: str
    timestamp: datetime
    change_summary: str  # What changed?
    author: Optional[str] = None
    session_id: Optional[str] = None  # Which session made this change?


class KnownIssue(BaseModel):
    """Known issue in the code context."""

    file_path: str
    issue: str  # Description of the issue
    severity: IssueSeverity
    status: IssueStatus
    found_at: datetime
    resolution_notes: Optional[str] = None


class CodeContext(BaseModel):
    """Code context for a task.

    Captures which code is relevant to a task, dependencies, recent changes,
    and known issues. Supports task-scoped code management with relevance scoring.
    """

    id: Optional[int] = None

    # Links to higher-level concepts
    goal_id: Optional[str] = None  # UUID as string
    task_id: Optional[str] = None  # UUID as string

    # Relevant code files
    relevant_files: list[FileInfo] = Field(default_factory=list)

    # Dependencies between files
    dependencies: list[FileDependency] = Field(default_factory=list)

    # Architecture notes
    architecture_notes: Optional[str] = None

    # Recent changes to relevant files
    recent_changes: list[RecentChange] = Field(default_factory=list)

    # Known issues in this context
    known_issues: list[KnownIssue] = Field(default_factory=list)

    # Metadata
    session_id: str  # Session this context was created in
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None  # When to refresh context?
    last_refreshed: Optional[datetime] = None

    # Consolidation tracking
    consolidation_status: Optional[str] = None  # "unconsolidated", "consolidated"
    consolidated_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)
