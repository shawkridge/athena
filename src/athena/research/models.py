"""Research task models for coordinating multi-agent research orchestration."""

from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Optional
import time


class ResearchStatus(str, Enum):
    """Status of a research task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Status of an individual research agent."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResearchTask(BaseModel):
    """Represents a research task orchestration."""

    id: Optional[int] = None
    topic: str = Field(..., description="Research topic or question")
    status: ResearchStatus = ResearchStatus.PENDING
    project_id: Optional[int] = None
    created_at: int = Field(default_factory=lambda: int(time.time()))
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    findings_count: int = 0
    entities_created: int = 0
    relations_created: int = 0
    notes: str = Field(default="")
    agent_results: dict = Field(default_factory=dict)  # {agent_name: finding_count, ...}

    model_config = ConfigDict(use_enum_values=True)


class ResearchFinding(BaseModel):
    """A single research finding."""

    id: Optional[int] = None
    research_task_id: int
    source: str = Field(..., description="Source of finding (arXiv, GitHub, etc.)")
    title: str = Field(..., description="Finding title")
    summary: str = Field(..., description="Summary of finding")
    url: Optional[str] = None
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    stored_to_memory: bool = False
    memory_id: Optional[int] = None

    model_config = ConfigDict(use_enum_values=True)


class AgentProgress(BaseModel):
    """Progress tracking for individual agents."""

    id: Optional[int] = None
    research_task_id: int
    agent_name: str = Field(..., description="Name of the research agent")
    status: AgentStatus = AgentStatus.PENDING
    findings_count: int = 0
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class FeedbackType(str, Enum):
    """Types of research feedback."""

    QUERY_REFINEMENT = "query_refinement"
    SOURCE_EXCLUSION = "source_exclusion"
    SOURCE_FOCUS = "source_focus"
    AGENT_FOCUS = "agent_focus"
    RESULT_FILTERING = "result_filtering"
    QUALITY_THRESHOLD = "quality_threshold"


class ResearchFeedback(BaseModel):
    """User feedback for research task refinement."""

    id: Optional[int] = None
    research_task_id: int
    feedback_type: FeedbackType = FeedbackType.QUERY_REFINEMENT
    content: str = Field(..., description="Feedback content")
    agent_target: Optional[str] = None
    created_at: int = Field(default_factory=lambda: int(__import__("time").time()))
    parent_feedback_id: Optional[int] = None
    applied: bool = False
    applied_at: Optional[int] = None

    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# PHASE 3.3: CONSOLIDATION MODELS
# ============================================================================


class ResearchPatternType(str, Enum):
    """Types of research patterns extracted from findings."""

    SOURCE_CREDIBILITY = "source_credibility"
    AGENT_EXPERTISE = "agent_expertise"
    CROSS_VALIDATION = "cross_validation"
    TEMPORAL_TREND = "temporal_trend"
    DOMAIN_SOURCE_FIT = "domain_source_fit"
    QUALITY_DISTRIBUTION = "quality_distribution"
    COVERAGE_COMPLETENESS = "coverage_completeness"
    REDUNDANCY_PATTERN = "redundancy_pattern"
    FEEDBACK_IMPACT = "feedback_impact"
    DISCOVERY_VELOCITY = "discovery_velocity"
    AGENT_COLLABORATION = "agent_collaboration"


class ResearchPattern(BaseModel):
    """Extracted pattern from research findings."""

    id: Optional[int] = None
    task_id: int
    pattern_type: ResearchPatternType
    pattern_content: str = Field(..., description="Pattern description")
    confidence: float = Field(ge=0.0, le=1.0, description="Pattern confidence (0-1)")
    metrics: dict = Field(default_factory=dict, description="Associated metrics")
    source_findings: list[int] = Field(default_factory=list, description="Finding IDs")
    finding_count: int = 0
    created_at: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)


class AgentDomainExpertise(BaseModel):
    """Learned domain expertise for an agent."""

    id: Optional[int] = None
    agent_name: str
    domain: str
    total_findings: int = 0
    avg_credibility: float = 0.0
    successful_tasks: int = 0
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_updated: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)


class SourceDomainCredibility(BaseModel):
    """Source credibility metrics per domain."""

    id: Optional[int] = None
    source: str
    domain: str
    avg_credibility: float = Field(ge=0.0, le=1.0)
    finding_count: int
    cross_validation_rate: Optional[float] = None
    temporal_trend: Optional[float] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_updated: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)


class QualityThreshold(BaseModel):
    """Learned quality thresholds per domain."""

    id: Optional[int] = None
    domain: str
    threshold_optimal: float = Field(default=0.75, ge=0.0, le=1.0)
    threshold_strict: float = Field(default=0.85, ge=0.0, le=1.0)
    threshold_lenient: float = Field(default=0.60, ge=0.0, le=1.0)
    findings_tested: int = 0
    retention_rate_optimal: Optional[float] = None
    last_updated: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)


class SearchStrategy(BaseModel):
    """Learned search strategy for a domain."""

    id: Optional[int] = None
    name: str
    domain: str
    description: Optional[str] = None
    recommended_sources: list[str] = Field(default_factory=list)
    excluded_sources: list[str] = Field(default_factory=list)
    expected_quality: float = Field(default=0.8, ge=0.0, le=1.0)
    expected_findings_per_query: int = Field(default=50)
    success_count: int = 0
    failure_count: int = 0
    created_from_patterns: list[int] = Field(default_factory=list)
    procedure_id: Optional[int] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_updated: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)


class ResearchGraphEntity(BaseModel):
    """Entity extracted from research findings."""

    id: Optional[int] = None
    task_id: int
    entity_name: str
    entity_type: Optional[str] = None
    mentioned_in_findings: list[int] = Field(default_factory=list)
    frequency: int = 1
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)


class ResearchGraphRelation(BaseModel):
    """Relation between entities from research findings."""

    id: Optional[int] = None
    task_id: int
    source_entity: str
    relation_type: str
    target_entity: str
    strength: float = Field(default=0.8, ge=0.0, le=1.0)
    source_findings: list[int] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)


class ResearchConsolidationRun(BaseModel):
    """Metadata for a research consolidation run."""

    id: Optional[int] = None
    task_id: int
    started_at: int = Field(default_factory=lambda: int(time.time()))
    completed_at: Optional[int] = None
    status: str = Field(default="running")  # running|completed|failed
    patterns_extracted: int = 0
    procedures_created: int = 0
    entities_created: int = 0
    relations_created: int = 0
    expertise_updates: int = 0
    strategy_improvements: int = 0
    error_message: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)
