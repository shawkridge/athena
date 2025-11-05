"""Unit tests for execution traces layer."""

import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from athena.ai_coordination.execution_traces import (
    CodeChange,
    ExecutionDecision,
    ExecutionError,
    ExecutionLesson,
    ExecutionOutcome,
    ExecutionTrace,
    QualityAssessment,
)
from athena.ai_coordination.execution_trace_store import ExecutionTraceStore
from athena.core.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        yield db
        db.conn.close()


@pytest.fixture
def store(temp_db):
    """Create an ExecutionTraceStore with temporary database."""
    return ExecutionTraceStore(temp_db)


@pytest.fixture
def goal_id():
    """Generate a unique goal ID."""
    return str(uuid4())


@pytest.fixture
def task_id():
    """Generate a unique task ID."""
    return str(uuid4())


@pytest.fixture
def plan_id():
    """Generate a unique plan ID."""
    return str(uuid4())


class TestExecutionTraceStore:
    """Tests for ExecutionTraceStore."""

    def test_record_execution_success(self, store, goal_id, task_id, plan_id):
        """Test recording a successful execution."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            task_id=task_id,
            plan_id=plan_id,
            session_id="test_session",
            action_type="code_generation",
            description="Implemented async database wrapper",
            outcome=ExecutionOutcome.SUCCESS,
            duration_seconds=300,
            ai_model_used="claude-3-sonnet",
            tokens_used=2500,
        )

        execution_id = store.record_execution(trace)

        assert execution_id is not None
        assert isinstance(execution_id, int)

    def test_record_execution_with_changes(self, store, goal_id):
        """Test recording execution with code changes."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="test_session",
            action_type="refactoring",
            description="Refactored database layer",
            outcome=ExecutionOutcome.SUCCESS,
            code_changes=[
                CodeChange(file_path="db.py", lines_added=50, lines_deleted=30),
                CodeChange(file_path="models.py", lines_added=20, lines_deleted=10),
            ],
        )

        execution_id = store.record_execution(trace)
        retrieved = store.get_execution(execution_id)

        assert len(retrieved.code_changes) == 2
        assert retrieved.code_changes[0].file_path == "db.py"
        assert retrieved.code_changes[0].lines_added == 50

    def test_record_execution_with_errors(self, store, goal_id):
        """Test recording execution with errors."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="test_session",
            action_type="testing",
            description="Test run",
            outcome=ExecutionOutcome.FAILURE,
            errors=[
                ExecutionError(
                    error_type="test",
                    message="Expected 5 but got 4",
                    file_path="test_db.py",
                    line_number=42,
                ),
            ],
        )

        execution_id = store.record_execution(trace)
        retrieved = store.get_execution(execution_id)

        assert len(retrieved.errors) == 1
        assert retrieved.errors[0].error_type == "test"
        assert retrieved.errors[0].message == "Expected 5 but got 4"

    def test_record_execution_with_lessons(self, store, goal_id):
        """Test recording execution with lessons learned."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="test_session",
            action_type="code_generation",
            description="Implemented async pattern",
            outcome=ExecutionOutcome.SUCCESS,
            lessons=[
                ExecutionLesson(
                    lesson="Always use context managers for database connections",
                    confidence=0.95,
                    applies_to=["async code", "database operations"],
                ),
            ],
        )

        execution_id = store.record_execution(trace)
        retrieved = store.get_execution(execution_id)

        assert len(retrieved.lessons) == 1
        assert retrieved.lessons[0].lesson == "Always use context managers for database connections"
        assert 0.95 in [retrieved.lessons[0].confidence]

    def test_record_execution_with_quality(self, store, goal_id):
        """Test recording execution with quality assessment."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="test_session",
            action_type="code_generation",
            description="Implemented feature",
            outcome=ExecutionOutcome.SUCCESS,
            quality_assessment=QualityAssessment(
                code_quality=0.9,
                approach_quality=0.85,
                efficiency=0.8,
                correctness=1.0,
            ),
        )

        execution_id = store.record_execution(trace)
        retrieved = store.get_execution(execution_id)

        assert retrieved.quality_assessment is not None
        assert retrieved.quality_assessment.code_quality == 0.9
        assert retrieved.quality_assessment.correctness == 1.0

    def test_get_execution_not_found(self, store):
        """Test retrieving non-existent execution."""
        retrieved = store.get_execution(99999)
        assert retrieved is None

    def test_get_executions_for_goal(self, store, goal_id):
        """Test retrieving all executions for a goal."""
        import time

        # Record multiple executions for same goal with delays to ensure ordering
        for i in range(3):
            trace = ExecutionTrace(
                goal_id=goal_id,
                session_id=f"session_{i}",
                action_type="code_generation",
                description=f"Attempt {i}",
                outcome=ExecutionOutcome.SUCCESS if i < 2 else ExecutionOutcome.FAILURE,
            )
            store.record_execution(trace)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        executions = store.get_executions_for_goal(goal_id)

        assert len(executions) == 3
        assert executions[0].description == "Attempt 2"  # Most recent first
        assert executions[-1].description == "Attempt 0"  # Oldest last

    def test_get_executions_for_task(self, store, task_id):
        """Test retrieving executions for a task."""
        trace1 = ExecutionTrace(
            task_id=task_id,
            session_id="session_1",
            action_type="code_generation",
            description="Task attempt 1",
            outcome=ExecutionOutcome.SUCCESS,
        )
        trace2 = ExecutionTrace(
            task_id=task_id,
            session_id="session_2",
            action_type="debugging",
            description="Task attempt 2",
            outcome=ExecutionOutcome.FAILURE,
        )

        store.record_execution(trace1)
        store.record_execution(trace2)

        executions = store.get_executions_for_task(task_id)

        assert len(executions) == 2

    def test_get_executions_by_outcome(self, store, goal_id):
        """Test filtering executions by outcome."""
        # Record successes
        for i in range(2):
            trace = ExecutionTrace(
                goal_id=goal_id,
                session_id=f"success_{i}",
                action_type="code_generation",
                description=f"Success {i}",
                outcome=ExecutionOutcome.SUCCESS,
            )
            store.record_execution(trace)

        # Record failures
        for i in range(2):
            trace = ExecutionTrace(
                goal_id=goal_id,
                session_id=f"failure_{i}",
                action_type="testing",
                description=f"Failure {i}",
                outcome=ExecutionOutcome.FAILURE,
            )
            store.record_execution(trace)

        successes = store.get_executions_by_outcome(goal_id, ExecutionOutcome.SUCCESS)
        failures = store.get_executions_by_outcome(goal_id, ExecutionOutcome.FAILURE)

        assert len(successes) == 2
        assert len(failures) == 2

    def test_get_successful_executions(self, store, goal_id):
        """Test getting only successful executions."""
        executions = store.get_successful_executions(goal_id)
        assert len(executions) == 0

        # Add some executions
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="success",
            action_type="code_generation",
            description="Success",
            outcome=ExecutionOutcome.SUCCESS,
        )
        store.record_execution(trace)

        executions = store.get_successful_executions(goal_id)
        assert len(executions) == 1
        assert executions[0].outcome == ExecutionOutcome.SUCCESS

    def test_get_recent_executions(self, store, goal_id):
        """Test getting recent executions."""
        for i in range(5):
            trace = ExecutionTrace(
                goal_id=goal_id,
                session_id=f"session_{i}",
                action_type="code_generation",
                description=f"Execution {i}",
                outcome=ExecutionOutcome.SUCCESS,
            )
            store.record_execution(trace)

        recent = store.get_recent_executions(limit=3)

        assert len(recent) == 3

    def test_calculate_success_rate_no_executions(self, store, goal_id):
        """Test success rate with no executions."""
        rate = store.calculate_success_rate(goal_id)
        assert rate == 0.0

    def test_calculate_success_rate_all_success(self, store, goal_id):
        """Test success rate with all successes."""
        for i in range(3):
            trace = ExecutionTrace(
                goal_id=goal_id,
                session_id=f"session_{i}",
                action_type="code_generation",
                description=f"Success {i}",
                outcome=ExecutionOutcome.SUCCESS,
            )
            store.record_execution(trace)

        rate = store.calculate_success_rate(goal_id)
        assert rate == 1.0

    def test_calculate_success_rate_mixed(self, store, goal_id):
        """Test success rate with mixed outcomes."""
        # Record 2 successes, 1 failure = 2/3
        trace1 = ExecutionTrace(
            goal_id=goal_id,
            session_id="success_1",
            action_type="code_generation",
            description="Success 1",
            outcome=ExecutionOutcome.SUCCESS,
        )
        trace2 = ExecutionTrace(
            goal_id=goal_id,
            session_id="failure",
            action_type="testing",
            description="Failure",
            outcome=ExecutionOutcome.FAILURE,
        )
        trace3 = ExecutionTrace(
            goal_id=goal_id,
            session_id="success_2",
            action_type="code_generation",
            description="Success 2",
            outcome=ExecutionOutcome.SUCCESS,
        )

        store.record_execution(trace1)
        store.record_execution(trace2)
        store.record_execution(trace3)

        rate = store.calculate_success_rate(goal_id)
        assert abs(rate - 2/3) < 0.01

    def test_get_quality_metrics_no_assessments(self, store, goal_id):
        """Test quality metrics with no assessments."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="session",
            action_type="code_generation",
            description="No quality assessment",
            outcome=ExecutionOutcome.SUCCESS,
        )
        store.record_execution(trace)

        metrics = store.get_quality_metrics(goal_id)

        assert all(v == 0.0 for v in metrics.values())

    def test_get_quality_metrics_with_assessments(self, store, goal_id):
        """Test quality metrics with assessments."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="session",
            action_type="code_generation",
            description="With quality",
            outcome=ExecutionOutcome.SUCCESS,
            quality_assessment=QualityAssessment(
                code_quality=0.9,
                approach_quality=0.8,
                efficiency=0.7,
                correctness=1.0,
            ),
        )
        store.record_execution(trace)

        metrics = store.get_quality_metrics(goal_id)

        assert metrics["code_quality"] == 0.9
        assert metrics["approach_quality"] == 0.8
        assert metrics["efficiency"] == 0.7
        assert metrics["correctness"] == 1.0

    def test_get_common_errors(self, store, goal_id):
        """Test getting common error patterns."""
        # Record executions with errors
        trace1 = ExecutionTrace(
            goal_id=goal_id,
            session_id="session_1",
            action_type="testing",
            description="Test failure",
            outcome=ExecutionOutcome.FAILURE,
            errors=[
                ExecutionError(error_type="test", message="Test failed"),
                ExecutionError(error_type="test", message="Another test failed"),
            ],
        )
        trace2 = ExecutionTrace(
            goal_id=goal_id,
            session_id="session_2",
            action_type="testing",
            description="Another failure",
            outcome=ExecutionOutcome.FAILURE,
            errors=[
                ExecutionError(error_type="type", message="Type mismatch"),
            ],
        )

        store.record_execution(trace1)
        store.record_execution(trace2)

        errors = store.get_common_errors(goal_id)

        assert errors["test"] == 2
        assert errors["type"] == 1

    def test_get_lessons_learned(self, store, goal_id):
        """Test getting lessons learned from successful executions."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="session",
            action_type="code_generation",
            description="Successful implementation",
            outcome=ExecutionOutcome.SUCCESS,
            lessons=[
                ExecutionLesson(
                    lesson="Use context managers",
                    confidence=0.9,
                ),
                ExecutionLesson(
                    lesson="Handle edge cases",
                    confidence=0.8,
                ),
            ],
        )
        store.record_execution(trace)

        lessons = store.get_lessons_learned(goal_id)

        assert len(lessons) == 2
        assert lessons[0].lesson == "Use context managers"  # Higher confidence first
        assert lessons[0].confidence == 0.9

    def test_consolidation_tracking(self, store, goal_id):
        """Test consolidation status tracking."""
        trace = ExecutionTrace(
            goal_id=goal_id,
            session_id="session",
            action_type="code_generation",
            description="Test",
            outcome=ExecutionOutcome.SUCCESS,
        )
        execution_id = store.record_execution(trace)

        # Check initial status
        execution = store.get_execution(execution_id)
        assert execution.consolidation_status == "unconsolidated"

        # Mark as consolidated
        store.mark_consolidated(execution_id)

        # Verify status changed
        execution = store.get_execution(execution_id)
        assert execution.consolidation_status == "consolidated"
        assert execution.consolidated_at is not None

    def test_get_unconsolidated_executions(self, store, goal_id):
        """Test getting unconsolidated executions."""
        # Record multiple executions
        for i in range(3):
            trace = ExecutionTrace(
                goal_id=goal_id,
                session_id=f"session_{i}",
                action_type="code_generation",
                description=f"Execution {i}",
                outcome=ExecutionOutcome.SUCCESS,
            )
            eid = store.record_execution(trace)
            if i == 0:
                store.mark_consolidated(eid)

        unconsolidated = store.get_unconsolidated_executions(goal_id)

        assert len(unconsolidated) == 2

    def test_multiple_goals_isolated(self, store):
        """Test that goals don't interfere with each other."""
        goal_id_1 = str(uuid4())
        goal_id_2 = str(uuid4())

        # Record executions for goal 1
        for i in range(2):
            trace = ExecutionTrace(
                goal_id=goal_id_1,
                session_id=f"g1_session_{i}",
                action_type="code_generation",
                description=f"Goal 1 execution {i}",
                outcome=ExecutionOutcome.SUCCESS,
            )
            store.record_execution(trace)

        # Record executions for goal 2
        for i in range(3):
            trace = ExecutionTrace(
                goal_id=goal_id_2,
                session_id=f"g2_session_{i}",
                action_type="code_generation",
                description=f"Goal 2 execution {i}",
                outcome=ExecutionOutcome.FAILURE,
            )
            store.record_execution(trace)

        executions_1 = store.get_executions_for_goal(goal_id_1)
        executions_2 = store.get_executions_for_goal(goal_id_2)

        assert len(executions_1) == 2
        assert len(executions_2) == 3
        assert executions_1[0].outcome == ExecutionOutcome.SUCCESS
        assert executions_2[0].outcome == ExecutionOutcome.FAILURE
