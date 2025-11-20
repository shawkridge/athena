"""
Coordination Store - Database abstraction for multi-agent orchestration

Provides a clean interface between coordination operations and the database,
using Athena's Database object API with correct psycopg AsyncConnection methods.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from athena.core.database import Database

logger = logging.getLogger(__name__)


class CoordinationStore:
    """Database store for coordination data (agents, tasks, etc.)."""

    def __init__(self, db: Database):
        """Initialize with Athena Database instance.

        Args:
            db: Athena Database object (provides async connection pool)
        """
        self.db = db
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize coordination tables if they don't exist."""
        if self._initialized:
            return

        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    # Create agents table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS agents (
                            agent_id VARCHAR(255) PRIMARY KEY,
                            agent_type VARCHAR(50) NOT NULL,
                            status VARCHAR(50) NOT NULL,
                            capabilities TEXT[] DEFAULT ARRAY[]::TEXT[],
                            tmux_pane_id VARCHAR(255),
                            process_pid INTEGER,
                            current_task_id VARCHAR(255),
                            tasks_completed INTEGER DEFAULT 0,
                            last_heartbeat TIMESTAMP DEFAULT NOW(),
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)

                    # Create tasks table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS agent_tasks (
                            task_id VARCHAR(255) PRIMARY KEY,
                            agent_id VARCHAR(255),
                            goal TEXT NOT NULL,
                            status VARCHAR(50) NOT NULL,
                            priority VARCHAR(50) DEFAULT 'MEDIUM',
                            progress_percentage INTEGER DEFAULT 0,
                            assigned_at TIMESTAMP,
                            completed_at TIMESTAMP,
                            error_message TEXT,
                            result TEXT,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW(),
                            FOREIGN KEY(agent_id) REFERENCES agents(agent_id) ON DELETE SET NULL
                        )
                    """)

                    # Create health checks table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS agent_health_checks (
                            id SERIAL PRIMARY KEY,
                            agent_id VARCHAR(255) NOT NULL,
                            status VARCHAR(50) NOT NULL,
                            cpu_percent FLOAT,
                            memory_mb INTEGER,
                            response_time_ms INTEGER,
                            check_timestamp TIMESTAMP DEFAULT NOW(),
                            FOREIGN KEY(agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
                        )
                    """)

                    # Create statistics table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS agent_statistics (
                            agent_id VARCHAR(255) PRIMARY KEY,
                            total_tasks_assigned INTEGER DEFAULT 0,
                            total_tasks_completed INTEGER DEFAULT 0,
                            total_tasks_failed INTEGER DEFAULT 0,
                            average_task_time_ms FLOAT,
                            success_rate FLOAT,
                            last_updated TIMESTAMP DEFAULT NOW(),
                            FOREIGN KEY(agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
                        )
                    """)

                await conn.commit()
                logger.info("Coordination tables initialized")
                self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize coordination store: {e}")
            raise

    # ========================================================================
    # Agent Operations
    # ========================================================================

    async def create_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        status: str = "idle",
        tmux_pane_id: Optional[str] = None,
        process_pid: Optional[int] = None,
    ) -> bool:
        """Create a new agent."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO agents
                        (agent_id, agent_type, capabilities, status, tmux_pane_id, process_pid)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (agent_id, agent_type, capabilities, status, tmux_pane_id, process_pid))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to create agent {agent_id}: {e}")
            return False

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT * FROM agents WHERE agent_id = %s",
                        (agent_id,)
                    )
                    row = await cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT * FROM agents")
                    rows = await cur.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []

    async def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent status."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE agents SET status = %s, updated_at = NOW() WHERE agent_id = %s",
                        (status, agent_id)
                    )
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update agent {agent_id} status: {e}")
            return False

    async def update_agent_heartbeat(self, agent_id: str) -> bool:
        """Update agent last heartbeat time."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE agents SET last_heartbeat = NOW() WHERE agent_id = %s",
                        (agent_id,)
                    )
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")
            return False

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM agents WHERE agent_id = %s", (agent_id,))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            return False

    # ========================================================================
    # Task Operations
    # ========================================================================

    async def create_task(
        self,
        task_id: str,
        goal: str,
        status: str = "PENDING",
        priority: str = "MEDIUM",
        agent_id: Optional[str] = None,
    ) -> bool:
        """Create a new task."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO agent_tasks
                        (task_id, goal, status, priority, agent_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (task_id, goal, status, priority, agent_id))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to create task {task_id}: {e}")
            return False

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT * FROM agent_tasks WHERE task_id = %s",
                        (task_id,)
                    )
                    row = await cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def list_tasks(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by agent."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    if agent_id:
                        await cur.execute(
                            "SELECT * FROM agent_tasks WHERE agent_id = %s ORDER BY created_at DESC",
                            (agent_id,)
                        )
                    else:
                        await cur.execute("SELECT * FROM agent_tasks ORDER BY created_at DESC")
                    rows = await cur.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    async def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE agent_tasks SET status = %s, updated_at = NOW() WHERE task_id = %s",
                        (status, task_id)
                    )
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id} status: {e}")
            return False

    async def update_task_progress(self, task_id: str, progress: int) -> bool:
        """Update task progress percentage."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE agent_tasks SET progress_percentage = %s, updated_at = NOW() WHERE task_id = %s",
                        (progress, task_id)
                    )
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id} progress: {e}")
            return False

    async def complete_task(self, task_id: str, result: Optional[str] = None) -> bool:
        """Mark task as completed."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        UPDATE agent_tasks
                        SET status = %s, completed_at = NOW(), result = %s, updated_at = NOW()
                        WHERE task_id = %s
                    """, ("COMPLETED", result, task_id))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    async def fail_task(self, task_id: str, error: Optional[str] = None) -> bool:
        """Mark task as failed."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        UPDATE agent_tasks
                        SET status = %s, error_message = %s, updated_at = NOW()
                        WHERE task_id = %s
                    """, ("FAILED", error, task_id))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as failed: {e}")
            return False

    # ========================================================================
    # Statistics
    # ========================================================================

    async def record_health_check(
        self,
        agent_id: str,
        status: str,
        cpu_percent: Optional[float] = None,
        memory_mb: Optional[int] = None,
        response_time_ms: Optional[int] = None,
    ) -> bool:
        """Record a health check for an agent."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO agent_health_checks
                        (agent_id, status, cpu_percent, memory_mb, response_time_ms)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (agent_id, status, cpu_percent, memory_mb, response_time_ms))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to record health check for {agent_id}: {e}")
            return False

    async def get_agent_statistics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for an agent."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT * FROM agent_statistics WHERE agent_id = %s",
                        (agent_id,)
                    )
                    row = await cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get statistics for {agent_id}: {e}")
            return None

    async def get_coordination_statistics(self) -> Dict[str, Any]:
        """Get overall coordination statistics."""
        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM agents")
                    agents = await cur.fetchval() if hasattr(cur, 'fetchval') else (await cur.fetchone())[0]

                    await cur.execute(
                        "SELECT COUNT(*) FROM agents WHERE status = %s",
                        ("busy",)
                    )
                    active_agents = await cur.fetchval() if hasattr(cur, 'fetchval') else (await cur.fetchone())[0]

                    await cur.execute("SELECT COUNT(*) FROM agent_tasks")
                    total_tasks = await cur.fetchval() if hasattr(cur, 'fetchval') else (await cur.fetchone())[0]

                    await cur.execute(
                        "SELECT COUNT(*) FROM agent_tasks WHERE status = %s",
                        ("COMPLETED",)
                    )
                    completed_tasks = await cur.fetchval() if hasattr(cur, 'fetchval') else (await cur.fetchone())[0]

                    await cur.execute(
                        "SELECT COUNT(*) FROM agent_tasks WHERE status = %s",
                        ("FAILED",)
                    )
                    failed_tasks = await cur.fetchval() if hasattr(cur, 'fetchval') else (await cur.fetchone())[0]

                    return {
                        "total_agents": agents,
                        "active_agents": active_agents,
                        "total_tasks": total_tasks,
                        "completed_tasks": completed_tasks,
                        "failed_tasks": failed_tasks,
                        "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
                    }
        except Exception as e:
            logger.error(f"Failed to get coordination statistics: {e}")
            return {}
