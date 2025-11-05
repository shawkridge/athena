"""
Workflow Manager for Phase 4 Integration Orchestrator.

Manages task workflows, agent coordination, and execution sequencing.
"""

import logging
import uuid
from typing import Optional
from datetime import datetime
from collections import defaultdict

from .orchestrator_models import (
    TaskWorkflow,
    WorkflowStep,
    WorkflowPhase,
)

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages task workflows and agent coordination."""

    def __init__(self):
        """Initialize workflow manager."""
        self.workflows: dict[str, TaskWorkflow] = {}
        self.step_dependencies: dict[str, set[str]] = defaultdict(set)
        self.step_results: dict[str, dict] = {}
        self.completed_steps: set[str] = set()
        self.failed_steps: set[str] = set()
        self.max_retries = 3

    def create_workflow(self, task_id: int, task_type: str, priority: int = 5) -> TaskWorkflow:
        """Create a new task workflow.

        Args:
            task_id: Task identifier
            task_type: Type of task
            priority: Priority level (1-10)

        Returns:
            Created TaskWorkflow
        """
        workflow_id = str(uuid.uuid4())
        workflow = TaskWorkflow(
            workflow_id=workflow_id,
            task_id=task_id,
            task_type=task_type,
            priority=priority,
        )
        self.workflows[workflow_id] = workflow
        logger.info(f"Created workflow {workflow_id} for task {task_id}")
        return workflow

    def add_step(
        self,
        workflow_id: str,
        agent_type: str,
        action: str,
        dependencies: Optional[list[str]] = None,
    ) -> WorkflowStep:
        """Add a step to a workflow.

        Args:
            workflow_id: Workflow identifier
            agent_type: Type of agent (planner, executor, etc.)
            action: Action to perform
            dependencies: List of step IDs this depends on

        Returns:
            Created WorkflowStep
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        workflow = self.workflows[workflow_id]
        step_id = f"{workflow_id}:{agent_type}:{len(workflow.steps)}"

        step = WorkflowStep(
            step_id=step_id,
            agent_type=agent_type,
            action=action,
            dependencies=dependencies or [],
        )

        workflow.steps.append(step)

        # Register dependencies
        for dep_id in (dependencies or []):
            self.step_dependencies[step_id].add(dep_id)

        logger.info(f"Added step {step_id} to workflow {workflow_id}")
        return step

    def get_next_executable_step(self, workflow_id: str) -> Optional[WorkflowStep]:
        """Get the next executable step in a workflow.

        Returns None if all steps are complete or if all waiting steps have
        unmet dependencies.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Next executable WorkflowStep or None
        """
        if workflow_id not in self.workflows:
            return None

        workflow = self.workflows[workflow_id]

        for step in workflow.steps:
            # Skip already completed or failed steps
            if step.status in [WorkflowPhase.COMPLETE]:
                continue
            if step.step_id in self.failed_steps:
                continue

            # Check dependencies
            all_deps_complete = all(
                dep_id in self.completed_steps
                for dep_id in step.dependencies
            )

            if all_deps_complete and step.status == WorkflowPhase.PENDING:
                return step

        return None

    def mark_step_started(self, step_id: str):
        """Mark a step as started.

        Args:
            step_id: Step identifier
        """
        for workflow in self.workflows.values():
            for step in workflow.steps:
                if step.step_id == step_id:
                    step.status = WorkflowPhase.EXECUTION
                    step.execution_time_ms = 0.0
                    logger.info(f"Step {step_id} started")
                    return

    def mark_step_completed(self, step_id: str, output_data: dict, execution_time_ms: float = 0.0):
        """Mark a step as completed.

        Args:
            step_id: Step identifier
            output_data: Output data from step
            execution_time_ms: Time taken to execute
        """
        for workflow in self.workflows.values():
            for step in workflow.steps:
                if step.step_id == step_id:
                    step.status = WorkflowPhase.COMPLETE
                    step.output_data = output_data
                    step.execution_time_ms = execution_time_ms
                    self.completed_steps.add(step_id)
                    self.step_results[step_id] = output_data
                    logger.info(f"Step {step_id} completed in {execution_time_ms:.1f}ms")
                    return

    def mark_step_failed(self, step_id: str, error_message: str):
        """Mark a step as failed.

        Args:
            step_id: Step identifier
            error_message: Error message
        """
        for workflow in self.workflows.values():
            for step in workflow.steps:
                if step.step_id == step_id:
                    if step.retry_count < step.max_retries:
                        # Retry
                        step.retry_count += 1
                        step.status = WorkflowPhase.PENDING
                        step.error_message = None
                        logger.info(f"Step {step_id} retry {step.retry_count}/{step.max_retries}")
                    else:
                        # Give up
                        step.status = WorkflowPhase.FAILED
                        step.error_message = error_message
                        self.failed_steps.add(step_id)
                        logger.error(f"Step {step_id} failed: {error_message}")
                    return

    def update_workflow_progress(self, workflow_id: str):
        """Update overall workflow progress.

        Args:
            workflow_id: Workflow identifier
        """
        if workflow_id not in self.workflows:
            return

        workflow = self.workflows[workflow_id]

        # Count steps
        total_steps = len(workflow.steps)
        completed_count = sum(
            1 for step in workflow.steps if step.status == WorkflowPhase.COMPLETE
        )
        failed_count = sum(
            1 for step in workflow.steps if step.status == WorkflowPhase.FAILED
        )

        # Update completion percentage
        if total_steps > 0:
            workflow.completion_percentage = (completed_count / total_steps) * 100.0

        # Update overall status
        if failed_count > 0:
            workflow.overall_status = "failed"
            workflow.current_phase = WorkflowPhase.FAILED
        elif completed_count == total_steps:
            workflow.overall_status = "success"
            workflow.current_phase = WorkflowPhase.COMPLETE
            workflow.completed_at = datetime.now()
        else:
            workflow.overall_status = "running"

        # Update error count
        workflow.error_count = failed_count

    def get_workflow_status(self, workflow_id: str) -> dict:
        """Get current status of a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Status dictionary
        """
        if workflow_id not in self.workflows:
            return {"status": "not_found"}

        workflow = self.workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "task_id": workflow.task_id,
            "status": workflow.overall_status,
            "phase": workflow.current_phase.value,
            "completion_percentage": workflow.completion_percentage,
            "steps_completed": sum(
                1 for step in workflow.steps if step.status == WorkflowPhase.COMPLETE
            ),
            "total_steps": len(workflow.steps),
            "errors": workflow.error_count,
        }

    def get_pending_workflows(self) -> list[TaskWorkflow]:
        """Get all pending workflows.

        Returns:
            List of pending TaskWorkflows
        """
        return [w for w in self.workflows.values() if w.overall_status == "pending"]

    def get_active_workflows(self) -> list[TaskWorkflow]:
        """Get all active workflows.

        Returns:
            List of active TaskWorkflows
        """
        return [w for w in self.workflows.values() if w.overall_status == "running"]

    def cancel_workflow(self, workflow_id: str):
        """Cancel a workflow.

        Args:
            workflow_id: Workflow identifier
        """
        if workflow_id not in self.workflows:
            return

        workflow = self.workflows[workflow_id]
        workflow.overall_status = "cancelled"
        workflow.current_phase = WorkflowPhase.FAILED
        logger.info(f"Workflow {workflow_id} cancelled")

    def detect_deadlock(self, workflow_id: str) -> bool:
        """Detect if a workflow is in deadlock.

        Deadlock occurs when there are incomplete steps with unsatisfied dependencies.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if deadlock detected
        """
        if workflow_id not in self.workflows:
            return False

        workflow = self.workflows[workflow_id]

        for step in workflow.steps:
            # Skip completed/failed steps
            if step.status in [WorkflowPhase.COMPLETE, WorkflowPhase.FAILED]:
                continue

            # Check if all dependencies can ever be satisfied
            for dep_id in step.dependencies:
                dep_found = False
                for other_step in workflow.steps:
                    if other_step.step_id == dep_id:
                        dep_found = True
                        if other_step.status == WorkflowPhase.FAILED:
                            # Dependency failed, this step can't complete
                            return True
                        break

                if not dep_found:
                    # Dependency doesn't exist
                    return True

        return False

    def get_critical_path(self, workflow_id: str) -> list[str]:
        """Get the critical path through the workflow.

        Returns the longest sequence of dependent steps.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of step IDs in critical path
        """
        if workflow_id not in self.workflows:
            return []

        workflow = self.workflows[workflow_id]

        # Build adjacency list
        graph: dict[str, list[str]] = defaultdict(list)
        for step in workflow.steps:
            for dep_id in step.dependencies:
                graph[dep_id].append(step.step_id)

        # Find longest path using DFS
        def longest_path(step_id: str, visited: set[str]) -> tuple[list[str], float]:
            """Recursively find longest path from step."""
            visited.add(step_id)
            max_path = [step_id]
            max_time = 0.0

            # Find the step to get execution time
            for step in workflow.steps:
                if step.step_id == step_id:
                    max_time = step.execution_time_ms
                    break

            for neighbor in graph[step_id]:
                if neighbor not in visited:
                    sub_path, sub_time = longest_path(neighbor, visited)
                    if len(sub_path) + 1 > len(max_path):
                        max_path = [step_id] + sub_path
                        max_time += sub_time

            visited.remove(step_id)
            return max_path, max_time

        # Find all root steps
        all_step_ids = {step.step_id for step in workflow.steps}
        root_steps = []
        for step in workflow.steps:
            if not step.dependencies:
                root_steps.append(step.step_id)

        critical_path = []
        max_total_time = 0.0

        for root_id in root_steps:
            path, total_time = longest_path(root_id, set())
            if total_time > max_total_time:
                critical_path = path
                max_total_time = total_time

        return critical_path
