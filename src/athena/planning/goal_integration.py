"""
Integration of Goal Decomposition Service with Prospective Memory.

Converts decomposed goals into prospective tasks, handling:
- Task hierarchy flattening to prospective tasks
- Dependency tracking
- Phase management and planning
- Priority inference
- Automatic memory storage
"""

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.planning.models import DecomposedGoal, TaskNode, Goal
from athena.prospective.models import (
    ProspectiveTask,
    TaskStatus,
    TaskPhase,
    TaskPriority,
    Plan,
    TaskDependency,
)
from athena.prospective.store import ProspectiveStore
from athena.prospective.dependencies import DependencyStore

logger = logging.getLogger(__name__)


class GoalIntegrationResult:
    """Result of integrating a decomposed goal into prospective memory."""

    def __init__(
        self,
        success: bool,
        goal_id: str,
        created_task_ids: List[int],
        task_mapping: Dict[str, int],  # TaskNode ID -> ProspectiveTask ID
        dependencies_created: int = 0,
        error_message: Optional[str] = None,
        warnings: List[str] = None,
    ):
        self.success = success
        self.goal_id = goal_id
        self.created_task_ids = created_task_ids
        self.task_mapping = task_mapping
        self.dependencies_created = dependencies_created
        self.error_message = error_message
        self.warnings = warnings or []


