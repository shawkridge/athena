"""
Orchestrator for Multi-Agent Coordination

Main orchestration engine that:
- Decomposes tasks using planning layer
- Assigns subtasks to specialist agents
- Spawns agents in tmux panes
- Monitors progress and handles failures
- Synthesizes results
"""

import asyncio
import logging
import subprocess
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

try:
    import libtmux
    LIBTMUX_AVAILABLE = True
except ImportError:
    LIBTMUX_AVAILABLE = False

from .models import Agent, AgentType, Task, TaskStatus, OrchestrationState
from .operations import CoordinationOperations

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestration engine for multi-agent task execution.

    Responsibilities:
    - Task decomposition via planning layer
    - Agent spawning and lifecycle management
    - Progress monitoring and state tracking
    - Failure handling and recovery
    - Result synthesis
    """

    def __init__(
        self,
        db,
        tmux_session_name: str = "athena_agents",
        context_token_limit: int = 200000,
    ):
        """
        Initialize orchestrator.

        Args:
            db: Database connection
            tmux_session_name: Name of tmux session for agents
            context_token_limit: Context window limit for token budgeting
        """
        self.db = db
        self.coordination_ops = CoordinationOperations(db)
        self.tmux_session_name = tmux_session_name
        self.context_token_limit = context_token_limit

        # Tmux server (if available)
        self.tmux_server = libtmux.Server() if LIBTMUX_AVAILABLE else None
        self.tmux_session = None

        # Orchestration state
        self.orchestrator_id = f"orchestrator_{uuid.uuid4().hex[:8]}"
        self.state: Optional[OrchestrationState] = None
        self.active_agents: Dict[str, Agent] = {}

        # Monitoring
        self._should_run = False
        self._health_check_task = None
        self._progress_monitor_task = None

    # ========================================================================
    # Session & Agent Spawning
    # ========================================================================

    async def initialize_session(self) -> bool:
        """
        Initialize tmux session for agents.

        Creates session if doesn't exist, or reuses existing one.
        """
        if not LIBTMUX_AVAILABLE:
            logger.warning(
                "libtmux not available; orchestrator will run without tmux visualization"
            )
            return True

        try:
            # Check if session exists
            self.tmux_session = self.tmux_server.find_where(
                {"session_name": self.tmux_session_name}
            )

            if self.tmux_session:
                logger.info(f"Reusing existing tmux session: {self.tmux_session_name}")
            else:
                # Create new session
                self.tmux_session = self.tmux_server.new_session(
                    session_name=self.tmux_session_name, kill_session=True
                )
                logger.info(f"Created new tmux session: {self.tmux_session_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize tmux session: {e}")
            return False

    async def spawn_agent(
        self,
        agent_type: AgentType,
        capabilities: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Spawn a new specialist agent in a tmux pane.

        Args:
            agent_type: Type of agent to spawn
            capabilities: Optional custom capabilities

        Returns:
            agent_id if successful, None on failure
        """
        try:
            # Register agent in database first
            agent_id = await self.coordination_ops.register_agent(
                agent_type=agent_type,
                capabilities=capabilities,
            )

            # If tmux available, spawn in pane
            if LIBTMUX_AVAILABLE and self.tmux_session:
                try:
                    window = self.tmux_session.windows[0]
                    pane = window.split_window()

                    # Update agent with pane info
                    await self.db.execute(
                        """
                        UPDATE agents
                        SET tmux_pane_id = %s, process_pid = %s, status = %s
                        WHERE agent_id = %s
                        """,
                        pane.id,
                        pane.pid,
                        "idle",
                        agent_id,
                    )

                    # Start agent worker
                    # (Would send command to start agent_worker.py with this agent_id)
                    logger.info(f"Spawned agent {agent_id} in pane {pane.id}")

                except Exception as e:
                    logger.warning(f"Could not create tmux pane for agent: {e}")
                    # Continue without tmux visualization

            self.active_agents[agent_id] = await self.coordination_ops.get_agent(
                agent_id
            )
            return agent_id

        except Exception as e:
            logger.error(f"Failed to spawn agent: {e}")
            return None

    async def kill_agent(self, agent_id: str) -> bool:
        """Kill an agent and clean up resources."""
        try:
            agent = self.active_agents.pop(agent_id, None)
            if not agent:
                return False

            # Kill tmux pane if available
            if LIBTMUX_AVAILABLE and agent.tmux_pane_id and self.tmux_session:
                try:
                    self.tmux_session.kill_pane(agent.tmux_pane_id)
                except Exception:
                    pass

            # Deregister from database
            await self.coordination_ops.deregister_agent(agent_id)

            logger.info(f"Killed agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error killing agent {agent_id}: {e}")
            return False

    # ========================================================================
    # Task Orchestration
    # ========================================================================

    async def orchestrate(
        self, parent_task_id: str, max_concurrent_agents: int = 4
    ) -> Optional[Dict[str, Any]]:
        """
        Main orchestration loop for a task.

        Decomposes task, assigns to agents, monitors progress, synthesizes results.

        Args:
            parent_task_id: ID of task to orchestrate
            max_concurrent_agents: Maximum agents to spawn simultaneously

        Returns:
            Orchestration results or None on failure
        """
        logger.info(f"Starting orchestration for task {parent_task_id}")

        try:
            # Initialize session
            if not await self.initialize_session():
                logger.warning("Could not initialize tmux session")

            # Initialize state
            self.state = OrchestrationState(
                orchestrator_id=self.orchestrator_id,
                parent_task_id=parent_task_id,
            )

            # Get parent task
            parent_task = await self.db.fetch_one(
                "SELECT * FROM prospective_tasks WHERE task_id = %s", parent_task_id
            )
            if not parent_task:
                logger.error(f"Parent task not found: {parent_task_id}")
                return None

            # TODO: Decompose task using planning layer
            # For now, assume task has been decomposed into subtasks
            subtasks = await self.coordination_ops.get_active_tasks()
            self.state.decomposed_subtasks = [t.task_id for t in subtasks if t.task_id != parent_task_id]

            # Start monitoring background tasks
            self._should_run = True
            self._health_check_task = asyncio.create_task(
                self._health_check_loop()
            )
            self._progress_monitor_task = asyncio.create_task(
                self._progress_monitor_loop()
            )

            # Assign agents to work
            await self._assign_work(max_concurrent_agents)

            # Wait for completion
            while not self._orchestration_complete():
                await asyncio.sleep(5)

                # Check for token budget
                if self.state.needs_checkpoint():
                    logger.info("Context budget 80% full; should checkpoint")
                    # Would trigger memory offloading here

            # Stop monitoring
            self._should_run = False
            if self._health_check_task:
                self._health_check_task.cancel()
            if self._progress_monitor_task:
                self._progress_monitor_task.cancel()

            # Gather results
            results = await self._gather_results()

            logger.info(f"Orchestration complete for task {parent_task_id}")
            return results

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            self._should_run = False
            return None

    async def _assign_work(self, max_concurrent: int) -> None:
        """Assign tasks to available agents."""
        # Find unassigned tasks
        tasks = await self.db.fetch(
            """
            SELECT * FROM prospective_tasks
            WHERE status = %s AND assigned_agent_id IS NULL
            LIMIT %s
            """,
            TaskStatus.PENDING.value,
            max_concurrent,
        )

        for task_row in tasks:
            task = Task.from_dict(dict(task_row))

            # Determine required agent type based on task
            agent_type = self._determine_agent_type(task)

            # Spawn or get idle agent
            agent_id = await self._get_or_spawn_agent(agent_type)
            if not agent_id:
                logger.warning(f"Could not assign agent for task {task.task_id}")
                continue

            # Try to claim task
            claimed = await self.coordination_ops.claim_task(agent_id, task.task_id)
            if claimed:
                logger.info(
                    f"Assigned task {task.task_id} to agent {agent_id}"
                )

    async def _get_or_spawn_agent(self, agent_type: AgentType) -> Optional[str]:
        """Get idle agent of type, or spawn new one."""
        # Check for idle agents of this type
        agents = await self.coordination_ops.list_agents(agent_type=agent_type)
        for agent in agents:
            if agent.status.value == "idle":
                return agent.agent_id

        # Spawn new agent
        agent_id = await self.spawn_agent(agent_type)
        return agent_id

    def _determine_agent_type(self, task: Task) -> AgentType:
        """Determine which agent type should handle a task."""
        # Simple heuristic based on task tags/title
        title_lower = task.title.lower()

        if any(word in title_lower for word in ["research", "find", "search"]):
            return AgentType.RESEARCH
        elif any(word in title_lower for word in ["analyze", "check", "review"]):
            return AgentType.ANALYSIS
        elif any(word in title_lower for word in ["write", "doc", "generate"]):
            return AgentType.DOCUMENTATION
        elif any(word in title_lower for word in ["test", "verify", "validate"]):
            return AgentType.VALIDATION
        else:
            return AgentType.SYNTHESIS

    def _orchestration_complete(self) -> bool:
        """Check if all work is complete."""
        if not self.state:
            return False

        return (
            len(self.state.failed_tasks) > 0 or  # Stopped due to failures
            len(self.state.completed_tasks) + len(self.state.failed_tasks)
            == len(self.state.decomposed_subtasks)
        )

    async def _gather_results(self) -> Dict[str, Any]:
        """Gather results from completed tasks."""
        results = {
            "orchestrator_id": self.orchestrator_id,
            "parent_task_id": self.state.parent_task_id if self.state else None,
            "status": "complete",
            "completed_tasks": self.state.completed_tasks if self.state else [],
            "failed_tasks": self.state.failed_tasks if self.state else [],
            "summary": f"Completed {len(self.state.completed_tasks) if self.state else 0} tasks",
        }
        return results

    # ========================================================================
    # Background Monitoring
    # ========================================================================

    async def _health_check_loop(self) -> None:
        """Background loop checking agent health."""
        while self._should_run:
            try:
                # Detect stale agents
                stale = await self.coordination_ops.detect_stale_agents()
                for agent in stale:
                    logger.warning(f"Agent {agent.agent_id} is stale (no heartbeat)")
                    # TODO: Respawn or mark failed

                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(10)

    async def _progress_monitor_loop(self) -> None:
        """Background loop monitoring task progress."""
        while self._should_run:
            try:
                # Get progress on active tasks
                active_tasks = await self.coordination_ops.get_active_tasks()

                for task in active_tasks:
                    if task.progress_percentage == 100:
                        # Task complete
                        if self.state and task.task_id not in self.state.completed_tasks:
                            self.state.completed_tasks.append(task.task_id)
                            logger.info(f"Task {task.task_id} completed")

                    elif task.status == TaskStatus.FAILED:
                        if self.state and task.task_id not in self.state.failed_tasks:
                            self.state.failed_tasks.append(task.task_id)
                            logger.error(f"Task {task.task_id} failed")

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in progress monitor loop: {e}")
                await asyncio.sleep(5)

    async def cleanup(self) -> None:
        """Clean up orchestrator resources."""
        self._should_run = False

        # Kill all agents
        for agent_id in list(self.active_agents.keys()):
            await self.kill_agent(agent_id)

        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._progress_monitor_task:
            self._progress_monitor_task.cancel()

        logger.info("Orchestrator cleaned up")
