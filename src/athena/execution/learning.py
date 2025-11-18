"""Execution Learner - Extract patterns and insights from execution outcomes."""

from typing import Dict, List, Any
import logging
import statistics

from .models import (
    TaskExecutionRecord,
    ExecutionPattern,
    TaskOutcome,
)

logger = logging.getLogger(__name__)


class ExecutionLearner:
    """Learn from execution outcomes and generate recommendations."""

    def __init__(self):
        """Initialize execution learner."""
        self.execution_patterns: Dict[str, ExecutionPattern] = {}
        self.recommendations: List[str] = []
        self.estimation_accuracy: Dict[str, float] = {}  # task_type -> accuracy
        self.bottlenecks: List[tuple[str, float]] = []  # (task_id, impact)

    def extract_execution_patterns(
        self, execution_records: Dict[str, TaskExecutionRecord]
    ) -> List[ExecutionPattern]:
        """Extract patterns from execution records.

        Args:
            execution_records: Dictionary of task execution records

        Returns:
            List of identified patterns
        """
        patterns: List[ExecutionPattern] = []

        if not execution_records:
            return patterns

        # Pattern 1: Task outcome distribution
        outcomes = [r.outcome for r in execution_records.values() if r.outcome]
        success_count = sum(1 for o in outcomes if o == TaskOutcome.SUCCESS)
        failure_count = sum(1 for o in outcomes if o == TaskOutcome.FAILURE)

        if len(outcomes) > 0:
            success_rate = success_count / len(outcomes)
            if success_rate < 0.8:
                pattern = ExecutionPattern(
                    pattern_id="high_failure_rate",
                    description=f"High failure rate: {failure_count}/{len(outcomes)} tasks failed",
                    confidence=0.85,
                    frequency=len(outcomes),
                    affected_tasks=list(execution_records.keys()),
                    impact=-0.3,  # Negative impact
                    actionable=True,
                    recommendation="Review task definitions and resource allocation",
                )
                patterns.append(pattern)

        # Pattern 2: Duration deviations
        records_with_duration = [
            r
            for r in execution_records.values()
            if r.actual_duration is not None and r.planned_duration
        ]

        if len(records_with_duration) > 1:
            deviations = [
                (r.actual_duration.total_seconds() / r.planned_duration.total_seconds())
                for r in records_with_duration
            ]

            avg_deviation = statistics.mean(deviations)
            if len(deviations) > 2:
                stdev = statistics.stdev(deviations)
            else:
                stdev = 0.0

            # Check if tasks consistently take longer
            if avg_deviation > 1.2:  # 20% over estimate
                pattern = ExecutionPattern(
                    pattern_id="estimation_underestimate",
                    description=f"Tasks take {(avg_deviation - 1) * 100:.1f}% longer than estimated",
                    confidence=0.8 if len(records_with_duration) > 3 else 0.6,
                    frequency=len(records_with_duration),
                    affected_tasks=[r.task_id for r in records_with_duration],
                    impact=-0.2,
                    actionable=True,
                    recommendation=f"Add {int((avg_deviation - 1) * 100)}% buffer to future estimates",
                )
                patterns.append(pattern)

        # Pattern 3: Resource utilization
        records_with_resources = [r for r in execution_records.values() if r.resources_used]

        if records_with_resources:
            all_resources = set()
            for r in records_with_resources:
                all_resources.update(r.resources_used.keys())

            for resource in all_resources:
                usages = [
                    (
                        r.resources_used.get(resource, 0)
                        / max(r.resources_planned.get(resource, 1), 0.01)
                    )
                    for r in records_with_resources
                    if r.resources_planned
                ]

                if usages and max(usages) > 0.95:  # Near saturation
                    pattern = ExecutionPattern(
                        pattern_id=f"resource_contention_{resource}",
                        description=f"Resource '{resource}' frequently near saturation ({max(usages):.0%})",
                        confidence=0.75,
                        frequency=sum(1 for u in usages if u > 0.8),
                        affected_tasks=[r.task_id for r in records_with_resources],
                        impact=-0.25,
                        actionable=True,
                        recommendation=f"Pre-allocate additional '{resource}' for future executions",
                    )
                    patterns.append(pattern)

        self.execution_patterns = {p.pattern_id: p for p in patterns}
        logger.info(f"Extracted {len(patterns)} patterns from execution")
        return patterns

    def compute_estimation_accuracy(
        self, execution_records: Dict[str, TaskExecutionRecord]
    ) -> Dict[str, float]:
        """Compute how accurate our time estimates were.

        Args:
            execution_records: Dictionary of task execution records

        Returns:
            Dictionary mapping task_type to accuracy (0.0-1.0)
        """
        accuracy_by_type: Dict[str, List[float]] = {}

        for record in execution_records.values():
            if record.actual_duration is None or record.planned_duration.total_seconds() == 0:
                continue

            # Calculate accuracy: 1.0 = exact, 0.0 = way off
            ratio = record.actual_duration.total_seconds() / record.planned_duration.total_seconds()

            # Convert ratio to accuracy score
            # Perfect: ratio = 1.0 → accuracy = 1.0
            # 2x over: ratio = 2.0 → accuracy = 0.5
            # 0.5x under: ratio = 0.5 → accuracy = 0.5
            if ratio >= 1.0:
                accuracy = 1.0 / ratio
            else:
                accuracy = ratio

            # Categorize by task ID pattern
            task_type = record.task_id.split("_")[0] if "_" in record.task_id else "default"

            if task_type not in accuracy_by_type:
                accuracy_by_type[task_type] = []
            accuracy_by_type[task_type].append(accuracy)

        # Compute average accuracy per type
        result = {}
        for task_type, accuracies in accuracy_by_type.items():
            avg_accuracy = statistics.mean(accuracies)
            result[task_type] = avg_accuracy
            self.estimation_accuracy[task_type] = avg_accuracy

        logger.info(f"Computed estimation accuracy for {len(result)} task types")
        return result

    def identify_bottlenecks(
        self, execution_records: Dict[str, TaskExecutionRecord]
    ) -> List[tuple[str, float]]:
        """Identify which tasks slowed down execution.

        Args:
            execution_records: Dictionary of task execution records

        Returns:
            List of (task_id, impact_score) tuples, sorted by impact
        """
        bottlenecks: List[tuple[str, float]] = []

        records_with_duration = [
            r
            for r in execution_records.values()
            if r.actual_duration is not None and r.planned_duration
        ]

        if not records_with_duration:
            return bottlenecks

        total_actual = sum(r.actual_duration.total_seconds() for r in records_with_duration)

        # Calculate impact of each task as percentage of total time
        for record in records_with_duration:
            if total_actual > 0:
                time_impact = record.actual_duration.total_seconds() / total_actual
            else:
                time_impact = 0.0

            # Also consider deviations
            if record.planned_duration.total_seconds() > 0:
                deviation = (
                    record.actual_duration.total_seconds() / record.planned_duration.total_seconds()
                )
            else:
                deviation = 1.0

            # Combined impact: time spent + how much it deviated
            impact = time_impact * deviation

            if impact > 0.05:  # Only include significant bottlenecks (5%+)
                bottlenecks.append((record.task_id, impact))

        # Sort by impact
        bottlenecks.sort(key=lambda x: x[1], reverse=True)
        self.bottlenecks = bottlenecks

        logger.info(f"Identified {len(bottlenecks)} bottleneck tasks")
        return bottlenecks

    def generate_recommendations(
        self,
        execution_records: Dict[str, TaskExecutionRecord],
    ) -> List[str]:
        """Generate recommendations for improving future executions.

        Args:
            execution_records: Dictionary of task execution records

        Returns:
            List of actionable recommendations
        """
        recommendations: List[str] = []

        # Extract patterns and metrics
        patterns = self.extract_execution_patterns(execution_records)
        accuracy = self.compute_estimation_accuracy(execution_records)
        bottlenecks = self.identify_bottlenecks(execution_records)

        # Recommendation 1: Based on patterns
        for pattern in patterns:
            if pattern.actionable:
                recommendations.append(pattern.recommendation)

        # Recommendation 2: Based on estimation accuracy
        for task_type, acc in accuracy.items():
            if acc < 0.7:
                buffer_needed = int((1 / acc - 1) * 100)
                recommendations.append(
                    f"Increase estimate for '{task_type}' tasks by {buffer_needed}%"
                )

        # Recommendation 3: Based on bottlenecks
        if bottlenecks:
            top_bottleneck = bottlenecks[0]
            if top_bottleneck[1] > 0.15:  # More than 15% of time
                recommendations.append(
                    f"Optimize '{top_bottleneck[0]}' - consumes {top_bottleneck[1]:.0%} of execution time"
                )

        # Recommendation 4: Resource allocation
        successful_tasks = sum(
            1 for r in execution_records.values() if r.outcome == TaskOutcome.SUCCESS
        )
        if successful_tasks < len(execution_records) * 0.8:
            recommendations.append(
                "Review task resource allocation - low success rate indicates insufficient resources"
            )

        # Recommendation 5: Quality improvements
        failed_tasks = [r for r in execution_records.values() if r.outcome == TaskOutcome.FAILURE]
        if failed_tasks:
            recommendations.append(
                f"Investigate {len(failed_tasks)} failed tasks and add preventive measures"
            )

        self.recommendations = recommendations
        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations

    def store_execution_outcome(self, execution_id: str, metadata: Dict[str, Any]) -> None:
        """Store execution outcome for future learning.

        Args:
            execution_id: Unique ID for this execution
            metadata: Metadata about the execution
        """
        logger.info(f"Storing execution outcome {execution_id}")
        # In a real implementation, this would persist to memory layer
        # For now, just log it

    def get_patterns(self) -> List[ExecutionPattern]:
        """Get all extracted patterns.

        Returns:
            List of execution patterns
        """
        return list(self.execution_patterns.values())

    def get_recommendations(self) -> List[str]:
        """Get all generated recommendations.

        Returns:
            List of recommendation strings
        """
        return list(self.recommendations)

    def get_bottlenecks(self) -> List[tuple[str, float]]:
        """Get identified bottlenecks.

        Returns:
            List of (task_id, impact_score) tuples
        """
        return list(self.bottlenecks)

    def reset(self) -> None:
        """Reset for new learning cycle."""
        self.execution_patterns.clear()
        self.recommendations.clear()
        self.estimation_accuracy.clear()
        self.bottlenecks.clear()
        logger.info("Execution learner reset")
