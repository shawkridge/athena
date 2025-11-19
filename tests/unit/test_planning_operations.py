"""Unit tests for planning memory operations."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from athena.planning.operations import PlanningOperations

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return MagicMock()


@pytest.fixture
def mock_planning_store():
    """Create a mock planning store with intelligent mocking."""
    # Track plans in memory
    plans = {}
    next_id = [1]

    async def store_plan_impl(plan: Dict[str, Any]):
        """Store a plan."""
        plan_id = next_id[0]
        next_id[0] += 1

        plan_obj = {
            "id": str(plan_id),
            "goal": plan.get("goal"),
            "description": plan.get("description", ""),
            "depth": plan.get("depth", 3),
            "tags": plan.get("tags", []),
            "steps": plan.get("steps", []),
            "assumptions": plan.get("assumptions", []),
            "risks": plan.get("risks", []),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        plans[str(plan_id)] = plan_obj
        return plan_obj

    async def get_plan_impl(plan_id: str):
        """Get a plan by ID."""
        plan_id_str = str(plan_id)
        return plans.get(plan_id_str)

    async def list_plans_impl(limit: int = 20, status: str = None):
        """List plans."""
        result = list(plans.values())
        if status:
            result = [p for p in result if p.get("status") == status]
        return result[:limit]

    async def validate_plan_impl(plan_id: str):
        """Validate a plan."""
        plan = await get_plan_impl(plan_id)
        if not plan:
            return {"valid": False, "error": "Plan not found"}

        # Mock validation results
        return {
            "valid": True,
            "plan_id": plan_id,
            "issues": [],
            "confidence": 0.85,
            "validation_type": "formal_verification",
        }

    async def estimate_effort_impl(plan_id: str):
        """Estimate effort for a plan."""
        plan = await get_plan_impl(plan_id)
        if not plan:
            return {"estimate": 0, "error": "Plan not found"}

        # Mock effort estimation based on depth and steps
        base_effort = plan.get("depth", 1) * 10
        step_effort = len(plan.get("steps", [])) * 5
        total = base_effort + step_effort

        return {
            "plan_id": plan_id,
            "total_effort_units": total,
            "effort_by_phase": [total // (plan.get("depth", 1) or 1)] * max(1, plan.get("depth", 1)),
            "confidence": 0.75,
        }

    async def update_plan_status_impl(plan_id: str, status: str):
        """Update plan status."""
        plan_id_str = str(plan_id)
        if plan_id_str not in plans:
            return False

        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if status not in valid_statuses:
            return False

        plans[plan_id_str]["status"] = status
        plans[plan_id_str]["updated_at"] = datetime.now().isoformat()
        return True

    store = MagicMock()
    store.store_plan = AsyncMock(side_effect=store_plan_impl)
    store.get_plan = AsyncMock(side_effect=get_plan_impl)
    store.list_plans = AsyncMock(side_effect=list_plans_impl)
    store.validate_plan = AsyncMock(side_effect=validate_plan_impl)
    store.estimate_effort = AsyncMock(side_effect=estimate_effort_impl)
    store.update_plan_status = AsyncMock(side_effect=update_plan_status_impl)
    return store


@pytest.fixture
def operations(mock_db, mock_planning_store):
    """Create test operations instance with mocked store."""
    ops = PlanningOperations(mock_db, mock_planning_store)
    return ops


class TestPlanningOperations:
    """Test planning memory operations."""

    async def test_create_plan_minimal(self, operations: PlanningOperations):
        """Test creating a plan with minimal parameters."""
        plan = await operations.create_plan("Implement feature X")

        assert plan is not None
        assert isinstance(plan, dict)
        assert plan["goal"] == "Implement feature X"
        assert plan["depth"] == 3  # Default depth
        assert "id" in plan

    async def test_create_plan_full(self, operations: PlanningOperations):
        """Test creating a plan with all parameters."""
        plan = await operations.create_plan(
            goal="Implement feature X",
            description="A complex feature requiring careful planning",
            depth=4,
            tags=["feature", "backend", "critical"],
        )

        assert plan["goal"] == "Implement feature X"
        assert plan["description"] == "A complex feature requiring careful planning"
        assert plan["depth"] == 4
        assert "feature" in plan["tags"]
        assert plan["status"] == "pending"

    async def test_create_plan_invalid_goal(self, operations: PlanningOperations):
        """Test creating plan with empty goal."""
        with pytest.raises(ValueError):
            await operations.create_plan("")

    async def test_create_plan_depth_clamping(self, operations: PlanningOperations):
        """Test that planning depth is clamped to 1-5 range."""
        # Test too high
        plan_high = await operations.create_plan("Test", depth=10)
        assert plan_high["depth"] == 5

        # Test too low
        plan_low = await operations.create_plan("Test", depth=0)
        assert plan_low["depth"] == 1

    async def test_create_multiple_plans(self, operations: PlanningOperations):
        """Test creating multiple plans."""
        plan1 = await operations.create_plan("Feature 1")
        plan2 = await operations.create_plan("Feature 2")
        plan3 = await operations.create_plan("Feature 3")

        assert plan1["id"] != plan2["id"]
        assert plan2["id"] != plan3["id"]
        assert plan1["goal"] != plan2["goal"]

    async def test_get_plan_success(self, operations: PlanningOperations):
        """Test getting a plan by ID."""
        created = await operations.create_plan("Test Plan")
        retrieved = await operations.get_plan(created["id"])

        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["goal"] == "Test Plan"

    async def test_get_plan_nonexistent(self, operations: PlanningOperations):
        """Test getting nonexistent plan."""
        result = await operations.get_plan("99999")
        assert result is None

    async def test_get_plan_string_id(self, operations: PlanningOperations):
        """Test getting plan with string ID."""
        created = await operations.create_plan("String ID Test")
        retrieved = await operations.get_plan(str(created["id"]))

        assert retrieved is not None
        assert retrieved["id"] == created["id"]

    async def test_list_plans_default(self, operations: PlanningOperations):
        """Test listing plans with defaults."""
        # Create some plans
        for i in range(3):
            await operations.create_plan(f"Plan {i}")

        plans = await operations.list_plans()

        assert plans is not None
        assert isinstance(plans, list)
        assert len(plans) >= 3

    async def test_list_plans_with_limit(self, operations: PlanningOperations):
        """Test listing plans with limit."""
        for i in range(10):
            await operations.create_plan(f"Plan {i}")

        plans = await operations.list_plans(limit=5)

        assert len(plans) <= 5

    async def test_list_plans_by_status(self, operations: PlanningOperations):
        """Test listing plans filtered by status."""
        # Create plans
        plan1 = await operations.create_plan("Plan 1")
        plan2 = await operations.create_plan("Plan 2")
        plan3 = await operations.create_plan("Plan 3")

        # Update some statuses
        await operations.update_plan_status(plan1["id"], "in_progress")
        await operations.update_plan_status(plan2["id"], "completed")

        # List by status
        in_progress = await operations.list_plans(status="in_progress")

        assert len(in_progress) >= 1
        assert any(p["id"] == plan1["id"] for p in in_progress)

    async def test_list_plans_empty(self, operations: PlanningOperations):
        """Test listing when no plans exist."""
        # Clear by using a store that returns empty
        plans = await operations.list_plans(limit=100)
        # Should handle gracefully
        assert isinstance(plans, list)

    async def test_validate_plan_success(self, operations: PlanningOperations):
        """Test validating a plan."""
        plan = await operations.create_plan("Plan to validate")
        validation = await operations.validate_plan(plan["id"])

        assert validation is not None
        assert isinstance(validation, dict)
        assert "valid" in validation

    async def test_validate_plan_nonexistent(self, operations: PlanningOperations):
        """Test validating nonexistent plan."""
        validation = await operations.validate_plan("99999")

        assert validation is not None
        assert validation.get("valid") == False

    async def test_validate_plan_structure(self, operations: PlanningOperations):
        """Test validation result structure."""
        plan = await operations.create_plan("Complex Plan", depth=4)
        validation = await operations.validate_plan(plan["id"])

        assert "valid" in validation
        assert "plan_id" in validation or "error" in validation

    async def test_estimate_effort_success(self, operations: PlanningOperations):
        """Test estimating effort for a plan."""
        plan = await operations.create_plan("Effortful Plan", depth=3)
        estimate = await operations.estimate_effort(plan["id"])

        assert estimate is not None
        assert isinstance(estimate, dict)
        assert "total_effort_units" in estimate or "error" in estimate

    async def test_estimate_effort_nonexistent(self, operations: PlanningOperations):
        """Test estimating effort for nonexistent plan."""
        estimate = await operations.estimate_effort("99999")

        assert "error" in estimate or estimate.get("total_effort_units", 0) == 0

    async def test_estimate_effort_depth_correlation(self, operations: PlanningOperations):
        """Test that effort increases with planning depth."""
        plan_shallow = await operations.create_plan("Shallow", depth=1)
        plan_deep = await operations.create_plan("Deep", depth=5)

        effort_shallow = await operations.estimate_effort(plan_shallow["id"])
        effort_deep = await operations.estimate_effort(plan_deep["id"])

        shallow_units = effort_shallow.get("total_effort_units", 0)
        deep_units = effort_deep.get("total_effort_units", 0)

        assert deep_units >= shallow_units

    async def test_update_plan_status_pending_to_in_progress(
        self, operations: PlanningOperations
    ):
        """Test updating plan status to in_progress."""
        plan = await operations.create_plan("Status Test")
        assert plan["status"] == "pending"

        result = await operations.update_plan_status(plan["id"], "in_progress")
        assert result == True

        updated = await operations.get_plan(plan["id"])
        assert updated["status"] == "in_progress"

    async def test_update_plan_status_to_completed(self, operations: PlanningOperations):
        """Test completing a plan."""
        plan = await operations.create_plan("Complete Test")
        await operations.update_plan_status(plan["id"], "in_progress")
        result = await operations.update_plan_status(plan["id"], "completed")

        assert result == True
        updated = await operations.get_plan(plan["id"])
        assert updated["status"] == "completed"

    async def test_update_plan_status_to_cancelled(self, operations: PlanningOperations):
        """Test cancelling a plan."""
        plan = await operations.create_plan("Cancel Test")
        result = await operations.update_plan_status(plan["id"], "cancelled")

        assert result == True

    async def test_update_plan_status_invalid_status(self, operations: PlanningOperations):
        """Test updating with invalid status."""
        plan = await operations.create_plan("Invalid Status Test")
        result = await operations.update_plan_status(plan["id"], "invalid_status")

        # Should return False for invalid status
        assert result == False

    async def test_update_plan_status_nonexistent(self, operations: PlanningOperations):
        """Test updating nonexistent plan."""
        result = await operations.update_plan_status("99999", "completed")
        assert result == False

    async def test_get_statistics_with_plans(self, operations: PlanningOperations):
        """Test getting statistics with existing plans."""
        for i in range(3):
            await operations.create_plan(f"Plan {i}", depth=2 + i)

        stats = await operations.get_statistics()

        assert stats is not None
        assert isinstance(stats, dict)
        assert "total_plans" in stats
        assert stats["total_plans"] >= 3

    async def test_get_statistics_structure(self, operations: PlanningOperations):
        """Test statistics structure."""
        plan = await operations.create_plan("Stats Test", depth=3)
        stats = await operations.get_statistics()

        assert "total_plans" in stats
        assert "total_steps" in stats
        assert "avg_depth" in stats
        assert "by_status" in stats
        assert "pending" in stats["by_status"]

    async def test_get_statistics_empty(self, operations: PlanningOperations):
        """Test statistics when no plans exist."""
        stats = await operations.get_statistics()

        assert stats is not None
        assert isinstance(stats, dict)
        assert "total_plans" in stats

    async def test_get_statistics_average_depth(self, operations: PlanningOperations):
        """Test that average depth is calculated correctly."""
        await operations.create_plan("Plan 1", depth=1)
        await operations.create_plan("Plan 2", depth=3)
        await operations.create_plan("Plan 3", depth=5)

        stats = await operations.get_statistics()

        # Average should be around 3
        assert 2.5 <= stats["avg_depth"] <= 3.5

    async def test_plan_status_transitions(self, operations: PlanningOperations):
        """Test valid plan status transitions."""
        plan = await operations.create_plan("Transition Test")

        # pending -> in_progress
        assert await operations.update_plan_status(plan["id"], "in_progress")

        # in_progress -> completed
        assert await operations.update_plan_status(plan["id"], "completed")

        # Check final status
        final = await operations.get_plan(plan["id"])
        assert final["status"] == "completed"

    async def test_plan_with_tags(self, operations: PlanningOperations):
        """Test creating plan with tags."""
        plan = await operations.create_plan(
            "Tagged Plan",
            tags=["urgent", "backend", "feature"],
        )

        assert "urgent" in plan["tags"]
        assert "backend" in plan["tags"]
        assert len(plan["tags"]) == 3


class TestPlanningEdgeCases:
    """Test planning operations edge cases."""

    async def test_create_plan_with_empty_tags(self, operations: PlanningOperations):
        """Test creating plan with empty tags list."""
        plan = await operations.create_plan("Plan", tags=[])
        assert plan["tags"] == []

    async def test_create_plan_with_empty_description(self, operations: PlanningOperations):
        """Test creating plan with empty description."""
        plan = await operations.create_plan("Plan", description="")
        assert plan["description"] == ""

    async def test_list_plans_with_zero_limit(self, operations: PlanningOperations):
        """Test listing with zero limit."""
        plans = await operations.list_plans(limit=0)
        assert isinstance(plans, list)

    async def test_get_plan_with_integer_id(self, operations: PlanningOperations):
        """Test getting plan with integer ID."""
        plan = await operations.create_plan("Integer ID Test")
        retrieved = await operations.get_plan(int(plan["id"]))

        assert retrieved is not None

    async def test_validate_plan_with_string_id(self, operations: PlanningOperations):
        """Test validating with string ID."""
        plan = await operations.create_plan("String Validation")
        validation = await operations.validate_plan(str(plan["id"]))

        assert validation is not None

    async def test_estimate_effort_with_string_id(self, operations: PlanningOperations):
        """Test effort estimation with string ID."""
        plan = await operations.create_plan("String Effort")
        estimate = await operations.estimate_effort(str(plan["id"]))

        assert estimate is not None

    async def test_plan_creation_with_unicode(self, operations: PlanningOperations):
        """Test plan creation with unicode characters."""
        plan = await operations.create_plan(
            "计划 Planification プラン",
            description="Multiple language test",
        )

        assert "计划" in plan["goal"]

    async def test_plan_creation_with_special_characters(self, operations: PlanningOperations):
        """Test plan creation with special characters."""
        plan = await operations.create_plan(
            "Plan @#$%^&*() with special chars!",
        )

        assert "@" in plan["goal"]

    async def test_very_deep_plan(self, operations: PlanningOperations):
        """Test creating plan with maximum depth."""
        plan = await operations.create_plan("Deep Plan", depth=100)
        assert plan["depth"] == 5  # Should clamp to max

    async def test_very_shallow_plan(self, operations: PlanningOperations):
        """Test creating plan with minimum depth."""
        plan = await operations.create_plan("Shallow Plan", depth=-10)
        assert plan["depth"] == 1  # Should clamp to min

    async def test_plan_with_many_tags(self, operations: PlanningOperations):
        """Test creating plan with many tags."""
        tags = [f"tag{i}" for i in range(50)]
        plan = await operations.create_plan("Many Tags Plan", tags=tags)

        assert len(plan["tags"]) == 50


class TestPlanningIntegration:
    """Test planning operations integration scenarios."""

    async def test_full_plan_lifecycle(self, operations: PlanningOperations):
        """Test complete plan lifecycle."""
        # 1. Create plan
        plan = await operations.create_plan(
            "Full Lifecycle Plan",
            depth=3,
            tags=["test", "integration"],
        )
        assert plan["status"] == "pending"

        # 2. Validate plan
        validation = await operations.validate_plan(plan["id"])
        assert validation is not None

        # 3. Estimate effort
        estimate = await operations.estimate_effort(plan["id"])
        assert estimate is not None

        # 4. Update status to in_progress
        assert await operations.update_plan_status(plan["id"], "in_progress")

        # 5. Verify status updated
        updated = await operations.get_plan(plan["id"])
        assert updated["status"] == "in_progress"

        # 6. Complete plan
        assert await operations.update_plan_status(plan["id"], "completed")

        # 7. Get final plan
        final = await operations.get_plan(plan["id"])
        assert final["status"] == "completed"

    async def test_multiple_plans_management(self, operations: PlanningOperations):
        """Test managing multiple plans."""
        # Create multiple plans
        plans = []
        for i in range(5):
            plan = await operations.create_plan(
                f"Plan {i}",
                depth=1 + (i % 3),
                tags=[f"type{i % 2}"],
            )
            plans.append(plan)

        # Update some to different statuses
        await operations.update_plan_status(plans[0]["id"], "in_progress")
        await operations.update_plan_status(plans[1]["id"], "completed")
        await operations.update_plan_status(plans[2]["id"], "cancelled")

        # List by status
        pending = await operations.list_plans(status="pending")
        in_progress = await operations.list_plans(status="in_progress")
        completed = await operations.list_plans(status="completed")

        # Verify counts
        assert any(p["id"] == plans[0]["id"] for p in in_progress)
        assert any(p["id"] == plans[1]["id"] for p in completed)

    async def test_plan_estimation_vs_depth(self, operations: PlanningOperations):
        """Test that effort estimates scale with depth."""
        plans_by_depth = {}
        for depth in range(1, 6):
            plan = await operations.create_plan(f"Depth {depth}", depth=depth)
            estimate = await operations.estimate_effort(plan["id"])
            plans_by_depth[depth] = estimate.get("total_effort_units", 0)

        # Verify increasing trend
        for i in range(1, 5):
            if plans_by_depth[i] > 0 and plans_by_depth[i + 1] > 0:
                assert plans_by_depth[i + 1] >= plans_by_depth[i]

    async def test_plan_validation_and_estimation(self, operations: PlanningOperations):
        """Test validating and estimating same plan."""
        plan = await operations.create_plan("Dual Test", depth=3)

        validation = await operations.validate_plan(plan["id"])
        estimate = await operations.estimate_effort(plan["id"])

        assert validation is not None
        assert estimate is not None
        assert "valid" in validation
        assert "total_effort_units" in estimate or "error" in estimate

    async def test_plan_statistics_evolution(self, operations: PlanningOperations):
        """Test statistics change as plans evolve."""
        # Initial stats
        initial_stats = await operations.get_statistics()
        initial_count = initial_stats.get("total_plans", 0)

        # Create plans
        for i in range(3):
            await operations.create_plan(f"Evolving Plan {i}")

        # Updated stats
        updated_stats = await operations.get_statistics()
        updated_count = updated_stats.get("total_plans", 0)

        # Verify increase
        assert updated_count >= initial_count + 3

    async def test_plan_list_and_get_consistency(self, operations: PlanningOperations):
        """Test that list and get operations are consistent."""
        # Create plans
        created_plans = []
        for i in range(3):
            plan = await operations.create_plan(f"Consistency {i}")
            created_plans.append(plan)

        # Get via list
        listed = await operations.list_plans(limit=100)
        listed_ids = {p["id"] for p in listed}

        # Verify all created plans are in list
        for plan in created_plans:
            assert plan["id"] in listed_ids

        # Get individually and verify
        for plan in created_plans:
            retrieved = await operations.get_plan(plan["id"])
            assert retrieved is not None
            assert retrieved["id"] == plan["id"]

    async def test_status_filtering_accuracy(self, operations: PlanningOperations):
        """Test that status filtering is accurate."""
        # Create and update plans to different statuses
        plan_pending = await operations.create_plan("Pending")
        plan_active = await operations.create_plan("Active")
        plan_done = await operations.create_plan("Done")
        plan_cancelled = await operations.create_plan("Cancelled")

        await operations.update_plan_status(plan_active["id"], "in_progress")
        await operations.update_plan_status(plan_done["id"], "completed")
        await operations.update_plan_status(plan_cancelled["id"], "cancelled")

        # Filter each status
        pending_list = await operations.list_plans(status="pending")
        active_list = await operations.list_plans(status="in_progress")
        done_list = await operations.list_plans(status="completed")

        # Verify filtering
        pending_ids = {p["id"] for p in pending_list}
        assert plan_pending["id"] in pending_ids

        active_ids = {p["id"] for p in active_list}
        assert plan_active["id"] in active_ids
