"""Consciousness measurement and analysis module.

Implements metrics for assessing consciousness-relevant properties based on
contemporary consciousness theories (GWT, IIT, HOT, Predictive Processing).

Provides:
- 6 consensus consciousness indicators (Phase 1A)
- Real-time consciousness scoring (Phase 1B)
- Φ (integrated information) calculation framework (Phase 2)
- Phenomenal properties: qualia, emotions, embodiment (Phase 3)
- Validation against academic literature (2024-2025)

Status: Phase 3 complete
- Global Workspace Indicator ✅
- Information Integration Indicator ✅
- Selective Attention Indicator ✅
- Working Memory Indicator ✅
- Meta-Cognition Indicator ✅
- Temporal Continuity Indicator ✅
- Consciousness Metrics System ✅
- Φ (Integrated Information) Calculation ✅
- Phenomenal Properties (Qualia, Emotions, Embodiment) ✅

Next: Phase 4 - Frontend visualization pages
Then: Phase 5 - Validation experiments
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
from .phi_calculation import (
    PhiResult,
    InformationTheory,
    PhiCalculator,
    IntegratedInformationSystem,
)
from .phenomenal import (
    Quale,
    EmotionType,
    EmotionalState,
    EmbodiedState,
    BodyAwareness,
    QualiaGenerator,
    EmotionSystem,
    EmbodimentSystem,
    PhenomenalConsciousness,
)
from .validation import (
    ExperimentResult,
    ValidationExperiments,
)

__all__ = [
    # Indicators
    "ConsciousnessIndicators",
    "IndicatorScore",
    "GlobalWorkspaceIndicator",
    "InformationIntegrationIndicator",
    "SelectiveAttentionIndicator",
    "WorkingMemoryIndicator",
    "MetaCognitionIndicator",
    "TemporalContinuityIndicator",
    # Metrics
    "ConsciousnessMetrics",
    "ConsciousnessScore",
    # Φ Calculation
    "PhiResult",
    "InformationTheory",
    "PhiCalculator",
    "IntegratedInformationSystem",
    # Phenomenal Properties
    "Quale",
    "EmotionType",
    "EmotionalState",
    "EmbodiedState",
    "BodyAwareness",
    "QualiaGenerator",
    "EmotionSystem",
    "EmbodimentSystem",
    "PhenomenalConsciousness",
    # Validation
    "ExperimentResult",
    "ValidationExperiments",
]
