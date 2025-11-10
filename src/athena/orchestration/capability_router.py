"""Capability-based task routing.

Routes tasks to agents based on required skills and current performance.
Uses knowledge graph for capability discovery and meta-memory for quality scoring.
"""

from typing import Optional, List, Dict, Tuple, Any

from ..core.database import Database
from .agent_registry import AgentRegistry
from .models import Agent, RoutingDecision, Task


class CapabilityRouter:
    """Route tasks to capable agents intelligently.

    Routing algorithm:
    1. Find all agents with required capabilities
    2. Filter available agents (not overloaded)
    3. Rank by quality score: success_rate * (1 - utilization)
    4. Select highest-ranked agent
    """

    def __init__(self, registry: AgentRegistry):
        """Initialize router.

        Args:
            registry: AgentRegistry instance for capability queries
        """
        self.registry = registry
        self.db = registry.db

    def route_task(
        self,
        task: Task,
        exclude_agents: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Select best agent for task.

        Returns agent_id if found, None otherwise.

        Args:
            task: Task to route
            exclude_agents: Agent IDs to exclude

        Returns:
            Agent ID or None if no capable available agent
        """
        exclude_agents = exclude_agents or []

        # Find capable agents
        candidates = self.registry.get_agents_by_capability(
            task.requirements, exclude_agents
        )

        if not candidates:
            return None  # No capable agents

        # Rank and select
        ranked = self.rank_candidates(candidates)

        for agent_id, _score in ranked:
            # Check if available
            if self._get_agent_utilization(agent_id) < 1.0:
                return agent_id

        # All candidates are at capacity
        return None

    def find_capable(self, requirements: List[str]) -> List[str]:
        """Find all agents with required capabilities.

        Args:
            requirements: List of required skill names

        Returns:
            List of capable agent IDs
        """
        return self.registry.get_agents_by_capability(requirements)

    def rank_candidates(
        self,
        candidates: List[str],
    ) -> List[Tuple[str, float]]:
        """Rank candidates by quality score.

        Quality score = success_rate * (1 - utilization)

        Args:
            candidates: List of agent IDs to rank

        Returns:
            List of (agent_id, score) tuples sorted by score descending
        """
        scores = []

        for agent_id in candidates:
            health = self.registry.get_agent_health(agent_id)
            success_rate = health.get("success_rate", 1.0)
            utilization = self._get_agent_utilization(agent_id)

            score = success_rate * (1.0 - min(utilization, 1.0))
            scores.append((agent_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def should_rebalance(self) -> bool:
        """Check if load rebalancing is needed.

        Rebalance if load skew > threshold (some agents idle, others overloaded).

        Returns:
            True if rebalancing recommended
        """
        cursor = self.db.get_cursor()

        # Get utilization stats
        cursor.execute(
            """
            SELECT
                COUNT(*) as agent_count,
                AVG(current_load / max_concurrent_tasks) as avg_util,
                MAX(current_load / max_concurrent_tasks) as max_util,
                MIN(current_load / max_concurrent_tasks) as min_util
            FROM (
                SELECT name,
                    CAST(json_extract(metadata, '$.current_load') AS INTEGER) as current_load,
                    CAST(json_extract(metadata, '$.max_concurrent_tasks') AS INTEGER) as max_concurrent_tasks
                FROM entities
                WHERE entity_type = 'agent'
            )
            """
        )

        row = cursor.fetchone()
        if not row or row["agent_count"] < 2:
            return False

        max_util = row["max_util"] or 0.0
        min_util = row["min_util"] or 0.0
        skew = max_util - min_util

        # Rebalance if skew > 50% (e.g., one agent 100%, another 10%)
        return skew > 0.5

    def get_load(self, agent_id: str) -> float:
        """Get agent's current load as fraction of capacity.

        Returns:
            current_load / max_concurrent_tasks (0-1+)
        """
        return self._get_agent_utilization(agent_id)

    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing performance statistics.

        Returns:
            Dict with routing stats
        """
        cursor = self.db.get_cursor()

        # Count by status
        cursor.execute(
            """
            SELECT COUNT(*) as total
            FROM episodic_events
            WHERE task_id IS NOT NULL
            """
        )
        total_tasks = cursor.fetchone()["total"] or 0

        # Successful assignments (assigned tasks)
        cursor.execute(
            """
            SELECT COUNT(*) as assigned
            FROM episodic_events
            WHERE task_id IS NOT NULL AND assigned_to IS NOT NULL
            """
        )
        assigned = cursor.fetchone()["assigned"] or 0

        assignment_rate = assigned / total_tasks if total_tasks > 0 else 0.0

        return {
            "total_tasks": total_tasks,
            "assigned_count": assigned,
            "assignment_rate": assignment_rate,
        }

    # Private helpers

    def _get_agent_utilization(self, agent_id: str) -> float:
        """Get agent utilization (running tasks / max concurrent).

        Args:
            agent_id: Agent ID

        Returns:
            Utilization as fraction (0-1+)
        """
        health = self.registry.get_agent_health(agent_id)

        if health.get("status") == "not_found":
            return 0.0

        max_concurrent = health.get("max_concurrent", 5)
        if max_concurrent <= 0:
            return 0.0

        # TODO: Get actual current load from agent
        # For now, return estimated based on completed tasks
        total = health.get("total_completed", 0) + health.get("total_failed", 0)

        # Estimate: if agent has completed 100 tasks with avg 1200ms each,
        # and current utilization is estimated as (total_tasks / 20) / max
        # This is a rough heuristic
        estimated_current = (total % max_concurrent) / max_concurrent
        return estimated_current

    def _get_agent_quality_score(self, agent_id: str) -> float:
        """Get quality score for agent.

        Quality = success_rate * (1 - utilization)

        Args:
            agent_id: Agent ID

        Returns:
            Score (0-1)
        """
        health = self.registry.get_agent_health(agent_id)

        if health.get("status") == "not_found":
            return 0.0

        success_rate = health.get("success_rate", 1.0)
        utilization = self._get_agent_utilization(agent_id)

        return success_rate * (1.0 - min(utilization, 1.0))
