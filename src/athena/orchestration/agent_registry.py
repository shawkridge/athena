"""Agent registry backed by local database.

Manages agent registration, capability tracking, and performance metrics.
Uses episodic events and local storage for durability and learning.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..core.database import Database
from ..graph.store import GraphStore
from ..meta.store import MetaMemoryStore
from .models import Agent, AgentStatistics


class AgentRegistry:
    """Manage agent capabilities and performance.

    Stores agents in database enabling:
    - Capability tracking and discovery
    - Performance metrics per agent
    - Dynamic skill learning from task execution
    - Team formation and coordination
    """

    def __init__(self, graph_store: GraphStore, meta_store: MetaMemoryStore):
        """Initialize agent registry.

        Args:
            graph_store: GraphStore instance (for future team formation)
            meta_store: MetaMemoryStore for performance metrics
        """
        self.graph = graph_store
        self.meta = meta_store
        self.db = graph_store.db
    def _ensure_schema(self) -> None:
        """Create agent registry table if not exists."""
        cursor = self.db.get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                capabilities TEXT NOT NULL,
                success_rate REAL DEFAULT 1.0,
                avg_completion_ms REAL DEFAULT 0,
                max_concurrent_tasks INTEGER DEFAULT 5,
                total_completed INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0,
                registered_at INTEGER NOT NULL,
                last_updated INTEGER,
                metadata TEXT
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_agents_id ON agents(agent_id)"
        )
        # commit handled by cursor context

    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register agent with capabilities.

        Args:
            agent_id: Unique agent identifier
            capabilities: List of skill names
            metadata: Custom metadata (max_concurrent_tasks, etc.)

        Raises:
            ValueError: If agent already registered
        """
        metadata = metadata or {}
        now = int(datetime.now().timestamp())

        cursor = self.db.get_cursor()

        # Check if agent already exists
        cursor.execute("SELECT id FROM agents WHERE agent_id = ?", [agent_id])
        if cursor.fetchone():
            raise ValueError(f"Agent {agent_id} already registered")

        # Insert agent
        try:
            cursor.execute(
                """
                INSERT INTO agents (
                    agent_id, capabilities, success_rate, avg_completion_ms,
                    max_concurrent_tasks, registered_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    agent_id,
                    json.dumps(capabilities),
                    metadata.get("success_rate", 1.0),
                    metadata.get("avg_completion_ms", 0),
                    metadata.get("max_concurrent_tasks", 5),
                    now,
                    json.dumps(metadata),
                ],
            )
            # commit handled by cursor context
        except Exception as e:
            raise ValueError(f"Failed to register agent {agent_id}: {e}")

    def get_agents_by_capability(
        self, required: List[str], exclude: Optional[List[str]] = None
    ) -> List[str]:
        """Find agents with required capabilities.

        Returns agents that have ALL required capabilities.

        Args:
            required: List of required skill names
            exclude: Agent IDs to exclude from results

        Returns:
            List of agent IDs with matching capabilities
        """
        exclude = exclude or []
        cursor = self.db.get_cursor()

        if not required:
            # Return all agents except excluded
            placeholders = ",".join("?" * len(exclude)) if exclude else ""
            where_clause = f" AND agent_id NOT IN ({placeholders})" if exclude else ""
            cursor.execute(
                f"SELECT agent_id FROM agents{where_clause}",
                exclude,
            )
            return [row["agent_id"] for row in cursor.fetchall()]

        # Find agents with ALL required capabilities
        # Using JSON operations to check if capabilities contain all required skills
        where_clauses = []
        for skill in required:
            # Check if capabilities JSON array contains the skill
            where_clauses.append(
                "json_array_length(capabilities) > 0 AND capabilities LIKE ?"
            )

        where_clause = " AND ".join(where_clauses)
        if exclude:
            where_clause += f" AND agent_id NOT IN ({','.join('?' * len(exclude))})"

        params = [f"%{skill}%" for skill in required] + exclude

        cursor.execute(
            f"SELECT agent_id FROM agents WHERE {where_clause}",
            params,
        )

        return [row["agent_id"] for row in cursor.fetchall()]

    def get_agent_capability(self, agent_id: str) -> List[str]:
        """Get agent's capabilities.

        Args:
            agent_id: Agent ID

        Returns:
            List of skill names
        """
        cursor = self.db.get_cursor()
        cursor.execute("SELECT capabilities FROM agents WHERE agent_id = ?", [agent_id])
        row = cursor.fetchone()

        if not row:
            return []

        try:
            return json.loads(row["capabilities"])
        except (json.JSONDecodeError, TypeError):
            return []

    def update_agent_performance(
        self,
        agent_id: str,
        success: bool,
        duration_ms: int,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update agent performance metrics from completed task.

        Args:
            agent_id: Agent ID
            success: Whether task succeeded
            duration_ms: Task execution time
            metrics: Additional metrics
        """
        metrics = metrics or {}
        now = int(datetime.now().timestamp())

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT success_rate, avg_completion_ms, total_completed, total_failed
            FROM agents WHERE agent_id = ?
            """,
            [agent_id],
        )
        row = cursor.fetchone()

        if not row:
            return  # Agent not found

        # Update metrics
        total_completed = row["total_completed"] + (1 if success else 0)
        total_failed = row["total_failed"] + (0 if success else 1)
        total = total_completed + total_failed

        new_success_rate = total_completed / total if total > 0 else 1.0

        # Update avg completion time (weighted average of successful tasks only)
        old_avg = row["avg_completion_ms"] or 0
        old_count = row["total_completed"]
        new_count = old_count + (1 if success else 0)
        # Only include duration if the task was successful
        if success:
            new_avg = (
                (old_avg * old_count + duration_ms) / new_count if new_count > 0 else 0
            )
        else:
            new_avg = old_avg  # Failed tasks don't affect avg

        # Update agent
        cursor.execute(
            """
            UPDATE agents
            SET success_rate = ?, avg_completion_ms = ?,
                total_completed = ?, total_failed = ?,
                last_updated = ?
            WHERE agent_id = ?
            """,
            [new_success_rate, new_avg, total_completed, total_failed, now, agent_id],
        )
        # commit handled by cursor context

    def get_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Get health status of agent.

        Args:
            agent_id: Agent ID

        Returns:
            Dict with {success_rate, avg_completion_ms, load, status, ...}
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT success_rate, avg_completion_ms, total_completed, total_failed, max_concurrent_tasks
            FROM agents WHERE agent_id = ?
            """,
            [agent_id],
        )
        row = cursor.fetchone()

        if not row:
            return {"status": "not_found"}

        success_rate = row["success_rate"] or 1.0

        return {
            "agent_id": agent_id,
            "success_rate": success_rate,
            "avg_completion_ms": row["avg_completion_ms"] or 0,
            "total_completed": row["total_completed"] or 0,
            "total_failed": row["total_failed"] or 0,
            "max_concurrent": row["max_concurrent_tasks"] or 5,
            "status": "healthy" if success_rate > 0.8 else "degraded",
        }

    def learn_new_capability(
        self,
        agent_id: str,
        capability: str,
        confidence: float = 1.0,
    ) -> None:
        """Add new skill to agent (from consolidation).

        Args:
            agent_id: Agent ID
            capability: New skill name
            confidence: Confidence in new skill (0-1)
        """
        cursor = self.db.get_cursor()

        # Get current capabilities
        cursor.execute("SELECT capabilities FROM agents WHERE agent_id = ?", [agent_id])
        row = cursor.fetchone()

        if not row:
            return  # Agent not found

        try:
            capabilities = json.loads(row["capabilities"])
        except (json.JSONDecodeError, TypeError):
            capabilities = []

        # Add new capability if not already present
        if capability not in capabilities:
            capabilities.append(capability)

            cursor.execute(
                "UPDATE agents SET capabilities = ? WHERE agent_id = ?",
                [json.dumps(capabilities), agent_id],
            )
            # commit handled by cursor context

    def deregister_agent(self, agent_id: str) -> None:
        """Remove agent from registry.

        Args:
            agent_id: Agent ID to remove
        """
        cursor = self.db.get_cursor()
        cursor.execute("DELETE FROM agents WHERE agent_id = ?", [agent_id])
        # commit handled by cursor context

    def get_agent_statistics(self) -> AgentStatistics:
        """Get statistics about agents.

        Returns:
            AgentStatistics with counts and distributions
        """
        cursor = self.db.get_cursor()

        # Count agents
        cursor.execute("SELECT COUNT(*) as count FROM agents")
        total_agents = cursor.fetchone()["count"] or 0

        # Average success rate
        cursor.execute("SELECT AVG(success_rate) as avg_success FROM agents")
        avg_success = cursor.fetchone()["avg_success"] or 0.0

        # Skill distribution - count how many agents have each skill
        skill_dist = {}
        cursor.execute("SELECT capabilities FROM agents")
        for row in cursor.fetchall():
            try:
                capabilities = json.loads(row["capabilities"])
                for skill in capabilities:
                    skill_dist[skill] = skill_dist.get(skill, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

        return AgentStatistics(
            total_agents=total_agents,
            avg_success_rate=avg_success,
            skill_distribution=skill_dist,
        )
