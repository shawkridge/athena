"""Pydantic models for metrics and API responses."""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# HOOK EXECUTION METRICS
# ============================================================================

class HookMetrics(BaseModel):
    """Metrics for a single hook execution."""

    hook_name: str
    status: str = Field(..., description="active | error | idle")
    execution_count: int = Field(..., description="Total executions this session")
    avg_latency_ms: float = Field(..., description="Average execution time")
    p95_latency_ms: float = Field(..., description="95th percentile latency")
    p99_latency_ms: float = Field(..., description="99th percentile latency")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="0.0-1.0")
    error_count: int = Field(..., description="Number of failures")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="0.0-1.0")
    last_execution: datetime
    last_error: Optional[datetime] = None
    agents_invoked: List[str] = Field(default_factory=list)


class HookPerformancePoint(BaseModel):
    """Single data point in hook performance history."""

    timestamp: datetime
    hook_name: str
    latency_ms: float
    success: bool
    agent_count: int


class AgentInvocationStats(BaseModel):
    """Statistics for agent invocations."""

    agent_name: str
    invocation_count: int
    priority: int
    success_rate: float
    avg_duration_ms: float


# ============================================================================
# MEMORY SYSTEM METRICS
# ============================================================================

class MemoryMetrics(BaseModel):
    """Overall memory system health metrics."""

    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality 0.0-1.0")
    compression_ratio: float = Field(..., ge=0.0, le=1.0, description="Compression efficiency")
    recall_accuracy: float = Field(..., ge=0.0, le=1.0, description="Recall accuracy")
    consistency: float = Field(..., ge=0.0, le=1.0, description="Consistency score")
    density: float = Field(..., ge=0.0, le=1.0, description="Information density")
    event_count: int = Field(..., description="Total episodic events")
    semantic_count: int = Field(..., description="Semantic memories stored")
    procedure_count: int = Field(..., description="Procedures extracted")
    gap_count: int = Field(..., description="Knowledge gaps identified")
    last_consolidation: datetime
    consolidation_in_progress: bool = False


class ConsolidationProgress(BaseModel):
    """Consolidation pipeline progress."""

    status: str = Field(..., description="idle | running | completed")
    events_processed: int
    events_total: int
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    patterns_extracted: int
    quality_score: float = Field(..., ge=0.0, le=1.0)
    duration_seconds: Optional[float] = None
    estimated_completion: Optional[datetime] = None


class DomainCoverage(BaseModel):
    """Coverage of knowledge per domain."""

    domain: str
    coverage_percent: float = Field(..., ge=0.0, le=100.0)
    event_count: int
    procedure_count: int
    expertise_level: str = Field(..., description="novice | intermediate | expert")


class KnowledgeGap(BaseModel):
    """Identified knowledge gap or contradiction."""

    gap_id: str
    gap_type: str = Field(..., description="contradiction | uncertainty | missing_knowledge")
    domain: str
    description: str
    severity: str = Field(..., description="low | medium | high | critical")
    discovered_at: datetime


# ============================================================================
# COGNITIVE LOAD METRICS
# ============================================================================

class WorkingMemoryItem(BaseModel):
    """Item currently in working memory."""

    item_id: str
    content: str
    item_type: str = Field(..., description="goal | fact | procedure | context")
    freshness_percent: float = Field(..., ge=0.0, le=100.0, description="0-100%")
    decay_rate_percent_per_hour: float
    time_added: datetime
    priority: int = Field(..., ge=1, le=10)


class CognitiveLoad(BaseModel):
    """Cognitive load and working memory status."""

    current_load: int = Field(..., ge=0, le=7, description="Current items (0-7)")
    max_capacity: int = Field(default=7, description="Maximum capacity")
    utilization_percent: float = Field(..., ge=0.0, le=100.0)
    active_items: List[WorkingMemoryItem]
    avg_decay_rate_percent: float = Field(..., description="% per hour")
    warnings: List[str] = Field(default_factory=list)
    status: str = Field(..., description="healthy | warning | critical")


class LoadTrendPoint(BaseModel):
    """Load data point for trending."""

    timestamp: datetime
    load: int
    utilization_percent: float
    warning_level: str = Field(..., description="none | warning | critical")


# ============================================================================
# TASK & PROJECT METRICS
# ============================================================================

