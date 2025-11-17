"""Storage and retrieval for thinking traces."""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .thinking_traces import (
    ProblemType,
    ReasoningPattern,
    ReasoningStep,
    ThinkingTrace,
)


class ThinkingTraceStore(BaseStore[ThinkingTrace]):
    """Manages thinking traces.

    Provides:
    - Record reasoning processes
    - Query thinking by goal/execution
    - Analyze reasoning patterns and effectiveness
    - Link thinking to execution outcomes
    """

    table_name = "thinking_traces"
    model_class = ThinkingTrace

    def __init__(self, db: Database):
        """Initialize store with database connection.

        Args:
            db: Database instance
        """
        super().__init__(db)
    def _row_to_model(self, row: Dict[str, Any]) -> ThinkingTrace:
        """Convert database row to ThinkingTrace model.

        Args:
            row: Database row as dict

        Returns:
            ThinkingTrace instance
        """
        # Parse reasoning steps
        reasoning_steps = []
        if row.get("reasoning_steps_json"):
            for step_data in self.deserialize_json(row.get("reasoning_steps_json"), []):
                reasoning_steps.append(ReasoningStep(**step_data))

        # Parse secondary patterns
        secondary_patterns = []
        if row.get("secondary_patterns_json"):
            for pattern_str in self.deserialize_json(row.get("secondary_patterns_json"), []):
                try:
                    secondary_patterns.append(ReasoningPattern(pattern_str))
                except ValueError:
                    pass

        consolidated_at = None
        if row.get("consolidated_at"):
            consolidated_at = self.from_timestamp(row.get("consolidated_at") // 1000 if row.get("consolidated_at") >= 1000000000000 else row.get("consolidated_at"))

        return ThinkingTrace(
            id=row.get("id"),
            problem=row.get("problem"),
            problem_type=ProblemType(row.get("problem_type")) if row.get("problem_type") else None,
            problem_complexity=row.get("problem_complexity"),
            reasoning_steps=reasoning_steps,
            conclusion=row.get("conclusion"),
            reasoning_quality=row.get("reasoning_quality"),
            primary_pattern=ReasoningPattern(row.get("primary_pattern")) if row.get("primary_pattern") else None,
            secondary_patterns=secondary_patterns,
            pattern_effectiveness=row.get("pattern_effectiveness"),
            linked_execution_id=row.get("linked_execution_id"),
            was_reasoning_correct=row.get("was_reasoning_correct"),
            execution_outcome_quality=row.get("execution_outcome_quality"),
            session_id=row.get("session_id"),
            timestamp=self.from_timestamp(row.get("timestamp") // 1000 if row.get("timestamp") and row.get("timestamp") >= 1000000000000 else row.get("timestamp")),
            duration_seconds=row.get("duration_seconds"),
            ai_model_used=row.get("ai_model_used"),
            consolidation_status=row.get("consolidation_status"),
            consolidated_at=consolidated_at,
        )

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Thinking traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thinking_traces (
                id SERIAL PRIMARY KEY,
                problem TEXT NOT NULL,
                problem_type TEXT NOT NULL,
                problem_complexity INTEGER DEFAULT 5,
                reasoning_steps_json TEXT,
                conclusion TEXT NOT NULL,
                reasoning_quality REAL DEFAULT 0.5,
                primary_pattern TEXT,
                secondary_patterns_json TEXT,
                pattern_effectiveness REAL,
                linked_execution_id TEXT,
                was_reasoning_correct BOOLEAN,
                execution_outcome_quality REAL,
                session_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                duration_seconds INTEGER DEFAULT 0,
                ai_model_used TEXT,
                consolidation_status TEXT DEFAULT 'unconsolidated',
                consolidated_at INTEGER,
                created_at INTEGER NOT NULL
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thinking_traces_session
            ON thinking_traces(session_id, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thinking_traces_execution
            ON thinking_traces(linked_execution_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thinking_traces_pattern
            ON thinking_traces(primary_pattern, pattern_effectiveness DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thinking_traces_correctness
            ON thinking_traces(was_reasoning_correct, created_at DESC)
        """)

        # commit handled by cursor context

    def record_thinking(self, trace: ThinkingTrace) -> int:
        """Record a reasoning process.

        Args:
            trace: ThinkingTrace to record

        Returns:
            ID of inserted thinking trace
        """
        now = self.now_timestamp()

        # Get enum values if needed
        problem_type_value = (
            trace.problem_type.value
            if hasattr(trace.problem_type, "value")
            else trace.problem_type
        )
        primary_pattern_value = (
            trace.primary_pattern.value
            if hasattr(trace.primary_pattern, "value")
            else trace.primary_pattern
        )

        result = self.execute("""
            INSERT INTO thinking_traces
            (problem, problem_type, problem_complexity, reasoning_steps_json, conclusion,
             reasoning_quality, primary_pattern, secondary_patterns_json, pattern_effectiveness,
             linked_execution_id, was_reasoning_correct, execution_outcome_quality,
             session_id, timestamp, duration_seconds, ai_model_used, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            trace.problem,
            problem_type_value,
            trace.problem_complexity,
            self.serialize_json([s.dict() for s in trace.reasoning_steps]),
            trace.conclusion,
            trace.reasoning_quality,
            primary_pattern_value,
            self.serialize_json(
                [p.value if hasattr(p, "value") else p
                 for p in trace.secondary_patterns]
            ),
            trace.pattern_effectiveness,
            trace.linked_execution_id,
            trace.was_reasoning_correct,
            trace.execution_outcome_quality,
            trace.session_id,
            int(trace.timestamp.timestamp() * 1000),
            trace.duration_seconds,
            trace.ai_model_used,
            now,
        ), fetch_one=True)

        self.commit()
        return result[0] if result else None

    def get_thinking(self, thinking_id: int) -> Optional[ThinkingTrace]:
        """Retrieve a thinking trace.

        Args:
            thinking_id: Thinking trace ID

        Returns:
            ThinkingTrace or None if not found
        """
        row = self.execute(
            "SELECT * FROM thinking_traces WHERE id = ?",
            (thinking_id,),
            fetch_one=True,
        )
        if not row:
            return None
        # Convert tuple to dict with column names
        col_names = ["id", "problem", "problem_type", "problem_complexity", "reasoning_steps_json",
                     "conclusion", "reasoning_quality", "primary_pattern", "secondary_patterns_json",
                     "pattern_effectiveness", "linked_execution_id", "was_reasoning_correct",
                     "execution_outcome_quality", "session_id", "timestamp", "duration_seconds",
                     "ai_model_used", "consolidation_status", "consolidated_at", "created_at"]
        return self._row_to_model(dict(zip(col_names, row)))

    def get_thinking_for_session(self, session_id: str) -> list[ThinkingTrace]:
        """Get all thinking traces in a session.

        Args:
            session_id: Session ID

        Returns:
            List of ThinkingTraces
        """
        rows = self.execute(
            "SELECT * FROM thinking_traces WHERE session_id = ? ORDER BY timestamp DESC",
            (session_id,),
            fetch_all=True,
        )
        col_names = ["id", "problem", "problem_type", "problem_complexity", "reasoning_steps_json",
                     "conclusion", "reasoning_quality", "primary_pattern", "secondary_patterns_json",
                     "pattern_effectiveness", "linked_execution_id", "was_reasoning_correct",
                     "execution_outcome_quality", "session_id", "timestamp", "duration_seconds",
                     "ai_model_used", "consolidation_status", "consolidated_at", "created_at"]
        return [self._row_to_model(dict(zip(col_names, row))) for row in (rows or [])]

    def link_thinking_to_execution(
        self,
        thinking_id: int,
        execution_id: str,
        was_correct: bool,
        outcome_quality: float,
    ) -> None:
        """Link a thinking trace to execution outcome.

        Args:
            thinking_id: Thinking trace ID
            execution_id: ExecutionTrace ID (UUID as string)
            was_correct: Whether the reasoning proved correct
            outcome_quality: Quality of the execution outcome (0.0-1.0)
        """
        self.execute("""
            UPDATE thinking_traces
            SET linked_execution_id = ?, was_reasoning_correct = ?,
                execution_outcome_quality = ?
            WHERE id = ?
        """, (execution_id, was_correct, outcome_quality, thinking_id))
        self.commit()

    def get_thinking_for_execution(self, execution_id: str) -> Optional[ThinkingTrace]:
        """Get thinking trace linked to an execution.

        Args:
            execution_id: ExecutionTrace ID (UUID as string)

        Returns:
            ThinkingTrace or None
        """
        row = self.execute(
            "SELECT * FROM thinking_traces WHERE linked_execution_id = ?",
            (execution_id,),
            fetch_one=True,
        )
        if not row:
            return None
        col_names = ["id", "problem", "problem_type", "problem_complexity", "reasoning_steps_json",
                     "conclusion", "reasoning_quality", "primary_pattern", "secondary_patterns_json",
                     "pattern_effectiveness", "linked_execution_id", "was_reasoning_correct",
                     "execution_outcome_quality", "session_id", "timestamp", "duration_seconds",
                     "ai_model_used", "consolidation_status", "consolidated_at", "created_at"]
        return self._row_to_model(dict(zip(col_names, row)))

    def get_thinking_by_pattern(
        self,
        pattern: ReasoningPattern,
        min_effectiveness: float = 0.0,
    ) -> list[ThinkingTrace]:
        """Get thinking traces using a specific reasoning pattern.

        Args:
            pattern: ReasoningPattern to filter by
            min_effectiveness: Minimum effectiveness threshold (0.0-1.0)

        Returns:
            List of ThinkingTraces
        """
        pattern_value = pattern.value if hasattr(pattern, "value") else pattern

        rows = self.execute("""
            SELECT * FROM thinking_traces
            WHERE primary_pattern = ?
            AND (pattern_effectiveness >= ? OR pattern_effectiveness IS NULL)
            ORDER BY pattern_effectiveness DESC NULLS LAST
        """, (pattern_value, min_effectiveness), fetch_all=True)

        col_names = ["id", "problem", "problem_type", "problem_complexity", "reasoning_steps_json",
                     "conclusion", "reasoning_quality", "primary_pattern", "secondary_patterns_json",
                     "pattern_effectiveness", "linked_execution_id", "was_reasoning_correct",
                     "execution_outcome_quality", "session_id", "timestamp", "duration_seconds",
                     "ai_model_used", "consolidation_status", "consolidated_at", "created_at"]
        return [self._row_to_model(dict(zip(col_names, row))) for row in (rows or [])]

    def get_reasoning_effectiveness(self) -> dict:
        """Analyze effectiveness of different reasoning patterns.

        Returns:
            dict with pattern → {avg_effectiveness, count, success_rate}
        """
        rows = self.execute("""
            SELECT
                primary_pattern,
                AVG(pattern_effectiveness) as avg_effectiveness,
                COUNT(*) as count,
                AVG(CASE WHEN was_reasoning_correct = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM thinking_traces
            WHERE primary_pattern IS NOT NULL
            GROUP BY primary_pattern
            ORDER BY avg_effectiveness DESC
        """, fetch_all=True)

        result = {}
        for row in (rows or []):
            pattern, avg_eff, count, success_rate = row
            result[pattern] = {
                "avg_effectiveness": avg_eff or 0.0,
                "count": count,
                "success_rate": success_rate or 0.0,
            }
        return result

    def get_correctness_analysis(self) -> dict:
        """Analyze correctness of reasoning vs execution outcomes.

        Returns:
            dict with:
            - total_linked: Count of thinking linked to executions
            - correct_reasoning_count: Times reasoning was correct
            - avg_reasoning_quality: Average quality of reasoning
            - avg_outcome_quality: Average quality when linked
        """
        row = self.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN was_reasoning_correct = 1 THEN 1 ELSE 0 END) as correct_count,
                AVG(reasoning_quality) as avg_reasoning_quality,
                AVG(execution_outcome_quality) as avg_outcome_quality
            FROM thinking_traces
            WHERE linked_execution_id IS NOT NULL
        """, fetch_one=True)

        if not row or row[0] == 0:
            return {
                "total_linked": 0,
                "correct_reasoning_count": 0,
                "correctness_rate": 0.0,
                "avg_reasoning_quality": 0.0,
                "avg_outcome_quality": 0.0,
            }

        total, correct_count, avg_reasoning_quality, avg_outcome_quality = row
        return {
            "total_linked": total,
            "correct_reasoning_count": correct_count,
            "correctness_rate": (correct_count / total) if total > 0 else 0.0,
            "avg_reasoning_quality": avg_reasoning_quality or 0.0,
            "avg_outcome_quality": avg_outcome_quality or 0.0,
        }

    def get_recent_thinking(self, limit: int = 10) -> list[ThinkingTrace]:
        """Get most recent thinking traces.

        Args:
            limit: Maximum number to return

        Returns:
            List of recent ThinkingTraces
        """
        rows = self.execute(
            "SELECT * FROM thinking_traces ORDER BY created_at DESC LIMIT ?",
            (limit,),
            fetch_all=True,
        )
        col_names = ["id", "problem", "problem_type", "problem_complexity", "reasoning_steps_json",
                     "conclusion", "reasoning_quality", "primary_pattern", "secondary_patterns_json",
                     "pattern_effectiveness", "linked_execution_id", "was_reasoning_correct",
                     "execution_outcome_quality", "session_id", "timestamp", "duration_seconds",
                     "ai_model_used", "consolidation_status", "consolidated_at", "created_at"]
        return [self._row_to_model(dict(zip(col_names, row))) for row in (rows or [])]

    def mark_consolidated(self, thinking_id: int) -> None:
        """Mark a thinking trace as consolidated.

        Args:
            thinking_id: Thinking trace ID
        """
        now = self.now_timestamp()
        self.execute("""
            UPDATE thinking_traces
            SET consolidation_status = 'consolidated', consolidated_at = ?
            WHERE id = ?
        """, (now, thinking_id))
        self.commit()

    def get_unconsolidated_thinking(self, limit: int = 100) -> list[ThinkingTrace]:
        """Get unconsolidated thinking traces for consolidation.

        Args:
            limit: Maximum number to return

        Returns:
            List of unconsolidated ThinkingTraces
        """
        rows = self.execute("""
            SELECT * FROM thinking_traces
            WHERE consolidation_status = 'unconsolidated'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,), fetch_all=True)
        col_names = ["id", "problem", "problem_type", "problem_complexity", "reasoning_steps_json",
                     "conclusion", "reasoning_quality", "primary_pattern", "secondary_patterns_json",
                     "pattern_effectiveness", "linked_execution_id", "was_reasoning_correct",
                     "execution_outcome_quality", "session_id", "timestamp", "duration_seconds",
                     "ai_model_used", "consolidation_status", "consolidated_at", "created_at"]
        return [self._row_to_model(dict(zip(col_names, row))) for row in (rows or [])]

