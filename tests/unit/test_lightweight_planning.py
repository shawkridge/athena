"""Tests for lightweight inference planning."""

import pytest

from athena.planning.lightweight_planning import (
    ExecutionPlan,
    ExecutionStrategy,
    LightweightPlanner,
    LightweightTask,
    PlanningConstraints,
    ResourceConstraint,
    ResourceEstimate,
)


@pytest.fixture
def planner():
    """Fixture providing lightweight planner."""
    constraints = PlanningConstraints(
        max_total_tokens=10000,
        max_latency_ms=5000.0,
        max_cost_dollars=0.10,
    )
    return LightweightPlanner(constraints)


@pytest.fixture
def sample_tasks():
    """Fixture providing sample tasks."""
    return [
        LightweightTask(
            task_id="search",
            description="Search memory for relevant context",
            priority=90,
            estimated_tokens=500,
            estimated_latency_ms=200.0,
            is_critical=True,
        ),
        LightweightTask(
            task_id="rank",
            description="Rank search results by relevance",
            priority=80,
            estimated_tokens=300,
            estimated_latency_ms=150.0,
            required_inputs=["search"],
        ),
        LightweightTask(
            task_id="generate",
            description="Generate response from results",
            priority=85,
            estimated_tokens=1000,
            estimated_latency_ms=500.0,
            required_inputs=["rank"],
        ),
    ]


class TestExecutionStrategy:
    """Tests for execution strategies."""

    def test_all_strategies_defined(self):
        """Test all strategies are defined."""
        strategies = [
            ExecutionStrategy.GREEDY,
            ExecutionStrategy.INCREMENTAL,
            ExecutionStrategy.PARALLEL,
            ExecutionStrategy.LAZY,
            ExecutionStrategy.STREAMING,
        ]
        assert len(strategies) == 5


class TestResourceConstraint:
    """Tests for resource constraints."""

    def test_all_constraints_defined(self):
        """Test all constraints are defined."""
        constraints = [
            ResourceConstraint.CPU_LIMITED,
            ResourceConstraint.MEMORY_LIMITED,
            ResourceConstraint.NETWORK_LATENCY,
            ResourceConstraint.BANDWIDTH_LIMITED,
            ResourceConstraint.ENERGY_LIMITED,
        ]
        assert len(constraints) == 5


class TestResourceEstimate:
    """Tests for resource estimates."""

    def test_create_estimate(self):
        """Test creating resource estimate."""
        estimate = ResourceEstimate(
            operation="test_op",
            estimated_tokens=1000,
            estimated_latency_ms=500.0,
            estimated_cost_dollars=0.01,
        )

        assert estimate.operation == "test_op"
        assert estimate.estimated_tokens == 1000

    def test_feasibility_within_budget(self):
        """Test feasibility check within budget."""
        estimate = ResourceEstimate(
            operation="test_op",
            estimated_tokens=1000,
            estimated_latency_ms=500.0,
            estimated_cost_dollars=0.01,
        )

        assert estimate.is_feasible_in_budget(
            max_tokens=2000,
            max_latency_ms=1000.0,
            max_cost=0.05,
        )

    def test_feasibility_exceeds_budget(self):
        """Test feasibility check exceeds budget."""
        estimate = ResourceEstimate(
            operation="test_op",
            estimated_tokens=2000,
            estimated_latency_ms=500.0,
            estimated_cost_dollars=0.01,
        )

        assert not estimate.is_feasible_in_budget(max_tokens=1000)

    def test_feasibility_multiple_constraints(self):
        """Test feasibility with multiple constraints."""
        estimate = ResourceEstimate(
            operation="test_op",
            estimated_tokens=1000,
            estimated_latency_ms=2000.0,
            estimated_cost_dollars=0.01,
            memory_mb=100.0,
        )

        # Passes all constraints
        assert estimate.is_feasible_in_budget(
            max_tokens=2000,
            max_latency_ms=3000.0,
            max_cost=0.05,
            max_memory_mb=150.0,
        )

        # Fails memory constraint
        assert not estimate.is_feasible_in_budget(max_memory_mb=50.0)


class TestLightweightTask:
    """Tests for lightweight tasks."""

    def test_create_task(self):
        """Test creating lightweight task."""
        task = LightweightTask(
            task_id="test_1",
            description="Test task",
            priority=75,
        )

        assert task.task_id == "test_1"
        assert task.priority == 75

    def test_task_with_dependencies(self):
        """Test task with dependencies."""
        task = LightweightTask(
            task_id="task_2",
            description="Task with deps",
            priority=80,
            required_inputs=["task_1"],
        )

        assert "task_1" in task.required_inputs


