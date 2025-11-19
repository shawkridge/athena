"""Learning Tracker - Stores and analyzes agent decision outcomes.

Tracks what decisions agents make, outcomes, and success rates.
Used by AdaptiveAgent to learn and improve decision-making over time.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from athena.core.database import Database


@dataclass
class LearningOutcome:
    """Record of a decision, outcome, and success metric."""

    agent_name: str
    decision: str  # What decision was made
    outcome: str  # What happened (success/failure/partial)
    success_rate: float  # 0.0 to 1.0
    execution_time_ms: float
    context: dict  # Context in which decision was made
    timestamp: datetime
    session_id: Optional[str] = None
    id: Optional[int] = None


class LearningTracker:
    """Tracks agent outcomes and maintains success rate history."""

    def __init__(self, db: Database):
        """Initialize tracker with database connection.

        Args:
            db: Database instance for storing outcomes
        """
        self.db = db

    def _init_schema(self):
        """Create learning outcomes table if it doesn't exist."""
        sql = """
        CREATE TABLE IF NOT EXISTS learning_outcomes (
            id SERIAL PRIMARY KEY,
            agent_name VARCHAR(255) NOT NULL,
            decision TEXT NOT NULL,
            outcome TEXT NOT NULL,
            success_rate FLOAT NOT NULL CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
            execution_time_ms FLOAT NOT NULL,
            context JSONB DEFAULT '{}',
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            session_id VARCHAR(255),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT valid_outcome CHECK (outcome IN ('success', 'failure', 'partial', 'error'))
        )
        """
        try:
            self.db.execute(sql)
        except Exception:
            # Table might already exist or other constraint issue
            pass

    async def track_outcome(
        self,
        agent_name: str,
        decision: str,
        outcome: str,
        success_rate: float,
        execution_time_ms: float = 0.0,
        context: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Record a decision outcome.

        Args:
            agent_name: Name of agent making decision
            decision: Description of decision made
            outcome: Result - one of 'success', 'failure', 'partial', 'error'
            success_rate: Score 0.0-1.0 indicating success
            execution_time_ms: How long execution took
            context: Additional context dict (optional)
            session_id: Session identifier (optional)

        Returns:
            ID of stored outcome record

        Raises:
            ValueError: If outcome not in valid set or success_rate out of range
        """
        if outcome not in ("success", "failure", "partial", "error"):
            raise ValueError(f"Invalid outcome: {outcome}")

        if not (0.0 <= success_rate <= 1.0):
            raise ValueError(f"success_rate must be 0.0-1.0, got {success_rate}")

        context = context or {}

        sql = """
        INSERT INTO learning_outcomes
        (agent_name, decision, outcome, success_rate, execution_time_ms, context, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            agent_name,
            decision,
            outcome,
            success_rate,
            execution_time_ms,
            context,
            session_id,
        )

        try:
            result = self.db.execute(sql, params)
            # Result should be a list with the ID
            if isinstance(result, list) and len(result) > 0:
                return result[0][0] if isinstance(result[0], tuple) else result[0]
            return -1
        except Exception as e:
            raise RuntimeError(f"Failed to track outcome: {e}")

    def get_success_rate(
        self, agent_name: str, decision: Optional[str] = None, time_window_hours: int = 24
    ) -> float:
        """Get success rate for an agent or specific decision.

        Args:
            agent_name: Name of agent to query
            decision: Specific decision type (optional - gets rate for all decisions if None)
            time_window_hours: Only consider outcomes from last N hours

        Returns:
            Success rate 0.0-1.0, or 0.0 if no outcomes found
        """
        where_clause = "agent_name = %s"
        params = [agent_name]

        if decision:
            where_clause += " AND decision = %s"
            params.append(decision)

        # Filter by time window
        where_clause += " AND timestamp > NOW() - INTERVAL '%s hours'"
        params.append(time_window_hours)

        sql = f"""
        SELECT AVG(success_rate) as avg_rate, COUNT(*) as total_count
        FROM learning_outcomes
        WHERE {where_clause}
        """

        try:
            result = self.db.execute(sql, params)
            if result and len(result) > 0:
                avg_rate, total = result[0]
                # avg_rate is None if no rows matched
                return float(avg_rate) if avg_rate is not None else 0.0
            return 0.0
        except Exception as e:
            raise RuntimeError(f"Failed to get success rate: {e}")

    def get_decision_history(
        self, agent_name: str, decision: Optional[str] = None, limit: int = 100
    ) -> list[LearningOutcome]:
        """Retrieve decision history for an agent.

        Args:
            agent_name: Name of agent
            decision: Filter by specific decision (optional)
            limit: Maximum number of records to return

        Returns:
            List of LearningOutcome records, most recent first
        """
        where_clause = "agent_name = %s"
        params = [agent_name]

        if decision:
            where_clause += " AND decision = %s"
            params.append(decision)

        sql = f"""
        SELECT id, agent_name, decision, outcome, success_rate,
               execution_time_ms, context, timestamp, session_id
        FROM learning_outcomes
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT %s
        """
        params.append(limit)

        try:
            results = self.db.execute(sql, params)
            outcomes = []

            if results:
                for row in results:
                    outcome = LearningOutcome(
                        id=row[0],
                        agent_name=row[1],
                        decision=row[2],
                        outcome=row[3],
                        success_rate=float(row[4]),
                        execution_time_ms=float(row[5]),
                        context=row[6] or {},
                        timestamp=row[7],
                        session_id=row[8],
                    )
                    outcomes.append(outcome)

            return outcomes
        except Exception as e:
            raise RuntimeError(f"Failed to get decision history: {e}")

    def get_statistics(self, agent_name: str) -> dict:
        """Get comprehensive statistics for an agent.

        Args:
            agent_name: Name of agent to analyze

        Returns:
            Dict with: total_decisions, success_rate, avg_time_ms,
                       outcomes breakdown, recent_performance
        """
        # Get overall statistics
        sql = """
        SELECT
            COUNT(*) as total,
            AVG(success_rate) as avg_success,
            MIN(success_rate) as min_success,
            MAX(success_rate) as max_success,
            AVG(execution_time_ms) as avg_time,
            COUNT(CASE WHEN outcome = 'success' THEN 1 END) as successes,
            COUNT(CASE WHEN outcome = 'failure' THEN 1 END) as failures
        FROM learning_outcomes
        WHERE agent_name = %s
        """

        try:
            results = self.db.execute(sql, (agent_name,))

            stats = {
                "agent_name": agent_name,
                "total_decisions": 0,
                "success_rate": 0.0,
                "min_success": 0.0,
                "max_success": 0.0,
                "avg_execution_time_ms": 0.0,
                "outcome_breakdown": {},
                "successes": 0,
                "failures": 0,
            }

            if results and len(results) > 0:
                row = results[0]
                total, avg_success, min_success, max_success, avg_time, successes, failures = row

                stats["total_decisions"] = int(total) if total else 0
                stats["success_rate"] = float(avg_success) if avg_success else 0.0
                stats["min_success"] = float(min_success) if min_success else 0.0
                stats["max_success"] = float(max_success) if max_success else 0.0
                stats["avg_execution_time_ms"] = float(avg_time) if avg_time else 0.0
                stats["successes"] = int(successes) if successes else 0
                stats["failures"] = int(failures) if failures else 0

                # Calculate outcome breakdown
                if stats["successes"] > 0:
                    stats["outcome_breakdown"]["success"] = stats["successes"]
                if stats["failures"] > 0:
                    stats["outcome_breakdown"]["failure"] = stats["failures"]

            return stats
        except Exception as e:
            raise RuntimeError(f"Failed to get statistics: {e}")
