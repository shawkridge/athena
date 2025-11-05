"""Data models for session continuity - save/restore full session state.

SessionSnapshot captures the complete state of a working session, enabling
seamless resumption across /clear boundaries or context limits.

Key features:
- Immutable snapshots (new snapshot, not updates)
- Version tracking for restore compatibility
- Resumption recommendations (which cycle, next step)
- Clean session restoration (no partial state)
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Status of a saved session."""

    ACTIVE = "active"  # Session currently in progress
    PAUSED = "paused"  # Session saved and paused
    RESUMED = "resumed"  # Session restored from snapshot
    COMPLETED = "completed"  # Session work completed


class ResumptionRecommendation(BaseModel):
    """Recommendation for resuming a paused session."""

    recommended_next_action: str  # e.g., "Continue executing cycle #5"
    reason: str  # Why this is recommended
    blockers: list[str] = Field(default_factory=list)  # Current blockers
    context_summary: str  # Brief context of where you left off
    estimated_remaining_time_minutes: int = 0  # Estimate to completion


class ExecutionTraceSnapshot(BaseModel):
    """Lightweight snapshot of a recent execution trace."""

    execution_id: Optional[str] = None
    timestamp: datetime
    goal_id: Optional[str] = None
    phase: str = "executing"  # "planning", "executing", "learning", etc.
    outcome: str  # "success", "failure", "partial"
    duration_seconds: int
    error_summary: Optional[str] = None


class ActionCycleSnapshot(BaseModel):
    """Lightweight snapshot of an active action cycle."""

    cycle_id: int
    goal_id: Optional[str] = None
    status: str  # "planning", "executing", "learning", "completed", "abandoned"
    attempt_count: int
    max_attempts: int
    current_step: Optional[str] = None  # Descriptive current step
    goal_description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CodeContextSnapshot(BaseModel):
    """Lightweight snapshot of task-scoped code context."""

    context_id: int
    task_id: Optional[str] = None
    relevant_files: list[str] = Field(default_factory=list)  # Top N files
    file_count: int = 0
    dependency_count: int = 0
    recent_changes: list[str] = Field(default_factory=list)  # Latest changes
    known_issues: list[str] = Field(default_factory=list)  # Current issues


class ProjectContextSnapshot(BaseModel):
    """Lightweight snapshot of project context state."""

    project_id: str
    project_name: str
    current_phase: str
    current_goal_id: Optional[str] = None
    completed_goals: int = 0
    in_progress_goals: int = 0
    blocked_goals: int = 0
    progress_percentage: float = 0.0


class SessionSnapshot(BaseModel):
    """Complete immutable snapshot of a session state.

    Captures all necessary context to resume work seamlessly.
    Versioned for compatibility with future restore operations.
    """

    id: Optional[int] = None
    snapshot_id: str  # UUID as string for unique identification
    session_id: str  # Which session this snapshot is for
    version: int = 1  # Snapshot format version (for compatibility)

    # Session context
    status: SessionStatus = SessionStatus.PAUSED
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "user"  # Who triggered the snapshot

    # Project state
    project_snapshot: ProjectContextSnapshot

    # Active work
    active_cycle_snapshot: Optional[ActionCycleSnapshot] = None
    code_context_snapshot: Optional[CodeContextSnapshot] = None

    # Recent history (for context)
    recent_executions: list[ExecutionTraceSnapshot] = Field(default_factory=list)  # Last 10-20

    # Resumption guidance
    resumption_recommendation: ResumptionRecommendation

    # Session metadata
    goals_at_snapshot_time: list[str] = Field(default_factory=list)  # Active goals
    time_in_session_seconds: int = 0  # How long this session has been running
    primary_objective: Optional[str] = None  # What was the primary goal?
    notes: Optional[str] = None  # User-provided context

    class Config:
        use_enum_values = True


class SessionMetadata(BaseModel):
    """Metadata about a saved session for quick access."""

    id: Optional[int] = None
    snapshot_id: str  # Link to SessionSnapshot
    project_id: str
    project_name: str

    # Quick reference
    status: SessionStatus = SessionStatus.PAUSED
    created_at: datetime = Field(default_factory=datetime.now)
    active_goal_count: int = 0
    active_cycle_id: Optional[int] = None

    # Resumption hints
    resumption_reason: str  # "context limit", "user pause", "phase complete", etc.
    time_since_last_activity_minutes: int = 0

    class Config:
        use_enum_values = True
