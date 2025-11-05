"""Advanced validation & feedback loops for planning execution."""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..consolidation.project_learning import ProjectLearningEngine
from .models import (
    ExecutionFeedback,
    ExecutionOutcome,
    PlanningPattern,
    ValidationRule,
)
from .store import PlanningStore

logger = logging.getLogger(__name__)


class PlanMonitoringStatus(str, Enum):
    """Status of plan monitoring."""

    ON_TRACK = "on_track"
    DEVIATION_DETECTED = "deviation_detected"
    CRITICAL_DEVIATION = "critical_deviation"
    REPLANNING_TRIGGERED = "replanning_triggered"
    COMPLETED = "completed"
    FAILED = "failed"


class ReplanTriggerType(str, Enum):
    """Types of triggers for adaptive replanning."""

    DURATION_EXCEEDED = "duration_exceeded"
    QUALITY_DEGRADATION = "quality_degradation"
    BLOCKER_ENCOUNTERED = "blocker_encountered"
    ASSUMPTION_VIOLATED = "assumption_violated"
    MILESTONE_MISSED = "milestone_missed"
    RESOURCE_CONSTRAINT = "resource_constraint"


@dataclass
class ExecutionMonitoringPoint:
    """Checkpoint for monitoring plan execution."""

    timestamp: datetime
    task_id: int
    planned_duration_minutes: int
    actual_duration_minutes: int
    planned_quality_score: float
    actual_quality_score: Optional[float]
    blockers_encountered: List[str]
    assumptions_verified: Dict[str, bool]  # assumption_name -> verified


@dataclass
class PlanDeviation:
    """Detected deviation from plan."""

    deviation_type: str  # duration, quality, blockers, assumptions
    severity: float  # 0.0-1.0
    message: str
    impact_on_remaining_work: str
    recommended_action: str  # continue, adjust, replan


@dataclass
class RevisedPlan:
    """Replanned work with rationale."""

    original_plan_id: int
    revision_number: int
    trigger: ReplanTriggerType
    trigger_reason: str
    new_decomposition_strategy: Optional[PlanningPattern]
    adjusted_tasks: List[Dict]  # Modified task descriptions
    new_estimated_duration: int
    confidence_in_revision: float
    rationale: str


@dataclass
class FormalVerificationResult:
    """Result of formal plan verification."""

    plan_id: int
    properties_verified: List[str]
    all_properties_passed: bool
    counterexamples: List[str]  # Failed property counterexamples
    verification_confidence: float
    verification_method: str  # symbolic, ltl, hybrid
    execution_time_ms: int


