"""Data models for spreading activation network."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class LinkType(str, Enum):
    """Type of associative link."""
    SEMANTIC = "semantic"  # Meaning-based association
    TEMPORAL = "temporal"  # Time-based co-occurrence
    CAUSAL = "causal"  # Cause-effect relationship
    SIMILARITY = "similarity"  # Feature similarity


@dataclass
class AssociationLink:
    """Link between two memories in the association network."""
    id: int
    project_id: int
    from_memory_id: int
    to_memory_id: int
    from_layer: str
    to_layer: str
    link_strength: float
    co_occurrence_count: int
    created_at: datetime
    last_strengthened: datetime
    link_type: LinkType


@dataclass
class ActivatedNode:
    """Node with current activation level."""
    memory_id: int
    memory_layer: str
    activation_level: float
    hop_distance: int
    source_activation_id: Optional[int] = None


@dataclass
class PrimedMemory:
    """Memory with temporal priming boost."""
    memory_id: int
    memory_layer: str
    priming_strength: float
    primed_at: datetime
    expires_at: datetime


@dataclass
class NetworkNode:
    """Node in the association network with metadata."""
    memory_id: int
    layer: str
    neighbors: list['AssociationLink']
    activation: float = 0.0
