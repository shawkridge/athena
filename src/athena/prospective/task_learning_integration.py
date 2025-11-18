"""Integration module for capturing and learning from task execution."""

import logging
from datetime import datetime
from typing import Optional

from ..core.database import Database
from ..core.config import ENABLE_LLM_FEATURES
from .models import ProspectiveTask, TaskPhase, TaskStatus
from .task_patterns import TaskExecutionMetrics
from .task_pattern_store import TaskPatternStore
from .pattern_extraction import PatternExtractor
from .pattern_validator import PatternValidator

logger = logging.getLogger(__name__)


class TaskLearningIntegration:
    """Captures metrics from completed tasks and triggers pattern extraction."""

    def __init__(self, db: Database):
        """Initialize task learning integration.

        Args:
            db: Database instance
        """
        self.db = db
        self.pattern_store = TaskPatternStore(db)
        self.validator = PatternValidator() if ENABLE_LLM_FEATURES else None

    def on_task_completed(self, task: ProspectiveTask, project_id: Optional[int] = None) -> bool:
        """Called when a task completes (in any phase).

        Captures execution metrics and optionally triggers pattern extraction.

        Args:
            task: Completed ProspectiveTask
            project_id: Project ID (if None, uses task.project_id)

        Returns:
            True if metrics captured successfully
        """
        try:
            if not task.completed_at:
                logger.warning(f"Task {task.id} not marked as completed")
                return False

            project_id = project_id or task.project_id

            # Extract metrics from task
            metrics = self._extract_metrics_from_task(task)
            if not metrics:
                logger.warning(f"Could not extract metrics from task {task.id}")
                return False

            # Save metrics
            metrics_id = self.pattern_store.save_execution_metrics(metrics)
            logger.info(f"Captured execution metrics for task {task.id} (metrics_id={metrics_id})")

            # Check if we should trigger pattern extraction
            # Extract after every N completed tasks (e.g., N=10)
            should_extract = self._should_trigger_extraction(project_id)
            if should_extract:
                self._trigger_pattern_extraction(project_id)

            return True

        except Exception as e:
            logger.error(f"Error capturing metrics for task {task.id}: {e}", exc_info=True)
            return False

    def _extract_metrics_from_task(self, task: ProspectiveTask) -> Optional[TaskExecutionMetrics]:
        """Extract execution metrics from a completed task.

        Args:
            task: ProspectiveTask to extract metrics from

        Returns:
            TaskExecutionMetrics or None if extraction fails
        """
        try:
            # Get estimated and actual times
            estimated_minutes = (
                task.plan.estimated_duration_minutes if task.plan else 30  # Default estimate
            )

            if not task.completed_at or not task.created_at:
                return None

            # Total time: from creation to completion
            total_actual_minutes = (task.completed_at - task.created_at).total_seconds() / 60

            # Phase times: extract from phase_metrics if available
            planning_minutes = 0
            plan_ready_minutes = 0
            executing_minutes = 0
            verifying_minutes = 0

            if task.phase_metrics:
                for phase_metric in task.phase_metrics:
                    if phase_metric.completed_at and phase_metric.started_at:
                        duration = (
                            phase_metric.completed_at - phase_metric.started_at
                        ).total_seconds() / 60

                        if phase_metric.phase == TaskPhase.PLANNING:
                            planning_minutes = duration
                        elif phase_metric.phase == TaskPhase.PLAN_READY:
                            plan_ready_minutes = duration
                        elif phase_metric.phase == TaskPhase.EXECUTING:
                            executing_minutes = duration
                        elif phase_metric.phase == TaskPhase.VERIFYING:
                            verifying_minutes = duration

            # Determine success
            success = task.status == TaskStatus.COMPLETED or task.phase == TaskPhase.COMPLETED
            failure_mode = task.failure_reason if not success else None

            # Handle priority - could be enum or string
            priority = "medium"
            if task.priority:
                priority = (
                    task.priority.value if hasattr(task.priority, "value") else str(task.priority)
                )

            metrics = TaskExecutionMetrics(
                task_id=task.id,
                estimated_total_minutes=int(estimated_minutes),
                actual_total_minutes=total_actual_minutes,
                planning_phase_minutes=planning_minutes,
                plan_ready_phase_minutes=plan_ready_minutes,
                executing_phase_minutes=executing_minutes,
                verifying_phase_minutes=verifying_minutes,
                success=success,
                failure_mode=failure_mode,
                priority=priority,
                dependencies_count=0,  # Could be enhanced with dependency store
                has_blockers=task.blocked_reason is not None,
                completed_at=task.completed_at,
            )

            return metrics

        except Exception as e:
            logger.error(f"Error extracting metrics from task {task.id}: {e}", exc_info=True)
            return None

    def _should_trigger_extraction(self, project_id: Optional[int], batch_size: int = 10) -> bool:
        """Determine if we should trigger pattern extraction.

        Extracts patterns after every N completed tasks.

        Args:
            project_id: Project ID
            batch_size: Extract after this many new metrics

        Returns:
            True if should extract patterns now
        """
        try:
            cursor = self.db.get_cursor()

            # Count recent metrics (from last extraction attempt)
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM task_execution_metrics m
                JOIN prospective_tasks t ON m.task_id = t.id
                WHERE t.project_id = %s
                AND m.created_at > (
                    SELECT COALESCE(MAX(last_validated_at), 0)
                    FROM task_patterns
                    WHERE project_id = %s
                    LIMIT 1
                )
            """,
                (project_id, project_id),
            )

            result = cursor.fetchone()
            count = result[0] if result else 0

            return count >= batch_size

        except Exception as e:
            logger.error(f"Error checking extraction trigger: {e}")
            return False

    def _trigger_pattern_extraction(self, project_id: Optional[int]) -> bool:
        """Trigger pattern extraction for a project.

        Args:
            project_id: Project ID to extract patterns for

        Returns:
            True if extraction succeeded
        """
        try:
            logger.info(f"Triggering pattern extraction for project {project_id}")

            # Get recent metrics
            metrics_list = self.pattern_store.get_recent_metrics(project_id or 0, limit=1000)

            if not metrics_list:
                logger.warning(f"No metrics found for project {project_id}")
                return False

            logger.info(f"Extracting patterns from {len(metrics_list)} metrics")

            # Extract patterns using System 1
            extractor = PatternExtractor(self.pattern_store, project_id)
            patterns = extractor.extract_all_patterns(metrics_list)

            # Apply System 2 validation to uncertain patterns
            if self.validator and ENABLE_LLM_FEATURES:
                logger.info("Applying System 2 LLM validation to uncertain patterns")
                patterns = self._apply_system_2_validation(patterns)

            # Save patterns
            for pattern in patterns:
                self.pattern_store.save_pattern(pattern)
                logger.debug(f"Saved pattern: {pattern.pattern_name}")

            # Extract correlations
            correlations = extractor.extract_property_correlations(metrics_list)
            for correlation in correlations:
                self.pattern_store.save_correlation(correlation)
                logger.debug(
                    f"Saved correlation: {correlation.property_name}="
                    f"{correlation.property_value}"
                )

            logger.info(
                f"Pattern extraction complete: {len(patterns)} patterns, "
                f"{len(correlations)} correlations"
            )

            return True

        except Exception as e:
            logger.error(f"Error during pattern extraction: {e}", exc_info=True)
            return False

    def _apply_system_2_validation(self, patterns: list) -> list:
        """Apply System 2 LLM validation to patterns that need it.

        Validates patterns with confidence < 0.8 using LLM.

        Args:
            patterns: List of patterns from System 1 extraction

        Returns:
            Updated patterns with System 2 validation applied
        """
        if not self.validator:
            logger.debug("Validator not available, skipping System 2 validation")
            return patterns

        try:
            # Get existing patterns for contradiction checking
            if patterns and patterns[0].project_id:
                existing = self.pattern_store.get_patterns_by_project(
                    patterns[0].project_id, min_confidence=0.7
                )
            else:
                existing = []

            # Validate batch
            validation_results = self.validator.validate_patterns_batch(patterns, existing)

            # Apply validation results to patterns
            for pattern in patterns:
                if pattern.id in validation_results:
                    result = validation_results[pattern.id]
                    pattern = self.validator.apply_validation_results(pattern, result)
                    logger.debug(
                        f"Applied System 2 validation to {pattern.pattern_name}: "
                        f"confidence {pattern.confidence_score:.2f}"
                    )

            return patterns

        except Exception as e:
            logger.error(f"Error applying System 2 validation: {e}", exc_info=True)
            logger.warning("Proceeding with System 1 patterns only")
            return patterns

    def get_task_history(self, project_id: Optional[int], limit: int = 100) -> list:
        """Get task execution history for a project.

        Args:
            project_id: Project ID
            limit: Maximum number of records

        Returns:
            List of execution metrics with task info
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT
                    t.id, t.content, t.priority, t.status,
                    m.estimated_total_minutes, m.actual_total_minutes,
                    m.estimation_error_percent, m.success, m.failure_mode,
                    m.completed_at
                FROM task_execution_metrics m
                JOIN prospective_tasks t ON m.task_id = t.id
                WHERE t.project_id = %s
                ORDER BY m.completed_at DESC
                LIMIT %s
            """,
                (project_id, limit),
            )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "task_id": row[0],
                        "task_content": row[1],
                        "priority": row[2],
                        "status": row[3],
                        "estimated_minutes": row[4],
                        "actual_minutes": row[5],
                        "error_percent": row[6],
                        "success": row[7],
                        "failure_mode": row[8],
                        "completed_at": datetime.fromtimestamp(row[9] / 1000) if row[9] else None,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error retrieving task history: {e}")
            return []
