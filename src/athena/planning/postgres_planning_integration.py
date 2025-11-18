"""PostgreSQL integration for planning operations.

This module provides seamless integration between planning operations and PostgreSQL,
enabling persistent storage and retrieval of planning decisions, scenarios, and validations.

Features:
- Store and retrieve planning decisions with validation status
- Manage task hierarchies and goal dependencies
- Store planning scenarios for strategy evaluation
- Query decision history and validation patterns
- Cross-layer planning-memory relationships
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from ..core.database_postgres import PostgresDatabase
from ..core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class PlanningDecision:
    """Represents a planning decision stored in PostgreSQL."""

    id: int
    project_id: int
    decision_type: str
    title: str
    rationale: str
    alternatives: List[str]
    validation_status: str  # pending, validating, valid, invalid
    validation_confidence: Optional[float]
    related_memory_ids: List[int]
    created_at: datetime
    validated_at: Optional[datetime]
    superseded_by: Optional[int]


@dataclass
class PlanningScenario:
    """Represents a planning scenario for strategy evaluation."""

    id: int
    project_id: int
    scenario_type: str  # "best_case", "worst_case", "nominal", "edge_case"
    description: str
    assumptions: List[str]
    expected_outcomes: List[str]
    risk_level: str  # "low", "medium", "high"
    testing_status: str  # "not_tested", "passed", "failed"
    created_at: datetime


class PostgresPlanningIntegration:
    """Integrates planning operations with PostgreSQL database.

    Provides:
    - Persistent decision and scenario storage
    - Query decision history with validation patterns
    - Cross-layer planning-memory relationships
    - Scenario simulation support for Q*-style planning
    """

    def __init__(self, db: Optional[Database] = None):
        """Initialize PostgreSQL planning integration.

        Args:
            db: Database instance (auto-detected as PostgreSQL or SQLite)
        """
        self.db = db
        self.is_postgres = self._check_postgres()

    def _check_postgres(self) -> bool:
        """Check if database is PostgreSQL."""
        if self.db is None:
            return False
        try:
            return isinstance(self.db, PostgresDatabase)
        except (ImportError, AttributeError):
            return False

    async def store_planning_decision(
        self,
        project_id: int,
        decision_type: str,
        title: str,
        rationale: str,
        alternatives: Optional[List[str]] = None,
        related_memory_ids: Optional[List[int]] = None,
    ) -> int:
        """Store a planning decision.

        Args:
            project_id: Project ID
            decision_type: Type of decision (decomposition, strategy, architecture, etc.)
            title: Decision title
            rationale: Decision rationale
            alternatives: List of considered alternatives
            related_memory_ids: Related memory vector IDs

        Returns:
            Decision ID
        """
        if not self.is_postgres or self.db is None:
            logger.warning("PostgreSQL not available for planning decision storage")
            return -1

        db = self.db

        try:
            # Store as memory first (for linkage with other layers)
            memory_id = await db.store_memory(
                project_id=project_id,
                content=f"Planning Decision: {title}\n\n{rationale}",
                embedding=[0.0] * 768,  # Will be computed by consolidation
                memory_type="planning_decision",
                domain="planning",
                tags=["decision", decision_type.lower()],
            )

            # Store decision metadata
            async with db.get_connection() as conn:
                result = await conn.execute(
                    """
                    INSERT INTO planning_decisions (
                        project_id, decision_type, title, rationale,
                        alternatives, context_memory_ids, validation_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        decision_type,
                        title,
                        rationale,
                        alternatives or [],
                        related_memory_ids or [],
                        "pending",
                    ),
                )
                row = await result.fetchone()
                decision_id = row[0] if row else -1
                await conn.commit()

            return decision_id
        except Exception as e:
            logger.error(f"Failed to store planning decision: {e}")
            return -1

    async def store_planning_scenario(
        self,
        project_id: int,
        scenario_type: str,
        description: str,
        assumptions: List[str],
        expected_outcomes: List[str],
        risk_level: str = "medium",
    ) -> int:
        """Store a planning scenario for evaluation.

        Args:
            project_id: Project ID
            scenario_type: Type of scenario (best_case, worst_case, nominal, edge_case)
            description: Scenario description
            assumptions: List of assumptions
            expected_outcomes: Expected outcomes
            risk_level: Risk assessment (low, medium, high)

        Returns:
            Scenario ID
        """
        if not self.is_postgres or self.db is None:
            logger.warning("PostgreSQL not available for planning scenario storage")
            return -1

        db = self.db

        try:
            async with db.get_connection() as conn:
                result = await conn.execute(
                    """
                    INSERT INTO planning_scenarios (
                        project_id, scenario_type, description,
                        assumptions, expected_outcomes, risk_level, testing_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        scenario_type,
                        description,
                        assumptions,
                        expected_outcomes,
                        risk_level,
                        "not_tested",
                    ),
                )
                row = await result.fetchone()
                scenario_id = row[0] if row else -1
                await conn.commit()

            return scenario_id
        except Exception as e:
            logger.error(f"Failed to store planning scenario: {e}")
            return -1

    async def get_related_decisions(
        self,
        project_id: int,
        memory_id: Optional[int] = None,
        decision_type: Optional[str] = None,
        validation_status: Optional[str] = None,
        limit: int = 10,
    ) -> List[PlanningDecision]:
        """Get planning decisions for a project.

        Args:
            project_id: Project ID
            memory_id: Optional filter by related memory
            decision_type: Optional filter by decision type
            validation_status: Optional filter by validation status
            limit: Maximum results

        Returns:
            List of PlanningDecision objects
        """
        if not self.is_postgres or self.db is None:
            return []

        db = self.db

        try:
            async with db.get_connection() as conn:
                # Build query with optional filters
                where_clause = "WHERE project_id = %s"
                params = [project_id]

                if decision_type:
                    where_clause += " AND decision_type = %s"
                    params.append(decision_type)

                if validation_status:
                    where_clause += " AND validation_status = %s"
                    params.append(validation_status)

                result = await conn.execute(
                    f"""
                    SELECT id, project_id, decision_type, title, rationale,
                           alternatives, validation_status, validation_confidence,
                           context_memory_ids, created_at, validated_at, superseded_by
                    FROM planning_decisions
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    params + [limit],
                )
                rows = await result.fetchall()

                decisions = []
                for row in rows:
                    decisions.append(
                        PlanningDecision(
                            id=row[0],
                            project_id=row[1],
                            decision_type=row[2],
                            title=row[3],
                            rationale=row[4],
                            alternatives=row[5] or [],
                            validation_status=row[6],
                            validation_confidence=row[7],
                            related_memory_ids=row[8] or [],
                            created_at=row[9],
                            validated_at=row[10],
                            superseded_by=row[11],
                        )
                    )

                return decisions
        except Exception as e:
            logger.error(f"Failed to get planning decisions: {e}")
            return []

    async def update_decision_validation(
        self,
        decision_id: int,
        validation_status: str,
        validation_confidence: Optional[float] = None,
        validation_notes: Optional[str] = None,
    ) -> bool:
        """Update decision validation status.

        Args:
            decision_id: Decision ID
            validation_status: New status (pending, validating, valid, invalid)
            validation_confidence: Confidence score (0-1)
            validation_notes: Optional validation notes

        Returns:
            True if successful
        """
        if not self.is_postgres or self.db is None:
            return False

        db = self.db

        try:
            async with db.get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE planning_decisions
                    SET validation_status = %s, validation_confidence = %s, validated_at = NOW()
                    WHERE id = %s
                    """,
                    (validation_status, validation_confidence, decision_id),
                )
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update decision validation: {e}")
            return False

    async def get_scenario_test_results(
        self,
        project_id: int,
        scenario_type: Optional[str] = None,
    ) -> List[PlanningScenario]:
        """Get scenario testing results.

        Args:
            project_id: Project ID
            scenario_type: Optional filter by scenario type

        Returns:
            List of PlanningScenario objects
        """
        if not self.is_postgres or self.db is None:
            return []

        db = self.db

        try:
            async with db.get_connection() as conn:
                where_clause = "WHERE project_id = %s"
                params = [project_id]

                if scenario_type:
                    where_clause += " AND scenario_type = %s"
                    params.append(scenario_type)

                result = await conn.execute(
                    f"""
                    SELECT id, project_id, scenario_type, description,
                           assumptions, expected_outcomes, risk_level,
                           testing_status, created_at
                    FROM planning_scenarios
                    {where_clause}
                    ORDER BY created_at DESC
                    """,
                    params,
                )
                rows = await result.fetchall()

                scenarios = []
                for row in rows:
                    scenarios.append(
                        PlanningScenario(
                            id=row[0],
                            project_id=row[1],
                            scenario_type=row[2],
                            description=row[3],
                            assumptions=row[4] or [],
                            expected_outcomes=row[5] or [],
                            risk_level=row[6],
                            testing_status=row[7],
                            created_at=row[8],
                        )
                    )

                return scenarios
        except Exception as e:
            logger.error(f"Failed to get scenario results: {e}")
            return []

    async def get_decision_patterns(
        self,
        project_id: int,
        lookback_decisions: int = 20,
    ) -> Dict[str, Any]:
        """Extract patterns from planning decisions.

        Args:
            project_id: Project ID
            lookback_decisions: Number of recent decisions to analyze

        Returns:
            Dictionary with decision patterns and insights
        """
        if not self.is_postgres or self.db is None:
            return {}

        decisions = await self.get_related_decisions(
            project_id=project_id,
            limit=lookback_decisions,
        )

        try:
            patterns = {
                "total_decisions": len(decisions),
                "by_type": {},
                "validation_success_rate": 0.0,
                "most_common_type": None,
                "decision_velocity": 0,  # decisions per day
            }

            # Group by type
            for decision in decisions:
                decision_type = decision.decision_type
                if decision_type not in patterns["by_type"]:
                    patterns["by_type"][decision_type] = {"count": 0, "valid": 0}
                patterns["by_type"][decision_type]["count"] += 1

                if decision.validation_status == "valid":
                    patterns["by_type"][decision_type]["valid"] += 1

            # Calculate success rate
            valid_count = sum(1 for d in decisions if d.validation_status == "valid")
            if decisions:
                patterns["validation_success_rate"] = valid_count / len(decisions)

            # Most common type
            if patterns["by_type"]:
                patterns["most_common_type"] = max(
                    patterns["by_type"].items(),
                    key=lambda x: x[1]["count"],
                )[0]

            return patterns
        except Exception as e:
            logger.error(f"Failed to extract decision patterns: {e}")
            return {}


async def initialize_planning_postgres(
    db: Optional[Database] = None,
) -> PostgresPlanningIntegration:
    """Initialize planning with PostgreSQL integration.

    Args:
        db: Database instance

    Returns:
        PostgresPlanningIntegration instance
    """
    integration = PostgresPlanningIntegration(db=db)

    if integration.is_postgres and db:
        try:
            # Ensure PostgreSQL is initialized
            if isinstance(db, PostgresDatabase):
                await db.initialize()
                logger.info("PostgreSQL planning integration initialized")
        except Exception as e:
            logger.warning(f"PostgreSQL initialization failed: {e}")

    return integration
