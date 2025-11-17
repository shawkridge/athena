"""Integration tests for effort prediction - Phase 1.

Tests the complete flow of task creation with automatic effort prediction.
"""

import pytest
from datetime import datetime

from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPriority
from athena.services.effort_predictor import EffortPredictorService
from athena.core.database import Database


@pytest.fixture
async def effort_predictor_service(test_database):
    """Create effort predictor service."""
    return EffortPredictorService(test_database)


@pytest.mark.asyncio
async def test_predict_for_feature_task(effort_predictor_service):
    """Test effort prediction for feature task type."""
    prediction = await effort_predictor_service.predict_for_task(
        project_id=1,
        task_description="Add user authentication to API",
        task_type="feature",
        base_estimate=120  # User thinks 2 hours
    )

    # Verify prediction has all required fields
    assert "effort" in prediction
    assert "confidence" in prediction
    assert "range" in prediction
    assert "bias_factor" in prediction
    assert "explanation" in prediction
    assert "sample_count" in prediction

    # Verify confidence is valid
    assert prediction["confidence"] in ["low", "medium", "high"]

    # Verify range is reasonable
    assert prediction["range"]["optimistic"] < prediction["effort"]
    assert prediction["effort"] < prediction["range"]["pessimistic"]

    # Verify effort is positive
    assert prediction["effort"] > 0

    print(f"✓ Feature prediction: {prediction['effort']}m (confidence: {prediction['confidence']})")


@pytest.mark.asyncio
async def test_predict_for_bugfix_task(effort_predictor_service):
    """Test effort prediction for bugfix task type."""
    prediction = await effort_predictor_service.predict_for_task(
        project_id=1,
        task_description="Fix critical bug in payment processing",
        task_type="bugfix",
        base_estimate=None  # No user estimate
    )

    # Should use default for bugfix (~30 minutes)
    assert prediction["effort"] > 0
    assert prediction["confidence"] is not None

    # Bugfix default should be relatively low
    assert prediction["effort"] < 120

    print(f"✓ Bugfix prediction: {prediction['effort']}m (used default)")


@pytest.mark.asyncio
async def test_prediction_with_no_estimate(effort_predictor_service):
    """Test prediction when user doesn't provide estimate."""
    prediction = await effort_predictor_service.predict_for_task(
        project_id=1,
        task_description="Write documentation for API",
        task_type="doc",
        base_estimate=None
    )

    # Should use default estimate
    assert prediction["effort"] > 0
    assert "explanation" in prediction

    print(f"✓ Default estimate used: {prediction['effort']}m")


@pytest.mark.asyncio
async def test_prediction_with_low_confidence(effort_predictor_service):
    """Test prediction confidence when no historical data exists."""
    prediction = await effort_predictor_service.predict_for_task(
        project_id=999,  # Non-existent project with no history
        task_description="Some random task",
        task_type="general",
        base_estimate=60
    )

    # With no history, should have low confidence
    assert prediction["confidence"] == "low"
    assert prediction["sample_count"] == 0
    assert "No historical" in prediction["explanation"]

    print(f"✓ Low confidence shown for new project: {prediction['confidence']}")


@pytest.mark.asyncio
async def test_prediction_format(effort_predictor_service):
    """Test that prediction has correct format and types."""
    prediction = await effort_predictor_service.predict_for_task(
        project_id=1,
        task_description="Test format validation",
        task_type="testing",
        base_estimate=45
    )

    # Verify types
    assert isinstance(prediction["effort"], int)
    assert isinstance(prediction["confidence"], str)
    assert isinstance(prediction["bias_factor"], float)
    assert isinstance(prediction["range"], dict)
    assert isinstance(prediction["explanation"], str)
    assert isinstance(prediction["sample_count"], int)

    # Verify range structure
    assert "optimistic" in prediction["range"]
    assert "expected" in prediction["range"]
    assert "pessimistic" in prediction["range"]

    # Verify range values are integers
    assert isinstance(prediction["range"]["optimistic"], int)
    assert isinstance(prediction["range"]["expected"], int)
    assert isinstance(prediction["range"]["pessimistic"], int)

    print("✓ Prediction format valid")


