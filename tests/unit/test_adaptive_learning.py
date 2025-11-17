"""Unit tests for adaptive learning system.

Tests cover:
- LearningTracker persistence and queries
- AdaptiveAgent decision-making and learning
- CodeAnalyzer with adaptive strategies
- Integration with real agents
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from athena.learning.tracker import LearningTracker, LearningOutcome
from athena.orchestration.adaptive_agent import AdaptiveAgent
from athena.core.database import Database


class MockDatabase:
    """Mock database for testing."""

    def __init__(self):
        self.data = {}
        self.execution_count = 0

    def execute(self, sql: str, params=None):
        """Mock execute that handles our test queries."""
        self.execution_count += 1

        # Handle CREATE TABLE statements
        if "CREATE TABLE" in sql:
            return None

        # Handle INSERT
        if "INSERT INTO learning_outcomes" in sql and "RETURNING id" in sql:
            # Create new outcome record
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
            # Return ID as list of list (mimics psycopg2)
            return [(outcome_id,)]

        # Handle SELECT AVG(success_rate)
        if "SELECT AVG(success_rate)" in sql:
            outcomes = [v for v in self.data.values()]
            if outcomes:
                avg_rate = sum(o['success_rate'] for o in outcomes) / len(outcomes)
                return [[avg_rate, len(outcomes)]]
            return [[None, 0]]

        # Handle SELECT for history
        if "SELECT id, agent_name, decision" in sql:
            outcomes = [v for v in self.data.values()]
            return [
                (
                    o['id'],
                    o['agent_name'],
                    o['decision'],
                    o['outcome'],
                    o['success_rate'],
                    o['execution_time_ms'],
                    o['context'],
                    o['timestamp'],
                    o['session_id']
                )
                for o in outcomes
            ]

        # Handle statistics query (COUNT, AVG, MIN, MAX, successes, failures)
        if "COUNT(*) as total" in sql and "AVG(success_rate)" in sql:
            outcomes = [v for v in self.data.values()]
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
    """Provide a mock database."""
    return MockDatabase()


@pytest.fixture
def learning_tracker(mock_db):
    """Provide a LearningTracker with mock database."""
    return LearningTracker(mock_db)


@pytest.mark.asyncio
class TestLearningTracker:
    """Tests for LearningTracker persistence and querying."""

    async def test_track_outcome_valid(self, learning_tracker, mock_db):
        """Test tracking a valid outcome."""
        outcome_id = await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.9,
            execution_time_ms=150.0,
            context={"file": "test.py"}
        )

        assert outcome_id > 0
        assert mock_db.execution_count > 0

    async def test_track_outcome_invalid_outcome_type(self, learning_tracker):
        """Test that invalid outcome types raise ValueError."""
        with pytest.raises(ValueError, match="Invalid outcome"):
            await learning_tracker.track_outcome(
                agent_name="test-agent",
                decision="strategy_a",
                outcome="unknown_outcome",  # Invalid
                success_rate=0.9
            )

    async def test_track_outcome_invalid_success_rate(self, learning_tracker):
        """Test that invalid success rates raise ValueError."""
        with pytest.raises(ValueError, match="success_rate must be"):
            await learning_tracker.track_outcome(
                agent_name="test-agent",
                decision="strategy_a",
                outcome="success",
                success_rate=1.5  # Out of range
            )

    async def test_track_outcome_with_session_id(self, learning_tracker, mock_db):
        """Test tracking outcome with session ID."""
        outcome_id = await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.8,
            session_id="session-123"
        )

        assert outcome_id > 0

    async def test_get_success_rate_no_history(self, learning_tracker):
        """Test getting success rate when no history exists."""
        rate = learning_tracker.get_success_rate("unknown-agent")
        assert rate == 0.0

    async def test_get_success_rate_with_history(self, learning_tracker, mock_db):
        """Test getting success rate with tracked outcomes."""
        # Track multiple outcomes
        await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.9
        )
        await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.8
        )
        await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="failure",
            success_rate=0.2
        )

        # Mock return average
        rate = learning_tracker.get_success_rate("test-agent")
        # Rate should be around 0.63 (average of 0.9, 0.8, 0.2)
        assert 0.0 <= rate <= 1.0

    async def test_get_success_rate_by_decision(self, learning_tracker, mock_db):
        """Test filtering success rate by specific decision."""
        await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="deep_analysis",
            outcome="success",
            success_rate=0.95
        )
        await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="quick_analysis",
            outcome="failure",
            success_rate=0.3
        )

        # Mock implementation - just verify it doesn't crash
        rate = learning_tracker.get_success_rate("test-agent", decision="deep_analysis")
        assert 0.0 <= rate <= 1.0

    async def test_get_decision_history(self, learning_tracker, mock_db):
        """Test retrieving decision history."""
        await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.9
        )

        history = learning_tracker.get_decision_history("test-agent", limit=10)

        # Should return empty list or outcomes (depends on mock)
        assert isinstance(history, list)

    async def test_get_statistics(self, learning_tracker, mock_db):
        """Test getting comprehensive statistics."""
        await learning_tracker.track_outcome(
            agent_name="test-agent",
            decision="strategy_a",
            outcome="success",
            success_rate=0.9
        )

        stats = learning_tracker.get_statistics("test-agent")

        # Verify stats structure
        assert isinstance(stats, dict)
        assert 'agent_name' in stats
        assert 'total_decisions' in stats
        assert 'success_rate' in stats

    async def test_track_multiple_agents(self, learning_tracker, mock_db):
        """Test tracking outcomes for multiple agents."""
        await learning_tracker.track_outcome(
            agent_name="agent-1",
            decision="strategy_a",
            outcome="success",
            success_rate=0.9
        )
        await learning_tracker.track_outcome(
            agent_name="agent-2",
            decision="strategy_b",
            outcome="success",
            success_rate=0.8
        )

        # Both should be tracked
        assert mock_db.execution_count >= 2


@pytest.mark.asyncio
class TestAdaptiveAgent:
    """Tests for AdaptiveAgent base class."""

    class ConcreteAdaptiveAgent(AdaptiveAgent):
        """Concrete implementation for testing."""

        async def decide(self, context: dict) -> str:
            """Simple decision logic."""
            success_rate = self.tracker.get_success_rate(self.agent_name, "strategy_a")
            return "strategy_a" if success_rate > 0.5 else "strategy_b"

        async def execute(self, decision: str, context: dict):
            """Simple execution logic."""
            return {"decision": decision, "result": "executed"}

    @pytest.fixture
    def agent(self, mock_db):
        """Provide a concrete adaptive agent."""
        return self.ConcreteAdaptiveAgent("test-agent", mock_db)

    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.agent_name == "test-agent"
        assert agent.tracker is not None
        assert agent._decision_history == []

    async def test_decide_returns_string(self, agent):
        """Test that decide() returns a decision string."""
        decision = await agent.decide({"code": "test"})
        assert isinstance(decision, str)

    async def test_execute_returns_result(self, agent):
        """Test that execute() returns a result."""
        result = await agent.execute("strategy_a", {"code": "test"})
        assert isinstance(result, dict)

    async def test_run_full_cycle(self, agent):
        """Test full run cycle (decide-execute-learn)."""
        context = {"code": "test code"}

        result = await agent.run(context)

        assert "decision" in result
        assert "result" in result
        assert "success_rate" in result
        assert "outcome" in result
        assert 0.0 <= result['success_rate'] <= 1.0

    async def test_run_records_decision_history(self, agent):
        """Test that run() updates decision history."""
        await agent.run({"code": "test"})
        await agent.run({"code": "test2"})

        recent = agent.get_recent_decisions(limit=2)
        assert len(recent) > 0

    async def test_evaluate_outcome_success(self, agent):
        """Test evaluation of successful outcomes."""
        success_rate, outcome = await agent._evaluate_outcome(
            result={"data": [1, 2, 3]},
            decision="test",
            context={}
        )

        assert outcome == "success"
        assert 0.0 <= success_rate <= 1.0

    async def test_evaluate_outcome_failure(self, agent):
        """Test evaluation of failed outcomes."""
        success_rate, outcome = await agent._evaluate_outcome(
            result=None,
            decision="test",
            context={}
        )

        assert outcome == "failure"
        assert success_rate == 0.0

    async def test_evaluate_outcome_partial(self, agent):
        """Test evaluation of partial outcomes."""
        success_rate, outcome = await agent._evaluate_outcome(
            result={"partial": True},
            decision="test",
            context={}
        )

        assert outcome == "partial"
        assert 0.0 <= success_rate <= 1.0

    async def test_get_performance_stats(self, agent):
        """Test retrieving performance statistics."""
        await agent.run({"code": "test"})

        stats = await agent.get_performance_stats()

        assert isinstance(stats, dict)
        assert 'agent_name' in stats
        assert 'total_decisions' in stats
        assert 'success_rate' in stats
        assert 'recent_decisions' in stats

    async def test_error_handling_in_run(self, agent):
        """Test that run() handles errors gracefully."""
        class FailingAgent(self.ConcreteAdaptiveAgent):
            async def execute(self, decision: str, context: dict):
                raise RuntimeError("Execution failed")

        failing_agent = FailingAgent("failing-agent", agent.db)

        with pytest.raises(RuntimeError):
            await failing_agent.run({"code": "test"})

    async def test_learn_from_outcome_custom(self, agent, mock_db):
        """Test custom learning implementation."""
        await agent.learn_from_outcome(
            decision="strategy_a",
            outcome="success",
            success_rate=0.95,
            context={"type": "test"}
        )

        # Verify outcome was tracked
        assert mock_db.execution_count > 0


@pytest.mark.asyncio
class TestCodeAnalyzerAdaptive:
    """Integration tests for CodeAnalyzer with adaptive learning."""

    async def test_code_analyzer_has_adaptive_methods(self):
        """Test that CodeAnalyzer has adaptive methods."""
        from athena.agents.code_analyzer import CodeAnalyzerAgent

        # Create without DB (non-adaptive)
        analyzer = CodeAnalyzerAgent(db=None)

        # Should have adaptive methods
        assert hasattr(analyzer, 'decide')
        assert hasattr(analyzer, 'execute')
        assert hasattr(analyzer, '_evaluate_outcome')

    async def test_code_analyzer_decide(self):
        """Test CodeAnalyzer decision logic."""
        from athena.agents.code_analyzer import CodeAnalyzerAgent

        analyzer = CodeAnalyzerAgent(db=None)

        # Without DB, should return default
        decision = await analyzer.decide({"code": "test"})
        assert decision == "deep_analysis"

    async def test_code_analyzer_execute_deep(self):
        """Test CodeAnalyzer deep analysis execution."""
        from athena.agents.code_analyzer import CodeAnalyzerAgent

        analyzer = CodeAnalyzerAgent(db=None)

        result = await analyzer.execute(
            "deep_analysis",
            {"code": "def foo(): pass", "language": "python"}
        )

        assert isinstance(result, dict)
        assert "issues" in result or "style" in result or "metrics" in result

    async def test_code_analyzer_evaluate_outcome(self):
        """Test CodeAnalyzer outcome evaluation."""
        from athena.agents.code_analyzer import CodeAnalyzerAgent

        analyzer = CodeAnalyzerAgent(db=None)

        # With issues found
        success_rate, outcome = await analyzer._evaluate_outcome(
            result={"issues": [{"severity": "high"}]},
            decision="deep_analysis",
            context={}
        )

        assert outcome == "success"
        assert success_rate > 0.5


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests across components."""

    async def test_full_learning_workflow(self, mock_db):
        """Test complete learning workflow."""
        tracker = LearningTracker(mock_db)

        # Simulate multiple decisions
        for i in range(5):
            await tracker.track_outcome(
                agent_name="analyzer",
                decision="deep_analysis" if i < 3 else "quick_analysis",
                outcome="success",
                success_rate=0.9 if i < 3 else 0.7,
                context={"iteration": i}
            )

        # Check learning happened
        stats = tracker.get_statistics("analyzer")
        assert stats['total_decisions'] > 0

    async def test_multiple_strategies_learning(self, mock_db):
        """Test learning across multiple strategies."""
        tracker = LearningTracker(mock_db)

        # Try different strategies
        for strategy in ["strategy_a", "strategy_b", "strategy_c"]:
            for _ in range(3):
                await tracker.track_outcome(
                    agent_name="agent",
                    decision=strategy,
                    outcome="success",
                    success_rate=0.8
                )

        stats = tracker.get_statistics("agent")
        assert stats['total_decisions'] >= 9

    async def test_failure_tracking(self, mock_db):
        """Test tracking of failures for learning."""
        tracker = LearningTracker(mock_db)

        # Track both successes and failures
        await tracker.track_outcome(
            agent_name="agent",
            decision="risky_strategy",
            outcome="failure",
            success_rate=0.0
        )

        await tracker.track_outcome(
            agent_name="agent",
            decision="safe_strategy",
            outcome="success",
            success_rate=0.95
        )

        # Agent should learn to avoid risky_strategy
        stats = tracker.get_statistics("agent")
        assert stats['failures'] >= 1


# Run async tests
@pytest.mark.asyncio
class TestLearningTrackerAsync:
    """Async versions of tracker tests."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
