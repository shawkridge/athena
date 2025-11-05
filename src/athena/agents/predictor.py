"""
Predictor Agent - Autonomous prediction and forecasting for task execution.

Completes the autonomous feedback loop:
Plan → Execute → Monitor → Learn → Predict → Plan (improved)

Capabilities:
- Duration forecasting with confidence intervals
- Resource requirement prediction
- Bottleneck detection and mitigation
- Success probability estimation
- Pattern-based learning
"""

import logging
from typing import Optional
from datetime import datetime
import uuid

from .base import BaseAgent, AgentMetrics
from .message_bus import Message, MessageType
from .predictor_models import (
    PredictionResult,
    DurationPrediction,
    RiskLevel,
    ResourceForecast,
    PredictionAccuracy,
    ConfidenceInterval,
)
from .temporal_reasoner import TemporalReasoner
from .bottleneck_detector import BottleneckDetector
from .timeseries import HybridEnsembleModel

logger = logging.getLogger(__name__)


class PredictorAgent(BaseAgent):
    """Predicts future task execution requirements and bottlenecks.

    Uses Monitor and Learner agent data to:
    - Forecast task durations with confidence intervals
    - Predict resource requirements
    - Detect and alert on bottlenecks
    - Estimate success probabilities
    - Generate mitigation recommendations
    """

    def __init__(self, db_path: str = "/home/user/.athena/memory.db"):
        """Initialize Predictor Agent.

        Args:
            db_path: Path to memory database
        """
        from .base import AgentType

        super().__init__(AgentType.PREDICTOR, db_path)

        # Core prediction components
        self.temporal_reasoner = TemporalReasoner(min_pattern_strength=0.6)
        self.bottleneck_detector = BottleneckDetector(
            saturation_threshold=0.85, critical_threshold=0.95
        )

        # Time series models for each metric
        self.time_series_models: dict[str, HybridEnsembleModel] = {}

        # Prediction tracking
        self.predictions: dict[str, PredictionResult] = {}
        self.prediction_accuracy_records: list[PredictionAccuracy] = []

        logger.info(f"Initialized Predictor Agent")

    async def process_message(self, message_dict: dict) -> dict:
        """Process incoming message (abstract method implementation).

        Args:
            message_dict: Message dictionary payload

        Returns:
            Response dictionary
        """
        try:
            action = message_dict.get("action")
            if action == "predict_task":
                result = await self.predict_task(
                    task_id=message_dict.get("task_id"),
                    task_type=message_dict.get("task_type", "unknown"),
                )
                return {"status": "success", "prediction": result.to_dict()}
            elif action == "detect_bottlenecks":
                bottlenecks = self.bottleneck_detector.detect_bottlenecks()
                return {
                    "status": "success",
                    "bottleneck_count": len(bottlenecks),
                    "alerts": [b.to_dict() for b in bottlenecks],
                }
            elif action == "record_metrics":
                await self.record_execution_metrics(
                    task_id=message_dict.get("task_id", "unknown"),
                    actual_duration=message_dict.get("actual_duration", 0.0),
                    resource_usage=message_dict.get("resource_usage", {}),
                )
                return {"status": "recorded"}
            return {"status": "unknown_action"}
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.metrics.errors_encountered += 1
            return {"status": "error", "error": str(e)}

    async def make_decision(self, context: dict) -> dict:
        """Make autonomous decision (abstract method implementation).

        Args:
            context: Contextual information for decision making

        Returns:
            Decision dictionary
        """
        # Predictor's autonomous decision: analyze current state and recommend actions
        return {
            "action": "analyze_patterns",
            "status": "analyzing",
            "metrics_count": len(self.temporal_reasoner.metric_history),
            "predictions_made": len(self.predictions),
            "bottlenecks_detected": len(self.bottleneck_detector.active_alerts),
        }

    async def predict_task(self, task_id: Optional[int], task_type: str, **kwargs) -> PredictionResult:
        """Predict execution requirements for a task.

        Args:
            task_id: Task identifier
            task_type: Type/category of task
            **kwargs: Additional task parameters

        Returns:
            PredictionResult with forecasts and recommendations
        """
        self.metrics.decisions_made += 1

        try:
            # Create base prediction result
            prediction_id = str(uuid.uuid4())
            prediction = PredictionResult(
                task_id=task_id,
                prediction_id=prediction_id,
                success_probability=0.8,
                confidence_score=0.75,
                overall_risk_level=RiskLevel.LOW,
            )

            # 1. Predict duration
            duration_pred = self._predict_duration(task_type)
            prediction.duration_prediction = duration_pred

            # 2. Predict resources
            resource_forecasts = self._predict_resources(task_type)
            prediction.resource_forecasts = resource_forecasts

            # 3. Detect bottlenecks
            bottlenecks = self.bottleneck_detector.detect_bottlenecks()
            prediction.bottleneck_alerts = bottlenecks

            # 4. Analyze temporal patterns
            patterns = self._analyze_patterns()
            prediction.temporal_patterns = patterns

            # 5. Generate recommendations
            recommendation_data = self._generate_recommendations(
                duration_pred, resource_forecasts, bottlenecks, patterns
            )
            prediction.recommendations = recommendation_data.get("recommendations", [])
            prediction.critical_constraints = recommendation_data.get("constraints", [])

            # 6. Calculate overall risk and success probability
            risk_and_prob = self._calculate_risk_and_probability(
                duration_pred, resource_forecasts, bottlenecks
            )
            prediction.overall_risk_level = risk_and_prob["risk_level"]
            prediction.success_probability = risk_and_prob["success_probability"]
            prediction.confidence_score = risk_and_prob["confidence"]

            # Store prediction
            self.predictions[prediction_id] = prediction

            # Record metrics
            self.metrics.decisions_successful += 1
            self.metrics.average_decision_time_ms = 200.0

            logger.info(f"Predicted task {task_type} with confidence {prediction.confidence_score:.2f}")

            return prediction

        except Exception as e:
            logger.error(f"Error predicting task: {e}")
            self.metrics.errors_encountered += 1
            raise

    async def record_execution_metrics(
        self, task_id: str, actual_duration: float, resource_usage: dict[str, float]
    ):
        """Record actual execution metrics for accuracy tracking.

        Args:
            task_id: Task identifier
            actual_duration: Actual duration in seconds
            resource_usage: Dict of {resource_name: usage_value}
        """
        # Update temporal reasoner
        self.temporal_reasoner.add_metric("duration_seconds", actual_duration)
        for resource_name, usage in resource_usage.items():
            self.temporal_reasoner.add_metric(resource_name, usage)

    def verify_prediction(
        self, prediction_id: str, actual_duration: float, actual_resources: dict[str, float]
    ) -> PredictionAccuracy:
        """Verify prediction accuracy after execution.

        Args:
            prediction_id: ID of original prediction
            actual_duration: Actual duration in seconds
            actual_resources: Dict of {resource: value}

        Returns:
            PredictionAccuracy record
        """
        if prediction_id not in self.predictions:
            logger.warning(f"Unknown prediction ID: {prediction_id}")
            return None

        prediction = self.predictions[prediction_id]

        # Calculate accuracy
        if prediction.duration_prediction:
            pred_ci = prediction.duration_prediction.forecasted_duration
            error_percent = (
                (actual_duration - pred_ci.point_estimate) / pred_ci.point_estimate * 100
                if pred_ci.point_estimate > 0
                else 0
            )

            # Check if actual fell in confidence interval
            duration_in_interval = (
                pred_ci.lower_bound <= actual_duration <= pred_ci.upper_bound
            )
        else:
            error_percent = 0
            duration_in_interval = False

        # Create accuracy record
        accuracy = PredictionAccuracy(
            prediction_id=prediction_id,
            actual_duration=actual_duration,
            predicted_duration=prediction.duration_prediction.forecasted_duration
            if prediction.duration_prediction
            else ConfidenceInterval(lower_bound=0, point_estimate=0, upper_bound=0),
            duration_error_percent=error_percent,
            actual_resources=actual_resources,
            duration_in_interval=duration_in_interval,
        )

        self.prediction_accuracy_records.append(accuracy)

        # Update metrics
        self.metrics.decisions_successful += 1

        logger.info(
            f"Prediction accuracy for {prediction_id}: "
            f"{error_percent:.1f}% error, "
            f"CI coverage: {duration_in_interval}"
        )

        return accuracy

    def _predict_duration(self, task_type: str) -> Optional[DurationPrediction]:
        """Predict task duration based on historical patterns.

        Args:
            task_type: Type of task

        Returns:
            DurationPrediction or None
        """
        metric_name = "duration_seconds"

        # Get time series model
        if metric_name not in self.time_series_models:
            self.time_series_models[metric_name] = HybridEnsembleModel()

        model = self.time_series_models[metric_name]

        # Get historical data
        if metric_name in self.temporal_reasoner.metric_history:
            data = [v for v, _ in self.temporal_reasoner.metric_history[metric_name]]

            if len(data) >= 5:
                model.fit(data)
                predictions, cis = model.predict(steps_ahead=1)

                if predictions:
                    pred_val = predictions[0]
                    ci_val = cis[0] if cis else pred_val * 0.2

                    # Find similar tasks
                    similar_count = len(
                        [
                            t
                            for t, _ in self.temporal_reasoner.find_similar_tasks(
                                {"duration": pred_val}
                            )
                        ]
                    )

                    return DurationPrediction(
                        task_type=task_type,
                        historical_average=sum(data) / len(data),
                        historical_median=sorted(data)[len(data) // 2],
                        forecasted_duration=ConfidenceInterval(
                            lower_bound=max(0.0, pred_val - ci_val),
                            point_estimate=pred_val,
                            upper_bound=pred_val + ci_val,
                        ),
                        similar_tasks=similar_count,
                        pattern_match_score=0.8 if similar_count > 0 else 0.5,
                    )

        # Default prediction if no history
        return DurationPrediction(
            task_type=task_type,
            historical_average=300.0,
            historical_median=300.0,
            forecasted_duration=ConfidenceInterval(
                lower_bound=200.0, point_estimate=300.0, upper_bound=400.0
            ),
            similar_tasks=0,
            pattern_match_score=0.3,
        )

    def _predict_resources(self, task_type: str) -> dict:
        """Predict resource requirements.

        Args:
            task_type: Type of task

        Returns:
            Dict of ResourceType -> ResourceForecast
        """
        forecasts = {}

        # Get forecasts for each resource type
        from .predictor_models import ResourceType

        for resource_type in ResourceType:
            forecast = self.bottleneck_detector.get_resource_forecast(resource_type)
            forecasts[resource_type] = forecast

        return forecasts

    def _analyze_patterns(self) -> list:
        """Analyze temporal patterns in metrics.

        Returns:
            List of detected patterns
        """
        patterns = []

        for metric_name in ["duration_seconds", "cpu_percent", "memory_mb"]:
            metric_patterns = self.temporal_reasoner.analyze_patterns(metric_name)
            patterns.extend(metric_patterns)

        return patterns

    def _generate_recommendations(
        self, duration_pred, resource_forecasts, bottlenecks, patterns
    ) -> dict:
        """Generate actionable recommendations.

        Args:
            duration_pred: Duration prediction
            resource_forecasts: Resource forecasts
            bottlenecks: Detected bottlenecks
            patterns: Temporal patterns

        Returns:
            Dict with recommendations and constraints
        """
        recommendations = []
        constraints = []

        # Recommendations from bottlenecks
        for bottleneck in bottlenecks:
            for mitigation in bottleneck.mitigation_options:
                recommendations.append(f"Mitigate {bottleneck.resource_type.value}: {mitigation}")

            if bottleneck.severity == RiskLevel.CRITICAL:
                constraints.append(
                    f"CRITICAL: {bottleneck.resource_type.value} will saturate in "
                    f"{bottleneck.predicted_saturation_time:.1f} hours"
                )

        # Recommendations from patterns
        for pattern in patterns[:2]:  # Top 2 patterns
            recommendations.append(f"Observed {pattern.pattern_type.value} pattern: {pattern.explanation}")

        # Duration-based recommendations
        if duration_pred and duration_pred.forecasted_duration:
            if duration_pred.forecasted_duration.upper_bound > 3600:
                recommendations.append("Long-running task detected - monitor for timeouts")

        return {"recommendations": recommendations, "constraints": constraints}

    def _calculate_risk_and_probability(self, duration_pred, resource_forecasts, bottlenecks) -> dict:
        """Calculate overall risk level and success probability.

        Args:
            duration_pred: Duration prediction
            resource_forecasts: Resource forecasts
            bottlenecks: Detected bottlenecks

        Returns:
            Dict with risk_level, success_probability, and confidence
        """
        # Base success probability
        success_prob = 0.85

        # Reduce for resource constraints
        if resource_forecasts:
            from .predictor_models import ResourceType

            for resource_type in ResourceType:
                if resource_type in resource_forecasts:
                    forecast = resource_forecasts[resource_type]
                    if forecast.is_constrained:
                        success_prob *= 0.9

        # Reduce for critical bottlenecks
        critical_count = sum(1 for b in bottlenecks if b.severity == RiskLevel.CRITICAL)
        success_prob *= (0.95 ** critical_count)

        # Determine risk level
        if success_prob >= 0.9:
            risk_level = RiskLevel.LOW
        elif success_prob >= 0.75:
            risk_level = RiskLevel.MEDIUM
        elif success_prob >= 0.5:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL

        # Confidence based on data availability
        confidence = 0.7 if len(self.temporal_reasoner.metric_history) > 0 else 0.5

        return {
            "risk_level": risk_level,
            "success_probability": max(0.0, min(1.0, success_prob)),
            "confidence": confidence,
        }

    async def _handle_predict_task(self, message: Message) -> dict:
        """Handle predict_task request."""
        content = message.content
        result = await self.predict_task(
            task_id=content.get("task_id"),
            task_type=content.get("task_type", "unknown"),
        )
        return {"status": "success", "prediction": result.to_dict()}

    async def _handle_detect_bottlenecks(self, message: Message) -> dict:
        """Handle detect_bottlenecks request."""
        bottlenecks = self.bottleneck_detector.detect_bottlenecks()
        return {
            "status": "success",
            "bottleneck_count": len(bottlenecks),
            "alerts": [b.to_dict() for b in bottlenecks],
        }

    async def _handle_record_metrics(self, message: Message):
        """Handle record_metrics notification."""
        content = message.content
        await self.record_execution_metrics(
            task_id=content.get("task_id", "unknown"),
            actual_duration=content.get("actual_duration", 0.0),
            resource_usage=content.get("resource_usage", {}),
        )

    async def _handle_notification(self, message: Message):
        """Handle other notifications."""
        if message.sender == "monitor":
            # Receive execution metrics from Monitor
            await self._handle_record_metrics(message)
        elif message.sender == "learner":
            # Receive improvement patterns from Learner
            logger.debug(f"Received learning update from {message.sender}")

    def get_status(self) -> dict:
        """Get predictor agent status."""
        return {
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "predictions_made": len(self.predictions),
            "accuracy_records": len(self.prediction_accuracy_records),
            "temporal_metrics": len(self.temporal_reasoner.metric_history),
            "active_alerts": len(self.bottleneck_detector.active_alerts),
            "decisions_made": self.metrics.decisions_made,
            "errors": self.metrics.errors_encountered,
        }