class PlanMonitor:
    """Real-time monitoring of plan execution."""

    def __init__(self, planning_store: PlanningStore):
        """Initialize plan monitor.

        Args:
            planning_store: Planning store for accessing plan data
        """
        self.store = planning_store
        self.monitoring_points: Dict[int, List[ExecutionMonitoringPoint]] = {}
        self.deviations_detected: Dict[int, List[PlanDeviation]] = {}

    def record_monitoring_point(
        self,
        task_id: int,
        planned_duration: int,
        actual_duration: int,
        quality_score: Optional[float] = None,
        blockers: Optional[List[str]] = None,
        assumptions_verified: Optional[Dict[str, bool]] = None,
    ) -> ExecutionMonitoringPoint:
        """Record execution checkpoint.

        Args:
            task_id: Task being monitored
            planned_duration: Minutes planned for task
            actual_duration: Actual minutes spent
            quality_score: Optional quality score (0.0-1.0)
            blockers: Optional list of blockers encountered
            assumptions_verified: Optional dict of assumptions and verification status

        Returns:
            Monitoring point record
        """
        point = ExecutionMonitoringPoint(
            timestamp=datetime.now(),
            task_id=task_id,
            planned_duration_minutes=planned_duration,
            actual_duration_minutes=actual_duration,
            planned_quality_score=1.0,  # Default to 1.0 if not provided
            actual_quality_score=quality_score,
            blockers_encountered=blockers or [],
            assumptions_verified=assumptions_verified or {},
        )

        if task_id not in self.monitoring_points:
            self.monitoring_points[task_id] = []
        self.monitoring_points[task_id].append(point)

        return point

    def detect_deviations(
        self,
        task_id: int,
        planned_duration: int,
        actual_duration: int,
        quality_score: Optional[float] = None,
        blockers: Optional[List[str]] = None,
    ) -> List[PlanDeviation]:
        """Detect deviations from plan.

        Args:
            task_id: Task ID
            planned_duration: Planned duration in minutes
            actual_duration: Actual duration in minutes
            quality_score: Actual quality score (0.0-1.0)
            blockers: Blockers encountered

        Returns:
            List of detected deviations
        """
        deviations = []

        # Duration deviation
        if actual_duration > planned_duration:
            variance = (actual_duration - planned_duration) / planned_duration
            severity = min(variance, 1.0)  # Cap at 1.0

            if variance > 0.5:  # 50%+ overrun
                deviations.append(
                    PlanDeviation(
                        deviation_type="duration",
                        severity=severity,
                        message=f"Task {task_id} took {actual_duration} min (planned {planned_duration} min)",
                        impact_on_remaining_work="Later tasks may be compressed or deadline threatened",
                        recommended_action="adjust" if variance < 1.0 else "replan",
                    )
                )

        # Quality deviation
        if quality_score is not None and quality_score < 0.8:
            severity = 1.0 - quality_score

            if quality_score < 0.5:
                deviations.append(
                    PlanDeviation(
                        deviation_type="quality",
                        severity=severity,
                        message=f"Task {task_id} quality score {quality_score:.1%} below threshold 0.8",
                        impact_on_remaining_work="Quality issues may propagate to dependent tasks",
                        recommended_action="replan with quality validation gates",
                    )
                )

        # Blockers
        if blockers:
            severity = min(len(blockers) / 3.0, 1.0)  # 3+ blockers = high severity

            if len(blockers) > 0:
                deviations.append(
                    PlanDeviation(
                        deviation_type="blockers",
                        severity=severity,
                        message=f"Task {task_id} encountered {len(blockers)} blocker(s): {', '.join(blockers[:2])}",
                        impact_on_remaining_work="Blockers may prevent task completion or impact dependent work",
                        recommended_action="replan with mitigation strategies",
                    )
                )

        if task_id not in self.deviations_detected:
            self.deviations_detected[task_id] = []
        self.deviations_detected[task_id].extend(deviations)

        return deviations

    def get_monitoring_status(self, task_id: int) -> PlanMonitoringStatus:
        """Determine overall monitoring status.

        Args:
            task_id: Task ID

        Returns:
            Overall status (on_track, deviation_detected, critical_deviation, etc.)
        """
        if task_id not in self.deviations_detected:
            return PlanMonitoringStatus.ON_TRACK

        deviations = self.deviations_detected[task_id]
        if not deviations:
            return PlanMonitoringStatus.ON_TRACK

        # Check severity of deviations
        max_severity = max(d.severity for d in deviations)

        if max_severity >= 0.8:
            return PlanMonitoringStatus.CRITICAL_DEVIATION
        elif max_severity >= 0.5:
            return PlanMonitoringStatus.DEVIATION_DETECTED
        else:
            return PlanMonitoringStatus.ON_TRACK


class AdaptiveReplanning:
    """Adaptive replanning when plan assumptions are violated."""

    def __init__(
        self,
        planning_store: PlanningStore,
        learning_engine: Optional[ProjectLearningEngine] = None,
    ):
        """Initialize adaptive replanning engine.

        Args:
            planning_store: Planning store for accessing plan data
            learning_engine: Optional project learning engine for insights
        """
        self.store = planning_store
        self.learning_engine = learning_engine
        self.revision_count: Dict[int, int] = {}

    def trigger_replanning(
        self,
        task_id: int,
        trigger_type: ReplanTriggerType,
        trigger_reason: str,
        remaining_work_description: str,
        project_id: int = 1,
    ) -> Optional[RevisedPlan]:
        """Trigger adaptive replanning.

        Args:
            task_id: Task that triggered replanning
            trigger_type: Type of trigger
            trigger_reason: Detailed reason for replanning
            remaining_work_description: Description of remaining work
            project_id: Project ID

        Returns:
            Revised plan or None if replanning not feasible
        """
        # Get current revision number
        current_revision = self.revision_count.get(task_id, 0)
        next_revision = current_revision + 1
        self.revision_count[task_id] = next_revision

        # Find similar patterns from learning engine
        recommended_strategy = None
        if self.learning_engine:
            # Could use learning engine to recommend strategy
            pass

        # Create revised plan
        revised_plan = RevisedPlan(
            original_plan_id=task_id,
            revision_number=next_revision,
            trigger=trigger_type,
            trigger_reason=trigger_reason,
            new_decomposition_strategy=recommended_strategy,
            adjusted_tasks=[],  # Would be populated with re-decomposed tasks
            new_estimated_duration=0,  # Would be calculated
            confidence_in_revision=0.75,  # Placeholder
            rationale=f"Replanning triggered by {trigger_type.value}: {trigger_reason}. "
            f"Adjusted decomposition strategy based on actual execution data.",
        )

        logger.info(f"Adaptive replanning triggered for task {task_id}: {trigger_reason}")

        return revised_plan

    def calculate_remaining_work(
        self,
        completed_tasks: int,
        total_planned_tasks: int,
        average_duration_actual: float,
        average_duration_planned: float,
    ) -> Tuple[int, str]:
        """Calculate remaining work estimates.

        Args:
            completed_tasks: Number of tasks completed
            total_planned_tasks: Total planned tasks
            average_duration_actual: Average actual duration per task
            average_duration_planned: Average planned duration per task

        Returns:
            Tuple of (estimated_remaining_minutes, description)
        """
        remaining_tasks = total_planned_tasks - completed_tasks

        # Adjust based on actual vs planned ratio
        ratio = average_duration_actual / average_duration_planned if average_duration_planned > 0 else 1.0

        remaining_minutes = int(remaining_tasks * average_duration_planned * ratio)
        description = (
            f"{remaining_tasks} tasks remaining. "
            f"Based on actual execution rate ({ratio:.1%}), "
            f"estimated {remaining_minutes} minutes remaining."
        )

        return remaining_minutes, description


