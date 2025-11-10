"""MCP Tools for Phase 7 Execution Intelligence."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from athena.execution import (
    ExecutionMonitor,
    AssumptionValidator,
    Assumption,
    AdaptiveReplanningEngine,
    ExecutionLearner,
    TaskOutcome,
    DeviationSeverity,
    AssumptionValidationType,
)


class ExecutionToolHandlers:
    """MCP tool handlers for execution intelligence."""

    def __init__(self):
        """Initialize execution tool handlers."""
        self.monitor = ExecutionMonitor()
        self.validator = AssumptionValidator()
        self.replanning_engine = AdaptiveReplanningEngine()
        self.learner = ExecutionLearner()

    # ======================
    # Execution Monitor Tools
    # ======================

    def initialize_plan(
        self,
        total_tasks: int,
        planned_duration_minutes: float,
        start_time_iso: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize execution monitoring for a plan.

        Args:
            total_tasks: Total number of tasks in plan
            planned_duration_minutes: Total planned duration in minutes
            start_time_iso: Plan start time (ISO format), defaults to now

        Returns:
            Confirmation with plan details
        """
        start_time = None
        if start_time_iso:
            start_time = datetime.fromisoformat(start_time_iso)

        planned_duration = timedelta(minutes=planned_duration_minutes)
        self.monitor.initialize_plan(total_tasks, planned_duration, start_time)

        return {
            "status": "initialized",
            "total_tasks": total_tasks,
            "planned_duration_minutes": planned_duration_minutes,
            "start_time": (start_time or datetime.utcnow()).isoformat(),
        }

    def record_task_start(
        self,
        task_id: str,
        planned_start_iso: str,
        planned_duration_minutes: float,
    ) -> Dict[str, Any]:
        """Record when a task actually starts.

        Args:
            task_id: ID of the task
            planned_start_iso: Planned start time (ISO format)
            planned_duration_minutes: Planned duration in minutes

        Returns:
            Task start record
        """
        planned_start = datetime.fromisoformat(planned_start_iso)
        planned_duration = timedelta(minutes=planned_duration_minutes)

        self.monitor.record_task_start(task_id, planned_start, planned_duration)

        return {
            "status": "recorded",
            "task_id": task_id,
            "actual_start": datetime.utcnow().isoformat(),
        }

    def record_task_completion(
        self,
        task_id: str,
        outcome: str,  # success/failure/partial/blocked
        resources_used: Optional[Dict[str, float]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record task completion.

        Args:
            task_id: ID of the task
            outcome: How the task completed
            resources_used: Actual resources consumed
            notes: Any notes about the task

        Returns:
            Task completion record
        """
        outcome_enum = TaskOutcome(outcome)
        record = self.monitor.record_task_completion(
            task_id, outcome_enum, resources_used, notes
        )

        if record is None:
            return {"status": "error", "message": f"Task {task_id} not found"}

        return {
            "status": "recorded",
            "task_id": task_id,
            "outcome": outcome,
            "duration_seconds": record.actual_duration.total_seconds()
            if record.actual_duration
            else None,
            "deviation": record.deviation,
            "confidence": record.confidence,
        }

    def get_plan_deviation(self) -> Dict[str, Any]:
        """Get current plan deviation metrics.

        Returns:
            PlanDeviation metrics
        """
        deviation = self.monitor.get_plan_deviation()

        return {
            "time_deviation_seconds": deviation.time_deviation.total_seconds(),
            "time_deviation_percent": deviation.time_deviation_percent,
            "resource_deviation": deviation.resource_deviation,
            "completion_rate": deviation.completion_rate,
            "completed_tasks": deviation.completed_tasks,
            "total_tasks": deviation.total_tasks,
            "tasks_at_risk": deviation.tasks_at_risk,
            "critical_path": deviation.critical_path,
            "estimated_completion": deviation.estimated_completion.isoformat(),
            "confidence": deviation.confidence,
            "deviation_severity": deviation.deviation_severity.value,
        }

    def predict_completion_time(self) -> Dict[str, Any]:
        """Predict actual completion time.

        Returns:
            Predicted completion time
        """
        predicted_time = self.monitor.predict_completion_time()

        return {
            "predicted_completion": predicted_time.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_critical_path(self) -> Dict[str, Any]:
        """Get critical path (bottleneck tasks).

        Returns:
            List of critical path task IDs
        """
        critical_path = self.monitor.get_critical_path()

        return {
            "critical_path": critical_path,
            "count": len(critical_path),
        }

    # ==========================
    # Assumption Validator Tools
    # ==========================

    def register_assumption(
        self,
        assumption_id: str,
        description: str,
        expected_value: str,  # JSON string
        validation_method: str,  # auto/manual/external/sensor
        check_frequency_minutes: float = 5.0,
        tolerance: float = 0.1,
        severity: str = "medium",
        affected_tasks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Register an assumption to validate during execution.

        Args:
            assumption_id: Unique ID for the assumption
            description: Human-readable description
            expected_value: Expected value (JSON string)
            validation_method: How to validate
            check_frequency_minutes: Check frequency in minutes
            tolerance: Acceptable variance (0.0-1.0)
            severity: Severity if violated
            affected_tasks: List of affected task IDs

        Returns:
            Confirmation
        """
        try:
            expected = json.loads(expected_value)
        except json.JSONDecodeError:
            expected = expected_value

        check_frequency = timedelta(minutes=check_frequency_minutes)
        severity_enum = DeviationSeverity(severity)
        method_enum = AssumptionValidationType(validation_method)

        self.validator.register_assumption(
            assumption_id,
            description,
            expected,
            method_enum,
            check_frequency,
            tolerance,
            severity_enum,
            affected_tasks or [],
        )

        return {
            "status": "registered",
            "assumption_id": assumption_id,
            "description": description,
        }

    def check_assumption(
        self,
        assumption_id: str,
        actual_value: str,  # JSON string
    ) -> Dict[str, Any]:
        """Check if an assumption still holds.

        Args:
            assumption_id: ID of assumption to check
            actual_value: Actual value (JSON string)

        Returns:
            Validation result
        """
        try:
            actual = json.loads(actual_value)
        except json.JSONDecodeError:
            actual = actual_value

        result = self.validator.check_assumption(assumption_id, actual)

        return {
            "assumption_id": assumption_id,
            "valid": result.valid,
            "validation_time": result.validation_time.isoformat(),
            "validation_type": result.validation_type.value,
            "confidence": result.confidence,
            "error_margin": result.error_margin,
        }

    def get_violated_assumptions(self) -> Dict[str, Any]:
        """Get list of currently violated assumptions.

        Returns:
            List of violations
        """
        violations = self.validator.get_violated_assumptions()

        return {
            "violations": [
                {
                    "assumption_id": v.assumption_id,
                    "severity": v.severity.value,
                    "impact": v.impact,
                    "mitigation": v.mitigation,
                    "replanning_required": v.replanning_required,
                    "affected_tasks": v.affected_tasks,
                }
                for v in violations
            ],
            "count": len(violations),
        }

    def predict_assumption_failure(
        self, assumption_id: str
    ) -> Dict[str, Any]:
        """Predict if an assumption will likely fail.

        Args:
            assumption_id: ID of assumption to predict

        Returns:
            Prediction result
        """
        prediction = self.validator.predict_assumption_failure(assumption_id)

        if prediction is None:
            return {
                "assumption_id": assumption_id,
                "will_fail": False,
                "reason": "Insufficient history or no concerning trend",
            }

        return {
            "assumption_id": assumption_id,
            "will_fail": True,
            "severity": prediction.severity.value,
            "impact": prediction.impact,
            "mitigation": prediction.mitigation,
            "affected_tasks": prediction.affected_tasks,
        }

    # =============================
    # Adaptive Replanning Tools
    # =============================

    def evaluate_replanning_need(
        self,
    ) -> Dict[str, Any]:
        """Evaluate if replanning is needed.

        Returns:
            Replanning evaluation
        """
        plan_deviation = self.monitor.get_plan_deviation()
        violations = self.validator.get_violated_assumptions()

        evaluation = self.replanning_engine.evaluate_replanning_need(
            plan_deviation, violations
        )

        return {
            "replanning_needed": evaluation.replanning_needed,
            "strategy": evaluation.strategy.value,
            "confidence": evaluation.confidence,
            "rationale": evaluation.rationale,
            "risk_level": evaluation.risk_level,
            "affected_tasks": evaluation.affected_tasks,
            "estimated_time_impact_minutes": evaluation.estimated_time_impact.total_seconds()
            / 60,
            "estimated_cost_impact": evaluation.estimated_cost_impact,
        }

    def generate_replanning_options(
        self,
        strategy: str,
        current_task_id: Optional[str] = None,
        segment_start_index: int = 0,
        segment_size: int = 5,
    ) -> Dict[str, Any]:
        """Generate replanning options based on strategy.

        Args:
            strategy: Replanning strategy (local/segment/full)
            current_task_id: Current task (for local strategy)
            segment_start_index: Starting index (for segment strategy)
            segment_size: Number of tasks (for segment strategy)

        Returns:
            List of replanning options
        """
        plan_deviation = self.monitor.get_plan_deviation()
        options: List[Any] = []

        if strategy == "local" and current_task_id:
            options = self.replanning_engine.generate_local_adjustment(
                current_task_id, {}, plan_deviation
            )
        elif strategy == "segment":
            options = self.replanning_engine.replan_segment(
                segment_start_index, segment_size, plan_deviation
            )
        elif strategy == "full":
            options = self.replanning_engine.full_replan(plan_deviation.tasks_at_risk)

        return {
            "strategy": strategy,
            "options": [
                {
                    "option_id": opt.option_id,
                    "title": opt.title,
                    "description": opt.description,
                    "timeline_impact_minutes": opt.timeline_impact.total_seconds() / 60,
                    "cost_impact": opt.cost_impact,
                    "success_probability": opt.success_probability,
                    "implementation_effort": opt.implementation_effort,
                    "risks": opt.risks,
                    "benefits": opt.benefits,
                }
                for opt in options
            ],
            "count": len(options),
        }

    def select_replanning_option(self, option_id: int) -> Dict[str, Any]:
        """Select a replanning option to execute.

        Args:
            option_id: ID of option to select

        Returns:
            Selected option details
        """
        option = self.replanning_engine.select_option(option_id)

        if option is None:
            return {"status": "error", "message": f"Option {option_id} not found"}

        return {
            "status": "selected",
            "option_id": option_id,
            "title": option.title,
            "implementation_effort": option.implementation_effort,
        }

    # =======================
    # Execution Learner Tools
    # =======================

    def extract_execution_patterns(self) -> Dict[str, Any]:
        """Extract patterns from execution records.

        Returns:
            List of identified patterns
        """
        records = self.monitor.get_all_task_records()
        records_dict = {r.task_id: r for r in records}

        patterns = self.learner.extract_execution_patterns(records_dict)

        return {
            "patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "description": p.description,
                    "confidence": p.confidence,
                    "frequency": p.frequency,
                    "impact": p.impact,
                    "actionable": p.actionable,
                    "recommendation": p.recommendation,
                }
                for p in patterns
            ],
            "count": len(patterns),
        }

    def compute_estimation_accuracy(self) -> Dict[str, Any]:
        """Compute estimation accuracy by task type.

        Returns:
            Accuracy metrics by task type
        """
        records = self.monitor.get_all_task_records()
        records_dict = {r.task_id: r for r in records}

        accuracy = self.learner.compute_estimation_accuracy(records_dict)

        return {
            "accuracy_by_type": accuracy,
            "average_accuracy": sum(accuracy.values()) / len(accuracy)
            if accuracy
            else 0.0,
        }

    def identify_bottlenecks(self) -> Dict[str, Any]:
        """Identify bottleneck tasks.

        Returns:
            List of bottleneck tasks
        """
        records = self.monitor.get_all_task_records()
        records_dict = {r.task_id: r for r in records}

        bottlenecks = self.learner.identify_bottlenecks(records_dict)

        return {
            "bottlenecks": [
                {
                    "task_id": task_id,
                    "impact": impact,
                    "impact_percent": f"{impact:.1%}",
                }
                for task_id, impact in bottlenecks
            ],
            "count": len(bottlenecks),
        }

    def generate_recommendations(self) -> Dict[str, Any]:
        """Generate recommendations for future executions.

        Returns:
            List of recommendations
        """
        records = self.monitor.get_all_task_records()
        records_dict = {r.task_id: r for r in records}

        recommendations = self.learner.generate_recommendations(records_dict)

        return {
            "recommendations": recommendations,
            "count": len(recommendations),
        }

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary.

        Returns:
            Summary of execution with all metrics
        """
        # Get metrics
        deviation = self.monitor.get_plan_deviation()
        violations = self.validator.get_violated_assumptions()
        records = self.monitor.get_all_task_records()
        records_dict = {r.task_id: r for r in records}

        # Get patterns and recommendations
        patterns = self.learner.extract_execution_patterns(records_dict)
        recommendations = self.learner.generate_recommendations(records_dict)
        bottlenecks = self.learner.identify_bottlenecks(records_dict)

        return {
            "execution_summary": {
                "total_tasks": deviation.total_tasks,
                "completed_tasks": deviation.completed_tasks,
                "completion_rate": f"{deviation.completion_rate:.1%}",
                "time_deviation_percent": f"{deviation.time_deviation_percent:.1f}%",
                "deviation_severity": deviation.deviation_severity.value,
                "violations_count": len(violations),
                "patterns_identified": len(patterns),
                "bottlenecks": [t[0] for t in bottlenecks[:3]],
                "recommendations": recommendations[:5],
                "estimated_completion": deviation.estimated_completion.isoformat(),
            }
        }
