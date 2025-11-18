"""Feedback Loop - Feed learning insights back to adaptive agents.

Closes the loop: Agents make decisions -> Learn from outcomes -> Update strategies

Pattern:
1. Agent decides using strategy S1
2. Hook records outcome
3. Learning system analyzes
4. Next time: Agent queries success rate of S1
5. Agent chooses better strategy for next decision

Implements reinforcement learning for agent decision-making.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AgentFeedbackCollector:
    """Collects outcomes from agent decisions for feedback."""

    def __init__(self):
        """Initialize feedback collector."""
        self._decision_history = {}  # agent -> [decisions]

    async def record_decision(
        self, agent_name: str, strategy_used: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a decision before execution.

        Returns decision_id for later outcome tracking.

        Args:
            agent_name: Name of agent
            strategy_used: Strategy chosen
            context: Decision context

        Returns:
            Decision ID for outcome tracking
        """
        decision_id = f"{agent_name}_{strategy_used}_{datetime.now().timestamp()}"

        if agent_name not in self._decision_history:
            self._decision_history[agent_name] = []

        self._decision_history[agent_name].append(
            {
                "id": decision_id,
                "strategy": strategy_used,
                "context": context,
                "timestamp": datetime.now(),
                "outcome": None,  # Will be filled later
            }
        )

        return decision_id

    async def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        success_score: float,
        result_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record outcome of a decision.

        Args:
            decision_id: ID from record_decision
            outcome: success/failure/partial
            success_score: 0.0-1.0 score
            result_context: Additional context

        Returns:
            Feedback summary
        """
        # Find the decision
        for agent_name, decisions in self._decision_history.items():
            for decision in decisions:
                if decision["id"] == decision_id:
                    decision["outcome"] = outcome
                    decision["success_score"] = success_score
                    decision["result_context"] = result_context
                    decision["outcome_timestamp"] = datetime.now()

                    return {
                        "status": "success",
                        "decision_id": decision_id,
                        "agent": agent_name,
                        "strategy": decision["strategy"],
                        "outcome": outcome,
                        "success": success_score,
                        "learning_recorded": True,
                    }

        return {
            "status": "not_found",
            "decision_id": decision_id,
            "error": "Decision not found in history",
        }

    def get_strategy_effectiveness(
        self, agent_name: str, time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get effectiveness of strategies used by agent.

        Args:
            agent_name: Agent to analyze
            time_window_hours: Look back period

        Returns:
            Strategy effectiveness statistics
        """
        if agent_name not in self._decision_history:
            return {"agent": agent_name, "strategies": {}, "samples": 0}

        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        decisions = [
            d
            for d in self._decision_history[agent_name]
            if d["timestamp"] >= cutoff and d["outcome"]
        ]

        if not decisions:
            return {"agent": agent_name, "strategies": {}, "samples": 0}

        # Group by strategy
        by_strategy = {}
        for decision in decisions:
            strategy = decision["strategy"]
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            by_strategy[strategy].append(decision)

        # Calculate effectiveness
        strategies = {}
        for strategy, decisions_list in by_strategy.items():
            outcomes = [d.get("success_score", 0.0) for d in decisions_list]
            avg_success = sum(outcomes) / len(outcomes) if outcomes else 0.0

            strategies[strategy] = {
                "success_rate": avg_success,
                "uses": len(decisions_list),
                "last_used": decisions_list[-1]["outcome_timestamp"].isoformat(),
            }

        return {
            "agent": agent_name,
            "strategies": strategies,
            "samples": len(decisions),
            "time_window_hours": time_window_hours,
        }

    def recommend_strategy(
        self, agent_name: str, available_strategies: List[str], time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Recommend which strategy agent should use.

        Args:
            agent_name: Agent making decision
            available_strategies: Strategies to choose from
            time_window_hours: Look back period

        Returns:
            Recommendation with reasoning
        """
        effectiveness = self.get_strategy_effectiveness(agent_name, time_window_hours)

        if not effectiveness["strategies"]:
            # No history - recommend trying each strategy
            return {
                "status": "no_history",
                "recommendation": "Try different strategies to build data",
                "suggested_strategy": available_strategies[0] if available_strategies else None,
                "confidence": 0.0,
            }

        # Score available strategies
        strategy_scores = {}
        for strategy in available_strategies:
            if strategy in effectiveness["strategies"]:
                info = effectiveness["strategies"][strategy]
                # Success rate with confidence adjustment (more uses = more confidence)
                uses = info["uses"]
                confidence = min(1.0, uses / 10.0)  # Full confidence after 10 uses
                score = info["success_rate"] * confidence
            else:
                score = 0.5  # Neutral score for untested strategies
                uses = 0

            strategy_scores[strategy] = {
                "score": score,
                "uses": uses,
                "base_rate": (
                    info.get("success_rate", 0.5)
                    if strategy in effectiveness["strategies"]
                    else None
                ),
            }

        # Find best strategy
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1]["score"])

        return {
            "status": "success",
            "recommendation": best_strategy[0],
            "score": best_strategy[1]["score"],
            "confidence": min(1.0, best_strategy[1]["uses"] / 10.0),
            "reasoning": f"Based on {best_strategy[1]['uses']} uses in last {time_window_hours}h",
            "all_scores": strategy_scores,
        }


class LearningInsightProvider:
    """Provides insights from learning system to agents."""

    def __init__(self, feedback_collector: AgentFeedbackCollector):
        """Initialize insight provider.

        Args:
            feedback_collector: Collector instance to query
        """
        self.collector = feedback_collector

    async def get_decision_guidance(
        self, agent_name: str, decision_type: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get guidance for an upcoming decision.

        Args:
            agent_name: Agent making decision
            decision_type: Type of decision
            context: Decision context

        Returns:
            Guidance with recommendations
        """
        try:
            # Try to get strategy effectiveness
            # (Agent would implement this based on their strategies)
            effectiveness = self.collector.get_strategy_effectiveness(agent_name)

            if effectiveness["samples"] == 0:
                return {
                    "status": "learning",
                    "guidance": "Insufficient data - keep exploring",
                    "confidence": 0.0,
                    "samples": 0,
                }

            # Provide summary
            best_strategy = None
            best_rate = 0.0
            for strategy, info in effectiveness["strategies"].items():
                if info["success_rate"] > best_rate:
                    best_rate = info["success_rate"]
                    best_strategy = strategy

            return {
                "status": "success",
                "guidance": f"Best strategy: {best_strategy} ({best_rate:.0%} success)",
                "best_strategy": best_strategy,
                "success_rate": best_rate,
                "samples": effectiveness["samples"],
                "confidence": min(1.0, effectiveness["samples"] / 10.0),
            }

        except Exception as e:
            logger.error(f"Failed to get decision guidance: {e}")
            return {"status": "error", "error": str(e), "guidance": "Guidance unavailable"}

    def explain_outcome(
        self, agent_name: str, strategy_used: str, outcome: str, success_score: float
    ) -> Dict[str, Any]:
        """Explain why outcome occurred given strategy.

        Args:
            agent_name: Agent making decision
            strategy_used: Strategy used
            outcome: Result
            success_score: Success metric

        Returns:
            Explanation for learning
        """
        effectiveness = self.collector.get_strategy_effectiveness(agent_name)

        if strategy_used not in effectiveness["strategies"]:
            return {
                "status": "new_strategy",
                "explanation": f"This is a new strategy for {agent_name}",
                "is_improvement": False,
                "guidance": "Track outcomes to measure effectiveness",
            }

        strategy_info = effectiveness["strategies"][strategy_used]
        historical_rate = strategy_info["success_rate"]

        if success_score > historical_rate:
            return {
                "status": "improvement",
                "explanation": f"Better than usual ({success_score:.0%} vs {historical_rate:.0%})",
                "is_improvement": True,
                "guidance": "This is a good execution - try to repeat",
            }
        elif success_score < historical_rate * 0.8:
            return {
                "status": "regression",
                "explanation": f"Worse than usual ({success_score:.0%} vs {historical_rate:.0%})",
                "is_improvement": False,
                "guidance": "Something was different - investigate and adapt",
            }
        else:
            return {
                "status": "normal",
                "explanation": "Consistent with typical performance",
                "is_improvement": False,
                "guidance": "Continue with this strategy",
            }

    def suggest_exploration(
        self, agent_name: str, available_strategies: List[str], exploration_rate: float = 0.1
    ) -> Optional[str]:
        """Suggest exploring a less-tested strategy.

        Implements epsilon-greedy exploration.

        Args:
            agent_name: Agent
            available_strategies: Strategies to choose from
            exploration_rate: Probability of exploration (default 10%)

        Returns:
            Strategy to explore, or None if should exploit best
        """
        import random

        if random.random() > exploration_rate:
            # Exploit best strategy
            return None

        # Explore: pick least-tested strategy
        effectiveness = self.collector.get_strategy_effectiveness(agent_name)

        use_counts = {
            s: effectiveness["strategies"].get(s, {}).get("uses", 0) for s in available_strategies
        }

        # Find strategy with fewest uses
        least_tested = min(use_counts.items(), key=lambda x: x[1])
        return least_tested[0]