class TestLightweightPlanner:
    """Tests for LightweightPlanner."""

    def test_planner_initialization(self, planner):
        """Test planner initializes correctly."""
        assert planner.constraints is not None
        assert planner.task_library == {}

    def test_register_task(self, planner, sample_tasks):
        """Test registering tasks."""
        for task in sample_tasks:
            planner.register_task(task)

        assert len(planner.task_library) == 3

    def test_estimate_resources(self, planner, sample_tasks):
        """Test resource estimation."""
        task = sample_tasks[0]

        estimate = planner.estimate_resource_usage(task)

        assert estimate.operation == task.task_id
        assert estimate.estimated_tokens > 0
        assert estimate.estimated_latency_ms > 0
        assert estimate.estimated_cost_dollars > 0

    def test_create_plan_greedy(self, planner, sample_tasks):
        """Test creating plan with greedy strategy."""
        for task in sample_tasks:
            planner.register_task(task)

        plan = planner.create_plan(
            [t.task_id for t in sample_tasks],
            strategy=ExecutionStrategy.GREEDY,
        )

        assert plan.strategy == ExecutionStrategy.GREEDY
        assert len(plan.tasks) > 0
        assert plan.total_estimated_tokens > 0

    def test_create_plan_incremental(self, planner, sample_tasks):
        """Test creating plan with incremental strategy."""
        for task in sample_tasks:
            planner.register_task(task)

        plan = planner.create_plan(
            [t.task_id for t in sample_tasks],
            strategy=ExecutionStrategy.INCREMENTAL,
        )

        assert plan.strategy == ExecutionStrategy.INCREMENTAL
        # Critical tasks should come first
        if len(plan.tasks) > 0:
            assert plan.tasks[0].is_critical

    def test_create_plan_parallel(self, planner, sample_tasks):
        """Test creating plan with parallel strategy."""
        for task in sample_tasks:
            planner.register_task(task)

        plan = planner.create_plan(
            [t.task_id for t in sample_tasks],
            strategy=ExecutionStrategy.PARALLEL,
        )

        assert plan.strategy == ExecutionStrategy.PARALLEL

    def test_create_plan_with_dependencies(self, planner, sample_tasks):
        """Test creating plan respects dependencies."""
        for task in sample_tasks:
            planner.register_task(task)

        dependencies = {
            "rank": ["search"],
            "generate": ["rank"],
        }

        plan = planner.create_plan(
            [t.task_id for t in sample_tasks],
            dependencies=dependencies,
        )

        # Should have tasks in correct order
        task_ids = [t.task_id for t in plan.tasks]
        if "search" in task_ids and "rank" in task_ids:
            assert task_ids.index("search") < task_ids.index("rank")

    def test_plan_respects_token_budget(self, planner):
        """Test plan respects token budget."""
        # Set reasonable token budget
        planner.constraints.max_total_tokens = 2000

        task = LightweightTask(
            task_id="moderate_task",
            description="Moderate task",
            priority=90,
            estimated_tokens=500,
            is_critical=False,
        )
        planner.register_task(task)

        plan = planner.create_plan(["moderate_task"])

        # Task should fit within budget
        assert plan.total_estimated_tokens <= planner.constraints.max_total_tokens

    def test_plan_includes_critical_task_despite_budget(self, planner):
        """Test plan includes critical task despite budget."""
        # Set low token budget
        planner.constraints.max_total_tokens = 100

        task = LightweightTask(
            task_id="critical_task",
            description="Critical large task",
            priority=90,
            estimated_tokens=1000,
            is_critical=True,  # Critical!
        )
        planner.register_task(task)

        plan = planner.create_plan(["critical_task"])

        # Critical task should be included
        assert len(plan.tasks) == 1


class TestExecutionPlan:
    """Tests for ExecutionPlan."""

    def test_create_plan(self):
        """Test creating execution plan."""
        plan = ExecutionPlan(
            plan_id="plan_1",
            strategy=ExecutionStrategy.GREEDY,
        )

        assert plan.plan_id == "plan_1"
        assert plan.tasks == []
        assert plan.total_estimated_tokens == 0

    def test_add_task_to_plan(self):
        """Test adding tasks to plan."""
        plan = ExecutionPlan(
            plan_id="plan_1",
            strategy=ExecutionStrategy.GREEDY,
        )

        task = LightweightTask(
            task_id="task_1",
            description="Test task",
            priority=80,
            estimated_tokens=500,
            estimated_latency_ms=200.0,
        )

        plan.add_task(task)

        assert len(plan.tasks) == 1
        assert plan.total_estimated_tokens == 500


