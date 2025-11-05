"""
Pydantic models for Phase 4 Integration Orchestrator.

Models for workflow management, agent coordination, and system metrics.
"""

from enum import Enum
from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowPhase(str, Enum):
    """Phases of workflow execution."""
    PENDING = "pending"
    PLANNING = "planning"
    PREDICTION = "prediction"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    LEARNING = "learning"
    COMPLETE = "complete"
    FAILED = "failed"


class WorkflowStep(BaseModel):
    """Single step in a workflow."""
    step_id: str = Field(..., description="Unique step identifier")
    agent_type: str = Field(..., description="Type of agent (planner, executor, etc.)")
    action: str = Field(..., description="Action to perform")
    status: WorkflowPhase = Field(default=WorkflowPhase.PENDING)
    input_data: Dict = Field(default_factory=dict, description="Input data for step")
    output_data: Dict = Field(default_factory=dict, description="Output from step")
    error_message: Optional[str] = None
    execution_time_ms: float = Field(default=0.0, description="Time to execute step")
    dependencies: list[str] = Field(default_factory=list, description="Dependent steps")
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "agent_type": self.agent_type,
            "action": self.action,
            "status": self.status.value,
            "execution_time_ms": self.execution_time_ms,
            "retry_count": self.retry_count,
            "has_error": self.error_message is not None,
        }


class TaskWorkflow(BaseModel):
    """Complete workflow for a task."""
    workflow_id: str = Field(..., description="Unique workflow identifier")
    task_id: int = Field(..., description="Associated task ID")
    task_type: str = Field(..., description="Type of task")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1-10)")
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_phase: WorkflowPhase = Field(default=WorkflowPhase.PENDING)
    steps: list[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    overall_status: str = Field(default="pending")  # pending, running, success, failed
    success_probability: float = Field(default=0.8, ge=0.0, le=1.0)
    estimated_duration_ms: float = Field(default=0.0)
    actual_duration_ms: float = Field(default=0.0)
    error_count: int = Field(default=0)
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority,
            "current_phase": self.current_phase.value,
            "overall_status": self.overall_status,
            "completion_percentage": self.completion_percentage,
            "success_probability": self.success_probability,
            "actual_duration_ms": self.actual_duration_ms,
        }


class AgentHealthStatus(BaseModel):
    """Health status of an agent."""
    agent_id: str = Field(..., description="Agent identifier")
    agent_type: str = Field(..., description="Type of agent")
    status: str = Field(..., description="operational|idle|error|shutdown")
    uptime_seconds: int = Field(default=0)
    decisions_made: int = Field(default=0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    error_count: int = Field(default=0)
    avg_decision_time_ms: float = Field(default=0.0)
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "health_score": self.health_score,
            "success_rate": self.success_rate,
            "error_count": self.error_count,
        }


class SystemMetrics(BaseModel):
    """System-level metrics from all agents."""
    timestamp: datetime = Field(default_factory=datetime.now)
    total_tasks: int = Field(default=0)
    active_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    failed_tasks: int = Field(default=0)
    avg_task_duration_ms: float = Field(default=0.0)
    avg_task_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    system_health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    active_agents: int = Field(default=0)
    total_errors: int = Field(default=0)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    agent_health_scores: Dict[str, float] = Field(default_factory=dict)
    resource_utilization: Dict[str, float] = Field(default_factory=dict)
    throughput_tasks_per_min: float = Field(default=0.0)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_tasks": self.total_tasks,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_task_success_rate": self.avg_task_success_rate,
            "system_health_score": self.system_health_score,
            "active_agents": self.active_agents,
            "error_rate": self.error_rate,
        }


class ErrorRecord(BaseModel):
    """Record of an error in workflow."""
    error_id: str = Field(..., description="Unique error identifier")
    workflow_id: str = Field(..., description="Workflow where error occurred")
    step_id: str = Field(..., description="Step where error occurred")
    agent_type: str = Field(..., description="Agent type that errored")
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    severity: str = Field(..., description="low|medium|high|critical")
    timestamp: datetime = Field(default_factory=datetime.now)
    is_recoverable: bool = Field(default=True)
    recovery_attempted: bool = Field(default=False)
    recovery_successful: bool = Field(default=False)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "error_id": self.error_id,
            "workflow_id": self.workflow_id,
            "error_type": self.error_type,
            "severity": self.severity,
            "is_recoverable": self.is_recoverable,
            "recovery_successful": self.recovery_successful,
        }


class OrchestratorConfig(BaseModel):
    """Configuration for the orchestrator."""
    max_concurrent_tasks: int = Field(default=10)
    max_retries_per_step: int = Field(default=3)
    step_timeout_seconds: int = Field(default=300)
    workflow_timeout_seconds: int = Field(default=3600)
    heartbeat_interval_seconds: int = Field(default=30)
    metrics_aggregation_interval_seconds: int = Field(default=60)
    enable_auto_recovery: bool = Field(default=True)
    enable_circuit_breaker: bool = Field(default=True)
    circuit_breaker_threshold: int = Field(default=5)  # errors before breaking
    circuit_breaker_timeout_seconds: int = Field(default=60)
