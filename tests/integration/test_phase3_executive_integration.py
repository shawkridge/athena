"""
Integration tests for Phase 3 Executive Function integration.

Tests goal-aware task decomposition, strategy selection, and workflow orchestration.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from athena.executive.models import Goal, GoalType, GoalStatus, StrategyType, ProgressMilestone
from athena.executive.hierarchy import GoalHierarchy
from athena.executive.strategy import StrategySelector
from athena.executive.conflict import ConflictResolver
from athena.executive.progress import ProgressMonitor
from athena.executive.agent_bridge import ExecutiveAgentBridge, GoalDecompositionContext
from athena.executive.orchestration_bridge import OrchestrationBridge, WorkflowState
from athena.executive.strategy_aware_planner import StrategyAwarePlanner, DecompositionStyle


@pytest.fixture
def mock_planner_agent():
    """Mock Planner Agent for testing."""
    class MockPlannerAgent:
        async def decompose_task(self, task: Dict[str, Any]):
            """Return a mock execution plan."""
            return {
                "status": "success",
                "plan": {
                    "id": 1,
                    "task_id": task.get("id"),
                    "task_description": task.get("description", ""),
                    "steps": [
                        {"id": 1, "description": "Plan", "estimated_duration_ms": 1800000, "dependencies": []},
                        {"id": 2, "description": "Implement", "estimated_duration_ms": 3600000, "dependencies": [1]},
                        {"id": 3, "description": "Test", "estimated_duration_ms": 1800000, "dependencies": [2]},
                        {"id": 4, "description": "Deploy", "estimated_duration_ms": 600000, "dependencies": [3]},
                    ],
                    "estimated_total_duration_ms": 7800000,
                    "estimated_total_resources": {"cpu": 50, "memory": 200},
                    "confidence": 0.8,
                    "complexity": "medium",
                    "critical_path": [1, 2, 3, 4],
                },
                "confidence": 0.8,
            }

    return MockPlannerAgent()


@pytest.fixture
def goal_hierarchy(tmp_path):
    """Create test goal hierarchy."""
    from athena.core.database import Database

    db = Database(tmp_path / "test.db")
    hierarchy = GoalHierarchy(db)
    hierarchy.project_id = 1
    return hierarchy


@pytest.fixture
def orchestration_bridge(goal_hierarchy, tmp_path):
    """Create orchestration bridge with test components."""
    bridge = OrchestrationBridge(
        hierarchy=goal_hierarchy,
        strategy_selector=StrategySelector(db_path=str(tmp_path / "strategies.db")),
        conflict_resolver=ConflictResolver(),
        progress_tracker=ProgressMonitor(),
    )
    return bridge


@pytest.fixture
def strategy_aware_planner(mock_planner_agent, orchestration_bridge):
    """Create strategy-aware planner."""
    return StrategyAwarePlanner(mock_planner_agent, orchestration_bridge)


class TestExecutiveAgentBridge:
    """Test ExecutiveAgentBridge for goal-aware decomposition."""

    def test_goal_to_decomposition_context(self):
        """Test converting goal to decomposition context."""
        bridge = ExecutiveAgentBridge()

        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Implement authentication system",
            goal_type=GoalType.PRIMARY,
            priority=8,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
            estimated_hours=40,
            deadline=datetime.now() + timedelta(days=7),
        )

        context = bridge.goal_to_decomposition_context(goal)

        assert isinstance(context, GoalDecompositionContext)
        assert context.goal == goal
        assert context.strategy in list(StrategyType)
        assert 0.0 <= context.confidence <= 1.0
        assert context.reasoning != ""
        assert len(context.alternative_strategies) > 0

    def test_rank_strategies(self):
        """Test strategy ranking by composite score."""
        bridge = ExecutiveAgentBridge()

        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Test goal",
            goal_type=GoalType.PRIMARY,
            priority=9,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
            deadline=datetime.now() + timedelta(days=2),  # Urgent
        )

        success_rates = {
            StrategyType.TOP_DOWN: 0.9,
            StrategyType.DEADLINE_DRIVEN: 0.85,
            StrategyType.BOTTOM_UP: 0.6,
        }

        ranked = bridge._rank_strategies(
            preferred=[StrategyType.TOP_DOWN, StrategyType.DEADLINE_DRIVEN],
            available=list(StrategyType),
            goal=goal,
            success_rates=success_rates,
        )

        # Top_DOWN and DEADLINE_DRIVEN should be highest
        assert ranked[0] in [StrategyType.TOP_DOWN, StrategyType.DEADLINE_DRIVEN]
        assert ranked[1] in [StrategyType.TOP_DOWN, StrategyType.DEADLINE_DRIVEN]

    def test_execution_plan_to_milestones(self):
        """Test converting plan steps to milestones."""
        bridge = ExecutiveAgentBridge()

        # Create mock plan with 8 steps
        class MockPlan:
            steps = [{"id": i, "description": f"Step {i}", "estimated_duration_ms": 1000000} for i in range(8)]
            estimated_total_duration_ms = 8000000

        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Test",
            goal_type=GoalType.PRIMARY,
            priority=5,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )

        milestones = bridge.execution_plan_to_milestones(MockPlan(), goal)

        assert len(milestones) == 4  # 25%, 50%, 75%, 100%
        assert all(isinstance(m, ProgressMilestone) for m in milestones)
        assert milestones[0].goal_id == 1

    def test_track_strategy_outcome(self):
        """Test recording strategy outcome for learning."""
        bridge = ExecutiveAgentBridge()

        rec = bridge.track_strategy_outcome(
            goal_id=1,
            strategy=StrategyType.TOP_DOWN,
            outcome="success",
            duration_ms=5400000,
            notes="Worked well for architecture-heavy task",
        )

        assert rec.strategy_type == StrategyType.TOP_DOWN
        assert rec.outcome == "success"
        assert rec.confidence == 0.95  # success maps to 0.95

    def test_plan_respects_goal_constraints(self):
        """Test validating plan against goal constraints."""
        bridge = ExecutiveAgentBridge()

        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Quick task",
            goal_type=GoalType.SUBGOAL,
            priority=5,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
            estimated_hours=10,  # 10 hours available
            deadline=datetime.now() + timedelta(hours=12),
        )

        # Plan within constraints
        class GoodPlan:
            estimated_total_duration_ms = 9 * 3600000  # 9 hours

        # Plan exceeding constraints
        class BadPlan:
            estimated_total_duration_ms = 20 * 3600000  # 20 hours

        assert bridge.plan_respects_goal_constraints(GoodPlan(), goal) == True
        assert bridge.plan_respects_goal_constraints(BadPlan(), goal) == False


class TestOrchestrationBridge:
    """Test OrchestrationBridge for workflow management."""

    def test_activate_goal(self, orchestration_bridge, goal_hierarchy):
        """Test activating a goal."""
        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Build feature",
            goal_type=GoalType.PRIMARY,
            priority=7,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )
        goal_hierarchy.create_goal(goal)

        result = orchestration_bridge.activate_goal(goal.id)

        assert result["status"] == "success"
        assert result["goal_id"] == 1
        assert orchestration_bridge.current_goal == 1
        assert 1 in orchestration_bridge.active_goals

    def test_switch_goal_with_cost(self, orchestration_bridge, goal_hierarchy):
        """Test switching goals with cost analysis."""
        goal1 = Goal(
            id=1,
            project_id=1,
            goal_text="Authentication",
            goal_type=GoalType.PRIMARY,
            priority=8,
            status=GoalStatus.ACTIVE,
            progress=0.5,
            created_at=datetime.now(),
        )
        goal2 = Goal(
            id=2,
            project_id=1,
            goal_text="Database",
            goal_type=GoalType.PRIMARY,
            priority=7,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )
        goal_hierarchy.create_goal(goal1)
        goal_hierarchy.create_goal(goal2)

        # Activate first goal
        orchestration_bridge.activate_goal(1)

        # Switch to second
        result = orchestration_bridge._switch_goal(1, 2)

        assert result["status"] == "success"
        assert result["switch_cost_ms"] > 0
        assert len(orchestration_bridge.switch_history) > 0

    def test_check_goal_conflicts(self, orchestration_bridge, goal_hierarchy):
        """Test conflict detection."""
        goal1 = Goal(
            id=1,
            project_id=1,
            goal_text="Frontend",
            goal_type=GoalType.PRIMARY,
            priority=9,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )
        goal2 = Goal(
            id=2,
            project_id=1,
            goal_text="Backend",
            goal_type=GoalType.PRIMARY,
            priority=9,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )
        goal_hierarchy.create_goal(goal1)
        goal_hierarchy.create_goal(goal2)

        result = orchestration_bridge.check_goal_conflicts(1)

        assert result["project_id"] == 1
        assert result["active_goal_count"] >= 0

    def test_get_goal_priority_ranking(self, orchestration_bridge, goal_hierarchy):
        """Test priority ranking logic."""
        goals = [
            Goal(
                id=1,
                project_id=1,
                goal_text="Urgent task",
                goal_type=GoalType.PRIMARY,
                priority=9,
                status=GoalStatus.ACTIVE,
                progress=0.0,
                created_at=datetime.now(),
                deadline=datetime.now() + timedelta(days=1),
            ),
            Goal(
                id=2,
                project_id=1,
                goal_text="Low priority",
                goal_type=GoalType.SUBGOAL,
                priority=3,
                status=GoalStatus.ACTIVE,
                progress=0.0,
                created_at=datetime.now(),
                deadline=datetime.now() + timedelta(days=30),
            ),
        ]
        for goal in goals:
            goal_hierarchy.create_goal(goal)

        ranked = orchestration_bridge.get_goal_priority_ranking(1)

        assert len(ranked) >= 1
        # First should have higher score than second
        if len(ranked) >= 2:
            assert ranked[0]["score"] >= ranked[1]["score"]

    def test_prepare_goal_for_planner(self, orchestration_bridge, goal_hierarchy):
        """Test preparing goal for planner."""
        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Implement feature",
            goal_type=GoalType.PRIMARY,
            priority=7,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )
        goal_hierarchy.create_goal(goal)

        context = orchestration_bridge.prepare_goal_for_planner(1)

        assert context["status"] == "success"
        assert context["goal_id"] == 1
        assert context["strategy"] in [s.value for s in StrategyType]
        assert 0.0 <= context["confidence"] <= 1.0

    def test_record_plan_execution(self, orchestration_bridge, goal_hierarchy):
        """Test recording execution progress."""
        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Test",
            goal_type=GoalType.PRIMARY,
            priority=5,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )
        goal_hierarchy.create_goal(goal)
        orchestration_bridge.activate_goal(1)

        result = orchestration_bridge.record_plan_execution(
            goal_id=1,
            plan_id=100,
            steps_completed=5,
            total_steps=10,
            errors=0,
            blockers=0,
        )

        assert result["status"] == "success"
        assert result["progress"] == 0.5
        assert 1 in orchestration_bridge.monitor_state

    def test_mark_goal_completed(self, orchestration_bridge, goal_hierarchy):
        """Test completing a goal."""
        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Finish feature",
            goal_type=GoalType.PRIMARY,
            priority=7,
            status=GoalStatus.ACTIVE,
            progress=1.0,
            created_at=datetime.now(),
        )
        goal_hierarchy.create_goal(goal)
        orchestration_bridge.activate_goal(1)

        result = orchestration_bridge.mark_goal_completed(1, "success", "All features done")

        assert result["status"] == "success"
        assert result["outcome"] == "success"
        assert 1 not in orchestration_bridge.active_goals

    def test_workflow_status(self, orchestration_bridge, goal_hierarchy):
        """Test getting workflow status."""
        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Test",
            goal_type=GoalType.PRIMARY,
            priority=5,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
        )
        goal_hierarchy.create_goal(goal)
        orchestration_bridge.activate_goal(1)

        status = orchestration_bridge.get_workflow_status()

        assert status["current_goal"] == 1
        assert len(status["active_goals"]) >= 1
        assert status["workflow_state"] in [s.value for s in WorkflowState]


class TestStrategyAwarePlanner:
    """Test StrategyAwarePlanner decomposition styles."""

    @pytest.mark.asyncio
    async def test_hierarchical_decomposition(self, strategy_aware_planner):
        """Test hierarchical (TOP_DOWN) decomposition."""
        result = await strategy_aware_planner.decompose_with_strategy(
            task={"id": 1, "description": "Build auth system"},
            strategy=StrategyType.TOP_DOWN,
            reasoning="Complex architectural decisions needed",
        )

        assert result["status"] == "success"
        assert result["strategy"] == "top_down"
        plan = result["plan"]
        assert len(plan["steps"]) > 4  # Should add design review phases
        assert plan["decomposition_style"] == "hierarchical"

    @pytest.mark.asyncio
    async def test_iterative_decomposition(self, strategy_aware_planner):
        """Test iterative (BOTTOM_UP) decomposition."""
        result = await strategy_aware_planner.decompose_with_strategy(
            task={"id": 1, "description": "MVP feature"},
            strategy=StrategyType.BOTTOM_UP,
            reasoning="Start with MVP, iterate on feedback",
        )

        assert result["status"] == "success"
        assert result["strategy"] == "bottom_up"
        assert result["plan"]["decomposition_style"] == "iterative"

    @pytest.mark.asyncio
    async def test_spike_decomposition(self, strategy_aware_planner):
        """Test spike (research-first) decomposition."""
        result = await strategy_aware_planner.decompose_with_strategy(
            task={"id": 1, "description": "Evaluate frameworks"},
            strategy=StrategyType.SPIKE,
            reasoning="Need to research before committing",
        )

        assert result["status"] == "success"
        assert result["strategy"] == "spike"
        plan = result["plan"]
        # First step should be research
        assert "research" in plan["steps"][0]["description"].lower() or "spike" in plan["steps"][0]["description"].lower()

    @pytest.mark.asyncio
    async def test_parallel_decomposition(self, strategy_aware_planner):
        """Test parallel decomposition for independent work."""
        result = await strategy_aware_planner.decompose_with_strategy(
            task={"id": 1, "description": "Build multi-component system"},
            strategy=StrategyType.PARALLEL,
            reasoning="Components can be built independently",
        )

        assert result["status"] == "success"
        assert result["strategy"] == "parallel"
        plan = result["plan"]
        # Should have multiple steps without dependencies on each other
        assert len(plan["steps"]) >= 5

    @pytest.mark.asyncio
    async def test_deadline_driven_decomposition(self, strategy_aware_planner):
        """Test deadline-driven (risk minimization) decomposition."""
        result = await strategy_aware_planner.decompose_with_strategy(
            task={"id": 1, "description": "Critical production fix"},
            strategy=StrategyType.DEADLINE_DRIVEN,
            reasoning="Deadline is imminent, minimize risk",
        )

        assert result["status"] == "success"
        assert result["strategy"] == "deadline_driven"
        plan = result["plan"]
        # Should emphasize core work early
        assert "core" in plan["steps"][0]["description"].lower() or "risk" in plan["steps"][0]["description"].lower()

    @pytest.mark.asyncio
    async def test_quality_first_decomposition(self, strategy_aware_planner):
        """Test quality-first (extra testing) decomposition."""
        result = await strategy_aware_planner.decompose_with_strategy(
            task={"id": 1, "description": "Critical system component"},
            strategy=StrategyType.QUALITY_FIRST,
            reasoning="Quality is paramount for this component",
        )

        assert result["status"] == "success"
        assert result["strategy"] == "quality_first"
        plan = result["plan"]
        # Should have extra testing/review phases
        assert len(plan["steps"]) > 6  # More steps for testing

    def test_all_decomposition_styles_valid(self):
        """Test all 9 decomposition styles are properly mapped."""
        style_map = StrategyAwarePlanner.STRATEGY_DECOMPOSITION_MAP

        assert len(style_map) == 9
        assert StrategyType.TOP_DOWN in style_map
        assert StrategyType.BOTTOM_UP in style_map
        assert StrategyType.SPIKE in style_map
        assert StrategyType.PARALLEL in style_map
        assert StrategyType.SEQUENTIAL in style_map
        assert StrategyType.DEADLINE_DRIVEN in style_map
        assert StrategyType.QUALITY_FIRST in style_map
        assert StrategyType.COLLABORATION in style_map
        assert StrategyType.EXPERIMENTAL in style_map


class TestEnd2EndIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_full_workflow_goal_to_plan(self, orchestration_bridge, strategy_aware_planner, goal_hierarchy):
        """Test complete flow from goal to strategy-aware plan."""
        # 1. Create goal
        goal = Goal(
            id=1,
            project_id=1,
            goal_text="Implement user authentication",
            goal_type=GoalType.PRIMARY,
            priority=8,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            created_at=datetime.now(),
            estimated_hours=40,
            deadline=datetime.now() + timedelta(days=7),
        )
        goal_hierarchy.create_goal(goal)

        # 2. Activate goal
        activate_result = orchestration_bridge.activate_goal(1)
        assert activate_result["status"] == "success"

        # 3. Prepare for planner
        prepare_result = orchestration_bridge.prepare_goal_for_planner(1)
        assert prepare_result["status"] == "success"
        strategy = prepare_result["strategy"]

        # 4. Decompose with strategy
        decompose_result = await strategy_aware_planner.decompose_with_strategy(
            task={"id": 1, "description": goal.goal_text},
            strategy=StrategyType[strategy.upper()],
            reasoning=prepare_result["reasoning"],
        )
        assert decompose_result["status"] == "success"

        # 5. Record execution
        plan = decompose_result["plan"]
        exec_result = orchestration_bridge.record_plan_execution(
            goal_id=1,
            plan_id=plan["id"],
            steps_completed=2,
            total_steps=len(plan["steps"]),
            errors=0,
            blockers=0,
        )
        assert exec_result["status"] == "success"

        # 6. Complete goal
        complete_result = orchestration_bridge.mark_goal_completed(1, "success")
        assert complete_result["status"] == "success"
        assert 1 not in orchestration_bridge.active_goals


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
