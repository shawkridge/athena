"""Verification layer - explicit quality gates for all memory operations.

This layer implements the "Verify Output" phase of the agentic loop,
making verification a first-class architectural concern.

Key components:
- VerificationGateway: Main gateway for all verification
- Gate types: Grounding, Confidence, Consistency, Soundness, Minimality, Coherence, Efficiency
- Remediation: Handlers for fixing violations
- Observability: Full decision logging and health metrics
"""

from .gateway import (
    VerificationGateway,
    Gate,
    GateResult,
    GateViolation,
    GateSeverity,
    GateType,
    GroundingGate,
    ConfidenceGate,
    ConsistencyGate,
    SoundnessGate,
    MinimalityGate,
    CoherenceGate,
    EfficiencyGate,
)

from .observability import (
    VerificationObserver,
    DecisionOutcome,
    ViolationPattern,
)

from .feedback_metrics import (
    FeedbackMetricsCollector,
    MetricSnapshot,
    MetricTrend,
)

__all__ = [
    "VerificationGateway",
    "Gate",
    "GateResult",
    "GateViolation",
    "GateSeverity",
    "GateType",
    "GroundingGate",
    "ConfidenceGate",
    "ConsistencyGate",
    "SoundnessGate",
    "MinimalityGate",
    "CoherenceGate",
    "EfficiencyGate",
    "VerificationObserver",
    "DecisionOutcome",
    "ViolationPattern",
    "FeedbackMetricsCollector",
    "MetricSnapshot",
    "MetricTrend",
]
