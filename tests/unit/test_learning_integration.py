"""Tests for LearningIntegration layer - learning feedback loops."""

from datetime import datetime
from uuid import uuid4

import pytest

from athena.ai_coordination.learning_integration import (
    FeedbackUpdate,
    FeedbackUpdateType,
    LearningCycle,
    LearningMetrics,
    LessonToProcedure,
    PatternType,
    ProcedureCandidate,
)
from athena.ai_coordination.learning_integration_mcp_tools import (
    LearningIntegrationMCPTools,
)
from athena.ai_coordination.learning_integration_store import (
    LearningIntegrationStore,
)
from athena.core.database import Database


class TestLearningIntegrationModels:
    """Test LearningIntegration data models."""

    def test_create_lesson_to_procedure(self):
        """Test creating a lesson-to-procedure mapping."""
        lesson = LessonToProcedure(
            lesson_id=1,
            lesson_text="Always validate input before processing",
            confidence=0.85,
            applies_to=["input validation", "error handling"],
            pattern_type=PatternType.ERROR_RECOVERY,
            procedure_steps=["1. Check for null", "2. Validate type", "3. Check bounds"],
        )

        assert lesson.lesson_id == 1
        assert lesson.confidence == 0.85
        assert lesson.can_create_procedure is True  # confidence >= 0.7
        assert len(lesson.procedure_steps) == 3

    def test_create_procedure_candidate(self):
        """Test creating a procedure candidate."""
        candidate = ProcedureCandidate(
            name="Input Validation Pattern",
            pattern_type=PatternType.ERROR_RECOVERY,
            confidence=0.9,
            source_lessons=[1, 2, 3],
            draft_procedure={"steps": ["validate", "process", "return"]},
            success_rate=0.95,
            estimated_impact=0.8,
            ready_for_creation=True,
        )

        assert candidate.name == "Input Validation Pattern"
        assert candidate.frequency == 3
        assert candidate.success_rate == 0.95
        assert candidate.ready_for_creation is True

    def test_create_feedback_update(self):
        """Test creating a feedback update."""
        feedback = FeedbackUpdate(
            update_type=FeedbackUpdateType.ERROR_PATTERN,
            target_id="err-123",
            action="update",
            reason="Pattern observed in 3+ cycles",
            new_data={"recovery_strategy": "validate_input"},
            confidence=0.85,
        )

        assert feedback.update_type == FeedbackUpdateType.ERROR_PATTERN
        assert feedback.action == "update"
        assert feedback.applied is False

    def test_create_learning_cycle(self):
        """Test creating a learning cycle."""
        cycle = LearningCycle(
            action_cycle_id=5,
            session_id="sess-001",
            lessons_extracted=3,
            procedures_created=1,
            feedback_updates_applied=2,
            estimated_impact=0.75,
        )

        assert cycle.action_cycle_id == 5
        assert cycle.lessons_extracted == 3
        assert cycle.estimated_impact == 0.75

    def test_create_learning_metrics(self):
        """Test creating learning metrics."""
        metrics = LearningMetrics(
            total_lessons_extracted=10,
            total_procedures_created=2,
            total_feedback_applied=5,
            average_lesson_confidence=0.8,
            procedure_success_rate=0.9,
            estimated_time_saved_hours=2.5,
            estimated_error_reduction_percent=20.0,
            period_days=7,
        )

        assert metrics.total_lessons_extracted == 10
        assert metrics.estimated_time_saved_hours == 2.5
        assert metrics.period_days == 7


