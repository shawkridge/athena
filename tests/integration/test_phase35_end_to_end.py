"""End-to-end integration tests for Phase 3.5 - Full planning system workflow."""

import pytest
import asyncio
from pathlib import Path

from athena.mcp.handlers import MemoryMCPServer
from athena.manager import UnifiedMemoryManager, QueryType


def run_async(coro):
    """Helper to run async code in sync tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def server(tmp_path: Path) -> MemoryMCPServer:
    """Create MCP server instance."""
    db_path = tmp_path / "test.db"
    return MemoryMCPServer(str(db_path))


class TestPlanningAwareRouting:
    """Test planning-aware query routing in UnifiedMemoryManager."""

    def test_classify_planning_query_decompose(self, server: MemoryMCPServer):
        """Test query classification for decompose queries."""
        query = "How should I decompose this authentication task?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.PLANNING

    def test_classify_planning_query_strategy(self, server: MemoryMCPServer):
        """Test query classification for strategy queries."""
        query = "What planning strategy would work best for this refactoring?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.PLANNING

    def test_classify_planning_query_orchestration(self, server: MemoryMCPServer):
        """Test query classification for orchestration queries."""
        query = "How should I orchestrate 5 agents for this project?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.PLANNING

    def test_classify_non_planning_query(self, server: MemoryMCPServer):
        """Test that non-planning queries are not classified as planning."""
        query = "What did I do yesterday?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.TEMPORAL

    def test_query_planning_layer(self, server: MemoryMCPServer):
        """Test querying the planning layer."""
        query = "Suggest a planning strategy for a complex refactoring"
        context = {"complexity": 7, "domain": "refactoring"}

        results = server.unified_manager._query_planning(query, context, k=3)
        assert isinstance(results, list)
        # Results may be empty if planning patterns not populated, but should not error


class TestEndToEndWorkflow:
    """Test complete workflows from planning to execution."""

    def test_workflow_decompose_and_validate(self, server: MemoryMCPServer):
        """Test: Decompose task -> Validate plan -> Execute."""
        # Step 1: Decompose a complex task
        decompose_args = {
            "task_description": "Build authentication system with OAuth2",
            "complexity_level": 7,
            "domain": "security",
        }
        decompose_result = run_async(server._handle_decompose_hierarchically(decompose_args))
        assert "✓" in decompose_result[0].text
        # Complexity 7 should give depth 3 for medium-high complexity
        assert "Depth: 3" in decompose_result[0].text or "Hierarchical" in decompose_result[0].text

        # Step 2: Get strategy suggestion
        strategy_args = {
            "task_description": "Build authentication system with OAuth2",
            "domain": "security",
            "complexity": 7,
        }
        strategy_result = run_async(server._handle_suggest_planning_strategy(strategy_args))
        assert "✓" in strategy_result[0].text
        assert "Hierarchical" in strategy_result[0].text or "Complex" in strategy_result[0].text

        # Step 3: Orchestration recommendation
        orch_args = {
            "num_agents": 3,
            "task_domains": ["security", "backend", "devops"],
        }
        orch_result = run_async(server._handle_recommend_orchestration(orch_args))
        assert "✓" in orch_result[0].text
        assert "Orchestrator-Worker" in orch_result[0].text

    def test_workflow_plan_validate_execute_feedback(self, server: MemoryMCPServer):
        """Test: Plan -> Validate -> Execute -> Record Feedback."""
        project = server.project_manager.store.create_project("oauth_project", "/tmp/oauth")

        # Step 1: Validate plan
        validate_args = {"project_id": project.id}
        validate_result = run_async(server._handle_validate_plan(validate_args))
        assert validate_result is not None  # Should handle gracefully

        # Step 2: Get project status before execution
        status_before = run_async(server._handle_get_project_status({"project_id": project.id}))
        assert status_before is not None

        # Step 3: Record execution feedback
        feedback_args = {
            "task_id": 1,
            "actual_duration": 120,
            "blockers": ["API rate limiting"],
            "quality_metrics": {"success": True, "quality_score": 0.88},
            "lessons_learned": "Rate limiting required upfront API planning",
        }
        feedback_result = run_async(server._handle_record_execution_feedback(feedback_args))
        assert "✓" in feedback_result[0].text

        # Step 4: Get project status after execution
        status_after = run_async(server._handle_get_project_status({"project_id": project.id}))
        assert status_after is not None

    def test_workflow_multiple_strategy_recommendations(self, server: MemoryMCPServer):
        """Test: Get multiple strategy recommendations for different complexities."""
        strategies = []

        # Simple task
        simple_result = run_async(server._handle_suggest_planning_strategy({
            "task_description": "Add button to UI",
            "complexity": 2,
        }))
        assert "Simple Sequential" in simple_result[0].text
        strategies.append(simple_result)

        # Medium task
        medium_result = run_async(server._handle_suggest_planning_strategy({
            "task_description": "Refactor database layer",
            "complexity": 5,
        }))
        assert "Hierarchical" in medium_result[0].text
        strategies.append(medium_result)

        # Complex task
        complex_result = run_async(server._handle_suggest_planning_strategy({
            "task_description": "Build microservices architecture",
            "complexity": 9,
        }))
        strategies.append(complex_result)

        # All should return results
        assert len(strategies) == 3
        for strategy in strategies:
            assert "✓" in strategy[0].text

    def test_workflow_full_project_lifecycle(self, server: MemoryMCPServer):
        """Test complete project lifecycle from planning to completion."""
        # Create project
        project = server.project_manager.store.create_project("full_lifecycle", "/tmp/lifecycle")

        # Phase 1: Planning
        plan_result = run_async(server._handle_decompose_hierarchically({
            "task_description": "Implement user authentication",
            "complexity_level": 6,
            "domain": "backend",
        }))
        assert "✓" in plan_result[0].text

        # Phase 2: Strategy
        strategy_result = run_async(server._handle_suggest_planning_strategy({
            "task_description": "Implement user authentication",
            "complexity": 6,
        }))
        assert "✓" in strategy_result[0].text

        # Phase 3: Orchestration
        orch_result = run_async(server._handle_recommend_orchestration({
            "num_agents": 2,
            "task_domains": ["backend"],
        }))
        assert "✓" in orch_result[0].text

        # Phase 4: Validation
        validate_result = run_async(server._handle_validate_plan({
            "project_id": project.id,
        }))
        assert validate_result is not None

        # Phase 5: Execution feedback
        feedback_result = run_async(server._handle_record_execution_feedback({
            "task_id": 1,
            "actual_duration": 90,
            "blockers": [],
            "quality_metrics": {"success": True, "quality_score": 0.95},
        }))
        assert "✓" in feedback_result[0].text

        # Phase 6: Status check
        status_result = run_async(server._handle_get_project_status({
            "project_id": project.id,
        }))
        assert status_result is not None


class TestPlanningQueryRouting:
    """Test that planning queries are properly routed in UnifiedMemoryManager."""

    def test_retrieve_planning_query_direct(self, server: MemoryMCPServer):
        """Test directly retrieving a planning query."""
        query = "How should I decompose this complex refactoring task?"
        context = {"complexity": 8, "domain": "refactoring"}

        results = server.unified_manager.retrieve(
            query=query,
            context=context,
            k=3
        )

        # Should have "planning" key in results
        assert "planning" in results or len(results) > 0

    def test_classify_multiple_planning_keywords(self, server: MemoryMCPServer):
        """Test classification with multiple planning keywords."""
        # Test key planning queries
        planning_queries = [
            "Can you suggest a decomposition strategy?",
            "What's the orchestration pattern?",
            "Recommend orchestration for 5 agents",
        ]

        for query in planning_queries:
            query_type = server.unified_manager._classify_query(query)
            assert query_type == QueryType.PLANNING, f"Query '{query}' not classified as PLANNING, got {query_type}"


class TestBackwardCompatibility:
    """Test that existing functionality still works (Phase 3.5 backward compatibility)."""

    def test_temporal_queries_still_work(self, server: MemoryMCPServer):
        """Test that temporal queries are not affected by planning routing."""
        query = "What did I do yesterday?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.TEMPORAL

    def test_factual_queries_still_work(self, server: MemoryMCPServer):
        """Test that factual queries are not affected by planning routing."""
        query = "What is the current architecture?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.FACTUAL

    def test_prospective_queries_still_work(self, server: MemoryMCPServer):
        """Test that prospective queries are not affected by planning routing."""
        query = "What tasks do I need to complete?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.PROSPECTIVE

    def test_procedural_queries_still_work(self, server: MemoryMCPServer):
        """Test that procedural queries are not affected by planning routing."""
        query = "How do I deploy this service?"
        query_type = server.unified_manager._classify_query(query)
        assert query_type == QueryType.PROCEDURAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
