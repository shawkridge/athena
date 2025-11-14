"""Unified verification gateway for all memory operations.

This module implements explicit quality gates that validate memory operations
before they commit to storage. It's the enforcement layer for the diagram's
"Verify Output" phase - making verification a first-class architectural concern.

Architecture:
- Each operation (recall, remember, consolidate, etc.) passes through gates
- Gates check: grounding, confidence, consistency, soundness, minimality
- Failed gates can trigger remediation (re-run, validate, adjust confidence)
- All decisions are observable and learnable
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class GateSeverity(Enum):
    """Severity levels for gate violations."""
    INFO = "info"           # Informational, no action needed
    WARNING = "warning"     # Minor issue, could be handled
    ERROR = "error"         # Major issue, should be escalated
    CRITICAL = "critical"   # Must be resolved before proceeding


class GateType(Enum):
    """Types of verification gates."""
    GROUNDING = "grounding"         # Is it grounded in source data?
    CONFIDENCE = "confidence"       # Is confidence calibrated?
    CONSISTENCY = "consistency"     # Is it consistent with memory?
    SOUNDNESS = "soundness"         # Is reasoning valid?
    MINIMALITY = "minimality"       # Is it minimal/non-redundant?
    COMPLETENESS = "completeness"   # Does it cover all requirements?
    COHERENCE = "coherence"         # Is it coherent with existing knowledge?
    EFFICIENCY = "efficiency"       # Is it efficient/performant?


@dataclass
class GateViolation:
    """A single gate violation."""
    gate_type: GateType
    severity: GateSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    remediation_hints: List[str] = field(default_factory=list)


@dataclass
class GateResult:
    """Result of gate verification."""
    operation_id: str
    operation_type: str         # "recall", "remember", "consolidate", etc.
    passed: bool                # All critical gates passed?
    violations: List[GateViolation] = field(default_factory=list)
    warnings: List[GateViolation] = field(default_factory=list)
    confidence_score: float = 0.0  # Overall confidence (0.0-1.0)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def has_critical_violations(self) -> bool:
        """Check if any critical violations exist."""
        return any(v.severity == GateSeverity.CRITICAL for v in self.violations)

    def has_errors(self) -> bool:
        """Check if any errors exist."""
        return any(v.severity == GateSeverity.ERROR for v in self.violations)


class Gate(ABC):
    """Base class for verification gates."""

    def __init__(self, gate_type: GateType, severity_threshold: GateSeverity = GateSeverity.ERROR):
        self.gate_type = gate_type
        self.severity_threshold = severity_threshold
        self.execution_count = 0
        self.success_count = 0
        self.last_executed = None

    def verify(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """
        Verify operation data.

        Returns None if passes, GateViolation if fails.
        """
        self.execution_count += 1
        self.last_executed = datetime.now()

        violation = self._check(operation_data)

        if violation is None:
            self.success_count += 1
        else:
            logger.warning(f"Gate {self.gate_type.value} violation: {violation.message}")

        return violation

    @abstractmethod
    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """
        Implement gate-specific check.
        Must be overridden by subclasses.
        """
        pass

    def get_success_rate(self) -> float:
        """Get success rate of this gate."""
        if self.execution_count == 0:
            return 1.0
        return self.success_count / self.execution_count


class GroundingGate(Gate):
    """Verify that outputs are grounded in source data."""

    def __init__(self, min_grounding_score: float = 0.5):
        super().__init__(GateType.GROUNDING)
        self.min_grounding_score = min_grounding_score

    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """Check grounding score."""
        grounding_score = operation_data.get("grounding_score", 0.0)

        if grounding_score < self.min_grounding_score:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.ERROR,
                message=f"Insufficient grounding: {grounding_score:.1%} < {self.min_grounding_score:.1%}",
                details={"grounding_score": grounding_score, "threshold": self.min_grounding_score},
                remediation_hints=[
                    "Increase source event coverage",
                    "Validate pattern against more evidence",
                    "Lower confidence estimate"
                ]
            )

        return None


class ConfidenceGate(Gate):
    """Verify that confidence is calibrated and reasonable."""

    def __init__(self, max_confidence: float = 0.95, min_samples: int = 3):
        super().__init__(GateType.CONFIDENCE)
        self.max_confidence = max_confidence
        self.min_samples = min_samples

    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """Check confidence calibration."""
        confidence = operation_data.get("confidence", 0.0)
        sample_count = operation_data.get("sample_count", 0)

        # Too confident without enough samples
        if confidence > 0.8 and sample_count < self.min_samples:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.WARNING,
                message=f"High confidence ({confidence:.1%}) with low samples ({sample_count})",
                details={"confidence": confidence, "samples": sample_count, "min_samples": self.min_samples},
                remediation_hints=[
                    "Gather more evidence before storing",
                    "Reduce confidence estimate",
                    "Mark for future validation"
                ]
            )

        # Unreasonably high confidence
        if confidence > self.max_confidence:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.WARNING,
                message=f"Over-confident estimate: {confidence:.1%} > {self.max_confidence:.1%}",
                details={"confidence": confidence, "max_allowed": self.max_confidence},
                remediation_hints=[
                    "Apply confidence penalty based on CoT brittleness",
                    "Use extended thinking more cautiously"
                ]
            )

        return None


class ConsistencyGate(Gate):
    """Verify consistency with existing memory."""

    def __init__(self, consistency_threshold: float = 0.7):
        super().__init__(GateType.CONSISTENCY)
        self.consistency_threshold = consistency_threshold

    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """Check consistency with existing memory."""
        consistency_score = operation_data.get("consistency_score", 1.0)
        existing_conflicts = operation_data.get("existing_conflicts", [])

        if consistency_score < self.consistency_threshold:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.WARNING,
                message=f"Low consistency: {consistency_score:.1%} < {self.consistency_threshold:.1%}",
                details={
                    "consistency_score": consistency_score,
                    "threshold": self.consistency_threshold,
                    "conflicts": len(existing_conflicts)
                },
                remediation_hints=[
                    "Review conflicting memories",
                    "Update or remove contradictory items",
                    "Merge similar patterns"
                ]
            )

        return None


class SoundnessGate(Gate):
    """Verify reasoning soundness (Q* properties)."""

    def __init__(self, required_properties: Optional[List[str]] = None):
        super().__init__(GateType.SOUNDNESS)
        self.required_properties = required_properties or [
            "optimality",      # Best solution found?
            "completeness",    # All cases covered?
            "consistency",     # No contradictions?
            "soundness",       # Valid reasoning?
            "minimality"       # Minimal complexity?
        ]

    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """Check Q* formal properties."""
        verified_properties = operation_data.get("verified_properties", [])

        missing_properties = [p for p in self.required_properties if p not in verified_properties]

        if missing_properties:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.WARNING,
                message=f"Missing property verification: {missing_properties}",
                details={"missing": missing_properties, "verified": verified_properties},
                remediation_hints=[
                    "Run formal verification on plan",
                    "Use scenario simulator for stress testing",
                    "Document why properties aren't verifiable"
                ]
            )

        return None


class MinimalityGate(Gate):
    """Verify that representations are minimal (no redundancy)."""

    def __init__(self, max_redundancy_ratio: float = 0.2):
        super().__init__(GateType.MINIMALITY)
        self.max_redundancy_ratio = max_redundancy_ratio

    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """Check for redundancy."""
        redundancy_ratio = operation_data.get("redundancy_ratio", 0.0)
        duplicate_count = operation_data.get("duplicate_count", 0)

        if redundancy_ratio > self.max_redundancy_ratio:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.WARNING,
                message=f"High redundancy: {redundancy_ratio:.1%} > {self.max_redundancy_ratio:.1%}",
                details={
                    "redundancy_ratio": redundancy_ratio,
                    "threshold": self.max_redundancy_ratio,
                    "duplicates_found": duplicate_count
                },
                remediation_hints=[
                    "Merge redundant patterns",
                    "Consolidate duplicate facts",
                    "Improve pattern generalization"
                ]
            )

        return None


class CoherenceGate(Gate):
    """Verify coherence with knowledge graph."""

    def __init__(self, min_coherence_score: float = 0.6):
        super().__init__(GateType.COHERENCE)
        self.min_coherence_score = min_coherence_score

    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """Check coherence with existing knowledge."""
        coherence_score = operation_data.get("coherence_score", 1.0)

        if coherence_score < self.min_coherence_score:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.WARNING,
                message=f"Low coherence: {coherence_score:.1%} < {self.min_coherence_score:.1%}",
                details={"coherence_score": coherence_score, "threshold": self.min_coherence_score},
                remediation_hints=[
                    "Connect to related entities in knowledge graph",
                    "Add contextual relationships",
                    "Improve semantic alignment"
                ]
            )

        return None


class EfficiencyGate(Gate):
    """Verify operational efficiency (performance)."""

    def __init__(self, max_execution_time_ms: float = 5000.0):
        super().__init__(GateType.EFFICIENCY)
        self.max_execution_time_ms = max_execution_time_ms

    def _check(self, operation_data: Dict[str, Any]) -> Optional[GateViolation]:
        """Check efficiency."""
        execution_time_ms = operation_data.get("execution_time_ms", 0.0)

        if execution_time_ms > self.max_execution_time_ms:
            return GateViolation(
                gate_type=self.gate_type,
                severity=GateSeverity.INFO,
                message=f"Slow operation: {execution_time_ms:.0f}ms > {self.max_execution_time_ms:.0f}ms",
                details={"execution_time_ms": execution_time_ms, "threshold": self.max_execution_time_ms},
                remediation_hints=[
                    "Profile operation for bottlenecks",
                    "Cache intermediate results",
                    "Consider async execution"
                ]
            )

        return None


class VerificationGateway:
    """Main verification gateway for all memory operations."""

    def __init__(self):
        """Initialize verification gateway with default gates."""
        self.gates: Dict[GateType, Gate] = {
            GateType.GROUNDING: GroundingGate(min_grounding_score=0.5),
            GateType.CONFIDENCE: ConfidenceGate(max_confidence=0.95, min_samples=3),
            GateType.CONSISTENCY: ConsistencyGate(consistency_threshold=0.7),
            GateType.SOUNDNESS: SoundnessGate(),
            GateType.MINIMALITY: MinimalityGate(max_redundancy_ratio=0.2),
            GateType.COHERENCE: CoherenceGate(min_coherence_score=0.6),
            GateType.EFFICIENCY: EfficiencyGate(max_execution_time_ms=5000.0),
        }

        self.decision_log: List[GateResult] = []
        self.remediation_handlers: Dict[GateType, Callable] = {}

    def register_remediation_handler(self, gate_type: GateType, handler: Callable) -> None:
        """Register a handler for gate violations."""
        self.remediation_handlers[gate_type] = handler

    def verify(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        gate_types: Optional[List[GateType]] = None
    ) -> GateResult:
        """
        Run verification gates on operation data.

        Args:
            operation_type: Type of operation ("recall", "remember", "consolidate", etc.)
            operation_data: Data to verify (should include fields expected by gates)
            gate_types: Specific gates to run (None = run all)

        Returns:
            GateResult with violations and pass/fail status
        """
        operation_id = operation_data.get("operation_id", f"{operation_type}_{datetime.now().timestamp()}")
        start_time = datetime.now()

        gates_to_run = gate_types or list(self.gates.keys())
        violations = []
        warnings = []

        for gate_type in gates_to_run:
            if gate_type not in self.gates:
                logger.warning(f"Unknown gate type: {gate_type}")
                continue

            gate = self.gates[gate_type]
            violation = gate.verify(operation_data)

            if violation:
                if violation.severity == GateSeverity.CRITICAL or violation.severity == GateSeverity.ERROR:
                    violations.append(violation)
                else:
                    warnings.append(violation)

        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Calculate overall confidence
        confidence_score = 1.0
        if violations:
            confidence_score *= 0.5  # Reduce by 50% for violations
        if warnings:
            confidence_score *= 0.9  # Reduce by 10% for warnings

        confidence_score *= operation_data.get("base_confidence", 0.7)
        confidence_score = max(0.0, min(1.0, confidence_score))

        result = GateResult(
            operation_id=operation_id,
            operation_type=operation_type,
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            confidence_score=confidence_score,
            execution_time_ms=execution_time_ms
        )

        self.decision_log.append(result)

        if not result.passed:
            logger.error(
                f"Gate verification failed for {operation_type}: "
                f"{len(violations)} violations, {len(warnings)} warnings"
            )

        return result

    def apply_remediation(self, result: GateResult, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply remediation for gate violations.

        Returns modified operation data.
        """
        remediated_data = operation_data.copy()

        for violation in result.violations + result.warnings:
            gate_type = violation.gate_type

            if gate_type in self.remediation_handlers:
                handler = self.remediation_handlers[gate_type]
                remediated_data = handler(violation, remediated_data)
            else:
                # Auto-remediation: apply hints
                if violation.remediation_hints:
                    logger.info(f"Auto-remediation for {gate_type.value}: {violation.remediation_hints[0]}")

        return remediated_data

    def get_gate_health(self) -> Dict[str, Any]:
        """Get health metrics for all gates."""
        health = {}

        for gate_type, gate in self.gates.items():
            health[gate_type.value] = {
                "success_rate": gate.get_success_rate(),
                "execution_count": gate.execution_count,
                "last_executed": gate.last_executed.isoformat() if gate.last_executed else None
            }

        return health

    def get_decision_insights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get insights from recent decisions."""
        recent = self.decision_log[-limit:]

        insights = []
        for result in recent:
            insights.append({
                "operation_id": result.operation_id,
                "operation_type": result.operation_type,
                "passed": result.passed,
                "confidence": result.confidence_score,
                "violations": len(result.violations),
                "warnings": len(result.warnings),
                "execution_time_ms": result.execution_time_ms,
                "timestamp": result.timestamp.isoformat()
            })

        return insights
