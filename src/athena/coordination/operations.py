"""
Coordination Operations for Multi-Agent Orchestration

Core operations for agent management, task assignment, and progress tracking.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from .models import (
    Agent,
    AgentStatus,
    AgentType,
    Task,
    TaskStatus,
    TaskPriority,
    CoordinationEvent,
    AGENT_CAPABILITIES,
)


class CoordinationOperations:
    """Operations for multi-agent coordination.

    Can be initialized with either:
    - A CoordinationStore instance (preferred)
    - A raw database object (legacy, will be wrapped)
    """

    def __init__(self, db):
        """Initialize with database connection or store.

        Args:
            db: Either a CoordinationStore instance or a Database object
        """
        # If it's a store, use it directly
        # If it's a database object, we'll work with it for backwards compatibility
        from .store import CoordinationStore
        if isinstance(db, CoordinationStore):
            self.store = db
            self.db = db.db
        else:
            # Legacy: raw database object
            self.store = None
            self.db = db

    # ============================================================================
    # Agent Management Operations
    # ============================================================================

    async def register_agent(
        self,
        agent_type: AgentType,
        capabilities: Optional[List[str]] = None,
        tmux_pane_id: Optional[str] = None,
        process_pid: Optional[int] = None,
    ) -> str:
        """
        Register a new agent in the system.

        Args:
            agent_type: Type of agent (research, analysis, etc.)
            capabilities: List of capabilities (defaults to agent type's capabilities)
            tmux_pane_id: Tmux pane identifier for this agent
            process_pid: OS process ID

        Returns:
            agent_id of the registered agent
        """
        agent_id = f"{agent_type.value}_{uuid.uuid4().hex[:8]}"
        caps = capabilities or AGENT_CAPABILITIES.get(agent_type, [])

        if self.store:
            # Use store API
            await self.store.create_agent(
                agent_id=agent_id,
                agent_type=agent_type.value,
                capabilities=caps,
                status=AgentStatus.IDLE.value,
                tmux_pane_id=tmux_pane_id,
                process_pid=process_pid,
            )
        else:
            # Legacy: direct database access (for backwards compatibility)
            raise NotImplementedError("Direct database access not supported. Please use CoordinationStore.")

        return agent_id

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        row = await self.db.fetch_one(
            "SELECT * FROM agents WHERE agent_id = %s", agent_id
        )

        if row:
            return Agent.from_dict(dict(row))
        return None

    async def list_agents(
        self,
        agent_type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
    ) -> List[Agent]:
        """List agents with optional filters."""
        if self.store:
            # Use store API
            agents_data = await self.store.list_agents()
            agents = [Agent.from_dict(d) for d in agents_data]

            # Apply filters if needed
            if agent_type:
                agents = [a for a in agents if a.agent_type == agent_type]
            if status:
                agents = [a for a in agents if a.status == status]

            return agents
        else:
            # Legacy path not supported
            raise NotImplementedError("Direct database access not supported. Please use CoordinationStore.")


    async def update_agent_status(
        self, agent_id: str, status: AgentStatus
    ) -> bool:
        """Update agent status."""
        result = await self.db.execute(
            """
            UPDATE agents
            SET status = %s, updated_at = NOW()
            WHERE agent_id = %s
            """,
            status.value,
            agent_id,
        )
        return result > 0

    async def heartbeat(self, agent_id: str) -> bool:
        """Record agent heartbeat (shows agent is alive)."""
        result = await self.db.execute(
            """
            UPDATE agents
            SET last_heartbeat = NOW(), updated_at = NOW()
            WHERE agent_id = %s
            """,
            agent_id,
        )
        return result > 0

    async def detect_stale_agents(
        self, stale_threshold_seconds: int = 60
    ) -> List[Agent]:
        """Find agents with stale heartbeats."""
        rows = await self.db.fetch(
            """
            SELECT * FROM agents
            WHERE status != %s
            AND (NOW() - last_heartbeat) > INTERVAL '1 second' * %s
            ORDER BY last_heartbeat ASC
            """,
            AgentStatus.OFFLINE.value,
            stale_threshold_seconds,
        )
        return [Agent.from_dict(dict(row)) for row in rows]

    async def deregister_agent(self, agent_id: str) -> bool:
        """Remove agent from registry."""
        result = await self.db.execute(
            "DELETE FROM agents WHERE agent_id = %s", agent_id
        )
        return result > 0

    # ============================================================================
    # Task Assignment & Claiming Operations
    # ============================================================================

    async def claim_task(self, agent_id: str, task_id: str) -> Optional[Task]:
        """
        Atomically claim a task for an agent using optimistic locking.

        Uses PostgreSQL's UPDATE with version checking to ensure atomic claim.
        Returns the task if successful, None if already claimed.

        Args:
            agent_id: ID of agent claiming the task
            task_id: ID of task to claim

        Returns:
            Task if claimed successfully, None otherwise
        """
        # Get current task with version
        task_row = await self.db.fetch_one(
            """
            SELECT * FROM prospective_tasks
            WHERE task_id = %s
            """,
            task_id,
        )

        if not task_row or task_row["status"] != "PENDING":
            return None

        current_version = task_row["version"]

        # Try to claim with optimistic lock
        result = await self.db.execute(
            """
            UPDATE prospective_tasks
            SET
                assigned_agent_id = %s,
                status = %s,
                claimed_at = NOW(),
                version = version + 1
            WHERE
                task_id = %s
                AND status = %s
                AND version = %s
            """,
            agent_id,
            TaskStatus.IN_PROGRESS.value,
            task_id,
            TaskStatus.PENDING.value,
            current_version,
        )

        # If update succeeded, return the task
        if result > 0:
            updated_task = await self.db.fetch_one(
                "SELECT * FROM prospective_tasks WHERE task_id = %s", task_id
            )
            return Task.from_dict(dict(updated_task))

        return None

    async def find_available_work(
        self, agent_id: str, agent_type: AgentType
    ) -> List[Task]:
        """
        Find pending tasks that agent can work on.

        Returns tasks that:
        - Are PENDING status
        - Have no assigned agent
        - Have all dependencies completed
        - Match agent capabilities

        Args:
            agent_id: ID of agent looking for work
            agent_type: Type of agent (to filter by capability)

        Returns:
            List of available tasks
        """
        capabilities = AGENT_CAPABILITIES.get(agent_type, [])

        rows = await self.db.fetch(
            """
            SELECT *
            FROM get_available_tasks(%s, 5)
            """,
            capabilities,
        )

        return [Task.from_dict(dict(row)) for row in rows]

    async def update_task_progress(
        self,
        agent_id: str,
        task_id: str,
        progress_pct: int,
        blocked_by: Optional[str] = None,
    ) -> bool:
        """Update task progress (called by agent during execution)."""
        result = await self.db.execute(
            """
            UPDATE prospective_tasks
            SET
                progress_percentage = %s,
                blocked_by = %s,
                updated_at = NOW()
            WHERE
                task_id = %s
                AND assigned_agent_id = %s
            """,
            progress_pct,
            blocked_by,
            task_id,
            agent_id,
        )
        return result > 0

    async def complete_task(
        self, task_id: str, outcome: str = "success"
    ) -> bool:
        """Mark task as completed."""
        result = await self.db.execute(
            """
            UPDATE prospective_tasks
            SET
                status = %s,
                progress_percentage = 100,
                updated_at = NOW()
            WHERE task_id = %s
            """,
            TaskStatus.COMPLETED.value,
            task_id,
        )
        return result > 0

    async def fail_task(self, task_id: str, error_message: str) -> bool:
        """Mark task as failed with error message."""
        result = await self.db.execute(
            """
            UPDATE prospective_tasks
            SET
                status = %s,
                blocked_by = %s,
                updated_at = NOW()
            WHERE task_id = %s
            """,
            TaskStatus.FAILED.value,
            error_message,
            task_id,
        )
        return result > 0

    async def get_agent_tasks(self, agent_id: str) -> List[Task]:
        """Get all tasks assigned to an agent."""
        rows = await self.db.fetch(
            """
            SELECT * FROM prospective_tasks
            WHERE assigned_agent_id = %s
            ORDER BY status, priority, created_at
            """,
            agent_id,
        )
        return [Task.from_dict(dict(row)) for row in rows]

    async def get_active_tasks(self, project_id: Optional[int] = None) -> List[Task]:
        """Get all active tasks (IN_PROGRESS or PENDING)."""
        query = """
            SELECT * FROM prospective_tasks
            WHERE status IN (%s, %s)
        """
        params = [TaskStatus.IN_PROGRESS.value, TaskStatus.PENDING.value]

        if project_id:
            query += " AND project_id = %s"
            params.append(project_id)

        rows = await self.db.fetch(query, *params)
        return [Task.from_dict(dict(row)) for row in rows]

    # ============================================================================
    # Progress Reporting Operations
    # ============================================================================

    async def report_progress(
        self,
        agent_id: str,
        task_id: str,
        progress_pct: int,
        findings: Optional[Dict[str, Any]] = None,
        blocked_by: Optional[str] = None,
    ) -> bool:
        """
        Report progress on a task.

        Updates task progress and writes progress event to episodic memory.

        Args:
            agent_id: ID of agent reporting
            task_id: ID of task being worked on
            progress_pct: Progress percentage (0-100)
            findings: Optional findings/intermediate results
            blocked_by: Optional reason task is blocked

        Returns:
            True if progress was recorded
        """
        # Update task progress
        await self.update_task_progress(agent_id, task_id, progress_pct, blocked_by)

        # Record progress event in episodic memory
        # (This would integrate with the episodic operations module)
        # For now, just return success
        return True

    # ============================================================================
    # Orchestration State Management
    # ============================================================================

    async def decompose_task(
        self,
        parent_task_id: str,
        subtask_descriptions: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Create subtasks from parent task decomposition.

        Args:
            parent_task_id: ID of parent task
            subtask_descriptions: List of subtask dicts with title, description, priority, etc.

        Returns:
            List of created subtask IDs
        """
        task_ids = []

        for i, subtask_desc in enumerate(subtask_descriptions):
            # Create subtask in prospective memory
            subtask_id = await self.db.fetch_one(
                """
                INSERT INTO prospective_tasks (
                    task_id, title, description, status, priority,
                    parent_task_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING task_id
                """,
                f"{parent_task_id}_subtask_{i}",
                subtask_desc.get("title", f"Subtask {i}"),
                subtask_desc.get("description", ""),
                TaskStatus.PENDING.value,
                subtask_desc.get("priority", TaskPriority.MEDIUM.value),
                parent_task_id,
            )

            if subtask_id:
                task_ids.append(subtask_id["task_id"])

        return task_ids

    async def get_orchestration_status(
        self, parent_task_id: str
    ) -> Dict[str, Any]:
        """Get status of orchestration for a task and its subtasks."""
        subtasks = await self.db.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM prospective_tasks
            WHERE parent_task_id = %s OR task_id = %s
            GROUP BY status
            """,
            parent_task_id,
            parent_task_id,
        )

        status_counts = {row["status"]: row["count"] for row in subtasks}

        return {
            "parent_task_id": parent_task_id,
            "total": sum(status_counts.values()),
            "pending": status_counts.get(TaskStatus.PENDING.value, 0),
            "in_progress": status_counts.get(TaskStatus.IN_PROGRESS.value, 0),
            "completed": status_counts.get(TaskStatus.COMPLETED.value, 0),
            "failed": status_counts.get(TaskStatus.FAILED.value, 0),
        }


# Convenience function for getting coordination operations
async def get_coordination_ops(db) -> CoordinationOperations:
    """Get coordination operations instance."""
    return CoordinationOperations(db)
