"""AdaptiveAgent - Base class for learning agents.

Agents that inherit from AdaptiveAgent can:
- Make decisions based on historical success rates
- Track outcomes of their decisions
- Adapt strategy selection based on learning
"""

from abc import ABC, abstractmethod
from typing import Optional, Any

from athena.learning.tracker import LearningTracker
from athena.core.database import Database


class AdaptiveAgent(ABC):
    """Base class for agents that learn and adapt from outcomes.

    Subclasses implement:
    - decide() - Make a decision (which strategy to use)
    - execute() - Execute the decision
    - learn_from_outcome() - Adapt based on result

    Example:
        class CodeAnalyzer(AdaptiveAgent):
            async def decide(self, code_snippet):
                # Choose analysis depth based on success rates
                success_rate = self.tracker.get_success_rate(self.agent_name, "deep_analysis")
                if success_rate > 0.8:
                    return "deep_analysis"
                return "quick_analysis"

            async def execute(self, decision, code_snippet):
                # Perform analysis with chosen strategy
                return await self._analyze_with_strategy(decision, code_snippet)

            async def learn_from_outcome(self, decision, outcome, success_rate):
                # Remember what worked
                await self.tracker.track_outcome(
                    agent_name=self.agent_name,
                    decision=decision,
                    outcome=outcome,
                    success_rate=success_rate
                )
    """

    def __init__(self, agent_name: str, db: Database):
        """Initialize adaptive agent.

        Args:
            agent_name: Unique name for this agent (used in tracking)
            db: Database instance for storing outcomes
        """
        self.agent_name = agent_name
        self.db = db
        self.tracker = LearningTracker(db)
        self._decision_history = []  # Track recent decisions in memory

    @abstractmethod
    async def decide(self, context: dict) -> str:
        """Make a decision based on available context and learning.

        This method should:
        1. Query success_rate from tracker for candidate strategies
        2. Select best strategy based on historical performance
        3. Fall back to default if no history

        Args:
            context: Decision context (what are we working on?)

        Returns:
            Decision string (e.g., "deep_analysis", "quick_scan", "use_cache")
        """
        pass

    @abstractmethod
    async def execute(self, decision: str, context: dict) -> Any:
        """Execute the decision.

        Args:
            decision: Decision made by decide()
            context: Same context passed to decide()

        Returns:
            Result of executing the decision
        """
        pass

    async def run(self, context: dict, session_id: Optional[str] = None) -> dict:
        """Execute the decide-execute-learn cycle.

        This is the main orchestration method that:
        1. Makes a decision
        2. Executes it
        3. Evaluates outcome
        4. Learns from result

        Args:
            context: Decision context
            session_id: Optional session identifier for tracking

        Returns:
            Dict with: decision, result, success_rate, outcome
        """
        try:
            # Step 1: Make decision
            decision = await self.decide(context)
            self._decision_history.append(decision)

            # Step 2: Execute decision
            result = await self.execute(decision, context)

            # Step 3: Evaluate outcome
            success_rate, outcome = await self._evaluate_outcome(result, decision, context)

            # Step 4: Learn
            await self.learn_from_outcome(
                decision=decision,
                outcome=outcome,
                success_rate=success_rate,
                context=context,
                session_id=session_id,
            )

            return {
                "decision": decision,
                "result": result,
                "success_rate": success_rate,
                "outcome": outcome,
            }

        except Exception:
            # Track failures too
            await self.learn_from_outcome(
                decision=getattr(self, "_last_decision", "unknown"),
                outcome="error",
                success_rate=0.0,
                context=context,
                session_id=session_id,
            )
            raise

    async def learn_from_outcome(
        self,
        decision: str,
        outcome: str,
        success_rate: float,
        context: dict,
        session_id: Optional[str] = None,
    ):
        """Learn from decision outcome.

        Default implementation records to tracker.
        Subclasses can override to customize learning.

        Args:
            decision: The decision that was made
            outcome: Result - 'success', 'failure', 'partial', 'error'
            success_rate: Score 0.0-1.0 indicating success
            context: Context from decision
            session_id: Optional session id
        """
        await self.tracker.track_outcome(
            agent_name=self.agent_name,
            decision=decision,
            outcome=outcome,
            success_rate=success_rate,
            context=context,
            session_id=session_id,
        )

    async def _evaluate_outcome(
        self, result: Any, decision: str, context: dict
    ) -> tuple[float, str]:
        """Evaluate result to determine success rate and outcome type.

        Default implementation checks for None/empty results.
        Subclasses should override for domain-specific evaluation.

        Args:
            result: Result from execute()
            decision: Decision that was executed
            context: Original context

        Returns:
            Tuple of (success_rate: 0.0-1.0, outcome: 'success'|'failure'|'partial'|'error')
        """
        if result is None or (isinstance(result, (list, dict)) and not result):
            return 0.0, "failure"

        if isinstance(result, dict):
            # Check for explicit success indicator
            if result.get("success") is True:
                return result.get("confidence", 0.9), "success"
            if result.get("success") is False:
                return 0.0, "failure"
            # Partial success
            if result.get("partial"):
                return 0.5, "partial"

        # Default: success
        return 0.8, "success"

    def get_recent_decisions(self, limit: int = 10) -> list[str]:
        """Get recent decisions made by this agent.

        Args:
            limit: Maximum decisions to return

        Returns:
            List of decision strings, most recent first
        """
        return self._decision_history[-limit:][::-1]

    async def get_performance_stats(self) -> dict:
        """Get performance statistics for this agent.

        Returns:
            Dict with: total_decisions, success_rate, decision_breakdown
        """
        stats = self.tracker.get_statistics(self.agent_name)  # get_statistics is synchronous
        return {
            "agent_name": self.agent_name,
            "total_decisions": stats["total_decisions"],
            "success_rate": stats["success_rate"],
            "avg_execution_time_ms": stats["avg_execution_time_ms"],
            "recent_decisions": self.get_recent_decisions(10),
        }
