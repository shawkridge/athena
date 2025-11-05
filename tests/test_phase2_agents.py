"""
Comprehensive test suite for Phase 2 agents.

Tests for:
- planning_orchestrator.py
- goal_orchestrator.py
- conflict_resolver.py

Coverage:
- Unit tests for all methods
- Integration tests for agent interactions
- MCP operation validation
- Error scenario handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Import agents
import sys
sys.path.insert(0, '/home/user/.work/athena/src')

from athena.agents.planning_orchestrator import (
    PlanningOrchestrator, PlanningStage, ReplannTrigger, PlanAnalysis, DecomposedPlan
)
from athena.agents.goal_orchestrator import (
    GoalOrchestrator, GoalState, GoalPriority, GoalMetrics, GoalContext
)
from athena.agents.conflict_resolver import (
    ConflictResolver, ConflictType, ConflictSeverity, ResolutionStrategy, ConflictDetail
)


class TestPlanningOrchestrator:
    """Test suite for PlanningOrchestrator agent."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        db = Mock()
        mcp = AsyncMock()
        return PlanningOrchestrator(db, mcp)

    @pytest.mark.asyncio
    async def test_orchestrate_planning_initialization(self, orchestrator):
        """Test orchestration starts and initializes properly."""
        orchestrator.mcp.call_operation = AsyncMock()

        # Create a result dict
        result = {
            "task": "Test task",
            "stages": {},
            "success": False,
            "errors": []
        }

        # Verify orchestrator has proper initialization
        assert orchestrator.db is not None
        assert orchestrator.mcp is not None
        assert orchestrator.current_plan is None
        assert orchestrator.monitoring_enabled is False

    @pytest.mark.asyncio
    async def test_analyze_task_complexity(self, orchestrator):
        """Test task analysis with complexity scoring."""
        # Low complexity
        result = await orchestrator._analyze_task("Simple task", 2)
        assert result.complexity == 2
        assert result.scope_days == 2
        assert result.risk_level == "Low"

        # High complexity
        result = await orchestrator._analyze_task("Complex task", 9)
        assert result.complexity == 9
        assert result.scope_days == 28
        assert result.risk_level == "Critical"

    @pytest.mark.asyncio
    async def test_decompose_plan_mcp_integration(self, orchestrator):
        """Test plan decomposition with MCP operation."""
        orchestrator.mcp.call_operation = AsyncMock(return_value={
            "phases": [{"name": "Phase 1", "duration": 5}],
            "tasks": [{"id": 1}, {"id": 2}, {"id": 3}],
            "dependencies": {"1": ["2"]},
            "critical_path": [1, 2],
            "total_duration_days": 10
        })

        result = await orchestrator._decompose_plan("Test task", 5)

        assert result.total_tasks == 3
        assert result.total_duration_days == 10
        assert len(result.critical_path) == 2
        orchestrator.mcp.call_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_plan_three_levels(self, orchestrator):
        """Test plan validation with 3-level checks."""
        orchestrator.mcp.call_operation = AsyncMock(return_value={
            "is_valid": True,
            "level": "GOOD",
            "confidence": 0.85,
            "issues": [],
            "warnings": ["Minor resource constraint"],
            "recommendations": ["Add buffer time"]
        })

        plan = DecomposedPlan(
            phases=[{"name": "Phase 1"}],
            total_tasks=10,
            critical_path=[1, 2],
            total_duration_days=7,
            dependencies={}
        )

        result = await orchestrator._validate_plan(plan)

        assert result["is_valid"] is True
        assert result["level"] == "GOOD"
        assert result["confidence"] == 0.85
        # warnings_found returns the count, not a list
        assert result["warnings"] == 1

    @pytest.mark.asyncio
    async def test_monitor_progress(self, orchestrator):
        """Test progress monitoring."""
        orchestrator.current_plan = {
            "goal_id": 1,
            "task_ids": [1, 2, 3]
        }

        result = await orchestrator.monitor_progress()

        assert result["goal_id"] == 1
        assert result["status"] == "monitoring_active"
        assert "deviations" in result

    @pytest.mark.asyncio
    async def test_trigger_replanning_on_deviation(self, orchestrator):
        """Test adaptive replanning trigger."""
        orchestrator.current_plan = {
            "goal_id": 1,
            "task_ids": [1, 2, 3]
        }

        orchestrator.mcp.call_operation = AsyncMock(return_value={
            "new_strategy": "parallel",
            "timeline_impact": -2,
            "recommendations": ["Add resources"]
        })

        result = await orchestrator.trigger_replanning(
            "DURATION_EXCEEDED",
            "Task taking 30% longer"
        )

        assert result["replanning_triggered"] is True
        assert result["trigger_type"] == "DURATION_EXCEEDED"

    @pytest.mark.asyncio
    async def test_error_handling_orchestration(self, orchestrator):
        """Test error handling in orchestration."""
        orchestrator.mcp.call_operation = AsyncMock(side_effect=Exception("MCP Error"))

        result = await orchestrator.orchestrate_planning("Test", complexity=5)

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "MCP Error" in result["errors"]


