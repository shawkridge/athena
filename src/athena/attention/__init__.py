"""Attention system for cognitive memory architecture."""

from .salience import SalienceTracker
from .focus import AttentionFocus
from .inhibition import AttentionInhibition
from .models import (
    SalienceScore,
    FocusState,
    InhibitionRecord,
    AttentionType,
    InhibitionType,
)

__all__ = [
    "SalienceTracker",
    "AttentionFocus",
    "AttentionInhibition",
    "SalienceScore",
    "FocusState",
    "InhibitionRecord",
    "AttentionType",
    "InhibitionType",
]
