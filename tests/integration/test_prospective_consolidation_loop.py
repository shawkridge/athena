"""Integration tests for Prospective→Consolidation bidirectional feedback loop.

Tests the complete loop:
1. Task execution → Metrics capture (ProspectiveStore)
2. Metrics → Pattern extraction (PatternExtractor)
3. Patterns → Task linkage (FK: learned_pattern_id)
4. Task outcome → Pattern update (ConsolidationHook)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPhase, TaskPriority
from athena.prospective.task_learning_integration import TaskLearningIntegration
from athena.prospective.consolidation_hook import ConsolidationHook
from athena.prospective.task_patterns import TaskPattern, PatternType, PatternStatus, ExtractionMethod
from athena.core.database import Database


class TestProspectiveConsolidationLoop:
    """Test bidirectional Prospective→Consolidation learning loop."""

    def test_task_completion_captures_metrics(self):
        """Test that task completion triggers metric capture."""
        mock_db = Mock()
        integration = TaskLearningIntegration(mock_db)

        # Create completed task
        now = datetime.now()
        task = ProspectiveTask(
            id=1,
            project_id=1,
            content="Implement authentication",
            active_form="Implementing authentication",
            created_at=now - timedelta(hours=2),
            completed_at=now,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
        )

        # Mock pattern store
        integration.pattern_store.save_execution_metrics = Mock(return_value=1)

        # Trigger metric capture
        result = integration.on_task_completed(task)

        assert result is True
        integration.pattern_store.save_execution_metrics.assert_called_once()

    def test_task_pattern_linkage(self):
        """Test that learned patterns are linked to tasks via FK."""
        mock_db = Mock()

        # Simulate stored pattern
        pattern = TaskPattern(
            id=100,
            project_id=1,
            pattern_name="high_priority_success",
            pattern_type=PatternType.SUCCESS_RATE,
            description="High priority tasks have high success",
            condition_json='{"priority": "high"}',
            prediction="85% success rate",
            sample_size=20,
            confidence_score=0.85,
            success_rate=0.85,
            failure_count=3,
            extraction_method=ExtractionMethod.STATISTICAL,
            status=PatternStatus.ACTIVE,
        )

        # Create task with pattern linkage
        task = ProspectiveTask(
            id=50,
            project_id=1,
            content="Implement feature",
            active_form="Implementing feature",
            created_at=datetime.now(),
            status=TaskStatus.PENDING,
            learned_pattern_id=pattern.id,  # FK linkage
        )

        # Verify linkage exists
        assert task.learned_pattern_id == pattern.id
        assert task.learned_pattern_id is not None

    def test_pattern_update_from_task_outcome(self):
        """Test that task success/failure updates pattern confidence."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        # Create initial pattern
        pattern = TaskPattern(
            id=1,
            project_id=1,
            pattern_name="test_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test pattern",
            condition_json="{}",
            prediction="Success",
            sample_size=10,
            confidence_score=0.70,
            success_rate=0.80,
            failure_count=2,
            extraction_method=ExtractionMethod.STATISTICAL,
            status=PatternStatus.ACTIVE,
        )

        # Task succeeded - pattern should be boosted
        updated = hook._update_pattern_from_outcome(pattern, success=True)

        assert updated.confidence_score > pattern.confidence_score
        assert updated.confidence_score == 0.75  # 0.70 + 0.05
        assert updated.status == PatternStatus.ACTIVE

    def test_pattern_deprecation_from_repeated_failures(self):
        """Test that repeated task failures deprecate patterns."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        # Start with medium confidence
        pattern = TaskPattern(
            id=1,
            project_id=1,
            pattern_name="failing_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Pattern that fails",
            condition_json="{}",
            prediction="Success",
            sample_size=10,
            confidence_score=0.50,
            success_rate=0.60,
            failure_count=2,
            extraction_method=ExtractionMethod.STATISTICAL,
            status=PatternStatus.ACTIVE,
        )

        # Multiple failures
        updated = pattern
        for i in range(2):
            updated = hook._update_pattern_from_outcome(updated, success=False)

        # Pattern should be deprecated
        assert updated.status == PatternStatus.DEPRECATED
        assert updated.confidence_score < 0.4

    def test_full_loop_integration(self):
        """Test complete loop: task → metrics → patterns → feedback."""
        mock_db = Mock()

        # Step 1: Task completes
        integration = TaskLearningIntegration(mock_db)
        now = datetime.now()
        task = ProspectiveTask(
            id=1,
            project_id=1,
            content="Test task",
            active_form="Testing task",
            created_at=now - timedelta(hours=1),
            completed_at=now,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
        )

        # Mock metrics capture
        integration.pattern_store.save_execution_metrics = Mock(return_value=1)

        # Step 2: Capture metrics
        result = integration.on_task_completed(task)
        assert result is True

        # Step 3: Simulate pattern learning
        learned_pattern = TaskPattern(
            id=100,
            project_id=1,
            pattern_name="high_priority_success",
            pattern_type=PatternType.SUCCESS_RATE,
            description="High priority tasks succeed",
            condition_json='{"priority": "high"}',
            prediction="85% success",
            sample_size=20,
            confidence_score=0.80,
            success_rate=0.85,
            failure_count=3,
            extraction_method=ExtractionMethod.STATISTICAL,
            status=PatternStatus.ACTIVE,
        )

        # Link task to pattern
        task_with_pattern = task.model_copy(update={"learned_pattern_id": learned_pattern.id})
        assert task_with_pattern.learned_pattern_id == learned_pattern.id

        # Step 4: Task succeeds, update pattern
        hook = ConsolidationHook(mock_db)
        updated_pattern = hook._update_pattern_from_outcome(learned_pattern, success=True)

        # Verify confidence increased
        assert updated_pattern.confidence_score > learned_pattern.confidence_score
        assert updated_pattern.status == PatternStatus.ACTIVE

    def test_consolidation_hook_batch_operations(self):
        """Test batch consolidation of multiple task-pattern pairs."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        # Mock task-pattern pairs
        pairs = [
            {"task_id": 1, "pattern_id": 100, "success": True},
            {"task_id": 2, "pattern_id": 100, "success": False},
            {"task_id": 3, "pattern_id": 101, "success": True},
            {"task_id": 4, "pattern_id": 101, "success": False},
            {"task_id": 5, "pattern_id": 102, "success": True},
        ]

        # Mock the on_task_completed_with_pattern method
        hook.on_task_completed_with_pattern = Mock(return_value=True)

        result = hook.consolidate_batch_outcomes(pairs)

        # Verify all pairs were processed
        assert result["total_pairs"] == 5
        assert result["successful"] == 5
        assert result["patterns_updated"] == 3  # Three unique patterns
        assert hook.on_task_completed_with_pattern.call_count == 5

    def test_feedback_prevents_pattern_hallucination(self):
        """Test that negative feedback prevents patterns from being used incorrectly."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        # Pattern with very high initial confidence (potentially hallucinated)
        hallucinated_pattern = TaskPattern(
            id=1,
            project_id=1,
            pattern_name="hallucinated_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Pattern that doesn't actually work",
            condition_json="{}",
            prediction="Success",
            sample_size=5,  # Very small sample - high risk
            confidence_score=0.95,  # Very high initial confidence
            success_rate=1.0,  # Perfect success - unrealistic
            failure_count=0,
            extraction_method=ExtractionMethod.STATISTICAL,
            status=PatternStatus.ACTIVE,
        )

        # Task using this pattern fails - feedback loop corrects it
        updated = hallucinated_pattern
        for i in range(3):  # Multiple failures
            updated = hook._update_pattern_from_outcome(updated, success=False)

        # Pattern should be significantly downgraded or deprecated
        assert updated.confidence_score < 0.7  # Much lower than initial 0.95
        assert updated.status in [PatternStatus.ACTIVE, PatternStatus.DEPRECATED]

        # If still active, confidence should be lower than hallucinated initial
        if updated.status == PatternStatus.ACTIVE:
            assert updated.confidence_score < hallucinated_pattern.confidence_score

    def test_meta_metadata_recording(self):
        """Test that feedback is properly recorded in pattern metadata."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        pattern = TaskPattern(
            id=1,
            project_id=1,
            pattern_name="test",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test",
            condition_json="{}",
            prediction="Success",
            sample_size=10,
            confidence_score=0.70,
            success_rate=0.80,
            failure_count=2,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        # Update with feedback
        outcome = "Task completed earlier than estimated"
        updated = hook._update_pattern_from_outcome(
            pattern, success=True, outcome_description=outcome
        )

        # Verify feedback is recorded
        assert "Feedback" in updated.validation_notes
        assert outcome in updated.validation_notes
        assert "success" in updated.validation_notes.lower()
