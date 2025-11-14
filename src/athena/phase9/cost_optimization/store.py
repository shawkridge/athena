"""Database store for Phase 9.2: Cost Optimization Layer."""

from typing import Optional

from athena.core.database import Database
from athena.phase9.cost_optimization.models import (
    BudgetAllocation,
    CostAnomalyAlert,
    CostOptimization,
    ResourceRate,
    ROICalculation,
    TaskCost,
)


class CostOptimizationStore:
    """Store for cost tracking and optimization data."""

    def __init__(self, db: Database):
        """Initialize store with database connection."""
        self.db = db
    def _ensure_schema(self):
        """Create tables on first use."""
        cursor = self.db.get_cursor()

        # Resource rates table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS resource_rates (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL,
                resource_type TEXT NOT NULL,
                name TEXT NOT NULL,
                rate REAL,
                unit TEXT,
                currency TEXT,
                category TEXT,
                notes TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                FOREIGN KEY(organization_id) REFERENCES organizations(id)
            )
            """
        )

        # Task costs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_costs (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                labor_cost REAL,
                compute_cost REAL,
                tool_cost REAL,
                infrastructure_cost REAL,
                external_service_cost REAL,
                training_cost REAL,
                total_cost REAL,
                cost_breakdown TEXT,
                estimated INTEGER,
                created_at INTEGER,
                updated_at INTEGER,
                FOREIGN KEY(task_id) REFERENCES prospective_tasks(id),
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # Budget allocation table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_allocations (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                total_budget REAL,
                allocated_budget TEXT,
                spent_amount REAL,
                remaining_budget REAL,
                budget_utilization REAL,
                currency TEXT,
                fiscal_period TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # ROI calculations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS roi_calculations (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                total_cost REAL,
                expected_value REAL,
                roi_percentage REAL,
                roi_ratio REAL,
                payback_period_days REAL,
                value_per_dollar REAL,
                cost_efficiency TEXT,
                created_at INTEGER,
                FOREIGN KEY(task_id) REFERENCES prospective_tasks(id),
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # Cost optimizations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cost_optimizations (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                current_approach TEXT,
                suggested_approach TEXT,
                estimated_cost_current REAL,
                estimated_cost_suggested REAL,
                cost_saving REAL,
                cost_saving_percentage REAL,
                risk_level TEXT,
                implementation_effort TEXT,
                reasoning TEXT,
                created_at INTEGER,
                FOREIGN KEY(task_id) REFERENCES prospective_tasks(id),
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # Cost anomaly alerts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cost_anomaly_alerts (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                task_id INTEGER,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                current_cost REAL,
                expected_cost REAL,
                variance_percentage REAL,
                recommended_action TEXT,
                created_at INTEGER,
                resolved INTEGER,
                resolution_notes TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(task_id) REFERENCES prospective_tasks(id)
            )
            """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_resource_rates_org ON resource_rates(organization_id, resource_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_costs_task ON task_costs(task_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_costs_project ON task_costs(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_budget_allocations_project ON budget_allocations(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_roi_calculations_task ON roi_calculations(task_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cost_optimizations_task ON cost_optimizations(task_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cost_anomaly_alerts_project ON cost_anomaly_alerts(project_id, resolved)"
        )

        # commit handled by cursor context

    def create_resource_rate(self, rate: ResourceRate) -> ResourceRate:
        """Create a new resource rate."""
        from datetime import datetime

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())
        cursor.execute(
            """
            INSERT INTO resource_rates
            (organization_id, resource_type, name, rate, unit, currency, category, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rate.organization_id,
                rate.resource_type,
                rate.name,
                rate.rate,
                rate.unit,
                rate.currency,
                rate.category,
                rate.notes,
                now,
                now,
            ),
        )
        # commit handled by cursor context
        rate.id = cursor.lastrowid
        return rate

    def get_resource_rate(self, name: str, organization_id: int) -> Optional[ResourceRate]:
        """Get resource rate by name."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM resource_rates WHERE name = ? AND organization_id = ?",
            (name, organization_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_resource_rate_row(row)

    def list_resource_rates(self, organization_id: int) -> list[ResourceRate]:
        """List all resource rates for organization."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM resource_rates WHERE organization_id = ? ORDER BY resource_type, name",
            (organization_id,),
        )
        rows = cursor.fetchall()
        return [self._parse_resource_rate_row(row) for row in rows]

    def create_task_cost(self, cost: TaskCost) -> TaskCost:
        """Create task cost record."""
        import json
        from datetime import datetime

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())
        cursor.execute(
            """
            INSERT INTO task_costs
            (task_id, project_id, labor_cost, compute_cost, tool_cost, infrastructure_cost,
             external_service_cost, training_cost, total_cost, cost_breakdown, estimated, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cost.task_id,
                cost.project_id,
                cost.labor_cost,
                cost.compute_cost,
                cost.tool_cost,
                cost.infrastructure_cost,
                cost.external_service_cost,
                cost.training_cost,
                cost.total_cost,
                json.dumps(cost.cost_breakdown),
                1 if cost.estimated else 0,
                now,
                now,
            ),
        )
        # commit handled by cursor context
        cost.id = cursor.lastrowid
        return cost

    def get_task_cost(self, task_id: int) -> Optional[TaskCost]:
        """Get latest task cost."""
        import json

        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM task_costs WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_task_cost_row(row)

    def get_project_total_cost(self, project_id: int) -> float:
        """Get total cost for all tasks in project."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(total_cost), 0) FROM task_costs WHERE project_id = ?",
            (project_id,),
        )
        result = cursor.fetchone()
        return result[0] if result else 0.0

    def create_budget_allocation(self, budget: BudgetAllocation) -> BudgetAllocation:
        """Create budget allocation."""
        import json
        from datetime import datetime

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())
        cursor.execute(
            """
            INSERT INTO budget_allocations
            (project_id, total_budget, allocated_budget, spent_amount, remaining_budget,
             budget_utilization, currency, fiscal_period, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                budget.project_id,
                budget.total_budget,
                json.dumps(budget.allocated_budget),
                budget.spent_amount,
                budget.remaining_budget,
                budget.budget_utilization,
                budget.currency,
                budget.fiscal_period,
                now,
                now,
            ),
        )
        # commit handled by cursor context
        budget.id = cursor.lastrowid
        return budget

    def get_budget_allocation(self, project_id: int) -> Optional[BudgetAllocation]:
        """Get latest budget allocation for project."""
        import json

        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM budget_allocations WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_budget_allocation_row(row)

    def create_roi_calculation(self, roi: ROICalculation) -> ROICalculation:
        """Create ROI calculation."""
        from datetime import datetime

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO roi_calculations
            (task_id, project_id, total_cost, expected_value, roi_percentage, roi_ratio,
             payback_period_days, value_per_dollar, cost_efficiency, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                roi.task_id,
                roi.project_id,
                roi.total_cost,
                roi.expected_value,
                roi.roi_percentage,
                roi.roi_ratio,
                roi.payback_period_days,
                roi.value_per_dollar,
                roi.cost_efficiency,
                int(datetime.now().timestamp()),
            ),
        )
        # commit handled by cursor context
        roi.id = cursor.lastrowid
        return roi

    def get_roi_calculation(self, task_id: int) -> Optional[ROICalculation]:
        """Get ROI calculation for task."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM roi_calculations WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_roi_row(row)

    def create_cost_optimization(
        self, optimization: CostOptimization
    ) -> CostOptimization:
        """Create cost optimization suggestion."""
        from datetime import datetime

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO cost_optimizations
            (task_id, project_id, current_approach, suggested_approach,
             estimated_cost_current, estimated_cost_suggested, cost_saving,
             cost_saving_percentage, risk_level, implementation_effort, reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                optimization.task_id,
                optimization.project_id,
                optimization.current_approach,
                optimization.suggested_approach,
                optimization.estimated_cost_current,
                optimization.estimated_cost_suggested,
                optimization.cost_saving,
                optimization.cost_saving_percentage,
                optimization.risk_level,
                optimization.implementation_effort,
                optimization.reasoning,
                int(datetime.now().timestamp()),
            ),
        )
        # commit handled by cursor context
        optimization.id = cursor.lastrowid
        return optimization

    def list_cost_optimizations(
        self, project_id: int, min_saving: float = 0.0
    ) -> list[CostOptimization]:
        """List cost optimization suggestions."""
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM cost_optimizations
            WHERE project_id = ? AND cost_saving >= ?
            ORDER BY cost_saving DESC
            """,
            (project_id, min_saving),
        )
        rows = cursor.fetchall()
        return [self._parse_cost_optimization_row(row) for row in rows]

    def create_anomaly_alert(self, alert: CostAnomalyAlert) -> CostAnomalyAlert:
        """Create cost anomaly alert."""
        from datetime import datetime

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO cost_anomaly_alerts
            (project_id, task_id, alert_type, severity, message, current_cost,
             expected_cost, variance_percentage, recommended_action, created_at, resolved, resolution_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert.project_id,
                alert.task_id,
                alert.alert_type,
                alert.severity,
                alert.message,
                alert.current_cost,
                alert.expected_cost,
                alert.variance_percentage,
                alert.recommended_action,
                int(datetime.now().timestamp()),
                1 if alert.resolved else 0,
                alert.resolution_notes,
            ),
        )
        # commit handled by cursor context
        alert.id = cursor.lastrowid
        return alert

    def get_active_alerts(self, project_id: int) -> list[CostAnomalyAlert]:
        """Get active cost anomaly alerts."""
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM cost_anomaly_alerts
            WHERE project_id = ? AND resolved = 0
            ORDER BY created_at DESC
            """,
            (project_id,),
        )
        rows = cursor.fetchall()
        return [self._parse_anomaly_alert_row(row) for row in rows]

    # Helper parsing methods

    @staticmethod
    def _parse_resource_rate_row(row) -> ResourceRate:
        """Parse database row to ResourceRate."""
        return ResourceRate(
            id=row[0],
            organization_id=row[1],
            resource_type=row[2],
            name=row[3],
            rate=row[4],
            unit=row[5],
            currency=row[6],
            category=row[7],
            notes=row[8],
            created_at=row[9],
            updated_at=row[10],
        )

    @staticmethod
    def _parse_task_cost_row(row) -> TaskCost:
        """Parse database row to TaskCost."""
        import json

        return TaskCost(
            id=row[0],
            task_id=row[1],
            project_id=row[2],
            labor_cost=row[3],
            compute_cost=row[4],
            tool_cost=row[5],
            infrastructure_cost=row[6],
            external_service_cost=row[7],
            training_cost=row[8],
            total_cost=row[9],
            cost_breakdown=json.loads(row[10]) if row[10] else {},
            estimated=bool(row[11]),
            created_at=row[12],
            updated_at=row[13],
        )

    @staticmethod
    def _parse_budget_allocation_row(row) -> BudgetAllocation:
        """Parse database row to BudgetAllocation."""
        import json

        return BudgetAllocation(
            id=row[0],
            project_id=row[1],
            total_budget=row[2],
            allocated_budget=json.loads(row[3]) if row[3] else {},
            spent_amount=row[4],
            remaining_budget=row[5],
            budget_utilization=row[6],
            currency=row[7],
            fiscal_period=row[8],
            created_at=row[9],
            updated_at=row[10],
        )

    @staticmethod
    def _parse_roi_row(row) -> ROICalculation:
        """Parse database row to ROICalculation."""
        return ROICalculation(
            id=row[0],
            task_id=row[1],
            project_id=row[2],
            total_cost=row[3],
            expected_value=row[4],
            roi_percentage=row[5],
            roi_ratio=row[6],
            payback_period_days=row[7],
            value_per_dollar=row[8],
            cost_efficiency=row[9],
            created_at=row[10],
        )

    @staticmethod
    def _parse_cost_optimization_row(row) -> CostOptimization:
        """Parse database row to CostOptimization."""
        return CostOptimization(
            id=row[0],
            task_id=row[1],
            project_id=row[2],
            current_approach=row[3],
            suggested_approach=row[4],
            estimated_cost_current=row[5],
            estimated_cost_suggested=row[6],
            cost_saving=row[7],
            cost_saving_percentage=row[8],
            risk_level=row[9],
            implementation_effort=row[10],
            reasoning=row[11],
            created_at=row[12],
        )

    @staticmethod
    def _parse_anomaly_alert_row(row) -> CostAnomalyAlert:
        """Parse database row to CostAnomalyAlert."""
        return CostAnomalyAlert(
            id=row[0],
            project_id=row[1],
            task_id=row[2],
            alert_type=row[3],
            severity=row[4],
            message=row[5],
            current_cost=row[6],
            expected_cost=row[7],
            variance_percentage=row[8],
            recommended_action=row[9],
            created_at=row[10],
            resolved=bool(row[11]),
            resolution_notes=row[12],
        )