class ProjectStatus(BaseModel):
    """Status of a single project."""

    project_id: int
    project_name: str
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    task_count: int
    completed_tasks: int
    active_goals: int
    health_score: float = Field(..., ge=0.0, le=1.0)
    status: str = Field(..., description="on_track | at_risk | blocked")
    last_update: datetime


class GoalStatus(BaseModel):
    """Status of a single goal."""

    goal_id: int
    goal_name: str
    project_id: int
    priority: int = Field(..., ge=1, le=10)
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    deadline: Optional[datetime] = None
    status: str = Field(..., description="pending | in_progress | completed | blocked")
    blocker_count: int
    dependencies: List[int] = Field(default_factory=list)


class TaskStatus(BaseModel):
    """Status of a single task."""

    task_id: int
    task_name: str
    goal_id: int
    project_id: int
    estimated_hours: float
    actual_hours: Optional[float] = None
    status: str = Field(..., description="pending | in_progress | completed | failed")
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    blocker_count: int
    created_at: datetime
    due_date: Optional[datetime] = None


class Milestone(BaseModel):
    """Project milestone."""

    milestone_id: int
    milestone_name: str
    project_id: int
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = Field(..., description="pending | in_progress | completed | missed")


class TaskMetrics(BaseModel):
    """Overall task and project metrics."""

    active_goals: int
    active_tasks: int
    total_projects: int
    completion_rate: float = Field(..., ge=0.0, le=1.0)
    on_time_rate: float = Field(..., ge=0.0, le=1.0)
    blocker_count: int
    milestone_progress: float = Field(..., ge=0.0, le=100.0)
    estimated_vs_actual_ratio: float = Field(..., description="Actual/Estimated hours")
    projects: List[ProjectStatus]
    active_goals_list: List[GoalStatus]


# ============================================================================
# LEARNING & ANALYTICS METRICS
# ============================================================================

class StrategyEffectiveness(BaseModel):
    """Effectiveness of a consolidation or execution strategy."""

    strategy_name: str
    usage_count: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_quality_improvement: float = Field(..., description="Quality delta")
    avg_duration_seconds: float


class Procedure(BaseModel):
    """Reusable procedure."""

    procedure_id: int
    procedure_name: str
    description: str
    usage_count: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    last_used: Optional[datetime] = None
    effectiveness_score: float = Field(..., ge=0.0, le=1.0)


class LearningMetrics(BaseModel):
    """Learning and knowledge metrics."""

    encoding_efficiency: float = Field(..., ge=0.0, le=1.0, description="% of events consolidated")
    patterns_extracted: int = Field(..., description="Total patterns discovered")
    patterns_this_session: int
    procedure_count: int
    procedure_reuse_rate: float = Field(..., ge=0.0, le=1.0)
    strategy_effectiveness: Dict[str, StrategyEffectiveness]
    knowledge_gaps_remaining: int
    knowledge_gaps_resolved_this_week: int
    learning_velocity: float = Field(..., description="Improvements per week")
    top_procedures: List[Procedure]


class LearningTrendPoint(BaseModel):
    """Learning metric data point for trending."""

    timestamp: datetime
    quality_score: float = Field(..., ge=0.0, le=1.0)
    patterns_extracted: int
    procedures_used: int


# ============================================================================
# DASHBOARD OVERVIEW
# ============================================================================

class SystemHealth(BaseModel):
    """Overall system health status."""

    quality_score: float = Field(..., ge=0.0, le=1.0)
    quality_status: str = Field(..., description="excellent | good | fair | poor")
    load_status: str = Field(..., description="healthy | warning | critical")
    hooks_status: str = Field(..., description="all_active | degraded | failed")
    database_status: str = Field(..., description="healthy | warning | error")
    last_update: datetime


class DashboardOverview(BaseModel):
    """Complete dashboard overview."""

    system_health: SystemHealth
    memory_metrics: MemoryMetrics
    cognitive_load: CognitiveLoad
    hook_count: int
    hooks_active: int
    consolidation: ConsolidationProgress
    active_goals: int
    active_tasks: int
    completion_rate: float = Field(..., ge=0.0, le=1.0)
    learning_velocity: float
    recent_events: List[Dict[str, str]] = Field(
        ..., description="Last N events with timestamp, type, status"
    )
    warnings: List[str] = Field(default_factory=list)
    last_updated: datetime
