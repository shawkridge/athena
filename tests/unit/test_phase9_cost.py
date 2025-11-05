"""Unit tests for Phase 9.2: Cost Optimization Layer."""

import pytest

from athena.core.database import Database
from athena.phase9.cost_optimization import (
    BudgetAllocation,
    CostCalculator,
    CostOptimizationStore,
    ResourceRate,
    ResourceType,
    ROICalculation,
    TaskCost,
)


@pytest.fixture
def cost_store(tmp_path):
    """Create cost store for testing."""
    db = Database(str(tmp_path / "test_cost.db"))
    return CostOptimizationStore(db)


@pytest.fixture
def calculator(cost_store):
    """Create calculator for testing."""
    return CostCalculator(cost_store)


class TestResourceRate:
    """Test ResourceRate functionality."""

    def test_create_resource_rate(self, cost_store):
        """Test creating resource rate."""
        rate = ResourceRate(
            organization_id=1,
            resource_type=ResourceType.LABOR,
            name="Senior Engineer",
            rate=150.0,
            unit="hour",
            currency="USD",
        )

        saved = cost_store.create_resource_rate(rate)
        assert saved.id is not None
        assert saved.name == "Senior Engineer"
        assert saved.rate == 150.0

    def test_get_resource_rate(self, cost_store):
        """Test retrieving resource rate."""
        rate = ResourceRate(
            organization_id=1,
            resource_type=ResourceType.LABOR,
            name="Engineer",
            rate=100.0,
        )
        cost_store.create_resource_rate(rate)

        retrieved = cost_store.get_resource_rate("Engineer", 1)
        assert retrieved is not None
        assert retrieved.rate == 100.0

    def test_list_resource_rates(self, cost_store):
        """Test listing resource rates."""
        for i in range(3):
            rate = ResourceRate(
                organization_id=1,
                resource_type=ResourceType.LABOR,
                name=f"Engineer_{i}",
                rate=100.0 + i * 10,
            )
            cost_store.create_resource_rate(rate)

        rates = cost_store.list_resource_rates(1)
        assert len(rates) == 3


