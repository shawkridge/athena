"""Cost calculation and optimization engine for Phase 9.2."""

from typing import Optional

from athena.phase9.cost_optimization.models import (
    BudgetAllocation,
    CostAnomalyAlert,
    CostOptimization,
    ROICalculation,
    TaskCost,
)
from athena.phase9.cost_optimization.store import CostOptimizationStore


class CostCalculator:
    """Calculate costs for tasks and projects."""

    def __init__(self, store: CostOptimizationStore):
        """Initialize calculator with store."""
        self.store = store

    def calculate_task_cost(
        self,
        task_id: int,
        project_id: int,
        estimated_duration_minutes: float,
        assigned_team: list[str] = None,
        tools_required: list[str] = None,
        infrastructure_hours: float = 0.0,
        external_service_calls: int = 0,
        training_required: bool = False,
        organization_id: int = 1,  # Default organization
    ) -> TaskCost:
        """Calculate total cost for a task."""
        if assigned_team is None:
            assigned_team = []
        if tools_required is None:
            tools_required = []

        # Get resource rates
        rates = self.store.list_resource_rates(organization_id)
        rate_map = {r.name: r for r in rates}

        # Calculate labor cost
        labor_cost = 0.0
        labor_breakdown = {}
        for person in assigned_team:
            if person in rate_map:
                rate = rate_map[person]
                hours = estimated_duration_minutes / 60
                cost = hours * rate.rate
                labor_cost += cost
                labor_breakdown[person] = cost
            else:
                # Default to ~100/hour if no rate found
                hours = estimated_duration_minutes / 60
                cost = hours * 100
                labor_cost += cost
                labor_breakdown[person] = cost

        # Calculate tool costs
        tool_cost = 0.0
        tool_breakdown = {}
        for tool in tools_required:
            if tool in rate_map:
                rate = rate_map[tool]
                # Assume monthly costs are divided by estimated project duration
                cost = rate.rate / 20  # Simplified: monthly / 20 days
                tool_cost += cost
                tool_breakdown[tool] = cost

        # Calculate infrastructure cost
        infrastructure_cost = 0.0
        if infrastructure_hours > 0:
            # Look for AWS/compute rate
            compute_rate = next((r for r in rates if "compute" in r.name.lower()), None)
            if compute_rate:
                infrastructure_cost = infrastructure_hours * compute_rate.rate
            else:
                # Default to $0.50/hour
                infrastructure_cost = infrastructure_hours * 0.5

        # Calculate external service costs
        external_service_cost = 0.0
        if external_service_calls > 0:
            # Assume $0.01 per call (example)
            external_service_cost = external_service_calls * 0.01

        # Calculate training cost
        training_cost = 0.0
        if training_required:
            training_cost = 200.0  # Flat training cost

        # Total cost
        total_cost = (
            labor_cost + tool_cost + infrastructure_cost + external_service_cost + training_cost
        )

        cost_breakdown = {
            "labor": labor_breakdown,
            "tools": tool_breakdown,
            "infrastructure": infrastructure_cost,
            "external_services": external_service_cost,
            "training": training_cost,
        }

        task_cost = TaskCost(
            task_id=task_id,
            project_id=project_id,
            labor_cost=labor_cost,
            compute_cost=infrastructure_cost,
            tool_cost=tool_cost,
            external_service_cost=external_service_cost,
            training_cost=training_cost,
            total_cost=total_cost,
            cost_breakdown=cost_breakdown,
            estimated=True,
        )

        return self.store.create_task_cost(task_cost)

    def calculate_roi(
        self,
        task_id: int,
        project_id: int,
        total_cost: float,
        expected_value: float,
        annual_benefit: Optional[float] = None,
    ) -> ROICalculation:
        """Calculate ROI for a task."""
        # ROI percentage
        roi_percentage = ((expected_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        # ROI ratio
        roi_ratio = (expected_value / total_cost) if total_cost > 0 else 0

        # Payback period
        payback_period_days = None
        if annual_benefit and annual_benefit > 0:
            payback_period_days = (total_cost / annual_benefit) * 365

        # Value per dollar
        value_per_dollar = (expected_value / total_cost) if total_cost > 0 else 0

        # Cost efficiency
        if value_per_dollar >= 2.0:
            cost_efficiency = "high"
        elif value_per_dollar >= 1.0:
            cost_efficiency = "medium"
        else:
            cost_efficiency = "low"

        roi = ROICalculation(
            task_id=task_id,
            project_id=project_id,
            total_cost=total_cost,
            expected_value=expected_value,
            roi_percentage=roi_percentage,
            roi_ratio=roi_ratio,
            payback_period_days=payback_period_days,
            value_per_dollar=value_per_dollar,
            cost_efficiency=cost_efficiency,
        )

        return self.store.create_roi_calculation(roi)

    def suggest_cost_optimizations(
        self,
        task_id: int,
        project_id: int,
        current_cost: float,
        current_approach: str = "standard",
    ) -> list[CostOptimization]:
        """Suggest cost optimization approaches."""
        optimizations = []

        # Suggestion 1: Parallelization
        parallel_cost = current_cost * 0.85  # 15% savings from parallelization
        optimizations.append(
            CostOptimization(
                task_id=task_id,
                project_id=project_id,
                current_approach=current_approach,
                suggested_approach="parallelization",
                estimated_cost_current=current_cost,
                estimated_cost_suggested=parallel_cost,
                cost_saving=current_cost - parallel_cost,
                cost_saving_percentage=(
                    ((current_cost - parallel_cost) / current_cost * 100) if current_cost > 0 else 0
                ),
                risk_level="low",
                implementation_effort="easy",
                reasoning="Run independent tasks in parallel to reduce total duration",
            )
        )

        # Suggestion 2: Resource optimization
        resource_optimized_cost = current_cost * 0.75  # 25% savings
        optimizations.append(
            CostOptimization(
                task_id=task_id,
                project_id=project_id,
                current_approach=current_approach,
                suggested_approach="resource_optimization",
                estimated_cost_current=current_cost,
                estimated_cost_suggested=resource_optimized_cost,
                cost_saving=current_cost - resource_optimized_cost,
                cost_saving_percentage=(
                    ((current_cost - resource_optimized_cost) / current_cost * 100)
                    if current_cost > 0
                    else 0
                ),
                risk_level="medium",
                implementation_effort="moderate",
                reasoning="Use lower-cost resources or automate repetitive tasks",
            )
        )

        # Suggestion 3: Iterative approach
        iterative_cost = current_cost * 0.80  # 20% savings
        optimizations.append(
            CostOptimization(
                task_id=task_id,
                project_id=project_id,
                current_approach=current_approach,
                suggested_approach="iterative_delivery",
                estimated_cost_current=current_cost,
                estimated_cost_suggested=iterative_cost,
                cost_saving=current_cost - iterative_cost,
                cost_saving_percentage=(
                    ((current_cost - iterative_cost) / current_cost * 100)
                    if current_cost > 0
                    else 0
                ),
                risk_level="medium",
                implementation_effort="moderate",
                reasoning="Deliver in iterations, focusing on high-value items first",
            )
        )

        # Suggestion 4: Tool/Infrastructure optimization
        tool_optimized_cost = current_cost * 0.90  # 10% savings
        optimizations.append(
            CostOptimization(
                task_id=task_id,
                project_id=project_id,
                current_approach=current_approach,
                suggested_approach="tool_optimization",
                estimated_cost_current=current_cost,
                estimated_cost_suggested=tool_optimized_cost,
                cost_saving=current_cost - tool_optimized_cost,
                cost_saving_percentage=(
                    ((current_cost - tool_optimized_cost) / current_cost * 100)
                    if current_cost > 0
                    else 0
                ),
                risk_level="low",
                implementation_effort="easy",
                reasoning="Consolidate tools, negotiate better rates, or use open-source alternatives",
            )
        )

        # Save all optimizations
        saved_optimizations = []
        for opt in optimizations:
            saved_optimizations.append(self.store.create_cost_optimization(opt))

        # Return sorted by cost saving
        return sorted(saved_optimizations, key=lambda o: o.cost_saving, reverse=True)

    def detect_budget_anomalies(
        self,
        project_id: int,
        current_total_cost: float,
        budget_allocation: BudgetAllocation,
    ) -> list[CostAnomalyAlert]:
        """Detect unusual spending patterns."""
        alerts = []

        # Check if budget exceeded
        if current_total_cost > budget_allocation.total_budget:
            variance = (
                (current_total_cost - budget_allocation.total_budget)
                / budget_allocation.total_budget
                * 100
            )
            alerts.append(
                CostAnomalyAlert(
                    project_id=project_id,
                    alert_type="budget_exceeded",
                    severity="critical",
                    message=f"Project budget exceeded by ${current_total_cost - budget_allocation.total_budget:.2f}",
                    current_cost=current_total_cost,
                    expected_cost=budget_allocation.total_budget,
                    variance_percentage=variance,
                    recommended_action="Review scope, find cost optimizations, or request budget increase",
                )
            )
        # Check if budget utilization is high (>80%)
        elif current_total_cost > budget_allocation.total_budget * 0.8:
            variance = (current_total_cost / budget_allocation.total_budget) * 100 - 100
            alerts.append(
                CostAnomalyAlert(
                    project_id=project_id,
                    alert_type="high_utilization",
                    severity="warning",
                    message=f"Budget utilization at {(current_total_cost / budget_allocation.total_budget * 100):.0f}%",
                    current_cost=current_total_cost,
                    expected_cost=budget_allocation.total_budget,
                    variance_percentage=variance,
                    recommended_action="Monitor remaining budget closely, prepare cost optimization plan",
                )
            )

        # Check for unusual spending spike
        if current_total_cost > budget_allocation.total_budget * 0.3:
            # If >30% spent too quickly, flag as unusual
            alerts.append(
                CostAnomalyAlert(
                    project_id=project_id,
                    alert_type="unusual_spending",
                    severity="warning",
                    message=f"Rapid spending detected: {(current_total_cost / budget_allocation.total_budget * 100):.0f}% of budget spent",
                    current_cost=current_total_cost,
                    expected_cost=budget_allocation.total_budget * 0.3,
                    variance_percentage=(
                        (current_total_cost / (budget_allocation.total_budget * 0.3) - 1) * 100
                    ),
                    recommended_action="Review task priorities and cost efficiency",
                )
            )

        # Save alerts
        saved_alerts = []
        for alert in alerts:
            saved_alerts.append(self.store.create_anomaly_alert(alert))

        return saved_alerts

    def estimate_project_budget(
        self,
        project_id: int,
        estimated_tasks: int,
        avg_task_cost: float,
        contingency_percentage: float = 15.0,
    ) -> BudgetAllocation:
        """Estimate total budget for project."""
        base_cost = estimated_tasks * avg_task_cost
        contingency = base_cost * (contingency_percentage / 100)
        total_budget = base_cost + contingency

        budget = BudgetAllocation(
            project_id=project_id,
            total_budget=total_budget,
            allocated_budget={
                "labor": base_cost * 0.7,
                "tools": base_cost * 0.15,
                "infrastructure": base_cost * 0.10,
                "contingency": contingency,
            },
            spent_amount=0.0,
            remaining_budget=total_budget,
            budget_utilization=0.0,
        )

        return self.store.create_budget_allocation(budget)
