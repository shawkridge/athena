"""Unit tests for ReAct Loop implementation

Tests for:
- Thought-Action tracking
- Observation memory
- ReAct loop execution
- Integration between components
"""

import asyncio
import pytest
from datetime import datetime

from athena.agents.thought_action import (
    Action,
    ActionType,
    Observation,
    ObservationType,
    Thought,
    ThoughtActionHistory,
    ThoughtType,
)
from athena.agents.observation_memory import ObservationMemory, IndexedObservation
from athena.agents.react_loop import (
    LoopConfig,
    LoopMetrics,
    LoopResult,
    LoopStatus,
    ReActLoop,
)


# ============================================================================
# Thought-Action History Tests
# ============================================================================


class TestThoughtActionHistory:
    """Test ThoughtActionHistory class"""

    def test_init(self):
        """Test history initialization"""
        history = ThoughtActionHistory(max_history_size=100)
        assert history.max_size == 100
        assert len(history.thoughts) == 0
        assert len(history.actions) == 0
        assert len(history.observations) == 0

    def test_add_thought(self):
        """Test adding a thought"""
        history = ThoughtActionHistory()
        thought = history.add_thought(
            content="Test thought",
            thought_type=ThoughtType.PROBLEM_ANALYSIS,
            reasoning="This is my reasoning",
            confidence=0.8,
        )

        assert thought.content == "Test thought"
        assert thought.thought_type == ThoughtType.PROBLEM_ANALYSIS
        assert thought.confidence == 0.8
        assert len(history.thoughts) == 1
        assert history.thoughts[0] == thought

    def test_add_action(self):
        """Test adding an action"""
        history = ThoughtActionHistory()
        thought = history.add_thought(content="Initial thought")

        action = history.add_action(
            content="Execute query",
            action_type=ActionType.QUERY,
            tool="search",
            parameters={"query": "test"},
            thought_id=thought.id,
        )

        assert action.content == "Execute query"
        assert action.action_type == ActionType.QUERY
        assert action.tool == "search"
        assert len(history.actions) == 1

    def test_add_observation(self):
        """Test adding an observation"""
        history = ThoughtActionHistory()
        action = history.add_action(content="Execute action")

        observation = history.add_observation(
            content="Result of action",
            action_id=action.id,
            observation_type=ObservationType.SUCCESS,
            relevance_score=0.9,
        )

        assert observation.content == "Result of action"
        assert observation.observation_type == ObservationType.SUCCESS
        assert observation.relevance_score == 0.9
        assert len(history.observations) == 1

    def test_update_action_execution(self):
        """Test updating action execution results"""
        history = ThoughtActionHistory()
        action = history.add_action(content="Execute query")

        success = history.update_action_execution(
            action_id=action.id,
            execution_time_ms=150.5,
            success=True,
            error=None,
        )

        assert success
        assert history.actions[0].execution_time_ms == 150.5
        assert history.actions[0].success is True

    def test_get_latest_thought(self):
        """Test getting latest thought"""
        history = ThoughtActionHistory()
        thought1 = history.add_thought(content="First thought")
        thought2 = history.add_thought(content="Second thought")

        latest = history.get_latest_thought()
        assert latest == thought2

    def test_get_latest_action(self):
        """Test getting latest action"""
        history = ThoughtActionHistory()
        action1 = history.add_action(content="First action")
        action2 = history.add_action(content="Second action")

        latest = history.get_latest_action()
        assert latest == action2

    def test_get_latest_observation(self):
        """Test getting latest observation"""
        history = ThoughtActionHistory()
        obs1 = history.add_observation(content="First observation", action_id="1")
        obs2 = history.add_observation(content="Second observation", action_id="2")

        latest = history.get_latest_observation()
        assert latest == obs2

    def test_thought_chain(self):
        """Test getting thought chain"""
        history = ThoughtActionHistory()
        thought1 = history.add_thought(content="Root thought")
        thought2 = history.add_thought(
            content="Child thought", parent_thought_id=thought1.id
        )
        thought3 = history.add_thought(
            content="Grandchild thought", parent_thought_id=thought2.id
        )

        chain = history.get_thought_chain(start_thought_id=thought3.id)

        assert len(chain) == 3
        assert chain[0] == thought1
        assert chain[1] == thought2
        assert chain[2] == thought3

    def test_get_action_for_thought(self):
        """Test getting action for a thought"""
        history = ThoughtActionHistory()
        thought = history.add_thought(content="Think")
        action = history.add_action(content="Act", thought_id=thought.id)

        found_action = history.get_action_for_thought(thought.id)
        assert found_action == action

    def test_get_observation_for_action(self):
        """Test getting observation for an action"""
        history = ThoughtActionHistory()
        action = history.add_action(content="Execute")
        observation = history.add_observation(
            content="Result", action_id=action.id
        )

        found_obs = history.get_observation_for_action(action.id)
        assert found_obs == observation

    def test_get_loop_iteration(self):
        """Test getting complete loop iteration"""
        history = ThoughtActionHistory()
        thought = history.add_thought(content="Think")
        action = history.add_action(content="Act", thought_id=thought.id)
        observation = history.add_observation(
            content="Observe", action_id=action.id
        )

        iteration = history.get_loop_iteration(0)

        assert iteration["iteration"] == 0
        assert iteration["thought"]["id"] == thought.id
        assert iteration["action"]["id"] == action.id
        assert iteration["observation"]["id"] == observation.id

    def test_get_full_history(self):
        """Test getting full history"""
        history = ThoughtActionHistory()
        thought = history.add_thought(content="Think")
        action = history.add_action(content="Act", thought_id=thought.id)
        observation = history.add_observation(
            content="Observe", action_id=action.id
        )

        full = history.get_full_history()

        assert len(full["thoughts"]) == 1
        assert len(full["actions"]) == 1
        assert len(full["observations"]) == 1
        assert full["stats"]["total_thoughts"] == 1
        assert full["stats"]["successful_actions"] == 0

    def test_clear_history(self):
        """Test clearing history"""
        history = ThoughtActionHistory()
        history.add_thought(content="Think")
        history.add_action(content="Act")
        history.add_observation(content="Observe", action_id="1")

        history.clear_history()

        assert len(history.thoughts) == 0
        assert len(history.actions) == 0
        assert len(history.observations) == 0

    def test_get_high_confidence_thoughts(self):
        """Test filtering high confidence thoughts"""
        history = ThoughtActionHistory()
        low = history.add_thought(content="Low", confidence=0.3)
        mid = history.add_thought(content="Mid", confidence=0.6)
        high = history.add_thought(content="High", confidence=0.9)

        result = history.get_high_confidence_thoughts(threshold=0.7)

        assert len(result) == 1
        assert result[0] == high

    def test_get_failed_actions(self):
        """Test getting failed actions"""
        history = ThoughtActionHistory()
        action1 = history.add_action(content="Action 1")
        action2 = history.add_action(content="Action 2")

        history.update_action_execution(action1.id, 100, success=True)
        history.update_action_execution(action2.id, 200, success=False)

        failed = history.get_failed_actions()

        assert len(failed) == 1
        assert failed[0].id == action2.id

    def test_max_history_size(self):
        """Test that history respects max size"""
        history = ThoughtActionHistory(max_history_size=5)

        for i in range(10):
            history.add_thought(content=f"Thought {i}")

        assert len(history.thoughts) == 5
        # Should keep the latest 5
        assert history.thoughts[0].content == "Thought 5"


