"""Unit tests for EffortPredictorService - Phase 1.

Tests the service layer for effort prediction.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from athena.services.effort_predictor import EffortPredictorService
from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPriority


class TestEffortPredictorService:
    """Test EffortPredictorService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mocked database."""
        return EffortPredictorService(mock_db)

    def test_service_initialization(self, mock_db):
        """Test service initializes correctly."""
        service = EffortPredictorService(mock_db)
        assert service.db is mock_db

    def test_default_estimate_for_feature(self, service):
        """Test default estimate for feature tasks."""
        estimate = service._default_estimate_for_type("feature")
        assert estimate == 180  # 3 hours

    def test_default_estimate_for_bugfix(self, service):
        """Test default estimate for bugfix tasks."""
        estimate = service._default_estimate_for_type("bugfix")
        assert estimate == 30  # 30 minutes

    def test_default_estimate_for_doc(self, service):
        """Test default estimate for doc tasks."""
        estimate = service._default_estimate_for_type("doc")
        assert estimate == 45  # 45 minutes

    def test_default_estimate_for_unknown_type(self, service):
        """Test default estimate for unknown task type."""
        estimate = service._default_estimate_for_type("unknown_type")
        assert estimate == 120  # 2 hours (default)

    def test_basic_prediction_format(self, service):
        """Test basic prediction has correct format."""
        pred = service._basic_prediction(100)

        # Check all required fields
        assert "effort" in pred
        assert "confidence" in pred
        assert "bias_factor" in pred
        assert "range" in pred
        assert "explanation" in pred
        assert "sample_count" in pred

        # Check types
        assert isinstance(pred["effort"], int)
        assert isinstance(pred["confidence"], str)
        assert isinstance(pred["bias_factor"], float)
        assert isinstance(pred["range"], dict)
        assert isinstance(pred["sample_count"], int)

        # Check range structure
        assert "optimistic" in pred["range"]
        assert "expected" in pred["range"]
        assert "pessimistic" in pred["range"]

    def test_basic_prediction_values(self, service):
        """Test basic prediction returns reasonable values."""
        base = 100
        pred = service._basic_prediction(base)

        assert pred["effort"] == base
        assert pred["confidence"] == "low"
        assert pred["bias_factor"] == 1.0
        assert pred["sample_count"] == 0

        # Range should be centered around base
        assert pred["range"]["optimistic"] < base
        assert pred["range"]["expected"] == base
        assert pred["range"]["pessimistic"] > base

    def test_task_attachment(self, service):
        """Test that predictions can be attached to tasks."""
        pred = service._basic_prediction(120)

        task = ProspectiveTask(
            project_id=1,
            content="Test task",
            active_form="Testing task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            effort_prediction=pred,
            effort_base_estimate=120,
            effort_task_type="feature"
        )

        # Verify task has prediction attached
        assert task.effort_prediction is not None
        assert task.effort_prediction["effort"] == 120
        assert task.effort_base_estimate == 120
        assert task.effort_task_type == "feature"

    @pytest.mark.asyncio
    async def test_predict_with_error_handling(self, service):
        """Test predict_for_task handles errors gracefully."""
        # With no valid estimator, should return basic prediction
        prediction = await service.predict_for_task(
            project_id=1,
            task_description="Test task",
            task_type="feature",
            base_estimate=100
        )

        # Should still return valid prediction
        assert prediction is not None
        assert "effort" in prediction
        assert prediction["effort"] > 0


class TestDefaultEstimates:
    """Test default estimates for various task types."""

    @pytest.fixture
    def service(self):
        """Create service."""
        mock_db = Mock()
        return EffortPredictorService(mock_db)

    def test_all_task_type_defaults(self, service):
        """Test default estimates for all task types."""
        task_types = {
            "bugfix": 30,
            "doc": 45,
            "refactor": 120,
            "feature": 180,
            "enhancement": 120,
            "research": 120,
            "testing": 90,
            "review": 45,
            "chore": 60,
            "general": 120,
        }

        for task_type, expected_estimate in task_types.items():
            estimate = service._default_estimate_for_type(task_type)
            assert estimate == expected_estimate, \
                f"Expected {expected_estimate} for '{task_type}', got {estimate}"

    def test_case_insensitive_defaults(self, service):
        """Test defaults are case-insensitive."""
        assert service._default_estimate_for_type("FEATURE") == 180
        assert service._default_estimate_for_type("Feature") == 180
        assert service._default_estimate_for_type("BUGFIX") == 30
        assert service._default_estimate_for_type("BugFix") == 30

    def test_empty_type_uses_default(self, service):
        """Test empty task type uses default."""
        estimate = service._default_estimate_for_type("")
        assert estimate == 120  # Default


@pytest.mark.asyncio
async def test_integration_prediction_attachment():
    """Integration test: Create task with prediction."""
    mock_db = Mock()
    service = EffortPredictorService(mock_db)

    # Get prediction
    pred = service._basic_prediction(150)

    # Attach to task
    task = ProspectiveTask(
        project_id=1,
        content="Implement user dashboard",
        active_form="Implementing user dashboard",
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        created_at=datetime.now(),
        effort_prediction=pred,
        effort_base_estimate=150,
        effort_task_type="feature"
    )

    # Verify
    assert task.effort_prediction is not None
    assert task.effort_prediction["effort"] == 150
    assert task.effort_prediction["confidence"] == "low"
    assert task.effort_base_estimate == 150
    assert task.effort_task_type == "feature"

    print(f"✓ Task created with prediction: {task.content}")
    print(f"  Effort: {task.effort_prediction['effort']}m")
    print(f"  Confidence: {task.effort_prediction['confidence']}")
