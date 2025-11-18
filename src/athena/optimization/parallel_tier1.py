"""Parallel Tier 1 Executor - Concurrent execution of layer queries for recall.

Integrates with manager.recall() to execute Tier 1 queries (episodic, semantic,
procedural, prospective, graph) in parallel for 3-4x speedup on multi-layer
recall operations.

Key features:
- Smart layer selection based on query keywords
- Async/await-based concurrent execution
- Graceful error isolation (one failure doesn't block others)
- Fallback to sequential if async unavailable
- Performance monitoring and statistics
- Seamless integration with existing recall pipeline
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .parallel_executor import ParallelLayerExecutor, QueryTask

logger = logging.getLogger(__name__)


class ParallelTier1Executor:
    """Orchestrates parallel Tier 1 execution for cascading recall.

    Intelligently selects which memory layers to query based on query keywords,
    then executes selected layers concurrently for optimal performance.

    Example:
        executor = ParallelTier1Executor(
            query_methods={
                "episodic": manager._query_episodic,
                "semantic": manager._query_semantic,
                "procedural": manager._query_procedural,
                "prospective": manager._query_prospective,
                "graph": manager._query_graph,
            }
        )

        results = await executor.execute_tier_1_parallel(
            query="What was the failing test?",
            context={"phase": "debugging"},
            k=5
        )
    """

    # Layer selection keywords
    LAYER_KEYWORDS = {
        "episodic": ["when", "last", "recent", "error", "failed", "happened"],
        "semantic": ["what", "is", "define", "explain", "know", "fact"],
        "procedural": ["how", "do", "build", "implement", "create", "make"],
        "prospective": ["task", "goal", "todo", "should", "remind", "schedule"],
        "graph": ["relate", "depend", "connect", "link", "relationship", "association"],
    }

    def __init__(
        self,
        query_methods: Dict[str, Callable],
        max_concurrent: int = 5,
        timeout_seconds: float = 10.0,
        enable_parallel: bool = True,
    ):
        """Initialize parallel Tier 1 executor.

        Args:
            query_methods: Dictionary of layer_name -> query function.
                          Functions should be sync and will be wrapped for async.
            max_concurrent: Max concurrent tasks (default 5)
            timeout_seconds: Timeout per layer query (default 10s)
            enable_parallel: Enable parallel execution (default True)
        """
        self.query_methods = query_methods
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds
        self.enable_parallel = enable_parallel

        # Initialize underlying parallel executor
        self.executor = ParallelLayerExecutor(
            max_concurrent=max_concurrent,
            timeout_seconds=timeout_seconds,
            enable_parallel=enable_parallel,
        )

        # Statistics
        self.tier1_executions = 0
        self.layers_executed_in_parallel = 0

    def select_layers_for_query(self, query: str, context: Optional[Dict] = None) -> List[str]:
        """Select which layers to query based on keywords and context.

        Smart selection avoids unnecessary queries and improves performance.

        Args:
            query: The search query
            context: Optional context (phase, recent_events, etc.)

        Returns:
            List of layer names to query (always includes "semantic")
        """
        context = context or {}
        query_lower = query.lower()
        selected_layers = set()

        # Semantic is always queried (factual baseline)
        selected_layers.add("semantic")

        # Episodic: temporal, debugging, error-related queries
        if context.get("phase") == "debugging" or any(
            word in query_lower for word in self.LAYER_KEYWORDS["episodic"]
        ):
            selected_layers.add("episodic")

        # Procedural: how-to, workflow, implementation queries
        if any(word in query_lower for word in self.LAYER_KEYWORDS["procedural"]):
            selected_layers.add("procedural")

        # Prospective: task, goal, reminder queries
        if any(word in query_lower for word in self.LAYER_KEYWORDS["prospective"]):
            selected_layers.add("prospective")

        # Graph: relationship, dependency queries
        if any(word in query_lower for word in self.LAYER_KEYWORDS["graph"]):
            selected_layers.add("graph")

        return sorted(selected_layers)

    def _wrap_sync_method_for_async(self, sync_fn: Callable, args: tuple, kwargs: dict) -> Callable:
        """Wrap a synchronous method for async execution.

        Args:
            sync_fn: The synchronous function
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Async function that calls the sync function
        """

        async def async_wrapper() -> Any:
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: sync_fn(*args, **kwargs))

        return async_wrapper

    async def execute_tier_1_parallel(
        self,
        query: str,
        context: Optional[Dict] = None,
        k: int = 5,
        use_parallel: bool = True,
    ) -> Dict[str, Any]:
        """Execute Tier 1 queries in parallel.

        Args:
            query: Search query
            context: Optional context (phase, session, etc.)
            k: Number of results per layer
            use_parallel: If False, falls back to sequential execution

        Returns:
            Dictionary with results from each selected layer
        """
        self.tier1_executions += 1
        context = context or {}

        # Select layers based on query and context
        selected_layers = self.select_layers_for_query(query, context)

        if not use_parallel or len(selected_layers) <= 1:
            # Fall back to sequential execution
            return await self._execute_sequential(query, context, k, selected_layers)

        # Build tasks for parallel execution
        tasks: List[QueryTask] = []

        for layer in selected_layers:
            if layer not in self.query_methods:
                logger.warning(f"Query method for layer '{layer}' not found")
                continue

            query_fn = self.query_methods[layer]

            # Create async wrapper for sync function
            async_fn = self._wrap_sync_method_for_async(query_fn, (query, context, k), {})

            # Create task
            task = QueryTask(
                layer_name=layer,
                query_fn=async_fn,
                args=(),
                kwargs={},
                timeout_seconds=self.timeout_seconds,
            )
            tasks.append(task)

        # Execute all tasks in parallel
        results_dict = await self.executor.execute_parallel(tasks)

        # Convert ExecutionResult objects to layer results
        tier_1_results = {}
        self.layers_executed_in_parallel += len(selected_layers)

        for layer_name, exec_result in results_dict.items():
            if exec_result.success and exec_result.result is not None:
                tier_1_results[layer_name] = exec_result.result
            else:
                logger.warning(f"Layer '{layer_name}' failed: {exec_result.error}")
                # Store error for debugging but don't fail entire recall
                tier_1_results[layer_name] = []

        return tier_1_results

    async def _execute_sequential(
        self,
        query: str,
        context: Dict,
        k: int,
        layers: List[str],
    ) -> Dict[str, Any]:
        """Execute Tier 1 queries sequentially (fallback).

        Args:
            query: Search query
            context: Query context
            k: Number of results per layer
            layers: Layers to query

        Returns:
            Dictionary with results from each layer
        """
        tier_1_results = {}

        for layer in layers:
            if layer not in self.query_methods:
                logger.warning(f"Query method for layer '{layer}' not found")
                continue

            try:
                query_fn = self.query_methods[layer]
                loop = asyncio.get_event_loop()

                # Execute sync function in thread pool
                result = await loop.run_in_executor(None, lambda fn=query_fn: fn(query, context, k))
                tier_1_results[layer] = result
            except Exception as e:
                logger.error(f"Error querying layer '{layer}': {e}")
                tier_1_results[layer] = []

        return tier_1_results

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics.

        Returns:
            Dictionary with execution metrics
        """
        stats = {
            "tier_1_executions": self.tier1_executions,
            "layers_executed_in_parallel": self.layers_executed_in_parallel,
        }

        # Include underlying executor stats
        if self.executor:
            stats.update(
                {
                    "total_parallel_queries": self.executor.total_parallel_queries,
                    "total_sequential_queries": self.executor.total_sequential_queries,
                    "failed_tasks": self.executor.failed_tasks,
                }
            )

        return stats
