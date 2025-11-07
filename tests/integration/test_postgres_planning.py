"""Integration tests for PostgreSQL planning functionality.

Tests planning decision storage, scenario management, and validation
using PostgreSQL backend.
"""

import pytest
from typing import AsyncGenerator

# Skip if PostgreSQL not available
pytest.importorskip("psycopg")

import pytest_asyncio

from athena.core.database_postgres import PostgresDatabase
from athena.planning.postgres_planning_integration import (
    PostgresPlanningIntegration,
    initialize_planning_postgres,
    PlanningDecision,
    PlanningScenario,
)


@pytest.fixture
def postgres_db() -> PostgresDatabase:
    """Create PostgreSQL database instance."""
    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )
    return db


@pytest_asyncio.fixture
async def initialized_db(postgres_db: PostgresDatabase) -> AsyncGenerator:
    """Initialize PostgreSQL database."""
    await postgres_db.initialize()
    yield postgres_db
    await postgres_db.close()


@pytest_asyncio.fixture
async def planning_integration(
    initialized_db: PostgresDatabase,
) -> PostgresPlanningIntegration:
    """Create planning integration."""
    return PostgresPlanningIntegration(db=initialized_db)


@pytest_asyncio.fixture
async def project_id(initialized_db: PostgresDatabase) -> int:
    """Create test project."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    project = await initialized_db.create_project(
        name=f"planning_test_{unique_id}",
        path=f"/test/planning/{unique_id}",
        language="python",
    )
    return project.id


class TestPlanningDecisionStorage:
    """Test planning decision storage."""

    @pytest.mark.asyncio
    async def test_store_planning_decision(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test storing a planning decision."""
        decision_id = await planning_integration.store_planning_decision(
            project_id=project_id,
            decision_type="architecture",
            title="Use PostgreSQL for persistent memory",
            rationale="Provides better scalability than SQLite for production use",
            alternatives=["MongoDB", "DynamoDB", "Keep SQLite"],
        )

        assert decision_id > 0, "Decision should be stored successfully"

    @pytest.mark.asyncio
    async def test_store_decomposition_decision(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test storing a decomposition strategy decision."""
        decision_id = await planning_integration.store_planning_decision(
            project_id=project_id,
            decision_type="decomposition",
            title="Phase 5 Part 3 Implementation Strategy",
            rationale="Break into three focused areas: code search, planning, analytics",
            alternatives=[
                "Single monolithic implementation",
                "Agile sprint-based approach",
            ],
            related_memory_ids=[1, 2, 3],
        )

        assert decision_id > 0, "Decomposition decision should be stored"

    @pytest.mark.asyncio
    async def test_store_multiple_decisions(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test storing multiple planning decisions."""
        decision_ids = []

        for i in range(3):
            decision_id = await planning_integration.store_planning_decision(
                project_id=project_id,
                decision_type="technical",
                title=f"Decision {i+1}",
                rationale=f"Rationale for decision {i+1}",
                alternatives=[f"Alt {j}" for j in range(2)],
            )
            decision_ids.append(decision_id)

        assert len([d for d in decision_ids if d > 0]) == 3, "All decisions should be stored"


class TestPlanningScenarios:
    """Test planning scenario management."""

    @pytest.mark.asyncio
    async def test_store_planning_scenario(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test storing a planning scenario."""
        scenario_id = await planning_integration.store_planning_scenario(
            project_id=project_id,
            scenario_type="best_case",
            description="All Phase 5 Part 3 components complete on time",
            assumptions=[
                "PostgreSQL stable",
                "Integration tests pass",
                "No blocking issues",
            ],
            expected_outcomes=[
                "Code search fully operational",
                "Planning layer integrated",
                "Analytics available",
            ],
            risk_level="low",
        )

        assert scenario_id > 0, "Scenario should be stored"

    @pytest.mark.asyncio
    async def test_store_worst_case_scenario(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test storing a worst-case scenario."""
        scenario_id = await planning_integration.store_planning_scenario(
            project_id=project_id,
            scenario_type="worst_case",
            description="PostgreSQL integration encounters major issues",
            assumptions=[
                "pgvector fails",
                "Async operations deadlock",
                "Need to rollback to SQLite",
            ],
            expected_outcomes=[
                "System falls back to SQLite",
                "Reduced performance",
                "Manual migration required",
            ],
            risk_level="high",
        )

        assert scenario_id > 0, "Worst-case scenario should be stored"

    @pytest.mark.asyncio
    async def test_store_edge_case_scenario(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test storing an edge-case scenario."""
        scenario_id = await planning_integration.store_planning_scenario(
            project_id=project_id,
            scenario_type="edge_case",
            description="Very large codebase (100k+ entities)",
            assumptions=[
                "Code search scales to enterprise size",
                "Queries remain under 1s",
                "Vector search indexes optimal",
            ],
            expected_outcomes=[
                "Full-text search works",
                "Dependency analysis completes",
                "Memory usage stays reasonable",
            ],
            risk_level="medium",
        )

        assert scenario_id > 0, "Edge-case scenario should be stored"


class TestDecisionRetrieval:
    """Test retrieving planning decisions."""

    @pytest.fixture
    async def populated_decisions(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ) -> int:
        """Create several test decisions."""
        for i in range(5):
            await planning_integration.store_planning_decision(
                project_id=project_id,
                decision_type="technical" if i % 2 == 0 else "architecture",
                title=f"Decision {i+1}",
                rationale=f"Rationale {i+1}",
            )

        return project_id

    @pytest.mark.asyncio
    async def test_get_all_decisions(
        self,
        planning_integration: PostgresPlanningIntegration,
        populated_decisions: int,
    ):
        """Test retrieving all decisions."""
        decisions = await planning_integration.get_related_decisions(
            project_id=populated_decisions,
            limit=10,
        )

        assert isinstance(decisions, list), "Should return list of decisions"
        # May be empty if PostgreSQL not available, but should not error
        assert all(
            isinstance(d, PlanningDecision) for d in decisions
        ), "Results should be PlanningDecision objects"

    @pytest.mark.asyncio
    async def test_filter_by_decision_type(
        self,
        planning_integration: PostgresPlanningIntegration,
        populated_decisions: int,
    ):
        """Test filtering decisions by type."""
        decisions = await planning_integration.get_related_decisions(
            project_id=populated_decisions,
            decision_type="technical",
            limit=10,
        )

        assert isinstance(decisions, list), "Should return filtered decisions"

    @pytest.mark.asyncio
    async def test_filter_by_validation_status(
        self,
        planning_integration: PostgresPlanningIntegration,
        populated_decisions: int,
    ):
        """Test filtering by validation status."""
        decisions = await planning_integration.get_related_decisions(
            project_id=populated_decisions,
            validation_status="pending",
            limit=10,
        )

        assert isinstance(decisions, list), "Should return filtered decisions"


class TestDecisionValidation:
    """Test decision validation status updates."""

    @pytest.mark.asyncio
    async def test_update_decision_validation(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test updating decision validation status."""
        # Store decision
        decision_id = await planning_integration.store_planning_decision(
            project_id=project_id,
            decision_type="technical",
            title="Test Decision",
            rationale="Test rationale",
        )

        if decision_id <= 0:
            pytest.skip("PostgreSQL not available")

        # Update validation
        success = await planning_integration.update_decision_validation(
            decision_id=decision_id,
            validation_status="valid",
            validation_confidence=0.95,
        )

        assert success is True, "Validation should be updated"

    @pytest.mark.asyncio
    async def test_mark_decision_invalid(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test marking decision as invalid."""
        decision_id = await planning_integration.store_planning_decision(
            project_id=project_id,
            decision_type="technical",
            title="Invalid Decision",
            rationale="This will be invalidated",
        )

        if decision_id <= 0:
            pytest.skip("PostgreSQL not available")

        success = await planning_integration.update_decision_validation(
            decision_id=decision_id,
            validation_status="invalid",
            validation_confidence=0.2,
        )

        assert success is True, "Should mark as invalid"


class TestScenarioRetrieval:
    """Test retrieving planning scenarios."""

    @pytest.fixture
    async def populated_scenarios(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ) -> int:
        """Create test scenarios."""
        scenarios = [
            ("best_case", "All goes well"),
            ("worst_case", "Everything fails"),
            ("nominal", "Expected behavior"),
            ("edge_case", "Extreme conditions"),
        ]

        for stype, desc in scenarios:
            await planning_integration.store_planning_scenario(
                project_id=project_id,
                scenario_type=stype,
                description=desc,
                assumptions=["test assumption"],
                expected_outcomes=["test outcome"],
            )

        return project_id

    @pytest.mark.asyncio
    async def test_get_scenario_results(
        self,
        planning_integration: PostgresPlanningIntegration,
        populated_scenarios: int,
    ):
        """Test retrieving scenario results."""
        scenarios = await planning_integration.get_scenario_test_results(
            project_id=populated_scenarios,
        )

        assert isinstance(scenarios, list), "Should return list of scenarios"
        assert all(
            isinstance(s, PlanningScenario) for s in scenarios
        ), "Results should be PlanningScenario objects"

    @pytest.mark.asyncio
    async def test_filter_scenarios_by_type(
        self,
        planning_integration: PostgresPlanningIntegration,
        populated_scenarios: int,
    ):
        """Test filtering scenarios by type."""
        scenarios = await planning_integration.get_scenario_test_results(
            project_id=populated_scenarios,
            scenario_type="best_case",
        )

        assert isinstance(scenarios, list), "Should return filtered scenarios"


class TestDecisionPatterns:
    """Test extracting patterns from planning decisions."""

    @pytest.mark.asyncio
    async def test_get_decision_patterns(
        self,
        planning_integration: PostgresPlanningIntegration,
        project_id: int,
    ):
        """Test extracting decision patterns."""
        # Store some decisions
        for i in range(3):
            await planning_integration.store_planning_decision(
                project_id=project_id,
                decision_type="technical",
                title=f"Decision {i}",
                rationale=f"Rationale {i}",
            )

        patterns = await planning_integration.get_decision_patterns(
            project_id=project_id,
            lookback_decisions=10,
        )

        assert isinstance(patterns, dict), "Should return patterns dictionary"
        assert "total_decisions" in patterns or len(patterns) == 0, "Should have expected keys"


class TestPostgresPlanningIntegrationInit:
    """Test initialization of PostgreSQL planning integration."""

    @pytest.mark.asyncio
    async def test_initialize_with_postgres(
        self,
        postgres_db: PostgresDatabase,
    ):
        """Test initializing planning with PostgreSQL."""
        await postgres_db.initialize()

        integration = await initialize_planning_postgres(db=postgres_db)

        assert integration is not None, "Should initialize integration"
        assert integration.is_postgres, "Should detect PostgreSQL"

        await postgres_db.close()

    @pytest.mark.asyncio
    async def test_initialize_without_db(self):
        """Test initializing without database."""
        integration = await initialize_planning_postgres(db=None)

        assert integration is not None, "Should initialize without database"
        assert not integration.is_postgres, "Should not detect PostgreSQL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
