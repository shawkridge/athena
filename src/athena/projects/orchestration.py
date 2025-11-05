"""Multi-agent orchestration and delegation tracking."""

from datetime import datetime
from typing import Optional, Dict, List

from pydantic import BaseModel, Field


class AgentDelegation(BaseModel):
    """Track delegation of task to agent."""

    id: Optional[int] = None
    from_agent: str
    to_agent: str
    task_id: int
    task_description: str
    success: bool
    handoff_cost_tokens: int = 0
    handoff_time_ms: int = 0
    completion_time_ms: Optional[int] = None
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)


class OrchestrationEffectiveness(BaseModel):
    """Track effectiveness of orchestration patterns."""

    orchestration_pattern_id: int
    total_delegations: int = 0
    successful_delegations: int = 0
    failed_delegations: int = 0
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    total_tokens_used: int = 0
    total_time_ms: int = 0
    speedup_factor: float = 1.0
    last_updated: datetime = Field(default_factory=datetime.now)


class OrchestrationTracking:
    """Track multi-agent delegation and orchestration effectiveness."""

    def __init__(self, db=None):
        """Initialize orchestration tracking.

        Args:
            db: Database instance for persistence
        """
        self.db = db
        # In-memory storage for demo/testing
        self._delegations: Dict = {}
        self._effectiveness: Dict = {}
        self._agent_teams: Dict = {}

    def record_delegation(
        self,
        from_agent: str,
        to_agent: str,
        task_id: int,
        task_description: str,
        success: bool,
        handoff_cost_tokens: int = 0,
        handoff_time_ms: int = 0,
        completion_time_ms: Optional[int] = None,
        quality_score: float = 0.0,
    ) -> AgentDelegation:
        """Record delegation of task to agent.

        Args:
            from_agent: Delegating agent name
            to_agent: Receiving agent name
            task_id: Task ID
            task_description: Task description
            success: Whether delegation succeeded
            handoff_cost_tokens: Tokens used in handoff
            handoff_time_ms: Time for handoff in ms
            completion_time_ms: Total completion time in ms
            quality_score: Quality of execution

        Returns:
            Recorded delegation
        """
        delegation = AgentDelegation(
            from_agent=from_agent,
            to_agent=to_agent,
            task_id=task_id,
            task_description=task_description,
            success=success,
            handoff_cost_tokens=handoff_cost_tokens,
            handoff_time_ms=handoff_time_ms,
            completion_time_ms=completion_time_ms,
            quality_score=quality_score,
        )

        key = f"{from_agent}_{to_agent}_{task_id}"
        self._delegations[key] = delegation

        if self.db:
            # Persist to database
            pass

        return delegation

    def record_agent_team(
        self,
        orchestration_pattern_id: int,
        agents: List[str],
        arrangement: str = "sequential",
    ) -> Dict:
        """Record successful agent team arrangement.

        Args:
            orchestration_pattern_id: Pattern ID
            agents: List of agent names in team
            arrangement: Arrangement type (sequential|parallel|hierarchical)

        Returns:
            Team record
        """
        team_record = {
            "orchestration_pattern_id": orchestration_pattern_id,
            "agents": agents,
            "arrangement": arrangement,
            "recorded_at": datetime.now(),
            "success_count": 0,
            "failure_count": 0,
            "total_executions": 0,
        }

        key = f"team_{orchestration_pattern_id}_{'-'.join(agents)}"
        self._agent_teams[key] = team_record

        if self.db:
            # Persist to database
            pass

        return team_record

    def calculate_orchestration_effectiveness(
        self,
        orchestration_pattern_id: int,
    ) -> OrchestrationEffectiveness:
        """Calculate orchestration pattern effectiveness.

        Args:
            orchestration_pattern_id: Pattern ID to analyze

        Returns:
            Effectiveness metrics
        """
        # Get all delegations for this pattern
        pattern_delegations = [
            d for d in self._delegations.values()
            if hasattr(d, 'orchestration_pattern_id')
        ]

        # For now, calculate from agent teams
        matching_teams = [
            t for t in self._agent_teams.values()
            if t["orchestration_pattern_id"] == orchestration_pattern_id
        ]

        total_delegations = len(pattern_delegations)
        successful = len([d for d in pattern_delegations if d.success])

        effectiveness = OrchestrationEffectiveness(
            orchestration_pattern_id=orchestration_pattern_id,
            total_delegations=total_delegations,
            successful_delegations=successful,
            failed_delegations=total_delegations - successful,
            success_rate=(successful / total_delegations) if total_delegations > 0 else 0.0,
            avg_quality_score=(
                sum(d.quality_score for d in pattern_delegations) / total_delegations
                if total_delegations > 0
                else 0.0
            ),
        )

        # Store effectiveness
        self._effectiveness[orchestration_pattern_id] = effectiveness

        return effectiveness

    def recommend_agent_team(
        self,
        task_complexity: int,  # 1-10 scale
        domains_needed: List[str],
        time_constraint_minutes: Optional[int] = None,
    ) -> Dict:
        """Recommend optimal agent team for task.

        Args:
            task_complexity: Task complexity (1-10)
            domains_needed: List of domains needed (e.g., ['frontend', 'backend', 'devops'])
            time_constraint_minutes: Time constraint if any

        Returns:
            Team recommendation with rationale
        """
        recommendation = {
            "recommended_team_size": 1,
            "agent_roles": [],
            "arrangement": "sequential",
            "expected_speedup": 1.0,
            "confidence": 0.0,
            "rationale": "",
        }

        # Heuristic: higher complexity and more domains = larger team
        base_team_size = 1 + len(domains_needed)

        # Cap at 5 agents (research suggests 3-5 is optimal)
        recommended_size = min(base_team_size, 5)

        if task_complexity >= 8:
            # High complexity: parallel specialist arrangement
            recommendation["arrangement"] = "parallel"
            recommendation["expected_speedup"] = 2.5
            recommendation["confidence"] = 0.80
            recommendation["rationale"] = "High complexity benefits from parallel specialist teams"

        elif task_complexity >= 5:
            # Medium complexity: hybrid arrangement
            recommendation["arrangement"] = "hybrid"
            recommendation["expected_speedup"] = 1.8
            recommendation["confidence"] = 0.70
            recommendation["rationale"] = "Medium complexity works well with hybrid orchestration"

        else:
            # Low complexity: sequential is fine
            recommendation["arrangement"] = "sequential"
            recommendation["expected_speedup"] = 1.0
            recommendation["confidence"] = 0.90
            recommendation["rationale"] = "Low complexity suitable for single agent"

        # Map domains to agent roles
        role_mapping = {
            "frontend": "Frontend Specialist",
            "backend": "Backend Specialist",
            "devops": "DevOps Engineer",
            "database": "Database Expert",
            "security": "Security Auditor",
        }

        if domains_needed:
            recommendation["agent_roles"] = [
                role_mapping.get(domain, domain.title())
                for domain in domains_needed[:recommended_size]
            ]
            recommendation["recommended_team_size"] = len(recommendation["agent_roles"])
        else:
            # Default single agent if no domains specified
            recommendation["agent_roles"] = ["General Agent"]
            recommendation["recommended_team_size"] = 1

        return recommendation

    def estimate_handoff_overhead(
        self,
        num_agents: int,
        num_handoffs: int,
        avg_tokens_per_handoff: int = 500,
    ) -> Dict:
        """Estimate token overhead from multi-agent handoffs.

        Args:
            num_agents: Number of agents in team
            num_handoffs: Number of handoff points
            avg_tokens_per_handoff: Average tokens per handoff

        Returns:
            Overhead estimation
        """
        # Research suggests 15x overhead for multi-agent vs single agent
        overhead_multiplier = 1.0 + (num_agents - 1) * 0.5  # Scales with team size
        total_overhead = num_handoffs * avg_tokens_per_handoff * overhead_multiplier

        estimation = {
            "num_agents": num_agents,
            "num_handoffs": num_handoffs,
            "avg_tokens_per_handoff": avg_tokens_per_handoff,
            "overhead_multiplier": overhead_multiplier,
            "total_estimated_tokens": total_overhead,
            "is_justified": overhead_multiplier < 2.0,  # Rule of thumb: <2x acceptable
            "note": "Multi-agent overhead justified for complex tasks, not for simple tasks",
        }

        return estimation

    def identify_successful_agent_pairs(
        self,
        min_success_rate: float = 0.85,
    ) -> List[Dict]:
        """Identify agent pairs that work well together.

        Args:
            min_success_rate: Minimum success rate threshold

        Returns:
            List of successful agent pair arrangements
        """
        agent_pair_stats = {}

        # Aggregate delegation statistics by agent pair
        for delegation in self._delegations.values():
            pair_key = f"{delegation.from_agent}_{delegation.to_agent}"
            if pair_key not in agent_pair_stats:
                agent_pair_stats[pair_key] = {
                    "from_agent": delegation.from_agent,
                    "to_agent": delegation.to_agent,
                    "successful": 0,
                    "total": 0,
                    "avg_quality": 0.0,
                }

            stats = agent_pair_stats[pair_key]
            stats["total"] += 1
            if delegation.success:
                stats["successful"] += 1
            stats["avg_quality"] = (
                (stats["avg_quality"] * (stats["total"] - 1) + delegation.quality_score) /
                stats["total"]
            )

        # Filter and rank by success rate
        successful_pairs = [
            {
                **stats,
                "success_rate": stats["successful"] / stats["total"],
            }
            for stats in agent_pair_stats.values()
            if (stats["successful"] / stats["total"]) >= min_success_rate
        ]

        # Sort by success rate descending
        successful_pairs.sort(key=lambda x: x["success_rate"], reverse=True)

        return successful_pairs

    def get_delegation_timeline(
        self,
        task_id: int,
    ) -> List[Dict]:
        """Get chronological timeline of delegations for a task.

        Args:
            task_id: Task ID

        Returns:
            Chronological list of delegations
        """
        delegations = [
            {
                "from_agent": d.from_agent,
                "to_agent": d.to_agent,
                "success": d.success,
                "quality_score": d.quality_score,
                "completion_time_ms": d.completion_time_ms,
                "timestamp": d.created_at,
            }
            for d in self._delegations.values()
            if d.task_id == task_id
        ]

        # Sort by timestamp
        delegations.sort(key=lambda x: x["timestamp"])
        return delegations