class TestLearningIntegrationStore:
    """Test LearningIntegrationStore operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        return Database(tmp_path / "test.db")

    @pytest.fixture
    def store(self, db):
        """Create store instance."""
        return LearningIntegrationStore(db)

    def test_create_lesson_to_procedure(self, store):
        """Test creating a lesson-to-procedure mapping."""
        lesson = store.create_lesson_to_procedure(
            lesson_id=1,
            lesson_text="Always validate input",
            confidence=0.85,
            applies_to=["validation", "error handling"],
            pattern_type="error_recovery",
            procedure_steps=["Check null", "Validate type"],
        )

        assert lesson.id is not None
        assert lesson.lesson_id == 1
        assert lesson.confidence == 0.85
        assert lesson.can_create_procedure is True

    def test_create_procedure_candidate(self, store):
        """Test creating a procedure candidate."""
        candidate = store.create_procedure_candidate(
            name="Validation Pattern",
            pattern_type="error_recovery",
            confidence=0.9,
            source_lessons=[1, 2, 3],
            draft_procedure={"steps": ["validate", "process"]},
            success_rate=0.95,
            estimated_impact=0.85,
            ready_for_creation=True,
        )

        assert candidate.id is not None
        assert candidate.name == "Validation Pattern"
        assert candidate.frequency == 3
        assert candidate.ready_for_creation is True

    def test_find_procedure_candidates(self, store):
        """Test finding procedure candidates by confidence."""
        # Create candidates
        store.create_procedure_candidate(
            name="High Confidence",
            pattern_type="error_recovery",
            confidence=0.85,
            source_lessons=[1, 2],
            draft_procedure={},
        )
        store.create_procedure_candidate(
            name="Low Confidence",
            pattern_type="optimization",
            confidence=0.5,
            source_lessons=[3],
            draft_procedure={},
        )

        # Find high confidence only
        candidates = store.find_procedure_candidates(min_confidence=0.7, min_frequency=2)
        assert len(candidates) == 1
        assert candidates[0].name == "High Confidence"

    def test_mark_procedure_created(self, store):
        """Test marking a candidate as created."""
        candidate = store.create_procedure_candidate(
            name="Test Candidate",
            pattern_type="optimization",
            confidence=0.8,
            source_lessons=[1],
            draft_procedure={},
        )

        success = store.mark_procedure_created(candidate.id, procedure_id=99)
        assert success
        assert candidate.created_procedure_id is None  # Original unchanged

    def test_create_feedback_update(self, store):
        """Test creating feedback update."""
        feedback = store.create_feedback_update(
            update_type="error_pattern",
            action="update",
            reason="Observed in multiple cycles",
            target_id="err-123",
            confidence=0.8,
        )

        assert feedback.id is not None
        assert feedback.update_type == FeedbackUpdateType.ERROR_PATTERN
        assert feedback.applied is False

    def test_get_pending_feedback(self, store):
        """Test retrieving pending feedback."""
        # Create multiple feedback updates
        store.create_feedback_update(
            update_type="error_pattern",
            action="update",
            reason="Feedback 1",
        )
        store.create_feedback_update(
            update_type="decision",
            action="replace",
            reason="Feedback 2",
        )

        pending = store.get_pending_feedback()
        assert len(pending) == 2
        assert all(not f.applied for f in pending)

    def test_mark_feedback_applied(self, store):
        """Test marking feedback as applied."""
        feedback = store.create_feedback_update(
            update_type="error_pattern",
            action="update",
            reason="Test feedback",
        )

        success = store.mark_feedback_applied(feedback.id)
        assert success

        # Verify no longer in pending
        pending = store.get_pending_feedback()
        assert len(pending) == 0

    def test_get_lessons_by_confidence(self, store):
        """Test retrieving lessons by confidence threshold."""
        store.create_lesson_to_procedure(
            lesson_id=1, lesson_text="High confidence", confidence=0.9
        )
        store.create_lesson_to_procedure(
            lesson_id=2, lesson_text="Low confidence", confidence=0.4
        )

        high_conf = store.get_lessons_by_confidence(min_confidence=0.7)
        assert len(high_conf) == 1
        assert high_conf[0].lesson_text == "High confidence"

    def test_create_learning_cycle(self, store):
        """Test creating a learning cycle."""
        cycle = store.create_learning_cycle(
            action_cycle_id=5,
            session_id="sess-001",
            lessons_extracted=3,
            procedures_created=1,
            feedback_updates_applied=2,
            estimated_impact=0.8,
        )

        assert cycle.id is not None
        assert cycle.action_cycle_id == 5
        assert cycle.lessons_extracted == 3

    def test_get_learning_cycle(self, store):
        """Test retrieving a learning cycle."""
        created = store.create_learning_cycle(
            action_cycle_id=5,
            session_id="sess-001",
            lessons_extracted=3,
            procedures_created=1,
        )

        retrieved = store.get_learning_cycle(created.id)
        assert retrieved is not None
        assert retrieved.action_cycle_id == 5
        assert retrieved.lessons_extracted == 3

    def test_get_learning_cycles_for_session(self, store):
        """Test retrieving cycles for a session."""
        session_id = "sess-001"
        store.create_learning_cycle(
            action_cycle_id=1, session_id=session_id, lessons_extracted=2
        )
        store.create_learning_cycle(
            action_cycle_id=2, session_id=session_id, lessons_extracted=3
        )
        store.create_learning_cycle(
            action_cycle_id=3, session_id="sess-002", lessons_extracted=1
        )

        cycles = store.get_learning_cycles_for_session(session_id)
        assert len(cycles) == 2
        assert all(c.session_id == session_id for c in cycles)

    def test_get_learning_metrics(self, store):
        """Test retrieving learning metrics."""
        # Create test data
        store.create_lesson_to_procedure(
            lesson_id=1, lesson_text="L1", confidence=0.9
        )
        store.create_lesson_to_procedure(
            lesson_id=2, lesson_text="L2", confidence=0.8
        )
        store.create_feedback_update(
            update_type="error_pattern", action="update", reason="F1"
        )
        store.mark_feedback_applied(1)

        metrics = store.get_learning_metrics(days=7)
        assert metrics.total_lessons_extracted == 2
        assert metrics.total_feedback_applied == 1
        assert metrics.period_days == 7


class TestLearningIntegrationMCPTools:
    """Test LearningIntegration MCP tools."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        return Database(tmp_path / "test.db")

    @pytest.fixture
    def tools(self, db):
        """Create MCP tools instance."""
        return LearningIntegrationMCPTools(db)

    def test_get_tools_returns_list(self, tools):
        """Test that get_tools returns list of Tool definitions."""
        tools_list = tools.get_tools()
        assert isinstance(tools_list, list)
        assert len(tools_list) == 6
        assert all(hasattr(t, "name") for t in tools_list)

    def test_create_procedure_tool(self, tools):
        """Test create_procedure_from_lesson MCP tool."""
        result = tools.handle_tool_call(
            "create_procedure_from_lesson",
            {
                "lesson_id": 1,
                "lesson_text": "Always validate input",
                "procedure_name": "Input Validation",
                "procedure_steps": ["Check null", "Validate type"],
                "confidence": 0.85,
                "pattern_type": "error_recovery",
            },
        )

        assert result["status"] == "success"
        assert result["lesson_id"] is not None
        assert result["confidence"] == 0.85

    def test_find_candidates_tool(self, tools):
        """Test find_procedure_candidates MCP tool."""
        # Create candidates
        tools.handle_tool_call(
            "create_procedure_from_lesson",
            {
                "lesson_id": 1,
                "lesson_text": "Validation lesson",
                "procedure_name": "Validation",
                "procedure_steps": ["Step 1"],
                "confidence": 0.85,
            },
        )

        result = tools.handle_tool_call(
            "find_procedure_candidates",
            {"min_confidence": 0.7, "min_frequency": 1},
        )

        assert result["status"] == "success"
        # Note: We won't have candidates yet (only lessons), but tool should work

    def test_apply_feedback_tool(self, tools):
        """Test apply_feedback_to_project MCP tool."""
        result = tools.handle_tool_call(
            "apply_feedback_to_project",
            {
                "feedback_type": "error_pattern",
                "action": "update",
                "reason": "Observed in multiple cycles",
                "target_id": "err-123",
                "confidence": 0.85,
            },
        )

        assert result["status"] == "success"
        assert result["feedback_id"] is not None
        assert result["confidence"] == 0.85

    def test_get_metrics_tool(self, tools):
        """Test get_learning_effectiveness MCP tool."""
        result = tools.handle_tool_call(
            "get_learning_effectiveness",
            {"days": 7},
        )

        assert result["status"] == "success"
        assert "lessons_extracted" in result
        assert "procedures_created" in result

    def test_consolidate_lessons_tool(self, tools):
        """Test consolidate_similar_lessons MCP tool."""
        # Create lessons
        for i in range(3):
            tools.handle_tool_call(
                "create_procedure_from_lesson",
                {
                    "lesson_id": i + 1,
                    "lesson_text": f"Lesson {i+1}",
                    "procedure_name": f"Proc {i+1}",
                    "procedure_steps": ["Step 1"],
                    "confidence": 0.85,
                },
            )

        result = tools.handle_tool_call(
            "consolidate_similar_lessons",
            {"min_confidence": 0.7},
        )

        assert result["status"] == "success"
        assert "lessons_found" in result

    def test_suggest_improvements_tool(self, tools):
        """Test suggest_process_improvements MCP tool."""
        # Create some lessons first
        tools.handle_tool_call(
            "create_procedure_from_lesson",
            {
                "lesson_id": 1,
                "lesson_text": "Improvement idea",
                "procedure_name": "Process Improvement",
                "procedure_steps": ["Step 1"],
                "confidence": 0.9,
            },
        )

        result = tools.handle_tool_call(
            "suggest_process_improvements",
            {"focus_area": "general"},
        )

        assert result["status"] == "success"
        assert "suggestions" in result