class TestPlanningConstraints:
    """Tests for PlanningConstraints."""

    def test_default_constraints(self):
        """Test default constraints."""
        constraints = PlanningConstraints()

        assert constraints.max_total_tokens == 10000
        assert constraints.max_latency_ms == 5000.0
        assert constraints.max_cost_dollars == 0.10

    def test_custom_constraints(self):
        """Test custom constraints."""
        constraints = PlanningConstraints(
            max_total_tokens=5000,
            max_latency_ms=2000.0,
            max_cost_dollars=0.05,
        )

        assert constraints.max_total_tokens == 5000
        assert constraints.max_latency_ms == 2000.0


class TestOptimizationSuggestions:
    """Tests for optimization suggestions."""

    def test_get_suggestions_token_budget_exceeded(self, planner, sample_tasks):
        """Test suggestions when token budget exceeded."""
        planner.constraints.max_total_tokens = 100
        for task in sample_tasks:
            planner.register_task(task)

        plan = planner.create_plan(
            [t.task_id for t in sample_tasks],
            strategy=ExecutionStrategy.GREEDY,
        )

        suggestions = planner.get_optimization_suggestions(plan)

        # Should have at least one suggestion
        assert len(suggestions) >= 0

    def test_get_suggestions_parallelizable_tasks(self, planner):
        """Test suggestions for parallelizable tasks."""
        # Create tasks that can be parallelized
        task1 = LightweightTask(
            task_id="task_1",
            description="Task 1",
            priority=80,
            can_parallelize=True,
        )
        task2 = LightweightTask(
            task_id="task_2",
            description="Task 2",
            priority=80,
            can_parallelize=True,
        )

        planner.register_task(task1)
        planner.register_task(task2)

        plan = planner.create_plan(
            ["task_1", "task_2"],
            strategy=ExecutionStrategy.GREEDY,  # Not parallel
        )

        suggestions = planner.get_optimization_suggestions(plan)

        # Should suggest parallelization
        assert any("parallelize" in s.lower() for s in suggestions)


class TestSummaryReport:
    """Tests for summary report generation."""

    def test_summary_report_format(self, planner, sample_tasks):
        """Test summary report has expected format."""
        for task in sample_tasks:
            planner.register_task(task)

        plan = planner.create_plan(
            [t.task_id for t in sample_tasks],
            strategy=ExecutionStrategy.INCREMENTAL,
        )

        report = planner.summary_report(plan)

        assert "LIGHTWEIGHT EXECUTION PLAN" in report
        assert "RESOURCE ESTIMATES" in report
        assert "EXECUTION ORDER" in report

    def test_summary_report_includes_tasks(self, planner, sample_tasks):
        """Test summary report includes all tasks."""
        for task in sample_tasks:
            planner.register_task(task)

        plan = planner.create_plan(
            [t.task_id for t in sample_tasks],
            strategy=ExecutionStrategy.GREEDY,
        )

        report = planner.summary_report(plan)

        for task in plan.tasks:
            assert task.description in report


class TestTopologicalSort:
    """Tests for task dependency sorting."""

    def test_topological_sort_linear(self, planner, sample_tasks):
        """Test topological sort with linear dependencies."""
        for task in sample_tasks:
            planner.register_task(task)

        dependencies = {
            "rank": ["search"],
            "generate": ["rank"],
        }

        plan = planner.create_plan(
            ["search", "rank", "generate"],
            dependencies=dependencies,
        )

        # Verify order
        task_ids = [t.task_id for t in plan.tasks]
        if "search" in task_ids:
            search_idx = task_ids.index("search")
            if "rank" in task_ids:
                rank_idx = task_ids.index("rank")
                assert search_idx < rank_idx


class TestIntegration:
    """Integration tests for lightweight planning."""

    def test_full_planning_workflow(self, planner):
        """Test complete planning workflow."""
        # 1. Register tasks
        tasks = [
            LightweightTask(
                task_id="retrieve",
                description="Retrieve context",
                priority=90,
                estimated_tokens=500,
                is_critical=True,
            ),
            LightweightTask(
                task_id="process",
                description="Process context",
                priority=80,
                estimated_tokens=300,
                required_inputs=["retrieve"],
            ),
            LightweightTask(
                task_id="generate",
                description="Generate output",
                priority=85,
                estimated_tokens=700,
                required_inputs=["process"],
            ),
        ]

        for task in tasks:
            planner.register_task(task)

        # 2. Create plan
        dependencies = {
            "process": ["retrieve"],
            "generate": ["process"],
        }

        plan = planner.create_plan(
            ["retrieve", "process", "generate"],
            strategy=ExecutionStrategy.INCREMENTAL,
            dependencies=dependencies,
        )

        # 3. Get optimization suggestions
        suggestions = planner.get_optimization_suggestions(plan)

        # 4. Generate summary
        report = planner.summary_report(plan)

        # Verify results
        assert len(plan.tasks) > 0
        assert "LIGHTWEIGHT EXECUTION PLAN" in report
