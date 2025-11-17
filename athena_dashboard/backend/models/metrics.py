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
# LLM USAGE METRICS
# ============================================================================

class LLMProviderStats(BaseModel):
    """Statistics for a single LLM provider."""

    provider: str = Field(..., description="claude | openai | ollama | llamacpp | etc")
    model: str = Field(..., description="Model name/version")
    type: str = Field(..., description="cloud | local")
    status: str = Field(..., description="available | unavailable | degraded")
    input_tokens: int = Field(default=0, description="Total input tokens consumed")
    output_tokens: int = Field(default=0, description="Total output tokens generated")
    total_tokens: int = Field(default=0, description="Total tokens used")
    estimated_cost: float = Field(default=0.0, description="Estimated cost in USD")
    requests_count: int = Field(default=0, description="Number of API calls")
    success_count: int = Field(default=0, description="Successful requests")
    error_count: int = Field(default=0, description="Failed requests")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="0.0-1.0")
    avg_latency_ms: float = Field(default=0.0, description="Average response time")
    requests_per_minute: float = Field(default=0.0, description="Current request rate")
    last_used: Optional[datetime] = None


class LLMStats(BaseModel):
    """Overall LLM usage statistics."""

    providers: List[LLMProviderStats] = Field(default_factory=list)
    total_input_tokens: int = Field(default=0)
    total_output_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    total_cost: float = Field(default=0.0, description="Total estimated cost")
    total_requests: int = Field(default=0)
    total_errors: int = Field(default=0)
    overall_success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    total_requests_per_minute: float = Field(default=0.0)
    last_24h_cost: float = Field(default=0.0, description="Cost in last 24 hours")
    last_24h_requests: int = Field(default=0)
    timestamp: datetime = Field(default_factory=datetime.now)


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


# ============================================================================
# PHASE 5: ADAPTIVE LEARNING SYSTEM METRICS
# ============================================================================

class CircuitBreakerStatus(BaseModel):
    """Status of a circuit breaker for service resilience."""

    service_name: str = Field(..., description="e.g., database, llm")
    state: str = Field(..., description="CLOSED | OPEN | HALF_OPEN")
    failure_count: int = Field(..., ge=0)
    failure_threshold: int = Field(..., ge=1)
    last_failure_time: Optional[datetime] = None
    recovery_timeout_seconds: int
    is_available: bool


class ResilientSystemHealth(BaseModel):
    """Health status of resilience layer."""

    database_breaker: CircuitBreakerStatus
    llm_breaker: CircuitBreakerStatus
    local_cache_items: int = Field(..., ge=0)
    local_cache_status: str = Field(..., description="empty | active")
    overall_status: str = Field(..., description="healthy | degraded | critical")


class AdaptiveTaskEstimation(BaseModel):
    """Task estimation metrics from adaptive learning."""

    task_type: str
    samples_collected: int
    avg_estimate_minutes: float = Field(..., ge=0.0)
    avg_actual_minutes: float = Field(..., ge=0.0)
    estimation_accuracy_percent: float = Field(..., ge=0.0, le=100.0)
    success_rate: float = Field(..., ge=0.0, le=1.0)
    trend: str = Field(..., description="improving | stable | degrading")
    confidence_level: str = Field(..., description="low | medium | high")
    last_updated: datetime


class AgentStrategyPerformance(BaseModel):
    """Performance metrics for agent decision strategies."""

    agent_name: str
    strategy_name: str
    use_count: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_execution_time_ms: float = Field(..., ge=0.0)
    recent_trend: str = Field(..., description="improving | stable | degrading")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Based on sample size")
    last_used: Optional[datetime] = None


class AgentLearningFeedback(BaseModel):
    """Feedback loop metrics for agent learning."""

    agent_name: str
    total_decisions_tracked: int
    strategies_tested: int
    best_strategy: str
    best_strategy_rate: float = Field(..., ge=0.0, le=1.0)
    strategies: Dict[str, AgentStrategyPerformance]
    exploration_rate_percent: float = Field(..., ge=0.0, le=100.0)
    learning_curve_quality: str = Field(..., description="steep | moderate | flat")


class LearningOutcomeStatistics(BaseModel):
    """Statistics on tracked learning outcomes."""

    outcomes_tracked: int
    success_count: int
    failure_count: int
    partial_count: int
    error_count: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    most_common_decision: str
    timestamp_range_days: int


class LearningSystemStatus(BaseModel):
    """Complete Phase 5 learning system status."""

    resilience: ResilientSystemHealth
    task_estimation: Dict[str, AdaptiveTaskEstimation] = Field(default_factory=dict)
    agent_feedback: Dict[str, AgentLearningFeedback] = Field(default_factory=dict)
    outcome_stats: LearningOutcomeStatistics
    llm_analysis_enabled: bool
    fallback_usage_percent: float = Field(..., ge=0.0, le=100.0)
    last_outcome_recorded: Optional[datetime] = None
    system_health_score: float = Field(..., ge=0.0, le=1.0)


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
    learning_system_status: Optional[LearningSystemStatus] = None
    recent_events: List[Dict[str, str]] = Field(
        ..., description="Last N events with timestamp, type, status"
    )
    warnings: List[str] = Field(default_factory=list)
    last_updated: datetime
