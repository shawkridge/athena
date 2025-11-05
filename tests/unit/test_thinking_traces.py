"""Unit tests for thinking traces layer."""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from athena.ai_coordination.thinking_traces import (
    ProblemType,
    ReasoningPattern,
    ReasoningStep,
    ThinkingTrace,
)
from athena.ai_coordination.thinking_trace_store import ThinkingTraceStore
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
    """Create a ThinkingTraceStore with temporary database."""
    return ThinkingTraceStore(temp_db)


@pytest.fixture
def execution_id():
    """Generate a unique execution ID."""
    return str(uuid4())


class TestThinkingTraceStore:
    """Tests for ThinkingTraceStore."""

    def test_record_thinking_basic(self, store):
        """Test recording a basic thinking trace."""
        trace = ThinkingTrace(
            problem="How to optimize database queries?",
            problem_type=ProblemType.OPTIMIZATION,
            problem_complexity=6,
            reasoning_steps=[
                ReasoningStep(step_number=1, thought="Analyze current query performance"),
                ReasoningStep(step_number=2, thought="Check for missing indexes"),
            ],
            conclusion="Add index on user_id and timestamp columns",
            reasoning_quality=0.85,
            primary_pattern=ReasoningPattern.DECOMPOSITION,
            session_id="test_session",
            duration_seconds=120,
            ai_model_used="claude-3-sonnet",
        )

        thinking_id = store.record_thinking(trace)

        assert thinking_id is not None
        assert isinstance(thinking_id, int)

    def test_record_thinking_with_secondary_patterns(self, store):
        """Test recording thinking with multiple reasoning patterns."""
        trace = ThinkingTrace(
            problem="Fix authentication bug in user service",
            problem_type=ProblemType.DEBUGGING,
            problem_complexity=7,
            reasoning_steps=[
                ReasoningStep(step_number=1, thought="Review authentication flow"),
                ReasoningStep(step_number=2, thought="Check token validation logic"),
                ReasoningStep(step_number=3, thought="Found issue in JWT expiry check"),
            ],
            conclusion="Token expiry validation was checking wrong field",
            reasoning_quality=0.9,
            primary_pattern=ReasoningPattern.DECOMPOSITION,
            secondary_patterns=[
                ReasoningPattern.FIRST_PRINCIPLES,
                ReasoningPattern.EMPIRICAL,
            ],
            session_id="test_session",
        )

        thinking_id = store.record_thinking(trace)
        retrieved = store.get_thinking(thinking_id)

        assert retrieved is not None
        assert len(retrieved.reasoning_steps) == 3
        assert len(retrieved.secondary_patterns) == 2
        assert retrieved.conclusion == "Token expiry validation was checking wrong field"

    def test_get_thinking_not_found(self, store):
        """Test retrieving non-existent thinking trace."""
        result = store.get_thinking(999)
        assert result is None

    def test_link_thinking_to_execution(self, store, execution_id):
        """Test linking thinking trace to execution outcome."""
        # Record thinking
        trace = ThinkingTrace(
            problem="Design database schema",
            problem_type=ProblemType.ARCHITECTURE,
            problem_complexity=8,
            reasoning_steps=[],
            conclusion="Use normalized design with proper indexes",
            reasoning_quality=0.88,
            primary_pattern=ReasoningPattern.FIRST_PRINCIPLES,
            session_id="test_session",
        )

        thinking_id = store.record_thinking(trace)

        # Link to execution
        store.link_thinking_to_execution(
            thinking_id=thinking_id,
            execution_id=execution_id,
            was_correct=True,
            outcome_quality=0.95,
        )

        # Verify link
        retrieved = store.get_thinking(thinking_id)
        assert retrieved.linked_execution_id == execution_id
        assert retrieved.was_reasoning_correct is True
        assert retrieved.execution_outcome_quality == 0.95

    def test_get_thinking_for_execution(self, store, execution_id):
        """Test retrieving thinking by execution ID."""
        trace = ThinkingTrace(
            problem="Optimize API response time",
            problem_type=ProblemType.OPTIMIZATION,
            reasoning_steps=[],
            conclusion="Add caching layer",
            session_id="test_session",
        )

        thinking_id = store.record_thinking(trace)
        store.link_thinking_to_execution(thinking_id, execution_id, True, 0.85)

        retrieved = store.get_thinking_for_execution(execution_id)
        assert retrieved is not None
        assert retrieved.id == thinking_id

    def test_get_thinking_for_execution_not_found(self, store):
        """Test retrieving thinking for non-existent execution."""
        result = store.get_thinking_for_execution(str(uuid4()))
        assert result is None

    def test_get_thinking_for_session(self, store):
        """Test retrieving all thinking in a session."""
        session_id = "test_session_multi"

        # Record multiple thinking traces in same session
        for i in range(3):
            trace = ThinkingTrace(
                problem=f"Problem {i}",
                problem_type=ProblemType.DEBUGGING,
                reasoning_steps=[],
                conclusion=f"Solution {i}",
                session_id=session_id,
            )
            store.record_thinking(trace)
            time.sleep(0.01)  # Ensure different timestamps

        results = store.get_thinking_for_session(session_id)
        assert len(results) == 3

    def test_get_thinking_by_pattern(self, store):
        """Test retrieving thinking by reasoning pattern."""
        # Record multiple thinking traces with different patterns
        patterns = [
            ReasoningPattern.DECOMPOSITION,
            ReasoningPattern.ANALOGY,
            ReasoningPattern.DECOMPOSITION,
        ]

        for i, pattern in enumerate(patterns):
            trace = ThinkingTrace(
                problem=f"Problem {i}",
                problem_type=ProblemType.DEBUGGING,
                reasoning_steps=[],
                conclusion=f"Solution {i}",
                primary_pattern=pattern,
                pattern_effectiveness=0.7 + (i * 0.1),
                session_id="test_session",
            )
            store.record_thinking(trace)

        # Query for decomposition patterns
        results = store.get_thinking_by_pattern(ReasoningPattern.DECOMPOSITION)
        assert len(results) == 2
        assert all(t.primary_pattern == ReasoningPattern.DECOMPOSITION for t in results)

    def test_get_thinking_by_pattern_with_min_effectiveness(self, store):
        """Test filtering thinking by effectiveness threshold."""
        patterns = [
            ReasoningPattern.DECOMPOSITION,
            ReasoningPattern.DECOMPOSITION,
            ReasoningPattern.DECOMPOSITION,
        ]
        effectiveness_scores = [0.6, 0.75, 0.9]

        for i, (pattern, eff) in enumerate(zip(patterns, effectiveness_scores)):
            trace = ThinkingTrace(
                problem=f"Problem {i}",
                problem_type=ProblemType.OPTIMIZATION,
                reasoning_steps=[],
                conclusion=f"Solution {i}",
                primary_pattern=pattern,
                pattern_effectiveness=eff,
                session_id="test_session",
            )
            store.record_thinking(trace)

        # Query with effectiveness threshold
        results = store.get_thinking_by_pattern(
            ReasoningPattern.DECOMPOSITION, min_effectiveness=0.7
        )
        assert len(results) == 2
        assert all(t.pattern_effectiveness >= 0.7 for t in results)

    def test_reasoning_effectiveness_analysis(self, store):
        """Test analyzing reasoning pattern effectiveness."""
        # Record thinking with different patterns and effectiveness scores
        patterns_data = [
            (ReasoningPattern.DECOMPOSITION, 0.85, True),
            (ReasoningPattern.DECOMPOSITION, 0.75, True),
            (ReasoningPattern.ANALOGY, 0.65, False),
            (ReasoningPattern.FIRST_PRINCIPLES, 0.95, True),
        ]

        for pattern, eff, was_correct in patterns_data:
            trace = ThinkingTrace(
                problem="Test problem",
                problem_type=ProblemType.DEBUGGING,
                reasoning_steps=[],
                conclusion="Test conclusion",
                primary_pattern=pattern,
                pattern_effectiveness=eff,
                was_reasoning_correct=was_correct,
                session_id="test_session",
            )
            store.record_thinking(trace)

        analysis = store.get_reasoning_effectiveness()

        assert ReasoningPattern.DECOMPOSITION.value in analysis
        assert ReasoningPattern.ANALOGY.value in analysis
        assert ReasoningPattern.FIRST_PRINCIPLES.value in analysis

        # Check decomposition: avg(0.85, 0.75) = 0.8, success = 2/2 = 1.0
        decomp = analysis[ReasoningPattern.DECOMPOSITION.value]
        assert decomp["count"] == 2
        assert decomp["success_rate"] == 1.0
        assert 0.79 <= decomp["avg_effectiveness"] <= 0.81

    def test_correctness_analysis_no_linked(self, store):
        """Test correctness analysis when no thinking is linked."""
        # Record thinking without linking
        trace = ThinkingTrace(
            problem="Test",
            problem_type=ProblemType.DEBUGGING,
            reasoning_steps=[],
            conclusion="Solution",
            session_id="test_session",
        )
        store.record_thinking(trace)

        analysis = store.get_correctness_analysis()
        assert analysis["total_linked"] == 0
        assert analysis["correctness_rate"] == 0.0

    def test_correctness_analysis_with_linked(self, store):
        """Test correctness analysis with linked thinking and executions."""
        # Record thinking and link to executions
        thinking_data = [
            (True, 0.95),
            (True, 0.90),
            (False, 0.60),
        ]

        for was_correct, outcome_quality in thinking_data:
            trace = ThinkingTrace(
                problem="Test",
                problem_type=ProblemType.DEBUGGING,
                reasoning_steps=[],
                conclusion="Solution",
                reasoning_quality=0.85,
                session_id="test_session",
            )
            thinking_id = store.record_thinking(trace)
            store.link_thinking_to_execution(
                thinking_id,
                execution_id=str(uuid4()),
                was_correct=was_correct,
                outcome_quality=outcome_quality,
            )

        analysis = store.get_correctness_analysis()
        assert analysis["total_linked"] == 3
        assert analysis["correct_reasoning_count"] == 2
        assert analysis["correctness_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert analysis["avg_outcome_quality"] == pytest.approx(0.817, abs=0.01)

    def test_get_recent_thinking(self, store):
        """Test retrieving recent thinking traces."""
        # Record multiple thinking traces with delays
        for i in range(15):
            trace = ThinkingTrace(
                problem=f"Problem {i}",
                problem_type=ProblemType.DEBUGGING,
                reasoning_steps=[],
                conclusion=f"Solution {i}",
                session_id="test_session",
            )
            store.record_thinking(trace)
            time.sleep(0.01)

        recent = store.get_recent_thinking(limit=10)
        assert len(recent) == 10
        # Most recent should be last recorded
        assert "14" in recent[0].problem

    def test_mark_consolidated(self, store):
        """Test marking thinking as consolidated."""
        trace = ThinkingTrace(
            problem="Test",
            problem_type=ProblemType.DEBUGGING,
            reasoning_steps=[],
            conclusion="Solution",
            session_id="test_session",
        )

        thinking_id = store.record_thinking(trace)
        assert store.get_thinking(thinking_id).consolidation_status == "unconsolidated"

        store.mark_consolidated(thinking_id)
        retrieved = store.get_thinking(thinking_id)
        assert retrieved.consolidation_status == "consolidated"
        assert retrieved.consolidated_at is not None

    def test_get_unconsolidated_thinking(self, store):
        """Test retrieving unconsolidated thinking for consolidation."""
        # Record thinking traces
        thinking_ids = []
        for i in range(5):
            trace = ThinkingTrace(
                problem=f"Problem {i}",
                problem_type=ProblemType.DEBUGGING,
                reasoning_steps=[],
                conclusion=f"Solution {i}",
                session_id="test_session",
            )
            thinking_ids.append(store.record_thinking(trace))

        # Consolidate some
        store.mark_consolidated(thinking_ids[0])
        store.mark_consolidated(thinking_ids[2])

        # Get unconsolidated
        unconsolidated = store.get_unconsolidated_thinking(limit=100)
        assert len(unconsolidated) == 3
        assert all(t.consolidation_status == "unconsolidated" for t in unconsolidated)

    def test_thinking_with_decision_points(self, store):
        """Test storing thinking with decision points."""
        trace = ThinkingTrace(
            problem="Choose database strategy",
            problem_type=ProblemType.ARCHITECTURE,
            reasoning_steps=[
                ReasoningStep(step_number=1, thought="Option A: PostgreSQL"),
                ReasoningStep(step_number=2, thought="Option B: MongoDB"),
                ReasoningStep(
                    step_number=3,
                    thought="Compare requirements",
                    decision_point=True,
                    decision_made="PostgreSQL with proper indexing",
                    rationale="Better for complex queries and ACID guarantees",
                ),
            ],
            conclusion="Use PostgreSQL",
            session_id="test_session",
        )

        thinking_id = store.record_thinking(trace)
        retrieved = store.get_thinking(thinking_id)

        # Verify decision point was stored
        decision_step = retrieved.reasoning_steps[2]
        assert decision_step.decision_point is True
        assert decision_step.decision_made == "PostgreSQL with proper indexing"
        assert decision_step.rationale is not None

    def test_multiple_sessions_isolated(self, store):
        """Test that different sessions don't interfere."""
        session_1 = "session_1"
        session_2 = "session_2"

        # Record thinking in session 1
        trace1 = ThinkingTrace(
            problem="Problem 1",
            problem_type=ProblemType.DEBUGGING,
            reasoning_steps=[],
            conclusion="Solution 1",
            session_id=session_1,
        )
        store.record_thinking(trace1)

        # Record thinking in session 2
        trace2 = ThinkingTrace(
            problem="Problem 2",
            problem_type=ProblemType.OPTIMIZATION,
            reasoning_steps=[],
            conclusion="Solution 2",
            session_id=session_2,
        )
        store.record_thinking(trace2)

        # Verify isolation
        results_1 = store.get_thinking_for_session(session_1)
        results_2 = store.get_thinking_for_session(session_2)

        assert len(results_1) == 1
        assert len(results_2) == 1
        assert results_1[0].session_id == session_1
        assert results_2[0].session_id == session_2
