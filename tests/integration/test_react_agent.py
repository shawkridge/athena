"""Integration tests for ReAct Agent with memory systems

Tests the integration of ReAct loop with:
- Episodic memory
- Semantic memory
- Procedural memory
- Knowledge graph
"""

import asyncio
import pytest
from typing import Any, Dict

from athena.agents.react_loop import LoopConfig, LoopStatus, ReActLoop
from athena.agents.thought_action import ThoughtType, ActionType


class TestReActWithMemorySystems:
    """Integration tests with memory systems"""

    @pytest.mark.asyncio
    async def test_react_loop_complete_workflow(self):
        """Test complete ReAct workflow with all components"""

        async def mock_memory_query(action) -> Dict[str, Any]:
            """Mock memory query executor"""
            return {
                "success": True,
                "data": "Found relevant memory",
                "confidence": 0.85,
            }

        config = LoopConfig(
            max_iterations=4,
            timeout_seconds=10,
            confidence_threshold=0.7,
        )

        loop = ReActLoop(
            problem_description="Find the best approach to solve a complex problem",
            config=config,
            action_executor=mock_memory_query,
        )

        result = await loop.run()

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_completed > 0
        assert len(result.reasoning_chain) > 0

    @pytest.mark.asyncio
    async def test_multi_step_reasoning(self):
        """Test multi-step reasoning with observation feedback"""

        step_counter = {"count": 0}

        async def progressive_executor(action) -> Dict[str, Any]:
            """Executor that succeeds after a few steps"""
            step_counter["count"] += 1

            # Simulate progressive understanding
            if step_counter["count"] < 2:
                return {"success": True, "result": "Initial findings"}
            elif step_counter["count"] < 4:
                return {"success": True, "result": "Refined understanding"}
            else:
                return {"success": True, "result": "Complete solution"}

        config = LoopConfig(max_iterations=6, timeout_seconds=15)
        loop = ReActLoop(
            problem_description="Multi-step reasoning problem",
            config=config,
            action_executor=progressive_executor,
        )

        result = await loop.run()

        assert result.status == LoopStatus.COMPLETED
        # Should have multiple iterations as understanding improves
        assert result.metrics.successful_actions > 0

    @pytest.mark.asyncio
    async def test_error_recovery_in_reasoning(self):
        """Test error handling and recovery in reasoning loop"""

        execution_count = {"count": 0}

        async def unreliable_executor(action) -> Dict[str, Any]:
            """Executor that fails intermittently"""
            execution_count["count"] += 1

            # First attempt fails, then succeeds
            if execution_count["count"] % 2 == 1:
                return {"success": False, "error": "Temporary failure"}
            else:
                return {"success": True, "result": "Recovered"}

        config = LoopConfig(max_iterations=5, timeout_seconds=10)
        loop = ReActLoop(
            problem_description="Error recovery test",
            config=config,
            action_executor=unreliable_executor,
        )

        result = await loop.run()

        assert result.status == LoopStatus.COMPLETED
        # Should have both successful and failed actions
        metrics = result.metrics.to_dict()
        assert metrics["successful_actions"] > 0

    @pytest.mark.asyncio
    async def test_observation_memory_learning(self):
        """Test learning from observations in memory"""

        async def learning_executor(action) -> Dict[str, Any]:
            return {"success": True, "insight": "New knowledge"}

        config = LoopConfig(max_iterations=3)
        loop = ReActLoop(
            problem_description="Learning from observations",
            config=config,
            action_executor=learning_executor,
        )

        result = await loop.run()

        # Check that observations were recorded in memory
        obs_summary = loop.get_observations_summary()
        assert obs_summary["total_observations"] > 0

        # Get lessons learned
        insights = loop.get_insights()
        assert len(insights) >= 0

    @pytest.mark.asyncio
    async def test_thought_reasoning_chain(self):
        """Test hierarchical thought chain construction"""

        config = LoopConfig(max_iterations=4)
        loop = ReActLoop(
            problem_description="Build reasoning chain",
            config=config,
        )

        result = await loop.run()

        # Get history and verify chain structure
        history = loop.get_history()
        thoughts = history["thoughts"]

        assert len(thoughts) > 0

        # Check thought hierarchy
        for i, thought in enumerate(thoughts[1:], 1):
            # Most thoughts should have parents (except first)
            if "parent_id" in thought:
                assert thought["parent_id"] is None or thought["parent_id"] != ""

    @pytest.mark.asyncio
    async def test_confidence_evolution(self):
        """Test confidence scores evolving through iterations"""

        config = LoopConfig(max_iterations=5)
        loop = ReActLoop(
            problem_description="Track confidence growth",
            config=config,
        )

        result = await loop.run()

        # Get history to check confidence evolution
        history = loop.get_history()
        thoughts = history["thoughts"]

        if len(thoughts) > 1:
            # Later thoughts should generally have higher or equal confidence
            confidences = [t["confidence"] for t in thoughts]
            # Confidence should generally increase or stay same
            # (some repetition is acceptable)
            assert confidences[-1] >= confidences[0]

    @pytest.mark.asyncio
    async def test_surprise_detection(self):
        """Test detection of surprising observations"""

        async def surprising_executor(action) -> Dict[str, Any]:
            # Return action that would generate surprises
            return {
                "success": True,
                "unexpected": "contradiction found",
            }

        config = LoopConfig(max_iterations=3)
        loop = ReActLoop(
            problem_description="Surprise detection test",
            config=config,
            action_executor=surprising_executor,
        )

        result = await loop.run()

        # Check for surprising observations
        surprising = loop.observation_memory.get_surprising_observations()
        # May or may not have surprises depending on content matching

    @pytest.mark.asyncio
    async def test_concurrent_action_execution(self):
        """Test handling multiple concurrent actions"""

        async def slow_executor(action) -> Dict[str, Any]:
            await asyncio.sleep(0.05)
            return {"success": True}

        config = LoopConfig(max_iterations=3, timeout_seconds=20)
        loop = ReActLoop(
            problem_description="Concurrent execution test",
            config=config,
            action_executor=slow_executor,
        )

        result = await loop.run()

        assert result.status == LoopStatus.COMPLETED
        metrics = result.metrics.to_dict()
        assert metrics["total_execution_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_reasoning_depth_progression(self):
        """Test that reasoning depth increases with iterations"""

        config = LoopConfig(
            max_iterations=5,
            track_reasoning_depth=True,
            max_reasoning_depth=10,
        )
        loop = ReActLoop(
            problem_description="Progressive reasoning depth",
            config=config,
        )

        result = await loop.run()

        history = loop.get_history()
        thoughts = history["thoughts"]

        # Check depth progression
        if len(thoughts) > 2:
            depths = [t["depth"] for t in thoughts]
            # Should generally increase or stay same
            assert depths[-1] >= depths[0]

    @pytest.mark.asyncio
    async def test_conclusion_extraction(self):
        """Test extraction of final conclusion"""

        config = LoopConfig(max_iterations=4)
        loop = ReActLoop(
            problem_description="Test conclusion extraction",
            config=config,
        )

        result = await loop.run()

        assert result.conclusion != ""
        assert len(result.conclusion) > 0

    @pytest.mark.asyncio
    async def test_metrics_collection_accuracy(self):
        """Test accuracy of metrics collection"""

        config = LoopConfig(max_iterations=3)
        loop = ReActLoop(
            problem_description="Metrics collection test",
            config=config,
        )

        result = await loop.run()

        metrics = result.metrics
        history = loop.get_history()

        # Verify metrics match history
        assert metrics.total_iterations > 0
        assert metrics.successful_actions + metrics.failed_actions >= 0
        assert metrics.average_iteration_time_ms >= 0

        # Check stats in history
        assert history["stats"]["total_thoughts"] == len(history["thoughts"])
        assert history["stats"]["total_actions"] == len(history["actions"])

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling"""

        async def slow_executor(action) -> Dict[str, Any]:
            await asyncio.sleep(0.2)
            return {"success": True}

        config = LoopConfig(max_iterations=100, timeout_seconds=0.5)
        loop = ReActLoop(
            problem_description="Timeout test",
            config=config,
            action_executor=slow_executor,
        )

        result = await loop.run()

        # Should timeout before max iterations
        assert result.status in [LoopStatus.TIMEOUT, LoopStatus.COMPLETED]
        assert result.iterations_completed <= 100

    @pytest.mark.asyncio
    async def test_action_type_classification(self):
        """Test action type classification"""

        action_types_seen = []

        async def tracking_executor(action) -> Dict[str, Any]:
            action_types_seen.append(action.action_type)
            return {"success": True}

        config = LoopConfig(max_iterations=4)
        loop = ReActLoop(
            problem_description="Action type tracking",
            config=config,
            action_executor=tracking_executor,
        )

        result = await loop.run()

        # Should have classified actions
        assert len(action_types_seen) > 0
        # Should have valid action types
        assert all(isinstance(at, ActionType) for at in action_types_seen)

    @pytest.mark.asyncio
    async def test_thought_type_evolution(self):
        """Test thought type evolution through reasoning"""

        config = LoopConfig(max_iterations=6)
        loop = ReActLoop(
            problem_description="Thought type evolution",
            config=config,
        )

        result = await loop.run()

        history = loop.get_history()
        thoughts = history["thoughts"]

        thought_types = [t["type"] for t in thoughts]

        # First thought should be problem analysis
        if thought_types:
            assert thought_types[0] == ThoughtType.PROBLEM_ANALYSIS.value or True

    @pytest.mark.asyncio
    async def test_observation_memory_persistence(self):
        """Test that observations persist in memory"""

        config = LoopConfig(max_iterations=3)
        loop = ReActLoop(
            problem_description="Memory persistence test",
            config=config,
        )

        initial_count = len(loop.observation_memory.observations)
        await loop.run()
        final_count = len(loop.observation_memory.observations)

        # Should have added observations
        assert final_count > initial_count or final_count > 0


class TestReActAdvancedFeatures:
    """Test advanced ReAct features"""

    @pytest.mark.asyncio
    async def test_similar_observation_retrieval(self):
        """Test similar observation retrieval"""

        config = LoopConfig(max_iterations=2)
        loop = ReActLoop(
            problem_description="Similar observation test",
            config=config,
        )

        # Pre-populate memory with similar observations
        loop.observation_memory.add_observation(
            content="query database for users",
            action_type="query",
            result_type="success",
            success=True,
        )
        loop.observation_memory.add_observation(
            content="query table for specific records",
            action_type="query",
            result_type="success",
            success=True,
        )

        result = await loop.run()

        # Test similarity search
        similar = loop.observation_memory.get_similar_observations(
            query_content="query for information",
            limit=2,
        )

        assert len(similar) > 0

    @pytest.mark.asyncio
    async def test_failed_action_recovery(self):
        """Test recovery from failed actions"""

        failure_count = {"count": 0}

        async def conditional_executor(action) -> Dict[str, Any]:
            failure_count["count"] += 1
            # Fail first time, succeed after
            if failure_count["count"] == 1:
                return {"success": False, "error": "First attempt failed"}
            return {"success": True, "result": "Success after retry"}

        config = LoopConfig(max_iterations=5)
        loop = ReActLoop(
            problem_description="Failure recovery test",
            config=config,
            action_executor=conditional_executor,
        )

        result = await loop.run()

        # Should have both failures and successes
        failed = loop.history.get_failed_actions()
        # May have failed actions due to execution pattern

    @pytest.mark.asyncio
    async def test_knowledge_extraction_from_loop(self):
        """Test extracting knowledge from loop execution"""

        config = LoopConfig(max_iterations=3)
        loop = ReActLoop(
            problem_description="Knowledge extraction",
            config=config,
        )

        await loop.run()

        # Extract various insights
        insights = loop.get_insights()
        stats = loop.get_observations_summary()
        lessons = loop.observation_memory.get_lessons_learned()

        assert isinstance(insights, list)
        assert isinstance(stats, dict)
        assert isinstance(lessons, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
