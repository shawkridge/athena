"""Data models for Working Memory layer."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ContentType(str, Enum):
    """Types of content in working memory."""

    VERBAL = "verbal"
    SPATIAL = "spatial"
    EPISODIC = "episodic"
    GOAL = "goal"


class Component(str, Enum):
    """Baddeley's working memory components."""

    PHONOLOGICAL = "phonological"
    VISUOSPATIAL = "visuospatial"
    EPISODIC_BUFFER = "episodic_buffer"
    CENTRAL_EXECUTIVE = "central_executive"


class GoalType(str, Enum):
    """Types of goals."""

    PRIMARY = "primary"
    SUBGOAL = "subgoal"
    MAINTENANCE = "maintenance"


class GoalStatus(str, Enum):
    """Goal status states."""

    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TargetLayer(str, Enum):
    """Target layers for consolidation."""

    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    PROSPECTIVE = "prospective"


@dataclass
class WorkingMemoryItem:
    """Working memory item (7±2 capacity)."""

    id: Optional[int] = None
    project_id: int = 0
    content: str = ""
    content_type: ContentType = ContentType.VERBAL
    component: Component = Component.PHONOLOGICAL
    activation_level: float = 1.0  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    decay_rate: float = 0.1  # Per second
    importance_score: float = 0.5  # 0.0 to 1.0 (affects decay rate)
    embedding: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def current_activation(self) -> float:
        """
        Get current activation (from metadata cache or calculated).

        Returns cached value from database view if available,
        otherwise calculates on the fly.
        """
        if self.metadata and "current_activation" in self.metadata:
            return self.metadata["current_activation"]
        return self.calculate_current_activation()

    def calculate_current_activation(self) -> float:
        """
        Calculate current activation with exponential decay.

        Formula: A(t) = A₀ * e^(-λt)
        where λ = decay_rate * (1 - importance * 0.5)

        Important items decay slower (importance reduces decay rate).
        """
        import math

        time_since_access = (datetime.now() - self.last_accessed).total_seconds()
        adaptive_rate = self.decay_rate * (1 - self.importance_score * 0.5)
        return self.activation_level * math.exp(-adaptive_rate * time_since_access)

    def rehearse(self):
        """Rehearse item (refresh activation to 1.0)."""
        self.activation_level = 1.0
        self.last_accessed = datetime.now()

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "WorkingMemoryItem":
        """Create WorkingMemoryItem from database row.

        Args:
            row: Database row dict from PostgreSQL query

        Returns:
            WorkingMemoryItem instance
        """
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return cls(
            id=row["id"],
            project_id=row["project_id"],
            content=row["content"],
            content_type=ContentType(row["content_type"]),
            component=Component(row["component"]),
            activation_level=row["activation_level"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            decay_rate=row["decay_rate"],
            importance_score=row["importance_score"],
            embedding=row["embedding"],
            metadata=metadata,
        )


@dataclass
class Goal:
    """Active goal managed by Central Executive."""

    id: Optional[int] = None
    project_id: int = 0
    goal_text: str = ""
    goal_type: GoalType = GoalType.PRIMARY
    parent_goal_id: Optional[int] = None
    priority: int = 5  # 1-10 scale
    status: GoalStatus = GoalStatus.ACTIVE
    progress: float = 0.0  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    completion_criteria: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def update_progress(self, progress: float, status: Optional[GoalStatus] = None):
        """Update goal progress and optionally status."""
        self.progress = max(0.0, min(1.0, progress))
        if status:
            self.status = status
        self.updated_at = datetime.now()

        # Auto-complete if progress reaches 1.0
        if self.progress >= 1.0 and self.status == GoalStatus.ACTIVE:
            self.status = GoalStatus.COMPLETED


@dataclass
class AttentionFocus:
    """Current attention focus."""

    id: Optional[int] = None
    project_id: int = 0
    focus_target: str = ""
    focus_type: str = "memory"  # file, concept, task, problem, memory
    attention_weight: float = 1.0
    started_at: datetime = field(default_factory=datetime.now)
    duration_seconds: int = 0


@dataclass
class DecayLogEntry:
    """Decay history entry for validation."""

    id: Optional[int] = None
    wm_id: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    activation_level: float = 1.0
    access_count: int = 0


@dataclass
class ConsolidationRoute:
    """Consolidation routing decision (for ML training)."""

    id: Optional[int] = None
    wm_id: int = 0
    target_layer: TargetLayer = TargetLayer.SEMANTIC
    confidence: Optional[float] = None
    was_correct: Optional[bool] = None
    routed_at: datetime = field(default_factory=datetime.now)
    features: Optional[Dict[str, float]] = None  # Feature vector for ML
