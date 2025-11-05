"""Temporal chain models for event sequence tracking.

Implements automatic temporal linking and causal inference.
Enables workflow reconstruction and pattern queries.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from ..episodic.models import EpisodicEvent


@dataclass
class TemporalRelation:
    """Relationship between events in time."""

    from_event_id: int
    to_event_id: int
    relation_type: str  # 'immediately_after', 'shortly_after', 'later_after', 'caused'
    strength: float  # Confidence in relation (0.0-1.0)
    inferred_at: datetime

    def __post_init__(self):
        """Validate temporal relation."""
        valid_types = ['immediately_after', 'shortly_after', 'later_after', 'caused']
        if self.relation_type not in valid_types:
            raise ValueError(f"Invalid relation_type: {self.relation_type}")
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"Strength must be in [0.0, 1.0], got {self.strength}")


@dataclass
class EventChain:
    """Sequence of temporally/causally related events."""

    events: List[EpisodicEvent]
    chain_type: str  # 'temporal', 'causal', 'workflow'
    start_time: datetime
    end_time: datetime
    session_id: Optional[str] = None

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

    @property
    def duration_seconds(self) -> float:
        """Total duration of the chain."""
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class CausalPattern:
    """Detected causal pattern in event sequences."""

    pattern_type: str  # 'error_fix', 'tdd_cycle', 'refactor', 'debug_session'
    events: List[EpisodicEvent]
    confidence: float
    description: str

    def __post_init__(self):
        """Validate causal pattern."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass
class TemporalQuery:
    """Query for temporal event patterns."""

    pattern: str  # Pattern description or template
    project_id: int
    lookback_days: int = 30
    min_confidence: float = 0.5

    def __post_init__(self):
        """Validate query."""
        if self.lookback_days < 1:
            raise ValueError("lookback_days must be >= 1")
        if not (0.0 <= self.min_confidence <= 1.0):
            raise ValueError(f"min_confidence must be in [0.0, 1.0]")


@dataclass
class EventSequence:
    """Matched event sequence from temporal query."""

    events: List[EpisodicEvent]
    pattern: str
    match_confidence: float
    temporal_relations: List[TemporalRelation]

    def __len__(self) -> int:
        return len(self.events)

    @property
    def start_time(self) -> datetime:
        """First event timestamp."""
        return self.events[0].timestamp if self.events else datetime.now()

    @property
    def end_time(self) -> datetime:
        """Last event timestamp."""
        return self.events[-1].timestamp if self.events else datetime.now()


@dataclass
class EntityMetadata:
    """Temporal metadata for knowledge graph entities."""

    entity_name: str
    last_access: datetime
    access_count: int
    recency_weight: float  # 0-1, exp decay based on age
    temporal_span_seconds: float  # How long entity has been active
    is_critical: bool  # Part of critical path
    related_entities: List[str]  # Entities in same context
    causality_score: float  # Average causality with related events

    def __post_init__(self):
        """Validate metadata."""
        if not (0.0 <= self.recency_weight <= 1.0):
            raise ValueError(f"recency_weight must be [0-1], got {self.recency_weight}")
        if not (0.0 <= self.causality_score <= 1.0):
            raise ValueError(f"causality_score must be [0-1], got {self.causality_score}")


@dataclass
class TemporalKGRelation:
    """Temporal relationship between entities in KG."""

    from_entity: str
    to_entity: str
    relation_type: str  # 'causes', 'depends_on', 'precedes', 'concurrent'
    causality: float  # 0-1, how likely from_entity caused to_entity
    recency_weight: float  # 0-1, based on when relation occurred
    frequency: float  # 0-1, how often this relation occurs
    dependency: bool  # Whether to_entity requires from_entity
    temporal_score: float  # Combined score: 0.5*causality + 0.3*recency + 0.2*dependency
    inferred_at: datetime

    def __post_init__(self):
        """Validate relation."""
        for score in [self.causality, self.recency_weight, self.frequency, self.temporal_score]:
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"Scores must be [0-1], got {score}")


@dataclass
class KGSynthesisResult:
    """Result of temporal KG synthesis."""

    entities_count: int  # Entities extracted
    relations_count: int  # Relations extracted
    temporal_relations_count: int  # Temporal relationships inferred
    latency_ms: float  # Processing time
    quality_score: float  # 0-1, validation quality
