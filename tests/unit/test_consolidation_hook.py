"""Unit tests for consolidation hook (bidirectional learning)."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from athena.prospective.consolidation_hook import ConsolidationHook
from athena.prospective.task_patterns import TaskPattern, PatternStatus, PatternType, ExtractionMethod


class TestConsolidationHook:
    """Test consolidation hook functionality."""

    def test_initialization(self):
        """Test consolidation hook initialization."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        assert hook.db is mock_db
        assert hook.pattern_store is not None
        assert hook.extractor is not None

    def test_update_pattern_from_successful_outcome(self):
        """Test pattern confidence increases when task succeeds."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        pattern = TaskPattern(
            id=1,
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
        )

        # Task succeeded
        updated = hook._update_pattern_from_outcome(pattern, success=True)

        # Confidence should increase
        assert updated.confidence_score > pattern.confidence_score
        assert updated.confidence_score == 0.75  # 0.70 + 0.05
        # Should have feedback
        assert "Feedback" in updated.validation_notes

    def test_update_pattern_from_failed_outcome(self):
        """Test pattern confidence decreases when task fails."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        pattern = TaskPattern(
            id=1,
            pattern_name="bad_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Pattern that fails",
            condition_json="{}",
            prediction="Success",
            sample_size=10,
            confidence_score=0.70,
            success_rate=0.80,
            failure_count=2,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        # Task failed
        updated = hook._update_pattern_from_outcome(pattern, success=False)

        # Confidence should decrease
        assert updated.confidence_score < pattern.confidence_score
        assert updated.confidence_score == 0.60  # 0.70 - 0.10

    def test_pattern_deprecated_on_low_confidence(self):
        """Test that patterns are deprecated when confidence drops below threshold."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        # Start with low confidence
        pattern = TaskPattern(
            id=1,
            pattern_name="weak_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Weak pattern",
            condition_json="{}",
            prediction="Success",
            sample_size=5,
            confidence_score=0.50,
            success_rate=0.60,
            failure_count=2,
            extraction_method=ExtractionMethod.STATISTICAL,
            status=PatternStatus.ACTIVE,
        )

        # Multiple failures push it below 0.4
        updated = pattern
        for _ in range(2):
            updated = hook._update_pattern_from_outcome(updated, success=False)

        # Should be deprecated
        assert updated.status == PatternStatus.DEPRECATED
        assert updated.confidence_score < 0.4

    def test_confidence_bounds(self):
        """Test confidence score is bounded between 0.0 and 1.0."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        # Start at 0.95
        pattern = TaskPattern(
            id=1,
            pattern_name="high_conf",
            pattern_type=PatternType.SUCCESS_RATE,
            description="High confidence",
            condition_json="{}",
            prediction="Success",
            sample_size=100,
            confidence_score=0.95,
            success_rate=0.95,
            failure_count=1,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        # Success boost should not exceed 1.0
        updated = hook._update_pattern_from_outcome(pattern, success=True)
        assert updated.confidence_score <= 1.0
        assert updated.confidence_score == 1.0  # 0.95 + 0.05 = 1.0

        # Start at 0.05
        low_pattern = pattern.model_copy(update={"confidence_score": 0.05})

        # Failure penalty should not go below 0.0
        updated_low = hook._update_pattern_from_outcome(low_pattern, success=False)
        assert updated_low.confidence_score >= 0.0
        # 0.05 - 0.10 would be -0.05, but bounded to 0.0
        assert updated_low.confidence_score == 0.0

    def test_batch_consolidation(self):
        """Test batch consolidation of multiple task-pattern pairs."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        # Mock the on_task_completed_with_pattern method
        hook.on_task_completed_with_pattern = Mock(return_value=True)

        pairs = [
            {"task_id": 1, "pattern_id": 100, "success": True},
            {"task_id": 2, "pattern_id": 100, "success": False},
            {"task_id": 3, "pattern_id": 101, "success": True},
        ]

        result = hook.consolidate_batch_outcomes(pairs)

        # Verify results
        assert result["total_pairs"] == 3
        assert result["successful"] == 3
        assert result["patterns_updated"] == 2  # Two unique patterns
        assert "timestamp" in result

        # Verify all pairs were processed
        assert hook.on_task_completed_with_pattern.call_count == 3

    def test_outcome_feedback_recording(self):
        """Test that outcome feedback is properly recorded."""
        mock_db = Mock()
        hook = ConsolidationHook(mock_db)

        pattern = TaskPattern(
            id=1,
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
            validation_notes="Initial notes",
        )

        outcome = "Task completed early due to clear requirements"
        updated = hook._update_pattern_from_outcome(
            pattern, success=True, outcome_description=outcome
        )

        # Feedback should be recorded
        assert "Feedback" in updated.validation_notes
        assert outcome in updated.validation_notes
        assert "success" in updated.validation_notes
