"""Storage and retrieval for execution traces."""

import json
import time
from datetime import datetime
from typing import Optional

from ..core.database import Database
from .execution_traces import (
    CodeChange,
    ExecutionDecision,
    ExecutionError,
    ExecutionLesson,
    ExecutionOutcome,
    ExecutionTrace,
    QualityAssessment,
)


class ExecutionTraceStore:
    """Manages execution traces.

    Provides:
    - Record execution attempts
    - Query executions by goal/task/plan
    - Analyze execution outcomes and patterns
    - Track quality metrics
    """

    def __init__(self, db: Database):
        """Initialize store with database connection.

        Args:
            db: Database instance
        """
        self.db = db
    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Execution traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT,
                task_id TEXT,
                plan_id TEXT,
                session_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                outcome TEXT NOT NULL,
                code_changes_json TEXT,
                errors_json TEXT,
                decisions_json TEXT,
                lessons_json TEXT,
                quality_json TEXT,
                duration_seconds INTEGER DEFAULT 0,
                ai_model_used TEXT,
                tokens_used INTEGER,
                consolidation_status TEXT DEFAULT 'unconsolidated',
                consolidated_at INTEGER,
                created_at INTEGER NOT NULL
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_traces_goal
            ON execution_traces(goal_id, outcome)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_traces_task
            ON execution_traces(task_id, outcome)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_traces_session
            ON execution_traces(session_id, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_traces_outcome
            ON execution_traces(outcome, created_at DESC)
        """)

        # commit handled by cursor context

    def record_execution(self, trace: ExecutionTrace) -> int:
        """Record an execution attempt.

        Args:
            trace: ExecutionTrace to record

        Returns:
            ID of inserted execution
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)  # Milliseconds

        # Get outcome value (handles both enum and string)
        outcome_value = trace.outcome.value if hasattr(trace.outcome, 'value') else trace.outcome

        cursor.execute("""
            INSERT INTO execution_traces
            (goal_id, task_id, plan_id, session_id, timestamp, action_type, description,
             outcome, code_changes_json, errors_json, decisions_json, lessons_json,
             quality_json, duration_seconds, ai_model_used, tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace.goal_id,
            trace.task_id,
            trace.plan_id,
            trace.session_id,
            int(trace.timestamp.timestamp() * 1000),
            trace.action_type,
            trace.description,
            outcome_value,
            json.dumps([c.dict() for c in trace.code_changes]),
            json.dumps([e.dict() for e in trace.errors]),
            json.dumps([d.dict() for d in trace.decisions]),
            json.dumps([l.dict() for l in trace.lessons]),
            json.dumps(trace.quality_assessment.dict()) if trace.quality_assessment else None,
            trace.duration_seconds,
            trace.ai_model_used,
            trace.tokens_used,
            now
        ))

        # commit handled by cursor context
        return cursor.lastrowid

    def get_execution(self, execution_id: int) -> Optional[ExecutionTrace]:
        """Retrieve an execution trace.

        Args:
            execution_id: Execution ID

        Returns:
            ExecutionTrace or None if not found
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM execution_traces WHERE id = ?",
            (execution_id,)
        )
        row = cursor.fetchone()
        return self._row_to_execution(row) if row else None

    def get_executions_for_goal(self, goal_id: str) -> list[ExecutionTrace]:
        """Get all executions for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            List of ExecutionTrace instances
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT * FROM execution_traces
            WHERE goal_id = ?
            ORDER BY timestamp DESC
        """, (goal_id,))

        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def get_executions_for_task(self, task_id: str) -> list[ExecutionTrace]:
        """Get all executions for a task.

        Args:
            task_id: Task UUID

        Returns:
            List of ExecutionTrace instances
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT * FROM execution_traces
            WHERE task_id = ?
            ORDER BY timestamp DESC
        """, (task_id,))

        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def get_executions_by_outcome(self, goal_id: str, outcome: ExecutionOutcome) -> list[ExecutionTrace]:
        """Get executions by outcome for a goal.

        Args:
            goal_id: Goal UUID
            outcome: ExecutionOutcome filter

        Returns:
            List of ExecutionTrace instances
        """
        cursor = self.db.get_cursor()
        # Get outcome value (handles both enum and string)
        outcome_value = outcome.value if hasattr(outcome, 'value') else outcome

        cursor.execute("""
            SELECT * FROM execution_traces
            WHERE goal_id = ? AND outcome = ?
            ORDER BY timestamp DESC
        """, (goal_id, outcome_value))

        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def get_successful_executions(self, goal_id: str) -> list[ExecutionTrace]:
        """Get successful executions for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            List of successful ExecutionTrace instances
        """
        return self.get_executions_by_outcome(goal_id, ExecutionOutcome.SUCCESS)

    def get_failed_executions(self, goal_id: str) -> list[ExecutionTrace]:
        """Get failed executions for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            List of failed ExecutionTrace instances
        """
        return self.get_executions_by_outcome(goal_id, ExecutionOutcome.FAILURE)

    def get_recent_executions(self, limit: int = 10) -> list[ExecutionTrace]:
        """Get recent executions across all goals.

        Args:
            limit: Maximum executions to return

        Returns:
            List of ExecutionTrace instances
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT * FROM execution_traces
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def calculate_success_rate(self, goal_id: str) -> float:
        """Calculate success rate for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            Success rate (0.0-1.0)
        """
        cursor = self.db.get_cursor()

        # Total executions
        cursor.execute(
            "SELECT COUNT(*) FROM execution_traces WHERE goal_id = ?",
            (goal_id,)
        )
        total = cursor.fetchone()[0]

        if total == 0:
            return 0.0

        # Successful executions
        success_value = ExecutionOutcome.SUCCESS.value if hasattr(ExecutionOutcome.SUCCESS, 'value') else ExecutionOutcome.SUCCESS

        cursor.execute(
            "SELECT COUNT(*) FROM execution_traces WHERE goal_id = ? AND outcome = ?",
            (goal_id, success_value)
        )
        successful = cursor.fetchone()[0]

        return successful / total if total > 0 else 0.0

    def get_quality_metrics(self, goal_id: str) -> dict:
        """Get average quality metrics for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            Dict with average quality scores
        """
        executions = self.get_executions_for_goal(goal_id)

        if not executions:
            return {
                "code_quality": 0.0,
                "approach_quality": 0.0,
                "efficiency": 0.0,
                "correctness": 0.0,
            }

        # Filter executions with quality assessment
        with_quality = [e for e in executions if e.quality_assessment]

        if not with_quality:
            return {
                "code_quality": 0.0,
                "approach_quality": 0.0,
                "efficiency": 0.0,
                "correctness": 0.0,
            }

        return {
            "code_quality": sum(e.quality_assessment.code_quality for e in with_quality) / len(with_quality),
            "approach_quality": sum(e.quality_assessment.approach_quality for e in with_quality) / len(with_quality),
            "efficiency": sum(e.quality_assessment.efficiency for e in with_quality) / len(with_quality),
            "correctness": sum(e.quality_assessment.correctness for e in with_quality) / len(with_quality),
        }

    def get_common_errors(self, goal_id: str) -> dict:
        """Get common error patterns for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            Dict mapping error_type to count
        """
        executions = self.get_executions_for_goal(goal_id)

        error_counts = {}
        for execution in executions:
            for error in execution.errors:
                error_type = error.error_type
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        # Sort by frequency
        return dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True))

    def get_lessons_learned(self, goal_id: str) -> list[ExecutionLesson]:
        """Get all lessons learned for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            List of ExecutionLesson instances
        """
        executions = self.get_successful_executions(goal_id)

        lessons = []
        for execution in executions:
            lessons.extend(execution.lessons)

        # Sort by confidence
        return sorted(lessons, key=lambda l: l.confidence, reverse=True)

    def mark_consolidated(self, execution_id: int) -> None:
        """Mark an execution as consolidated.

        Args:
            execution_id: Execution ID
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)

        cursor.execute("""
            UPDATE execution_traces
            SET consolidation_status = ?, consolidated_at = ?
            WHERE id = ?
        """, ("consolidated", now, execution_id))

        # commit handled by cursor context

    def get_unconsolidated_executions(self, goal_id: str) -> list[ExecutionTrace]:
        """Get unconsolidated executions for a goal.

        Args:
            goal_id: Goal UUID

        Returns:
            List of unconsolidated ExecutionTrace instances
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT * FROM execution_traces
            WHERE goal_id = ? AND consolidation_status = 'unconsolidated'
            ORDER BY timestamp DESC
        """, (goal_id,))

        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def _row_to_execution(self, row: tuple) -> ExecutionTrace:
        """Convert database row to ExecutionTrace.

        Args:
            row: Database row tuple

        Returns:
            ExecutionTrace instance
        """
        # Convert outcome string to enum
        outcome_value = row[8]
        outcome = ExecutionOutcome(outcome_value)

        return ExecutionTrace(
            id=row[0],
            goal_id=row[1],
            task_id=row[2],
            plan_id=row[3],
            session_id=row[4],
            timestamp=datetime.fromtimestamp(row[5] / 1000),
            action_type=row[6],
            description=row[7],
            outcome=outcome,
            code_changes=[CodeChange(**c) for c in json.loads(row[9] or "[]")],
            errors=[ExecutionError(**e) for e in json.loads(row[10] or "[]")],
            decisions=[ExecutionDecision(**d) for d in json.loads(row[11] or "[]")],
            lessons=[ExecutionLesson(**l) for l in json.loads(row[12] or "[]")],
            quality_assessment=QualityAssessment(**json.loads(row[13])) if row[13] else None,
            duration_seconds=row[14],
            ai_model_used=row[15],
            tokens_used=row[16],
            consolidation_status=row[17],
            consolidated_at=datetime.fromtimestamp(row[18] / 1000) if row[18] else None,
        )
