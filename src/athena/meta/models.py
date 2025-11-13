"""Data models for meta-memory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ExpertiseLevel(str, Enum):
    """Expertise levels for domains."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class DomainCoverage(BaseModel):
    """Coverage tracking for a knowledge domain."""

    id: Optional[int] = None
    domain: str  # react|authentication|testing|graphql|etc
    category: str  # technology|pattern|project-area|skill

    # Coverage metrics
    memory_count: int = 0
    episodic_count: int = 0
    procedural_count: int = 0
    entity_count: int = 0

    # Quality metrics
    avg_confidence: float = 0.0
    avg_usefulness: float = 0.0
    last_updated: Optional[datetime] = None

    # Gap analysis
    gaps: list[str] = Field(default_factory=list)  # Identified knowledge gaps
    strength_areas: list[str] = Field(default_factory=list)  # Strong areas

    # Metadata
    first_encounter: Optional[datetime] = None
    expertise_level: ExpertiseLevel = ExpertiseLevel.BEGINNER

    model_config = ConfigDict(use_enum_values=True)


class MemoryQuality(BaseModel):
    """Quality tracking for a memory."""

    memory_id: int
    memory_layer: str  # semantic|episodic|procedural|prospective|graph

    # Usage metrics
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    useful_count: int = 0

    # Quality scores
    usefulness_score: float = 0.0  # 0-1
    confidence: float = 1.0  # 0-1
    relevance_decay: float = 1.0  # 0-1

    # Provenance
    source: str = "user"  # user|inferred|learned|imported
    verified: bool = False


class KnowledgeTransfer(BaseModel):
    """Cross-project knowledge transfer tracking."""

    id: Optional[int] = None
    from_project_id: int
    to_project_id: int
    knowledge_item_id: int
    knowledge_layer: str
    transferred_at: datetime = Field(default_factory=datetime.now)
    applicability_score: float = 0.0  # How well it transferred


class AttentionItem(BaseModel):
    """An item in the attention budget (working memory)."""

    id: Optional[int] = None
    project_id: int
    item_type: str  # goal|task|entity|memory|observation
    item_id: int  # ID in respective layer

    # Salience tracking
    salience_score: float = 0.5  # 0-1, computed from recency + importance + relevance
    importance: float = 0.5  # 0-1, user-defined priority
    relevance: float = 0.5  # 0-1, to current task/goal
    recency: float = 0.5  # 0-1, recent access boosts this

    # Access tracking
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    activation_level: float = 0.0  # 0-1, active items have higher activation

    # Metadata
    added_at: datetime = Field(default_factory=datetime.now)
    context: str = ""  # Why this item is in focus


class WorkingMemory(BaseModel):
    """Working memory state (7±2 items in focus)."""

    id: Optional[int] = None
    project_id: int

    # Capacity constraints (Baddeley's model)
    capacity: int = 7  # Central capacity
    capacity_variance: int = 2  # ±2 items
    current_load: int = 0  # Current number of items
    cognitive_load: float = 0.0  # 0-1 percentage of capacity used

    # Item management
    active_items: list[int] = Field(default_factory=list)  # IDs of AttentionItem
    total_slots_used: int = 0

    # Saturation and overflow handling
    overflow_threshold: float = 0.85  # Warn when >85% capacity
    overflow_items: list[int] = Field(default_factory=list)  # Items bumped out

    # Temporal dynamics
    last_consolidated: Optional[datetime] = None
    consolidation_interval_hours: int = 8  # Sleep-like consolidation every 8 hours

    # Metrics
    item_decay_rate: float = 0.1  # How fast items lose activation (per hour)
    refresh_threshold: float = 0.3  # Refresh items that fall below this

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


class AttentionBudget(BaseModel):
    """Allocates attention resources across focus areas."""

    id: Optional[int] = None
    project_id: int

    # Budget allocation (must sum to 1.0)
    current_focus: str  # "coding"|"debugging"|"learning"|"planning"|"reviewing"
    focus_allocation: dict[str, float] = Field(
        default_factory=lambda: {
            "coding": 0.3,
            "debugging": 0.2,
            "learning": 0.15,
            "planning": 0.2,
            "reviewing": 0.15,
        }
    )

    # Real-time attention metrics
    current_focus_level: float = 0.0  # 0-1 how focused we are
    context_switches: int = 0  # Number of switches in current session
    context_switch_cost: float = 0.0  # Productivity loss from switching

    # Energy and fatigue
    mental_energy: float = 1.0  # 0-1, decreases throughout day
    fatigue_level: float = 0.0  # 0-1, increases with intensity
    optimal_session_length_minutes: int = 90  # Pomodoro-like

    # Distraction tracking
    distraction_sources: list[str] = Field(default_factory=list)
    distraction_level: float = 0.0  # 0-1

    # Metadata
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    total_focused_time_minutes: int = 0

    model_config = ConfigDict(use_enum_values=True)
