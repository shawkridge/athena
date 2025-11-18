"""Storage for learning integration - procedures, feedback, and learning cycles."""

import json
import time
from datetime import datetime
from typing import Optional

from ..core.database import Database
from .learning_integration import (
    FeedbackUpdate,
    FeedbackUpdateType,
    LearningCycle,
    LearningMetrics,
    LessonToProcedure,
    PatternType,
    ProcedureCandidate,
)


class LearningIntegrationStore:
    """Manages learning integration - closing the feedback loop.

    Provides:
    - Convert lessons to procedures
    - Find procedure candidates
    - Apply feedback to project
    - Track learning metrics
    - Support consolidation and improvement
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

        # Lessons to procedures table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons_to_procedures (
                id SERIAL PRIMARY KEY,
                lesson_id INTEGER NOT NULL,
                lesson_text TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                applies_to_json TEXT,
                pattern_type TEXT DEFAULT 'optimization',
                can_create_procedure INTEGER DEFAULT 0,
                suggested_procedure_name TEXT,
                procedure_steps_json TEXT,
                created_at INTEGER NOT NULL
            )
        """
        )

        # Procedure candidates table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS procedure_candidates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source_lessons_json TEXT,
                frequency INTEGER DEFAULT 1,
                draft_procedure_json TEXT,
                success_rate REAL DEFAULT 0.5,
                estimated_impact REAL DEFAULT 0.5,
                ready_for_creation INTEGER DEFAULT 0,
                created_procedure_id INTEGER,
                created_at INTEGER NOT NULL
            )
        """
        )

        # Feedback updates table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_updates (
                id SERIAL PRIMARY KEY,
                update_type TEXT NOT NULL,
                target_id TEXT,
                action TEXT NOT NULL,
                new_data_json TEXT,
                reason TEXT NOT NULL,
                source_lesson_id INTEGER,
                confidence REAL DEFAULT 0.5,
                applied INTEGER DEFAULT 0,
                applied_at INTEGER,
                created_at INTEGER NOT NULL
            )
        """
        )

        # Learning cycles table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_cycles (
                id SERIAL PRIMARY KEY,
                action_cycle_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                lessons_extracted INTEGER DEFAULT 0,
                high_confidence_lessons INTEGER DEFAULT 0,
                procedures_created INTEGER DEFAULT 0,
                procedure_candidates_identified INTEGER DEFAULT 0,
                feedback_updates_created INTEGER DEFAULT 0,
                feedback_updates_applied INTEGER DEFAULT 0,
                improvements_identified INTEGER DEFAULT 0,
                estimated_impact REAL DEFAULT 0.0,
                estimated_time_saved_seconds INTEGER DEFAULT 0,
                learning_cycle_success_rate REAL DEFAULT 0.0,
                created_at INTEGER NOT NULL
            )
        """
        )

        # Indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lessons_confidence
            ON lessons_to_procedures(confidence)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_candidates_ready
            ON procedure_candidates(ready_for_creation)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_applied
            ON feedback_updates(applied)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_learning_cycles_session
            ON learning_cycles(session_id)
        """
        )

        # commit handled by cursor context

    def create_lesson_to_procedure(
        self,
        lesson_id: int,
        lesson_text: str,
        confidence: float = 0.5,
        applies_to: Optional[list[str]] = None,
        pattern_type: str = "optimization",
        procedure_steps: Optional[list[str]] = None,
    ) -> LessonToProcedure:
        """Create lesson-to-procedure mapping.

        Args:
            lesson_id: Source lesson ID
            lesson_text: The lesson text
            confidence: Confidence 0.0-1.0
            applies_to: Areas this applies to
            pattern_type: Type of pattern
            procedure_steps: Draft procedure steps

        Returns:
            LessonToProcedure with ID
        """
        now_timestamp = int(time.time())
        applies_to_json = json.dumps(applies_to or [])
        procedure_steps_json = json.dumps(procedure_steps or [])
        can_create = confidence >= 0.7

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO lessons_to_procedures (
                lesson_id, lesson_text, confidence, applies_to_json,
                pattern_type, can_create_procedure, procedure_steps_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson_id,
                lesson_text,
                confidence,
                applies_to_json,
                pattern_type,
                1 if can_create else 0,
                procedure_steps_json,
                now_timestamp,
            ),
        )
        # commit handled by cursor context

        return LessonToProcedure(
            id=cursor.lastrowid,
            lesson_id=lesson_id,
            lesson_text=lesson_text,
            confidence=confidence,
            applies_to=applies_to or [],
            pattern_type=PatternType(pattern_type),
            procedure_steps=procedure_steps or [],
            created_at=datetime.fromtimestamp(now_timestamp),
        )

    def find_procedure_candidates(
        self, min_confidence: float = 0.7, min_frequency: int = 2
    ) -> list[ProcedureCandidate]:
        """Find clusters of similar lessons ready for procedures.

        Args:
            min_confidence: Minimum confidence threshold
            min_frequency: Minimum number of similar lessons

        Returns:
            List of ProcedureCandidate objects
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT
                id, name, pattern_type, confidence, source_lessons_json,
                frequency, draft_procedure_json, success_rate, estimated_impact,
                ready_for_creation, created_procedure_id, created_at
            FROM procedure_candidates
            WHERE confidence >= ? AND frequency >= ?
            ORDER BY confidence DESC, frequency DESC
            """,
            (min_confidence, min_frequency),
        )

        results = []
        for row in cursor.fetchall():
            candidate = ProcedureCandidate(
                id=row[0],
                name=row[1],
                pattern_type=PatternType(row[2]),
                confidence=row[3],
                source_lessons=json.loads(row[4]),
                draft_procedure=json.loads(row[6]),
                success_rate=row[7],
                estimated_impact=row[8],
                ready_for_creation=bool(row[9]),
                created_procedure_id=row[10],
                created_at=datetime.fromtimestamp(row[11]),
            )
            results.append(candidate)

        return results

    def create_procedure_candidate(
        self,
        name: str,
        pattern_type: str,
        confidence: float,
        source_lessons: list[int],
        draft_procedure: dict,
        success_rate: float = 0.5,
        estimated_impact: float = 0.5,
        ready_for_creation: bool = False,
    ) -> ProcedureCandidate:
        """Create a procedure candidate from grouped lessons.

        Args:
            name: Procedure name
            pattern_type: Type of pattern
            confidence: Combined confidence
            source_lessons: Lesson IDs that contributed
            draft_procedure: Draft procedure data
            success_rate: Success rate across lessons
            estimated_impact: Impact estimation
            ready_for_creation: Should auto-create?

        Returns:
            ProcedureCandidate with ID
        """
        now_timestamp = int(time.time())
        source_json = json.dumps(source_lessons)
        draft_json = json.dumps(draft_procedure)

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO procedure_candidates (
                name, pattern_type, confidence, source_lessons_json,
                frequency, draft_procedure_json, success_rate, estimated_impact,
                ready_for_creation, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                pattern_type,
                confidence,
                source_json,
                len(source_lessons),
                draft_json,
                success_rate,
                estimated_impact,
                1 if ready_for_creation else 0,
                now_timestamp,
            ),
        )
        # commit handled by cursor context

        return ProcedureCandidate(
            id=cursor.lastrowid,
            name=name,
            pattern_type=PatternType(pattern_type),
            confidence=confidence,
            source_lessons=source_lessons,
            draft_procedure=draft_procedure,
            success_rate=success_rate,
            estimated_impact=estimated_impact,
            ready_for_creation=ready_for_creation,
            created_at=datetime.fromtimestamp(now_timestamp),
        )

    def mark_procedure_created(self, candidate_id: int, procedure_id: int) -> bool:
        """Mark a candidate as having created a procedure.

        Args:
            candidate_id: ProcedureCandidate ID
            procedure_id: Created procedure ID

        Returns:
            True if updated successfully
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            UPDATE procedure_candidates
            SET created_procedure_id = ?
            WHERE id = ?
            """,
            (procedure_id, candidate_id),
        )
        # commit handled by cursor context
        return cursor.rowcount > 0

    def create_feedback_update(
        self,
        update_type: str,
        action: str,
        reason: str,
        new_data: Optional[dict] = None,
        target_id: Optional[str] = None,
        source_lesson_id: Optional[int] = None,
        confidence: float = 0.5,
    ) -> FeedbackUpdate:
        """Create a feedback update to apply to project.

        Args:
            update_type: Type of update
            action: What action (update, deprecate, replace, add)
            reason: Why this feedback
            new_data: What to update with
            target_id: Which item to update
            source_lesson_id: Which lesson triggered this
            confidence: Confidence in feedback

        Returns:
            FeedbackUpdate with ID
        """
        now_timestamp = int(time.time())
        new_data_json = json.dumps(new_data or {})

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO feedback_updates (
                update_type, target_id, action, new_data_json, reason,
                source_lesson_id, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update_type,
                target_id,
                action,
                new_data_json,
                reason,
                source_lesson_id,
                confidence,
                now_timestamp,
            ),
        )
        # commit handled by cursor context

        return FeedbackUpdate(
            id=cursor.lastrowid,
            update_type=FeedbackUpdateType(update_type),
            target_id=target_id,
            action=action,
            new_data=new_data or {},
            reason=reason,
            source_lesson_id=source_lesson_id,
            confidence=confidence,
            created_at=datetime.fromtimestamp(now_timestamp),
        )

    def get_pending_feedback(self) -> list[FeedbackUpdate]:
        """Get all unapplied feedback updates.

        Returns:
            List of FeedbackUpdate objects
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT
                id, update_type, target_id, action, new_data_json, reason,
                source_lesson_id, confidence, applied, created_at
            FROM feedback_updates
            WHERE applied = 0
            ORDER BY confidence DESC, created_at DESC
            """
        )

        results = []
        for row in cursor.fetchall():
            update = FeedbackUpdate(
                id=row[0],
                update_type=FeedbackUpdateType(row[1]),
                target_id=row[2],
                action=row[3],
                new_data=json.loads(row[4]),
                reason=row[5],
                source_lesson_id=row[6],
                confidence=row[7],
                applied=bool(row[8]),
                created_at=datetime.fromtimestamp(row[9]),
            )
            results.append(update)

        return results

    def mark_feedback_applied(self, feedback_id: int) -> bool:
        """Mark feedback as applied.

        Args:
            feedback_id: Feedback update ID

        Returns:
            True if updated successfully
        """
        now_timestamp = int(time.time())
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            UPDATE feedback_updates
            SET applied = 1, applied_at = ?
            WHERE id = ?
            """,
            (now_timestamp, feedback_id),
        )
        # commit handled by cursor context
        return cursor.rowcount > 0

    def get_lessons_by_confidence(self, min_confidence: float = 0.5) -> list[LessonToProcedure]:
        """Get lessons above confidence threshold.

        Args:
            min_confidence: Minimum confidence

        Returns:
            List of LessonToProcedure objects
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT
                id, lesson_id, lesson_text, confidence, applies_to_json,
                pattern_type, can_create_procedure, suggested_procedure_name,
                procedure_steps_json, created_at
            FROM lessons_to_procedures
            WHERE confidence >= ?
            ORDER BY confidence DESC
            """,
            (min_confidence,),
        )

        results = []
        for row in cursor.fetchall():
            lesson = LessonToProcedure(
                id=row[0],
                lesson_id=row[1],
                lesson_text=row[2],
                confidence=row[3],
                applies_to=json.loads(row[4]),
                pattern_type=PatternType(row[5]),
                suggested_procedure_name=row[7],
                procedure_steps=json.loads(row[8]),
                created_at=datetime.fromtimestamp(row[9]),
            )
            results.append(lesson)

        return results

    def create_learning_cycle(
        self,
        action_cycle_id: int,
        session_id: str,
        lessons_extracted: int = 0,
        procedures_created: int = 0,
        feedback_updates_applied: int = 0,
        estimated_impact: float = 0.0,
    ) -> LearningCycle:
        """Create learning cycle record.

        Args:
            action_cycle_id: Source action cycle
            session_id: Session ID
            lessons_extracted: Number of lessons
            procedures_created: Procedures created
            feedback_updates_applied: Feedback updates applied
            estimated_impact: Impact 0.0-1.0

        Returns:
            LearningCycle with ID
        """
        now_timestamp = int(time.time())

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO learning_cycles (
                action_cycle_id, session_id, lessons_extracted,
                procedures_created, feedback_updates_applied,
                estimated_impact, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_cycle_id,
                session_id,
                lessons_extracted,
                procedures_created,
                feedback_updates_applied,
                estimated_impact,
                now_timestamp,
            ),
        )
        # commit handled by cursor context

        return LearningCycle(
            id=cursor.lastrowid,
            action_cycle_id=action_cycle_id,
            session_id=session_id,
            lessons_extracted=lessons_extracted,
            procedures_created=procedures_created,
            feedback_updates_applied=feedback_updates_applied,
            estimated_impact=estimated_impact,
            created_at=datetime.fromtimestamp(now_timestamp),
        )

    def get_learning_cycle(self, cycle_id: int) -> Optional[LearningCycle]:
        """Get learning cycle by ID.

        Args:
            cycle_id: Learning cycle ID

        Returns:
            LearningCycle if found, None otherwise
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT
                id, action_cycle_id, session_id, lessons_extracted,
                high_confidence_lessons, procedures_created,
                procedure_candidates_identified, feedback_updates_created,
                feedback_updates_applied, improvements_identified,
                estimated_impact, estimated_time_saved_seconds,
                learning_cycle_success_rate, created_at
            FROM learning_cycles WHERE id = ?
            """,
            (cycle_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return LearningCycle(
            id=row[0],
            action_cycle_id=row[1],
            session_id=row[2],
            lessons_extracted=row[3],
            high_confidence_lessons=row[4],
            procedures_created=row[5],
            procedure_candidates_identified=row[6],
            feedback_updates_created=row[7],
            feedback_updates_applied=row[8],
            improvements_identified=row[9],
            estimated_impact=row[10],
            estimated_time_saved_seconds=row[11],
            learning_cycle_success_rate=row[12],
            created_at=datetime.fromtimestamp(row[13]),
        )

    def get_learning_cycles_for_session(
        self, session_id: str, limit: int = 10
    ) -> list[LearningCycle]:
        """Get learning cycles for a session.

        Args:
            session_id: Session ID
            limit: Maximum to return

        Returns:
            List of LearningCycle objects
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT
                id, action_cycle_id, session_id, lessons_extracted,
                high_confidence_lessons, procedures_created,
                procedure_candidates_identified, feedback_updates_created,
                feedback_updates_applied, improvements_identified,
                estimated_impact, estimated_time_saved_seconds,
                learning_cycle_success_rate, created_at
            FROM learning_cycles
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        )

        results = []
        for row in cursor.fetchall():
            cycle = LearningCycle(
                id=row[0],
                action_cycle_id=row[1],
                session_id=row[2],
                lessons_extracted=row[3],
                high_confidence_lessons=row[4],
                procedures_created=row[5],
                procedure_candidates_identified=row[6],
                feedback_updates_created=row[7],
                feedback_updates_applied=row[8],
                improvements_identified=row[9],
                estimated_impact=row[10],
                estimated_time_saved_seconds=row[11],
                learning_cycle_success_rate=row[12],
                created_at=datetime.fromtimestamp(row[13]),
            )
            results.append(cycle)

        return results

    def get_learning_metrics(self, days: int = 7) -> LearningMetrics:
        """Get aggregated learning metrics for a period.

        Args:
            days: Number of days to look back

        Returns:
            LearningMetrics object
        """
        cutoff_timestamp = int(time.time()) - (days * 86400)

        cursor = self.db.get_cursor()

        # Count lessons
        cursor.execute(
            """
            SELECT COUNT(*), AVG(confidence)
            FROM lessons_to_procedures
            WHERE created_at >= ?
            """,
            (cutoff_timestamp,),
        )
        lesson_row = cursor.fetchone()
        total_lessons = lesson_row[0] if lesson_row else 0
        avg_confidence = lesson_row[1] or 0.0

        # Count procedures
        cursor.execute(
            """
            SELECT COUNT(*), AVG(success_rate)
            FROM procedure_candidates
            WHERE created_at >= ? AND created_procedure_id IS NOT NULL
            """,
            (cutoff_timestamp,),
        )
        proc_row = cursor.fetchone()
        total_procedures = proc_row[0] if proc_row else 0
        proc_success = proc_row[1] or 0.0

        # Count feedback
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM feedback_updates
            WHERE created_at >= ? AND applied = 1
            """,
            (cutoff_timestamp,),
        )
        feedback_row = cursor.fetchone()
        total_feedback = feedback_row[0] if feedback_row else 0

        # Learning cycle metrics
        cursor.execute(
            """
            SELECT
                SUM(estimated_impact),
                SUM(estimated_time_saved_seconds),
                AVG(learning_cycle_success_rate)
            FROM learning_cycles
            WHERE created_at >= ?
            """,
            (cutoff_timestamp,),
        )
        cycle_row = cursor.fetchone()
        total_impact = cycle_row[0] or 0.0
        total_time_saved = cycle_row[1] or 0
        avg_success = cycle_row[2] or 0.0

        return LearningMetrics(
            total_lessons_extracted=total_lessons,
            total_procedures_created=total_procedures,
            total_feedback_applied=total_feedback,
            average_lesson_confidence=avg_confidence,
            procedure_success_rate=proc_success,
            feedback_application_rate=(
                total_feedback / total_lessons if total_lessons > 0 else 0.0
            ),
            estimated_time_saved_hours=total_time_saved / 3600.0,
            estimated_error_reduction_percent=min(100.0, total_impact * 100),
            period_days=days,
            measurement_period_start=datetime.fromtimestamp(cutoff_timestamp),
            measurement_period_end=datetime.now(),
        )
