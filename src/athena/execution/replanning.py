"""Adaptive Replanning Engine - Generate intelligent replanning options."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from .models import (
    ReplanningStrategy,
    ReplanningEvaluation,
    ReplanningOption,
    PlanDeviation,
    AssumptionViolation,
    DeviationSeverity,
)

logger = logging.getLogger(__name__)


class AdaptiveReplanningEngine:
    """Generate and manage intelligent replanning options."""

    def __init__(self):
        """Initialize replanning engine."""
        self.replanning_evaluations: List[ReplanningEvaluation] = []
        self.replanning_options: List[ReplanningOption] = []
        self.selected_option: Optional[ReplanningOption] = None
        self.replanning_count = 0

    def evaluate_replanning_need(
        self,
        plan_deviation: PlanDeviation,
        violations: List[AssumptionViolation],
    ) -> ReplanningEvaluation:
        """Evaluate if replanning is needed and what strategy to use.

        Args:
            plan_deviation: Current plan deviation metrics
            violations: List of assumption violations

        Returns:
            ReplanningEvaluation with recommendation
        """
        now = datetime.utcnow()
        replanning_needed = False
        strategy = ReplanningStrategy.NONE
        confidence = 0.9
        rationale = ""
        risk_level = "low"
        estimated_time_impact = timedelta(0)
        estimated_cost_impact = 0.0

        # Decision logic based on severity and context
        if len(violations) > 1:
            # Multiple violations → FULL replan
            replanning_needed = True
            strategy = ReplanningStrategy.FULL
            confidence = 0.85
            rationale = f"Multiple assumption violations ({len(violations)})"
            risk_level = "high"
            estimated_time_impact = timedelta(hours=1)
            estimated_cost_impact = 500.0

        elif len(violations) == 1:
            violation = violations[0]

            if plan_deviation.deviation_severity == DeviationSeverity.CRITICAL:
                # Critical deviation → FULL replan
                replanning_needed = True
                strategy = ReplanningStrategy.FULL
                confidence = 0.8
                rationale = (
                    f"Critical deviation ({plan_deviation.time_deviation_percent:.1f}%) + violation"
                )
                risk_level = "high"
                estimated_time_impact = timedelta(hours=1)
                estimated_cost_impact = 500.0

            elif plan_deviation.deviation_severity == DeviationSeverity.HIGH:
                # High deviation with violation → SEGMENT
                replanning_needed = True
                strategy = ReplanningStrategy.SEGMENT
                confidence = 0.8
                rationale = (
                    f"High deviation ({plan_deviation.time_deviation_percent:.1f}%) + violation"
                )
                risk_level = "medium"
                estimated_time_impact = timedelta(minutes=15)
                estimated_cost_impact = 100.0

            elif plan_deviation.completion_rate > 0.7 and violation.severity in [
                DeviationSeverity.LOW,
                DeviationSeverity.MEDIUM,
            ]:
                # Late-stage single issue → LOCAL adjustment
                replanning_needed = True
                strategy = ReplanningStrategy.LOCAL
                confidence = 0.75
                rationale = (
                    f"Late-stage issue (70%+ complete) + {violation.severity.value} violation"
                )
                risk_level = "low"
                estimated_time_impact = timedelta(minutes=5)
                estimated_cost_impact = 50.0

            elif violation.severity == DeviationSeverity.CRITICAL:
                # Critical violation → ABORT
                replanning_needed = True
                strategy = ReplanningStrategy.ABORT
                confidence = 0.9
                rationale = "Critical violation - cannot continue"
                risk_level = "critical"
                estimated_time_impact = timedelta(0)
                estimated_cost_impact = 0.0

            else:
                # Minor violation - try LOCAL
                replanning_needed = True
                strategy = ReplanningStrategy.LOCAL
                confidence = 0.7
                rationale = f"Single {violation.severity.value} violation"
                risk_level = "low"
                estimated_time_impact = timedelta(minutes=5)
                estimated_cost_impact = 25.0

        elif plan_deviation.deviation_severity == DeviationSeverity.CRITICAL:
            # Critical deviation alone
            replanning_needed = True
            strategy = ReplanningStrategy.SEGMENT
            confidence = 0.8
            rationale = f"Critical time deviation ({plan_deviation.time_deviation_percent:.1f}%)"
            risk_level = "high"
            estimated_time_impact = timedelta(minutes=20)
            estimated_cost_impact = 150.0

        elif plan_deviation.deviation_severity == DeviationSeverity.HIGH:
            # High deviation - SEGMENT if early, LOCAL if late
            if plan_deviation.completion_rate < 0.5:
                replanning_needed = True
                strategy = ReplanningStrategy.SEGMENT
                confidence = 0.75
                rationale = f"High deviation early in execution ({plan_deviation.time_deviation_percent:.1f}%)"
                risk_level = "medium"
                estimated_time_impact = timedelta(minutes=15)
                estimated_cost_impact = 100.0

        affected_tasks = plan_deviation.tasks_at_risk
        recommended_option = 0  # Will be determined when generating options

        evaluation = ReplanningEvaluation(
            replanning_needed=replanning_needed,
            strategy=strategy,
            confidence=confidence,
            rationale=rationale,
            affected_tasks=affected_tasks,
            estimated_time_impact=estimated_time_impact,
            estimated_cost_impact=estimated_cost_impact,
            risk_level=risk_level,
            recommended_option=recommended_option,
            evaluation_time=now,
        )

        self.replanning_evaluations.append(evaluation)
        logger.info(
            f"Replanning evaluation: {strategy.value} "
            f"(needed={replanning_needed}, confidence={confidence:.2f})"
        )

        return evaluation

    def generate_local_adjustment(
        self,
        current_task_id: str,
        current_parameters: Dict[str, Any],
        plan_deviation: PlanDeviation,
    ) -> List[ReplanningOption]:
        """Generate LOCAL adjustment options for current task.

        Args:
            current_task_id: ID of current task
            current_parameters: Current task parameters
            plan_deviation: Current plan deviation

        Returns:
            List of local adjustment options
        """
        options: List[ReplanningOption] = []
        option_id = len(self.replanning_options)

        # Option 1: Add resources to current task
        option1 = ReplanningOption(
            option_id=option_id,
            title="Add resources to current task",
            description=f"Allocate additional resources to {current_task_id} to speed up completion",
            timeline_impact=timedelta(minutes=-5),  # Negative = faster
            cost_impact=50.0,
            resource_impact={"workers": 1, "cpu": 0.25},
            success_probability=0.8,
            implementation_effort="low",
            risks=["Resource contention", "Context switching overhead"],
            benefits=["Faster completion", "Reduced overall delay"],
        )
        options.append(option1)
        option_id += 1

        # Option 2: Reduce scope of current task
        option2 = ReplanningOption(
            option_id=option_id,
            title="Reduce scope of current task",
            description=f"Reduce scope of {current_task_id} to complete faster",
            timeline_impact=timedelta(minutes=-10),
            cost_impact=-30.0,
            resource_impact={"workers": 0},
            success_probability=0.7,
            implementation_effort="medium",
            risks=["Reduced quality", "Possible rework later"],
            benefits=["Faster completion", "Lower cost", "Move forward"],
        )
        options.append(option2)
        option_id += 1

        # Option 3: Extend deadline
        option3 = ReplanningOption(
            option_id=option_id,
            title="Extend overall deadline",
            description="Extend the project deadline to accommodate current delays",
            timeline_impact=timedelta(hours=2),  # Positive = more time
            cost_impact=100.0,
            resource_impact={},
            success_probability=0.95,
            implementation_effort="low",
            risks=["Stakeholder impact", "Constraint violation"],
            benefits=["Lower stress", "Better quality", "Higher success rate"],
        )
        options.append(option3)

        self.replanning_options.extend(options)
        logger.info(f"Generated {len(options)} local adjustment options")
        return options

    def replan_segment(
        self,
        segment_start_index: int,
        segment_size: int = 5,
        plan_deviation: Optional[PlanDeviation] = None,
    ) -> List[ReplanningOption]:
        """Generate SEGMENT replanning options for next N tasks.

        Args:
            segment_start_index: Starting index in task sequence
            segment_size: Number of tasks to replan (default 5)
            plan_deviation: Current plan deviation

        Returns:
            List of segment replanning options
        """
        options: List[ReplanningOption] = []
        option_id = len(self.replanning_options)

        # Option 1: Parallel execution
        option1 = ReplanningOption(
            option_id=option_id,
            title="Execute next tasks in parallel",
            description=f"Parallelize tasks {segment_start_index} to {segment_start_index + segment_size}",
            timeline_impact=timedelta(minutes=-20),
            cost_impact=200.0,
            resource_impact={"workers": 3, "cpu": 1.0},
            success_probability=0.75,
            implementation_effort="medium",
            risks=["Dependency issues", "Resource contention"],
            benefits=["Significant time savings", "Better utilization"],
        )
        options.append(option1)
        option_id += 1

        # Option 2: Task prioritization
        option2 = ReplanningOption(
            option_id=option_id,
            title="Reprioritize task sequence",
            description=f"Reorder tasks {segment_start_index} to {segment_start_index + segment_size} for efficiency",
            timeline_impact=timedelta(minutes=-10),
            cost_impact=0.0,
            resource_impact={},
            success_probability=0.85,
            implementation_effort="low",
            risks=["Dependency violation"],
            benefits=["Better task ordering", "Reduced delays"],
        )
        options.append(option2)
        option_id += 1

        # Option 3: Skip optional tasks
        option3 = ReplanningOption(
            option_id=option_id,
            title="Skip optional tasks",
            description=f"Skip non-critical tasks in segment {segment_start_index} to {segment_start_index + segment_size}",
            timeline_impact=timedelta(minutes=-30),
            cost_impact=-100.0,
            resource_impact={},
            success_probability=0.8,
            implementation_effort="low",
            risks=["Incomplete delivery", "Quality issues"],
            benefits=["Significant time savings", "Cost reduction"],
        )
        options.append(option3)

        self.replanning_options.extend(options)
        logger.info(f"Generated {len(options)} segment replanning options")
        return options

    def full_replan(
        self,
        affected_tasks: List[str],
    ) -> List[ReplanningOption]:
        """Generate FULL replanning options for complete plan.

        Args:
            affected_tasks: List of tasks affected by violations

        Returns:
            List of full replanning options
        """
        options: List[ReplanningOption] = []
        option_id = len(self.replanning_options)

        # Option 1: Complete re-planning with new strategy
        option1 = ReplanningOption(
            option_id=option_id,
            title="Complete re-planning with new strategy",
            description="Generate completely new plan from scratch with adaptive strategy",
            timeline_impact=timedelta(hours=1),
            cost_impact=500.0,
            resource_impact={"workers": 2, "cpu": 2.0},
            success_probability=0.9,
            implementation_effort="high",
            risks=["Significant rework", "Context loss"],
            benefits=["Optimal plan", "Addresses root causes"],
        )
        options.append(option1)
        option_id += 1

        # Option 2: Modular replanning
        option2 = ReplanningOption(
            option_id=option_id,
            title="Modular re-planning",
            description="Replan in modules to minimize disruption",
            timeline_impact=timedelta(minutes=30),
            cost_impact=300.0,
            resource_impact={"workers": 1, "cpu": 1.0},
            success_probability=0.8,
            implementation_effort="medium",
            risks=["Module integration issues"],
            benefits=["Reduced disruption", "Faster replanning"],
        )
        options.append(option2)
        option_id += 1

        # Option 3: Escalation
        option3 = ReplanningOption(
            option_id=option_id,
            title="Escalate to human oversight",
            description="Escalate to human decision-maker for manual replanning",
            timeline_impact=timedelta(hours=2),
            cost_impact=1000.0,
            resource_impact={"workers": 1},
            success_probability=0.95,
            implementation_effort="low",
            risks=["Human error", "Slow decision"],
            benefits=["Expert insight", "High confidence"],
        )
        options.append(option3)

        self.replanning_options.extend(options)
        logger.info(f"Generated {len(options)} full replanning options")
        return options

    def get_replanning_options(self) -> List[ReplanningOption]:
        """Get all generated replanning options.

        Returns:
            List of ReplanningOption objects
        """
        return list(self.replanning_options)

    def select_option(self, option_id: int) -> Optional[ReplanningOption]:
        """Select a replanning option to execute.

        Args:
            option_id: ID of option to select

        Returns:
            Selected option or None if not found
        """
        for option in self.replanning_options:
            if option.option_id == option_id:
                self.selected_option = option
                self.replanning_count += 1
                logger.info(f"Selected replanning option {option_id}: {option.title}")
                return option

        logger.warning(f"Replanning option {option_id} not found")
        return None

    def get_selected_option(self) -> Optional[ReplanningOption]:
        """Get currently selected replanning option.

        Returns:
            Selected option or None
        """
        return self.selected_option

    def reset(self) -> None:
        """Reset for new planning cycle."""
        self.replanning_options.clear()
        self.replanning_evaluations.clear()
        self.selected_option = None
        logger.info("Replanning engine reset")