class TestCostCalculator:
    """Test CostCalculator functionality."""

    def test_calculate_task_cost_basic(self, calculator, cost_store):
        """Test basic task cost calculation."""
        # Create resource rates first
        rate = ResourceRate(
            organization_id=1,
            resource_type=ResourceType.LABOR,
            name="Engineer",
            rate=100.0,
        )
        cost_store.create_resource_rate(rate)

        # Calculate cost
        cost = calculator.calculate_task_cost(
            task_id=1,
            project_id=1,
            estimated_duration_minutes=480,  # 8 hours
            assigned_team=["Engineer"],
            tools_required=[],
            organization_id=1,
        )

        assert cost.task_id == 1
        assert cost.project_id == 1
        assert cost.labor_cost == 800.0  # 8 hours * $100/hour
        assert cost.total_cost == 800.0

    def test_calculate_task_cost_with_tools(self, calculator, cost_store):
        """Test task cost with tools."""
        # Create rates
        for rate_config in [
            (ResourceType.LABOR, "Engineer", 100.0),
            (ResourceType.TOOLS, "GitHub Enterprise", 50.0),  # Monthly
        ]:
            rate = ResourceRate(
                organization_id=1,
                resource_type=rate_config[0],
                name=rate_config[1],
                rate=rate_config[2],
            )
            cost_store.create_resource_rate(rate)

        cost = calculator.calculate_task_cost(
            task_id=1,
            project_id=1,
            estimated_duration_minutes=480,
            assigned_team=["Engineer"],
            tools_required=["GitHub Enterprise"],
            organization_id=1,
        )

        assert cost.labor_cost == 800.0  # 8 hours * $100
        assert cost.tool_cost > 0  # Should include tool cost
        assert cost.total_cost > 800.0

    def test_calculate_task_cost_with_infrastructure(self, calculator, cost_store):
        """Test task cost with infrastructure."""
        cost = calculator.calculate_task_cost(
            task_id=1,
            project_id=1,
            estimated_duration_minutes=480,
            assigned_team=[],
            infrastructure_hours=10.0,
            organization_id=1,
        )

        # Infrastructure cost is stored in compute_cost field
        assert cost.compute_cost > 0
        assert cost.total_cost == cost.compute_cost

    def test_calculate_roi_positive(self, calculator):
        """Test ROI calculation with positive return."""
        roi = calculator.calculate_roi(
            task_id=1,
            project_id=1,
            total_cost=1000.0,
            expected_value=3000.0,
            annual_benefit=500.0,
        )

        assert roi.roi_percentage == 200.0  # (3000 - 1000) / 1000 * 100
        assert roi.roi_ratio == 3.0  # 3000 / 1000
        assert roi.value_per_dollar == 3.0
        assert roi.cost_efficiency == "high"

    def test_calculate_roi_break_even(self, calculator):
        """Test ROI at break-even."""
        roi = calculator.calculate_roi(
            task_id=1,
            project_id=1,
            total_cost=1000.0,
            expected_value=1000.0,
        )

        assert roi.roi_percentage == 0.0
        assert roi.roi_ratio == 1.0
        assert roi.value_per_dollar == 1.0
        assert roi.cost_efficiency == "medium"

    def test_calculate_roi_negative(self, calculator):
        """Test ROI calculation with negative return."""
        roi = calculator.calculate_roi(
            task_id=1,
            project_id=1,
            total_cost=1000.0,
            expected_value=500.0,
        )

        assert roi.roi_percentage == -50.0
        assert roi.roi_ratio == 0.5
        assert roi.value_per_dollar == 0.5
        assert roi.cost_efficiency == "low"

    def test_suggest_cost_optimizations(self, calculator):
        """Test cost optimization suggestions."""
        optimizations = calculator.suggest_cost_optimizations(
            task_id=1,
            project_id=1,
            current_cost=1000.0,
            current_approach="standard",
        )

        assert len(optimizations) >= 3  # At least 3 suggestions
        assert all(o.task_id == 1 for o in optimizations)
        assert all(o.cost_saving > 0 for o in optimizations)
        assert all(o.cost_saving_percentage > 0 for o in optimizations)
        # Should be sorted by saving amount
        assert optimizations[0].cost_saving >= optimizations[-1].cost_saving

    def test_detect_budget_exceeded(self, calculator, cost_store):
        """Test detection of budget exceeding."""
        budget = BudgetAllocation(
            project_id=1,
            total_budget=1000.0,
            allocated_budget={"labor": 700, "tools": 200, "infrastructure": 100},
            spent_amount=0.0,
            remaining_budget=1000.0,
        )
        cost_store.create_budget_allocation(budget)

        # Current spend exceeds budget
        alerts = calculator.detect_budget_anomalies(
            project_id=1,
            current_total_cost=1200.0,
            budget_allocation=budget,
        )

        assert len(alerts) > 0
        assert any(a.alert_type == "budget_exceeded" for a in alerts)

    def test_detect_high_utilization(self, calculator, cost_store):
        """Test detection of high budget utilization."""
        budget = BudgetAllocation(
            project_id=1,
            total_budget=1000.0,
        )
        cost_store.create_budget_allocation(budget)

        alerts = calculator.detect_budget_anomalies(
            project_id=1,
            current_total_cost=850.0,  # 85% utilization
            budget_allocation=budget,
        )

        assert len(alerts) > 0
        assert any(a.alert_type == "high_utilization" for a in alerts)

    def test_estimate_project_budget(self, calculator):
        """Test project budget estimation."""
        budget = calculator.estimate_project_budget(
            project_id=1,
            estimated_tasks=10,
            avg_task_cost=100.0,
            contingency_percentage=20.0,
        )

        assert budget.project_id == 1
        assert budget.total_budget == 1200.0  # 10 * 100 + 20% contingency
        assert budget.allocated_budget["labor"] > 0
        assert budget.allocated_budget["contingency"] == 200.0


class TestTaskCost:
    """Test TaskCost functionality."""

    def test_create_task_cost(self, cost_store):
        """Test creating task cost record."""
        cost = TaskCost(
            task_id=1,
            project_id=1,
            labor_cost=800.0,
            compute_cost=50.0,
            tool_cost=25.0,
            infrastructure_cost=100.0,
            external_service_cost=10.0,
            training_cost=200.0,
            total_cost=1185.0,
            cost_breakdown={
                "labor": {"Engineer": 800.0},
                "tools": {"GitHub": 25.0},
            },
            estimated=True,
        )

        saved = cost_store.create_task_cost(cost)
        assert saved.id is not None
        assert saved.total_cost == 1185.0

    def test_get_task_cost(self, cost_store):
        """Test retrieving task cost."""
        cost1 = TaskCost(
            task_id=1,
            project_id=1,
            total_cost=1000.0,
            estimated=True,
        )
        cost_store.create_task_cost(cost1)

        retrieved = cost_store.get_task_cost(1)
        assert retrieved is not None
        assert retrieved.total_cost == 1000.0

    def test_get_project_total_cost(self, cost_store):
        """Test calculating project total cost."""
        for i in range(3):
            cost = TaskCost(
                task_id=i + 1,
                project_id=1,
                total_cost=100.0 + i * 50,
            )
            cost_store.create_task_cost(cost)

        total = cost_store.get_project_total_cost(1)
        assert total == 100.0 + 150.0 + 200.0  # 450.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
