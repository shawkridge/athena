"""Pattern-based retrieval using learned patterns from AdaptiveAgent learning.

Uses patterns extracted during consolidation to improve retrieval quality.
Learns which retrieval strategies work best and adapts query expansion.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from athena.learning.tracker import LearningTracker
from athena.core.database import Database


class PatternBasedRetrieval:
    """Advanced retrieval that learns from agent outcomes and patterns.

    Uses learned patterns to:
    - Expand queries with related concepts
    - Score results based on pattern similarity
    - Adapt retrieval strategies by success rate
    - Recognize when similar problems succeeded before
    """

    def __init__(self, db: Database):
        """Initialize pattern-based retrieval.

        Args:
            db: Database for access to patterns and learning outcomes
        """
        self.db = db
        self.tracker = LearningTracker(db)
        self._pattern_cache = {}  # Cache learned patterns
        self._strategy_stats = {}  # Track which strategies work

    async def retrieve_with_patterns(
        self, query: str, agent_name: str, limit: int = 10, time_window_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Retrieve memories using learned patterns from agent history.

        Strategy:
        1. Get agent's success history for similar queries
        2. Expand query with patterns that worked before
        3. Retrieve using expanded query
        4. Re-rank by pattern similarity
        5. Track which strategy performed best

        Args:
            query: Original search query
            agent_name: Agent making the query (for learning context)
            limit: Max results to return
            time_window_days: Only use patterns from last N days

        Returns:
            List of retrieved memories with pattern scores
        """
        # Get agent's decision history to identify patterns
        history = self.tracker.get_decision_history(agent_name, limit=50)

        # Extract patterns: what decisions led to success?
        successful_patterns = self._extract_success_patterns(
            history, time_window_days=time_window_days
        )

        # Expand query with successful patterns
        expanded_query = self._expand_query(query, successful_patterns)

        # Retrieve memories (would call RAG manager in real implementation)
        results = await self._retrieve_base(expanded_query, limit)

        # Re-rank by pattern relevance
        ranked = self._rerank_by_patterns(results, successful_patterns)

        # Track that we used this strategy
        await self.tracker.track_outcome(
            agent_name=f"{agent_name}-retrieval",
            decision=f"pattern_expansion_{len(successful_patterns)}_patterns",
            outcome="success" if ranked else "partial",
            success_rate=0.8 if ranked else 0.3,
            context={
                "query": query,
                "expanded_with": len(successful_patterns),
                "results_count": len(ranked),
            },
        )

        return ranked

    def _extract_success_patterns(
        self, history: List, time_window_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Extract patterns from successful decisions.

        Args:
            history: Decision history from LearningTracker
            time_window_days: Only consider recent decisions

        Returns:
            List of patterns that led to success
        """
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        patterns = []

        for outcome in history:
            # Only look at successes
            if outcome.outcome != "success":
                continue

            # Only recent
            if outcome.timestamp < cutoff_date:
                continue

            # Extract decision as a pattern
            pattern = {
                "decision": outcome.decision,
                "success_rate": outcome.success_rate,
                "context": outcome.context,
                "frequency": 1,  # Will aggregate
            }
            patterns.append(pattern)

        # Aggregate: count frequency of each decision
        aggregated = {}
        for p in patterns:
            decision = p["decision"]
            if decision not in aggregated:
                aggregated[decision] = {
                    "decision": decision,
                    "avg_success_rate": 0.0,
                    "frequency": 0,
                    "contexts": [],
                }
            aggregated[decision]["frequency"] += 1
            aggregated[decision]["contexts"].append(p["context"])

        # Calculate averages
        result = []
        for decision, data in aggregated.items():
            result.append(
                {
                    "pattern": decision,
                    "success_rate": data["avg_success_rate"] / max(data["frequency"], 1),
                    "frequency": data["frequency"],
                    "examples": data["contexts"][:3],  # Keep top 3 examples
                }
            )

        return sorted(result, key=lambda x: x["success_rate"], reverse=True)

    def _expand_query(self, query: str, patterns: List[Dict[str, Any]]) -> str:
        """Expand query with learned patterns.

        Args:
            query: Original query
            patterns: Successful patterns to incorporate

        Returns:
            Expanded query incorporating patterns
        """
        if not patterns:
            return query

        # Use top 3 patterns for expansion
        pattern_keywords = []
        for p in patterns[:3]:
            pattern_keywords.append(p["pattern"])

        # Create expanded query
        expanded = f"{query} OR ({' OR '.join(pattern_keywords)})"
        return expanded

    def _rerank_by_patterns(
        self, results: List[Dict[str, Any]], patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Re-rank results by similarity to learned patterns.

        Args:
            results: Retrieved results
            patterns: Learned patterns

        Returns:
            Re-ranked results with pattern scores
        """
        if not patterns or not results:
            return results

        # Score each result by pattern match
        scored = []
        for result in results:
            pattern_score = 0.0
            match_count = 0

            # Check if result content matches any pattern
            result_text = str(result.get("content", "")).lower()

            for pattern in patterns:
                if pattern["pattern"].lower() in result_text:
                    pattern_score += pattern["success_rate"]
                    match_count += 1

            # Average pattern score
            if match_count > 0:
                pattern_score = pattern_score / match_count
            else:
                pattern_score = 0.5  # Default if no match

            result["pattern_score"] = pattern_score
            scored.append(result)

        # Sort by pattern score (descending)
        return sorted(scored, key=lambda x: x.get("pattern_score", 0), reverse=True)

    async def _retrieve_base(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Base retrieval (would call actual RAG in production).

        Args:
            query: Query to retrieve
            limit: Max results

        Returns:
            Retrieved memories (mock for now)
        """
        # In production, this would call RAGManager
        # For now, return empty list (will integrate with RAGManager)
        return []

    async def learn_retrieval_effectiveness(
        self,
        agent_name: str,
        strategy: str,
        results_count: int,
        user_feedback: Optional[float] = None,
    ):
        """Learn which retrieval strategies work best.

        Args:
            agent_name: Agent performing retrieval
            strategy: Retrieval strategy used
            results_count: Number of results returned
            user_feedback: Optional feedback score (0-1)
        """
        # Evaluate success: got results?
        if results_count == 0:
            success_rate = 0.1
            outcome = "failure"
        elif results_count < 3:
            success_rate = 0.5
            outcome = "partial"
        else:
            success_rate = 0.9
            outcome = "success"

        # If user gave feedback, use it
        if user_feedback is not None:
            success_rate = user_feedback
            outcome = "success" if user_feedback > 0.5 else "failure"

        # Track this
        await self.tracker.track_outcome(
            agent_name=f"{agent_name}-retrieval",
            decision=strategy,
            outcome=outcome,
            success_rate=success_rate,
            context={"results_count": results_count},
        )

    def get_best_strategy(self, agent_name: str) -> str:
        """Get the best-performing retrieval strategy for an agent.

        Args:
            agent_name: Agent to analyze

        Returns:
            Best strategy name
        """
        # Query learning tracker for this agent's retrieval stats
        success_rate = self.tracker.get_success_rate(
            f"{agent_name}-retrieval", time_window_hours=24
        )

        # For now, return default
        # In production, would analyze different strategies
        return "pattern_based" if success_rate > 0.6 else "fallback_basic"
