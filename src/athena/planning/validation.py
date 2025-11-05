"""Plan validation and feedback loop integration.

Validates plans before execution:
- Structure validation (phases, tasks, dependencies, milestones)
- Feasibility validation (duration, resources, risks vs historical data)
- Rule-based validation (formal, heuristic, LLM-based checks)
- Feedback loop integration (monitor execution vs plan assumptions)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import statistics

from .models import ValidationRule, ExecutionFeedback, ExecutionOutcome
from .store import PlanningStore
from .advanced_validation import (
    AdvancedValidationManager,
    PlanMonitoringStatus,
    ReplanTriggerType,
)


class Severity(str, Enum):
    """Validation severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AdjustmentAction(str, Enum):
    """Actions to take when plan deviates."""

    CONTINUE = "continue"  # Continue with current plan
    ADJUST = "adjust"  # Minor adjustments, keep plan
    REPLAN = "replan"  # Significant deviation, replanning needed


@dataclass
class ValidationResult:
    """Result of plan structure validation."""

    valid: bool
    issues: List[str] = field(default_factory=list)
    severity: Severity = Severity.LOW
    summary: str = ""

    def add_issue(self, issue: str, severity: Severity = Severity.MEDIUM):
        """Add a validation issue."""
        self.issues.append(issue)
        # Update overall severity if this issue is worse
        severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        if severity_order.index(severity) > severity_order.index(self.severity):
            self.severity = severity


@dataclass
class RiskFactor:
    """A risk factor identified during feasibility validation."""

    name: str
    description: str
    probability: float  # 0.0 to 1.0
    impact: float  # 0.0 to 1.0
    mitigation: Optional[str] = None

    @property
    def risk_score(self) -> float:
        """Calculate risk score (probability * impact)."""
        return self.probability * self.impact


@dataclass
class FeasibilityReport:
    """Result of plan feasibility validation."""

    feasible: bool
    confidence: float  # 0.0 to 1.0
    risks: List[RiskFactor] = field(default_factory=list)
    estimated_duration_minutes: Optional[int] = None
    available_time_minutes: Optional[int] = None
    duration_variance_estimate: float = 1.0  # Ratio of estimated to actual
    summary: str = ""


@dataclass
class RuleValidationResult:
    """Result of rule-based validation."""

    all_pass: bool
    violations: List[str] = field(default_factory=list)
    rules_checked: int = 0
    rules_passed: int = 0
    summary: str = ""


@dataclass
class AdjustmentRecommendation:
    """Recommendation for plan adjustment."""

    action: AdjustmentAction
    reason: str
    confidence: float  # 0.0 to 1.0
    suggested_changes: List[str] = field(default_factory=list)
    continue_threshold: float = 0.85  # Confidence to continue


