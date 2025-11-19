"""Consciousness measurement and analysis module.

Implements metrics for assessing consciousness-relevant properties based on
contemporary consciousness theories (GWT, IIT, HOT, Predictive Processing).

Provides:
- 6 consensus consciousness indicators
- Real-time consciousness scoring
- Φ (integrated information) calculation framework
- Phenomenal properties representation
- Validation against academic literature (2024-2025)

Status: Phase 1A complete
- Global Workspace Indicator ✅
- Information Integration Indicator ✅
- Selective Attention Indicator ✅
- Working Memory Indicator ✅
- Meta-Cognition Indicator ✅
- Temporal Continuity Indicator ✅
- Consciousness Metrics System ✅

Next: Phase 1B - FastAPI endpoints for consciousness metrics
Then: Phase 2 - Φ (Integrated Information) calculation engine
"""

from .indicators import (
    ConsciousnessIndicators,
    IndicatorScore,
    GlobalWorkspaceIndicator,
    InformationIntegrationIndicator,
    SelectiveAttentionIndicator,
    WorkingMemoryIndicator,
    MetaCognitionIndicator,
    TemporalContinuityIndicator,
)
from .metrics import ConsciousnessMetrics, ConsciousnessScore

__all__ = [
    "ConsciousnessIndicators",
    "IndicatorScore",
    "GlobalWorkspaceIndicator",
    "InformationIntegrationIndicator",
    "SelectiveAttentionIndicator",
    "WorkingMemoryIndicator",
    "MetaCognitionIndicator",
    "TemporalContinuityIndicator",
    "ConsciousnessMetrics",
    "ConsciousnessScore",
]