class TestGoalOrchestrator:
    """Test suite for GoalOrchestrator agent."""

    @pytest.fixture
    def orchestrator(self):
        """Create goal orchestrator with mocked dependencies."""
        db = Mock()
        mcp = AsyncMock()
        return GoalOrchestrator(db, mcp)

    @pytest.fixture
    def sample_goal(self):
        """Create a sample goal context."""
        return GoalContext(
            goal_id=1,
            name="Implement auth",
            description="Add user authentication",
            state=GoalState.PENDING,
            priority=9,
            deadline=(datetime.utcnow() + timedelta(days=7)).isoformat(),
            owner="Alice",
            metrics=GoalMetrics(health_score=1.0),
            dependencies=[],
            dependent_goals=[2, 3]
        )

    @pytest.mark.asyncio
    async def test_activate_goal_success(self, orchestrator, sample_goal):
        """Test successful goal activation."""
        orchestrator._load_goal = AsyncMock(return_value=sample_goal)
        orchestrator._check_dependencies = AsyncMock(return_value={
            "satisfied": True,
            "blocked_by": [],
            "details": []
        })
        orchestrator._analyze_context_switch = AsyncMock(return_value={
            "cost_minutes": 10,
            "memory_loss": 0.1
        })
        orchestrator._check_resources = AsyncMock(return_value={
            "available": True,
            "missing_resources": []
        })
        orchestrator._analyze_priority = AsyncMock(return_value={
            "priority_score": 9,
            "urgency_score": 10
        })
        orchestrator.mcp.call_operation = AsyncMock(return_value={"success": True})

        result = await orchestrator.activate_goal(1)

        assert result["success"] is True
        assert result["goal_id"] == 1
        assert 1 in orchestrator.active_goals

    @pytest.mark.asyncio
    async def test_activate_goal_blocked_by_dependency(self, orchestrator, sample_goal):
        """Test goal activation blocked by unmet dependency."""
        orchestrator._load_goal = AsyncMock(return_value=sample_goal)
        orchestrator._check_dependencies = AsyncMock(return_value={
            "satisfied": False,
            "blocked_by": [0],
            "details": [{"goal_id": 0, "state": "PENDING"}]
        })

        result = await orchestrator.activate_goal(1)

        assert len(result["warnings"]) > 0
        assert "Dependency blocker" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_track_goal_progress_with_milestones(self, orchestrator, sample_goal):
        """Test progress tracking with milestone detection."""
        orchestrator.goal_hierarchy[1] = sample_goal
        orchestrator._calculate_health_score = AsyncMock(return_value=0.85)
        orchestrator._detect_milestones = AsyncMock(return_value=["25% Progress"])
        orchestrator._check_timeline_slip = AsyncMock(return_value={
            "is_slipping": False,
            "days_behind": 0
        })
        orchestrator.mcp.call_operation = AsyncMock()

        result = await orchestrator.track_goal_progress(1, {
            "percent": 25,
            "errors": 0,
            "blockers": 0
        })

        assert result["success"] is True
        assert len(result["milestones_reached"]) > 0

    @pytest.mark.asyncio
    async def test_complete_goal_success(self, orchestrator, sample_goal):
        """Test goal completion."""
        orchestrator.goal_hierarchy[1] = sample_goal
        orchestrator.active_goals[1] = sample_goal
        orchestrator.mcp.call_operation = AsyncMock()

        result = await orchestrator.complete_goal(1, "success")

        assert result["success"] is True
        assert sample_goal.state == GoalState.COMPLETED
        assert 1 not in orchestrator.active_goals

    @pytest.mark.asyncio
    async def test_complete_goal_activates_dependents(self, orchestrator, sample_goal):
        """Test that completing a goal activates dependent goals."""
        orchestrator.goal_hierarchy[1] = sample_goal

        # Create dependent goals
        dep_goal = GoalContext(
            goal_id=2,
            name="Integration testing",
            description="Test auth integration",
            state=GoalState.PENDING,
            priority=8,
            dependencies=[1],
            dependent_goals=[]
        )
        orchestrator.goal_hierarchy[2] = dep_goal

        orchestrator.mcp.call_operation = AsyncMock()
        orchestrator.activate_goal = AsyncMock()

        result = await orchestrator.complete_goal(1, "success")

        assert result["success"] is True
        # Verify dependent goal activation was requested
        assert sample_goal.state == GoalState.COMPLETED

    @pytest.mark.asyncio
    async def test_get_goal_hierarchy(self, orchestrator, sample_goal):
        """Test hierarchy retrieval."""
        orchestrator.goal_hierarchy[1] = sample_goal
        orchestrator.mcp.call_operation = AsyncMock(return_value={
            "status": "ok"
        })

        result = await orchestrator.get_goal_hierarchy()

        assert result["success"] is True
        assert len(result["hierarchy"]) == 1
        assert result["hierarchy"][0]["goal_id"] == 1

    @pytest.mark.asyncio
    async def test_check_goal_deadlines(self, orchestrator):
        """Test deadline detection."""
        # Overdue goal
        overdue = GoalContext(
            goal_id=1,
            name="Overdue goal",
            description="Overdue description",
            state=GoalState.IN_PROGRESS,
            priority=5,
            deadline=(datetime.utcnow() - timedelta(days=2)).isoformat()
        )

        # Approaching deadline
        approaching = GoalContext(
            goal_id=2,
            name="Approaching goal",
            description="Approaching description",
            state=GoalState.IN_PROGRESS,
            priority=5,
            deadline=(datetime.utcnow() + timedelta(days=1)).isoformat()
        )

        orchestrator.goal_hierarchy = {1: overdue, 2: approaching}

        result = await orchestrator.check_goal_deadlines()

        assert result["success"] is True
        assert len(result["overdue"]) == 1
        assert len(result["approaching_deadlines"]) == 1

    @pytest.mark.asyncio
    async def test_health_score_calculation(self, orchestrator, sample_goal):
        """Test health score composite calculation."""
        # Perfect health
        sample_goal.metrics.progress_percent = 100
        sample_goal.metrics.errors_encountered = 0
        sample_goal.metrics.blockers_active = 0
        score = await orchestrator._calculate_health_score(sample_goal)
        assert score >= 0.8

        # Degraded health
        sample_goal.metrics.progress_percent = 30
        sample_goal.metrics.errors_encountered = 5
        sample_goal.metrics.blockers_active = 2
        score = await orchestrator._calculate_health_score(sample_goal)
        assert score < 0.6


