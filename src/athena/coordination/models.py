"""
Coordination Models for Multi-Agent Orchestration

Dataclasses representing agents, their state, and coordination events.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any


class AgentStatus(str, Enum):
    """Status of an agent."""

    IDLE = "idle"
    BUSY = "busy"
    FAILED = "failed"
    OFFLINE = "offline"


class AgentType(str, Enum):
    """Types of specialist agents."""

    RESEARCH = "research"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    TESTING = "testing"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskPriority(str, Enum):
    """Priority level of a task."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Capability-to-agent mapping
AGENT_CAPABILITIES = {
    AgentType.RESEARCH: [
        "web_search",
        "documentation_retrieval",
        "academic_research",
        "source_gathering",
    ],
    AgentType.ANALYSIS: [
        "code_analysis",
        "pattern_detection",
        "complexity_assessment",
        "dependency_analysis",
    ],
    AgentType.SYNTHESIS: [
        "information_synthesis",
        "result_aggregation",
        "insight_generation",
        "summary_writing",
    ],
    AgentType.VALIDATION: [
        "testing",
        "quality_assessment",
        "correctness_verification",
        "performance_validation",
    ],
    AgentType.OPTIMIZATION: [
        "performance_optimization",
        "bottleneck_analysis",
        "resource_efficiency",
        "profiling",
    ],
    AgentType.DOCUMENTATION: [
        "documentation_writing",
        "api_documentation",
        "guide_generation",
        "example_creation",
    ],
    AgentType.CODE_REVIEW: [
        "code_review",
        "security_review",
        "quality_assessment",
        "best_practices",
    ],
    AgentType.DEBUGGING: [
        "debugging",
        "root_cause_analysis",
        "troubleshooting",
        "diagnostics",
    ],
    AgentType.TESTING: [
        "test_generation",
        "unit_testing",
        "integration_testing",
        "coverage_analysis",
    ],
}


@dataclass
class Agent:
    """Represents a specialist agent in the system."""

    agent_id: str
    agent_type: AgentType
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    tmux_pane_id: Optional[str] = None
    process_pid: Optional[int] = None
    current_task_id: Optional[str] = None
    restart_count: int = 0
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_stale(self, stale_threshold_seconds: int = 60) -> bool:
        """Check if agent heartbeat is stale."""
        elapsed = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
        return elapsed > stale_threshold_seconds

    def can_execute(self, required_capabilities: List[str]) -> bool:
        """Check if agent has required capabilities."""
        return all(cap in self.capabilities for cap in required_capabilities)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Create Agent from database row dict."""
        # Convert timestamps from database format
        if isinstance(data.get("last_heartbeat"), str):
            data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # Convert agent_type if string
        if isinstance(data.get("agent_type"), str):
            data["agent_type"] = AgentType(data["agent_type"])

        # Convert status if string
        if isinstance(data.get("status"), str):
            data["status"] = AgentStatus(data["status"])

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Task:
    """Represents a task in the prospective memory system."""

    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_agent_id: Optional[str] = None
    progress_percentage: int = 0
    blocked_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    estimated_effort_minutes: Optional[int] = None
    project_id: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    def is_pending(self) -> bool:
        """Check if task is awaiting assignment."""
        return self.status == TaskStatus.PENDING and self.assigned_agent_id is None

    def is_active(self) -> bool:
        """Check if task is currently being worked on."""
        return self.status == TaskStatus.IN_PROGRESS

    def is_completed(self) -> bool:
        """Check if task has finished."""
        return self.status == TaskStatus.COMPLETED

    def is_blocked(self) -> bool:
        """Check if task is blocked."""
        return self.blocked_by is not None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from database row dict."""
        # Convert timestamps from database format
        if isinstance(data.get("claimed_at"), str):
            data["claimed_at"] = datetime.fromisoformat(data["claimed_at"])
        if isinstance(data.get("deadline"), str):
            data["deadline"] = datetime.fromisoformat(data["deadline"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # Convert enums if strings
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])
        if isinstance(data.get("priority"), str):
            data["priority"] = TaskPriority(data["priority"])

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CoordinationEvent:
    """Represents a progress event from an agent."""

    event_id: int
    agent_id: str
    task_id: str
    event_type: str = "agent_progress"  # From episodic_events
    progress_percentage: int = 0
    findings: Dict[str, Any] = field(default_factory=dict)
    blocked_by: Optional[str] = None
    status: str = "in_progress"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoordinationEvent":
        """Create CoordinationEvent from database row dict."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class OrchestrationState:
    """Represents the state of the orchestration system."""

    orchestrator_id: str
    parent_task_id: str
    decomposed_subtasks: List[str] = field(default_factory=list)
    active_agents: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    blocked_tasks: List[str] = field(default_factory=list)
    context_tokens_used: int = 0
    context_tokens_limit: int = 200000
    last_checkpoint: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def needs_checkpoint(self) -> bool:
        """Check if state should be checkpointed (token usage high)."""
        return self.context_tokens_used > (self.context_tokens_limit * 0.8)

    def context_budget_remaining(self) -> int:
        """Get remaining context tokens."""
        return self.context_tokens_limit - self.context_tokens_used

    def progress_percentage(self) -> float:
        """Calculate overall progress."""
        total = len(self.decomposed_subtasks)
        if total == 0:
            return 0.0

        completed = len(self.completed_tasks)
        return (completed / total) * 100


@dataclass
class AgentMetrics:
    """Metrics for agent performance."""

    agent_id: str
    total_tasks_assigned: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_task_duration_seconds: float = 0.0
    success_rate: float = 0.0
    average_heartbeat_latency_ms: float = 0.0
    last_task_completion: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    restart_count: int = 0

    def calculate_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.total_tasks_completed + self.total_tasks_failed
        if total == 0:
            return 0.0
        return (self.total_tasks_completed / total) * 100

    def is_healthy(self) -> bool:
        """Determine if agent is healthy based on metrics."""
        # Healthy if: success rate > 70% and not recently failed
        success_rate = self.calculate_success_rate()
        if success_rate < 70:
            return False

        if self.last_failure:
            time_since_failure = (datetime.now(timezone.utc) - self.last_failure).total_seconds()
            if time_since_failure < 300:  # Failed in last 5 minutes
                return False

        return True
