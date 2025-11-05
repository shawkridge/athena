"""Data models for executive function system."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List


class GoalType(str, Enum):
    """Goal type classification."""

    PRIMARY = "primary"
    SUBGOAL = "subgoal"
    MAINTENANCE = "maintenance"


class GoalStatus(str, Enum):
    """Goal status lifecycle."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class StrategyType(str, Enum):
    """Strategy types for goal execution."""

    TOP_DOWN = "top_down"  # Decompose then execute
    BOTTOM_UP = "bottom_up"  # Start small, build up
    SPIKE = "spike"  # Research/prototype first
    INCREMENTAL = "incremental"  # MVP early
    PARALLEL = "parallel"  # Work on multiple at once
    SEQUENTIAL = "sequential"  # One at a time
    DEADLINE_DRIVEN = "deadline_driven"  # Focus on deadline
    QUALITY_FIRST = "quality_first"  # Perfectionist
    COLLABORATION = "collaboration"  # Involve others
    EXPERIMENTAL = "experimental"  # Try multiple approaches


@dataclass
class Goal:
    """Goal representation."""

    id: int
    project_id: int
    goal_text: str
    goal_type: GoalType
    priority: int  # 1-10
    status: GoalStatus
    progress: float  # 0.0-1.0
    created_at: datetime
    parent_goal_id: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: float = 0.0
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def is_on_track(self) -> bool:
        """Check if goal is on track vs deadline."""
        if not self.deadline or not self.estimated_hours:
            return True

        elapsed = (datetime.now() - self.created_at).total_seconds() / 3600
        expected_progress = elapsed / self.estimated_hours
        return self.progress >= expected_progress * 0.8  # Allow 20% buffer

    def days_to_deadline(self) -> Optional[int]:
        """Days until deadline, or None if no deadline."""
        if not self.deadline:
            return None
        return (self.deadline.date() - datetime.now().date()).days

    def is_urgent(self) -> bool:
        """Check if goal is urgent (within 3 days of deadline)."""
        days_left = self.days_to_deadline()
        return days_left is not None and days_left <= 3


@dataclass
class TaskSwitch:
    """Record of task switching event."""

    id: int
    project_id: int
    to_goal_id: int
    from_goal_id: Optional[int] = None
    switch_cost_ms: int = 0
    reason: str = "user_request"  # priority_change, blocker, deadline, completion, user_request
    switched_at: datetime = field(default_factory=datetime.now)
    context_snapshot: Optional[str] = None  # JSON


@dataclass
class ProgressMilestone:
    """Goal milestone for progress tracking."""

    id: int
    goal_id: int
    milestone_text: str
    expected_progress: float  # 0.25, 0.5, 0.75, 1.0
    actual_progress: float = 0.0
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def is_on_track(self) -> bool:
        """Check if milestone is on track."""
        if not self.target_date:
            return True

        elapsed = (datetime.now() - self.target_date).total_seconds()
        return elapsed <= 0  # Not yet past target date


@dataclass
class StrategyRecommendation:
    """Strategy recommendation for a goal."""

    id: int
    goal_id: int
    strategy_name: StrategyType
    confidence: float  # 0.0-1.0
    model_version: Optional[str] = None
    recommended_at: datetime = field(default_factory=datetime.now)
    outcome: Optional[str] = None  # 'success', 'failure', 'pending'


@dataclass
class ExecutiveMetrics:
    """Aggregate metrics for executive function."""

    id: int
    project_id: int
    metric_date: datetime
    total_goals: int = 0
    completed_goals: int = 0
    abandoned_goals: int = 0
    average_switch_cost_ms: float = 0.0
    total_switch_overhead_ms: int = 0
    average_goal_completion_hours: Optional[float] = None
    success_rate: float = 0.0  # completed / (completed + abandoned)
    efficiency_score: float = 0.0  # 0-100

    def calculate_efficiency_score(self) -> float:
        """
        Calculate efficiency score.

        efficiency = 100 × (completed_goals / total_goals) × (1 - switch_overhead_ratio)
        """
        if self.total_goals == 0:
            return 100.0

        goal_completion_rate = self.completed_goals / self.total_goals
        # TODO: Calculate based on total duration
        switch_overhead_ratio = min(0.5, self.total_switch_overhead_ms / 10000.0)

        return 100.0 * goal_completion_rate * (1.0 - switch_overhead_ratio)
