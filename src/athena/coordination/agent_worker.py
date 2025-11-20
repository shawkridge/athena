"""
Agent Worker Base Class for Specialist Agents

Base class that all specialist agents inherit from.
Handles:
- Main work loop (polling, task claiming, execution)
- Heartbeat management
- Progress reporting
- Error handling and retries
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .models import Agent, AgentType, Task, TaskStatus
from .operations import CoordinationOperations

logger = logging.getLogger(__name__)


class AgentWorker(ABC):
    """
    Base class for specialist agent workers.

    Each agent type (Research, Analysis, Synthesis, etc.) extends this class
    and implements the execute() method.

    Responsibilities:
    - Poll for assigned work
    - Claim tasks atomically
    - Report progress during execution
    - Handle errors and retries
    - Send heartbeats to show agent is alive
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        db,
        heartbeat_interval_seconds: int = 30,
        poll_interval_seconds: int = 5,
    ):
        """
        Initialize agent worker.

        Args:
            agent_id: Unique ID for this agent instance
            agent_type: Type of agent (determines capabilities)
            db: Database connection
            heartbeat_interval_seconds: How often to send heartbeat
            poll_interval_seconds: How often to poll for work
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.db = db
        self.coordination_ops = CoordinationOperations(db)

        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.poll_interval_seconds = poll_interval_seconds

        # Agent state
        self.is_running = False
        self._current_task: Optional[Task] = None
        self._stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_runtime_seconds": 0,
        }

        # Background tasks
        self._heartbeat_task = None
        self._work_loop_task = None

    async def start(self) -> None:
        """Start the agent worker."""
        logger.info(f"Starting agent worker: {self.agent_id}")

        self.is_running = True

        # Start background heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start work loop (blocking)
        self._work_loop_task = asyncio.create_task(self._work_loop())

    async def stop(self) -> None:
        """Stop the agent worker gracefully."""
        logger.info(f"Stopping agent worker: {self.agent_id}")

        self.is_running = False

        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._work_loop_task:
            self._work_loop_task.cancel()

        logger.info(
            f"Agent {self.agent_id} stats: "
            f"completed={self._stats['tasks_completed']}, "
            f"failed={self._stats['tasks_failed']}"
        )

    # ====================================================================
    # Main Work Loop
    # ====================================================================

    async def _work_loop(self) -> None:
        """
        Main work loop:
        1. Find available tasks
        2. Claim task atomically
        3. Execute task
        4. Report completion or failure
        5. Repeat
        """
        while self.is_running:
            try:
                # Find available work
                tasks = await self.coordination_ops.find_available_work(
                    self.agent_id, self.agent_type
                )

                if not tasks:
                    # No work available, wait a bit
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue

                # Try to claim and execute each task
                for task in tasks:
                    if not self.is_running:
                        break

                    claimed_task = await self.coordination_ops.claim_task(
                        self.agent_id, task.task_id
                    )

                    if not claimed_task:
                        # Someone else claimed it, move to next
                        continue

                    # Execute the claimed task
                    await self._execute_task(claimed_task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in work loop: {e}")
                await asyncio.sleep(self.poll_interval_seconds)

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        self._current_task = task

        start_time = datetime.now(timezone.utc)
        logger.info(f"Executing task: {task.task_id}")

        try:
            # Call subclass's execute implementation
            result = await self.execute(task)

            # Report completion
            await self.coordination_ops.complete_task(task.task_id, outcome="success")
            await self.coordination_ops.report_progress(
                agent_id=self.agent_id,
                task_id=task.task_id,
                progress_pct=100,
                findings=result,
            )

            self._stats["tasks_completed"] += 1
            logger.info(f"Task {task.task_id} completed successfully")

        except Exception as e:
            # Report failure
            error_msg = f"{type(e).__name__}: {str(e)}"
            await self.coordination_ops.fail_task(task.task_id, error_msg)
            await self.coordination_ops.report_progress(
                agent_id=self.agent_id,
                task_id=task.task_id,
                progress_pct=0,
                findings={"error": error_msg},
                blocked_by=error_msg,
            )

            self._stats["tasks_failed"] += 1
            logger.error(f"Task {task.task_id} failed: {error_msg}")

        finally:
            self._current_task = None
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._stats["total_runtime_seconds"] += elapsed

    # ====================================================================
    # Heartbeat Management
    # ====================================================================

    async def _heartbeat_loop(self) -> None:
        """Background loop sending heartbeats."""
        while self.is_running:
            try:
                await self.coordination_ops.heartbeat(self.agent_id)
                await asyncio.sleep(self.heartbeat_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error sending heartbeat: {e}")
                await asyncio.sleep(self.heartbeat_interval_seconds)

    # ====================================================================
    # Progress Reporting
    # ====================================================================

    async def report_progress(
        self,
        progress_pct: int,
        findings: Optional[Dict[str, Any]] = None,
        blocked_by: Optional[str] = None,
    ) -> bool:
        """
        Report progress on current task.

        Args:
            progress_pct: Progress percentage (0-100)
            findings: Optional intermediate findings
            blocked_by: Optional reason task is blocked

        Returns:
            True if reported successfully
        """
        if not self._current_task:
            return False

        return await self.coordination_ops.report_progress(
            agent_id=self.agent_id,
            task_id=self._current_task.task_id,
            progress_pct=progress_pct,
            findings=findings,
            blocked_by=blocked_by,
        )

    # ====================================================================
    # Abstract Methods (Implemented by Subclasses)
    # ====================================================================

    @abstractmethod
    async def execute(self, task: Task) -> Dict[str, Any]:
        """
        Execute a task. Implemented by specialist agents.

        Args:
            task: Task to execute

        Returns:
            Dictionary of findings/results
        """
        raise NotImplementedError

    # ====================================================================
    # Utilities
    # ====================================================================

    async def load_memory_context(
        self, query: str, limit: int = 10
    ) -> Optional[Any]:
        """
        Load context from Athena memory for a query.

        Agents can use this to fetch relevant memories while executing.

        Args:
            query: Semantic query for memory
            limit: Max results to return

        Returns:
            Memory results or None
        """
        # Would integrate with Athena's recall() operation
        # For now, stub implementation
        logger.debug(f"Loading context for query: {query}")
        return None

    async def store_findings(self, findings: Dict[str, Any], tags: list) -> None:
        """
        Store findings in Athena memory.

        Args:
            findings: Dictionary of findings/results
            tags: Tags for categorization
        """
        # Would integrate with Athena's remember() operation
        logger.debug(f"Storing findings with tags: {tags}")

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return self._stats.copy()


# Convenience function for agent factory
async def create_agent_worker(
    agent_id: str,
    agent_type: AgentType,
    db,
    specialist_class: type,
) -> AgentWorker:
    """
    Create and return a specialist agent instance.

    Args:
        agent_id: Unique agent ID
        agent_type: Type of agent
        db: Database connection
        specialist_class: Subclass of AgentWorker

    Returns:
        Initialized agent instance
    """
    return specialist_class(agent_id=agent_id, agent_type=agent_type, db=db)
