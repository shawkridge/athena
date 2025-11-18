"""Unit tests for Phase 5 - Advanced features and optimizations."""

import pytest
from datetime import datetime
from athena.learning.cross_project_synthesis import CrossProjectSynthesis
from athena.learning.performance_profiler import PerformanceProfiler, PerformanceMetric
from athena.consolidation.advanced_strategies import AdvancedConsolidationStrategy


class MockDB:
    def __init__(self):
        self.data = {}

    def execute(self, sql, params=None):
        if "CREATE TABLE" in sql:
            return None
        if "INSERT" in sql and "RETURNING id" in sql:
            outcome_id = len(self.data) + 1
            if params:
                self.data[outcome_id] = {
                    "id": outcome_id,
                    "agent_name": params[0],
                    "decision": params[1],
                    "outcome": params[2],
                    "success_rate": params[3],
                    "execution_time_ms": params[4],
                    "context": params[5] if len(params) > 5 else {},
                    "session_id": params[6] if len(params) > 6 else None,
                    "timestamp": datetime.now(),
                }
            return [(outcome_id,)]
        if "SELECT AVG(success_rate)" in sql:
            agent_name = params[0] if params else None
            outcomes = [
                v for v in self.data.values() if not agent_name or v["agent_name"] == agent_name
            ]
            if outcomes:
                avg_rate = sum(o["success_rate"] for o in outcomes) / len(outcomes)
                return [[avg_rate, len(outcomes)]]
            return [[None, 0]]
        return None


@pytest.fixture
def mock_db():
    return MockDB()


@pytest.fixture
def cross_project_synthesis(mock_db):
    return CrossProjectSynthesis(mock_db)


@pytest.fixture
def performance_profiler(mock_db):
    return PerformanceProfiler(mock_db)


@pytest.fixture
def advanced_strategy(mock_db):
    return AdvancedConsolidationStrategy(mock_db)


@pytest.mark.asyncio
class TestCrossProjectSynthesis:
    """Tests for cross-project learning synthesis."""

    async def test_initialization(self, cross_project_synthesis):
        """Test synthesis initializes."""
        assert cross_project_synthesis is not None
        assert cross_project_synthesis.tracker is not None

    async def test_get_universal_practices(self, cross_project_synthesis, mock_db):
        """Test getting universal best practices."""
        tracker = cross_project_synthesis.tracker

        # Add outcomes
        await tracker.track_outcome(
            agent_name="code-analyzer",
            decision="deep_analysis",
            outcome="success",
            success_rate=0.95,
        )

        practices = cross_project_synthesis.get_universal_best_practices("code-analyzer")
        assert isinstance(practices, list)

    async def test_detect_trends(self, cross_project_synthesis):
        """Test trend detection."""
        trends = cross_project_synthesis.detect_emerging_trends()

        assert isinstance(trends, dict)
        assert "improving" in trends
        assert "declining" in trends
        assert "stable" in trends

    async def test_learning_velocity(self, cross_project_synthesis, mock_db):
        """Test learning velocity analysis."""
        tracker = cross_project_synthesis.tracker

        # Add some data
        for i in range(3):
            await tracker.track_outcome(
                agent_name="code-analyzer",
                decision=f"test_{i}",
                outcome="success",
                success_rate=0.8 + (i * 0.05),
            )

        velocity = cross_project_synthesis.learning_velocity_analysis()

        assert isinstance(velocity, dict)
        assert "agent_velocities" in velocity
        assert "system_velocity" in velocity

    async def test_get_cross_project_insights(self, cross_project_synthesis):
        """Test comprehensive cross-project insights."""
        insights = cross_project_synthesis.get_cross_project_insights()

        assert isinstance(insights, dict)
        assert "universal_practices" in insights
        assert "trends" in insights
        assert "recommendations" in insights


