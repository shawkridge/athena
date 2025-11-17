"""Integration tests for planning operations API.

Tests the async operations.py API against the PlanningStore
to ensure the paradigm is properly implemented.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
from src.athena.planning.store import PlanningStore
from src.athena.planning.operations import PlanningOperations


class MockDatabase:
    """Mock database for testing planning operations."""

    def __init__(self):
        self.patterns = {}  # id -> pattern data
        self.next_id = 0
        self.cursor_instance = None
        self.last_inserted_pattern = None

    def get_cursor(self):
        """Return a mock cursor."""
        self.cursor_instance = MockCursor(self)
        return self.cursor_instance


class MockCursor:
    """Mock cursor for database operations."""

    def __init__(self, db):
        self.db = db
        self.lastrowid = 0
        self._result = None

    def execute(self, sql, params=None):
        """Mock execute - handle INSERT/SELECT statements."""
        sql_upper = sql.upper()

        # Handle INSERT INTO planning_patterns
        if "INSERT INTO planning_patterns" in sql_upper:
            self.db.next_id += 1
            self.lastrowid = self.db.next_id
            # Store pattern data from params
            if params:
                self.db.patterns[self.db.next_id] = {
                    'id': self.db.next_id,
                    'name': params[2] if len(params) > 2 else 'Unnamed',
                    'description': params[3] if len(params) > 3 else '',
                    'complexity_max': params[10] if len(params) > 10 else 3,
                }
            return

        # Handle SELECT FROM planning_patterns WHERE id = ?
        if "SELECT" in sql_upper and "planning_patterns" in sql_upper and params:
            pattern_id = params[0] if params else None
            if pattern_id in self.db.patterns:
                pattern = self.db.patterns[pattern_id]
                # Return a full row matching pattern schema
                self._result = [
                    pattern['id'],  # id
                    1,  # project_id
                    'hierarchical',  # pattern_type
                    pattern['name'],  # name
                    pattern['description'],  # description
                    0.5,  # success_rate
                    0.5,  # quality_score
                    0,  # execution_count
                    [],  # applicable_domains
                    ['general'],  # applicable_task_types
                    1,  # complexity_min
                    pattern['complexity_max'],  # complexity_max
                    {},  # conditions
                    'user',  # source
                    None,  # research_reference
                    0,  # created_at
                    None,  # last_used
                ]
            return

        # Handle SELECT from planning_patterns (list query)
        if "SELECT" in sql_upper and "planning_patterns" in sql_upper:
            self._result = []
            for pid, pattern in self.db.patterns.items():
                self._result.append([
                    pattern['id'],
                    1,
                    'hierarchical',
                    pattern['name'],
                    pattern['description'],
                    0.5,
                    0.5,
                    0,
                    [],
                    ['general'],
                    1,
                    pattern['complexity_max'],
                    {},
                    'user',
                    None,
                    0,
                    None,
                ])
            return

        # Default: skip (for CREATE TABLE, etc.)
        pass

    def fetchone(self):
        """Fetch one row."""
        if self._result:
            row = self._result if isinstance(self._result, list) and len(self._result) > 0 else None
            self._result = None
            return row
        return None

    def fetchall(self):
        """Fetch all rows."""
        result = self._result if isinstance(self._result, list) else []
        self._result = None
        return result


@pytest.fixture
def planning_ops():
    """Create a planning operations instance with test database."""
    db = MockDatabase()
    store = PlanningStore(db)

    ops = PlanningOperations(db, store)
    return ops


class TestPlanningOperationsAPI:
    """Test the planning operations async API.

    NOTE: These tests verify API structure and paradigm compliance.
    Full integration tests require a real database connection.
    """

    @pytest.mark.asyncio
    async def test_operations_callable(self, planning_ops):
        """Verify all operations are callable async functions."""
        # Test that all methods exist and are callable
        assert callable(planning_ops.create_plan)
        assert callable(planning_ops.get_plan)
        assert callable(planning_ops.list_plans)
        assert callable(planning_ops.validate_plan)
        assert callable(planning_ops.estimate_effort)
        assert callable(planning_ops.update_plan_status)
        assert callable(planning_ops.get_statistics)

    @pytest.mark.asyncio
    async def test_create_plan_structure(self, planning_ops):
        """Test that create_plan returns expected structure."""
        # Note: Mock DB means this will return a created pattern
        result = await planning_ops.create_plan(
            goal="Test goal",
            description="Test description",
            depth=3,
            tags=["test"]
        )

        # Verify structure matches expected API
        assert isinstance(result, dict)
        assert "goal" in result or "id" in result  # Should have at least one key

    @pytest.mark.asyncio
    async def test_get_plan_structure(self, planning_ops):
        """Test that get_plan returns expected structure or None."""
        result = await planning_ops.get_plan(9999)
        # Should return None for non-existent plan
        assert result is None

    @pytest.mark.asyncio
    async def test_list_plans_structure(self, planning_ops):
        """Test that list_plans returns a list."""
        result = await planning_ops.list_plans(limit=10)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_validate_plan_not_found(self, planning_ops):
        """Test validation of non-existent plan."""
        result = await planning_ops.validate_plan(9999)
        assert isinstance(result, dict)
        assert result.get("valid") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_estimate_effort_not_found(self, planning_ops):
        """Test effort estimation for non-existent plan."""
        result = await planning_ops.estimate_effort(9999)
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_plan_status_not_found(self, planning_ops):
        """Test updating status of non-existent plan."""
        result = await planning_ops.update_plan_status(9999, "completed")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_statistics_structure(self, planning_ops):
        """Test that get_statistics returns expected structure."""
        result = await planning_ops.get_statistics()
        assert isinstance(result, dict)
        assert "total_plans" in result


class TestPlanningAPIParadigmCompliance:
    """Test that planning API complies with Athena paradigm."""

    @pytest.mark.asyncio
    async def test_operations_are_async_callable(self, planning_ops):
        """Verify all operations are properly async."""
        # All public operations should be coroutines
        assert asyncio.iscoroutinefunction(planning_ops.create_plan)
        assert asyncio.iscoroutinefunction(planning_ops.get_plan)
        assert asyncio.iscoroutinefunction(planning_ops.list_plans)
        assert asyncio.iscoroutinefunction(planning_ops.validate_plan)
        assert asyncio.iscoroutinefunction(planning_ops.estimate_effort)
        assert asyncio.iscoroutinefunction(planning_ops.update_plan_status)
        assert asyncio.iscoroutinefunction(planning_ops.get_statistics)

    @pytest.mark.asyncio
    async def test_store_methods_exist(self, planning_ops):
        """Verify PlanningStore has the required async wrapper methods."""
        store = planning_ops.store

        # All methods that operations.py calls should exist
        assert hasattr(store, "store_plan")
        assert hasattr(store, "get_plan")
        assert hasattr(store, "list_plans")
        assert hasattr(store, "validate_plan")
        assert hasattr(store, "estimate_effort")
        assert hasattr(store, "update_plan_status")

    @pytest.mark.asyncio
    async def test_operations_use_correct_signatures(self, planning_ops):
        """Verify operations have correct type signatures."""
        import inspect

        # get_plan should accept int or str ID
        sig = inspect.signature(planning_ops.get_plan)
        params = list(sig.parameters.keys())
        assert "plan_id" in params

        # create_plan should accept goal at minimum
        sig = inspect.signature(planning_ops.create_plan)
        params = list(sig.parameters.keys())
        assert "goal" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
