"""Multi-project coordination: dependencies, critical path, and resource management.

Provides:
- Cross-project task dependencies
- Critical path analysis
- Resource conflict detection
- Project timeline synchronization
- Dependency graph visualization
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from ..prospective.models import ProspectiveTask, TaskPhase, TaskStatus
from ..prospective.store import ProspectiveStore

logger = logging.getLogger(__name__)


class ProjectDependency:
    """Dependency between tasks across projects."""

    def __init__(
        self,
        from_task_id: int,
        from_project_id: int,
        to_task_id: int,
        to_project_id: int,
        dependency_type: str,  # blocks, depends_on, related_to
        description: Optional[str] = None,
    ):
        """Initialize project dependency."""
        self.from_task_id = from_task_id
        self.from_project_id = from_project_id
        self.to_task_id = to_task_id
        self.to_project_id = to_project_id
        self.dependency_type = dependency_type
        self.description = description
        self.created_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "from_task_id": self.from_task_id,
            "from_project_id": self.from_project_id,
            "to_task_id": self.to_task_id,
            "to_project_id": self.to_project_id,
            "dependency_type": self.dependency_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


class CriticalPath:
    """Critical path in project network."""

    def __init__(
        self,
        task_ids: list[int],
        total_duration_minutes: float,
        slack_time_minutes: float,
    ):
        """Initialize critical path."""
        self.task_ids = task_ids
        self.total_duration_minutes = total_duration_minutes
        self.slack_time_minutes = slack_time_minutes

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_ids": self.task_ids,
            "total_duration_minutes": self.total_duration_minutes,
            "slack_time_minutes": self.slack_time_minutes,
        }


class ResourceConflict:
    """Detected resource conflict between tasks."""

    def __init__(
        self,
        conflict_type: str,  # time, person, tool, data
        task_ids: list[int],
        description: str,
        severity: str,  # low, medium, high
        recommendation: str,
    ):
        """Initialize resource conflict."""
        self.conflict_type = conflict_type
        self.task_ids = task_ids
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.conflict_type,
            "task_ids": self.task_ids,
            "description": self.description,
            "severity": self.severity,
            "recommendation": self.recommendation,
        }


class ProjectCoordinator:
    """Coordinate tasks and resources across multiple projects."""

    def __init__(self, db: Database):
        """Initialize project coordinator.

        Args:
            db: Database instance
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)
        self.dependencies = []  # In-memory store for cross-project deps

    async def add_dependency(
        self,
        from_task_id: int,
        from_project_id: int,
        to_task_id: int,
        to_project_id: int,
        dependency_type: str,
    ) -> bool:
        """Add a cross-project task dependency.

        Args:
            from_task_id: Task that has the dependency
            from_project_id: Project of from_task
            to_task_id: Task that is depended on
            to_project_id: Project of to_task
            dependency_type: blocks, depends_on, related_to

        Returns:
            True if added successfully
        """
        try:
            dep = ProjectDependency(
                from_task_id=from_task_id,
                from_project_id=from_project_id,
                to_task_id=to_task_id,
                to_project_id=to_project_id,
                dependency_type=dependency_type,
            )
            self.dependencies.append(dep)
            logger.info(
                f"Added dependency: Task {from_task_id} ({dependency_type}) -> Task {to_task_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error adding dependency: {e}")
            return False

    async def get_dependencies(
        self, task_id: Optional[int] = None, project_id: Optional[int] = None
    ) -> list[ProjectDependency]:
        """Get dependencies for a task or project.

        Args:
            task_id: Optional task ID filter
            project_id: Optional project ID filter

        Returns:
            List of matching dependencies
        """
        result = self.dependencies

        if task_id:
            result = [
                d
                for d in result
                if d.from_task_id == task_id or d.to_task_id == task_id
            ]

        if project_id:
            result = [
                d
                for d in result
                if d.from_project_id == project_id or d.to_project_id == project_id
            ]

        return result

    async def analyze_critical_path(self, project_id: int) -> Optional[CriticalPath]:
        """Analyze critical path for project.

        Args:
            project_id: Project ID

        Returns:
            CriticalPath with longest duration tasks
        """
        tasks = self.prospective_store.get_tasks_by_project(project_id)

        if not tasks:
            return None

        # Find longest sequence of tasks (simplified critical path)
        # In a full implementation, this would use proper graph algorithms
        sequenced_tasks = [t for t in tasks if t.phase in [TaskPhase.PLANNING, TaskPhase.EXECUTING]]

        if not sequenced_tasks:
            return None

        # Sort by creation time to approximate sequence
        sequenced_tasks.sort(key=lambda t: t.created_at)

        # Calculate total duration
        total_duration = 0.0
        for task in sequenced_tasks:
            if task.plan and task.plan.estimated_duration_minutes:
                total_duration += task.plan.estimated_duration_minutes
            else:
                total_duration += 30  # Default estimate

        # Calculate slack (how much we can delay without affecting end date)
        total_slack = 0.0
        for task in sequenced_tasks:
            if task.phase_started_at and task.plan:
                elapsed = (datetime.now() - task.phase_started_at).total_seconds() / 60
                slack = max(0, task.plan.estimated_duration_minutes - elapsed)
                total_slack += slack

        return CriticalPath(
            task_ids=[t.id for t in sequenced_tasks],
            total_duration_minutes=total_duration,
            slack_time_minutes=total_slack,
        )

    async def detect_resource_conflicts(
        self, project_ids: list[int]
    ) -> list[ResourceConflict]:
        """Detect resource conflicts across projects.

        Args:
            project_ids: List of project IDs to check

        Returns:
            List of detected conflicts
        """
        conflicts = []
        all_tasks = []

        # Gather all tasks from projects
        for project_id in project_ids:
            all_tasks.extend(self.prospective_store.get_tasks_by_project(project_id))

        # Check for time conflicts (overlapping executions)
        executing_tasks = [t for t in all_tasks if t.phase == TaskPhase.EXECUTING]

        if len(executing_tasks) > 1:
            # Check for same person assigned to multiple tasks
            assignee_tasks = {}
            for task in executing_tasks:
                assignee = task.assignee or "user"
                if assignee not in assignee_tasks:
                    assignee_tasks[assignee] = []
                assignee_tasks[assignee].append(task)

            for assignee, tasks in assignee_tasks.items():
                if len(tasks) > 1:
                    conflicts.append(
                        ResourceConflict(
                            conflict_type="person",
                            task_ids=[t.id for t in tasks],
                            description=f"{assignee} assigned to {len(tasks)} concurrent tasks",
                            severity="high",
                            recommendation=f"Reassign tasks to balance {assignee}'s workload",
                        )
                    )

        # Check for blocked tasks
        blocked_tasks = [t for t in all_tasks if t.blocked_reason]
        if blocked_tasks:
            for task in blocked_tasks:
                conflicts.append(
                    ResourceConflict(
                        conflict_type="blocker",
                        task_ids=[task.id],
                        description=f"Task blocked: {task.blocked_reason}",
                        severity="high",
                        recommendation="Resolve blocking issue to unblock task",
                    )
                )

        return conflicts

    async def get_project_network(self, project_ids: list[int]) -> dict:
        """Get network view of all projects and their dependencies.

        Args:
            project_ids: List of project IDs

        Returns:
            Dictionary with network information
        """
        projects_data = {}
        all_dependencies = []

        for project_id in project_ids:
            tasks = self.prospective_store.get_tasks_by_project(project_id)
            projects_data[project_id] = {
                "task_count": len(tasks),
                "active_tasks": sum(1 for t in tasks if t.phase == TaskPhase.EXECUTING),
                "completed_tasks": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
                "blocked_tasks": sum(1 for t in tasks if t.blocked_reason),
            }

        # Get cross-project dependencies
        all_dependencies = await self.get_dependencies(project_id=None)

        # Filter to only include dependencies between specified projects
        relevant_deps = [
            d
            for d in all_dependencies
            if d.from_project_id in project_ids and d.to_project_id in project_ids
        ]

        return {
            "projects": projects_data,
            "dependencies": [d.to_dict() for d in relevant_deps],
            "dependency_count": len(relevant_deps),
        }

    async def get_resource_allocation(self, project_ids: list[int]) -> dict:
        """Get resource allocation across projects.

        Args:
            project_ids: List of project IDs

        Returns:
            Dictionary with resource allocation
        """
        all_tasks = []

        for project_id in project_ids:
            all_tasks.extend(self.prospective_store.get_tasks_by_project(project_id))

        # Allocate by person
        person_allocation = {}
        for task in all_tasks:
            assignee = task.assignee or "user"
            if assignee not in person_allocation:
                person_allocation[assignee] = {
                    "total_tasks": 0,
                    "active_tasks": 0,
                    "estimated_hours": 0.0,
                }

            person_allocation[assignee]["total_tasks"] += 1

            if task.phase in [TaskPhase.PLANNING, TaskPhase.EXECUTING]:
                person_allocation[assignee]["active_tasks"] += 1

            if task.plan:
                person_allocation[assignee]["estimated_hours"] += task.plan.estimated_duration_minutes / 60

        # Allocate by priority
        priority_allocation = {}
        for task in all_tasks:
            priority_name = (
                task.priority.value if hasattr(task.priority, "value") else str(task.priority)
            )
            if priority_name not in priority_allocation:
                priority_allocation[priority_name] = 0
            priority_allocation[priority_name] += 1

        return {
            "by_person": person_allocation,
            "by_priority": priority_allocation,
            "total_tasks": len(all_tasks),
            "total_resources_hours": sum(
                p["estimated_hours"] for p in person_allocation.values()
            ),
        }

    async def suggest_task_sequencing(self, project_id: int) -> list[dict]:
        """Suggest optimal sequencing of tasks.

        Args:
            project_id: Project ID

        Returns:
            List of suggested task sequences
        """
        tasks = self.prospective_store.get_tasks_by_project(project_id)

        # Group by phase and priority
        suggested_sequence = []

        # First: high priority planning tasks
        planning = [
            t
            for t in tasks
            if t.phase == TaskPhase.PLANNING and str(t.priority).lower() == "high"
        ]
        if planning:
            suggested_sequence.append({
                "group": "High Priority Planning",
                "task_ids": [t.id for t in planning],
                "rationale": "High priority tasks should be planned first",
            })

        # Second: medium/low priority planning
        other_planning = [t for t in tasks if t.phase == TaskPhase.PLANNING and t not in planning]
        if other_planning:
            suggested_sequence.append({
                "group": "Other Planning Tasks",
                "task_ids": [t.id for t in other_planning],
                "rationale": "Complete planning before execution",
            })

        # Third: ready-to-execute tasks
        ready = [t for t in tasks if t.phase == TaskPhase.PLAN_READY]
        if ready:
            suggested_sequence.append({
                "group": "Ready for Execution",
                "task_ids": [t.id for t in ready],
                "rationale": "Execute tasks once planning is complete",
            })

        return suggested_sequence
