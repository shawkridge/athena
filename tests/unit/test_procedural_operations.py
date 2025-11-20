"""Unit tests for procedural memory operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from athena.procedural.operations import ProceduralOperations
from athena.procedural.models import Procedure

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return MagicMock()


@pytest.fixture
def mock_store():
    """Create a mock procedural store with intelligent mocking."""
    # We'll track procedures in a dict for stateful responses
    procedures = {}
    next_id = [1]  # Use list to allow modification in nested functions

    async def store_proc(proc):
        proc_id = next_id[0]
        next_id[0] += 1
        # Ensure proc has an ID before storing
        if proc.id is None:
            proc.id = proc_id
        procedures[proc.id] = proc
        return proc

    async def get_proc(proc_id):
        return procedures.get(proc_id)

    async def list_procs(**kwargs):
        return list(procedures.values())

    async def search_procs(query, **kwargs):
        return [p for p in procedures.values() if query.lower() in (p.name or "").lower()]

    async def update_proc(proc):
        if proc.id in procedures:
            procedures[proc.id] = proc
        return proc

    async def delete_proc(proc_id):
        if proc_id in procedures:
            del procedures[proc_id]
            return True
        return False

    store = MagicMock()
    store.store = AsyncMock(side_effect=store_proc)
    store.get = AsyncMock(side_effect=get_proc)
    store.list = AsyncMock(side_effect=list_procs)
    store.search = AsyncMock(side_effect=search_procs)
    store.update = AsyncMock(side_effect=update_proc)
    store.delete = AsyncMock(side_effect=delete_proc)
    return store


@pytest.fixture
def operations(mock_db, mock_store):
    """Create test operations instance with mocked store."""
    ops = ProceduralOperations(mock_db, mock_store)
    return ops


class TestProceduralOperations:
    """Test procedural memory operations."""

    async def test_extract_procedure(self, operations: ProceduralOperations):
        """Test extracting a procedure."""
        procedure_id = await operations.extract_procedure(
            name="Test Workflow",
            description="A test workflow",
            steps=[
                {"action": "step1", "params": {"key": "value"}},
                {"action": "step2", "params": {}},
            ],
            tags=["testing", "workflow"],
            success_rate=0.8,
            source="test_agent",
        )

        assert procedure_id is not None
        assert isinstance(procedure_id, int)
        assert procedure_id > 0

    async def test_extract_procedure_invalid_input(self, operations: ProceduralOperations):
        """Test extracting procedure with invalid input."""
        with pytest.raises(ValueError):
            await operations.extract_procedure(
                name="",
                description="Missing name",
                steps=[],
            )

        with pytest.raises(ValueError):
            await operations.extract_procedure(
                name="Valid",
                description="",
                steps=[],
            )

        with pytest.raises(ValueError):
            await operations.extract_procedure(
                name="Valid",
                description="Valid",
                steps=[],
            )

    async def test_list_procedures(self, operations: ProceduralOperations):
        """Test listing procedures."""
        # Extract a few procedures
        for i in range(3):
            await operations.extract_procedure(
                name=f"Procedure {i}",
                description=f"Description {i}",
                steps=[{"action": f"step{i}", "params": {}}],
                success_rate=0.5 + (i * 0.1),
            )

        procedures = await operations.list_procedures(limit=10)

        assert len(procedures) >= 3
        assert all(isinstance(p, Procedure) for p in procedures)

    async def test_list_procedures_with_success_filter(self, operations: ProceduralOperations):
        """Test listing procedures with success rate filter."""
        await operations.extract_procedure(
            name="High Success",
            description="High success procedure",
            steps=[{"action": "test", "params": {}}],
            success_rate=0.9,
        )

        await operations.extract_procedure(
            name="Low Success",
            description="Low success procedure",
            steps=[{"action": "test", "params": {}}],
            success_rate=0.1,
        )

        high_success = await operations.list_procedures(min_success_rate=0.8)

        assert all(p.success_rate >= 0.8 for p in high_success)

    async def test_get_procedure(self, operations: ProceduralOperations):
        """Test getting a specific procedure."""
        # First extract a procedure
        proc_id = await operations.extract_procedure(
            name="Get Test",
            description="Test getting",
            steps=[{"action": "test", "params": {}}],
        )

        # Then get it back
        procedure = await operations.get_procedure(proc_id)

        assert procedure is not None
        assert procedure.id == proc_id
        # Verify it was stored with the correct name
        assert "Get Test" in (procedure.name or "")

    async def test_get_procedure_string_id(self, operations: ProceduralOperations):
        """Test getting procedure with string ID."""
        proc_id = await operations.extract_procedure(
            name="String ID Test",
            description="Test with string ID",
            steps=[{"action": "test", "params": {}}],
        )

        # Pass ID as string
        procedure = await operations.get_procedure(str(proc_id))

        assert procedure is not None
        assert procedure.id == proc_id

    async def test_get_nonexistent_procedure(self, operations: ProceduralOperations):
        """Test getting nonexistent procedure."""
        # First delete all procedures to ensure empty state
        procs = await operations.list_procedures(limit=10000)
        for proc in procs:
            if proc.id:
                await operations.store.delete(proc.id)

        result = await operations.get_procedure(99999)
        assert result is None

    async def test_search_procedures(self, operations: ProceduralOperations):
        """Test searching procedures."""
        await operations.extract_procedure(
            name="Python Testing Framework",
            description="For testing Python code",
            steps=[{"action": "test", "params": {}}],
        )

        await operations.extract_procedure(
            name="Git Workflow",
            description="Git operations",
            steps=[{"action": "git", "params": {}}],
        )

        results = await operations.search_procedures("Python", limit=10)

        assert len(results) > 0
        assert any("Python" in p.name for p in results)

    async def test_search_empty_query(self, operations: ProceduralOperations):
        """Test searching with empty query."""
        results = await operations.search_procedures("", limit=10)
        assert results == []

    async def test_get_procedures_by_tags(self, operations: ProceduralOperations):
        """Test getting procedures by tags (deprecated - should return empty)."""
        # Tags are not supported in the current schema
        results = await operations.get_procedures_by_tags(["testing", "workflow"])
        assert results == []

    async def test_update_procedure_success_rate(self, operations: ProceduralOperations):
        """Test updating procedure success rate."""
        proc_id = await operations.extract_procedure(
            name="Success Update",
            description="Update success rate",
            steps=[{"action": "test", "params": {}}],
            success_rate=0.5,
        )

        # Update with success
        success = await operations.update_procedure_success(proc_id, success=True)
        assert success is True

        procedure = await operations.get_procedure(proc_id)
        assert procedure.usage_count == 1
        assert procedure.success_rate > 0.5  # Should have increased

    async def test_update_procedure_failure(self, operations: ProceduralOperations):
        """Test updating procedure with failure."""
        proc_id = await operations.extract_procedure(
            name="Failure Update",
            description="Record failure",
            steps=[{"action": "test", "params": {}}],
            success_rate=0.8,
        )

        # Update with failure
        success = await operations.update_procedure_success(proc_id, success=False)
        assert success is True

        procedure = await operations.get_procedure(proc_id)
        assert procedure.usage_count == 1
        assert procedure.success_rate < 0.8  # Should have decreased

    async def test_update_nonexistent_procedure(self, operations: ProceduralOperations):
        """Test updating nonexistent procedure."""
        # Ensure the procedure doesn't exist
        procs = await operations.list_procedures(limit=10000)
        for proc in procs:
            if proc.id == 99999 or proc.id:
                await operations.store.delete(proc.id)

        success = await operations.update_procedure_success(99999, success=True)
        assert success is False

    async def test_update_procedure_string_id(self, operations: ProceduralOperations):
        """Test updating procedure with string ID."""
        proc_id = await operations.extract_procedure(
            name="String ID Update",
            description="Update with string ID",
            steps=[{"action": "test", "params": {}}],
        )

        # Update with string ID
        success = await operations.update_procedure_success(str(proc_id), success=True)
        assert success is True

    async def test_exponential_moving_average_success(self, operations: ProceduralOperations):
        """Test exponential moving average success rate calculation."""
        proc_id = await operations.extract_procedure(
            name="EMA Test",
            description="Test EMA calculation",
            steps=[{"action": "test", "params": {}}],
            success_rate=0.5,
        )

        # First success update
        await operations.update_procedure_success(proc_id, success=True)
        proc1 = await operations.get_procedure(proc_id)
        # (0.5 * 0 + 1.0) / 1 = 1.0
        assert proc1.success_rate == 1.0
        assert proc1.usage_count == 1

        # Second failure update
        await operations.update_procedure_success(proc_id, success=False)
        proc2 = await operations.get_procedure(proc_id)
        # (1.0 * 1 + 0.0) / 2 = 0.5
        assert proc2.success_rate == 0.5
        assert proc2.usage_count == 2

    async def test_get_statistics(self, operations: ProceduralOperations):
        """Test getting procedure statistics."""
        # Create procedures with different success rates
        for i in range(3):
            await operations.extract_procedure(
                name=f"Stat Test {i}",
                description=f"Statistics test {i}",
                steps=[{"action": "test", "params": {}}],
                success_rate=0.5 + (i * 0.1),
            )

        stats = await operations.get_statistics()

        assert "total_procedures" in stats
        assert "avg_success_rate" in stats
        assert "total_uses" in stats
        assert "avg_uses_per_procedure" in stats
        assert stats["total_procedures"] >= 3

    async def test_get_statistics_empty(self, operations: ProceduralOperations):
        """Test getting statistics with no procedures."""
        # Delete all procedures first
        procedures = await operations.list_procedures(limit=10000)
        for proc in procedures:
            if proc.id:
                await operations.store.delete(proc.id)

        stats = await operations.get_statistics()

        assert stats["total_procedures"] == 0
        assert stats["avg_success_rate"] == 0.0
        assert stats["avg_use_count"] == 0  # Empty state uses avg_use_count

    async def test_procedure_source_tracking(self, operations: ProceduralOperations):
        """Test that procedure source is tracked."""
        proc_id = await operations.extract_procedure(
            name="Source Test",
            description="Test source tracking",
            steps=[{"action": "test", "params": {}}],
            source="llm_generated",
        )

        procedure = await operations.get_procedure(proc_id)

        # Verify source was passed through (created_by should match source)
        assert procedure is not None
        assert procedure.created_by == "llm_generated"

    async def test_success_rate_clamping(self, operations: ProceduralOperations):
        """Test that success rate is clamped to [0, 1]."""
        # Test with invalid success rates
        proc_id = await operations.extract_procedure(
            name="Clamping Test",
            description="Test success rate clamping",
            steps=[{"action": "test", "params": {}}],
            success_rate=1.5,  # Should be clamped to 1.0
        )

        procedure = await operations.get_procedure(proc_id)

        assert procedure.success_rate == 1.0

        # Test with negative
        proc_id2 = await operations.extract_procedure(
            name="Clamping Test 2",
            description="Test negative clamping",
            steps=[{"action": "test", "params": {}}],
            success_rate=-0.5,  # Should be clamped to 0.0
        )

        procedure2 = await operations.get_procedure(proc_id2)

        assert procedure2.success_rate == 0.0
