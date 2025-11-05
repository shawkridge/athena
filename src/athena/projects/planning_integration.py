"""Integration of planning patterns with project structure."""

from datetime import datetime
from typing import Optional, Dict, List

from .models import ProjectPlan, PhasePlan, TaskStatusModel, Milestone, ProjectDependency


class PlanningIntegration:
    """Integrate planning patterns with project execution tracking."""

    def __init__(self, db=None):
        """Initialize planning integration.

        Args:
            db: Database instance for persistence
        """
        self.db = db
        # In-memory storage for demo/testing
        self._task_pattern_links: Dict = {}
        self._task_feedback: Dict = {}

    def link_task_to_pattern(
        self,
        task_id: int,
        pattern_id: int,
        pattern_type: str = "planning_pattern"
    ) -> Dict:
        """Link a task to a planning pattern.

        Args:
            task_id: Task ID
            pattern_id: Pattern ID (from planning store)
            pattern_type: Type of pattern (planning_pattern|decomposition_strategy|orchestration_pattern)

        Returns:
            Link record with metadata
        """
        link = {
            "task_id": task_id,
            "pattern_id": pattern_id,
            "pattern_type": pattern_type,
            "linked_at": datetime.now(),
            "effectiveness": None,  # Will be updated after execution
        }

        key = f"task_{task_id}_pattern_{pattern_id}"
        self._task_pattern_links[key] = link

        if self.db:
            # Persist to database
            pass

        return link

    def record_task_completion(
        self,
        task_id: int,
        actual_duration_minutes: int,
        completion_metrics: Optional[Dict] = None,
        blockers: Optional[List] = None,
        quality_score: Optional[float] = None,
    ) -> Dict:
        """Record task completion and calculate variance.

        Args:
            task_id: Task ID
            actual_duration_minutes: Actual duration in minutes
            completion_metrics: Task-specific metrics
            blockers: Any blockers encountered
            quality_score: Quality assessment (0-1)

        Returns:
            Completion record with variance calculations
        """
        feedback = {
            "task_id": task_id,
            "actual_duration_minutes": actual_duration_minutes,
            "completion_metrics": completion_metrics or {},
            "blockers": blockers or [],
            "quality_score": quality_score or 0.0,
            "recorded_at": datetime.now(),
            "duration_variance_pct": 0.0,
        }

        self._task_feedback[task_id] = feedback

        if self.db:
            # Persist to database
            pass

        return feedback

    def validate_milestone(self, milestone: Milestone) -> Dict:
        """Validate milestone prerequisites before transition.

        Args:
            milestone: Milestone to validate

        Returns:
            Validation result with status and issues
        """
        validation_result = {
            "milestone_id": milestone.id,
            "valid": True,
            "issues": [],
            "warnings": [],
            "checked_at": datetime.now(),
        }

        # Check task dependencies are completed
        for task_id in milestone.depends_on_task_ids:
            feedback = self._task_feedback.get(task_id)
            if not feedback:
                validation_result["issues"].append(
                    f"Dependent task {task_id} not completed"
                )
                validation_result["valid"] = False

        # Check milestone dependencies are met
        # (In full implementation, would query milestone store)

        # Check assumptions
        if milestone.assumptions:
            # In full implementation, would verify each assumption
            validation_result["warnings"].append(
                f"Verify {len(milestone.assumptions)} assumptions before proceeding"
            )

        return validation_result

    def get_task_pattern_link(self, task_id: int) -> Optional[dict]:
        """Get the pattern linked to a task.

        Args:
            task_id: Task ID

        Returns:
            Link record if exists, None otherwise
        """
        for key, link in self._task_pattern_links.items():
            if link["task_id"] == task_id:
                return link
        return None

    def calculate_plan_vs_actual(
        self,
        phase: PhasePlan,
    ) -> Dict:
        """Calculate plan vs actual variance for a phase.

        Args:
            phase: Phase to analyze

        Returns:
            Variance analysis
        """
        analysis = {
            "phase_id": phase.id,
            "phase_number": phase.phase_number,
            "planned_duration_days": phase.planned_duration_days,
            "actual_duration_days": phase.actual_duration_days,
            "variance_percentage": 0.0,
            "status": "pending",
            "quality_score": phase.quality_score,
        }

        if phase.actual_duration_days:
            variance = (
                (phase.actual_duration_days - phase.planned_duration_days) /
                phase.planned_duration_days * 100
            )
            analysis["variance_percentage"] = variance

        return analysis

    def update_task_quality_score(
        self,
        task: TaskStatusModel,
        completion_metrics: Dict,
    ) -> float:
        """Update task quality score based on completion metrics.

        Args:
            task: Task model
            completion_metrics: Metrics from execution

        Returns:
            Updated quality score (0-1)
        """
        score = 0.0
        weights = {
            "code_coverage": 0.3,
            "test_pass_rate": 0.3,
            "performance": 0.2,
            "security_audit": 0.2,
        }

        for metric_name, metric_value in completion_metrics.items():
            weight = weights.get(metric_name, 0.0)
            if weight > 0 and isinstance(metric_value, (int, float)):
                # Normalize metric to 0-1 range
                normalized = min(1.0, max(0.0, metric_value))
                score += normalized * weight

        return score

    def get_project_progress(
        self,
        project_plan: ProjectPlan,
        phases: List[PhasePlan],
        tasks: List[TaskStatusModel],
    ) -> Dict:
        """Calculate comprehensive project progress.

        Args:
            project_plan: Project plan
            phases: List of phases
            tasks: List of tasks

        Returns:
            Progress summary
        """
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        in_progress_tasks = len([t for t in tasks if t.status == "in_progress"])

        total_phases = len(phases)
        completed_phases = len([p for p in phases if p.status == "completed"])

        schedule_variance = 0.0
        if project_plan.actual_duration_days and project_plan.estimated_duration_days:
            schedule_variance = (
                (project_plan.actual_duration_days - project_plan.estimated_duration_days) /
                project_plan.estimated_duration_days * 100
            )

        # Calculate average quality
        quality_scores = [t.quality_score for t in tasks if t.quality_score > 0]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        progress = {
            "project_id": project_plan.project_id,
            "phases_complete_percentage": (completed_phases / total_phases * 100) if total_phases > 0 else 0.0,
            "tasks_complete_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0,
            "tasks_in_progress": in_progress_tasks,
            "schedule_variance_percentage": schedule_variance,
            "quality_score": avg_quality,
            "overall_progress_percentage": (
                (completed_phases / total_phases * 0.4 + completed_tasks / total_tasks * 0.6 * 100)
                if total_phases > 0 and total_tasks > 0
                else 0.0
            ),
            "status": "on_track" if schedule_variance < 20 else "at_risk" if schedule_variance < 50 else "off_track",
        }

        return progress

    def recommend_replanning_trigger(
        self,
        phase: PhasePlan,
        current_progress_pct: float,
    ) -> Dict:
        """Determine if replanning is needed based on progress.

        Args:
            phase: Phase being executed
            current_progress_pct: Current progress percentage

        Returns:
            Replanning recommendation
        """
        recommendation = {
            "phase_id": phase.id,
            "trigger_replanning": False,
            "reason": None,
            "confidence": 0.0,
        }

        # Heuristic: if at 50% time but <25% progress, trigger replanning
        if current_progress_pct < 25 and phase.actual_duration_days:
            expected_progress_at_50_pct_time = 50.0
            if current_progress_pct < expected_progress_at_50_pct_time * 0.5:
                recommendation["trigger_replanning"] = True
                recommendation["reason"] = "Progress falling behind schedule"
                recommendation["confidence"] = 0.85

        return recommendation
