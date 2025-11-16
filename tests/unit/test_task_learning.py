"""Unit tests for task learning and pattern extraction."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from athena.prospective.task_patterns import (
    TaskPattern,
    TaskExecutionMetrics,
    TaskPropertyCorrelation,
    PatternType,
    ExtractionMethod,
    PatternStatus,
)
from athena.prospective.task_pattern_store import TaskPatternStore
from athena.prospective.pattern_extraction import PatternExtractor
from athena.prospective.pattern_validator import PatternValidator
from athena.prospective.task_learning_integration import TaskLearningIntegration
from athena.prospective.models import ProspectiveTask, TaskPhase, TaskStatus, TaskPriority
from athena.core.database import Database


class TestTaskPatternStore:
    """Test TaskPatternStore model and methods."""

    def test_pattern_model_creation(self):
        """Test creating TaskPattern models."""
        pattern = TaskPattern(
            project_id=1,
            pattern_name="high_priority_success",
            pattern_type=PatternType.SUCCESS_RATE,
            description="High priority tasks have 85% success rate",
            condition_json=json.dumps({"priority": "high"}),
            prediction="85% success rate",
            sample_size=20,
            confidence_score=0.85,
            success_rate=0.85,
            failure_count=3,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        assert pattern.pattern_name == "high_priority_success"
        assert pattern.confidence_score == 0.85
        assert pattern.success_rate == 0.85
        assert pattern.status == PatternStatus.ACTIVE

    def test_pattern_model_with_validation_dates(self):
        """Test pattern model with validation dates."""
        now = datetime.now()
        pattern = TaskPattern(
            pattern_name="test",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test",
            condition_json="{}",
            prediction="test",
            confidence_score=0.8,
            success_rate=0.8,
            extraction_method=ExtractionMethod.STATISTICAL,
            system_2_validated=True,
            last_validated_at=now,
        )

        assert pattern.system_2_validated is True
        assert pattern.last_validated_at == now

    def test_execution_metrics_model(self):
        """Test TaskExecutionMetrics model."""
        metrics = TaskExecutionMetrics(
            task_id=1,
            estimated_total_minutes=120,
            actual_total_minutes=110.5,
            planning_phase_minutes=30,
            executing_phase_minutes=70,
            success=True,
            priority="high",
            complexity_estimate=4,
            dependencies_count=2,
            completed_at=datetime.now(),
        )

        assert metrics.task_id == 1
        assert metrics.estimated_total_minutes == 120
        assert metrics.success is True

    def test_correlation_model(self):
        """Test TaskPropertyCorrelation model."""
        correlation = TaskPropertyCorrelation(
            project_id=1,
            property_name="priority",
            property_value="high",
            total_tasks=50,
            successful_tasks=42,
            failed_tasks=8,
            success_rate=0.84,
            sample_size=50,
            confidence_level=0.95,
            avg_estimated_minutes=120.0,
            avg_actual_minutes=115.0,
            estimation_accuracy_percent=95.8,
        )

        assert correlation.property_name == "priority"
        assert correlation.success_rate == 0.84
        assert correlation.confidence_level == 0.95


class TestPatternExtraction:
    """Test System 1 pattern extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with mock store."""
        mock_store = Mock(spec=TaskPatternStore)
        return PatternExtractor(mock_store, project_id=1)

    def test_extract_priority_patterns(self, extractor: PatternExtractor):
        """Test extracting priority-based patterns."""
        # Create metrics with clear pattern
        metrics_list = []

        # High priority: 90% success (9/10)
        for i in range(9):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=65,
                success=True,
                priority="high",
                completed_at=datetime.now(),
            ))
        metrics_list.append(TaskExecutionMetrics(
            task_id=9,
            estimated_total_minutes=60,
            actual_total_minutes=90,
            success=False,
            failure_mode="Blocked by external factor",
            priority="high",
            completed_at=datetime.now(),
        ))

        # Low priority: 40% success (4/10)
        for i in range(10, 14):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=65,
                success=True,
                priority="low",
                completed_at=datetime.now(),
            ))
        for i in range(14, 20):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=90,
                success=False,
                priority="low",
                completed_at=datetime.now(),
            ))

        patterns = extractor._extract_priority_patterns(metrics_list)

        # Should extract high and low priority patterns
        assert len(patterns) >= 1

        # Check pattern quality
        for pattern in patterns:
            assert pattern.pattern_type == PatternType.SUCCESS_RATE
            assert pattern.sample_size >= 5
            assert 0.0 <= pattern.confidence_score <= 1.0
            assert 0.0 <= pattern.success_rate <= 1.0

    def test_extract_duration_patterns(self, extractor: PatternExtractor):
        """Test extracting duration-based patterns."""
        metrics_list = []

        # Short tasks: 80% success
        for i in range(8):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=30,
                actual_total_minutes=32,
                success=True,
                completed_at=datetime.now(),
            ))
        metrics_list.append(TaskExecutionMetrics(
            task_id=8,
            estimated_total_minutes=30,
            actual_total_minutes=40,
            success=False,
            completed_at=datetime.now(),
        ))

        # Long tasks: 70% success
        for i in range(9, 16):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=300,
                actual_total_minutes=310,
                success=True,
                completed_at=datetime.now(),
            ))
        for i in range(16, 20):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=300,
                actual_total_minutes=400,
                success=False,
                completed_at=datetime.now(),
            ))

        patterns = extractor._extract_duration_patterns(metrics_list)

        assert len(patterns) >= 1
        for pattern in patterns:
            assert pattern.pattern_type == PatternType.DURATION

    def test_calculate_confidence(self, extractor: PatternExtractor):
        """Test confidence score calculation."""
        # Small sample, high success rate → moderate confidence
        conf1 = extractor._calculate_confidence(sample_size=5, success_rate=0.9)
        assert 0.0 < conf1 < 1.0

        # Large sample, moderate success rate → high confidence
        conf2 = extractor._calculate_confidence(sample_size=100, success_rate=0.65)
        assert conf2 > conf1

        # Very small sample → low confidence
        conf3 = extractor._calculate_confidence(sample_size=2, success_rate=0.5)
        assert conf3 < conf1

    def test_extract_all_patterns(self, extractor: PatternExtractor):
        """Test extracting all pattern types."""
        metrics_list = []

        # Create diverse metrics
        for i in range(30):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60 + (i % 3) * 60,
                actual_total_minutes=65 + (i % 3) * 60,
                success=(i % 4) > 0,  # 75% success
                priority=["low", "medium", "high"][i % 3],
                complexity_estimate=(i % 5) + 1,
                dependencies_count=i % 3,
                planning_phase_minutes=30 if i % 2 == 0 else 60,
                completed_at=datetime.now(),
            ))

        patterns = extractor.extract_all_patterns(metrics_list)

        # Should extract multiple patterns
        assert len(patterns) > 0

        # All patterns should have valid structure
        for pattern in patterns:
            assert pattern.pattern_name
            assert pattern.pattern_type in [
                PatternType.SUCCESS_RATE,
                PatternType.DURATION,
                PatternType.PHASE_CORRELATION,
            ]
            assert 0.0 <= pattern.confidence_score <= 1.0
            assert pattern.sample_size >= 5


class TestPatternValidator:
    """Test System 2 LLM-based validation."""

    @pytest.fixture
    def validator(self):
        """Create validator."""
        return PatternValidator()

    def test_fallback_validation(self, validator: PatternValidator):
        """Test fallback validation when LLM unavailable."""
        pattern = TaskPattern(
            project_id=1,
            pattern_name="test_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test pattern",
            condition_json="{}",
            prediction="75% success",
            sample_size=50,
            confidence_score=0.7,
            success_rate=0.75,
            failure_count=5,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        result = validator._fallback_validation(pattern, None)

        assert "is_valid" in result
        assert "confidence_adjustment" in result
        assert "validation_notes" in result
        assert isinstance(result["confidence_adjustment"], (int, float))
        assert -0.15 <= result["confidence_adjustment"] <= 0.15

    def test_apply_validation_results(self, validator: PatternValidator):
        """Test applying validation results to pattern."""
        pattern = TaskPattern(
            project_id=1,
            pattern_name="test_pattern",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test pattern",
            condition_json="{}",
            prediction="75% success",
            sample_size=20,
            confidence_score=0.65,
            success_rate=0.75,
            failure_count=2,
            extraction_method=ExtractionMethod.STATISTICAL,
        )

        validation_result = {
            "is_valid": True,
            "confidence_adjustment": 0.1,
            "validation_notes": "LLM confirms pattern is valid",
            "contradictions": [],
            "recommendations": [],
        }

        updated = validator.apply_validation_results(pattern, validation_result)

        # Check updates
        assert updated.system_2_validated is True
        assert updated.extraction_method == ExtractionMethod.LLM_VALIDATED
        assert updated.confidence_score == 0.75  # 0.65 + 0.1
        assert updated.validation_notes == "LLM confirms pattern is valid"


class TestTaskLearningIntegration:
    """Test task learning integration workflow."""

    @pytest.fixture
    def integration(self):
        """Create integration with mock database."""
        mock_db = Mock(spec=Database)
        integration = TaskLearningIntegration(mock_db)
        return integration

    def test_extract_metrics_from_task(self, integration: TaskLearningIntegration):
        """Test extracting metrics from completed task."""
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

        metrics = integration._extract_metrics_from_task(task)

        assert metrics is not None
        assert metrics.task_id == 1
        assert metrics.success is True
        assert metrics.actual_total_minutes > 0
        assert metrics.priority == "high"

    def test_extract_metrics_with_phases(self, integration: TaskLearningIntegration):
        """Test extracting metrics with phase information."""
        now = datetime.now()

        from athena.prospective.models import PhaseMetrics

        task = ProspectiveTask(
            id=1,
            project_id=1,
            content="Test task",
            active_form="Testing task",
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

        assert metrics is not None
        assert metrics.planning_phase_minutes > 0
        assert metrics.executing_phase_minutes > 0

    def test_should_trigger_extraction(self, integration: TaskLearningIntegration):
        """Test extraction trigger logic."""
        # Initially, should not trigger (no metrics)
        should_extract = integration._should_trigger_extraction(project_id=1, batch_size=10)
        # May be False due to no metrics, which is fine
        assert isinstance(should_extract, bool)


class TestPropertyCorrelations:
    """Test property correlation analysis."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with mock store."""
        mock_store = Mock(spec=TaskPatternStore)
        return PatternExtractor(mock_store, project_id=1)

    def test_extract_property_correlations(self, extractor: PatternExtractor):
        """Test extracting property correlations."""
        metrics_list = []

        # Create metrics with clear priority correlation
        for i in range(10):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=65,
                success=i < 8,  # 80% success for high priority
                priority="high",
                completed_at=datetime.now(),
            ))

        for i in range(10, 20):
            metrics_list.append(TaskExecutionMetrics(
                task_id=i,
                estimated_total_minutes=60,
                actual_total_minutes=70,
                success=i < 14,  # 40% success for low priority
                priority="low",
                completed_at=datetime.now(),
            ))

        correlations = extractor.extract_property_correlations(metrics_list)

        # Should extract correlations for each priority
        assert len(correlations) >= 2

        # Check correlation structure
        for corr in correlations:
            assert corr.property_name == "priority"
            assert corr.property_value in ["high", "low"]
            assert 0.0 <= corr.success_rate <= 1.0
            assert corr.total_tasks > 0


class TestModelValidation:
    """Test Pydantic model validation."""

    def test_task_pattern_model(self):
        """Test TaskPattern model validation."""
        # Valid pattern
        pattern = TaskPattern(
            pattern_name="test",
            pattern_type=PatternType.SUCCESS_RATE,
            description="Test",
            condition_json="{}",
            prediction="test",
            confidence_score=0.8,
            success_rate=0.8,
            extraction_method=ExtractionMethod.STATISTICAL,
        )
        assert pattern.pattern_name == "test"

    def test_execution_metrics_model(self):
        """Test TaskExecutionMetrics model validation."""
        metrics = TaskExecutionMetrics(
            task_id=1,
            estimated_total_minutes=60,
            actual_total_minutes=65,
            completed_at=datetime.now(),
        )
        assert metrics.task_id == 1
        assert metrics.success is True  # Default

    def test_correlation_model(self):
        """Test TaskPropertyCorrelation model validation."""
        corr = TaskPropertyCorrelation(
            property_name="priority",
            property_value="high",
            success_rate=0.85,
        )
        assert corr.property_name == "priority"
        assert corr.total_tasks == 1  # Default


# Markers for test categorization
pytestmark = pytest.mark.unit
