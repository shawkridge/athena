"""Pattern extraction from task execution metrics using System 1 (fast, statistical) approach."""

import json
import logging
from collections import defaultdict
from datetime import datetime
from statistics import mean, stdev
from typing import List, Dict, Any, Tuple

from .task_patterns import (
    TaskPattern,
    TaskExecutionMetrics,
    TaskPropertyCorrelation,
    PatternType,
    ExtractionMethod,
    PatternStatus,
)
from .task_pattern_store import TaskPatternStore

logger = logging.getLogger(__name__)


class PatternExtractor:
    """Extracts patterns from task execution metrics using fast statistical methods."""

    MIN_SAMPLE_SIZE = 5  # Minimum tasks needed to extract pattern
    HIGH_CONFIDENCE_THRESHOLD = 0.8  # Success rate for "high confidence" patterns
    MODERATE_CONFIDENCE_THRESHOLD = 0.65

    def __init__(self, store: TaskPatternStore, project_id: int):
        """Initialize pattern extractor.

        Args:
            store: TaskPatternStore instance
            project_id: Project to analyze patterns for
        """
        self.store = store
        self.project_id = project_id

    def extract_all_patterns(
        self, metrics_list: List[TaskExecutionMetrics]
    ) -> List[TaskPattern]:
        """Extract all patterns from a list of execution metrics.

        This is System 1: Fast, statistical extraction without LLM.

        Args:
            metrics_list: List of TaskExecutionMetrics to analyze

        Returns:
            List of extracted TaskPattern objects
        """
        if not metrics_list or len(metrics_list) < self.MIN_SAMPLE_SIZE:
            logger.warning(
                f"Not enough metrics to extract patterns: {len(metrics_list)} < {self.MIN_SAMPLE_SIZE}"
            )
            return []

        patterns = []

        # Extract different types of patterns
        patterns.extend(self._extract_priority_patterns(metrics_list))
        patterns.extend(self._extract_duration_patterns(metrics_list))
        patterns.extend(self._extract_phase_duration_patterns(metrics_list))
        patterns.extend(self._extract_complexity_patterns(metrics_list))
        patterns.extend(self._extract_dependency_patterns(metrics_list))

        logger.info(f"Extracted {len(patterns)} patterns from {len(metrics_list)} metrics")
        return patterns

    def _extract_priority_patterns(
        self, metrics_list: List[TaskExecutionMetrics]
    ) -> List[TaskPattern]:
        """Extract patterns about priority and success rate.

        Example: "High priority tasks have 85% success rate"
        """
        patterns = []

        # Group by priority
        by_priority = defaultdict(list)
        for m in metrics_list:
            by_priority[m.priority].append(m)

        for priority, metrics in by_priority.items():
            if len(metrics) < self.MIN_SAMPLE_SIZE:
                continue

            successful = sum(1 for m in metrics if m.success)
            success_rate = successful / len(metrics)

            # Only create pattern if success rate differs meaningfully from overall
            overall_success = sum(1 for m in metrics_list if m.success) / len(metrics_list)
            if abs(success_rate - overall_success) < 0.1:  # Less than 10% difference
                continue

            confidence = self._calculate_confidence(len(metrics), success_rate)

            pattern = TaskPattern(
                project_id=self.project_id,
                pattern_name=f"{priority}_priority_success_pattern",
                pattern_type=PatternType.SUCCESS_RATE,
                description=f"Tasks with {priority} priority have {success_rate:.1%} success rate",
                condition_json=json.dumps({"priority": priority}),
                prediction=f"{success_rate:.1%} success rate",
                sample_size=len(metrics),
                confidence_score=confidence,
                success_rate=success_rate,
                failure_count=len(metrics) - successful,
                extraction_method=ExtractionMethod.STATISTICAL,
                status=PatternStatus.ACTIVE,
                learned_from_tasks=json.dumps([m.task_id for m in metrics]),
            )

            patterns.append(pattern)
            logger.debug(
                f"Extracted priority pattern: {priority} → {success_rate:.1%} success"
                f" (confidence: {confidence:.2f})"
            )

        return patterns

    def _extract_duration_patterns(
        self, metrics_list: List[TaskExecutionMetrics]
    ) -> List[TaskPattern]:
        """Extract patterns about total task duration.

        Example: "Tasks estimated >2 hours have 90% success rate"
        """
        patterns = []

        # Group by estimated duration ranges
        short_tasks = [m for m in metrics_list if m.estimated_total_minutes <= 60]
        medium_tasks = [m for m in metrics_list if 60 < m.estimated_total_minutes <= 240]
        long_tasks = [m for m in metrics_list if m.estimated_total_minutes > 240]

        for label, tasks in [("short", short_tasks), ("medium", medium_tasks), ("long", long_tasks)]:
            if len(tasks) < self.MIN_SAMPLE_SIZE:
                continue

            successful = sum(1 for t in tasks if t.success)
            success_rate = successful / len(tasks)

            if label == "short":
                min_min, max_min = 0, 60
                condition = {"estimated_minutes_max": 60}
            elif label == "medium":
                min_min, max_min = 60, 240
                condition = {"estimated_minutes_min": 60, "estimated_minutes_max": 240}
            else:
                min_min, max_min = 240, 999999
                condition = {"estimated_minutes_min": 240}

            confidence = self._calculate_confidence(len(tasks), success_rate)

            pattern = TaskPattern(
                project_id=self.project_id,
                pattern_name=f"{label}_duration_pattern",
                pattern_type=PatternType.DURATION,
                description=f"{label.capitalize()} tasks ({min_min}-{max_min} min est.) have {success_rate:.1%} success",
                condition_json=json.dumps(condition),
                prediction=f"{success_rate:.1%} success rate for {label} tasks",
                sample_size=len(tasks),
                confidence_score=confidence,
                success_rate=success_rate,
                failure_count=len(tasks) - successful,
                extraction_method=ExtractionMethod.STATISTICAL,
                status=PatternStatus.ACTIVE,
                learned_from_tasks=json.dumps([m.task_id for m in tasks]),
            )

            patterns.append(pattern)
            logger.debug(
                f"Extracted duration pattern: {label} → {success_rate:.1%} success"
                f" (n={len(tasks)})"
            )

        return patterns

    def _extract_phase_duration_patterns(
        self, metrics_list: List[TaskExecutionMetrics]
    ) -> List[TaskPattern]:
        """Extract patterns about specific phase durations.

        Example: "Planning phase >2 hours correlates with 90% success"
        """
        patterns = []

        # Analyze planning phase impact
        with_long_planning = [m for m in metrics_list if m.planning_phase_minutes >= 120]
        with_short_planning = [m for m in metrics_list if m.planning_phase_minutes < 120]

        for label, tasks in [("long_planning", with_long_planning), ("short_planning", with_short_planning)]:
            if len(tasks) < self.MIN_SAMPLE_SIZE:
                continue

            successful = sum(1 for t in tasks if t.success)
            success_rate = successful / len(tasks)

            condition = {"planning_phase_minutes_min": 120} if label == "long_planning" else {"planning_phase_minutes_max": 120}
            confidence = self._calculate_confidence(len(tasks), success_rate)

            pattern = TaskPattern(
                project_id=self.project_id,
                pattern_name=f"{label}_phase_pattern",
                pattern_type=PatternType.PHASE_CORRELATION,
                description=f"Tasks with {label} (120+ min) have {success_rate:.1%} success",
                condition_json=json.dumps(condition),
                prediction=f"{success_rate:.1%} success with {label}",
                sample_size=len(tasks),
                confidence_score=confidence,
                success_rate=success_rate,
                failure_count=len(tasks) - successful,
                extraction_method=ExtractionMethod.STATISTICAL,
                status=PatternStatus.ACTIVE,
                learned_from_tasks=json.dumps([m.task_id for m in tasks]),
            )

            patterns.append(pattern)
            logger.debug(
                f"Extracted phase pattern: {label} → {success_rate:.1%} success"
                f" (n={len(tasks)})"
            )

        return patterns

    def _extract_complexity_patterns(
        self, metrics_list: List[TaskExecutionMetrics]
    ) -> List[TaskPattern]:
        """Extract patterns about task complexity."""
        patterns = []

        # Filter tasks with complexity estimates
        estimated_tasks = [m for m in metrics_list if m.complexity_estimate is not None]
        if len(estimated_tasks) < self.MIN_SAMPLE_SIZE:
            return patterns

        # Group by complexity
        by_complexity = defaultdict(list)
        for m in estimated_tasks:
            by_complexity[m.complexity_estimate].append(m)

        for complexity, tasks in sorted(by_complexity.items()):
            if len(tasks) < self.MIN_SAMPLE_SIZE:
                continue

            successful = sum(1 for t in tasks if t.success)
            success_rate = successful / len(tasks)

            confidence = self._calculate_confidence(len(tasks), success_rate)

            pattern = TaskPattern(
                project_id=self.project_id,
                pattern_name=f"complexity_{complexity}_pattern",
                pattern_type=PatternType.SUCCESS_RATE,
                description=f"Tasks with complexity {complexity}/5 have {success_rate:.1%} success",
                condition_json=json.dumps({"complexity_estimate": complexity}),
                prediction=f"{success_rate:.1%} success for complexity {complexity}",
                sample_size=len(tasks),
                confidence_score=confidence,
                success_rate=success_rate,
                failure_count=len(tasks) - successful,
                extraction_method=ExtractionMethod.STATISTICAL,
                status=PatternStatus.ACTIVE,
                learned_from_tasks=json.dumps([m.task_id for m in tasks]),
            )

            patterns.append(pattern)

        return patterns

    def _extract_dependency_patterns(
        self, metrics_list: List[TaskExecutionMetrics]
    ) -> List[TaskPattern]:
        """Extract patterns about task dependencies."""
        patterns = []

        # Group by dependency count
        no_deps = [m for m in metrics_list if m.dependencies_count == 0]
        with_deps = [m for m in metrics_list if m.dependencies_count > 0]

        for label, tasks in [("no_dependencies", no_deps), ("with_dependencies", with_deps)]:
            if len(tasks) < self.MIN_SAMPLE_SIZE:
                continue

            successful = sum(1 for t in tasks if t.success)
            success_rate = successful / len(tasks)

            condition = (
                {"dependencies_count": 0} if label == "no_dependencies" else
                {"dependencies_count_min": 1}
            )
            confidence = self._calculate_confidence(len(tasks), success_rate)

            pattern = TaskPattern(
                project_id=self.project_id,
                pattern_name=f"{label}_pattern",
                pattern_type=PatternType.SUCCESS_RATE,
                description=f"Tasks {label} have {success_rate:.1%} success rate",
                condition_json=json.dumps(condition),
                prediction=f"{success_rate:.1%} success",
                sample_size=len(tasks),
                confidence_score=confidence,
                success_rate=success_rate,
                failure_count=len(tasks) - successful,
                extraction_method=ExtractionMethod.STATISTICAL,
                status=PatternStatus.ACTIVE,
                learned_from_tasks=json.dumps([m.task_id for m in tasks]),
            )

            patterns.append(pattern)
            logger.debug(
                f"Extracted dependency pattern: {label} → {success_rate:.1%} success"
                f" (n={len(tasks)})"
            )

        return patterns

    def _calculate_confidence(self, sample_size: int, success_rate: float) -> float:
        """Calculate confidence score for a pattern.

        Combines:
        1. Sample size confidence (larger samples = more confidence)
        2. Success rate extremeness (patterns with extreme rates are less certain)

        Returns:
            Confidence score 0.0-1.0
        """
        # Sample size confidence (increases with n, plateaus at 100)
        sample_confidence = min(sample_size / 100, 1.0)

        # Success rate confidence (more extreme rates = less confident due to regression to mean)
        # Confidence is highest at 50% (most uncertain) and decreases toward 0% or 100%
        # We want opposite: 100% or 0% success = high confidence
        rate_confidence = 1.0 - (abs(success_rate - 0.5) * 2 - 0.5) ** 2

        # Combine: both factors matter, but sample size matters more
        combined = (sample_confidence * 0.7) + (rate_confidence * 0.3)

        return min(max(combined, 0.0), 1.0)

    def extract_property_correlations(
        self, metrics_list: List[TaskExecutionMetrics]
    ) -> List[TaskPropertyCorrelation]:
        """Extract property correlations from metrics.

        Analyzes which property values correlate with success/failure.
        """
        correlations = []

        # Analyze priority
        by_priority = defaultdict(list)
        for m in metrics_list:
            by_priority[m.priority].append(m)

        for priority, tasks in by_priority.items():
            if len(tasks) < self.MIN_SAMPLE_SIZE:
                continue

            successful = sum(1 for t in tasks if t.success)
            failed = len(tasks) - successful

            avg_estimated = mean([t.estimated_total_minutes for t in tasks])
            avg_actual = mean([t.actual_total_minutes for t in tasks])
            estimation_accuracy = 100 - (
                abs(avg_actual - avg_estimated) / avg_estimated * 100
            ) if avg_estimated > 0 else 0

            correlation = TaskPropertyCorrelation(
                project_id=self.project_id,
                property_name="priority",
                property_value=priority,
                total_tasks=len(tasks),
                successful_tasks=successful,
                failed_tasks=failed,
                success_rate=successful / len(tasks),
                sample_size=len(tasks),
                confidence_level=self._calculate_confidence(len(tasks), successful / len(tasks)),
                avg_estimated_minutes=avg_estimated,
                avg_actual_minutes=avg_actual,
                estimation_accuracy_percent=max(estimation_accuracy, 0),
            )

            correlations.append(correlation)

        logger.info(f"Extracted {len(correlations)} property correlations")
        return correlations