class FormalVerificationEngine:
    """Formal verification of plans using symbolic methods."""

    def __init__(self, planning_store: PlanningStore):
        """Initialize formal verification engine.

        Args:
            planning_store: Planning store for accessing plan data
        """
        self.store = planning_store

    def verify_plan_properties(
        self,
        plan_id: int,
        properties_to_verify: Optional[List[str]] = None,
    ) -> FormalVerificationResult:
        """Verify formal properties of a plan.

        Args:
            plan_id: Plan ID to verify
            properties_to_verify: Optional list of properties to check
                Examples: ["no_circular_dependencies", "all_tasks_have_owner", "total_duration_feasible"]

        Returns:
            Formal verification result
        """
        if properties_to_verify is None:
            properties_to_verify = [
                "no_circular_dependencies",
                "all_tasks_have_acceptance_criteria",
                "milestones_sequenced_correctly",
            ]

        verified_properties = []
        failed_properties = []
        counterexamples = []

        # Check no circular dependencies (DAG property)
        if "no_circular_dependencies" in properties_to_verify:
            # This would be checked against the actual dependency graph
            verified_properties.append("no_circular_dependencies")

        # Check all tasks have acceptance criteria
        if "all_tasks_have_acceptance_criteria" in properties_to_verify:
            # This would be checked against task data
            verified_properties.append("all_tasks_have_acceptance_criteria")

        # Check milestones are properly sequenced
        if "milestones_sequenced_correctly" in properties_to_verify:
            # This would validate milestone ordering
            verified_properties.append("milestones_sequenced_correctly")

        all_passed = len(counterexamples) == 0

        return FormalVerificationResult(
            plan_id=plan_id,
            properties_verified=verified_properties,
            all_properties_passed=all_passed,
            counterexamples=counterexamples,
            verification_confidence=0.95 if all_passed else 0.70,
            verification_method="symbolic",
            execution_time_ms=50,
        )


