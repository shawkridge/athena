"""Data models for IDE context and integration."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FileOpenMode(str, Enum):
    """File open mode in editor."""

    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    PREVIEW = "preview"
    MODIFIED = "modified"


class GitChangeType(str, Enum):
    """Type of git change."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"
    UNMERGED = "unmerged"


class IDEFile(BaseModel):
    """Representation of an open file in IDE."""

    id: Optional[int] = None
    project_id: int
    file_path: str = Field(..., description="Absolute path to file")

    # Open state
    is_open: bool = Field(default=False, description="Is file currently open?")
    open_mode: FileOpenMode = Field(default=FileOpenMode.READ_ONLY)

    # Content
    content_hash: Optional[str] = Field(None, description="Hash of current content")
    line_count: Optional[int] = Field(None, description="Total lines in file")
    language: Optional[str] = Field(None, description="File language/extension")

    # Tracking
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    # Metadata
    is_dirty: bool = Field(default=False, description="Has unsaved changes?")
    encoding: str = Field(default="utf-8", description="File encoding")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class CursorPosition(BaseModel):
    """Cursor position and selection state."""

    id: Optional[int] = None
    file_id: int = Field(..., description="ID of file")

    # Position
    line: int = Field(ge=1, description="Line number (1-indexed)")
    column: int = Field(ge=0, description="Column number (0-indexed)")

    # Selection (if any)
    selection_start_line: Optional[int] = Field(None, description="Selection start line")
    selection_start_column: Optional[int] = Field(None, description="Selection start column")
    selection_end_line: Optional[int] = Field(None, description="Selection end line")
    selection_end_column: Optional[int] = Field(None, description="Selection end column")
    selected_text: Optional[str] = Field(None, description="Currently selected text")

    # Context
    context_lines_before: int = Field(default=5, description="Lines to show before cursor")
    context_lines_after: int = Field(default=5, description="Lines to show after cursor")
    context: Optional[str] = Field(None, description="Code context around cursor")

    # Status
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class GitStatus(BaseModel):
    """Git status for a file."""

    id: Optional[int] = None
    project_id: int
    file_path: str = Field(..., description="Path to file")

    # Current state
    change_type: GitChangeType = Field(..., description="Type of change")
    is_staged: bool = Field(default=False, description="Is change staged?")
    is_untracked: bool = Field(default=False, description="Is file untracked?")

    # Conflict state
    is_conflicted: bool = Field(default=False, description="Has merge conflicts?")
    conflict_details: Optional[str] = Field(None, description="Conflict information")

    # Diff info
    lines_added: int = Field(default=0, ge=0, description="Lines added")
    lines_deleted: int = Field(default=0, ge=0, description="Lines deleted")
    lines_modified: int = Field(default=0, ge=0, description="Lines modified")

    # History
    last_commit_hash: Optional[str] = Field(None, description="Last commit SHA")
    last_commit_author: Optional[str] = Field(None, description="Last commit author")
    last_commit_message: Optional[str] = Field(None, description="Last commit message")
    last_commit_date: Optional[datetime] = None

    # Blame info
    blame_lines: list[str] = Field(
        default_factory=list, description="Blame info per line"
    )

    checked_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class GitDiff(BaseModel):
    """Git diff for a file."""

    id: Optional[int] = None
    project_id: int
    file_path: str

    # Diff content
    old_content: Optional[str] = Field(None, description="Previous content")
    new_content: Optional[str] = Field(None, description="Current content")

    # Unified diff
    unified_diff: Optional[str] = Field(None, description="Unified diff format")

    # Stats
    lines_added: int = Field(ge=0, description="Total added lines")
    lines_deleted: int = Field(ge=0, description="Total deleted lines")

    # Hunk info
    hunks: list[dict] = Field(
        default_factory=list,
        description="List of diff hunks with line ranges"
    )

    # Change type
    change_type: GitChangeType = Field(default=GitChangeType.MODIFIED)

    captured_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class IDEContextSnapshot(BaseModel):
    """Snapshot of IDE state at a point in time."""

    id: Optional[int] = None
    project_id: int

    # Session
    session_id: str = Field(..., description="Unique session identifier")

    # Open files
    open_files: list[str] = Field(
        default_factory=list, description="Paths to open files"
    )
    open_file_count: int = Field(default=0, description="Number of open files")

    # Active file
    active_file: Optional[str] = Field(None, description="Currently active file")
    active_line: Optional[int] = Field(None, description="Cursor line in active file")
    active_column: Optional[int] = Field(None, description="Cursor column in active file")

    # Git state
    current_branch: Optional[str] = Field(None, description="Current git branch")
    uncommitted_changes: int = Field(default=0, description="Count of files with changes")
    untracked_files: int = Field(default=0, description="Count of untracked files")

    # Terminal state (if integrated)
    terminal_open: bool = Field(default=False, description="Is terminal open?")
    terminal_cwd: Optional[str] = Field(None, description="Terminal working directory")

    # Other panels
    debug_open: bool = Field(default=False, description="Is debugger open?")
    test_explorer_open: bool = Field(default=False, description="Is test explorer open?")
    git_panel_open: bool = Field(default=False, description="Is git panel open?")

    # Settings
    zoom_level: float = Field(default=1.0, description="Editor zoom level")
    theme: Optional[str] = Field(None, description="Current theme")
    font_size: Optional[int] = Field(None, description="Font size in pixels")

    captured_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class IDEActivity(BaseModel):
    """Track IDE user activity and patterns."""

    id: Optional[int] = None
    project_id: int

    # File activity
    file_path: str
    activity_type: str = Field(
        description="save, open, close, edit, refactor, test, debug"
    )

    # Context
    cursor_position: Optional[str] = Field(None, description="Line:column format")
    selected_text: Optional[str] = Field(None, description="Selected text snippet")
    entity_id: Optional[int] = Field(None, description="ID of code entity affected")

    # Timing
    duration_seconds: Optional[float] = Field(None, description="Activity duration")

    # Agent involvement
    agent_triggered: bool = Field(default=False, description="Was agent involved?")
    agent_id: Optional[str] = Field(None, description="Which agent?")

    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True
