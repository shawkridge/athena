"""Data models for Hebbian learning."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AccessRecord:
    """Record of memory access for co-occurrence detection."""
    id: int
    project_id: int
    memory_id: int
    memory_layer: str
    accessed_at: datetime
    activation_level: float


@dataclass
class HebbianStats:
    """Statistics for Hebbian learning process."""
    id: int
    project_id: int
    total_accesses: int
    links_created: int
    links_strengthened: int
    links_weakened: int
    avg_link_strength: float
    last_learning_at: datetime
