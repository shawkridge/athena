"""Data models for memory flow routing system."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class MemoryTier(str, Enum):
    """Memory storage tier in the information flow hierarchy."""

    WORKING = "working"  # 7±2 active items (Baddeley limit)
    SESSION = "session"  # ~100 items (warm cache)
    EPISODIC = "episodic"  # Unlimited storage


class ActivationState(BaseModel):
    """State of a memory item in the flow system."""

    event_id: int
    current_activation: float = Field(default=1.0, ge=0.0, le=1.0)
    last_access_time: datetime = Field(default_factory=datetime.now)
    access_count: int = Field(default=0)
    time_created: datetime = Field(default_factory=datetime.now)

    # RIF (Retrieval-Induced Forgetting) tracking
    interference_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    similar_items_count: int = Field(default=0)

    # Consolidation state
    current_tier: MemoryTier = MemoryTier.EPISODIC
    consolidation_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    actionability: float = Field(default=0.5, ge=0.0, le=1.0)

    model_config = ConfigDict(use_enum_values=True)


class ConsolidationRule(BaseModel):
    """Rule for selective consolidation based on activation."""

    min_activation: float = Field(default=0.7)  # Threshold for promotion
    target_tier: MemoryTier  # Where to promote
    action: str  # 'promote', 'maintain', 'decay'
    decay_rate: float = Field(default=0.1, ge=0.0)  # Exponential decay parameter

    model_config = ConfigDict(use_enum_values=True)


class TemporalCluster(BaseModel):
    """Cluster of temporally-related events for consolidated consolidation."""

    cluster_id: int
    event_ids: list[int]
    time_window_start: datetime
    time_window_end: datetime
    mean_importance: float
    mean_actionability: float
    total_activation: float
    cluster_coherence: float = Field(default=0.5, ge=0.0, le=1.0)

    model_config = ConfigDict(use_enum_values=True)


class FlowStatistics(BaseModel):
    """Statistics about memory flow over a period."""

    period_start: datetime
    period_end: datetime
    working_memory_items: int
    session_cache_items: int
    promoted_to_semantic: int
    decayed_items: int
    mean_activation: float
    max_interference: float
    consolidation_rate: float  # Items promoted / total items

    model_config = ConfigDict(use_enum_values=True)
