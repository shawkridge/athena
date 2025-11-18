"""Storage and orchestration for action cycles."""

import json
import time
from datetime import datetime
from typing import Optional

from ..core.database import Database
from .action_cycles import (
    ActionCycle,
    CycleStatus,
    ExecutionSummary,
    LessonLearned,
    PlanAdjustment,
    PlanAssumption,
)


class ActionCycleStore:
    """Manages action cycles and orchestration.

    Provides:
    - Create and manage action cycles
    - Record execution results
    - Detect failures and trigger replanning
    - Extract lessons learned
    - Calculate success metrics
    - Support for multi-attempt orchestration
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

        # Action cycles table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_cycles (
                id SERIAL PRIMARY KEY,
                goal_id TEXT,
                goal_description TEXT NOT NULL,
                goal_priority REAL DEFAULT 5.0,
                plan_description TEXT NOT NULL,
                plan_quality REAL DEFAULT 0.5,
                plan_assumptions_json TEXT,
                max_attempts INTEGER DEFAULT 5,
                current_attempt INTEGER DEFAULT 1,
                total_executions INTEGER DEFAULT 0,
                successful_executions INTEGER DEFAULT 0,
                failed_executions INTEGER DEFAULT 0,
                partial_executions INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                lessons_json TEXT,
                plan_adjustments_json TEXT,
                replanning_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'planning',
                reason_abandoned TEXT,
                session_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                started_execution_at INTEGER,
                completed_at INTEGER,
                consolidation_status TEXT DEFAULT 'unconsolidated',
                consolidated_at INTEGER
            )
        """
        )

        # Executions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cycle_executions (
                id SERIAL PRIMARY KEY,
                cycle_id INTEGER NOT NULL,
                attempt_number INTEGER NOT NULL,
                execution_id TEXT,
                outcome TEXT NOT NULL,
                duration_seconds INTEGER DEFAULT 0,
                code_changes_count INTEGER DEFAULT 0,
                errors_encountered INTEGER DEFAULT 0,
                lessons_json TEXT,
                timestamp INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (cycle_id) REFERENCES action_cycles(id)
            )
        """
        )

        # Indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_action_cycles_goal
            ON action_cycles(goal_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_action_cycles_status
            ON action_cycles(status)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_action_cycles_session
            ON action_cycles(session_id, created_at DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cycle_executions_cycle
            ON cycle_executions(cycle_id, attempt_number DESC)
        """
        )

        # commit handled by cursor context

    def create_cycle(
        self,
        goal_description: str,
        plan_description: str,
        session_id: str,
        goal_id: Optional[str] = None,
        goal_priority: float = 5.0,
        plan_quality: float = 0.5,
        plan_assumptions: list[PlanAssumption] = None,
        max_attempts: int = 5,
    ) -> int:
        """Create a new action cycle.

        Args:
            goal_description: Human-readable goal
            plan_description: Human-readable plan
            session_id: Session ID
            goal_id: Optional UUID of goal
            goal_priority: Priority (1-10)
            plan_quality: Quality estimate (0.0-1.0)
            plan_assumptions: List of assumptions
            max_attempts: Maximum attempts allowed

        Returns:
            ID of created cycle
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)

        # Serialize assumptions
        assumptions_json = None
        if plan_assumptions:
            assumptions_json = json.dumps([a.dict() for a in plan_assumptions])

        cursor.execute(
            """
            INSERT INTO action_cycles
            (goal_id, goal_description, goal_priority, plan_description, plan_quality,
             plan_assumptions_json, max_attempts, session_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                goal_id,
                goal_description,
                goal_priority,
                plan_description,
                plan_quality,
                assumptions_json,
                max_attempts,
                session_id,
                CycleStatus.PLANNING.value,
                now,
            ),
        )

        # commit handled by cursor context
        return cursor.lastrowid

    def get_cycle(self, cycle_id: int) -> Optional[ActionCycle]:
        """Retrieve an action cycle.

        Args:
            cycle_id: Cycle ID

        Returns:
            ActionCycle or None if not found
        """
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM action_cycles WHERE id = ?", (cycle_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_cycle(row)

    def get_active_cycle(self, goal_id: str) -> Optional[ActionCycle]:
        """Get active cycle for a goal.

        Args:
            goal_id: Goal ID (UUID as string)

        Returns:
            ActionCycle if found and active, None otherwise
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """SELECT * FROM action_cycles
               WHERE goal_id = ? AND status IN ('planning', 'executing', 'learning')
               ORDER BY created_at DESC LIMIT 1""",
            (goal_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_cycle(row)

    def get_cycles_for_goal(self, goal_id: str) -> list[ActionCycle]:
        """Get all cycles for a goal.

        Args:
            goal_id: Goal ID (UUID as string)

        Returns:
            List of ActionCycles
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM action_cycles WHERE goal_id = ? ORDER BY created_at DESC", (goal_id,)
        )
        return [self._row_to_cycle(row) for row in cursor.fetchall()]

    def start_execution(self, cycle_id: int) -> None:
        """Mark cycle as starting execution phase.

        Args:
            cycle_id: Cycle ID
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)
        cursor.execute(
            """
            UPDATE action_cycles
            SET status = ?, started_execution_at = ?
            WHERE id = ?
        """,
            (CycleStatus.EXECUTING.value, now, cycle_id),
        )
        # commit handled by cursor context

    def record_execution_result(
        self,
        cycle_id: int,
        attempt_number: int,
        outcome: str,  # "success", "failure", "partial"
        execution_id: Optional[str] = None,
        duration_seconds: int = 0,
        code_changes_count: int = 0,
        errors_encountered: int = 0,
        lessons_from_attempt: list[str] = None,
    ) -> int:
        """Record result of an execution attempt.

        Args:
            cycle_id: Cycle ID
            attempt_number: Which attempt (1-based)
            outcome: "success", "failure", "partial"
            execution_id: Optional ExecutionTrace ID (UUID as string)
            duration_seconds: How long execution took
            code_changes_count: Number of code changes
            errors_encountered: Number of errors
            lessons_from_attempt: Lessons from this attempt

        Returns:
            ID of execution record
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)

        lessons_json = None
        if lessons_from_attempt:
            lessons_json = json.dumps(lessons_from_attempt)

        # Record execution
        cursor.execute(
            """
            INSERT INTO cycle_executions
            (cycle_id, attempt_number, execution_id, outcome, duration_seconds,
             code_changes_count, errors_encountered, lessons_json, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                cycle_id,
                attempt_number,
                execution_id,
                outcome,
                duration_seconds,
                code_changes_count,
                errors_encountered,
                lessons_json,
                now,
                now,
            ),
        )

        exec_id = cursor.lastrowid

        # Update cycle metrics
        cycle = self.get_cycle(cycle_id)
        if cycle:
            # Increment appropriate counter
            new_total = cycle.total_executions + 1
            new_successful = cycle.successful_executions + (1 if outcome == "success" else 0)
            new_failed = cycle.failed_executions + (1 if outcome == "failure" else 0)
            new_partial = cycle.partial_executions + (1 if outcome == "partial" else 0)
            new_success_rate = new_successful / new_total if new_total > 0 else 0.0

            cursor.execute(
                """
                UPDATE action_cycles
                SET total_executions = ?, successful_executions = ?,
                    failed_executions = ?, partial_executions = ?,
                    success_rate = ?, current_attempt = ?
                WHERE id = ?
            """,
                (
                    new_total,
                    new_successful,
                    new_failed,
                    new_partial,
                    new_success_rate,
                    attempt_number + 1,
                    cycle_id,
                ),
            )

        # commit handled by cursor context
        return exec_id

    def should_replan(self, cycle_id: int) -> bool:
        """Determine if replanning is needed.

        Replanning is triggered when:
        - Last execution failed
        - Success rate is too low
        - Multiple consecutive failures
        - Assumptions were violated

        Args:
            cycle_id: Cycle ID

        Returns:
            True if replanning should be triggered
        """
        cycle = self.get_cycle(cycle_id)
        if not cycle or cycle.total_executions == 0:
            return False

        # Get last execution
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT outcome FROM cycle_executions WHERE cycle_id = ? ORDER BY attempt_number DESC LIMIT 1",
            (cycle_id,),
        )
        last_result = cursor.fetchone()

        if not last_result:
            return False

        last_outcome = last_result[0]

        # Trigger replanning on:
        # 1. Any failure
        if last_outcome == "failure":
            return True

        # 2. Low success rate after multiple attempts
        if cycle.total_executions >= 3 and cycle.success_rate < 0.5:
            return True

        # 3. Two consecutive failures
        if cycle.total_executions >= 2:
            cursor.execute(
                """
                SELECT outcome FROM cycle_executions
                WHERE cycle_id = ? ORDER BY attempt_number DESC LIMIT 2
            """,
                (cycle_id,),
            )
            last_two = cursor.fetchall()
            if len(last_two) == 2 and last_two[0][0] == "failure" and last_two[1][0] == "failure":
                return True

        return False

    def trigger_replan(
        self,
        cycle_id: int,
        new_plan_description: str,
        new_plan_quality: float = 0.5,
        reason: str = "Previous attempt failed",
    ) -> None:
        """Trigger replanning.

        Args:
            cycle_id: Cycle ID
            new_plan_description: New plan
            new_plan_quality: Quality of new plan
            reason: Why replanning was triggered
        """
        cycle = self.get_cycle(cycle_id)
        if not cycle:
            return

        cursor = self.db.get_cursor()

        # Add plan adjustment
        adjustment = PlanAdjustment(
            adjustment=new_plan_description,
            reason=reason,
            triggered_by_attempt=cycle.current_attempt,
            confidence=new_plan_quality,
        )

        # Update plan and increment replan count
        new_adjustments = cycle.plan_adjustments + [adjustment]
        adjustments_json = json.dumps([a.dict() for a in new_adjustments])

        cursor.execute(
            """
            UPDATE action_cycles
            SET plan_description = ?, plan_quality = ?,
                plan_adjustments_json = ?, replanning_count = ?
            WHERE id = ?
        """,
            (
                new_plan_description,
                new_plan_quality,
                adjustments_json,
                cycle.replanning_count + 1,
                cycle_id,
            ),
        )

        # commit handled by cursor context

    def add_lesson(
        self,
        cycle_id: int,
        lesson: str,
        source_attempt: int,
        confidence: float = 0.5,
        applies_to: list[str] = None,
        can_create_procedure: bool = False,
    ) -> None:
        """Add a lesson learned to cycle.

        Args:
            cycle_id: Cycle ID
            lesson: What was learned?
            source_attempt: Which attempt yielded this?
            confidence: Confidence in lesson (0.0-1.0)
            applies_to: What domains does this apply to?
            can_create_procedure: Can this become a procedure?
        """
        cycle = self.get_cycle(cycle_id)
        if not cycle:
            return

        new_lesson = LessonLearned(
            lesson=lesson,
            source_attempt=source_attempt,
            confidence=confidence,
            applies_to=applies_to or [],
            can_create_procedure=can_create_procedure,
        )

        new_lessons = cycle.lessons_learned + [new_lesson]
        lessons_json = json.dumps([l.dict() for l in new_lessons])

        cursor = self.db.get_cursor()
        cursor.execute(
            "UPDATE action_cycles SET lessons_json = ? WHERE id = ?", (lessons_json, cycle_id)
        )
        # commit handled by cursor context

    def complete_cycle(
        self,
        cycle_id: int,
        final_status: str = "completed",
        reason_if_abandoned: Optional[str] = None,
    ) -> None:
        """Complete an action cycle.

        Args:
            cycle_id: Cycle ID
            final_status: "completed" or "abandoned"
            reason_if_abandoned: Why was it abandoned?
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)

        cursor.execute(
            """
            UPDATE action_cycles
            SET status = ?, completed_at = ?, reason_abandoned = ?
            WHERE id = ?
        """,
            (final_status, now, reason_if_abandoned, cycle_id),
        )

        # commit handled by cursor context

    def abandon_cycle(
        self,
        cycle_id: int,
        reason: str,
    ) -> None:
        """Abandon a cycle (max attempts exceeded or other reason).

        Args:
            cycle_id: Cycle ID
            reason: Why was it abandoned?
        """
        self.complete_cycle(cycle_id, final_status="abandoned", reason_if_abandoned=reason)

    def get_execution_summary(self, cycle_id: int) -> dict:
        """Get summary of all executions in a cycle.

        Args:
            cycle_id: Cycle ID

        Returns:
            dict with execution statistics
        """
        cycle = self.get_cycle(cycle_id)
        if not cycle:
            return {}

        return {
            "total_attempts": cycle.total_executions,
            "successful": cycle.successful_executions,
            "failed": cycle.failed_executions,
            "partial": cycle.partial_executions,
            "success_rate": cycle.success_rate,
            "replanning_count": cycle.replanning_count,
            "max_attempts": cycle.max_attempts,
            "lessons_learned_count": len(cycle.lessons_learned),
        }

    def get_active_cycles(self, session_id: str) -> list[ActionCycle]:
        """Get all active cycles in a session.

        Args:
            session_id: Session ID

        Returns:
            List of active ActionCycles
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM action_cycles
            WHERE session_id = ? AND status IN ('planning', 'executing', 'learning')
            ORDER BY created_at DESC
        """,
            (session_id,),
        )
        return [self._row_to_cycle(row) for row in cursor.fetchall()]

    def mark_consolidated(self, cycle_id: int) -> None:
        """Mark a cycle as consolidated.

        Args:
            cycle_id: Cycle ID
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)
        cursor.execute(
            """
            UPDATE action_cycles
            SET consolidation_status = 'consolidated', consolidated_at = ?
            WHERE id = ?
        """,
            (now, cycle_id),
        )
        # commit handled by cursor context

    def get_unconsolidated_cycles(self, limit: int = 100) -> list[ActionCycle]:
        """Get unconsolidated cycles for consolidation.

        Args:
            limit: Maximum number to return

        Returns:
            List of unconsolidated ActionCycles
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM action_cycles
            WHERE consolidation_status = 'unconsolidated'
            ORDER BY created_at ASC
            LIMIT ?
        """,
            (limit,),
        )
        return [self._row_to_cycle(row) for row in cursor.fetchall()]

    def _row_to_cycle(self, row: tuple) -> ActionCycle:
        """Convert database row to ActionCycle object.

        Args:
            row: Database row tuple

        Returns:
            ActionCycle instance
        """
        (
            id_,
            goal_id,
            goal_description,
            goal_priority,
            plan_description,
            plan_quality,
            plan_assumptions_json,
            max_attempts,
            current_attempt,
            total_executions,
            successful_executions,
            failed_executions,
            partial_executions,
            success_rate,
            lessons_json,
            plan_adjustments_json,
            replanning_count,
            status,
            reason_abandoned,
            session_id,
            created_at,
            started_execution_at,
            completed_at,
            consolidation_status,
            consolidated_at,
        ) = row

        # Parse assumptions
        plan_assumptions = []
        if plan_assumptions_json:
            for assumption_data in json.loads(plan_assumptions_json):
                plan_assumptions.append(PlanAssumption(**assumption_data))

        # Parse lessons
        lessons = []
        if lessons_json:
            for lesson_data in json.loads(lessons_json):
                lessons.append(LessonLearned(**lesson_data))

        # Parse plan adjustments
        adjustments = []
        if plan_adjustments_json:
            for adj_data in json.loads(plan_adjustments_json):
                adjustments.append(PlanAdjustment(**adj_data))

        # Get executions for this cycle
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT attempt_number, execution_id, outcome, duration_seconds,
                   code_changes_count, errors_encountered, lessons_json, timestamp
            FROM cycle_executions
            WHERE cycle_id = ? ORDER BY attempt_number ASC
        """,
            (id_,),
        )

        executions = []
        for exec_row in cursor.fetchall():
            (
                attempt_num,
                exec_id,
                outcome,
                duration,
                changes,
                errors,
                exec_lessons_json,
                timestamp,
            ) = exec_row

            exec_lessons = []
            if exec_lessons_json:
                exec_lessons = json.loads(exec_lessons_json)

            executions.append(
                ExecutionSummary(
                    attempt_number=attempt_num,
                    execution_id=exec_id,
                    outcome=outcome,
                    duration_seconds=duration,
                    code_changes_count=changes,
                    errors_encountered=errors,
                    lessons_from_attempt=exec_lessons,
                    timestamp=datetime.fromtimestamp(timestamp / 1000),
                )
            )

        return ActionCycle(
            id=id_,
            goal_id=goal_id,
            goal_description=goal_description,
            goal_priority=goal_priority,
            plan_description=plan_description,
            plan_quality=plan_quality,
            plan_assumptions=plan_assumptions,
            max_attempts=max_attempts,
            current_attempt=current_attempt,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            partial_executions=partial_executions,
            success_rate=success_rate,
            executions=executions,
            lessons_learned=lessons,
            plan_adjustments=adjustments,
            replanning_count=replanning_count,
            status=CycleStatus(status),
            reason_abandoned=reason_abandoned,
            session_id=session_id,
            created_at=datetime.fromtimestamp(created_at / 1000),
            started_execution_at=(
                datetime.fromtimestamp(started_execution_at / 1000)
                if started_execution_at
                else None
            ),
            completed_at=datetime.fromtimestamp(completed_at / 1000) if completed_at else None,
            consolidation_status=consolidation_status,
            consolidated_at=(
                datetime.fromtimestamp(consolidated_at / 1000) if consolidated_at else None
            ),
        )
