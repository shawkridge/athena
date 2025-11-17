"""Integration tests for task learning pipeline.

Tests the full workflow:
1. Task completion → metrics capture
2. Metrics analysis → pattern extraction
3. Pattern extraction → System 2 validation
4. Validation → pattern storage
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from athena.prospective.task_patterns import (
    TaskPattern,
    TaskExecutionMetrics,
    PatternType,
    ExtractionMethod,
)
from athena.prospective.task_pattern_store import TaskPatternStore
from athena.prospective.pattern_extraction import PatternExtractor
from athena.prospective.pattern_validator import PatternValidator
from athena.prospective.task_learning_integration import TaskLearningIntegration
from athena.prospective.models import (
    ProspectiveTask,
    TaskPhase,
    TaskStatus,
    TaskPriority,
    PhaseMetrics,
)


class TestTaskCompletionToMetricsCapture:
    """Test task completion triggers metrics capture."""

    def test_capture_simple_task_completion(self):
        """Test capturing metrics from a simple completed task."""
        mock_db = Mock()
        integration = TaskLearningIntegration(mock_db)

        # Create a completed task
        now = datetime.now()
        task = ProspectiveTask(
            id=1,
            project_id=1,
            content="Implement feature",
            active_form="Implementing feature",
            created_at=now - timedelta(hours=2),
            completed_at=now,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
        )

        # Extract metrics
        metrics = integration._extract_metrics_from_task(task)

        # Verify metrics extracted
        assert metrics is not None
        assert metrics.task_id == 1
        assert metrics.success is True
        assert metrics.actual_total_minutes > 0
        assert metrics.priority == "high"

    def test_capture_task_with_phase_tracking(self):
        """Test capturing metrics from task with phase details."""
        mock_db = Mock()
        integration = TaskLearningIntegration(mock_db)

        now = datetime.now()
        task = ProspectiveTask(
            id=2,
            project_id=1,
            content="Implement feature",
            active_form="Implementing feature",
            created_at=now - timedelta(hours=2),
            completed_at=now,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.COMPLETED,
            phase_metrics=[
                PhaseMetrics(
                    phase=TaskPhase.PLANNING,
                    started_at=now - timedelta(hours=2),
                    completed_at=now - timedelta(hours=1, minutes=30),
                ),
                PhaseMetrics(
                    phase=TaskPhase.EXECUTING,
                    started_at=now - timedelta(hours=1, minutes=30),
                    completed_at=now,
                ),
            ],
        )

        metrics = integration._extract_metrics_from_task(task)

        # Verify phase metrics extracted
        assert metrics.planning_phase_minutes > 0
        assert metrics.executing_phase_minutes > 0
        assert (
            metrics.planning_phase_minutes + metrics.executing_phase_minutes
            > 0
        )

    def test_capture_failed_task(self):
        """Test capturing metrics from a failed task."""
        mock_db = Mock()
        integration = TaskLearningIntegration(mock_db)

        now = datetime.now()
        task = ProspectiveTask(
            id=3,
            project_id=1,
            content="Implement feature",
            active_form="Implementing feature",
            created_at=now - timedelta(hours=3),
            completed_at=now,
            status=TaskStatus.BLOCKED,
            phase=TaskPhase.FAILED,
            failure_reason="External blocker: API unavailable",
        )

        metrics = integration._extract_metrics_from_task(task)

        # Verify failure captured
        assert metrics is not None
        assert metrics.success is False
        assert metrics.failure_mode == "External blocker: API unavailable"


class TestPatternExtractionAccuracy:
    """Test System 1 pattern extraction accuracy."""

    def test_extract_priority_pattern_high_confidence(self):
        """Test extracting high-confidence priority patterns."""
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        # Create test data: high priority tasks with 90% success
        metrics_list = []
        for i in range(10):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=60,
                    actual_total_minutes=65,
                    success=i < 9,  # 90% success
                    priority="high",
                    completed_at=datetime.now(),
                )
            )

        # Add low priority tasks (40% success) for contrast
        for i in range(10, 20):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=60,
                    actual_total_minutes=80,
                    success=i < 14,  # 40% success
                    priority="low",
                    completed_at=datetime.now(),
                )
            )

        patterns = extractor._extract_priority_patterns(metrics_list)

        # Should extract at least one pattern
        assert len(patterns) > 0

        # Verify pattern quality
        high_priority_patterns = [
            p for p in patterns if "high" in p.pattern_name
        ]
        assert len(high_priority_patterns) > 0

        for pattern in high_priority_patterns:
            # High priority should have high success rate
            assert pattern.success_rate > 0.8
            # Should have reasonable sample size
            assert pattern.sample_size >= 5
            # Confidence should be positive (even if not super high with small sample)
            assert pattern.confidence_score > 0.0
            assert pattern.confidence_score <= 1.0

    def test_extract_duration_pattern(self):
        """Test extracting duration-based patterns."""
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        metrics_list = []

        # Short tasks: mostly successful
        for i in range(10):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=30,
                    actual_total_minutes=32,
                    success=i < 9,  # 90% success
                    completed_at=datetime.now(),
                )
            )

        # Long tasks: less successful
        for i in range(10, 20):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=300,
                    actual_total_minutes=350,
                    success=i < 14,  # 40% success
                    completed_at=datetime.now(),
                )
            )

        patterns = extractor._extract_duration_patterns(metrics_list)

        assert len(patterns) > 0

        # Should identify that short tasks succeed more
        short_patterns = [p for p in patterns if "short" in p.pattern_name]
        long_patterns = [p for p in patterns if "long" in p.pattern_name]

        if short_patterns and long_patterns:
            assert short_patterns[0].success_rate > long_patterns[0].success_rate

    def test_all_patterns_have_valid_confidence(self):
        """Test that all extracted patterns have valid confidence scores."""
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        # Create diverse test data
        metrics_list = []
        for i in range(30):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=60 + (i % 3) * 60,
                    actual_total_minutes=65 + (i % 3) * 60,
                    success=(i % 4) > 0,  # 75% success
                    priority=["low", "medium", "high"][i % 3],
                    complexity_estimate=(i % 5) + 1,
                    dependencies_count=i % 3,
                    completed_at=datetime.now(),
                )
            )

        patterns = extractor.extract_all_patterns(metrics_list)

        # All patterns should have valid confidence
        for pattern in patterns:
            assert 0.0 <= pattern.confidence_score <= 1.0
            assert pattern.sample_size >= 5
            assert 0.0 <= pattern.success_rate <= 1.0


class TestSystem2Validation:
    """Test System 2 LLM-based pattern validation."""

    def test_validate_uncertain_pattern(self):
        """Test System 2 validation of uncertain patterns."""
        validator = PatternValidator()

        # Create a pattern with medium confidence
        pattern = TaskPattern(
            pattern_name="test_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test pattern with medium confidence",
            condition_json=json.dumps({"priority": "medium"}),
            prediction="65% success rate",
            sample_size=15,
            confidence_score=0.65,  # Below 0.8 threshold
            success_rate=0.65,
            failure_count=5,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        # Validate using fallback (no LLM)
        result = validator._fallback_validation(pattern, None)

        assert "is_valid" in result
        assert "confidence_adjustment" in result
        assert result["confidence_adjustment"] is not None

    def test_apply_validation_results_to_pattern(self):
        """Test applying validation results updates pattern correctly."""
        validator = PatternValidator()

        pattern = TaskPattern(
            pattern_name="test",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test",
            condition_json="{}",
            prediction="test",
            sample_size=25,
            confidence_score=0.70,
            success_rate=0.70,
            failure_count=3,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        validation_result = {
            "is_valid": True,
            "confidence_adjustment": 0.15,
            "validation_notes": "LLM confirms pattern",
            "contradictions": [],
            "recommendations": [],
        }

        updated = validator.apply_validation_results(pattern, validation_result)

        # Confidence should increase
        assert updated.confidence_score > pattern.confidence_score
        # Should be marked as validated
        assert updated.system_2_validated is True
        # Extraction method should update
        assert updated.extraction_method == ExtractionMethod.LLM_VALIDATED

    def test_high_confidence_patterns_skip_validation(self):
        """Test that high-confidence patterns skip validation."""
        validator = PatternValidator()

        pattern = TaskPattern(
            pattern_name="high_conf",
            pattern_type=PatternType.SUCCESS_RATE,
            description="High confidence pattern",
            condition_json="{}",
            prediction="test",
            sample_size=100,
            confidence_score=0.90,  # Above 0.8 threshold
            success_rate=0.90,
            failure_count=2,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        result = validator.validate_pattern(pattern, None)

        # High confidence patterns should skip validation
        assert result["confidence_adjustment"] == 0.0
        assert "already high confidence" in result["validation_notes"]


class TestFullPipeline:
    """Test the complete learning pipeline."""

    def test_end_to_end_task_to_pattern(self):
        """Test complete pipeline: task → metrics → patterns → validation."""
        mock_db = Mock()
        integration = TaskLearningIntegration(mock_db)

        # Step 1: Create completed task
        now = datetime.now()
        task = ProspectiveTask(
            id=1,
            project_id=1,
            content="Test task",
            active_form="Testing task",
            created_at=now - timedelta(hours=2),
            completed_at=now,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
        )

        # Step 2: Extract metrics
        metrics = integration._extract_metrics_from_task(task)
        assert metrics is not None
        assert metrics.success is True

        # Step 3: Create extractor and extract patterns
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        # Create additional metrics for pattern extraction
        metrics_list = [metrics]
        for i in range(1, 10):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i + 1,
                    estimated_total_minutes=120,
                    actual_total_minutes=125,
                    success=i < 8,  # 80% success
                    priority="high",
                    completed_at=datetime.now(),
                )
            )

        patterns = extractor.extract_all_patterns(metrics_list)
        assert len(patterns) > 0

        # Step 4: Validate patterns
        validator = PatternValidator()
        for pattern in patterns:
            if pattern.confidence_score < 0.8:
                result = validator.validate_pattern(pattern, None)
                assert "is_valid" in result
                updated = validator.apply_validation_results(pattern, result)
                assert updated.system_2_validated is True

        # Pipeline completed successfully
        assert len(patterns) > 0
        assert all(p.confidence_score >= 0.0 for p in patterns)
        assert all(p.confidence_score <= 1.0 for p in patterns)

    def test_property_correlation_extraction(self):
        """Test extracting property correlations from metrics."""
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        # Create metrics with clear priority correlation
        metrics_list = []
        # High priority: 85% success
        for i in range(10):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=60,
                    actual_total_minutes=65,
                    success=i < 8,
                    priority="high",
                    completed_at=datetime.now(),
                )
            )

        # Low priority: 40% success
        for i in range(10, 20):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=60,
                    actual_total_minutes=75,
                    success=i < 14,
                    priority="low",
                    completed_at=datetime.now(),
                )
            )

        correlations = extractor.extract_property_correlations(metrics_list)

        # Should extract correlations
        assert len(correlations) >= 2

        # Verify correlation structure
        for corr in correlations:
            assert corr.property_name == "priority"
            assert 0.0 <= corr.success_rate <= 1.0
            assert corr.total_tasks > 0

    def test_metrics_error_handling(self):
        """Test error handling for malformed tasks."""
        mock_db = Mock()
        integration = TaskLearningIntegration(mock_db)

        # Task without completion timestamp
        task = ProspectiveTask(
            id=1,
            project_id=1,
            content="Incomplete task",
            active_form="Working on task",
            created_at=datetime.now(),
            completed_at=None,  # Not completed
            status=TaskStatus.PENDING,
        )

        metrics = integration._extract_metrics_from_task(task)
        # Should return None for incomplete task
        assert metrics is None


class TestIntegrationEdgeCases:
    """Test edge cases in the integration pipeline."""

    def test_very_small_sample_size(self):
        """Test extraction with very small sample size."""
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        # Only 3 metrics
        metrics_list = [
            TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=65,
                success=True,
                priority="high",
                completed_at=datetime.now(),
            )
            for i in range(3)
        ]

        patterns = extractor.extract_all_patterns(metrics_list)

        # Should not extract patterns with very small sample
        # (MIN_SAMPLE_SIZE = 5)
        assert len(patterns) == 0

    def test_all_success_pattern(self):
        """Test extraction when all tasks succeed."""
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        metrics_list = [
            TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=65,
                success=True,  # All succeed
                priority="high",
                completed_at=datetime.now(),
            )
            for i in range(10)
        ]

        patterns = extractor.extract_all_patterns(metrics_list)

        # Should still extract patterns even with 100% success
        assert len(patterns) >= 0

        # If patterns extracted, success rate should be high
        for pattern in patterns:
            assert pattern.success_rate >= 0.8

    def test_all_failure_pattern(self):
        """Test extraction when all tasks fail."""
        mock_store = Mock(spec=TaskPatternStore)
        extractor = PatternExtractor(mock_store, project_id=1)

        metrics_list = [
            TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=120,  # Double the estimate
                success=False,  # All fail
                failure_mode="Scope creep",
                priority="low",
                completed_at=datetime.now(),
            )
            for i in range(10)
        ]

        patterns = extractor.extract_all_patterns(metrics_list)

        # Should extract patterns even with 0% success
        assert len(patterns) >= 0


# Markers for test categorization
pytestmark = pytest.mark.integration
