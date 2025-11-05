"""ML-Based Quality Predictions for code quality scoring.

Provides:
- Feature extraction from symbols and metrics
- Quality prediction model training and evaluation
- Historical prediction accuracy tracking
- Model confidence scoring
- Refactoring impact predictions
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


class ConfidenceLevel(str, Enum):
    """Confidence levels for ML predictions."""
    VERY_LOW = "very_low"      # <0.5
    LOW = "low"                 # 0.5-0.65
    MEDIUM = "medium"           # 0.65-0.8
    HIGH = "high"               # 0.8-0.9
    VERY_HIGH = "very_high"    # >0.9


class QualityTrend(str, Enum):
    """Quality trend directions."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class FeatureVector:
    """Extracted features from a symbol."""
    symbol_name: str
    cyclomatic_complexity: float
    cognitive_complexity: float
    lines_of_code: int
    comment_ratio: float  # 0-1
    test_coverage: float  # 0-1
    documentation_score: float  # 0-1
    dependency_count: int
    incoming_dependencies: int
    detected_patterns: int
    detected_smells: int
    security_score: float  # 0-1
    performance_score: float  # 0-1
    maintainability_score: float  # 0-1


@dataclass
class Prediction:
    """ML prediction for quality."""
    symbol_name: str
    predicted_quality_score: float  # 0-100
    predicted_category: str  # excellent, good, fair, poor, critical
    confidence: float  # 0-1
    confidence_level: ConfidenceLevel
    feature_importance: Dict[str, float]  # feature -> importance score
    reasoning: List[str]  # Explanation of prediction


@dataclass
class PredictionMetric:
    """Metrics for a prediction."""
    predicted_value: float
    actual_value: Optional[float] = None
    error: Optional[float] = None  # actual - predicted
    absolute_error: Optional[float] = None
    is_correct: Optional[bool] = None  # Within tolerance


@dataclass
class ModelPerformance:
    """Performance metrics for the model."""
    total_predictions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0  # correct/total
    mean_absolute_error: float = 0.0
    mean_squared_error: float = 0.0
    precision_by_category: Dict[str, float] = field(default_factory=dict)
    recall_by_category: Dict[str, float] = field(default_factory=dict)
    f1_by_category: Dict[str, float] = field(default_factory=dict)


