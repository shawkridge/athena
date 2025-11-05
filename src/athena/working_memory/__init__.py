"""
Working Memory Layer (Layer 0-1) - Baddeley's Model

Implements Baddeley & Hitch's (1974) Working Memory model with:
- Central Executive: Attention control and goal management
- Phonological Loop: Verbal/linguistic temporary storage (7±2 items)
- Visuospatial Sketchpad: Spatial/visual information
- Episodic Buffer: Integration between WM and LTM

Key Features:
- Capacity constraint: 7±2 items (Miller's law)
- Exponential decay: A(t) = A₀ * e^(-λt)
- Adaptive decay rates: Important items decay slower
- ML-based consolidation routing
"""

from .models import (
    WorkingMemoryItem,
    Goal,
    AttentionFocus,
    ConsolidationRoute
)

from .central_executive import CentralExecutive
from .phonological_loop import PhonologicalLoop
from .visuospatial_sketchpad import VisuospatialSketchpad
from .episodic_buffer import EpisodicBuffer
from .consolidation_router import ConsolidationRouter

__all__ = [
    # Models
    'WorkingMemoryItem',
    'Goal',
    'AttentionFocus',
    'ConsolidationRoute',

    # Components
    'CentralExecutive',
    'PhonologicalLoop',
    'VisuospatialSketchpad',
    'EpisodicBuffer',
    'ConsolidationRouter',
]