class TestLearningIntegrationIntegration:
    """Integration tests for complete learning loops."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        return Database(tmp_path / "test.db")

    @pytest.fixture
    def store(self, db):
        """Create store instance."""
        return LearningIntegrationStore(db)

    def test_complete_learning_loop(self, store):
        """Test complete feedback loop: lesson -> candidate -> procedure -> feedback."""
        # Step 1: Create lessons
        lesson1 = store.create_lesson_to_procedure(
            lesson_id=1,
            lesson_text="Always validate input before processing",
            confidence=0.9,
            applies_to=["validation"],
            pattern_type="error_recovery",
        )
        lesson2 = store.create_lesson_to_procedure(
            lesson_id=2,
            lesson_text="Validate input to prevent errors",
            confidence=0.85,
            applies_to=["validation"],
            pattern_type="error_recovery",
        )

        assert lesson1.can_create_procedure is True
        assert lesson2.can_create_procedure is True

        # Step 2: Create procedure candidate
        candidate = store.create_procedure_candidate(
            name="Input Validation Pattern",
            pattern_type="error_recovery",
            confidence=0.875,  # Average of lessons
            source_lessons=[lesson1.id, lesson2.id],
            draft_procedure={
                "steps": ["Check null", "Validate type", "Check bounds"],
                "success_rate": 0.95,
            },
            success_rate=0.95,
            ready_for_creation=True,
        )

        assert candidate.ready_for_creation is True
        assert candidate.frequency == 2

        # Step 3: Create feedback update
        feedback = store.create_feedback_update(
            update_type="error_pattern",
            action="update",
            reason="Validation pattern observed in multiple cycles",
            target_id="err-invalid-input",
            source_lesson_id=lesson1.id,
            confidence=0.9,
        )

        assert not feedback.applied

        # Step 4: Apply feedback
        store.mark_feedback_applied(feedback.id)
        pending = store.get_pending_feedback()
        assert len(pending) == 0

        # Step 5: Create learning cycle
        cycle = store.create_learning_cycle(
            action_cycle_id=5,
            session_id="sess-001",
            lessons_extracted=2,
            procedures_created=1,
            feedback_updates_applied=1,
            estimated_impact=0.85,
        )

        assert cycle.lessons_extracted == 2
        assert cycle.estimated_impact == 0.85

    def test_multiple_pattern_types(self, store):
        """Test handling multiple pattern types."""
        patterns = ["error_recovery", "optimization", "design", "workflow", "testing"]

        for i, pattern in enumerate(patterns):
            store.create_lesson_to_procedure(
                lesson_id=i + 1,
                lesson_text=f"Lesson for {pattern}",
                confidence=0.8,
                pattern_type=pattern,
            )

        # Get all lessons
        all_lessons = store.get_lessons_by_confidence(min_confidence=0.7)
        assert len(all_lessons) == 5
        types = {l.pattern_type for l in all_lessons}
        assert len(types) == 5

    def test_learning_metrics_calculation(self, store):
        """Test learning metrics aggregation."""
        # Create test data
        for i in range(5):
            store.create_lesson_to_procedure(
                lesson_id=i + 1,
                lesson_text=f"Lesson {i+1}",
                confidence=0.7 + (i * 0.05),
            )

        # Create and apply feedback
        for i in range(3):
            feedback = store.create_feedback_update(
                update_type="error_pattern",
                action="update",
                reason=f"Feedback {i+1}",
            )
            store.mark_feedback_applied(feedback.id)

        # Get metrics
        metrics = store.get_learning_metrics(days=7)
        assert metrics.total_lessons_extracted == 5
        assert metrics.total_feedback_applied == 3
        assert metrics.feedback_application_rate == 0.6  # 3/5