class GoalToProspectiveConverter:
    """Converts decomposed goals into prospective tasks."""

    def __init__(self, db: Database):
        """Initialize the converter.

        Args:
            db: Database instance for accessing prospective memory
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)
        self.dependency_store = DependencyStore(db)

    async def integrate_decomposed_goal(
        self,
        decomposed_goal: DecomposedGoal,
        goal: Goal,
        project_id: Optional[int] = None,
        assignee: str = "claude",
        auto_phase_transition: bool = False,
    ) -> GoalIntegrationResult:
        """
        Integrate a decomposed goal into prospective memory.

        Args:
            decomposed_goal: Result from GoalDecompositionService
            goal: Original goal
            project_id: Project context
            assignee: Who will execute these tasks
            auto_phase_transition: Whether to auto-transition phases

        Returns:
            GoalIntegrationResult with task IDs and dependencies
        """
        try:
            logger.info(f"Integrating decomposed goal: {goal.title}")

            # Step 1: Create prospective task for the goal itself
            goal_task = await self._create_goal_task(
                decomposed_goal, goal, project_id, assignee
            )

            # Step 2: Convert TaskNodes to ProspectiveTasks
            task_mapping, prospective_tasks = await self._convert_task_nodes(
                decomposed_goal,
                goal,
                project_id,
                assignee,
                parent_task_id=goal_task.id,
            )

            # Step 3: Save all tasks to database
            created_task_ids = [task.id for task in prospective_tasks if task.id]
            created_task_ids.insert(0, goal_task.id)

            logger.info(
                f"Created {len(created_task_ids)} prospective tasks from decomposition"
            )

            # Step 4: Create dependency relationships
            dependencies_created = await self._create_dependencies(
                task_mapping, decomposed_goal.all_tasks
            )

            # Step 5: Set critical path tasks
            await self._mark_critical_path(task_mapping, decomposed_goal)

            warnings = self._validate_integration(decomposed_goal, created_task_ids)

            return GoalIntegrationResult(
                success=True,
                goal_id=goal.id,
                created_task_ids=created_task_ids,
                task_mapping=task_mapping,
                dependencies_created=dependencies_created,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Failed to integrate decomposed goal: {e}", exc_info=True)
            return GoalIntegrationResult(
                success=False,
                goal_id=goal.id,
                created_task_ids=[],
                task_mapping={},
                error_message=str(e),
            )

    async def _create_goal_task(
        self,
        decomposed_goal: DecomposedGoal,
        goal: Goal,
        project_id: Optional[int],
        assignee: str,
    ) -> ProspectiveTask:
        """Create the main goal task.

        Args:
            decomposed_goal: Decomposed goal
            goal: Original goal
            project_id: Project context
            assignee: Task assignee

        Returns:
            ProspectiveTask for the goal
        """
        # Create a plan from root tasks
        steps = [f"Complete: {task.title}" for task in decomposed_goal.root_tasks]

        plan = Plan(
            steps=steps,
            estimated_duration_minutes=decomposed_goal.total_estimated_effort,
            validated=False,
            validation_notes="Auto-generated from decomposition",
        )

        task = ProspectiveTask(
            project_id=project_id,
            content=f"[GOAL] {goal.title}",
            active_form=f"Completing goal: {goal.title}",
            status=TaskStatus.ACTIVE,
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLAN_READY,  # Goal task starts with plan ready
            plan=plan,
            plan_created_at=datetime.now(),
            phase_started_at=datetime.now(),
            assignee=assignee,
            notes=f"Decomposed into {decomposed_goal.num_tasks} tasks. {goal.description}",
        )

        # Save and get ID
        saved_task = await self.prospective_store.create(task)
        return saved_task

    async def _convert_task_nodes(
        self,
        decomposed_goal: DecomposedGoal,
        goal: Goal,
        project_id: Optional[int],
        assignee: str,
        parent_task_id: int,
    ) -> Tuple[Dict[str, int], List[ProspectiveTask]]:
        """
        Convert TaskNodes to ProspectiveTasks.

        Args:
            decomposed_goal: Decomposed goal with TaskNodes
            goal: Original goal
            project_id: Project context
            assignee: Task assignee
            parent_task_id: Parent goal task ID

        Returns:
            Tuple of (task_mapping, list of created tasks)
        """
        task_mapping = {}
        prospective_tasks = []

        # Group by hierarchy level
        root_tasks = [t for t in decomposed_goal.all_tasks.values() if not t.parent_id]

        for root_task in root_tasks:
            # Create prospective task for this root task
            prospective_task = await self._task_node_to_prospective(
                root_task,
                decomposed_goal,
                project_id,
                assignee,
                parent_task_id,
            )

            task_mapping[root_task.id] = prospective_task.id
            prospective_tasks.append(prospective_task)

            # Process subtasks recursively
            subtask_ids = await self._process_subtasks(
                root_task,
                decomposed_goal,
                project_id,
                assignee,
                task_mapping,
                prospective_task.id,
            )

        return task_mapping, prospective_tasks

    async def _task_node_to_prospective(
        self,
        task_node: TaskNode,
        decomposed_goal: DecomposedGoal,
        project_id: Optional[int],
        assignee: str,
        parent_task_id: int,
    ) -> ProspectiveTask:
        """Convert a TaskNode to a ProspectiveTask.

        Args:
            task_node: TaskNode from decomposition
            decomposed_goal: Parent decomposed goal
            project_id: Project context
            assignee: Task assignee
            parent_task_id: Parent task ID in prospective memory

        Returns:
            ProspectiveTask instance
        """
        # Determine priority from criticality
        priority = self._infer_priority(
            task_node.estimated_complexity,
            task_node.estimated_priority,
            task_node.critical_path,
        )

        # Create plan from subtasks
        plan = self._create_plan_from_task_node(task_node, decomposed_goal)

        # Calculate due date
        due_date = self._calculate_due_date(
            task_node.estimated_effort_minutes
        ) if task_node.estimated_effort_minutes else None

        task = ProspectiveTask(
            project_id=project_id,
            content=f"{task_node.title}",
            active_form=f"Working on {task_node.title.lower()}",
            status=TaskStatus.PENDING,
            priority=priority,
            phase=TaskPhase.PLANNING,  # Leaf tasks start in planning
            plan=plan,
            plan_created_at=datetime.now(),
            phase_started_at=None,
            assignee=assignee,
            notes=task_node.description,
            due_at=due_date,
        )

        # Save to database
        saved_task = await self.prospective_store.create(task)

        logger.debug(
            f"Created prospective task {saved_task.id} for node {task_node.id}: "
            f"{task_node.title}"
        )

        return saved_task

    async def _process_subtasks(
        self,
        parent_task_node: TaskNode,
        decomposed_goal: DecomposedGoal,
        project_id: Optional[int],
        assignee: str,
        task_mapping: Dict[str, int],
        parent_task_id: int,
    ) -> List[int]:
        """Process subtasks recursively.

        Args:
            parent_task_node: Parent TaskNode
            decomposed_goal: Full decomposition
            project_id: Project context
            assignee: Task assignee
            task_mapping: Accumulator for node->task ID mapping
            parent_task_id: Parent task ID in prospective memory

        Returns:
            List of created subtask IDs
        """
        created_ids = []

        for subtask_id in parent_task_node.subtask_ids:
            subtask_node = decomposed_goal.all_tasks.get(subtask_id)
            if not subtask_node:
                logger.warning(f"Subtask {subtask_id} not found in decomposition")
                continue

            prospective_task = await self._task_node_to_prospective(
                subtask_node, decomposed_goal, project_id, assignee, parent_task_id
            )

            task_mapping[subtask_id] = prospective_task.id
            created_ids.append(prospective_task.id)

            # Recursively process further subtasks
            further_subtasks = await self._process_subtasks(
                subtask_node,
                decomposed_goal,
                project_id,
                assignee,
                task_mapping,
                prospective_task.id,
            )
            created_ids.extend(further_subtasks)

        return created_ids

    async def _create_dependencies(
        self,
        task_mapping: Dict[str, int],
        all_tasks: Dict[str, TaskNode],
    ) -> int:
        """Create dependency relationships between tasks.

        Args:
            task_mapping: TaskNode ID -> ProspectiveTask ID mapping
            all_tasks: All TaskNodes from decomposition

        Returns:
            Number of dependencies created
        """
        created_count = 0

        for task_id, task_node in all_tasks.items():
            if task_id not in task_mapping:
                continue

            prospective_task_id = task_mapping[task_id]

            # Parent-child dependency: subtasks depend on parent
            if task_node.parent_id and task_node.parent_id in task_mapping:
                parent_task_id = task_mapping[task_node.parent_id]
                dependency = TaskDependency(
                    task_id=prospective_task_id,
                    depends_on_task_id=parent_task_id,
                    dependency_type="blocks",
                )
                await self.dependency_store.create(dependency)
                created_count += 1

            # Explicit dependencies
            for depends_on_node_id in task_node.depends_on:
                if depends_on_node_id in task_mapping:
                    depends_on_task_id = task_mapping[depends_on_node_id]
                    dependency = TaskDependency(
                        task_id=prospective_task_id,
                        depends_on_task_id=depends_on_task_id,
                        dependency_type="blocks",
                    )
                    await self.dependency_store.create(dependency)
                    created_count += 1

        logger.info(f"Created {created_count} task dependencies")
        return created_count

    async def _mark_critical_path(
        self, task_mapping: Dict[str, int], decomposed_goal: DecomposedGoal
    ) -> None:
        """Mark critical path tasks in prospective memory.

        Args:
            task_mapping: TaskNode ID -> ProspectiveTask ID mapping
            decomposed_goal: Decomposed goal with critical path info
        """
        for task_id, task_node in decomposed_goal.all_tasks.items():
            if not task_node.critical_path or task_id not in task_mapping:
                continue

            prospective_task_id = task_mapping[task_id]
            task = await self.prospective_store.get(prospective_task_id)
            if task:
                # Mark in notes that this is critical
                if not task.notes:
                    task.notes = ""
                task.notes += "\n[CRITICAL PATH]"
                await self.prospective_store.update(prospective_task_id, task)

    def _validate_integration(
        self, decomposed_goal: DecomposedGoal, created_task_ids: List[int]
    ) -> List[str]:
        """Validate the integration result.

        Args:
            decomposed_goal: Decomposed goal
            created_task_ids: Created task IDs

        Returns:
            List of warnings
        """
        warnings = []

        if len(created_task_ids) < decomposed_goal.num_tasks:
            warnings.append(
                f"Only created {len(created_task_ids)} tasks from {decomposed_goal.num_tasks} "
                "decomposed tasks"
            )

        if decomposed_goal.completeness_score < 0.7:
            warnings.append(
                f"Low decomposition completeness: {decomposed_goal.completeness_score:.2%}"
            )

        if decomposed_goal.clarity_score < 0.7:
            warnings.append(
                f"Low decomposition clarity: {decomposed_goal.clarity_score:.2%}"
            )

        return warnings

    @staticmethod
    def _infer_priority(
        complexity: int, original_priority: int, is_critical: bool
    ) -> TaskPriority:
        """Infer task priority from decomposition metrics.

        Args:
            complexity: Complexity score (1-10)
            original_priority: Original priority (1-10)
            is_critical: Whether task is on critical path

        Returns:
            TaskPriority enum value
        """
        if is_critical:
            return TaskPriority.CRITICAL
        elif original_priority >= 8 or complexity >= 8:
            return TaskPriority.HIGH
        elif original_priority >= 5 or complexity >= 5:
            return TaskPriority.MEDIUM
        else:
            return TaskPriority.LOW

    @staticmethod
    def _create_plan_from_task_node(
        task_node: TaskNode, decomposed_goal: DecomposedGoal
    ) -> Plan:
        """Create a Plan from a TaskNode.

        Args:
            task_node: TaskNode with subtasks
            decomposed_goal: Full decomposition for context

        Returns:
            Plan instance
        """
        # Collect subtask steps
        steps = []
        for subtask_id in task_node.subtask_ids:
            subtask = decomposed_goal.all_tasks.get(subtask_id)
            if subtask:
                steps.append(f"Complete: {subtask.title}")

        return Plan(
            steps=steps or ["Execute task"],
            estimated_duration_minutes=task_node.estimated_effort_minutes or 30,
            validated=False,
            validation_notes="Auto-generated from decomposition",
        )

    @staticmethod
    def _calculate_due_date(effort_minutes: int) -> Optional[datetime]:
        """Calculate due date based on effort estimate.

        Args:
            effort_minutes: Estimated effort in minutes

        Returns:
            Suggested due date or None
        """
        if not effort_minutes:
            return None

        # Estimate: 1 day per 8 hours of work
        days = max(1, effort_minutes / (8 * 60))
        return datetime.now() + timedelta(days=days)
