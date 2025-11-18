"""Consolidation Optimizer using learning insights from AdaptiveAgent.

Enhances consolidation by:
- Using agent success rates to prioritize which memories to consolidate
- Learning which consolidation strategies work best
- Adapting consolidation timing based on learning patterns
- Focusing on agent improvements through intelligent consolidation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from athena.learning.tracker import LearningTracker
from athena.core.database import Database


class ConsolidationLearningOptimizer:
    """Optimize consolidation using learned patterns from agents.

    Learns which consolidation strategies are most effective and
    prioritizes consolidation of memories from agents that are improving.
    """

    def __init__(self, db: Database):
        """Initialize consolidation optimizer.

        Args:
            db: Database for access to learning data
        """
        self.db = db
        self.tracker = LearningTracker(db)
        self._consolidation_experiments = []

    def get_prioritized_memories(
        self, all_memories: List[Dict[str, Any]], agent_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get memories prioritized for consolidation based on learning.

        Strategy:
        1. Score memories by agent learning progress
        2. Prioritize memories from agents that are improving
        3. Highlight memories related to agent decisions
        4. Return memories in consolidation priority order

        Args:
            all_memories: All available memories to consolidate
            agent_names: Optional list of agents to focus on

        Returns:
            Prioritized list of memories for consolidation
        """
        if not all_memories:
            return []

        # Get agent improvement scores
        agent_scores = self._calculate_agent_scores(agent_names)

        # Score each memory
        scored_memories = []
        for memory in all_memories:
            score = self._score_memory(memory, agent_scores)
            memory_copy = memory.copy() if isinstance(memory, dict) else memory
            if isinstance(memory_copy, dict):
                memory_copy["consolidation_priority_score"] = score
            scored_memories.append((memory_copy, score))

        # Sort by score (descending)
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        return [m[0] for m in scored_memories]

    def _calculate_agent_scores(self, agent_names: Optional[List[str]]) -> Dict[str, float]:
        """Calculate improvement scores for agents.

        Args:
            agent_names: Optional list of agents to score

        Returns:
            Dict mapping agent_name to improvement_score (0-1)
        """
        scores = {}

        # Get agents to analyze
        agents = agent_names or [
            "code-analyzer",
            "research-coordinator",
            "workflow-orchestrator",
            "metacognition",
        ]

        for agent_name in agents:
            # Get last 2 time windows of success rates
            rate_now = self.tracker.get_success_rate(agent_name, time_window_hours=24)
            rate_yesterday = self.tracker.get_success_rate(agent_name, time_window_hours=48)

            # Calculate improvement (higher = getting better)
            improvement = rate_now - rate_yesterday if rate_yesterday > 0 else 0.0
            improvement = max(-1.0, min(1.0, improvement))  # Clamp to [-1, 1]

            # Normalize to [0, 1]
            score = (improvement + 1.0) / 2.0

            scores[agent_name] = score

        return scores

    def _score_memory(self, memory: Dict[str, Any], agent_scores: Dict[str, float]) -> float:
        """Score a single memory for consolidation priority.

        Args:
            memory: Memory to score
            agent_scores: Agent improvement scores

        Returns:
            Priority score (0-1, higher = consolidate first)
        """
        score = 0.5  # Default baseline

        # Boost if from an improving agent
        if isinstance(memory, dict):
            agent = memory.get("source_agent")
            if agent and agent in agent_scores:
                # Weight: if agent is improving, memory is valuable
                score += agent_scores[agent] * 0.3

            # Boost if memory is high importance
            importance = float(memory.get("importance", 0.5))
            score += importance * 0.2

            # Boost if recent
            timestamp = memory.get("timestamp")
            if timestamp:
                age_hours = (datetime.now() - timestamp).total_seconds() / 3600
                recency = max(0, 1 - (age_hours / 168))  # Decay over week
                score += recency * 0.2

        return min(1.0, score)

    def select_consolidation_strategy(self, memory_count: int, agent_improvement_avg: float) -> str:
        """Select consolidation strategy based on learning.

        Args:
            memory_count: Number of memories to consolidate
            agent_improvement_avg: Average agent improvement score (0-1)

        Returns:
            Strategy name: "aggressive", "balanced", or "conservative"
        """
        # Track this decision for learning
        decision = None

        if agent_improvement_avg > 0.7:
            # Agents are improving fast - be aggressive with consolidation
            decision = "aggressive"
        elif agent_improvement_avg > 0.4:
            # Moderate improvement - balanced approach
            decision = "balanced"
        else:
            # Low improvement - conservative consolidation
            decision = "conservative"

        # Track the decision
        self._consolidation_experiments.append(
            {
                "timestamp": datetime.now(),
                "decision": decision,
                "memory_count": memory_count,
                "agent_improvement": agent_improvement_avg,
            }
        )

        return decision

    async def learn_consolidation_effectiveness(
        self,
        strategy_used: str,
        patterns_extracted: int,
        procedures_extracted: int,
        agent_feedback: Optional[Dict[str, float]] = None,
    ):
        """Learn effectiveness of consolidation strategy.

        Args:
            strategy_used: Strategy that was used ("aggressive", "balanced", "conservative")
            patterns_extracted: Number of patterns extracted
            procedures_extracted: Number of procedures extracted
            agent_feedback: Optional feedback from agents about consolidation
        """
        # Calculate success: did we extract patterns/procedures?
        extracted_total = patterns_extracted + procedures_extracted
        if extracted_total == 0:
            success_rate = 0.3  # Not very successful
            outcome = "failure"
        elif extracted_total < 5:
            success_rate = 0.6
            outcome = "partial"
        else:
            success_rate = 0.9
            outcome = "success"

        # Adjust if agents provided feedback
        if agent_feedback:
            avg_feedback = (
                sum(agent_feedback.values()) / len(agent_feedback) if agent_feedback else 0
            )
            success_rate = (success_rate + avg_feedback) / 2

        # Track this learning
        await self.tracker.track_outcome(
            agent_name="consolidation-optimizer",
            decision=f"consolidation_{strategy_used}",
            outcome=outcome,
            success_rate=success_rate,
            context={
                "patterns": patterns_extracted,
                "procedures": procedures_extracted,
                "agent_feedback_count": len(agent_feedback) if agent_feedback else 0,
            },
        )

    def get_optimal_consolidation_timing(
        self, agent_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Determine optimal timing for next consolidation.

        Uses learning to predict when consolidation will be most effective.

        Args:
            agent_names: Optional agents to analyze

        Returns:
            Dict with: next_consolidation_time, urgency (0-1), reason
        """
        # Get agents
        agents = agent_names or [
            "code-analyzer",
            "research-coordinator",
            "workflow-orchestrator",
            "metacognition",
        ]

        # Check agent improvement velocity
        improvement_scores = []
        for agent in agents:
            rate_now = self.tracker.get_success_rate(agent, time_window_hours=24)
            rate_6h = self.tracker.get_success_rate(agent, time_window_hours=30)  # ~6h avg

            if rate_6h > 0:
                velocity = (rate_now - rate_6h) / rate_6h
                improvement_scores.append(velocity)

        avg_velocity = (
            sum(improvement_scores) / len(improvement_scores) if improvement_scores else 0.0
        )

        # High improvement velocity = consolidate sooner (capture the learning)
        # Low improvement velocity = consolidate later (let more data accumulate)
        if avg_velocity > 0.2:
            hours_until = 4  # Soon
            urgency = 0.9
            reason = "Agents improving rapidly"
        elif avg_velocity > 0.05:
            hours_until = 12  # Normal schedule
            urgency = 0.5
            reason = "Steady agent improvement"
        else:
            hours_until = 24  # Later
            urgency = 0.1
            reason = "Waiting for agent improvement before consolidating"

        next_time = datetime.now() + timedelta(hours=hours_until)

        return {
            "next_consolidation": next_time.isoformat(),
            "hours_until": hours_until,
            "urgency": urgency,
            "reason": reason,
            "agent_velocity": avg_velocity,
        }

    def get_consolidation_stats(self) -> Dict[str, Any]:
        """Get statistics about consolidation learning.

        Returns:
            Dict with consolidation learning statistics
        """
        return {
            "total_experiments": len(self._consolidation_experiments),
            "strategies_used": len(set(e["decision"] for e in self._consolidation_experiments)),
            "consolidation_tracker_stats": self.tracker.get_statistics("consolidation-optimizer"),
        }
