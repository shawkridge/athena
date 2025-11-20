"""
Learning Integration for Multi-Agent Orchestration

This module integrates the orchestration system with Athena's learning layers:
- Procedural memory learns from agent workflows
- Meta-memory tracks agent effectiveness per domain
- Consolidation optimizes agent behavior over time
- Expertise tracking guides task-to-agent routing
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentPerformanceMetrics:
    """Metrics tracking agent effectiveness."""
    agent_id: str
    agent_type: str
    domain: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    avg_duration_minutes: float
    expertise_score: float  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "domain": self.domain,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": round(self.success_rate, 2),
            "avg_duration_minutes": round(self.avg_duration_minutes, 2),
            "expertise_score": round(self.expertise_score, 2),
        }


class LearningIntegrationManager:
    """
    Manages learning integration between orchestration and Athena's memory layers.

    Responsibilities:
    - Extract procedures from agent workflows
    - Track agent effectiveness per domain
    - Update meta-memory with expertise insights
    - Route tasks to high-performing agents
    - Learn patterns from agent execution
    """

    def __init__(self, db, procedural_store=None, meta_store=None):
        """Initialize learning integration.

        Args:
            db: Database connection
            procedural_store: ProceduralStore instance (optional)
            meta_store: MetaStore instance (optional)
        """
        self.db = db
        self.procedural_store = procedural_store
        self.meta_store = meta_store
        self._performance_cache: Dict[str, AgentPerformanceMetrics] = {}

    async def record_task_completion(
        self,
        agent_id: str,
        task_id: int,
        task_content: str,
        domain: str,
        success: bool,
        duration_minutes: float,
        result: Optional[str] = None
    ) -> bool:
        """Record task completion and update learning metrics.

        Args:
            agent_id: ID of agent that completed task
            task_id: ID of completed task
            task_content: Content/description of task
            domain: Domain/category of task (research, analysis, synthesis)
            success: Whether task completed successfully
            duration_minutes: Time taken to complete
            result: Optional result/output from task

        Returns:
            True if recorded successfully
        """
        try:
            # 1. Record in episodic memory as learning event
            from athena.episodic.operations import remember

            event_content = f"Agent {agent_id} completed task #{task_id} ({domain})"
            if result:
                event_content += f"\nResult: {result[:500]}"

            await remember(
                content=event_content,
                event_type="agent_workflow",
                tags=["orchestration", "agent_learning", domain, agent_id],
                importance=0.7 if success else 0.4
            )

            # 2. Update performance metrics
            await self._update_performance_metrics(
                agent_id, task_id, domain, success, duration_minutes
            )

            # 3. Extract procedure if successful
            if success and self.procedural_store:
                await self._extract_procedure(
                    agent_id, task_content, domain, duration_minutes
                )

            # 4. Update meta-memory with expertise
            if self.meta_store:
                await self._update_expertise(agent_id, domain, success)

            return True

        except Exception as e:
            logger.error(f"Failed to record task completion: {e}")
            return False

    async def _update_performance_metrics(
        self,
        agent_id: str,
        task_id: int,
        domain: str,
        success: bool,
        duration_minutes: float
    ) -> None:
        """Update cached performance metrics for agent."""
        try:
            # Query or initialize metrics
            metrics = self._performance_cache.get(agent_id)
            if not metrics:
                metrics = await self._load_metrics(agent_id, domain)

            # Update counts
            metrics.total_tasks += 1
            if success:
                metrics.completed_tasks += 1
            else:
                metrics.failed_tasks += 1

            # Update success rate
            metrics.success_rate = (
                metrics.completed_tasks / metrics.total_tasks
                if metrics.total_tasks > 0 else 0
            )

            # Update average duration
            old_avg = metrics.avg_duration_minutes
            metrics.avg_duration_minutes = (
                (old_avg * (metrics.total_tasks - 1) + duration_minutes)
                / metrics.total_tasks
            )

            # Calculate expertise score (0-1 based on success rate and speed)
            # Success rate: 50% of score
            # Speed bonus: faster agents get +boost (assuming <5min is fast)
            speed_bonus = 0.2 if duration_minutes < 5 else (0.1 if duration_minutes < 15 else 0)
            metrics.expertise_score = min(
                metrics.success_rate * 0.5 + speed_bonus,
                1.0
            )

            self._performance_cache[agent_id] = metrics

            # Persist to database
            await self._persist_metrics(agent_id, metrics)

        except Exception as e:
            logger.error(f"Failed to update metrics for {agent_id}: {e}")

    async def _extract_procedure(
        self,
        agent_id: str,
        task_content: str,
        domain: str,
        duration_minutes: float
    ) -> None:
        """Extract reusable procedure from successful task execution."""
        if not self.procedural_store:
            return

        try:
            # Create procedure name from domain + task pattern
            procedure_name = f"execute_{domain}_workflow"

            # Check if similar procedure exists
            existing = await self.procedural_store.list_procedures(
                category=domain, limit=10
            )

            # Only create new procedure if we don't have many for this domain
            if len(existing) < 5:
                await self.procedural_store.extract_procedure(
                    name=procedure_name,
                    category=domain,
                    steps=[
                        {"step": 1, "action": "analyze_task", "description": task_content[:100]},
                        {"step": 2, "action": "execute", "description": f"Execute by {agent_id}"},
                        {"step": 3, "action": "validate", "description": "Validate results"}
                    ],
                    success_rate=1.0,
                    estimated_duration_minutes=duration_minutes
                )

                logger.info(f"Extracted procedure {procedure_name} from {agent_id}")

        except Exception as e:
            logger.error(f"Failed to extract procedure: {e}")

    async def _update_expertise(
        self,
        agent_id: str,
        domain: str,
        success: bool
    ) -> None:
        """Update meta-memory with agent expertise in domain."""
        if not self.meta_store:
            return

        try:
            # Record domain expertise
            expertise_key = f"agent_{agent_id}_expertise_{domain}"

            # Get current expertise
            current = await self.meta_store.get_expertise(
                domain=domain, agent_id=agent_id
            )

            if current:
                # Boost expertise on success
                new_score = min(current + (0.1 if success else -0.05), 1.0)
            else:
                new_score = 0.8 if success else 0.3

            # Update meta-memory
            await self.meta_store.rate_memory(
                memory_id=expertise_key,
                quality_score=new_score,
                usefulness=1.0 if success else 0.3
            )

        except Exception as e:
            logger.error(f"Failed to update expertise: {e}")

    async def _load_metrics(self, agent_id: str, domain: str) -> AgentPerformanceMetrics:
        """Load or initialize metrics for agent."""
        try:
            # Try to get from database
            # For now, return initialized metrics
            return AgentPerformanceMetrics(
                agent_id=agent_id,
                agent_type="specialist",
                domain=domain,
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                success_rate=0.0,
                avg_duration_minutes=0.0,
                expertise_score=0.5
            )
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            return AgentPerformanceMetrics(
                agent_id=agent_id,
                agent_type="specialist",
                domain=domain,
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                success_rate=0.0,
                avg_duration_minutes=0.0,
                expertise_score=0.5
            )

    async def _persist_metrics(
        self,
        agent_id: str,
        metrics: AgentPerformanceMetrics
    ) -> None:
        """Persist metrics to database."""
        try:
            # Store in episodic memory as metadata
            from athena.episodic.operations import remember

            await remember(
                content=f"Agent metrics update: {metrics.to_dict()}",
                event_type="agent_metrics",
                tags=["agent_performance", agent_id, metrics.domain],
                importance=0.3
            )

        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")

    async def get_agent_expertise(self, agent_id: str, domain: str) -> float:
        """Get agent expertise score for a domain (0-1).

        Args:
            agent_id: ID of agent
            domain: Domain to check expertise in

        Returns:
            Expertise score (0-1)
        """
        metrics = self._performance_cache.get(agent_id)
        if metrics and metrics.domain == domain:
            return metrics.expertise_score

        # Load from database
        metrics = await self._load_metrics(agent_id, domain)
        return metrics.expertise_score

    async def get_best_agent_for_domain(
        self,
        domain: str,
        available_agents: List[str]
    ) -> Optional[str]:
        """Get best-performing agent for a domain.

        Args:
            domain: Domain/category of work
            available_agents: List of available agent IDs

        Returns:
            Best agent ID or None
        """
        if not available_agents:
            return None

        best_agent = None
        best_score = -1.0

        for agent_id in available_agents:
            score = await self.get_agent_expertise(agent_id, domain)
            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of agent performance across all domains.

        Returns:
            Dictionary with performance statistics
        """
        if not self._performance_cache:
            return {"agents": []}

        return {
            "agents": [
                metrics.to_dict()
                for metrics in self._performance_cache.values()
            ],
            "total_agents": len(self._performance_cache),
            "avg_success_rate": (
                sum(m.success_rate for m in self._performance_cache.values())
                / len(self._performance_cache)
                if self._performance_cache else 0
            )
        }


# Global instance (initialized by orchestrator)
_learning_manager: Optional[LearningIntegrationManager] = None


async def get_learning_manager(
    db=None,
    procedural_store=None,
    meta_store=None
) -> LearningIntegrationManager:
    """Get or initialize learning integration manager."""
    global _learning_manager

    if _learning_manager is None:
        _learning_manager = LearningIntegrationManager(
            db=db,
            procedural_store=procedural_store,
            meta_store=meta_store
        )

    return _learning_manager
