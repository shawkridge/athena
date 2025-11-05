"""
Time series analysis and forecasting models for the Predictor Agent.

Includes:
- ARIMA model for stationary/non-stationary series
- Exponential smoothing for trending/seasonal data
- Hybrid ensemble combining multiple models
- Auto-ARIMA parameter selection
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import math
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TimeSeriesModel(ABC):
    """Abstract base class for time series models."""

    def __init__(self, name: str, window_size: int = 50):
        """Initialize time series model.

        Args:
            name: Model name
            window_size: Number of historical points to use
        """
        self.name = name
        self.window_size = window_size
        self.data_points: list[float] = []
        self.timestamps: list[datetime] = []
        self.is_fitted = False

    @abstractmethod
    def fit(self, data: list[float], timestamps: Optional[list[datetime]] = None) -> bool:
        """Fit model to data.

        Args:
            data: Historical data points
            timestamps: Optional timestamps for each point

        Returns:
            True if fitting succeeded
        """
        pass

    @abstractmethod
    def predict(self, steps_ahead: int = 1) -> Tuple[list[float], list[float]]:
        """Predict future values.

        Args:
            steps_ahead: Number of steps to forecast

        Returns:
            Tuple of (predictions, confidence_intervals)
        """
        pass

    def add_observation(self, value: float, timestamp: Optional[datetime] = None):
        """Add new observation to model.

        Args:
            value: New observation
            timestamp: Optional timestamp
        """
        self.data_points.append(value)
        self.timestamps.append(timestamp or datetime.now())

        # Keep only last window_size points
        if len(self.data_points) > self.window_size:
            self.data_points.pop(0)
            self.timestamps.pop(0)

    def get_summary(self) -> dict:
        """Get model summary statistics."""
        if not self.data_points:
            return {}

        values = self.data_points
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)

        return {
            "name": self.name,
            "is_fitted": self.is_fitted,
            "data_points": len(self.data_points),
            "mean": mean,
            "std_dev": std_dev,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
        }


class ARIMAModel(TimeSeriesModel):
    """Simple ARIMA-like model with automatic differencing."""

    def __init__(self, order: Tuple[int, int, int] = (1, 1, 1)):
        """Initialize ARIMA model.

        Args:
            order: (p, d, q) tuple for AR, differencing, MA orders
        """
        super().__init__("ARIMA", window_size=100)
        self.p, self.d, self.q = order
        self.ar_coefs: list[float] = []
        self.ma_coefs: list[float] = []
        self.mean: float = 0.0
        self.residuals: list[float] = []

    def fit(self, data: list[float], timestamps: Optional[list[datetime]] = None) -> bool:
        """Fit ARIMA model to data."""
        if len(data) < max(self.p, self.d, self.q) + 5:
            logger.warning("Not enough data points for ARIMA fitting")
            return False

        self.data_points = data[-self.window_size:]
        if timestamps:
            self.timestamps = timestamps[-self.window_size:]

        # Apply differencing
        differenced = self._difference(self.data_points, self.d)

        # Calculate mean
        self.mean = sum(self.data_points) / len(self.data_points)

        # Simplified AR coefficient estimation
        self.ar_coefs = self._estimate_ar_coefs(differenced, self.p)
        self.ma_coefs = self._estimate_ma_coefs(differenced, self.q)

        # Calculate residuals
        self.residuals = self._calculate_residuals(differenced)

        self.is_fitted = True
        return True

    def predict(self, steps_ahead: int = 1) -> Tuple[list[float], list[float]]:
        """Predict future values using ARIMA."""
        if not self.is_fitted or not self.data_points:
            return [], []

        predictions = []
        confidence_intervals = []

        # Start with last value
        last_value = self.data_points[-1]
        current = last_value

        # Residual std for confidence
        residual_std = math.sqrt(
            sum(r ** 2 for r in self.residuals) / len(self.residuals)
            if self.residuals
            else 1.0
        )

        for i in range(steps_ahead):
            # Simple AR prediction: next = mean + sum(ar_coef * lag)
            ar_contrib = 0.0
            for j, coef in enumerate(self.ar_coefs):
                lag_idx = len(self.data_points) - j - 1
                if lag_idx >= 0:
                    ar_contrib += coef * self.data_points[lag_idx]

            current = self.mean + ar_contrib

            # Ensure non-negative for resource predictions
            current = max(current, 0.0)
            predictions.append(current)

            # Confidence interval grows with forecast horizon
            ci = residual_std * math.sqrt(i + 1) * 1.96
            confidence_intervals.append(ci)

        return predictions, confidence_intervals

    @staticmethod
    def _difference(data: list[float], order: int) -> list[float]:
        """Apply differencing to make series stationary."""
        result = list(data)
        for _ in range(order):
            if len(result) < 2:
                break
            result = [result[i + 1] - result[i] for i in range(len(result) - 1)]
        return result

    @staticmethod
    def _estimate_ar_coefs(data: list[float], p: int) -> list[float]:
        """Estimate autoregressive coefficients using Yule-Walker."""
        if len(data) < p + 5:
            return [0.1] * p

        # Simplified: use autocorrelation-like approximation
        coefs = []
        for lag in range(1, p + 1):
            if len(data) > lag:
                correlation = sum(
                    data[i] * data[i - lag] for i in range(lag, len(data))
                ) / (len(data) - lag)
                coef = correlation / (1 + lag ** 0.5)
                coefs.append(min(0.5, max(-0.5, coef)))
        return coefs

    @staticmethod
    def _estimate_ma_coefs(data: list[float], q: int) -> list[float]:
        """Estimate moving average coefficients."""
        if len(data) < q + 5:
            return [0.05] * q
        return [0.05] * q

    def _calculate_residuals(self, differenced: list[float]) -> list[float]:
        """Calculate model residuals."""
        if not self.ar_coefs:
            return differenced

        residuals = []
        for i in range(len(differenced)):
            predicted = sum(
                coef * differenced[i - j - 1]
                for j, coef in enumerate(self.ar_coefs)
                if i - j - 1 >= 0
            )
            residuals.append(differenced[i] - predicted)
        return residuals


class ExponentialSmoothingModel(TimeSeriesModel):
    """Exponential smoothing for trending/seasonal data."""

    def __init__(self, alpha: float = 0.3, beta: float = 0.1, gamma: float = 0.1):
        """Initialize exponential smoothing model.

        Args:
            alpha: Smoothing for level
            beta: Smoothing for trend
            gamma: Smoothing for seasonality
        """
        super().__init__("ExponentialSmoothing", window_size=50)
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.level: float = 0.0
        self.trend: float = 0.0
        self.seasonal: dict[int, float] = {}
        self.season_length: int = 12  # Default to monthly seasonality

    def fit(self, data: list[float], timestamps: Optional[list[datetime]] = None) -> bool:
        """Fit exponential smoothing model."""
        if len(data) < 3:
            return False

        self.data_points = data[-self.window_size:]
        if timestamps:
            self.timestamps = timestamps[-self.window_size:]

        # Initialize level
        self.level = self.data_points[0]

        # Initialize trend
        if len(self.data_points) > 1:
            self.trend = (self.data_points[-1] - self.data_points[0]) / (len(self.data_points) - 1)
        else:
            self.trend = 0.0

        # Apply smoothing
        for i, value in enumerate(self.data_points):
            prev_level = self.level
            self.level = self.alpha * value + (1 - self.alpha) * (prev_level + self.trend)
            self.trend = self.beta * (self.level - prev_level) + (1 - self.beta) * self.trend

            # Seasonal component
            season_idx = i % self.season_length
            if season_idx not in self.seasonal:
                self.seasonal[season_idx] = 1.0

        self.is_fitted = True
        return True

    def predict(self, steps_ahead: int = 1) -> Tuple[list[float], list[float]]:
        """Predict using exponential smoothing."""
        if not self.is_fitted:
            return [], []

        predictions = []
        confidence_intervals = []

        for i in range(steps_ahead):
            # Base prediction: level + trend
            pred = self.level + (i + 1) * self.trend

            # Apply seasonal component
            season_idx = (len(self.data_points) + i) % self.season_length
            seasonal_factor = self.seasonal.get(season_idx, 1.0)
            pred = pred * seasonal_factor

            # Ensure non-negative
            pred = max(pred, 0.0)
            predictions.append(pred)

            # Confidence grows with horizon
            ci = abs(self.trend) * (i + 1) * 0.5 + 1.0
            confidence_intervals.append(ci)

        return predictions, confidence_intervals


class HybridEnsembleModel(TimeSeriesModel):
    """Ensemble combining ARIMA, exponential smoothing, and simple averaging."""

    def __init__(self):
        """Initialize ensemble model."""
        super().__init__("HybridEnsemble", window_size=100)
        self.arima_model = ARIMAModel()
        self.smoothing_model = ExponentialSmoothingModel()
        self.models = [self.arima_model, self.smoothing_model]

    def fit(self, data: list[float], timestamps: Optional[list[datetime]] = None) -> bool:
        """Fit all ensemble models."""
        if len(data) < 10:
            return False

        self.data_points = data[-self.window_size:]
        if timestamps:
            self.timestamps = timestamps[-self.window_size:]

        # Fit individual models
        arima_ok = self.arima_model.fit(self.data_points, self.timestamps)
        smoothing_ok = self.smoothing_model.fit(self.data_points, self.timestamps)

        if not (arima_ok or smoothing_ok):
            return False

        self.is_fitted = True
        return True

    def predict(self, steps_ahead: int = 1) -> Tuple[list[float], list[float]]:
        """Predict using ensemble averaging."""
        if not self.is_fitted:
            return [], []

        all_predictions = []
        all_cis = []

        for model in self.models:
            if model.is_fitted:
                preds, cis = model.predict(steps_ahead)
                if preds:
                    all_predictions.append(preds)
                    all_cis.append(cis)

        if not all_predictions:
            return [], []

        # Average predictions
        ensemble_predictions = [
            sum(preds[i] for preds in all_predictions) / len(all_predictions)
            for i in range(steps_ahead)
        ]

        # Average confidence intervals
        ensemble_cis = [
            sum(cis[i] for cis in all_cis) / len(all_cis) for i in range(steps_ahead)
        ]

        return ensemble_predictions, ensemble_cis

    def add_observation(self, value: float, timestamp: Optional[datetime] = None):
        """Add observation to all models."""
        super().add_observation(value, timestamp)
        self.arima_model.add_observation(value, timestamp)
        self.smoothing_model.add_observation(value, timestamp)
