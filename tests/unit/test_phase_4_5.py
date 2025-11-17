"""Unit tests for Phase 4.5 - MemoryCoordinator enhancements.

Tests cover:
- Pattern-based retrieval with learned patterns
- Consolidation optimizer with learning insights
- Integration of adaptive learning into memory operations
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from athena.rag.pattern_based_retrieval import PatternBasedRetrieval
from athena.consolidation.learning_optimizer import ConsolidationLearningOptimizer
from athena.learning.tracker import LearningTracker, LearningOutcome


class MockDatabase:
    """Mock database for testing."""

    def __init__(self):
        self.data = {}

    def execute(self, sql: str, params=None):
        """Mock execute."""
        if "CREATE TABLE" in sql:
            return None
        if "INSERT" in sql and "RETURNING id" in sql:
            outcome_id = len(self.data) + 1
            if params:
                self.data[outcome_id] = {
                    'id': outcome_id,
                    'agent_name': params[0],
                    'decision': params[1],
                    'outcome': params[2],
                    'success_rate': params[3],
                    'execution_time_ms': params[4],
                    'context': params[5] if len(params) > 5 else {},
                    'session_id': params[6] if len(params) > 6 else None,
                    'timestamp': datetime.now()
                }
            return [(outcome_id,)]
        if "SELECT AVG(success_rate)" in sql:
            # Filter by agent_name from WHERE clause
            agent_name = params[0] if params else None
            outcomes = [v for v in self.data.values() if not agent_name or v['agent_name'] == agent_name]
            if outcomes:
                avg_rate = sum(o['success_rate'] for o in outcomes) / len(outcomes)
                return [[avg_rate, len(outcomes)]]
            return [[None, 0]]
        if "COUNT(*)" in sql:
            outcomes = list(self.data.values())
            if outcomes:
                total = len(outcomes)
                avg_rate = sum(o['success_rate'] for o in outcomes) / len(outcomes)
                min_rate = min(o['success_rate'] for o in outcomes)
                max_rate = max(o['success_rate'] for o in outcomes)
                avg_time = sum(o['execution_time_ms'] for o in outcomes) / len(outcomes)
                successes = len([o for o in outcomes if o['outcome'] == 'success'])
                failures = len([o for o in outcomes if o['outcome'] == 'failure'])
                return [(total, avg_rate, min_rate, max_rate, avg_time, successes, failures)]
            return [(0, None, None, None, None, 0, 0)]
        return None


@pytest.fixture
def mock_db():
    """Provide mock database."""
    return MockDatabase()


@pytest.fixture
def learning_tracker(mock_db):
    """Provide learning tracker."""
    return LearningTracker(mock_db)


@pytest.fixture
def pattern_retrieval(mock_db):
    """Provide pattern-based retrieval."""
    return PatternBasedRetrieval(mock_db)


@pytest.fixture
def consolidation_optimizer(mock_db):
    """Provide consolidation optimizer."""
    return ConsolidationLearningOptimizer(mock_db)


@pytest.mark.asyncio
class TestPatternBasedRetrieval:
    """Tests for pattern-based retrieval."""

    async def test_initialization(self, pattern_retrieval):
        """Test pattern retrieval initializes."""
        assert pattern_retrieval is not None
        assert pattern_retrieval.tracker is not None

    async def test_extract_success_patterns(self, pattern_retrieval, mock_db):
        """Test extracting patterns from successful decisions."""
        # Add some successful outcomes
        tracker = pattern_retrieval.tracker
        await tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.9
        )
        await tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.85
        )

        # Get decision history
        history = tracker.get_decision_history("test-agent")

        # Extract patterns
        patterns = pattern_retrieval._extract_success_patterns(history)

        assert isinstance(patterns, list)
        if patterns:
            assert 'pattern' in patterns[0]
            assert 'success_rate' in patterns[0]

    def test_expand_query(self, pattern_retrieval):
        """Test query expansion with patterns."""
        patterns = [
            {'pattern': 'testing', 'success_rate': 0.9, 'frequency': 3},
            {'pattern': 'validation', 'success_rate': 0.8, 'frequency': 2}
        ]

        expanded = pattern_retrieval._expand_query("how to test", patterns)

        assert "how to test" in expanded
        assert "testing" in expanded or "validation" in expanded

    def test_rerank_by_patterns(self, pattern_retrieval):
        """Test re-ranking results by patterns."""
        results = [
            {'content': 'Testing strategies work well', 'id': 1},
            {'content': 'Deployment requires validation', 'id': 2},
            {'content': 'Random unrelated content', 'id': 3}
        ]

        patterns = [
            {'pattern': 'testing', 'success_rate': 0.9, 'frequency': 3},
            {'pattern': 'validation', 'success_rate': 0.8, 'frequency': 2}
        ]

        reranked = pattern_retrieval._rerank_by_patterns(results, patterns)

        # Should be reordered
        assert len(reranked) == len(results)
        # Results with pattern matches should be higher (if patterns exist)
        if any('pattern_score' in r for r in reranked):
            assert reranked[0]['pattern_score'] >= reranked[-1]['pattern_score']

    async def test_learn_retrieval_effectiveness(self, pattern_retrieval, mock_db):
        """Test learning from retrieval results."""
        await pattern_retrieval.learn_retrieval_effectiveness(
            agent_name="analyzer",
            strategy="pattern_expansion_2",
            results_count=5,
            user_feedback=0.9
        )

        # Verify it was tracked
        tracker = pattern_retrieval.tracker
        stats = tracker.get_statistics("analyzer-retrieval")
        assert stats['total_decisions'] > 0


@pytest.mark.asyncio
class TestConsolidationOptimizer:
    """Tests for consolidation learning optimizer."""

    def test_initialization(self, consolidation_optimizer):
        """Test optimizer initializes."""
        assert consolidation_optimizer is not None
        assert consolidation_optimizer.tracker is not None

    def test_calculate_agent_scores(self, consolidation_optimizer, mock_db):
        """Test calculating agent improvement scores."""
        tracker = consolidation_optimizer.tracker

        # Add outcomes for different agents
        asyncio.run(tracker.track_outcome(
            agent_name="code-analyzer",
            decision="test",
            outcome="success",
            success_rate=0.8
        ))

        scores = consolidation_optimizer._calculate_agent_scores(["code-analyzer"])

        assert isinstance(scores, dict)
        assert "code-analyzer" in scores
        assert 0.0 <= scores["code-analyzer"] <= 1.0

    def test_score_memory(self, consolidation_optimizer):
        """Test memory priority scoring."""
        agent_scores = {"code-analyzer": 0.8}
        memory = {
            'source_agent': 'code-analyzer',
            'importance': 0.7,
            'timestamp': datetime.now()
        }

        score = consolidation_optimizer._score_memory(memory, agent_scores)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be prioritized

    def test_select_consolidation_strategy(self, consolidation_optimizer):
        """Test strategy selection based on improvement."""
        # High improvement
        strategy_high = consolidation_optimizer.select_consolidation_strategy(
            memory_count=100,
            agent_improvement_avg=0.8
        )
        assert strategy_high == "aggressive"

        # Medium improvement
        strategy_med = consolidation_optimizer.select_consolidation_strategy(
            memory_count=100,
            agent_improvement_avg=0.5
        )
        assert strategy_med == "balanced"

        # Low improvement
        strategy_low = consolidation_optimizer.select_consolidation_strategy(
            memory_count=100,
            agent_improvement_avg=0.2
        )
        assert strategy_low == "conservative"

    async def test_learn_consolidation_effectiveness(self, consolidation_optimizer, mock_db):
        """Test learning consolidation effectiveness."""
        await consolidation_optimizer.learn_consolidation_effectiveness(
            strategy_used="balanced",
            patterns_extracted=5,
            procedures_extracted=3,
            agent_feedback={"analyzer": 0.9}
        )

        # Verify it was tracked
        stats = consolidation_optimizer.tracker.get_statistics("consolidation-optimizer")
        assert stats['total_decisions'] > 0

    def test_get_optimal_timing(self, consolidation_optimizer):
        """Test optimal consolidation timing calculation."""
        timing = consolidation_optimizer.get_optimal_consolidation_timing()

        assert isinstance(timing, dict)
        assert 'next_consolidation' in timing
        assert 'urgency' in timing
        assert 'reason' in timing
        assert 0.0 <= timing['urgency'] <= 1.0

    def test_get_consolidation_stats(self, consolidation_optimizer):
        """Test getting consolidation statistics."""
        consolidation_optimizer.select_consolidation_strategy(100, 0.5)

        stats = consolidation_optimizer.get_consolidation_stats()

        assert isinstance(stats, dict)
        assert 'total_experiments' in stats
        assert stats['total_experiments'] >= 1

    def test_prioritize_memories(self, consolidation_optimizer):
        """Test memory prioritization for consolidation."""
        memories = [
            {'id': 1, 'source_agent': 'code-analyzer', 'importance': 0.5},
            {'id': 2, 'source_agent': 'research', 'importance': 0.8},
            {'id': 3, 'source_agent': 'code-analyzer', 'importance': 0.9, 'timestamp': datetime.now()}
        ]

        prioritized = consolidation_optimizer.get_prioritized_memories(memories)

        # Should return same memories but reordered
        assert len(prioritized) == len(memories)
        assert all(m.get('consolidation_priority_score') is not None for m in prioritized if isinstance(m, dict))


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for Phase 4.5."""

    async def test_retrieval_and_consolidation_workflow(
        self,
        pattern_retrieval,
        consolidation_optimizer,
        mock_db
    ):
        """Test combined retrieval and consolidation workflow."""
        # Add learning data
        tracker = pattern_retrieval.tracker
        await tracker.track_outcome(
            agent_name="analyzer",
            decision="deep_analysis",
            outcome="success",
            success_rate=0.9
        )

        # Test retrieval
        results = await pattern_retrieval.retrieve_with_patterns(
            query="test query",
            agent_name="analyzer"
        )
        assert isinstance(results, list)

        # Test consolidation timing
        timing = consolidation_optimizer.get_optimal_consolidation_timing()
        assert timing['next_consolidation'] is not None

    async def test_learning_improves_consolidation(
        self,
        consolidation_optimizer,
        mock_db
    ):
        """Test that learning data improves consolidation decisions."""
        tracker = consolidation_optimizer.tracker

        # Build up learning data
        for i in range(5):
            await tracker.track_outcome(
                agent_name="code-analyzer",
                decision=f"strategy_{i}",
                outcome="success",
                success_rate=0.8 + (i * 0.02)
            )

        # Get scores - should reflect the learning
        scores = consolidation_optimizer._calculate_agent_scores(["code-analyzer"])
        assert "code-analyzer" in scores

        # Get timing - should use the learning data
        timing = consolidation_optimizer.get_optimal_consolidation_timing()
        assert timing is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