@pytest.mark.asyncio
class TestPerformanceProfiler:
    """Tests for performance profiling."""

    async def test_initialization(self, performance_profiler):
        """Test profiler initializes."""
        assert performance_profiler is not None
        assert len(performance_profiler._metrics_buffer) == 0

    async def test_record_execution(self, performance_profiler):
        """Test recording executions."""
        performance_profiler.record_execution(
            agent_name="code-analyzer", operation="analyze", execution_time_ms=300, memory_mb=50.0
        )

        assert len(performance_profiler._metrics_buffer) == 1
        metric = performance_profiler._metrics_buffer[0]
        assert metric.execution_time_ms == 300
        assert metric.memory_mb == 50.0

    async def test_record_slow_execution(self, performance_profiler, mock_db):
        """Test recording slow execution."""
        # Record something way over target
        performance_profiler.record_execution(
            agent_name="code-analyzer",
            operation="analyze",
            execution_time_ms=1500,  # Way over 500ms target
        )

        # Should be tracked as performance issue
        assert len(performance_profiler._metrics_buffer) == 1

    async def test_get_performance_stats(self, performance_profiler):
        """Test getting performance stats."""
        # Record some executions
        for i in range(3):
            performance_profiler.record_execution(
                agent_name="code-analyzer", operation="test", execution_time_ms=400 + (i * 50)
            )

        stats = performance_profiler.get_performance_stats("code-analyzer")

        assert stats["agent"] == "code-analyzer"
        assert stats["measurements"] == 3
        assert stats["avg_time_ms"] > 0

    async def test_calculate_trend(self, performance_profiler):
        """Test trend calculation."""
        metrics = [
            PerformanceMetric("test", "op", 500.0, datetime.now(), None),
            PerformanceMetric("test", "op", 450.0, datetime.now(), None),
            PerformanceMetric("test", "op", 400.0, datetime.now(), None),
        ]

        trend = performance_profiler._calculate_trend(metrics)
        assert trend in ["improving", "stable", "degrading"]

    async def test_get_slowest_operations(self, performance_profiler):
        """Test finding slowest operations."""
        performance_profiler.record_execution("test", "fast", 100)
        performance_profiler.record_execution("test", "slow", 800)
        performance_profiler.record_execution("test", "slow", 900)

        slowest = performance_profiler.get_slowest_operations("test")
        assert len(slowest) > 0
        assert slowest[0]["operation"] == "slow"

    async def test_recommend_optimizations(self, performance_profiler):
        """Test optimization recommendations."""
        # Record a slow operation
        for _ in range(5):
            performance_profiler.record_execution(
                agent_name="code-analyzer", operation="slow_op", execution_time_ms=1200
            )

        recs = performance_profiler.recommend_optimizations("code-analyzer")
        assert isinstance(recs, list)
        assert len(recs) > 0

    async def test_get_system_performance(self, performance_profiler):
        """Test system-wide performance."""
        # Record some executions for multiple agents
        performance_profiler.record_execution("code-analyzer", "test", 400)
        performance_profiler.record_execution("research-coordinator", "test", 900)

        system_perf = performance_profiler.get_system_performance()

        assert isinstance(system_perf, dict)
        assert "system_health_score" in system_perf
        assert "agents" in system_perf


@pytest.mark.asyncio
class TestAdvancedStrategies:
    """Tests for advanced consolidation strategies."""

    async def test_initialization(self, advanced_strategy):
        """Test strategy initializes."""
        assert advanced_strategy is not None

    async def test_extract_causal_patterns(self, advanced_strategy, mock_db):
        """Test causal pattern extraction."""
        tracker = advanced_strategy.tracker

        # Add a sequence of decisions
        for i in range(5):
            await tracker.track_outcome(
                agent_name="code-analyzer",
                decision=f"decision_{i}",
                outcome="success",
                success_rate=0.85,
            )

        patterns = advanced_strategy.extract_causal_patterns()
        assert isinstance(patterns, list)

    async def test_extract_hierarchical_patterns(self, advanced_strategy, mock_db):
        """Test hierarchical pattern extraction."""
        tracker = advanced_strategy.tracker

        # Add outcomes
        for i in range(10):
            await tracker.track_outcome(
                agent_name="code-analyzer",
                decision="test_decision",
                outcome="success",
                success_rate=0.85,
            )

        hierarchy = advanced_strategy.extract_hierarchical_patterns("code-analyzer")

        assert isinstance(hierarchy, dict)
        assert "micro_patterns" in hierarchy
        assert "meso_patterns" in hierarchy
        assert "macro_pattern" in hierarchy

    async def test_validate_pattern_confidence(self, advanced_strategy):
        """Test pattern validation."""
        pattern = {"occurrences": 5, "strength": 0.85, "consistency": 0.9}

        confidence = advanced_strategy.validate_pattern_confidence(pattern)

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be fairly confident

    async def test_synthesize_multi_agent(self, advanced_strategy, mock_db):
        """Test multi-agent pattern synthesis."""
        tracker = advanced_strategy.tracker

        # Add outcomes for multiple agents
        agents = ["code-analyzer", "research-coordinator"]
        for agent in agents:
            for i in range(5):
                await tracker.track_outcome(
                    agent_name=agent,
                    decision="universal_decision",
                    outcome="success",
                    success_rate=0.85,
                )

        synthesis = advanced_strategy.synthesize_multi_agent_patterns()

        assert isinstance(synthesis, dict)
        assert "universal_patterns" in synthesis

    async def test_extract_procedures(self, advanced_strategy, mock_db):
        """Test procedural knowledge extraction."""
        tracker = advanced_strategy.tracker

        # Add successful sequence
        for i in range(8):
            await tracker.track_outcome(
                agent_name="code-analyzer",
                decision=f"step_{i}",
                outcome="success",
                success_rate=0.9,
            )

        procedures = advanced_strategy.extract_procedural_knowledge("code-analyzer")

        assert isinstance(procedures, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
