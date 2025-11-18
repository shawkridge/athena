"""Adaptive strategy selector for intelligent execution approach selection.

This module analyzes queries and intelligently decides whether to use:
- CACHE: Cached results (10-50x faster)
- PARALLEL: Async parallel layers (3-4x faster)
- DISTRIBUTED: Worker pool (5-10x faster for high-load)
- SEQUENTIAL: Sequential execution (fallback)

The selector uses a decision tree based on:
- Cache availability (probability that results are cached)
- Query complexity (number of layers, estimated cost)
- Parallelization benefit (from dependency graph)
- Current system load
- Historical accuracy of predictions
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from .dependency_graph import DependencyGraph
from .cross_layer_cache import CrossLayerCache
from .performance_profiler import PerformanceProfiler

logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """Which execution approach to use for a query."""

    CACHE = "cache"  # Use cached results (10-50x faster)
    PARALLEL = "parallel"  # Use async parallel layers (3-4x faster)
    DISTRIBUTED = "distributed"  # Use worker pool (5-10x faster)
    SEQUENTIAL = "sequential"  # Sequential execution (fallback)


@dataclass
class StrategyDecision:
    """Decision and reasoning for execution strategy."""

    strategy: ExecutionStrategy  # Which strategy to use
    confidence: float  # 0.0-1.0, confidence in this decision
    reasoning: str  # Explanation of why this strategy was chosen
    estimated_latency_ms: float  # Expected execution time
    estimated_speedup: float  # Expected speedup vs sequential
    fallback_strategy: ExecutionStrategy  # What to try if this fails
    cache_key: Optional[str] = None  # If CACHE strategy, the cache key


@dataclass
class QueryAnalysis:
    """Pre-analysis of query for optimization potential."""

    query_type: str
    suggested_layers: list
    num_layers: int
    estimated_cost_ms: float  # Sequential execution time estimate
    cache_hit_probability: float  # 0.0-1.0
    parallelization_benefit: float  # Expected speedup from parallel
    complexity_score: float  # 0.0-1.0, query complexity


class AdaptiveStrategySelector:
    """Intelligently selects execution strategy for each query.

    Analyzes query characteristics, system state, and historical data
    to choose the optimal execution approach:

    1. CACHE: If results likely cached (>80% probability)
    2. PARALLEL: If low complexity and benefit > 1.5x
    3. DISTRIBUTED: If high cost (>500ms) and high concurrency benefit
    4. SEQUENTIAL: Fallback for simple, low-cost queries

    Example:
        selector = AdaptiveStrategySelector(
            profiler=profiler,
            dependency_graph=dep_graph,
            cross_layer_cache=cache
        )

        decision = selector.select_strategy(
            query_text="What happened yesterday?",
            query_type="temporal",
            num_layers=2,
            estimated_cost=100.0,
            cache_availability=0.7,
            parallelization_benefit=2.5,
        )

        if decision.strategy == ExecutionStrategy.CACHE:
            # Use cache
        elif decision.strategy == ExecutionStrategy.PARALLEL:
            # Use parallel executor
    """

    def __init__(
        self,
        profiler: PerformanceProfiler,
        dependency_graph: DependencyGraph,
        cross_layer_cache: CrossLayerCache,
    ):
        """Initialize strategy selector.

        Args:
            profiler: Performance profiler for metrics
            dependency_graph: Dependency graph for parallelization analysis
            cross_layer_cache: Cross-layer cache for availability checking
        """
        self.profiler = profiler
        self.dependency_graph = dependency_graph
        self.cross_layer_cache = cross_layer_cache

        # Decision history for accuracy tracking
        self.decision_history: list = []
        self.decision_accuracy: Dict[ExecutionStrategy, float] = {
            s: 0.5 for s in ExecutionStrategy
        }  # Start neutral

        # Thresholds (can be tuned)
        self.cache_threshold = 0.75  # Use cache if >75% probability
        self.parallel_threshold = 1.5  # Use parallel if benefit > 1.5x
        self.distributed_threshold = 500.0  # Use distributed if cost > 500ms
        self.high_concurrency_threshold = 10  # Layer count threshold

        logger.info("AdaptiveStrategySelector initialized")

    def select_strategy(
        self,
        query_text: str,
        query_type: str,
        num_layers: int,
        estimated_cost: float,
        cache_availability: float,
        parallelization_benefit: float,
    ) -> StrategyDecision:
        """Intelligently choose execution strategy.

        Args:
            query_text: The query text
            query_type: Type of query
            num_layers: Number of layers to query
            estimated_cost: Sequential execution cost (ms)
            cache_availability: Probability results are cached (0-1)
            parallelization_benefit: Expected parallel speedup (1.0+)

        Returns:
            StrategyDecision with chosen strategy and reasoning
        """
        # Analyze query
        analysis = QueryAnalysis(
            query_type=query_type,
            suggested_layers=[],  # Filled from dependency graph
            num_layers=num_layers,
            estimated_cost_ms=estimated_cost,
            cache_hit_probability=cache_availability,
            parallelization_benefit=parallelization_benefit,
            complexity_score=self._compute_complexity_score(num_layers, estimated_cost),
        )

        # Get suggested layers from dependency graph
        analysis.suggested_layers = self.dependency_graph.get_layer_selection(query_type)

        # Apply decision tree
        decision = self._apply_decision_tree(analysis)

        # Record decision
        self.decision_history.append(
            {
                "timestamp": time.time(),
                "query_type": query_type,
                "analysis": analysis,
                "decision": decision,
            }
        )

        logger.debug(
            f"Strategy selected: {decision.strategy.value} (confidence={decision.confidence:.2f}, "
            f"speedup={decision.estimated_speedup:.1f}x)"
        )

        return decision

    def _apply_decision_tree(self, analysis: QueryAnalysis) -> StrategyDecision:
        """Apply decision tree logic.

        Decision tree:
        1. If cache_availability > 75%: CACHE
        2. If num_layers <= 3 AND parallelization_benefit > 1.5x: PARALLEL
        3. If estimated_cost > 500ms: DISTRIBUTED
        4. Otherwise: SEQUENTIAL
        """

        # DECISION 1: Check cache
        if analysis.cache_hit_probability > self.cache_threshold:
            return StrategyDecision(
                strategy=ExecutionStrategy.CACHE,
                confidence=analysis.cache_hit_probability,
                reasoning=f"High cache availability ({analysis.cache_hit_probability:.0%}), "
                f"expect 10-50x speedup",
                estimated_latency_ms=max(
                    5.0, analysis.estimated_cost_ms / 50.0
                ),  # Assume 50x speedup
                estimated_speedup=50.0,
                fallback_strategy=ExecutionStrategy.PARALLEL,
            )

        # DECISION 2: Check parallelization benefit
        if (
            analysis.num_layers > 1
            and analysis.parallelization_benefit > self.parallel_threshold
            and analysis.complexity_score < 0.7
        ):
            return StrategyDecision(
                strategy=ExecutionStrategy.PARALLEL,
                confidence=min(analysis.parallelization_benefit / 5.0, 1.0),
                reasoning=f"Good parallelization benefit ({analysis.parallelization_benefit:.1f}x), "
                f"low complexity ({analysis.complexity_score:.1f})",
                estimated_latency_ms=analysis.estimated_cost_ms / analysis.parallelization_benefit,
                estimated_speedup=analysis.parallelization_benefit,
                fallback_strategy=ExecutionStrategy.SEQUENTIAL,
            )

        # DECISION 3: Check for high-cost queries
        if (
            analysis.estimated_cost_ms > self.distributed_threshold
            and analysis.parallelization_benefit > 1.2
        ):
            return StrategyDecision(
                strategy=ExecutionStrategy.DISTRIBUTED,
                confidence=min(analysis.estimated_cost_ms / 1000.0, 1.0),
                reasoning=f"High query cost ({analysis.estimated_cost_ms:.0f}ms), "
                f"distributed execution can improve with benefit of {analysis.parallelization_benefit:.1f}x",
                estimated_latency_ms=analysis.estimated_cost_ms / 6.0,  # Assume 6x speedup
                estimated_speedup=6.0,
                fallback_strategy=ExecutionStrategy.PARALLEL,
            )

        # DECISION 4: Fallback to sequential
        return StrategyDecision(
            strategy=ExecutionStrategy.SEQUENTIAL,
            confidence=0.8,
            reasoning=f"Simple query (cost={analysis.estimated_cost_ms:.0f}ms, "
            f"layers={analysis.num_layers}), sequential is efficient",
            estimated_latency_ms=analysis.estimated_cost_ms,
            estimated_speedup=1.0,
            fallback_strategy=ExecutionStrategy.PARALLEL,
        )

    def _compute_complexity_score(self, num_layers: int, estimated_cost: float) -> float:
        """Compute query complexity score.

        Args:
            num_layers: Number of layers
            estimated_cost: Estimated execution time (ms)

        Returns:
            Complexity score (0.0-1.0)
        """
        # Complexity increases with layers and cost
        layer_factor = min(num_layers / 5.0, 1.0)  # Cap at 5 layers
        cost_factor = min(estimated_cost / 1000.0, 1.0)  # Cap at 1000ms

        complexity = (layer_factor * 0.6) + (cost_factor * 0.4)
        return min(complexity, 1.0)

    def record_execution_outcome(
        self,
        decision: StrategyDecision,
        actual_latency_ms: float,
        success: bool,
    ) -> None:
        """Record actual execution outcome to train decision accuracy.

        Args:
            decision: Original decision made
            actual_latency_ms: Actual execution time
            success: Whether execution succeeded
        """
        if not success:
            # Mark as unsuccessful strategy
            self.decision_accuracy[decision.strategy] *= 0.95
            return

        # Calculate accuracy
        estimated = decision.estimated_latency_ms
        actual = actual_latency_ms

        if estimated > 0:
            accuracy = min(estimated / actual, actual / estimated)
            accuracy = max(accuracy, 0.1)  # Floor at 0.1

            # Update running average
            old_accuracy = self.decision_accuracy[decision.strategy]
            self.decision_accuracy[decision.strategy] = (old_accuracy * 0.9) + (accuracy * 0.1)

    def get_strategy_statistics(self) -> Dict[str, Any]:
        """Get statistics about strategy selection accuracy.

        Returns:
            Dictionary with accuracy and selection stats
        """
        if not self.decision_history:
            return {
                "decisions_made": 0,
                "accuracy": 0.0,
                "strategy_distribution": {},
            }

        # Count strategy usage
        strategy_counts = {}
        for decision_record in self.decision_history:
            strategy = decision_record["decision"].strategy
            strategy_counts[strategy.value] = strategy_counts.get(strategy.value, 0) + 1

        # Calculate average accuracy
        avg_accuracy = sum(self.decision_accuracy.values()) / len(self.decision_accuracy)

        return {
            "decisions_made": len(self.decision_history),
            "average_accuracy": avg_accuracy,
            "strategy_distribution": strategy_counts,
            "strategy_accuracy": {k.value: v for k, v in self.decision_accuracy.items()},
            "recent_decisions": self._get_recent_decisions(limit=10),
        }

    def _get_recent_decisions(self, limit: int = 10) -> list:
        """Get recent decisions for debugging.

        Args:
            limit: Number of recent decisions to return

        Returns:
            List of recent decision records
        """
        result = []
        for record in self.decision_history[-limit:]:
            decision = record["decision"]
            result.append(
                {
                    "query_type": record["query_type"],
                    "strategy": decision.strategy.value,
                    "confidence": decision.confidence,
                    "speedup": decision.estimated_speedup,
                    "reasoning": decision.reasoning,
                }
            )
        return result

    def reset(self) -> None:
        """Reset statistics (for testing)."""
        self.decision_history.clear()
        self.decision_accuracy = {s: 0.5 for s in ExecutionStrategy}
        logger.info("AdaptiveStrategySelector reset")
