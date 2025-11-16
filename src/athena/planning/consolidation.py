"""Planning pattern consolidation and learning from execution feedback.

Extracts planning patterns from episodic events and execution feedback.
Learns which decomposition strategies work best for different task types.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from collections import defaultdict
import statistics

from .models import (
    PlanningPattern,
    DecompositionStrategy,
    ExecutionFeedback,
    PatternType,
    DecompositionType,
    ExecutionOutcome,
)
from .store import PlanningStore


class PlanningConsolidator:
    """Consolidates execution feedback into improved planning patterns."""

    def __init__(self, planning_store: PlanningStore):
        """Initialize consolidator.

        Args:
            planning_store: PlanningStore instance for CRUD operations
        """
        self.store = planning_store

    def extract_planning_patterns(
        self, project_id: int, min_executions: int = 3
    ) -> List[PlanningPattern]:
        """Extract planning patterns from execution feedback.

        Groups execution feedback by task type and decomposition strategy,
        then creates new PlanningPattern objects based on observed success rates.

        Args:
            project_id: Project ID to analyze
            min_executions: Minimum executions to extract a pattern

        Returns:
            List of extracted PlanningPattern objects (not yet persisted)
        """
        # Get all execution feedback for this project
        cursor = self.store.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM execution_feedback
            WHERE project_id = ?
            ORDER BY created_at
        """,
            (project_id,),
        )
        feedback_rows = cursor.fetchall()

        if not feedback_rows:
            return []

        # Convert rows to ExecutionFeedback objects
        feedback_list = [
            self.store._row_to_execution_feedback(row) for row in feedback_rows
        ]
        feedback_list = [f for f in feedback_list if f]

        if len(feedback_list) < min_executions:
            return []

        # Group by task type + decomposition strategy tag
        grouped = self._group_feedback_by_strategy(feedback_list)

        # Extract patterns from each group
        extracted_patterns = []
        for strategy_key, feedbacks in grouped.items():
            if len(feedbacks) >= min_executions:
                pattern = self._extract_pattern_from_feedback(
                    project_id, strategy_key, feedbacks
                )
                if pattern:
                    extracted_patterns.append(pattern)

        return extracted_patterns

    def calculate_pattern_effectiveness(
        self,
        pattern: PlanningPattern,
        feedback_list: List[ExecutionFeedback],
    ) -> PlanningPattern:
        """Calculate and update pattern effectiveness metrics.

        Updates pattern with:
        - success_rate: Percentage of successful executions
        - quality_score: Average quality across executions
        - execution_count: Total number of executions

        Args:
            pattern: PlanningPattern to update
            feedback_list: List of ExecutionFeedback for this pattern

        Returns:
            Updated PlanningPattern with metrics
        """
        if not feedback_list:
            return pattern

        # Calculate success rate
        successful = sum(
            1
            for f in feedback_list
            if f.execution_outcome == ExecutionOutcome.SUCCESS
        )
        success_rate = successful / len(feedback_list) if feedback_list else 0.0

        # Calculate quality score (average of execution quality scores)
        quality_scores = [f.execution_quality_score for f in feedback_list if f]
        quality_score = (
            statistics.mean(quality_scores) if quality_scores else 0.0
        )

        # Calculate actual vs planned ratio variance
        duration_variances = []
        for f in feedback_list:
            if f.planned_duration_minutes and f.actual_duration_minutes:
                variance = (
                    f.actual_duration_minutes / f.planned_duration_minutes
                )
                duration_variances.append(variance)

        # Determine if this pattern helps with duration estimation
        if duration_variances:
            avg_variance = statistics.mean(duration_variances)
            # Lower variance = more accurate estimates
            pattern.quality_score = quality_score * (1.0 - abs(avg_variance - 1.0))
        else:
            pattern.quality_score = quality_score

        # Update metrics
        pattern.success_rate = success_rate
        pattern.execution_count = len(feedback_list)
        pattern.feedback_count = len(feedback_list)

        # Update last used timestamp
        pattern.last_used = datetime.now()

        return pattern

    def generate_strategy_recommendations(
        self,
        project_id: int,
        task_description: str,
        task_type: str,
        complexity: int = 5,
        limit: int = 3,
    ) -> List[Tuple[DecompositionStrategy, float, str]]:
        """Generate ordered decomposition strategy recommendations.

        Analyzes historical execution feedback to recommend the best
        decomposition strategies for a given task type and complexity.

        Args:
            project_id: Project ID
            task_description: Description of the task
            task_type: Type of task (e.g., 'refactoring', 'feature')
            complexity: Task complexity (1-10 scale)
            limit: Maximum recommendations to return

        Returns:
            List of tuples: (strategy, confidence_score, rationale)
        """
        # Find strategies applicable to this task type
        strategies = self.store.find_strategies_by_type(
            project_id, task_type, limit=10
        )

        if not strategies:
            return []

        # Score each strategy based on execution history
        scored_strategies = []
        for strategy in strategies:
            # Get feedback for this strategy
            cursor = self.store.db.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM execution_feedback
                WHERE project_id = ?
                AND learning_extracted LIKE ?
                ORDER BY created_at DESC
                LIMIT 20
            """,
                (project_id, f"%{strategy.strategy_name}%"),
            )

            feedback_rows = cursor.fetchall()
            feedback_list = [
                self.store._row_to_execution_feedback(row)
                for row in feedback_rows
            ]
            feedback_list = [f for f in feedback_list if f]

            # Calculate confidence score
            if feedback_list:
                # Success rate
                success_rate = strategy.success_rate

                # Accuracy of time estimates (lower is better)
                duration_accuracies = []
                for f in feedback_list:
                    if (
                        f.planned_duration_minutes
                        and f.actual_duration_minutes
                    ):
                        accuracy = min(
                            f.actual_duration_minutes / f.planned_duration_minutes,
                            f.planned_duration_minutes
                            / f.actual_duration_minutes,
                        )
                        duration_accuracies.append(accuracy)

                avg_duration_accuracy = (
                    statistics.mean(duration_accuracies)
                    if duration_accuracies
                    else 0.5
                )

                # Combined confidence
                confidence = (success_rate * 0.6) + (
                    avg_duration_accuracy * 0.4
                )

                # Generate rationale
                rationale = (
                    f"Success rate: {success_rate:.0%}, "
                    f"time estimate accuracy: {avg_duration_accuracy:.0%}, "
                    f"chunk size: {strategy.chunk_size_minutes} min, "
                    f"adaptive depth: {strategy.adaptive_depth}"
                )

                scored_strategies.append(
                    (strategy, confidence, rationale)
                )

        # Sort by confidence descending
        scored_strategies.sort(key=lambda x: x[1], reverse=True)

        # Return top N
        return scored_strategies[:limit]

    def _group_feedback_by_strategy(
        self, feedback_list: List[ExecutionFeedback]
    ) -> dict:
        """Group feedback by strategy/task type combination.

        Args:
            feedback_list: List of ExecutionFeedback objects

        Returns:
            Dict mapping (task_type, strategy) → [feedback, ...]
        """
        grouped = defaultdict(list)

        for feedback in feedback_list:
            # Extract task type and strategy from learning_extracted field
            task_type = "unknown"
            strategy_name = "unknown"

            if feedback.learning_extracted:
                # Parse learning string to extract strategy info
                # Format: "strategy={name},task_type={type},...:
                parts = feedback.learning_extracted.split(",")
                for part in parts:
                    if part.startswith("strategy="):
                        strategy_name = part.split("=", 1)[1].strip()
                    elif part.startswith("task_type="):
                        task_type = part.split("=", 1)[1].strip()

            key = (task_type, strategy_name)
            grouped[key].append(feedback)

        return grouped

    def _extract_pattern_from_feedback(
        self,
        project_id: int,
        strategy_key: Tuple[str, str],
        feedbacks: List[ExecutionFeedback],
    ) -> Optional[PlanningPattern]:
        """Extract a PlanningPattern from grouped feedback.

        Args:
            project_id: Project ID
            strategy_key: (task_type, strategy_name) tuple
            feedbacks: List of ExecutionFeedback for this strategy

        Returns:
            PlanningPattern or None if extraction fails
        """
        task_type, strategy_name = strategy_key

        if not feedbacks:
            return None

        # Calculate metrics
        successful = sum(
            1 for f in feedbacks if f.execution_outcome == ExecutionOutcome.SUCCESS
        )
        success_rate = successful / len(feedbacks)

        quality_scores = [f.execution_quality_score for f in feedbacks]
        quality_score = (
            statistics.mean(quality_scores) if quality_scores else 0.0
        )

        # Determine pattern type based on strategy
        pattern_type = PatternType.HIERARCHICAL  # Default
        if "recursive" in strategy_name.lower():
            pattern_type = PatternType.RECURSIVE
        elif "graph" in strategy_name.lower():
            pattern_type = PatternType.GRAPH_BASED
        elif "hybrid" in strategy_name.lower():
            pattern_type = PatternType.HYBRID
        elif "flat" in strategy_name.lower():
            pattern_type = PatternType.FLAT

        # Create pattern
        try:
            pattern = PlanningPattern(
                project_id=project_id,
                pattern_type=pattern_type,
                name=f"{task_type}-{strategy_name}",
                description=f"Learned from {len(feedbacks)} executions of {task_type} using {strategy_name}",
                success_rate=success_rate,
                quality_score=quality_score,
                execution_count=len(feedbacks),
                applicable_domains=["learned"],
                applicable_task_types=[task_type],
                conditions={
                    "task_type": task_type,
                    "strategy": strategy_name,
                    "min_executions": len(feedbacks),
                },
                source="learned",
            )
            return pattern
        except (OSError, ValueError, TypeError, KeyError, IndexError):
            return None


def extract_planning_patterns(
    planning_store: PlanningStore,
    project_id: int,
    min_executions: int = 3,
) -> List[PlanningPattern]:
    """Extract planning patterns from execution feedback.

    Convenience function that creates a consolidator and extracts patterns.

    Args:
        planning_store: PlanningStore instance
        project_id: Project ID to analyze
        min_executions: Minimum executions to extract a pattern

    Returns:
        List of extracted PlanningPattern objects
    """
    consolidator = PlanningConsolidator(planning_store)
    return consolidator.extract_planning_patterns(project_id, min_executions)


def calculate_pattern_effectiveness(
    planning_store: PlanningStore,
    pattern: PlanningPattern,
    pattern_id: int,
) -> PlanningPattern:
    """Calculate effectiveness metrics for a pattern.

    Convenience function that calculates effectiveness and updates the pattern.

    Args:
        planning_store: PlanningStore instance
        pattern: PlanningPattern to update
        pattern_id: ID of pattern to fetch feedback for

    Returns:
        Updated PlanningPattern
    """
    consolidator = PlanningConsolidator(planning_store)

    # Get all feedback for this pattern
    feedback_list = planning_store.get_feedback_for_pattern(pattern_id, limit=50)

    # Calculate effectiveness
    return consolidator.calculate_pattern_effectiveness(pattern, feedback_list)


def generate_strategy_recommendations(
    planning_store: PlanningStore,
    project_id: int,
    task_description: str,
    task_type: str,
    complexity: int = 5,
    limit: int = 3,
) -> List[Tuple[DecompositionStrategy, float, str]]:
    """Generate strategy recommendations.

    Convenience function that generates recommendations.

    Args:
        planning_store: PlanningStore instance
        project_id: Project ID
        task_description: Description of the task
        task_type: Type of task
        complexity: Task complexity (1-10)
        limit: Maximum recommendations

    Returns:
        List of tuples: (strategy, confidence_score, rationale)
    """
    consolidator = PlanningConsolidator(planning_store)
    return consolidator.generate_strategy_recommendations(
        project_id, task_description, task_type, complexity, limit
    )
