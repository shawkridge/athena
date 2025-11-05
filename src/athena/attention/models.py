"""Data models for attention system."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AttentionType(str, Enum):
    """Type of attention focus."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BACKGROUND = "background"


class InhibitionType(str, Enum):
    """Type of memory inhibition."""
    PROACTIVE = "proactive"  # Old memories suppressed by new
    RETROACTIVE = "retroactive"  # New learning suppresses old
    SELECTIVE = "selective"  # User-directed suppression


class TransitionType(str, Enum):
    """Type of attention transition."""
    VOLUNTARY = "voluntary"  # User-directed
    AUTOMATIC = "automatic"  # Salience-triggered
    INTERRUPTION = "interruption"  # External event
    RETURN = "return"  # Resume previous focus


@dataclass
class SalienceScore:
    """Salience score for a memory."""
    memory_id: int
    memory_layer: str
    salience_score: float
    novelty_score: float
    surprise_score: float
    contradiction_score: float
    detected_at: datetime
    reason: Optional[str] = None
    conflicting_memory_id: Optional[int] = None


@dataclass
class FocusState:
    """Current attention focus state."""
    id: int
    project_id: int
    focus_memory_id: int
    focus_layer: str
    attention_weight: float
    focus_type: AttentionType
    started_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None
    transition_type: Optional[TransitionType] = None
    previous_focus_id: Optional[int] = None


@dataclass
class InhibitionRecord:
    """Memory inhibition record."""
    id: int
    project_id: int
    memory_id: int
    memory_layer: str
    inhibition_strength: float
    inhibition_type: InhibitionType
    reason: Optional[str]
    inhibited_at: datetime
    expires_at: Optional[datetime] = None
