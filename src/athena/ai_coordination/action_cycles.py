"""Data models for action cycles - Goal → Plan → Execute → Learn orchestration.

ActionCycle is the central orchestration unit that manages:
- Goal definition and prioritization
- Planning phase with assumptions
- Execution phase with multiple attempts
- Learning phase with lesson extraction
- Replanning when failures detected
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CycleStatus(str, Enum):
    """Status of an action cycle."""

    PLANNING = "planning"  # Planning phase
    EXECUTING = "executing"  # Executing planned steps
    LEARNING = "learning"  # Learning from attempts
    COMPLETED = "completed"  # Successfully completed
    ABANDONED = "abandoned"  # Abandoned (max attempts exceeded)


class PlanAssumption(BaseModel):
    """Assumption made in the plan."""

    assumption: str  # What was assumed?
    confidence: float = 0.5  # 0.0-1.0: How confident in this assumption?
    critical: bool = False  # Is this assumption critical to success?
    validation_strategy: Optional[str] = None  # How to validate this assumption?


class ExecutionSummary(BaseModel):
    """Summary of execution attempt."""

    attempt_number: int
    execution_id: Optional[str] = None  # UUID of ExecutionTrace
    outcome: str  # "success", "failure", "partial"
    duration_seconds: int = 0
    code_changes_count: int = 0
    errors_encountered: int = 0
    lessons_from_attempt: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class LessonLearned(BaseModel):
    """Lesson extracted from execution attempts."""

    lesson: str  # What was learned?
    source_attempt: int  # Which attempt yielded this lesson?
    confidence: float = 0.5  # 0.0-1.0: How confident in this lesson?
    applies_to: list[str] = Field(default_factory=list)  # e.g., ["async code", "error handling"]
    can_create_procedure: bool = False  # Can this become a reusable procedure?


class PlanAdjustment(BaseModel):
    """Adjustment to plan based on learning."""

    adjustment: str  # What changed in the plan?
    reason: str  # Why was this adjustment necessary?
    triggered_by_attempt: int  # Which attempt triggered this?
    confidence: float = 0.5  # 0.0-1.0: How confident in this adjustment?


class ActionCycle(BaseModel):
    """Complete action cycle for a goal.

    Orchestrates Goal → Plan → Execute → Learn loop with replanning support.
    Tracks all attempts, lessons learned, and plan adjustments.
    """

    id: Optional[int] = None

    # Goal context
    goal_id: Optional[str] = None  # UUID of goal this cycle is for
    goal_description: str  # Human-readable goal
    goal_priority: float = 5.0  # Priority (1-10)

    # Planning
    plan_description: str  # Human-readable plan
    plan_quality: float = 0.5  # 0.0-1.0: Quality of plan
    plan_assumptions: list[PlanAssumption] = Field(default_factory=list)

    # Execution tracking
    executions: list[ExecutionSummary] = Field(default_factory=list)
    max_attempts: int = 5  # Maximum retry attempts
    current_attempt: int = 1

    # Metrics
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    partial_executions: int = 0
    success_rate: float = 0.0

    # Learning
    lessons_learned: list[LessonLearned] = Field(default_factory=list)
    plan_adjustments: list[PlanAdjustment] = Field(default_factory=list)
    replanning_count: int = 0  # How many times did we replan?

    # Status and metadata
    status: CycleStatus = CycleStatus.PLANNING
    reason_abandoned: Optional[str] = None

    # Timestamps
    session_id: str  # Session this cycle is in
    created_at: datetime = Field(default_factory=datetime.now)
    started_execution_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Consolidation tracking
    consolidation_status: Optional[str] = None  # "unconsolidated", "consolidated"
    consolidated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
