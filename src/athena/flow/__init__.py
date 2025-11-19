"""Memory flow routing system.

Manages information flow across episodic, session cache, and semantic layers
using neuroscience-inspired dual-process consolidation with temporal decay,
interference effects, and selective promotion.
"""

from .router import MemoryFlowRouter
from .models import ActivationState, MemoryTier, ConsolidationRule
from .hooks_integration import FlowHooksHandler, get_flow_hooks_handler
from .episodic_integration import FlowAwareEpisodicStore, wrap_episodic_store_with_flow

__all__ = [
    "MemoryFlowRouter",
    "ActivationState",
    "MemoryTier",
    "ConsolidationRule",
    "FlowHooksHandler",
    "get_flow_hooks_handler",
    "FlowAwareEpisodicStore",
    "wrap_episodic_store_with_flow",
]