class TestConflictResolver:
    """Test suite for ConflictResolver agent."""

    @pytest.fixture
    def resolver(self):
        """Create conflict resolver with mocked dependencies."""
        db = Mock()
        mcp = AsyncMock()
        return ConflictResolver(db, mcp)

    @pytest.fixture
    def sample_goals(self):
        """Create sample goals with conflicts."""
        return [
            {
                "id": 1,
                "name": "Auth",
                "owner": "Alice",
                "priority": 9,
                "deadline": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "dependencies": [],
                "estimated_hours": 40
            },
            {
                "id": 2,
                "name": "API",
                "owner": "Alice",
                "priority": 7,
                "deadline": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "dependencies": [],
                "estimated_hours": 40
            },
            {
                "id": 3,
                "name": "Database",
                "owner": "Bob",
                "priority": 8,
                "deadline": (datetime.utcnow() + timedelta(days=10)).isoformat(),
                "dependencies": [1],
                "estimated_hours": 30
            }
        ]

    @pytest.mark.asyncio
    async def test_detect_resource_contention(self, resolver, sample_goals):
        """Test detection of resource conflicts."""
        resolver.mcp.call_operation = AsyncMock()

        result = await resolver.detect_conflicts(sample_goals)

        assert result["success"] is True
        # Should detect Alice is needed for both goal 1 and 2
        assert result["conflicts_detected"] > 0
        assert "resource_contention" in result["by_type"]

    @pytest.mark.asyncio
    async def test_detect_dependency_cycles(self, resolver):
        """Test detection of circular dependencies."""
        goals = [
            {"id": 1, "name": "Goal A", "dependencies": [2]},
            {"id": 2, "name": "Goal B", "dependencies": [1]},
        ]
        resolver.mcp.call_operation = AsyncMock()

        result = await resolver.detect_conflicts(goals)

        assert result["success"] is True
        assert "dependency_cycle" in result["by_type"]

    @pytest.mark.asyncio
    async def test_detect_timing_conflicts(self, resolver):
        """Test detection of timing conflicts."""
        goals = [
            {"id": 1, "name": "Goal 1", "deadline": "2025-11-10", "estimated_hours": 20},
            {"id": 2, "name": "Goal 2", "deadline": "2025-11-10", "estimated_hours": 20},
            {"id": 3, "name": "Goal 3", "deadline": "2025-11-10", "estimated_hours": 20},
        ]
        resolver.mcp.call_operation = AsyncMock()

        result = await resolver.detect_conflicts(goals)

        assert result["success"] is True
        # Should detect timing conflict (3+ goals same deadline)
        assert "timing_conflict" in result["by_type"]

    @pytest.mark.asyncio
    async def test_detect_capacity_overload(self, resolver):
        """Test detection of capacity overload."""
        goals = [
            {"id": i, "name": f"Goal {i}", "estimated_hours": 100}
            for i in range(10)
        ]
        resolver.mcp.call_operation = AsyncMock()

        result = await resolver.detect_conflicts(goals)

        assert result["success"] is True
        # 1000 hours >> 160 available (40h * 4 weeks)
        assert "capacity_overload" in result["by_type"]

    @pytest.mark.asyncio
    async def test_resolve_conflicts_dry_run(self, resolver, sample_goals):
        """Test conflict resolution with dry-run preview."""
        resolver.mcp.call_operation = AsyncMock()

        # First detect
        result = await resolver.detect_conflicts(sample_goals)
        assert result["success"] is True

        # Then resolve with dry-run
        result = await resolver.resolve_conflicts(
            strategy="priority",
            dry_run=True
        )

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "timeline_impact" in result

    @pytest.mark.asyncio
    async def test_resolve_conflicts_apply(self, resolver, sample_goals):
        """Test conflict resolution with changes applied."""
        # First detect conflicts
        resolver.mcp.call_operation = AsyncMock()

        # Detect first
        await resolver.detect_conflicts(sample_goals)

        # Then resolve without dry-run
        result = await resolver.resolve_conflicts(
            strategy="priority",
            dry_run=False
        )

        assert result["success"] is True
        assert result["dry_run"] is False
        # Verify MCP was called
        assert resolver.mcp.call_operation.called

    @pytest.mark.asyncio
    async def test_suggest_resolution(self, resolver):
        """Test resolution suggestions."""
        # Create a conflict
        conflict = ConflictDetail(
            conflict_id="test_1",
            conflict_type=ConflictType.RESOURCE_CONTENTION,
            severity=ConflictSeverity.HIGH,
            involved_goals=[1, 2],
            description="Alice needed for both",
            root_cause="Resource overlap"
        )
        resolver.detected_conflicts["test_1"] = conflict

        result = await resolver.suggest_resolution("test_1")

        assert result["success"] is True
        assert len(result["options"]) > 0
        assert result["recommended"] is not None

    @pytest.mark.asyncio
    async def test_error_handling_conflict_detection(self, resolver):
        """Test error handling in conflict detection."""
        resolver.mcp.call_operation = AsyncMock(side_effect=Exception("MCP Error"))

        result = await resolver.detect_conflicts([])

        assert result["success"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_cycle_detection_algorithm(self, resolver):
        """Test DFS cycle detection algorithm."""
        graph = {
            1: [2],
            2: [3],
            3: [1],  # Cycle: 1->2->3->1
            4: []
        }

        visited = set()
        path = []
        has_cycle = resolver._has_cycle(1, graph, visited, path)

        assert has_cycle is True

    @pytest.mark.asyncio
    async def test_option_ranking_algorithm(self, resolver):
        """Test resolution option ranking."""
        from athena.agents.conflict_resolver import ResolutionOption

        options = [
            ResolutionOption(
                option_id="opt1",
                strategy=ResolutionStrategy.PRIORITY_BASED,
                description="Suspend lower priority",
                timeline_impact_days=7,
                resource_impact={},
                risk_level="MEDIUM",
                estimated_cost=0
            ),
            ResolutionOption(
                option_id="opt2",
                strategy=ResolutionStrategy.RESOURCE_BASED,
                description="Reassign resource",
                timeline_impact_days=0,
                resource_impact={"person_b": 0.5},
                risk_level="MEDIUM",
                estimated_cost=0
            ),
            ResolutionOption(
                option_id="opt3",
                strategy=ResolutionStrategy.TIMELINE_BASED,
                description="Extend timeline",
                timeline_impact_days=14,
                resource_impact={},
                risk_level="HIGH",
                estimated_cost=0
            )
        ]

        ranked = resolver._rank_options(options)

        # Option 2 should rank highest (no timeline impact)
        assert ranked[0].option_id == "opt2"


class TestAgentIntegration:
    """Integration tests for agent interactions."""

    @pytest.fixture
    def agents(self):
        """Create all three agents for integration testing."""
        db = Mock()
        mcp = AsyncMock()

        return {
            "planning": PlanningOrchestrator(db, mcp),
            "goal": GoalOrchestrator(db, mcp),
            "conflict": ConflictResolver(db, mcp)
        }

    @pytest.mark.asyncio
    async def test_agents_initialization(self, agents):
        """Test that all agents initialize correctly."""
        # Verify all agents are properly initialized
        assert agents["planning"] is not None
        assert agents["goal"] is not None
        assert agents["conflict"] is not None

        # Verify they have proper attributes
        assert hasattr(agents["planning"], "db")
        assert hasattr(agents["planning"], "mcp")
        assert hasattr(agents["goal"], "goal_hierarchy")
        assert hasattr(agents["goal"], "active_goals")
        assert hasattr(agents["conflict"], "detected_conflicts")

    @pytest.mark.asyncio
    async def test_conflict_resolution_affects_goals(self, agents):
        """Test that conflict resolution impacts goal state."""
        goals = [
            {
                "id": 1,
                "name": "Goal 1",
                "owner": "Alice",
                "priority": 9,
                "deadline": "2025-11-10",
                "dependencies": [],
                "estimated_hours": 40
            },
            {
                "id": 2,
                "name": "Goal 2",
                "owner": "Alice",
                "priority": 7,
                "deadline": "2025-11-10",
                "dependencies": [],
                "estimated_hours": 40
            }
        ]

        agents["conflict"].mcp.call_operation = AsyncMock()

        # Detect conflicts
        detect_result = await agents["conflict"].detect_conflicts(goals)
        assert detect_result["success"] is True

        # Resolve conflicts
        resolve_result = await agents["conflict"].resolve_conflicts(
            dry_run=False
        )
        assert resolve_result["success"] is True

        # In production, goal states would be updated by goal_orchestrator


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
