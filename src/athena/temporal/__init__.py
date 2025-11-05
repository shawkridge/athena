"""Temporal chain system for event sequence tracking.

Implements automatic temporal linking and causal inference.
Enables workflow reconstruction and pattern queries.
"""

from .chains import (
    calculate_causal_strength,
    create_temporal_chains,
    create_temporal_relations,
    detect_causal_patterns,
    infer_causal_relations,
    is_likely_causal,
)
from .models import (
    CausalPattern,
    EventChain,
    EventSequence,
    TemporalQuery,
    TemporalRelation,
)
from .queries import query_by_temporal_pattern

__all__ = [
    # Models
    "TemporalRelation",
    "EventChain",
    "CausalPattern",
    "TemporalQuery",
    "EventSequence",
    # Chain creation
    "create_temporal_chains",
    "create_temporal_relations",
    "infer_causal_relations",
    "is_likely_causal",
    "calculate_causal_strength",
    "detect_causal_patterns",
    # Queries
    "query_by_temporal_pattern",
]