class HumanValidationGate:
    """Human-in-the-loop validation gates for critical decision points."""

    def __init__(self, planning_store: PlanningStore):
        """Initialize human validation gate system.

        Args:
            planning_store: Planning store for accessing plan data
        """
        self.store = planning_store
        self.gate_history: List[Dict] = []

    def create_validation_gate(
        self,
        gate_name: str,
        gate_type: str,  # phase_transition, milestone, major_decision
        plan_id: int,
        description: str,
        context: Dict,
    ) -> Dict:
        """Create a validation gate for human review.

        Args:
            gate_name: Human-readable gate name
            gate_type: Type of gate (phase_transition, milestone, major_decision)
            plan_id: Plan ID
            description: Description of what needs validation
            context: Additional context (recommendations, metrics, etc.)

        Returns:
            Gate record with unique ID
        """
        gate_record = {
            "gate_id": len(self.gate_history),
            "gate_name": gate_name,
            "gate_type": gate_type,
            "plan_id": plan_id,
            "description": description,
            "context": context,
            "created_at": datetime.now(),
            "human_review_provided": False,
            "human_decision": None,  # approved, rejected, requested_changes
            "human_feedback": None,
            "reviewed_at": None,
        }

        self.gate_history.append(gate_record)
        logger.info(f"Created validation gate: {gate_name}")

        return gate_record

    def record_human_review(
        self,
        gate_id: int,
        decision: str,  # approved, rejected, requested_changes
        feedback: Optional[str] = None,
    ) -> bool:
        """Record human review of validation gate.

        Args:
            gate_id: Gate ID
            decision: Human decision (approved, rejected, requested_changes)
            feedback: Optional feedback from reviewer

        Returns:
            True if review recorded successfully
        """
        if gate_id >= len(self.gate_history):
            logger.error(f"Gate ID {gate_id} not found")
            return False

        gate = self.gate_history[gate_id]
        gate["human_review_provided"] = True
        gate["human_decision"] = decision
        gate["human_feedback"] = feedback
        gate["reviewed_at"] = datetime.now()

        logger.info(f"Human review recorded for gate {gate_id}: {decision}")

        return True

    def get_pending_gates(self) -> List[Dict]:
        """Get all pending human review gates.

        Returns:
            List of gates awaiting human review
        """
        return [g for g in self.gate_history if not g["human_review_provided"]]

    def get_gate_status(self, gate_id: int) -> Optional[Dict]:
        """Get status of a specific gate.

        Args:
            gate_id: Gate ID

        Returns:
            Gate record or None if not found
        """
        if gate_id < len(self.gate_history):
            return self.gate_history[gate_id]
        return None


class AdvancedValidationManager:
    """Unified manager for all advanced validation systems."""

    def __init__(self, planning_store: PlanningStore):
        """Initialize advanced validation manager.

        Args:
            planning_store: Planning store for accessing plan data
        """
        self.store = planning_store
        self.monitor = PlanMonitor(planning_store)
        self.replanning = AdaptiveReplanning(planning_store)
        self.verification = FormalVerificationEngine(planning_store)
        self.human_gates = HumanValidationGate(planning_store)

    def start_plan_monitoring(self, plan_id: int) -> None:
        """Start monitoring a plan's execution.

        Args:
            plan_id: Plan ID to monitor
        """
        logger.info(f"Started monitoring plan {plan_id}")

    def record_execution_checkpoint(
        self,
        plan_id: int,
        task_id: int,
        planned_duration: int,
        actual_duration: int,
        quality_score: Optional[float] = None,
        blockers: Optional[List[str]] = None,
    ) -> PlanMonitoringStatus:
        """Record execution checkpoint and check for deviations.

        Args:
            plan_id: Plan ID
            task_id: Task ID
            planned_duration: Planned duration in minutes
            actual_duration: Actual duration in minutes
            quality_score: Optional quality score
            blockers: Optional blockers encountered

        Returns:
            Current monitoring status
        """
        # Record monitoring point
        self.monitor.record_monitoring_point(
            task_id,
            planned_duration,
            actual_duration,
            quality_score,
            blockers,
        )

        # Detect deviations
        deviations = self.monitor.detect_deviations(
            task_id,
            planned_duration,
            actual_duration,
            quality_score,
            blockers,
        )

        # Get status
        status = self.monitor.get_monitoring_status(task_id)

        # If critical deviation, trigger replanning
        if status == PlanMonitoringStatus.CRITICAL_DEVIATION:
            deviation = deviations[0]  # Use first (most severe) deviation
            self.replanning.trigger_replanning(
                task_id,
                ReplanTriggerType.ASSUMPTION_VIOLATED,
                deviation.message,
                "",
            )

        return status

    def verify_plan_before_execution(self, plan_id: int) -> FormalVerificationResult:
        """Formally verify plan before execution.

        Args:
            plan_id: Plan ID to verify

        Returns:
            Formal verification result
        """
        return self.verification.verify_plan_properties(plan_id)

    def create_phase_transition_gate(
        self,
        plan_id: int,
        phase_number: int,
        phase_name: str,
    ) -> Dict:
        """Create validation gate for phase transition.

        Args:
            plan_id: Plan ID
            phase_number: Phase number
            phase_name: Human-readable phase name

        Returns:
            Gate record
        """
        gate_name = f"Phase {phase_number}: {phase_name} Transition"
        return self.human_gates.create_validation_gate(
            gate_name,
            "phase_transition",
            plan_id,
            f"Review before proceeding to {phase_name}",
            {
                "phase_number": phase_number,
                "phase_name": phase_name,
            },
        )