@pytest.mark.asyncio
async def test_different_task_types(effort_predictor_service):
    """Test prediction for various task types."""
    task_types = ["feature", "bugfix", "refactor", "doc", "testing"]
    predictions = {}

    for task_type in task_types:
        pred = await effort_predictor_service.predict_for_task(
            project_id=1,
            task_description=f"Generic {task_type} task",
            task_type=task_type,
            base_estimate=None
        )
        predictions[task_type] = pred["effort"]

    # Verify we got predictions for all types
    assert len(predictions) == len(task_types)

    # Bugfix should be shorter than feature
    assert predictions["bugfix"] < predictions["feature"]

    # Doc should be reasonable
    assert predictions["doc"] > 0

    print(f"✓ All task types predicted:")
    for task_type, effort in predictions.items():
        print(f"  {task_type}: {effort}m")


@pytest.mark.asyncio
async def test_prediction_improves_with_history(effort_predictor_service, test_database: Database):
    """Test that predictions improve as history grows.

    This test simulates recording completions and verifies that
    subsequent predictions become more accurate.
    """
    # Get initial prediction (no history)
    pred1 = await effort_predictor_service.predict_for_task(
        project_id=2,  # New project
        task_description="Feature task",
        task_type="feature",
        base_estimate=100
    )

    initial_confidence = pred1["confidence"]
    initial_bias = pred1["bias_factor"]

    # Record some completions (simulate history)
    accuracy_store = effort_predictor_service.accuracy_store

    for i in range(5):
        accuracy_store.record_completion(
            project_id=2,
            task_type="feature",
            estimate_minutes=100,
            actual_minutes=113  # Consistently 13% over
        )

    # Get new prediction (with history)
    pred2 = await effort_predictor_service.predict_for_task(
        project_id=2,
        task_description="Another feature task",
        task_type="feature",
        base_estimate=100
    )

    new_confidence = pred2["confidence"]
    new_bias = pred2["bias_factor"]

    # Verify improvements
    confidence_levels = {"low": 0, "medium": 1, "high": 2}
    assert confidence_levels.get(new_confidence, -1) >= confidence_levels.get(initial_confidence, -1)

    # Bias should reflect 13% overrun
    assert new_bias > initial_bias

    # New estimate should be higher (reflecting the bias)
    assert pred2["effort"] > pred1["effort"]

    print(f"✓ Prediction improved with history:")
    print(f"  Confidence: {initial_confidence} → {new_confidence}")
    print(f"  Bias factor: {initial_bias:.2f}x → {new_bias:.2f}x")
    print(f"  Estimate: {pred1['effort']}m → {pred2['effort']}m")


class TestEffortPredictorErrorHandling:
    """Test error handling in effort predictor."""

    @pytest.mark.asyncio
    async def test_handles_invalid_task_type(self, effort_predictor_service):
        """Test that invalid task type is handled gracefully."""
        prediction = await effort_predictor_service.predict_for_task(
            project_id=1,
            task_description="Unknown type task",
            task_type="unknown_type_xyz",
            base_estimate=120
        )

        # Should still return prediction (with default estimate)
        assert prediction["effort"] > 0
        assert prediction["confidence"] is not None

    @pytest.mark.asyncio
    async def test_handles_none_description(self, effort_predictor_service):
        """Test that None description is handled."""
        prediction = await effort_predictor_service.predict_for_task(
            project_id=1,
            task_description="",
            task_type="feature",
            base_estimate=90
        )

        # Should still return prediction
        assert prediction["effort"] > 0

    @pytest.mark.asyncio
    async def test_handles_zero_estimate(self, effort_predictor_service):
        """Test that zero estimate is handled."""
        prediction = await effort_predictor_service.predict_for_task(
            project_id=1,
            task_description="Task with zero estimate",
            task_type="feature",
            base_estimate=0
        )

        # Should return prediction, possibly using default
        assert prediction["effort"] >= 0


@pytest.mark.asyncio
async def test_effort_prediction_end_to_end(test_database: Database):
    """End-to-end test of effort prediction integration.

    Simulates creating a task and verifying the prediction is attached.
    """
    service = EffortPredictorService(test_database)

    # Create prediction
    prediction = await service.predict_for_task(
        project_id=1,
        task_description="Build REST API endpoint",
        task_type="feature",
        base_estimate=180
    )

    # Verify prediction can be attached to a task
    task = ProspectiveTask(
        project_id=1,
        content="Build REST API endpoint",
        active_form="Building REST API endpoint",
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        created_at=datetime.now(),
        # Attach prediction
        effort_prediction=prediction,
        effort_base_estimate=180,
        effort_task_type="feature"
    )

    # Verify task has prediction
    assert task.effort_prediction is not None
    assert task.effort_prediction["effort"] > 0
    assert task.effort_base_estimate == 180
    assert task.effort_task_type == "feature"

    print("✓ End-to-end prediction attachment successful")
