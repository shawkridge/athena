"""Dependency graph engine for learning layer relationships and query patterns.

This module models how memory layers depend on each other, learning from actual
query execution patterns to optimize future executions. It tracks:
- Which layers typically appear together
- How often parallelization provides benefit
- Common query patterns and their layer requirements
- Cache worthiness of layer combinations

The dependency graph continuously updates as queries execute, enabling the
adaptive strategy selector to make increasingly accurate decisions.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json

from .performance_profiler import QueryMetrics, PerformanceProfiler

logger = logging.getLogger(__name__)


@dataclass
class LayerDependency:
    """Models relationship between two layers."""

    source_layer: str  # Layer that provides data
    target_layer: str  # Layer that depends on source
    co_occurrence_count: int = 0  # Times they've queried together
    avg_parallel_speedup: float = 1.0  # (Sequential time / Parallel time)
    sequential_only_count: int = 0  # Times target required source result first
    parallel_benefit: float = 0.0  # Estimated benefit (0-1) from parallelizing
    cache_worthiness: float = 0.0  # (0-1) Value of caching this pair


@dataclass
class QueryPattern:
    """Learned pattern from queries of same type."""

    query_type: str
    typical_layers: List[str]  # Layers usually queried for this type
    frequency: int = 0
    avg_success_rate: float = 0.95
    avg_latency_ms: float = 0.0
    cache_hit_rate: float = 0.0
    parallelization_benefit: float = 1.0  # Sequential / Parallel speedup


class DependencyGraph:
    """Learns and maintains layer dependency relationships.

    This graph continuously updates as queries execute, tracking:
    - Which layers query together (co-occurrence)
    - Benefits of parallelizing specific layer combinations
    - Common patterns for each query type
    - Cache worthiness of layer combinations

    Example:
        profiler = PerformanceProfiler()
        dep_graph = DependencyGraph(profiler)

        # Learn from query execution
        dep_graph.update_from_metrics(query_metrics)

        # Get smart recommendations
        layers = dep_graph.get_layer_selection("temporal", context)
        benefit = dep_graph.get_parallelization_benefit(layers)
        cached = dep_graph.get_cached_results(layers, query_hash)
    """

    def __init__(self, profiler: PerformanceProfiler, min_samples: int = 5):
        """Initialize dependency graph.

        Args:
            profiler: Performance profiler for historical metrics
            min_samples: Minimum observations before making recommendations
        """
        self.profiler = profiler
        self.min_samples = min_samples

        # Layer-to-layer dependencies
        self.dependencies: Dict[Tuple[str, str], LayerDependency] = {}

        # Query type patterns
        self.query_patterns: Dict[str, QueryPattern] = {}

        # Layer co-occurrence frequencies
        self.layer_co_occurrence: Dict[Tuple[str, str], int] = defaultdict(int)

        # Query patterns by type
        self.query_type_layers: Dict[str, List[str]] = {
            "temporal": ["episodic", "semantic"],
            "factual": ["semantic", "graph"],
            "relational": ["graph", "semantic"],
            "procedural": ["procedural", "semantic"],
            "prospective": ["prospective", "semantic"],
            "meta": ["meta", "semantic"],
            "planning": ["semantic", "procedural", "graph"],
        }

        # Cache of computed recommendations
        self._recommendation_cache: Dict[str, List[str]] = {}
        self._benefit_cache: Dict[str, float] = {}

        logger.info("DependencyGraph initialized")

    def update_from_metrics(self, metrics: QueryMetrics) -> None:
        """Learn dependencies from query execution metrics.

        Args:
            metrics: Query metrics containing layers queried and latencies
        """
        if len(metrics.layers_queried) < 2:
            return  # No dependencies with single layer

        # Update layer co-occurrence
        for i, layer1 in enumerate(metrics.layers_queried):
            for layer2 in metrics.layers_queried[i + 1 :]:
                pair = tuple(sorted([layer1, layer2]))
                self.layer_co_occurrence[pair] += 1

                # Update or create dependency
                dep_key = (layer1, layer2)
                if dep_key not in self.dependencies:
                    self.dependencies[dep_key] = LayerDependency(
                        source_layer=layer1,
                        target_layer=layer2,
                    )

                dep = self.dependencies[dep_key]
                dep.co_occurrence_count += 1

                # Calculate parallelization benefit
                if metrics.parallel_execution and metrics.layer_latencies:
                    l1_latency = metrics.layer_latencies.get(layer1, 0)
                    l2_latency = metrics.layer_latencies.get(layer2, 0)

                    if l1_latency > 0 and l2_latency > 0:
                        sequential_time = l1_latency + l2_latency
                        parallel_time = max(l1_latency, l2_latency)

                        if parallel_time > 0:
                            speedup = sequential_time / parallel_time
                            dep.avg_parallel_speedup = (
                                (dep.avg_parallel_speedup * (dep.co_occurrence_count - 1)) + speedup
                            ) / dep.co_occurrence_count

                # Calculate cache worthiness
                # (Success Rate × Result Count × Frequency) / Query Cost
                success_factor = 1.0 if metrics.success else 0.0
                frequency_factor = min(dep.co_occurrence_count / 100.0, 1.0)  # Cap at 1.0
                result_factor = min(metrics.result_count / 100.0, 1.0)
                cost_factor = max(metrics.latency_ms / 1000.0, 0.1)  # Avoid division by zero

                dep.cache_worthiness = (
                    success_factor * frequency_factor * result_factor
                ) / cost_factor

        # Update query patterns
        self._update_query_patterns(metrics)

        # Invalidate recommendation cache
        self._recommendation_cache.clear()
        self._benefit_cache.clear()

        logger.debug(
            f"Updated dependency graph from query {metrics.query_id}, "
            f"layers: {metrics.layers_queried}"
        )

    def _update_query_patterns(self, metrics: QueryMetrics) -> None:
        """Update patterns for this query type.

        Args:
            metrics: Query metrics for pattern extraction
        """
        query_type = metrics.query_type

        if query_type not in self.query_patterns:
            self.query_patterns[query_type] = QueryPattern(
                query_type=query_type,
                typical_layers=metrics.layers_queried,
            )

        pattern = self.query_patterns[query_type]
        pattern.frequency += 1
        pattern.avg_latency_ms = (
            (pattern.avg_latency_ms * (pattern.frequency - 1)) + metrics.latency_ms
        ) / pattern.frequency

        # Update success rate
        success_factor = 1.0 if metrics.success else 0.0
        pattern.avg_success_rate = (
            (pattern.avg_success_rate * (pattern.frequency - 1)) + success_factor
        ) / pattern.frequency

        # Update cache hit rate
        cache_factor = 1.0 if metrics.cache_hit else 0.0
        pattern.cache_hit_rate = (
            (pattern.cache_hit_rate * (pattern.frequency - 1)) + cache_factor
        ) / pattern.frequency

        # Update typical layers (if different from current)
        if metrics.layers_queried != pattern.typical_layers:
            # Weighted average towards new pattern
            current_set = set(pattern.typical_layers)
            new_set = set(metrics.layers_queried)

            # If new set is subset or similar, consider updating
            overlap = len(current_set & new_set) / max(len(current_set | new_set), 1)
            if overlap > 0.6:  # >60% overlap
                pattern.typical_layers = list(new_set)

    def get_layer_selection(self, query_type: str, context: Optional[Dict] = None) -> List[str]:
        """Get recommended layers to query for this query type.

        Args:
            query_type: Type of query (temporal, factual, relational, etc.)
            context: Optional context for more specific recommendations

        Returns:
            List of recommended layer names to query
        """
        # Check cache
        cache_key = f"{query_type}:{json.dumps(context or {}, sort_keys=True)}"
        if cache_key in self._recommendation_cache:
            return self._recommendation_cache[cache_key]

        # Use learned pattern if available
        if query_type in self.query_patterns:
            pattern = self.query_patterns[query_type]
            if pattern.frequency >= self.min_samples:
                result = pattern.typical_layers
                self._recommendation_cache[cache_key] = result
                return result

        # Fallback to defaults
        result = self.query_type_layers.get(query_type, ["semantic"])
        self._recommendation_cache[cache_key] = result
        return result

    def get_parallelization_benefit(self, layers: List[str]) -> float:
        """Estimate speedup from parallelizing these layers.

        Args:
            layers: List of layer names

        Returns:
            Estimated speedup factor (1.0 = no benefit, >1.0 = benefit)
        """
        if len(layers) <= 1:
            return 1.0

        # Check cache
        cache_key = ",".join(sorted(layers))
        if cache_key in self._benefit_cache:
            return self._benefit_cache[cache_key]

        total_benefit = 0.0
        pair_count = 0

        # Average parallelization benefit across all layer pairs
        for i, layer1 in enumerate(layers):
            for layer2 in layers[i + 1 :]:
                dep_key = (layer1, layer2)
                if dep_key in self.dependencies:
                    dep = self.dependencies[dep_key]
                    if (
                        dep.co_occurrence_count >= self.min_samples
                        and dep.avg_parallel_speedup > 1.0
                    ):
                        total_benefit += dep.avg_parallel_speedup
                        pair_count += 1

        if pair_count > 0:
            benefit = min(total_benefit / pair_count, 5.0)  # Cap at 5x
        else:
            # No observed benefit data, estimate from layer count
            benefit = min(len(layers) * 1.2, 3.0)

        self._benefit_cache[cache_key] = benefit
        return benefit

    def get_cached_results_benefit(self, layers: List[str]) -> float:
        """Estimate cache worthiness for this layer combination.

        Args:
            layers: List of layer names

        Returns:
            Cache worthiness score (0-1, higher = more worth caching)
        """
        if len(layers) == 0:
            return 0.0

        total_worthiness = 0.0
        pair_count = 0

        # Average cache worthiness across all layer pairs
        for i, layer1 in enumerate(layers):
            for layer2 in layers[i + 1 :]:
                dep_key = (layer1, layer2)
                if dep_key in self.dependencies:
                    total_worthiness += self.dependencies[dep_key].cache_worthiness
                    pair_count += 1

        if pair_count > 0:
            return min(total_worthiness / pair_count, 1.0)
        else:
            # No data, estimate based on layer count and frequency
            base_worthiness = 0.3
            frequency_bonus = min(self.profiler.metrics_count / 100, 0.3)
            return min(base_worthiness + frequency_bonus, 1.0)

    def get_query_pattern_stats(self, query_type: str) -> Optional[QueryPattern]:
        """Get learned statistics for a query type.

        Args:
            query_type: Type of query

        Returns:
            QueryPattern with statistics, or None if not enough data
        """
        pattern = self.query_patterns.get(query_type)
        if pattern and pattern.frequency >= self.min_samples:
            return pattern
        return None

    def get_layer_coupling_score(self, layer1: str, layer2: str) -> float:
        """Get how tightly coupled two layers are (0-1).

        Args:
            layer1: First layer
            layer2: Second layer

        Returns:
            Coupling score (0 = independent, 1 = always together)
        """
        dep_key = (layer1, layer2)
        if dep_key not in self.dependencies:
            return 0.0

        dep = self.dependencies[dep_key]

        # Normalize by total queries of these layers
        layer1_stats = self.profiler.get_layer_metrics(layer1)
        layer2_stats = self.profiler.get_layer_metrics(layer2)

        if not layer1_stats or not layer2_stats:
            return 0.0

        max_queries = max(layer1_stats.total_queries, layer2_stats.total_queries)
        if max_queries == 0:
            return 0.0

        coupling = min(dep.co_occurrence_count / max_queries, 1.0)
        return coupling

    def get_independent_layers(self, layers: List[str]) -> List[str]:
        """Get layers that are independent from the given set.

        Args:
            layers: Input layer names

        Returns:
            List of layers not typically queried with the input set
        """
        all_layers = {
            "episodic",
            "semantic",
            "procedural",
            "prospective",
            "graph",
            "meta",
        }
        input_set = set(layers)

        independent = []
        for layer in all_layers - input_set:
            is_independent = True
            for input_layer in input_set:
                coupling = self.get_layer_coupling_score(input_layer, layer)
                if coupling > 0.5:  # >50% coupling means not independent
                    is_independent = False
                    break

            if is_independent:
                independent.append(layer)

        return independent

    def get_graph_statistics(self) -> Dict[str, any]:
        """Get overall dependency graph statistics.

        Returns:
            Dictionary with graph metrics
        """
        total_edges = len(self.dependencies)
        avg_speedup = sum(d.avg_parallel_speedup for d in self.dependencies.values()) / max(
            total_edges, 1
        )
        avg_cache_worthiness = sum(d.cache_worthiness for d in self.dependencies.values()) / max(
            total_edges, 1
        )

        return {
            "total_edges": total_edges,
            "total_query_types": len(self.query_patterns),
            "total_observations": sum(d.co_occurrence_count for d in self.dependencies.values()),
            "avg_parallel_speedup": avg_speedup,
            "avg_cache_worthiness": avg_cache_worthiness,
            "most_coupled_layers": self._get_most_coupled_pair(),
            "least_coupled_layers": self._get_least_coupled_pair(),
        }

    def _get_most_coupled_pair(self) -> Optional[Tuple[str, str]]:
        """Get pair of layers with highest coupling."""
        if not self.dependencies:
            return None

        max_dep = max(
            self.dependencies.items(),
            key=lambda x: x[1].co_occurrence_count,
        )
        return (max_dep[1].source_layer, max_dep[1].target_layer)

    def _get_least_coupled_pair(self) -> Optional[Tuple[str, str]]:
        """Get pair of layers with lowest coupling."""
        if not self.dependencies:
            return None

        min_dep = min(
            self.dependencies.items(),
            key=lambda x: x[1].co_occurrence_count,
        )
        return (min_dep[1].source_layer, min_dep[1].target_layer)

    def reset(self) -> None:
        """Clear all learned patterns (for testing)."""
        self.dependencies.clear()
        self.query_patterns.clear()
        self.layer_co_occurrence.clear()
        self._recommendation_cache.clear()
        self._benefit_cache.clear()
        logger.info("DependencyGraph reset")