# ============================================================================
# Observation Memory Tests
# ============================================================================


class TestObservationMemory:
    """Test ObservationMemory class"""

    def test_init(self):
        """Test memory initialization"""
        memory = ObservationMemory(max_observations=100)
        assert memory.max_size == 100
        assert len(memory.observations) == 0

    def test_add_observation(self):
        """Test adding an observation"""
        memory = ObservationMemory()
        obs = memory.add_observation(
            content="Test observation",
            action_type="query",
            result_type="success",
            success=True,
            relevance_score=0.8,
        )

        assert obs.content == "Test observation"
        assert obs.action_type == "query"
        assert obs.result_type == "success"
        assert len(memory.observations) == 1

    def test_get_by_action_type(self):
        """Test getting observations by action type"""
        memory = ObservationMemory()
        obs1 = memory.add_observation(
            content="Query 1", action_type="query", result_type="success"
        )
        obs2 = memory.add_observation(
            content="Retrieve 1", action_type="retrieve", result_type="success"
        )
        obs3 = memory.add_observation(
            content="Query 2", action_type="query", result_type="success"
        )

        queries = memory.get_by_action_type("query")

        assert len(queries) == 2
        assert obs1 in queries
        assert obs3 in queries
        assert obs2 not in queries

    def test_get_by_result_type(self):
        """Test getting observations by result type"""
        memory = ObservationMemory()
        obs1 = memory.add_observation(
            content="Success", action_type="query", result_type="success"
        )
        obs2 = memory.add_observation(
            content="Failure", action_type="query", result_type="failure"
        )

        successes = memory.get_by_result_type("success")
        failures = memory.get_by_result_type("failure")

        assert len(successes) == 1
        assert successes[0] == obs1
        assert len(failures) == 1
        assert failures[0] == obs2

    def test_get_successful_observations(self):
        """Test getting successful observations"""
        memory = ObservationMemory()
        obs1 = memory.add_observation(
            content="Success 1", action_type="query", result_type="success", success=True
        )
        obs2 = memory.add_observation(
            content="Failure 1", action_type="query", result_type="failure", success=False
        )
        obs3 = memory.add_observation(
            content="Success 2", action_type="query", result_type="success", success=True
        )

        successful = memory.get_successful_observations()

        assert len(successful) == 2
        assert obs1 in successful
        assert obs3 in successful

    def test_get_failed_observations(self):
        """Test getting failed observations"""
        memory = ObservationMemory()
        obs1 = memory.add_observation(
            content="Success", action_type="query", result_type="success", success=True
        )
        obs2 = memory.add_observation(
            content="Failure", action_type="query", result_type="failure", success=False
        )

        failed = memory.get_failed_observations()

        assert len(failed) == 1
        assert failed[0] == obs2

    def test_get_by_date_range(self):
        """Test getting observations by date range"""
        memory = ObservationMemory()
        # All observations will have today's date
        obs1 = memory.add_observation(
            content="Obs 1", action_type="query", result_type="success"
        )
        obs2 = memory.add_observation(
            content="Obs 2", action_type="query", result_type="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = "2025-11-06"
        tomorrow = "2025-11-08"

        # Should find observations in today's date
        result = memory.get_by_date_range(yesterday, tomorrow)
        assert len(result) >= 2

    def test_get_high_relevance_observations(self):
        """Test getting high relevance observations"""
        memory = ObservationMemory()
        obs1 = memory.add_observation(
            content="Low", action_type="query", result_type="success", relevance_score=0.3
        )
        obs2 = memory.add_observation(
            content="High", action_type="query", result_type="success", relevance_score=0.9
        )

        high_rel = memory.get_high_relevance_observations(threshold=0.7)

        assert len(high_rel) == 1
        assert high_rel[0] == obs2

    def test_get_surprising_observations(self):
        """Test getting observations with surprises"""
        memory = ObservationMemory()
        obs1 = memory.add_observation(
            content="No surprise", action_type="query", result_type="success"
        )
        obs2 = memory.add_observation(
            content="With surprise",
            action_type="query",
            result_type="success",
            surprise_flags=["unexpected_result"],
        )

        surprising = memory.get_surprising_observations()

        assert len(surprising) == 1
        assert surprising[0] == obs2

    def test_get_similar_observations(self):
        """Test similarity search"""
        memory = ObservationMemory()
        obs1 = memory.add_observation(
            content="query the database for users",
            action_type="query",
            result_type="success",
        )
        obs2 = memory.add_observation(
            content="retrieve records from table",
            action_type="retrieve",
            result_type="success",
        )
        obs3 = memory.add_observation(
            content="query for specific user information",
            action_type="query",
            result_type="success",
        )

        similar = memory.get_similar_observations(
            query_content="query for users", limit=2
        )

        assert len(similar) > 0
        # Most similar should be obs1 or obs3
        assert similar[0][0] in [obs1, obs3]

    def test_get_statistics(self):
        """Test getting statistics"""
        memory = ObservationMemory()
        memory.add_observation(
            content="Success 1", action_type="query", result_type="success", success=True
        )
        memory.add_observation(
            content="Failure 1", action_type="retrieve", result_type="failure", success=False
        )
        memory.add_observation(
            content="Success 2", action_type="query", result_type="success", success=True
        )

        stats = memory.get_statistics()

        assert stats["total_observations"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["success_rate"] > 0.6
        assert stats["unique_action_types"] == 2

    def test_get_lessons_learned(self):
        """Test getting lessons learned"""
        memory = ObservationMemory()
        memory.add_observation(
            content="Obs 1",
            action_type="query",
            result_type="success",
            lesson_learned="Query optimization matters",
        )
        memory.add_observation(
            content="Obs 2",
            action_type="retrieve",
            result_type="success",
            lesson_learned="Indexing helps performance",
        )

        lessons = memory.get_lessons_learned()

        assert len(lessons) == 2
        assert any("Query optimization" in lesson for _, lesson in lessons)

    def test_get_common_issues(self):
        """Test getting common failure issues"""
        memory = ObservationMemory()
        memory.add_observation(
            content="Failure 1",
            action_type="query",
            result_type="failure",
            success=False,
            lesson_learned="Timeout on large queries",
        )
        memory.add_observation(
            content="Failure 2",
            action_type="query",
            result_type="failure",
            success=False,
            lesson_learned="Timeout on large queries",
        )
        memory.add_observation(
            content="Failure 3",
            action_type="retrieve",
            result_type="failure",
            success=False,
            lesson_learned="Connection lost",
        )

        issues = memory.get_common_issues()

        # "Timeout on large queries" should be most common
        assert len(issues) >= 1
        assert issues[0] == "Timeout on large queries"

    def test_clear_memory(self):
        """Test clearing memory"""
        memory = ObservationMemory()
        memory.add_observation(
            content="Obs 1", action_type="query", result_type="success"
        )
        memory.add_observation(
            content="Obs 2", action_type="retrieve", result_type="success"
        )

        memory.clear_memory()

        assert len(memory.observations) == 0
        assert len(memory.by_action_type) == 0


# ============================================================================
# ReAct Loop Tests
# ============================================================================


class TestReActLoop:
    """Test ReActLoop class"""

    def test_init(self):
        """Test loop initialization"""
        config = LoopConfig(max_iterations=5)
        loop = ReActLoop(problem_description="Solve a problem", config=config)

        assert loop.problem_description == "Solve a problem"
        assert loop.config.max_iterations == 5
        assert loop.current_iteration == 0
        assert loop.status == LoopStatus.INITIALIZED

    @pytest.mark.asyncio
    async def test_run_loop(self):
        """Test running the loop"""
        config = LoopConfig(max_iterations=3, timeout_seconds=30)
        loop = ReActLoop(problem_description="Test problem", config=config)

        result = await loop.run()

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_completed >= 1
        assert result.final_thought is not None
        assert result.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_loop_with_custom_executor(self):
        """Test loop with custom action executor"""
        async def custom_executor(action):
            return {"success": True, "result": "Custom result"}

        config = LoopConfig(max_iterations=2)
        loop = ReActLoop(
            problem_description="Test",
            config=config,
            action_executor=custom_executor,
        )

        result = await loop.run()

        assert result.status == LoopStatus.COMPLETED
        assert result.metrics.successful_actions > 0

    @pytest.mark.asyncio
    async def test_loop_history_tracking(self):
        """Test that loop tracks history"""
        config = LoopConfig(max_iterations=3)
        loop = ReActLoop(problem_description="Track history", config=config)

        await loop.run()

        history = loop.get_history()

        assert history["stats"]["total_thoughts"] > 0
        assert history["stats"]["total_actions"] > 0

    @pytest.mark.asyncio
    async def test_loop_observations_summary(self):
        """Test observation summary"""
        config = LoopConfig(max_iterations=2)
        loop = ReActLoop(problem_description="Test observations", config=config)

        await loop.run()

        summary = loop.get_observations_summary()

        assert "total_observations" in summary
        assert summary["success_rate"] >= 0.0

    @pytest.mark.asyncio
    async def test_loop_metrics(self):
        """Test loop metrics collection"""
        config = LoopConfig(max_iterations=2)
        loop = ReActLoop(problem_description="Test metrics", config=config)

        result = await loop.run()

        assert result.metrics.total_iterations > 0
        assert result.metrics.average_iteration_time_ms >= 0

    def test_loop_config(self):
        """Test LoopConfig"""
        config = LoopConfig(
            max_iterations=20,
            timeout_seconds=600,
            confidence_threshold=0.8,
        )

        assert config.max_iterations == 20
        assert config.timeout_seconds == 600
        assert config.confidence_threshold == 0.8

    def test_loop_result(self):
        """Test LoopResult"""
        thought = Thought(content="Final thought", confidence=0.9)
        metrics = LoopMetrics(total_iterations=3)
        result = LoopResult(
            status=LoopStatus.COMPLETED,
            final_thought=thought,
            conclusion="Test conclusion",
            confidence=0.9,
            iterations_completed=3,
            metrics=metrics,
        )

        assert result.status == LoopStatus.COMPLETED
        assert result.conclusion == "Test conclusion"

        result_dict = result.to_dict()
        assert result_dict["status"] == "completed"
        assert result_dict["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_thought_step(self):
        """Test thinking step"""
        config = LoopConfig(max_iterations=1)
        loop = ReActLoop(problem_description="Test thinking", config=config)

        await loop._initial_analysis()
        await loop._think_step()

        latest_thought = loop.history.get_latest_thought()

        assert latest_thought is not None
        assert latest_thought.thought_type in [
            ThoughtType.PROBLEM_ANALYSIS,
            ThoughtType.DECOMPOSITION,
        ]

    @pytest.mark.asyncio
    async def test_act_step(self):
        """Test action step"""
        config = LoopConfig(max_iterations=1)
        loop = ReActLoop(problem_description="Test action", config=config)

        await loop._initial_analysis()
        await loop._think_step()
        await loop._act_step()

        latest_action = loop.history.get_latest_action()

        assert latest_action is not None
        assert latest_action.action_type != ""

    @pytest.mark.asyncio
    async def test_observe_step(self):
        """Test observation step"""
        config = LoopConfig(max_iterations=1)
        loop = ReActLoop(problem_description="Test observe", config=config)

        await loop._initial_analysis()
        await loop._think_step()
        await loop._act_step()
        await loop._observe_step()

        latest_obs = loop.history.get_latest_observation()

        assert latest_obs is not None

    def test_get_insights(self):
        """Test getting insights"""
        config = LoopConfig(max_iterations=1)
        loop = ReActLoop(problem_description="Test", config=config)

        # Add some observations with lessons
        loop.observation_memory.add_observation(
            content="Obs 1",
            action_type="query",
            result_type="success",
            lesson_learned="Key insight 1",
        )
        loop.observation_memory.add_observation(
            content="Obs 2",
            action_type="query",
            result_type="success",
            lesson_learned="Key insight 2",
        )

        insights = loop.get_insights()

        assert len(insights) == 2
        assert "Key insight 1" in insights


# ============================================================================
# Integration Tests
# ============================================================================


class TestReActIntegration:
    """Integration tests for full ReAct workflows"""

    @pytest.mark.asyncio
    async def test_full_reasoning_loop(self):
        """Test complete reasoning loop workflow"""
        config = LoopConfig(max_iterations=5, timeout_seconds=30)
        loop = ReActLoop(problem_description="What is 2+2?", config=config)

        result = await loop.run()

        assert result.status in [LoopStatus.COMPLETED, LoopStatus.TIMEOUT]
        assert result.iterations_completed > 0

    @pytest.mark.asyncio
    async def test_thought_action_observation_cycle(self):
        """Test think-act-observe cycle"""
        history = ThoughtActionHistory()

        # Simulate one cycle
        thought = history.add_thought(
            content="Analyzing problem",
            thought_type=ThoughtType.PROBLEM_ANALYSIS,
            confidence=0.6,
        )

        action = history.add_action(
            content="Execute query",
            action_type=ActionType.QUERY,
            thought_id=thought.id,
        )

        history.update_action_execution(action.id, 100, success=True)

        observation = history.add_observation(
            content="Query succeeded",
            action_id=action.id,
            observation_type=ObservationType.SUCCESS,
        )

        # Verify cycle
        cycle = history.get_loop_iteration(0)
        assert cycle["thought"]["id"] == thought.id
        assert cycle["action"]["id"] == action.id
        assert cycle["observation"]["id"] == observation.id

    def test_memory_observation_integration(self):
        """Test integration between history and memory"""
        history = ThoughtActionHistory()
        memory = ObservationMemory()

        # Add to history
        action = history.add_action(content="Query", action_type=ActionType.QUERY)
        obs = history.add_observation(content="Result", action_id=action.id)

        # Also add to memory
        memory.add_observation(
            content="Result",
            action_type="query",
            result_type="success",
            success=True,
        )

        # Verify both track it
        assert len(history.observations) == 1
        assert len(memory.observations) == 1
        assert memory.get_by_action_type("query")[0].content == "Result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
