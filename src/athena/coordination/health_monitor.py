"""
Health Monitoring and Agent Recovery

Detects and recovers from:
- Stale heartbeats (agent hung/dead)
- Stuck tasks (agent claimed but no progress)
- Failed tasks (agent error)
- Resource exhaustion (agent overloaded)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict

from .models import Agent, AgentStatus, Task, TaskStatus
from .operations import CoordinationOperations

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor agent health and orchestration state."""

    def __init__(
        self,
        db,
        stale_threshold_seconds: int = 60,
        stuck_threshold_seconds: int = 300,
        check_interval_seconds: int = 10,
    ):
        """
        Initialize health monitor.

        Args:
            db: Database connection
            stale_threshold_seconds: Heartbeat older than this = stale
            stuck_threshold_seconds: Task uncompleted for this long = stuck
            check_interval_seconds: How often to check health
        """
        self.db = db
        self.coordination_ops = CoordinationOperations(db)
        self.stale_threshold_seconds = stale_threshold_seconds
        self.stuck_threshold_seconds = stuck_threshold_seconds
        self.check_interval_seconds = check_interval_seconds

        self.is_running = False
        self._check_task = None

    async def start(self) -> None:
        """Start health monitoring."""
        logger.info("Starting health monitor")
        self.is_running = True
        self._check_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop health monitoring."""
        logger.info("Stopping health monitor")
        self.is_running = False
        if self._check_task:
            self._check_task.cancel()

    # ====================================================================
    # Health Check Logic
    # ====================================================================

    async def _monitor_loop(self) -> None:
        """Main health check loop."""
        while self.is_running:
            try:
                # Check for stale agents
                stale = await self.detect_stale_agents()
                for agent in stale:
                    await self._handle_stale_agent(agent)

                # Check for stuck tasks
                stuck = await self.detect_stuck_tasks()
                for task in stuck:
                    await self._handle_stuck_task(task)

                # Check for failed tasks needing retry
                failed = await self.detect_retryable_tasks()
                for task in failed:
                    await self._handle_retryable_task(task)

                await asyncio.sleep(self.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(self.check_interval_seconds)

    async def detect_stale_agents(self) -> List[Agent]:
        """Find agents with stale heartbeats."""
        rows = await self.db.fetch(
            """
            SELECT * FROM agents
            WHERE status != %s
            AND (NOW() - last_heartbeat) > INTERVAL '1 second' * %s
            ORDER BY last_heartbeat ASC
            """,
            AgentStatus.OFFLINE.value,
            self.stale_threshold_seconds,
        )

        return [Agent.from_dict(dict(row)) for row in rows]

    async def detect_stuck_tasks(self) -> List[Task]:
        """Find tasks that haven't progressed recently."""
        rows = await self.db.fetch(
            """
            SELECT * FROM prospective_tasks
            WHERE status = %s
            AND claimed_at IS NOT NULL
            AND (NOW() - claimed_at) > INTERVAL '1 second' * %s
            AND progress_percentage < 100
            ORDER BY claimed_at ASC
            """,
            TaskStatus.IN_PROGRESS.value,
            self.stuck_threshold_seconds,
        )

        return [Task.from_dict(dict(row)) for row in rows]

    async def detect_retryable_tasks(self) -> List[Task]:
        """Find failed tasks that can be retried."""
        rows = await self.db.fetch(
            """
            SELECT * FROM prospective_tasks
            WHERE status = %s
            AND (metadata->>'retry_count')::int < 3
            ORDER BY updated_at ASC
            """,
            TaskStatus.FAILED.value,
        )

        return [Task.from_dict(dict(row)) for row in rows]

    # ====================================================================
    # Recovery Actions
    # ====================================================================

    async def _handle_stale_agent(self, agent: Agent) -> None:
        """Handle stale agent (no heartbeat)."""
        logger.warning(
            f"Agent {agent.agent_id} is stale (no heartbeat for {self.stale_threshold_seconds}s)"
        )

        try:
            # Mark agent as offline
            await self.coordination_ops.update_agent_status(agent.agent_id, AgentStatus.OFFLINE)

            # Reassign its tasks
            tasks = await self.coordination_ops.get_agent_tasks(agent.agent_id)
            for task in tasks:
                if task.status == TaskStatus.IN_PROGRESS:
                    # Mark as failed and retryable
                    await self.coordination_ops.fail_task(
                        task.task_id,
                        f"Agent {agent.agent_id} went offline (stale heartbeat)",
                    )

                    logger.info(f"Reassigned task {task.task_id} (agent went offline)")

            # Attempt respawn
            if agent.restart_count < 3:
                logger.info(f"Attempting to respawn agent {agent.agent_id}")
                await self.respawn_agent(agent)
            else:
                logger.error(f"Agent {agent.agent_id} exceeded max restarts; giving up")

        except Exception as e:
            logger.error(f"Error handling stale agent {agent.agent_id}: {e}")

    async def _handle_stuck_task(self, task: Task) -> None:
        """Handle task that's been in progress too long."""
        elapsed = (datetime.now(timezone.utc) - task.claimed_at).total_seconds()

        logger.warning(
            f"Task {task.task_id} is stuck (in progress for {int(elapsed)}s, "
            f"progress={task.progress_percentage}%)"
        )

        try:
            # Get agent to check status
            if task.assigned_agent_id:
                agent = await self.coordination_ops.get_agent(task.assigned_agent_id)

                if agent and agent.status == AgentStatus.OFFLINE:
                    # Agent is offline; task will be reassigned
                    logger.info(f"Reassigning task {task.task_id} (agent offline)")
                    await self.coordination_ops.fail_task(
                        task.task_id,
                        f"Task stuck: assigned agent {task.assigned_agent_id} offline",
                    )
                else:
                    # Agent is alive but not making progress
                    # Try killing task and reassigning
                    logger.warning("Task appears stuck; killing and reassigning")
                    await self.coordination_ops.fail_task(
                        task.task_id,
                        "Task stuck: no progress for extended time",
                    )

        except Exception as e:
            logger.error(f"Error handling stuck task {task.task_id}: {e}")

    async def _handle_retryable_task(self, task: Task) -> None:
        """Handle failed task that should be retried."""
        retry_count = int(task.blocked_by.split("attempt ")[-1] if task.blocked_by else 0)

        if retry_count >= 3:
            logger.info(f"Task {task.task_id} exceeded max retries; escalating to user")
            return

        logger.info(f"Retrying failed task {task.task_id} (attempt {retry_count + 1}/3)")

        try:
            # Reset task for retry
            await self.db.execute(
                """
                UPDATE prospective_tasks
                SET
                    status = %s,
                    assigned_agent_id = NULL,
                    progress_percentage = 0,
                    blocked_by = %s,
                    version = version + 1
                WHERE task_id = %s
                """,
                TaskStatus.PENDING.value,
                f"retry attempt {retry_count + 1}",
                task.task_id,
            )

        except Exception as e:
            logger.error(f"Error retrying task {task.task_id}: {e}")

    # ====================================================================
    # Agent Respawning
    # ====================================================================

    async def respawn_agent(self, agent: Agent) -> Optional[str]:
        """
        Respawn a dead agent.

        Args:
            agent: Agent to respawn

        Returns:
            New agent ID or None if failed
        """
        try:
            # Increment restart count
            await self.db.execute(
                """
                UPDATE agents
                SET restart_count = restart_count + 1,
                    status = %s
                WHERE agent_id = %s
                """,
                AgentStatus.IDLE.value,
                agent.agent_id,
            )

            # In real implementation, would spawn new tmux pane
            logger.info(f"Respawned agent {agent.agent_id}")
            return agent.agent_id

        except Exception as e:
            logger.error(f"Failed to respawn agent {agent.agent_id}: {e}")
            return None

    async def auto_heal(self) -> Dict[str, int]:
        """
        Run auto-healing checks and return summary.

        Returns:
            Dict with counts of issues detected and fixed
        """
        summary = {
            "stale_agents": 0,
            "stuck_tasks": 0,
            "retried_tasks": 0,
        }

        try:
            stale = await self.detect_stale_agents()
            summary["stale_agents"] = len(stale)
            for agent in stale:
                await self._handle_stale_agent(agent)

            stuck = await self.detect_stuck_tasks()
            summary["stuck_tasks"] = len(stuck)
            for task in stuck:
                await self._handle_stuck_task(task)

            retryable = await self.detect_retryable_tasks()
            summary["retried_tasks"] = len(retryable)
            for task in retryable:
                await self._handle_retryable_task(task)

            return summary

        except Exception as e:
            logger.error(f"Error in auto-heal: {e}")
            return summary


class RecoveryPolicy:
    """Policy for agent recovery actions."""

    # Recovery strategy per failure type
    STRATEGIES = {
        "stale_heartbeat": {
            "action": "respawn",
            "max_attempts": 3,
            "backoff_seconds": 10,
        },
        "stuck_task": {
            "action": "kill_and_reassign",
            "max_attempts": 2,
            "backoff_seconds": 5,
        },
        "task_failure": {
            "action": "retry",
            "max_attempts": 3,
            "backoff_seconds": 30,
        },
    }

    @staticmethod
    def should_retry(failure_type: str, attempt_count: int) -> bool:
        """Check if failure should be retried."""
        strategy = RecoveryPolicy.STRATEGIES.get(failure_type, {})
        return attempt_count < strategy.get("max_attempts", 0)

    @staticmethod
    def get_backoff_delay(failure_type: str, attempt_count: int) -> int:
        """Get backoff delay before retry."""
        strategy = RecoveryPolicy.STRATEGIES.get(failure_type, {})
        base_delay = strategy.get("backoff_seconds", 10)
        # Exponential backoff: 10s, 20s, 40s, etc.
        return base_delay * (2**attempt_count)
