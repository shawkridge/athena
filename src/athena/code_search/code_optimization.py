"""Performance optimization system for code search operations.

Provides query optimization, batch processing, parallel execution, and
performance profiling to maximize throughput and minimize latency.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Optimization levels."""

    NONE = 0
    BASIC = 1
    AGGRESSIVE = 2
    MAXIMUM = 3


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation."""

    operation: str
    execution_time_ms: float
    memory_used_mb: float = 0.0
    cache_hits: int = 0
    items_processed: int = 0
    throughput_ops_per_sec: float = 0.0

    def calculate_throughput(self) -> float:
        """Calculate throughput in operations per second."""
        if self.execution_time_ms <= 0:
            return 0.0
        seconds = self.execution_time_ms / 1000
        return self.items_processed / seconds if seconds > 0 else 0.0


class QueryOptimizer:
    """Optimizes queries for faster execution."""

    def __init__(self):
        """Initialize query optimizer."""
        self.optimization_history: Dict[str, PerformanceMetrics] = {}
        self.common_patterns: Dict[str, float] = {}

    def optimize_query(
        self, query_text: str, optimization_level: OptimizationLevel = OptimizationLevel.BASIC
    ) -> str:
        """Optimize query text for faster execution."""
        optimized = query_text

        if optimization_level == OptimizationLevel.NONE:
            return optimized

        # Basic: Remove extra whitespace
        optimized = " ".join(optimized.split())

        if optimization_level.value >= OptimizationLevel.BASIC.value:
            # Remove common stop words that don't affect meaning
            stop_words = {"the", "a", "and", "or", "in", "of", "to", "from"}
            terms = optimized.split()
            optimized = " ".join(t for t in terms if t.lower() not in stop_words)

        if optimization_level.value >= OptimizationLevel.AGGRESSIVE.value:
            # Reorder terms by estimated selectivity (specific before general)
            terms = optimized.split()
            terms.sort(key=lambda t: -len(t))  # Longer, more specific terms first
            optimized = " ".join(terms)

        if optimization_level.value >= OptimizationLevel.MAXIMUM.value:
            # Apply learned patterns
            for pattern, benefit in self.common_patterns.items():
                if pattern in optimized.lower():
                    # Pattern is present - this query may benefit from special handling
                    pass

        return optimized

    def predict_query_cost(self, query_text: str) -> float:
        """Predict execution cost (0-1, where 1 is most expensive)."""
        # Cost factors: term count, filter complexity, boolean operators
        factors = 0.0

        # Term count
        term_count = len(query_text.split())
        factors += min(term_count * 0.1, 0.3)

        # Filter complexity
        filters = query_text.count("with") + query_text.count("where")
        factors += min(filters * 0.15, 0.3)

        # Boolean operators
        boolean_ops = query_text.lower().count(" and ") + query_text.lower().count(" or ")
        factors += min(boolean_ops * 0.2, 0.4)

        return min(factors, 1.0)

    def record_query_performance(self, query: str, metrics: PerformanceMetrics) -> None:
        """Record performance metrics for a query."""
        self.optimization_history[query] = metrics


class SearchOptimizer:
    """Optimizes search result processing."""

    def __init__(self, max_results_threshold: int = 1000):
        """Initialize search optimizer."""
        self.max_results_threshold = max_results_threshold

    def optimize_result_processing(
        self,
        results: List[Dict[str, Any]],
        optimization_level: OptimizationLevel = OptimizationLevel.BASIC,
    ) -> List[Dict[str, Any]]:
        """Optimize result processing and filtering."""
        if optimization_level == OptimizationLevel.NONE:
            return results

        optimized = results

        # Basic: Deduplication
        if optimization_level.value >= OptimizationLevel.BASIC.value:
            seen = set()
            deduplicated = []
            for r in optimized:
                entity_id = (r.get("name"), r.get("file_path"))
                if entity_id not in seen:
                    deduplicated.append(r)
                    seen.add(entity_id)
            optimized = deduplicated

        # Aggressive: Score sorting optimization
        if optimization_level.value >= OptimizationLevel.AGGRESSIVE.value:
            # Sort by score descending (highest first)
            optimized = sorted(optimized, key=lambda r: r.get("combined_score", 0), reverse=True)

        # Maximum: Truncate at threshold
        if optimization_level.value >= OptimizationLevel.MAXIMUM.value:
            if len(optimized) > self.max_results_threshold:
                optimized = optimized[: self.max_results_threshold]

        return optimized

    def estimate_result_quality(self, results: List[Dict[str, Any]]) -> float:
        """Estimate average quality of results (0-1)."""
        if not results:
            return 0.0

        # Average combined score
        scores = [r.get("combined_score", 0) for r in results if isinstance(r, dict)]
        return sum(scores) / len(scores) if scores else 0.0


class BatchOptimizer:
    """Optimizes batch operations."""

    def __init__(self, optimal_batch_size: int = 100):
        """Initialize batch optimizer."""
        self.optimal_batch_size = optimal_batch_size

    def calculate_optimal_batch_size(
        self,
        items_count: int,
        item_size_bytes: float = 1000,
        memory_limit_mb: float = 1024,
    ) -> int:
        """Calculate optimal batch size for processing."""
        memory_limit_bytes = memory_limit_mb * 1024 * 1024
        max_items_by_memory = int(memory_limit_bytes / max(item_size_bytes, 1))
        optimal = min(max_items_by_memory, self.optimal_batch_size)
        return max(optimal, 1)

    def batch_items(self, items: List[Any], batch_size: Optional[int] = None) -> List[List[Any]]:
        """Split items into optimized batches."""
        if batch_size is None:
            batch_size = self.calculate_optimal_batch_size(len(items))

        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i : i + batch_size])
        return batches


class PerformanceProfiler:
    """Profiles and monitors performance."""

    def __init__(self):
        """Initialize profiler."""
        self.metrics: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self.operation_times: Dict[str, List[float]] = defaultdict(list)

    def profile_operation(
        self, operation_name: str, func: Callable, *args, **kwargs
    ) -> Tuple[Any, PerformanceMetrics]:
        """Profile an operation's execution time."""
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_ms = (time.time() - start_time) * 1000

        metrics = PerformanceMetrics(
            operation=operation_name,
            execution_time_ms=elapsed_ms,
        )

        self.metrics[operation_name].append(metrics)
        self.operation_times[operation_name].append(elapsed_ms)

        return result, metrics

    def get_operation_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        times = self.operation_times.get(operation_name, [])
        if not times:
            return {}

        return {
            "count": len(times),
            "total_ms": sum(times),
            "avg_ms": sum(times) / len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "median_ms": sorted(times)[len(times) // 2],
        }

    def get_slowest_operations(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get slowest operations."""
        avg_times = [
            (op, sum(times) / len(times) if times else 0)
            for op, times in self.operation_times.items()
        ]
        return sorted(avg_times, key=lambda x: x[1], reverse=True)[:limit]

    def generate_performance_report(self) -> str:
        """Generate performance report."""
        report = "PERFORMANCE PROFILING REPORT\n"
        report += "=" * 60 + "\n\n"

        total_time = sum(sum(times) for times in self.operation_times.values())
        report += f"Total Execution Time: {total_time:.2f}ms\n\n"

        report += "Slowest Operations:\n"
        report += "-" * 60 + "\n"

        slowest = self.get_slowest_operations(10)
        for op_name, avg_time in slowest:
            stats = self.get_operation_stats(op_name)
            report += f"\n{op_name}:\n"
            report += f"  Average: {avg_time:.2f}ms\n"
            report += f"  Count: {stats.get('count', 0)}\n"
            report += (
                f"  Min/Max: {stats.get('min_ms', 0):.2f}ms / {stats.get('max_ms', 0):.2f}ms\n"
            )

        return report


class OptimizationEngine:
    """Main optimization orchestration engine."""

    def __init__(self):
        """Initialize optimization engine."""
        self.query_optimizer = QueryOptimizer()
        self.search_optimizer = SearchOptimizer()
        self.batch_optimizer = BatchOptimizer()
        self.profiler = PerformanceProfiler()
        self.optimization_level = OptimizationLevel.BASIC

    def optimize_search_pipeline(
        self,
        query_text: str,
        execute_search_func: Callable,
        process_results_func: Callable,
        optimization_level: OptimizationLevel = OptimizationLevel.BASIC,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Optimize entire search pipeline."""
        self.optimization_level = optimization_level

        # Step 1: Optimize query
        optimized_query = self.query_optimizer.optimize_query(query_text, optimization_level)
        query_cost = self.query_optimizer.predict_query_cost(optimized_query)

        # Step 2: Execute search
        results, exec_metrics = self.profiler.profile_operation(
            "search_execution", execute_search_func, optimized_query
        )

        # Step 3: Optimize results
        optimized_results = self.search_optimizer.optimize_result_processing(
            results, optimization_level
        )

        # Step 4: Process results
        final_results, process_metrics = self.profiler.profile_operation(
            "result_processing", process_results_func, optimized_results
        )

        optimization_info = {
            "original_query": query_text,
            "optimized_query": optimized_query,
            "query_cost_estimate": query_cost,
            "result_quality": self.search_optimizer.estimate_result_quality(optimized_results),
            "deduplication_ratio": len(results) / max(len(optimized_results), 1),
            "execution_metrics": {
                "search_ms": exec_metrics.execution_time_ms,
                "processing_ms": process_metrics.execution_time_ms,
                "total_ms": exec_metrics.execution_time_ms + process_metrics.execution_time_ms,
            },
        }

        return final_results, optimization_info

    def set_optimization_level(self, level: OptimizationLevel) -> None:
        """Set global optimization level."""
        self.optimization_level = level

    def get_performance_insights(self) -> Dict[str, Any]:
        """Get performance insights and recommendations."""
        slowest = self.profiler.get_slowest_operations(5)

        return {
            "optimization_level": self.optimization_level.name,
            "slowest_operations": slowest,
            "total_operations": len(self.profiler.metrics),
            "recommendation": self._generate_recommendation(slowest),
        }

    def _generate_recommendation(self, slowest_ops: List[Tuple[str, float]]) -> str:
        """Generate optimization recommendations."""
        if not slowest_ops:
            return "System performing well. No immediate optimization needed."

        slowest_op = slowest_ops[0][0]
        slowest_time = slowest_ops[0][1]

        if slowest_time > 1000:
            return f"Critical: {slowest_op} is taking {slowest_time:.0f}ms. Consider increasing cache or using batch optimization."
        elif slowest_time > 500:
            return (
                f"Warning: {slowest_op} is taking {slowest_time:.0f}ms. Consider caching results."
            )
        else:
            return "Performance is acceptable. Consider profiling specific operations for micro-optimizations."