class PlanValidator:
    """Validates plans before execution."""

    def __init__(self, planning_store: PlanningStore):
        """Initialize validator.

        Args:
            planning_store: PlanningStore instance
        """
        self.store = planning_store

    def validate_plan_structure(
        self, plan_dict: Dict[str, Any]
    ) -> ValidationResult:
        """Validate plan structure.

        Checks:
        - Non-empty phases list
        - All tasks have acceptance criteria
        - Dependencies form DAG (no cycles)
        - Milestones sequenced correctly

        Args:
            plan_dict: Plan dictionary with structure

        Returns:
            ValidationResult with issues and severity
        """
        result = ValidationResult(valid=True)

        # Check phases
        phases = plan_dict.get("phases", [])
        if not phases:
            result.add_issue("Plan has no phases", Severity.CRITICAL)
            result.valid = False
            return result

        # Check tasks and acceptance criteria
        for phase in phases:
            phase_num = phase.get("phase_number", "unknown")
            tasks = phase.get("tasks", [])

            if not tasks:
                result.add_issue(
                    f"Phase {phase_num} has no tasks",
                    Severity.MEDIUM,
                )

            for task in tasks:
                task_id = task.get("id", "unknown")
                criteria = task.get("acceptance_criteria", [])

                if not criteria:
                    result.add_issue(
                        f"Task {task_id} has no acceptance criteria",
                        Severity.HIGH,
                    )

        # Check dependencies form DAG (no cycles)
        dependencies = plan_dict.get("dependencies", [])
        if dependencies:
            if self._has_cycle(dependencies):
                result.add_issue(
                    "Plan has circular dependencies (not a DAG)",
                    Severity.CRITICAL,
                )
                result.valid = False

        # Check milestones sequenced
        milestones = plan_dict.get("milestones", [])
        if milestones:
            for i, milestone in enumerate(milestones):
                if i > 0:
                    prev_date = milestones[i - 1].get("target_date")
                    curr_date = milestone.get("target_date")
                    if prev_date and curr_date and prev_date > curr_date:
                        result.add_issue(
                            f"Milestones not sequenced (milestone {i} before {i-1})",
                            Severity.MEDIUM,
                        )

        # Generate summary
        if result.valid:
            result.summary = f"Plan structure valid: {len(phases)} phases, {sum(len(p.get('tasks', [])) for p in phases)} tasks"
        else:
            result.summary = f"Plan structure invalid: {len(result.issues)} issues found"

        return result

    def validate_plan_feasibility(
        self,
        project_id: int,
        plan_dict: Dict[str, Any],
        available_time_minutes: int = 480,
    ) -> FeasibilityReport:
        """Validate plan feasibility.

        Checks:
        - Estimated duration vs available time
        - Resource constraints
        - Risk factors

        Args:
            project_id: Project ID
            plan_dict: Plan dictionary
            available_time_minutes: Available time for plan execution

        Returns:
            FeasibilityReport with feasibility assessment
        """
        report = FeasibilityReport(feasible=True, confidence=0.5)
        report.available_time_minutes = available_time_minutes

        # Estimate total duration
        phases = plan_dict.get("phases", [])
        total_estimated_minutes = 0

        for phase in phases:
            tasks = phase.get("tasks", [])
            for task in tasks:
                estimated = task.get("estimated_duration_minutes", 30)
                total_estimated_minutes += estimated

        report.estimated_duration_minutes = total_estimated_minutes

        # Get historical data for similar task types
        cursor = self.store.db.conn.cursor()
        cursor.execute(
            """
            SELECT actual_duration_minutes, planned_duration_minutes
            FROM execution_feedback
            WHERE project_id = ?
            AND actual_duration_minutes IS NOT NULL
            AND planned_duration_minutes IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 20
        """,
            (project_id,),
        )

        historical_data = cursor.fetchall()
        if historical_data:
            # Calculate actual vs planned ratio
            ratios = []
            for actual, planned in historical_data:
                if planned > 0:
                    ratios.append(actual / planned)

            if ratios:
                report.duration_variance_estimate = statistics.mean(ratios)

        # Adjust estimated duration based on historical variance
        adjusted_estimate = int(total_estimated_minutes * report.duration_variance_estimate)

        # Check if feasible
        if adjusted_estimate > available_time_minutes:
            report.feasible = False
            report.confidence = 0.3

            # Calculate how much over
            overage = adjusted_estimate - available_time_minutes
            report.risks.append(
                RiskFactor(
                    name="Duration Overrun",
                    description=f"Plan would exceed available time by {overage} minutes",
                    probability=0.9,
                    impact=0.8,
                    mitigation="Reduce scope or extend available time",
                )
            )
        else:
            # Plan fits within available time
            buffer = available_time_minutes - adjusted_estimate
            confidence_boost = min(buffer / available_time_minutes, 0.5)
            report.confidence = min(0.5 + confidence_boost, 0.95)

        # Identify other risks
        num_tasks = sum(len(p.get("tasks", [])) for p in phases)
        if num_tasks > 20:
            report.risks.append(
                RiskFactor(
                    name="High Task Count",
                    description=f"Plan has {num_tasks} tasks (>20 increases complexity)",
                    probability=0.6,
                    impact=0.5,
                    mitigation="Consider higher-level decomposition",
                )
            )

        # Generate summary
        status = "Feasible" if report.feasible else "Infeasible"
        report.summary = (
            f"{status} plan: {total_estimated_minutes}min estimated, "
            f"{adjusted_estimate}min adjusted (variance: {report.duration_variance_estimate:.1f}x), "
            f"{available_time_minutes}min available, confidence: {report.confidence:.0%}"
        )

        return report

    def apply_validation_rules(
        self,
        project_id: int,
        plan_dict: Dict[str, Any],
        rules: List[ValidationRule],
    ) -> RuleValidationResult:
        """Apply validation rules to plan.

        Args:
            project_id: Project ID
            plan_dict: Plan dictionary
            rules: List of ValidationRule objects to apply

        Returns:
            RuleValidationResult with violations
        """
        result = RuleValidationResult(all_pass=True)
        result.rules_checked = len(rules)

        for rule in rules:
            # Apply each rule
            passed = self._apply_single_rule(rule, plan_dict)

            if passed:
                result.rules_passed += 1
            else:
                result.all_pass = False
                result.violations.append(
                    f"Rule '{rule.rule_name}' failed: {rule.description}"
                )

        # Generate summary
        result.summary = (
            f"Validation: {result.rules_passed}/{result.rules_checked} rules passed"
        )

        return result

    def feedback_loop_integration(
        self,
        plan_dict: Dict[str, Any],
        feedback: ExecutionFeedback,
        deviation_threshold: float = 0.20,
    ) -> AdjustmentRecommendation:
        """Integrate execution feedback and recommend adjustments.

        Analyzes deviation from plan and recommends whether to continue,
        adjust, or replan.

        Args:
            plan_dict: Original plan dictionary
            feedback: In-progress ExecutionFeedback
            deviation_threshold: Threshold for deviation (default 20%)

        Returns:
            AdjustmentRecommendation
        """
        recommendation = AdjustmentRecommendation(
            action=AdjustmentAction.CONTINUE,
            reason="Plan on track",
            confidence=0.95,
        )

        # Check if we have both planned and actual data
        if not feedback.planned_duration_minutes or feedback.actual_duration_minutes is None:
            return recommendation

        # Calculate variance
        planned = feedback.planned_duration_minutes
        actual = feedback.actual_duration_minutes

        variance = abs(actual - planned) / planned if planned > 0 else 0.0

        # Evaluate against assumption violations
        if feedback.assumption_violations:
            recommendation.reason = "Plan assumptions violated"
            recommendation.confidence = 0.6

            if variance > deviation_threshold * 2:
                recommendation.action = AdjustmentAction.REPLAN
                recommendation.suggested_changes = feedback.assumption_violations
            elif variance > deviation_threshold:
                recommendation.action = AdjustmentAction.ADJUST
                recommendation.suggested_changes = [
                    "Adjust remaining tasks based on current pace"
                ]
            else:
                recommendation.action = AdjustmentAction.CONTINUE

        # Evaluate duration variance
        elif variance > deviation_threshold * 2:
            recommendation.action = AdjustmentAction.REPLAN
            recommendation.reason = f"Duration variance {variance:.0%} exceeds 2x threshold"
            recommendation.confidence = 0.7
            recommendation.suggested_changes = [
                f"Actual pace is {actual/planned:.1f}x estimated",
                "Replan remaining work with adjusted estimates",
            ]

        elif variance > deviation_threshold:
            recommendation.action = AdjustmentAction.ADJUST
            recommendation.reason = f"Duration variance {variance:.0%} detected"
            recommendation.confidence = 0.8
            recommendation.suggested_changes = [
                f"Adjust estimates: pace is {actual/planned:.1f}x planned",
                "Continue with adjusted timeline",
            ]

        # Check execution quality
        if feedback.execution_quality_score < 0.7:
            recommendation.suggested_changes.append(
                f"Quality score low ({feedback.execution_quality_score:.0%}), consider quality review"
            )

        # Check blockers
        if feedback.blockers_encountered:
            recommendation.suggested_changes.append(
                f"Blockers encountered: {', '.join(feedback.blockers_encountered[:2])}"
            )

        return recommendation

    def _has_cycle(self, dependencies: List[Dict[str, Any]]) -> bool:
        """Check if dependency graph has cycles.

        Args:
            dependencies: List of dependency dicts with 'from_task' and 'to_task'

        Returns:
            True if cycle detected
        """
        if not dependencies:
            return False

        # Build adjacency list
        graph = {}
        for dep in dependencies:
            from_task = dep.get("from_task")
            to_task = dep.get("to_task")

            if from_task not in graph:
                graph[from_task] = []
            graph[from_task].append(to_task)

        # DFS to detect cycle
        def has_cycle_dfs(node: str, visited: set, rec_stack: set) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle_dfs(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for node in graph:
            if node not in visited:
                if has_cycle_dfs(node, visited, set()):
                    return True

        return False

    def _apply_single_rule(
        self, rule: ValidationRule, plan_dict: Dict[str, Any]
    ) -> bool:
        """Apply a single validation rule.

        Args:
            rule: ValidationRule to apply
            plan_dict: Plan to validate

        Returns:
            True if rule passes
        """
        # For heuristic rules, apply simple checks
        if rule.check_function == "check_task_duration":
            max_duration = rule.parameters.get("max_duration_hours", 8)
            phases = plan_dict.get("phases", [])
            for phase in phases:
                for task in phase.get("tasks", []):
                    duration_min = task.get("estimated_duration_minutes", 0)
                    if duration_min > max_duration * 60:
                        return False
            return True

        elif rule.check_function == "check_dependencies":
            # Dependencies should form DAG
            dependencies = plan_dict.get("dependencies", [])
            return not self._has_cycle(dependencies)

        elif rule.check_function == "check_acceptance_criteria":
            # All tasks must have acceptance criteria
            phases = plan_dict.get("phases", [])
            for phase in phases:
                for task in phase.get("tasks", []):
                    if not task.get("acceptance_criteria"):
                        return False
            return True

        # Default to pass for unknown rules
        return True


# Convenience functions

def validate_plan_structure(plan_dict: Dict[str, Any]) -> ValidationResult:
    """Convenience function for structure validation.

    Note: Structure validation doesn't require a store, but PlanValidator
    needs one for other operations. This function creates a minimal validator.
    """
    # Structure validation doesn't need a store, just create validator with None
    validator = PlanValidator(None)
    return validator.validate_plan_structure(plan_dict)


def validate_plan_feasibility(
    planning_store: PlanningStore,
    project_id: int,
    plan_dict: Dict[str, Any],
    available_time_minutes: int = 480,
) -> FeasibilityReport:
    """Convenience function for feasibility validation."""
    validator = PlanValidator(planning_store)
    return validator.validate_plan_feasibility(
        project_id, plan_dict, available_time_minutes
    )


def apply_validation_rules(
    planning_store: PlanningStore,
    project_id: int,
    plan_dict: Dict[str, Any],
    rules: List[ValidationRule],
) -> RuleValidationResult:
    """Convenience function for rule validation."""
    validator = PlanValidator(planning_store)
    return validator.apply_validation_rules(project_id, plan_dict, rules)


def feedback_loop_integration(
    plan_dict: Dict[str, Any],
    feedback: ExecutionFeedback,
    deviation_threshold: float = 0.20,
) -> AdjustmentRecommendation:
    """Convenience function for feedback loop integration."""
    validator = PlanValidator(None)  # Doesn't need store
    return validator.feedback_loop_integration(plan_dict, feedback, deviation_threshold)


# Advanced Validation Integration

def create_advanced_validation_system(
    planning_store: PlanningStore,
) -> AdvancedValidationManager:
    """Create an advanced validation system.

    Args:
        planning_store: Planning store for accessing plan data

    Returns:
        Advanced validation manager with all subsystems initialized
    """
    return AdvancedValidationManager(planning_store)


def monitor_plan_execution(
    validation_manager: AdvancedValidationManager,
    plan_id: int,
    task_id: int,
    planned_duration: int,
    actual_duration: int,
    quality_score: Optional[float] = None,
    blockers: Optional[List[str]] = None,
) -> PlanMonitoringStatus:
    """Monitor plan execution and detect deviations.

    Args:
        validation_manager: Advanced validation manager
        plan_id: Plan being monitored
        task_id: Current task
        planned_duration: Planned duration in minutes
        actual_duration: Actual duration in minutes
        quality_score: Optional quality score (0.0-1.0)
        blockers: Optional list of blockers encountered

    Returns:
        Monitoring status (on_track, deviation_detected, critical_deviation, etc.)
    """
    return validation_manager.record_execution_checkpoint(
        plan_id, task_id, planned_duration, actual_duration, quality_score, blockers
    )


def trigger_adaptive_replanning(
    validation_manager: AdvancedValidationManager,
    task_id: int,
    trigger_type: ReplanTriggerType,
    trigger_reason: str,
    remaining_work_description: str,
    project_id: int = 1,
):
    """Trigger adaptive replanning when assumptions violated.

    Args:
        validation_manager: Advanced validation manager
        task_id: Task that triggered replanning
        trigger_type: Type of trigger (DURATION_EXCEEDED, QUALITY_DEGRADATION, etc.)
        trigger_reason: Detailed reason for replanning
        remaining_work_description: Description of remaining work
        project_id: Project ID

    Returns:
        Revised plan or None if replanning not feasible
    """
    return validation_manager.replanning.trigger_replanning(
        task_id, trigger_type, trigger_reason, remaining_work_description, project_id
    )


def verify_plan_formally(
    validation_manager: AdvancedValidationManager,
    plan_id: int,
    properties: Optional[List[str]] = None,
):
    """Formally verify plan properties before execution.

    Args:
        validation_manager: Advanced validation manager
        plan_id: Plan to verify
        properties: Optional list of properties to verify

    Returns:
        Formal verification result
    """
    return validation_manager.verify_plan_before_execution(plan_id)


def create_validation_gate(
    validation_manager: AdvancedValidationManager,
    plan_id: int,
    phase_number: int,
    phase_name: str,
):
    """Create a validation gate for human review.

    Args:
        validation_manager: Advanced validation manager
        plan_id: Plan being validated
        phase_number: Phase number
        phase_name: Human-readable phase name

    Returns:
        Gate record with ID and metadata
    """
    return validation_manager.create_phase_transition_gate(plan_id, phase_number, phase_name)


def get_pending_validation_gates(
    validation_manager: AdvancedValidationManager,
) -> List[Dict[str, Any]]:
    """Get all pending human review gates.

    Args:
        validation_manager: Advanced validation manager

    Returns:
        List of gates awaiting human review
    """
    return validation_manager.human_gates.get_pending_gates()


def approve_validation_gate(
    validation_manager: AdvancedValidationManager,
    gate_id: int,
    feedback: Optional[str] = None,
) -> bool:
    """Approve a validation gate.

    Args:
        validation_manager: Advanced validation manager
        gate_id: Gate ID
        feedback: Optional approval feedback

    Returns:
        True if approval recorded successfully
    """
    return validation_manager.human_gates.record_human_review(
        gate_id, "approved", feedback
    )


def reject_validation_gate(
    validation_manager: AdvancedValidationManager,
    gate_id: int,
    feedback: str,
) -> bool:
    """Reject a validation gate.

    Args:
        validation_manager: Advanced validation manager
        gate_id: Gate ID
        feedback: Rejection reason

    Returns:
        True if rejection recorded successfully
    """
    return validation_manager.human_gates.record_human_review(
        gate_id, "rejected", feedback
    )
