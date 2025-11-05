"""Data models for consolidation system."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConsolidationType(str, Enum):
    """Types of consolidation runs."""

    SCHEDULED = "scheduled"
    MANUAL = "manual"
    TRIGGERED = "triggered"


class ConsolidationRun(BaseModel):
    """Record of a consolidation run."""

    id: Optional[int] = None
    project_id: Optional[int] = None  # None for global consolidation
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "running"  # running|completed|failed

    # What was done
    memories_scored: int = 0
    memories_pruned: int = 0
    patterns_extracted: int = 0
    conflicts_resolved: int = 0

    # Quality improvements
    avg_quality_before: Optional[float] = None
    avg_quality_after: Optional[float] = None

    # Metadata
    consolidation_type: ConsolidationType = ConsolidationType.SCHEDULED
    notes: Optional[str] = None

    class Config:
        use_enum_values = True


class PatternType(str, Enum):
    """Types of extracted patterns."""

    WORKFLOW = "workflow"
    ANTI_PATTERN = "anti-pattern"
    BEST_PRACTICE = "best-practice"
    RELATIONSHIP = "relationship"


class ExtractedPattern(BaseModel):
    """Pattern extracted from episodic events."""

    id: Optional[int] = None
    consolidation_run_id: int
    pattern_type: PatternType
    pattern_content: str
    confidence: float = 0.0
    occurrences: int = 1

    # Source events
    source_events: list[int] = Field(default_factory=list)

    # Actions taken
    created_procedure: bool = False
    created_semantic_memory: bool = False
    updated_entity: bool = False

    class Config:
        use_enum_values = True


class ConflictType(str, Enum):
    """Types of memory conflicts."""

    CONTRADICTION = "contradiction"
    DUPLICATION = "duplication"
    INCONSISTENCY = "inconsistency"


class ConflictSeverity(str, Enum):
    """Severity of conflicts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryConflict(BaseModel):
    """Conflict between memories."""

    id: Optional[int] = None
    discovered_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    status: str = "pending"  # pending|resolved|ignored

    # Conflicting items
    item1_layer: str
    item1_id: int
    item2_layer: str
    item2_id: int

    # Conflict details
    conflict_type: ConflictType
    description: Optional[str] = None

    # Resolution
    resolution_strategy: Optional[str] = None  # timestamp_precedence|merge|user_input|keep_both
    resolution_notes: Optional[str] = None

    # Metadata
    severity: ConflictSeverity = ConflictSeverity.MEDIUM

    class Config:
        use_enum_values = True