class MLQualityPredictor:
    """Predicts code quality using machine learning techniques."""

    def __init__(self):
        """Initialize predictor."""
        self.training_data: List[Tuple[FeatureVector, float]] = []
        self.predictions: Dict[str, Prediction] = {}
        self.performance = ModelPerformance()
        self.feature_weights: Dict[str, float] = self._initialize_weights()

    def _initialize_weights(self) -> Dict[str, float]:
        """Initialize feature weights based on importance."""
        return {
            "cyclomatic_complexity": -0.15,  # Lower complexity is better
            "cognitive_complexity": -0.12,
            "lines_of_code": -0.08,
            "comment_ratio": 0.10,  # Higher ratio is better
            "test_coverage": 0.20,
            "documentation_score": 0.12,
            "dependency_count": -0.10,
            "incoming_dependencies": -0.05,
            "detected_patterns": 0.15,
            "detected_smells": -0.15,
            "security_score": 0.18,
            "performance_score": 0.12,
            "maintainability_score": 0.18,
        }

    def extract_features(self, symbol_data: Dict) -> FeatureVector:
        """Extract features from symbol data.

        Args:
            symbol_data: Dict with symbol analysis data

        Returns:
            FeatureVector
        """
        return FeatureVector(
            symbol_name=symbol_data.get("name", "unknown"),
            cyclomatic_complexity=symbol_data.get("cyclomatic_complexity", 1.0),
            cognitive_complexity=symbol_data.get("cognitive_complexity", 1.0),
            lines_of_code=symbol_data.get("lines_of_code", 10),
            comment_ratio=symbol_data.get("comment_ratio", 0.0),
            test_coverage=symbol_data.get("test_coverage", 0.0),
            documentation_score=symbol_data.get("documentation_score", 0.5),
            dependency_count=symbol_data.get("dependency_count", 0),
            incoming_dependencies=symbol_data.get("incoming_dependencies", 0),
            detected_patterns=symbol_data.get("detected_patterns", 0),
            detected_smells=symbol_data.get("detected_smells", 0),
            security_score=symbol_data.get("security_score", 0.7),
            performance_score=symbol_data.get("performance_score", 0.7),
            maintainability_score=symbol_data.get("maintainability_score", 0.7),
        )

    def normalize_features(self, features: FeatureVector) -> Dict[str, float]:
        """Normalize features to 0-1 range.

        Args:
            features: Feature vector to normalize

        Returns:
            Dict of normalized feature values
        """
        normalized = {}

        # Normalize complexity scores (lower is better, scale 1-50)
        normalized["cyclomatic_complexity"] = min(
            1.0, features.cyclomatic_complexity / 50.0
        )
        normalized["cognitive_complexity"] = min(
            1.0, features.cognitive_complexity / 50.0
        )

        # Normalize LOC (scale 1-1000)
        normalized["lines_of_code"] = min(1.0, features.lines_of_code / 1000.0)

        # Already normalized (0-1)
        normalized["comment_ratio"] = features.comment_ratio
        normalized["test_coverage"] = features.test_coverage
        normalized["documentation_score"] = features.documentation_score
        normalized["security_score"] = features.security_score
        normalized["performance_score"] = features.performance_score
        normalized["maintainability_score"] = features.maintainability_score

        # Normalize dependency counts (scale 0-20)
        normalized["dependency_count"] = min(1.0, features.dependency_count / 20.0)
        normalized["incoming_dependencies"] = min(
            1.0, features.incoming_dependencies / 20.0
        )

        # Normalize pattern/smell counts (scale 0-10)
        normalized["detected_patterns"] = min(1.0, features.detected_patterns / 10.0)
        normalized["detected_smells"] = min(1.0, features.detected_smells / 10.0)

        return normalized

    def predict(self, symbol_data: Dict) -> Prediction:
        """Predict quality for a symbol.

        Args:
            symbol_data: Dict with symbol analysis data

        Returns:
            Prediction with score and confidence
        """
        features = self.extract_features(symbol_data)
        normalized = self.normalize_features(features)

        # Calculate weighted score (0-1)
        score = 0.0  # Start from baseline
        total_weight = 0.0

        for feature_name, normalized_value in normalized.items():
            weight = self.feature_weights.get(feature_name, 0.0)
            total_weight += abs(weight)

            # Reverse negative weights (lower values should improve score)
            if weight < 0:
                score += (1.0 - normalized_value) * abs(weight)
            else:
                score += normalized_value * weight

        # Normalize by total weight to get 0-1 range
        if total_weight > 0:
            score = score / total_weight

        # Clamp to 0-1
        score = max(0.0, min(1.0, score))

        # Convert to 0-100 scale
        quality_score = score * 100.0

        # Determine category
        category = self._score_to_category(quality_score)

        # Calculate confidence based on feature consistency
        confidence = self._calculate_confidence(features, normalized, score)

        # Determine confidence level
        confidence_level = self._get_confidence_level(confidence)

        # Calculate feature importance for this prediction
        feature_importance = self._calculate_feature_importance(
            normalized, features
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            features, quality_score, confidence, feature_importance
        )

        prediction = Prediction(
            symbol_name=features.symbol_name,
            predicted_quality_score=quality_score,
            predicted_category=category,
            confidence=confidence,
            confidence_level=confidence_level,
            feature_importance=feature_importance,
            reasoning=reasoning,
        )

        self.predictions[features.symbol_name] = prediction
        return prediction

    def _score_to_category(self, score: float) -> str:
        """Convert numeric score to category.

        Args:
            score: Quality score 0-100

        Returns:
            Category string
        """
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 55:
            return "fair"
        elif score >= 40:
            return "poor"
        else:
            return "critical"

    def _calculate_confidence(
        self, features: FeatureVector, normalized: Dict[str, float], score: float
    ) -> float:
        """Calculate prediction confidence.

        Args:
            features: Feature vector
            normalized: Normalized features
            score: Calculated score

        Returns:
            Confidence 0-1
        """
        # Start with baseline confidence
        confidence = 0.65

        # Boost confidence if test coverage is very high
        if features.test_coverage > 0.85:
            confidence = min(1.0, confidence + 0.25)
        elif features.test_coverage > 0.7:
            confidence = min(1.0, confidence + 0.15)

        # Boost confidence if good metrics are consistent (many high values)
        high_values = sum(1 for v in normalized.values() if v > 0.75)
        confidence += (high_values * 0.02)  # 2% per high-quality metric

        # Reduce confidence for high complexity
        if features.cyclomatic_complexity > 30:
            confidence = max(0.4, confidence - 0.2)

        # Reduce confidence if too many conflicting signals
        low_values = sum(1 for v in normalized.values() if v < 0.3)
        if low_values > 4:
            confidence = max(0.4, confidence - 0.15)

        return max(0.3, min(1.0, confidence))

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Map confidence score to level.

        Args:
            confidence: Confidence 0-1

        Returns:
            ConfidenceLevel
        """
        if confidence > 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence > 0.8:
            return ConfidenceLevel.HIGH
        elif confidence > 0.65:
            return ConfidenceLevel.MEDIUM
        elif confidence > 0.5:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _calculate_feature_importance(
        self, normalized: Dict[str, float], features: FeatureVector
    ) -> Dict[str, float]:
        """Calculate importance of each feature for this prediction.

        Args:
            normalized: Normalized features
            features: Original features

        Returns:
            Dict of feature importance scores
        """
        importance = {}
        for feature_name, weight in self.feature_weights.items():
            if feature_name in normalized:
                # Importance is weight * how far from neutral (0.5)
                normalized_value = normalized[feature_name]
                deviation = abs(normalized_value - 0.5)
                importance[feature_name] = abs(weight) * deviation

        # Normalize importances to sum to 1.0
        total = sum(importance.values()) or 1.0
        return {k: v / total for k, v in importance.items()}

    def _generate_reasoning(
        self,
        features: FeatureVector,
        quality_score: float,
        confidence: float,
        feature_importance: Dict[str, float],
    ) -> List[str]:
        """Generate human-readable reasoning for prediction.

        Args:
            features: Feature vector
            quality_score: Predicted quality score
            confidence: Prediction confidence
            feature_importance: Feature importance scores

        Returns:
            List of reasoning statements
        """
        reasoning = []

        # Top positive factors
        positive_factors = sorted(
            [(k, v) for k, v in feature_importance.items() if self.feature_weights[k] > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:2]

        for feature_name, importance in positive_factors:
            if importance > 0.1:
                reasoning.append(
                    f"Positive: {feature_name.replace('_', ' ')} "
                    f"(importance: {importance:.2f})"
                )

        # Top negative factors
        negative_factors = sorted(
            [(k, v) for k, v in feature_importance.items() if self.feature_weights[k] < 0],
            key=lambda x: x[1],
            reverse=True,
        )[:2]

        for feature_name, importance in negative_factors:
            if importance > 0.1:
                reasoning.append(
                    f"Concern: {feature_name.replace('_', ' ')} "
                    f"(importance: {importance:.2f})"
                )

        # Confidence statement
        if confidence > 0.8:
            reasoning.append(f"High confidence prediction ({confidence:.1%})")
        elif confidence < 0.6:
            reasoning.append(f"Low confidence prediction ({confidence:.1%})")

        return reasoning

    def train_on_data(
        self, symbol_data_list: List[Dict], actual_scores: List[float]
    ) -> None:
        """Train model on historical data.

        Args:
            symbol_data_list: List of symbol data dicts
            actual_scores: List of actual quality scores (0-100)
        """
        for symbol_data, actual_score in zip(symbol_data_list, actual_scores):
            features = self.extract_features(symbol_data)
            # Normalize actual score to 0-1
            normalized_score = actual_score / 100.0
            self.training_data.append((features, normalized_score))

    def evaluate_predictions(
        self, actual_scores: Dict[str, float]
    ) -> ModelPerformance:
        """Evaluate model predictions against actual scores.

        Args:
            actual_scores: Dict of symbol_name -> actual_score (0-100)

        Returns:
            ModelPerformance metrics
        """
        performance = ModelPerformance()

        squared_errors = []
        category_metrics = {}

        for symbol_name, prediction in self.predictions.items():
            if symbol_name in actual_scores:
                actual_score = actual_scores[symbol_name]
                predicted_score = prediction.predicted_quality_score

                # Calculate errors
                error = actual_score - predicted_score
                abs_error = abs(error)
                squared_errors.append(error ** 2)

                # Check if within tolerance (5 points)
                is_correct = abs_error <= 5.0

                performance.total_predictions += 1
                if is_correct:
                    performance.correct_predictions += 1

                # Track by category
                actual_category = self._score_to_category(actual_score)
                if actual_category not in category_metrics:
                    category_metrics[actual_category] = {
                        "correct": 0,
                        "total": 0,
                    }
                category_metrics[actual_category]["total"] += 1
                if prediction.predicted_category == actual_category:
                    category_metrics[actual_category]["correct"] += 1

        # Calculate aggregate metrics
        if performance.total_predictions > 0:
            performance.accuracy = (
                performance.correct_predictions / performance.total_predictions
            )

        if squared_errors:
            performance.mean_squared_error = sum(squared_errors) / len(squared_errors)
            performance.mean_absolute_error = math.sqrt(
                performance.mean_squared_error
            )

        # Calculate per-category metrics
        for category, metrics in category_metrics.items():
            performance.precision_by_category[category] = (
                metrics["correct"] / metrics["total"]
                if metrics["total"] > 0
                else 0.0
            )
            performance.recall_by_category[category] = (
                metrics["correct"] / metrics["total"]
                if metrics["total"] > 0
                else 0.0
            )

        self.performance = performance
        return performance

    def predict_refactoring_impact(
        self, current_metrics: Dict, refactoring_changes: Dict
    ) -> Dict:
        """Predict quality improvement from refactoring.

        Args:
            current_metrics: Current symbol metrics
            refactoring_changes: Changes that would be made

        Returns:
            Dict with impact prediction
        """
        # Get current prediction
        current_prediction = self.predict(current_metrics)
        current_score = current_prediction.predicted_quality_score

        # Simulate refactored metrics
        refactored_metrics = current_metrics.copy()
        refactored_metrics.update(refactoring_changes)

        # Get refactored prediction
        refactored_prediction = self.predict(refactored_metrics)
        refactored_score = refactored_prediction.predicted_quality_score

        # Calculate impact
        score_improvement = refactored_score - current_score
        percent_improvement = (score_improvement / current_score) * 100 if current_score > 0 else 0

        return {
            "current_score": current_score,
            "predicted_score": refactored_score,
            "score_improvement": score_improvement,
            "percent_improvement": percent_improvement,
            "current_category": current_prediction.predicted_category,
            "predicted_category": refactored_prediction.predicted_category,
            "worth_refactoring": score_improvement > 2.0,  # At least 2 point improvement
        }

    def get_prediction_summary(self) -> Dict:
        """Get summary of all predictions.

        Returns:
            Summary dict
        """
        if not self.predictions:
            return {
                "total_predictions": 0,
                "average_score": 0.0,
                "score_distribution": {},
                "confidence_distribution": {},
            }

        scores = [p.predicted_quality_score for p in self.predictions.values()]
        confidences = [p.confidence for p in self.predictions.values()]

        score_dist = {}
        for pred in self.predictions.values():
            category = pred.predicted_category
            score_dist[category] = score_dist.get(category, 0) + 1

        confidence_dist = {}
        for pred in self.predictions.values():
            level = pred.confidence_level.value
            confidence_dist[level] = confidence_dist.get(level, 0) + 1

        return {
            "total_predictions": len(self.predictions),
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 100.0,
            "average_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "score_distribution": score_dist,
            "confidence_distribution": confidence_dist,
            "model_accuracy": self.performance.accuracy,
            "mean_absolute_error": self.performance.mean_absolute_error,
        }
