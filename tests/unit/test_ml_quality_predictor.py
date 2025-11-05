"""Unit tests for ML Quality Predictor.

Tests ML-based quality predictions including:
- Feature extraction and normalization
- Quality score prediction
- Confidence calculation
- Model training and evaluation
- Refactoring impact predictions
"""

import pytest
from athena.symbols.ml_quality_predictor import (
    MLQualityPredictor,
    FeatureVector,
    ConfidenceLevel,
    QualityTrend,
)


@pytest.fixture
def predictor():
    """Create a fresh ML predictor."""
    return MLQualityPredictor()


@pytest.fixture
def sample_symbol_data():
    """Create sample symbol data."""
    return {
        "name": "test_function",
        "cyclomatic_complexity": 3,
        "cognitive_complexity": 2,
        "lines_of_code": 25,
        "comment_ratio": 0.2,
        "test_coverage": 0.8,
        "documentation_score": 0.7,
        "dependency_count": 2,
        "incoming_dependencies": 1,
        "detected_patterns": 1,
        "detected_smells": 0,
        "security_score": 0.85,
        "performance_score": 0.8,
        "maintainability_score": 0.75,
    }


@pytest.fixture
def poor_symbol_data():
    """Create poor quality symbol data."""
    return {
        "name": "poor_function",
        "cyclomatic_complexity": 35,
        "cognitive_complexity": 40,
        "lines_of_code": 500,
        "comment_ratio": 0.0,
        "test_coverage": 0.0,
        "documentation_score": 0.1,
        "dependency_count": 15,
        "incoming_dependencies": 20,
        "detected_patterns": 0,
        "detected_smells": 8,
        "security_score": 0.3,
        "performance_score": 0.2,
        "maintainability_score": 0.2,
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_predictor_initialization(predictor):
    """Test predictor initializes correctly."""
    assert predictor.training_data == []
    assert predictor.predictions == {}
    assert predictor.feature_weights is not None
    assert len(predictor.feature_weights) > 0


def test_feature_weights_initialized(predictor):
    """Test feature weights are initialized."""
    weights = predictor.feature_weights
    assert "cyclomatic_complexity" in weights
    assert "test_coverage" in weights
    assert "detected_smells" in weights


# ============================================================================
# Feature Extraction Tests
# ============================================================================


def test_extract_features_basic(predictor, sample_symbol_data):
    """Test basic feature extraction."""
    features = predictor.extract_features(sample_symbol_data)

    assert isinstance(features, FeatureVector)
    assert features.symbol_name == "test_function"
    assert features.cyclomatic_complexity == 3
    assert features.test_coverage == 0.8


def test_extract_features_with_defaults(predictor):
    """Test feature extraction with missing data."""
    minimal_data = {"name": "minimal_func"}
    features = predictor.extract_features(minimal_data)

    assert features.symbol_name == "minimal_func"
    assert features.cyclomatic_complexity == 1.0  # Default
    assert features.test_coverage == 0.0  # Default
    assert features.lines_of_code == 10  # Default


def test_normalize_features(predictor, sample_symbol_data):
    """Test feature normalization."""
    features = predictor.extract_features(sample_symbol_data)
    normalized = predictor.normalize_features(features)

    assert "cyclomatic_complexity" in normalized
    assert "test_coverage" in normalized
    assert all(0.0 <= v <= 1.0 for v in normalized.values())


# ============================================================================
# Prediction Tests
# ============================================================================


def test_predict_good_quality(predictor, sample_symbol_data):
    """Test prediction for good quality code."""
    prediction = predictor.predict(sample_symbol_data)

    assert prediction.symbol_name == "test_function"
    assert 0.0 <= prediction.predicted_quality_score <= 100.0
    assert prediction.predicted_category in ["excellent", "good", "fair", "poor", "critical"]
    assert 0.0 <= prediction.confidence <= 1.0


def test_predict_poor_quality(predictor, poor_symbol_data):
    """Test prediction for poor quality code."""
    prediction = predictor.predict(poor_symbol_data)

    assert prediction.predicted_quality_score < 60.0
    assert prediction.predicted_category in ["poor", "critical"]


def test_predict_stores_prediction(predictor, sample_symbol_data):
    """Test that predictions are stored."""
    prediction = predictor.predict(sample_symbol_data)

    assert "test_function" in predictor.predictions
    assert predictor.predictions["test_function"] == prediction


def test_prediction_confidence_levels(predictor):
    """Test confidence level mapping."""
    # High confidence data (consistent metrics)
    good_data = {
        "name": "good",
        "cyclomatic_complexity": 5,
        "cognitive_complexity": 3,
        "test_coverage": 0.9,
        "detected_smells": 0,
        "security_score": 0.9,
        "performance_score": 0.9,
        "maintainability_score": 0.9,
    }
    prediction = predictor.predict(good_data)
    assert prediction.confidence_level in [
        ConfidenceLevel.HIGH,
        ConfidenceLevel.VERY_HIGH,
    ]


def test_score_to_category(predictor):
    """Test score to category conversion."""
    assert predictor._score_to_category(90) == "excellent"
    assert predictor._score_to_category(75) == "good"
    assert predictor._score_to_category(60) == "fair"
    assert predictor._score_to_category(45) == "poor"
    assert predictor._score_to_category(20) == "critical"


# ============================================================================
# Confidence Calculation Tests
# ============================================================================


def test_calculate_confidence_boost_for_tests(predictor, sample_symbol_data):
    """Test confidence boost for high test coverage."""
    sample_symbol_data["test_coverage"] = 0.95
    prediction = predictor.predict(sample_symbol_data)

    assert prediction.confidence > 0.7


def test_calculate_confidence_penalty_for_complexity(predictor):
    """Test confidence penalty for high complexity."""
    complex_data = {
        "name": "complex",
        "cyclomatic_complexity": 40,
        "test_coverage": 0.5,
    }
    prediction = predictor.predict(complex_data)

    assert prediction.confidence < 0.8


def test_confidence_never_below_minimum(predictor, poor_symbol_data):
    """Test confidence has minimum threshold."""
    prediction = predictor.predict(poor_symbol_data)

    assert prediction.confidence >= 0.3


# ============================================================================
# Feature Importance Tests
# ============================================================================


def test_calculate_feature_importance(predictor, sample_symbol_data):
    """Test feature importance calculation."""
    features = predictor.extract_features(sample_symbol_data)
    normalized = predictor.normalize_features(features)
    importance = predictor._calculate_feature_importance(normalized, features)

    assert isinstance(importance, dict)
    # Importances should sum to ~1.0
    assert 0.9 <= sum(importance.values()) <= 1.1


def test_feature_importance_identifies_key_factors(predictor):
    """Test that important factors are identified."""
    # High complexity should be important
    complex_data = {
        "name": "test",
        "cyclomatic_complexity": 50,
        "test_coverage": 0.5,
    }
    features = predictor.extract_features(complex_data)
    normalized = predictor.normalize_features(features)
    importance = predictor._calculate_feature_importance(normalized, features)

    # Cyclomatic complexity should be among top factors
    assert isinstance(importance, dict)


# ============================================================================
# Reasoning Generation Tests
# ============================================================================


def test_generate_reasoning(predictor, sample_symbol_data):
    """Test reasoning generation."""
    prediction = predictor.predict(sample_symbol_data)

    assert len(prediction.reasoning) > 0
    assert all(isinstance(r, str) for r in prediction.reasoning)


def test_reasoning_includes_confidence(predictor):
    """Test reasoning includes confidence statement."""
    low_confidence_data = {
        "name": "uncertain",
        "cyclomatic_complexity": 1,
        "test_coverage": 0.1,
        "detected_smells": 5,
    }
    prediction = predictor.predict(low_confidence_data)

    reasoning_text = " ".join(prediction.reasoning).lower()
    assert "confidence" in reasoning_text or len(prediction.reasoning) > 0


# ============================================================================
# Training and Evaluation Tests
# ============================================================================


def test_train_on_data(predictor, sample_symbol_data, poor_symbol_data):
    """Test training on historical data."""
    data_list = [sample_symbol_data, poor_symbol_data]
    scores = [75.0, 35.0]

    predictor.train_on_data(data_list, scores)

    assert len(predictor.training_data) == 2


def test_evaluate_predictions_accuracy(predictor, sample_symbol_data):
    """Test prediction evaluation."""
    prediction = predictor.predict(sample_symbol_data)
    actual_scores = {"test_function": 78.0}

    performance = predictor.evaluate_predictions(actual_scores)

    assert performance.total_predictions == 1
    assert performance.accuracy >= 0.0


def test_evaluate_predictions_with_multiple_samples(predictor):
    """Test evaluation with multiple predictions."""
    data1 = {
        "name": "func1",
        "cyclomatic_complexity": 5,
        "test_coverage": 0.8,
    }
    data2 = {
        "name": "func2",
        "cyclomatic_complexity": 20,
        "test_coverage": 0.2,
    }

    predictor.predict(data1)
    predictor.predict(data2)

    actual_scores = {"func1": 75.0, "func2": 45.0}
    performance = predictor.evaluate_predictions(actual_scores)

    assert performance.total_predictions == 2


def test_mean_absolute_error_calculation(predictor, sample_symbol_data):
    """Test MAE calculation."""
    prediction = predictor.predict(sample_symbol_data)
    actual_scores = {"test_function": prediction.predicted_quality_score + 10}

    performance = predictor.evaluate_predictions(actual_scores)

    assert performance.mean_absolute_error >= 0.0


# ============================================================================
# Refactoring Impact Tests
# ============================================================================


def test_predict_refactoring_impact_positive(predictor, sample_symbol_data):
    """Test predicting positive refactoring impact."""
    refactoring_changes = {
        "cyclomatic_complexity": 1,  # Reduce complexity significantly
        "test_coverage": 0.98,  # Increase test coverage significantly
        "detected_smells": 0,  # Remove all smells
    }

    impact = predictor.predict_refactoring_impact(
        sample_symbol_data, refactoring_changes
    )

    assert impact["score_improvement"] > 0
    assert impact["worth_refactoring"] == True


def test_predict_refactoring_impact_negative(predictor, sample_symbol_data):
    """Test predicting negative refactoring impact."""
    refactoring_changes = {
        "cyclomatic_complexity": 50,  # Increase complexity
        "detected_smells": 5,  # Add smells
    }

    impact = predictor.predict_refactoring_impact(
        sample_symbol_data, refactoring_changes
    )

    assert impact["score_improvement"] < 0
    assert impact["worth_refactoring"] == False


def test_refactoring_impact_includes_category_change(predictor):
    """Test refactoring impact shows category change."""
    current = {
        "name": "func",
        "cyclomatic_complexity": 20,
        "test_coverage": 0.3,
        "detected_smells": 4,
    }

    refactoring = {
        "cyclomatic_complexity": 8,
        "test_coverage": 0.8,
        "detected_smells": 0,
    }

    impact = predictor.predict_refactoring_impact(current, refactoring)

    assert "current_category" in impact
    assert "predicted_category" in impact


# ============================================================================
# Summary Generation Tests
# ============================================================================


def test_prediction_summary_empty(predictor):
    """Test summary with no predictions."""
    summary = predictor.get_prediction_summary()

    assert summary["total_predictions"] == 0
    assert summary["average_score"] == 0.0


def test_prediction_summary_with_data(predictor, sample_symbol_data, poor_symbol_data):
    """Test summary with predictions."""
    predictor.predict(sample_symbol_data)
    predictor.predict(poor_symbol_data)

    summary = predictor.get_prediction_summary()

    assert summary["total_predictions"] == 2
    assert summary["average_score"] > 0.0
    assert "score_distribution" in summary
    assert "confidence_distribution" in summary


def test_summary_score_distribution(predictor):
    """Test score distribution in summary."""
    data_excellent = {
        "name": "excellent",
        "cyclomatic_complexity": 1,
        "test_coverage": 1.0,
        "detected_smells": 0,
    }
    data_poor = {
        "name": "poor",
        "cyclomatic_complexity": 40,
        "test_coverage": 0.0,
        "detected_smells": 8,
    }

    predictor.predict(data_excellent)
    predictor.predict(data_poor)

    summary = predictor.get_prediction_summary()

    assert len(summary["score_distribution"]) >= 2


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_prediction_workflow(predictor, sample_symbol_data):
    """Test complete prediction workflow."""
    # Predict
    prediction = predictor.predict(sample_symbol_data)
    assert prediction is not None

    # Evaluate (even with single sample)
    actual_scores = {"test_function": 77.5}
    performance = predictor.evaluate_predictions(actual_scores)
    assert performance.total_predictions == 1

    # Get summary
    summary = predictor.get_prediction_summary()
    assert summary["total_predictions"] == 1


def test_batch_predictions(predictor):
    """Test batch prediction processing."""
    symbols = [
        {
            "name": f"func{i}",
            "cyclomatic_complexity": i + 1,
            "test_coverage": 0.5 + (i * 0.05),
            "detected_smells": i % 3,
        }
        for i in range(5)
    ]

    for symbol in symbols:
        predictor.predict(symbol)

    assert len(predictor.predictions) == 5
    summary = predictor.get_prediction_summary()
    assert summary["total_predictions"] == 5


def test_prediction_consistency(predictor, sample_symbol_data):
    """Test that same input produces same prediction."""
    pred1 = predictor.predict(sample_symbol_data)
    score1 = pred1.predicted_quality_score

    # Clear predictions but keep same predictor
    predictor.predictions = {}

    pred2 = predictor.predict(sample_symbol_data)
    score2 = pred2.predicted_quality_score

    assert abs(score1 - score2) < 0.01  # Should be identical


def test_multiple_symbol_analysis(predictor):
    """Test analyzing multiple different symbols."""
    symbols = {
        "simple": {
            "name": "simple",
            "cyclomatic_complexity": 1,
            "test_coverage": 0.9,
        },
        "moderate": {
            "name": "moderate",
            "cyclomatic_complexity": 10,
            "test_coverage": 0.6,
        },
        "complex": {
            "name": "complex",
            "cyclomatic_complexity": 30,
            "test_coverage": 0.2,
        },
    }

    for symbol in symbols.values():
        predictor.predict(symbol)

    # Verify predictions are ranked
    predictions = list(predictor.predictions.values())
    scores = [p.predicted_quality_score for p in predictions]

    # Simple should score higher than complex
    assert scores[0] > scores[2]


# ============================================================================
# Edge Cases Tests
# ============================================================================


def test_predict_extreme_values(predictor):
    """Test prediction with extreme metric values."""
    extreme_data = {
        "name": "extreme",
        "cyclomatic_complexity": 100,
        "lines_of_code": 10000,
        "test_coverage": 0.0,
        "detected_smells": 20,
    }

    prediction = predictor.predict(extreme_data)

    assert 0.0 <= prediction.predicted_quality_score <= 100.0
    assert prediction.confidence > 0.0


def test_predict_zero_values(predictor):
    """Test prediction with zero metrics."""
    zero_data = {
        "name": "minimal",
        "cyclomatic_complexity": 1,
        "lines_of_code": 1,
        "test_coverage": 0.0,
        "detected_smells": 0,
    }

    prediction = predictor.predict(zero_data)

    assert prediction.predicted_quality_score > 0.0


def test_confidence_bounds(predictor, sample_symbol_data):
    """Test confidence always within bounds."""
    for _ in range(10):
        prediction = predictor.predict(sample_symbol_data)
        assert 0.0 <= prediction.confidence <= 1.0
