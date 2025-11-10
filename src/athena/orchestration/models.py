"""Data models for orchestration layer.

Defines the core data structures for task queue, agent registry,
and routing decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class TaskStatus(str, Enum):
    """Task lifecycle states."""

    PENDING = "pending"  # Created, waiting for assignment
    ASSIGNED = "assigned"  # Assigned to agent, waiting to start
    RUNNING = "running"  # Agent executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Failed, not retrying
    BLOCKED = "blocked"  # Blocked by dependency failure


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Task:
    """Task definition and state.

    Represents a work unit to be executed by an agent.
    Tasks support dependencies (must complete in order).
    """

    id: Optional[str] = None  # UUID
    content: str = ""  # Description/prompt
    task_type: str = ""  # research, analysis, synthesis, etc.
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    requirements: List[str] = field(default_factory=list)  # Required skills
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    assigned_to: Optional[str] = None  # Agent ID
    created_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None  # Task result/output
    error: Optional[str] = None  # Error message if failed
    retry_count: int = 0  # Number of retry attempts
    execution_duration_ms: Optional[int] = None  # Wall-clock time
    estimated_duration_ms: Optional[int] = None  # Pre-execution estimate

    def is_ready_to_execute(self, completed_tasks: List[str]) -> bool:
        """Check if task is ready (all dependencies completed).

        Args:
            completed_tasks: List of completed task IDs

        Returns:
            True if all dependencies are in completed_tasks
        """
        return all(dep_id in completed_tasks for dep_id in self.dependencies)

    def get_age_seconds(self) -> float:
        """Get task age in seconds since creation."""
        if not self.created_at:
            return 0.0
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class Agent:
    """Agent definition and performance metrics.

    Represents an autonomous agent capable of executing tasks.
    Tracks capabilities and performance for routing decisions.
    """

    id: str  # Unique agent identifier
    capabilities: List[str] = field(default_factory=list)  # Skills/expertise
    max_concurrent_tasks: int = 5  # Max parallel tasks
    success_rate: float = 1.0  # Task success rate (0-1)
    avg_completion_ms: float = 0.0  # Average task duration
    current_load: int = 0  # Currently running tasks
    total_completed: int = 0  # Tasks completed
    total_failed: int = 0  # Tasks failed
    last_updated: Optional[datetime] = None  # Last metric update
    metadata: Dict[str, Any] = field(default_factory=dict)  # Custom metadata

    def get_utilization(self) -> float:
        """Get current utilization as fraction of capacity.

        Returns:
            current_load / max_concurrent_tasks (0-1+)
        """
        if self.max_concurrent_tasks <= 0:
            return 0.0
        return self.current_load / self.max_concurrent_tasks

    def is_available(self) -> bool:
        """Check if agent has capacity for more tasks.

        Returns:
            True if current_load < max_concurrent_tasks
        """
        return self.current_load < self.max_concurrent_tasks

    def get_quality_score(self) -> float:
        """Get quality score for ranking (success_rate * (1 - utilization)).

        Factors in both success rate and current load.
        Returns:
            Composite score (higher is better)
        """
        utilization = self.get_utilization()
        return self.success_rate * (1.0 - min(utilization, 1.0))


@dataclass
class RoutingDecision:
    """Result of routing algorithm.

    Captures which agent was selected and why.
    """

    selected_agent: Optional[str] = None  # Agent ID or None
    candidates: List[str] = field(default_factory=list)  # All capable agents
    scores: Dict[str, float] = field(default_factory=dict)  # Score per candidate
    reason: str = ""  # Explanation (no capable agent, agent selection logic, etc.)

    def is_successful(self) -> bool:
        """Check if routing succeeded in finding an agent.

        Returns:
            True if selected_agent is not None
        """
        return self.selected_agent is not None


@dataclass
class TaskMetrics:
    """Metrics captured during/after task execution."""

    duration_ms: int = 0  # Wall-clock execution time
    rows_processed: int = 0  # For data processing tasks
    items_created: int = 0  # For generation tasks
    errors_found: int = 0  # For validation/linting tasks
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueueStatistics:
    """Statistics about task queue state.

    Useful for monitoring and optimization.
    """

    pending_count: int = 0
    assigned_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    avg_wait_time_seconds: float = 0.0  # Time in queue before assignment
    avg_execution_time_ms: float = 0.0
    success_rate: float = 0.0  # Completed / (completed + failed)

    def total_count(self) -> int:
        """Get total task count across all statuses."""
        return (
            self.pending_count
            + self.assigned_count
            + self.running_count
            + self.completed_count
            + self.failed_count
        )

    def active_count(self) -> int:
        """Get count of active tasks (assigned or running)."""
        return self.assigned_count + self.running_count


@dataclass
class AgentStatistics:
    """Statistics about agents and their performance."""

    total_agents: int = 0
    available_agents: int = 0  # Agents with capacity
    busy_agents: int = 0  # Agents at max capacity
    avg_success_rate: float = 0.0
    avg_utilization: float = 0.0
    skill_distribution: Dict[str, int] = field(default_factory=dict)  # Skill → agent count
    hotspot_agents: List[str] = field(default_factory=list)  # Over-utilized agents
