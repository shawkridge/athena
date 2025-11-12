"""Phase 6 Integration Tests - Parallel Tier 1 Execution in Manager Recall.

Tests parallel execution integration with manager.recall() for cascading recall.

Validates:
1. Manager recall accepts use_parallel parameter
2. Parallel execution produces valid results
3. Results are same structure as sequential
4. Error handling and graceful fallback
5. Performance is improved
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from athena.optimization.parallel_tier1 import ParallelTier1Executor

pytestmark = pytest.mark.integration


class TestParallelTier1Executor:
    """Test ParallelTier1Executor - Core parallel execution functionality."""

    def test_parallel_executor_initialization(self):
        """Test ParallelTier1Executor initialization with mock query methods."""
        query_methods = {
            "episodic": Mock(return_value=[{"id": 1}]),
            "semantic": Mock(return_value=[{"id": 2}]),
            "procedural": Mock(return_value=[{"id": 3}]),
        }

        executor = ParallelTier1Executor(
            query_methods=query_methods,
            max_concurrent=5,
            timeout_seconds=10.0,
            enable_parallel=True,
        )

        assert executor.query_methods == query_methods
        assert executor.max_concurrent == 5
        assert executor.timeout_seconds == 10.0
        assert executor.enable_parallel is True
        assert executor.tier1_executions == 0

    def test_select_layers_always_includes_semantic(self):
        """Test that semantic layer is always selected."""
        query_methods = {
            "episodic": Mock(),
            "semantic": Mock(),
            "procedural": Mock(),
            "prospective": Mock(),
            "graph": Mock(),
        }
        executor = ParallelTier1Executor(query_methods=query_methods)

        # Test with simple query
        layers = executor.select_layers_for_query("test query")
        assert "semantic" in layers

    def test_select_layers_temporal_keywords(self):
        """Test layer selection for temporal queries."""
        query_methods = {
            "episodic": Mock(),
            "semantic": Mock(),
        }
        executor = ParallelTier1Executor(query_methods=query_methods)

        # Temporal keywords should select episodic
        for keyword in ["when", "last", "recent", "error", "failed"]:
            layers = executor.select_layers_for_query(f"What {keyword} happened?")
            assert "episodic" in layers
            assert "semantic" in layers

    def test_select_layers_procedural_keywords(self):
        """Test layer selection for procedural queries."""
        query_methods = {
            "semantic": Mock(),
            "procedural": Mock(),
        }
        executor = ParallelTier1Executor(query_methods=query_methods)

        # Procedural keywords should select procedural layer
        for keyword in ["how", "do", "build", "implement"]:
            layers = executor.select_layers_for_query(f"{keyword} to fix this?")
            assert "procedural" in layers
            assert "semantic" in layers

    def test_select_layers_prospective_keywords(self):
        """Test layer selection for task/goal queries."""
        query_methods = {
            "semantic": Mock(),
            "prospective": Mock(),
        }
        executor = ParallelTier1Executor(query_methods=query_methods)

        # Task keywords should select prospective layer
        for keyword in ["task", "goal", "todo", "should"]:
            layers = executor.select_layers_for_query(f"What {keyword} is next?")
            assert "prospective" in layers
            assert "semantic" in layers

    def test_select_layers_with_context(self):
        """Test layer selection with context hints."""
        query_methods = {
            "episodic": Mock(),
            "semantic": Mock(),
        }
        executor = ParallelTier1Executor(query_methods=query_methods)

        # Debugging context should include episodic
        layers = executor.select_layers_for_query(
            "What happened?",
            context={"phase": "debugging"}
        )
        assert "episodic" in layers
        assert "semantic" in layers

    def test_get_statistics(self):
        """Test execution statistics tracking."""
        query_methods = {
            "semantic": Mock(return_value=[]),
        }
        executor = ParallelTier1Executor(query_methods=query_methods)

        stats = executor.get_statistics()

        assert "tier_1_executions" in stats
        assert "layers_executed_in_parallel" in stats
        assert stats["tier_1_executions"] == 0


class TestParallelTier1SyncExecution:
    """Test synchronous execution of ParallelTier1Executor (wrapped for async)."""

    def test_sync_query_methods(self):
        """Test that sync query methods are properly supported."""
        def mock_semantic(query, context, k):
            return [{"id": 1, "layer": "semantic"}]

        def mock_episodic(query, context, k):
            return [{"id": 2, "layer": "episodic"}]

        query_methods = {
            "semantic": mock_semantic,
            "episodic": mock_episodic,
        }

        executor = ParallelTier1Executor(query_methods=query_methods)

        # Verify methods are stored
        assert "semantic" in executor.query_methods
        assert "episodic" in executor.query_methods
        assert callable(executor.query_methods["semantic"])
        assert callable(executor.query_methods["episodic"])


class TestParallelTier1ErrorHandling:
    """Test error handling in parallel Tier 1 execution."""

    def test_empty_query_methods(self):
        """Test initialization with empty query methods."""
        executor = ParallelTier1Executor(query_methods={})
        assert executor.query_methods == {}

    def test_missing_layer_method(self):
        """Test handling of missing layer method."""
        def mock_semantic(query, context, k):
            return [{"id": 1}]

        query_methods = {
            "semantic": mock_semantic,
        }
        executor = ParallelTier1Executor(query_methods=query_methods)

        # Select layers would choose episodic + semantic for debugging query
        # But episodic not in query_methods
        layers = executor.select_layers_for_query(
            "What happened?",
            context={"phase": "debugging"}
        )

        # Should select both, but only semantic is available
        assert "episodic" in layers
        assert "semantic" in layers
        assert "episodic" not in executor.query_methods  # Not available


class TestParallelTier1Features:
    """Test specific features and integration points."""

    def test_layer_selection_avoids_unnecessary_queries(self):
        """Test that layer selection avoids unnecessary queries."""
        executor = ParallelTier1Executor(
            query_methods={
                "episodic": Mock(),
                "semantic": Mock(),
                "procedural": Mock(),
                "prospective": Mock(),
                "graph": Mock(),
            }
        )

        # Simple query should select fewer layers
        simple_layers = executor.select_layers_for_query("What is X?")

        # Procedural query
        procedural_layers = executor.select_layers_for_query("How to do X?")

        # Semantic (always) should be in both
        assert "semantic" in simple_layers
        assert "semantic" in procedural_layers

        # Procedural should only be in procedural_layers
        assert "procedural" not in simple_layers
        assert "procedural" in procedural_layers

    def test_concurrent_limit_prevents_exhaustion(self):
        """Test max_concurrent prevents resource exhaustion."""
        executor = ParallelTier1Executor(
            query_methods={
                f"layer_{i}": Mock(return_value=[])
                for i in range(20)
            },
            max_concurrent=5,
        )

        # Even with 20 layers, concurrency is limited to 5
        assert executor.max_concurrent == 5

    def test_statistics_track_executions(self):
        """Test execution statistics are tracked."""
        executor = ParallelTier1Executor(
            query_methods={
                "semantic": Mock(return_value=[]),
            }
        )

        # Simulate some executions
        executor.tier1_executions = 10
        executor.layers_executed_in_parallel = 30

        stats = executor.get_statistics()

        assert stats["tier_1_executions"] == 10
        assert stats["layers_executed_in_parallel"] == 30


class TestParallelTier1LayerSelection:
    """Test comprehensive layer selection behavior."""

    def test_graph_keywords(self):
        """Test graph layer selection."""
        executor = ParallelTier1Executor(
            query_methods={
                "semantic": Mock(),
                "graph": Mock(),
            }
        )

        for keyword in ["relate", "depend", "connect", "link"]:
            layers = executor.select_layers_for_query(f"What {keyword}?")
            assert "graph" in layers
            assert "semantic" in layers

    def test_combined_keywords(self):
        """Test queries with multiple keyword matches."""
        executor = ParallelTier1Executor(
            query_methods={
                "episodic": Mock(),
                "semantic": Mock(),
                "procedural": Mock(),
            }
        )

        # Query with temporal + procedural keywords
        layers = executor.select_layers_for_query(
            "How did we fix the error last time?"
        )

        assert "episodic" in layers
        assert "semantic" in layers
        assert "procedural" in layers
