"""Data models for Phase 9.2: Cost Optimization Layer."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Types of resources that have costs."""

    LABOR = "labor"  # Person-hours
    COMPUTE = "compute"  # Cloud compute, servers
    TOOLS = "tools"  # Software licenses, SaaS
    INFRASTRUCTURE = "infrastructure"  # Hosting, databases
    EXTERNAL_SERVICES = "external_services"  # Third-party APIs
    TRAINING = "training"  # Learning/training costs


class CostCategory(str, Enum):
    """High-level cost categories."""

    DIRECT = "direct"  # Direct project costs
    INDIRECT = "indirect"  # Shared/overhead costs
    VARIABLE = "variable"  # Scale with output
    FIXED = "fixed"  # Fixed regardless of output


class ResourceRate(BaseModel):
    """Cost rate for a resource."""

    id: Optional[int] = None
    organization_id: int
    resource_type: ResourceType
    name: str  # e.g., "Senior Engineer", "AWS Compute", "GitHub Enterprise"
    rate: float  # Cost per unit
    unit: str = "hour"  # Unit of measure (hour, month, per-task, etc.)
    currency: str = "USD"
    category: CostCategory = CostCategory.DIRECT
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class TaskCost(BaseModel):
    """Cost breakdown for a task."""

    id: Optional[int] = None
    task_id: int
    project_id: int
    labor_cost: float = 0.0  # Total labor cost
    compute_cost: float = 0.0
    tool_cost: float = 0.0
    infrastructure_cost: float = 0.0
    external_service_cost: float = 0.0
    training_cost: float = 0.0
    total_cost: float = 0.0
    cost_breakdown: dict = Field(default_factory=dict)  # Detailed breakdown
    estimated: bool = True  # Is this estimated or actual?
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class BudgetAllocation(BaseModel):
    """Budget allocation for a project."""

    id: Optional[int] = None
    project_id: int
    total_budget: float
    allocated_budget: dict = Field(default_factory=dict)  # {resource_type: amount}
    spent_amount: float = 0.0
    remaining_budget: float = 0.0
    budget_utilization: float = 0.0  # Percentage (0-1)
    currency: str = "USD"
    fiscal_period: str = "2025-Q1"  # e.g., "2025-Q1", "2025"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ROICalculation(BaseModel):
    """ROI (Return on Investment) for a task/project."""

    id: Optional[int] = None
    task_id: int
    project_id: int
    total_cost: float  # Investment
    expected_value: float  # Expected return
    roi_percentage: float  # (value - cost) / cost * 100
    roi_ratio: float  # value / cost
    payback_period_days: Optional[float] = None
    value_per_dollar: float  # Expected value per dollar spent
    cost_efficiency: str  # "high", "medium", "low"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class CostOptimization(BaseModel):
    """Cost optimization suggestion for a task."""

    id: Optional[int] = None
    task_id: int
    project_id: int
    current_approach: str
    suggested_approach: str
    estimated_cost_current: float
    estimated_cost_suggested: float
    cost_saving: float
    cost_saving_percentage: float
    risk_level: str  # "none", "low", "medium", "high"
    implementation_effort: str  # "trivial", "easy", "moderate", "hard"
    reasoning: str
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class CostAnomalyAlert(BaseModel):
    """Alert for unusual spending patterns."""

    id: Optional[int] = None
    project_id: int
    task_id: Optional[int] = None
    alert_type: str  # "budget_exceeded", "unusual_spending", "cost_spike"
    severity: str = "warning"  # "info", "warning", "critical"
    message: str
    current_cost: float
    expected_cost: float
    variance_percentage: float
    recommended_action: str
    created_at: datetime = Field(default_factory=datetime.now)
    resolved: bool = False
    resolution_notes: Optional[str] = None

    class Config:
        use_enum_values = True
