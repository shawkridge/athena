"""Research task models for coordinating multi-agent research orchestration."""

from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Optional
from datetime import datetime
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
