"""
Monitor Agent

Tracks execution health and detects anomalies in real-time.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .base import AgentType, BaseAgent


class ExecutionMetric(BaseModel):
    """Single execution metric measurement"""
    timestamp: int
    metric_type: str  # duration, resource, error, quality
    value: float
    threshold: Optional[float] = None
    status: str = "normal"  # normal, warning, critical


class Anomaly(BaseModel):
    """Detected anomaly in execution"""
    id: str
    type: str  # duration, resource, error_rate, quality
    severity: str  # low, medium, high, critical
    message: str
    value: float
    baseline: float
    deviation_percent: float
    timestamp: int


class MonitorAgent(BaseAgent):
    """
    Monitor Agent: Tracks execution health and detects anomalies.

    Responsibilities:
    - Monitor task execution in real-time
    - Detect deviations from plan
    - Track resource usage and bottlenecks
    - Alert on anomalies
    - Maintain execution metrics
    """

    def __init__(self, db_path: str):
        """
        Initialize Monitor agent.

        Args:
            db_path: Path to memory database
        """
        super().__init__(AgentType.MONITOR, db_path)
        self.execution_baselines: Dict[int, Dict[str, Any]] = {}
        self.execution_metrics: Dict[int, List[ExecutionMetric]] = {}
        self.execution_anomalies: Dict[int, List[Anomaly]] = {}

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming messages.

        Args:
            message: Message payload

        Returns:
            Response payload
        """
        try:
            if message.get("action") == "start_monitoring":
                return await self.start_monitoring(
                    message.get("execution_id"),
                    message.get("plan", {})
                )
            elif message.get("action") == "record_metric":
                return await self.record_metric(
                    message.get("execution_id"),
                    message.get("metric", {})
                )
            elif message.get("action") == "get_metrics":
                return await self.get_execution_metrics(
                    message.get("execution_id")
                )
            elif message.get("action") == "get_health":
                return await self.get_health_score(
                    message.get("execution_id")
                )
            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {message.get('action')}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make monitoring decision based on metrics.

        Args:
            context: Decision context

        Returns:
            Decision output with confidence score
        """
        execution_id = context.get("execution_id")
        return await self.get_health_score(execution_id)

    async def start_monitoring(self, execution_id: int,
                              plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Begin monitoring an execution.

        Args:
            execution_id: ID of execution to monitor
            plan: Execution plan for baseline

        Returns:
            Monitoring initialization response
        """
        self.execution_baselines[execution_id] = {
            "plan": plan,
            "estimated_duration": plan.get("estimated_total_duration_ms", 0),
            "estimated_resources": plan.get("estimated_total_resources", {}),
            "start_time": datetime.now(),
            "status": "running"
        }

        self.execution_metrics[execution_id] = []
        self.execution_anomalies[execution_id] = []

        return {
            "status": "success",
            "execution_id": execution_id,
            "message": "Monitoring started"
        }

    async def record_metric(self, execution_id: int,
                           metric: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record execution metric.

        Args:
            execution_id: ID of execution
            metric: Metric data (duration_ms, resources, errors, quality_score)

        Returns:
            Response with anomaly detections
        """
        if execution_id not in self.execution_baselines:
            return {
                "status": "error",
                "error": "Unknown execution"
            }

        baseline = self.execution_baselines[execution_id]

        # Parse metric - store raw value for anomaly detection
        metric_value = metric.get("value", 0.0)
        metric_type = metric.get("type", "resource")

        # For resource metrics with dict values, store as JSON
        if isinstance(metric_value, dict):
            exec_metric = ExecutionMetric(
                timestamp=int(datetime.now().timestamp()),
                metric_type=metric_type,
                value=1.0  # Store scalar for Pydantic, keep dict in memory
            )
            # Store original dict for anomaly detection
            exec_metric._raw_value = metric_value
        else:
            exec_metric = ExecutionMetric(
                timestamp=int(datetime.now().timestamp()),
                metric_type=metric_type,
                value=float(metric_value)
            )

        # Initialize metrics list if needed
        if execution_id not in self.execution_metrics:
            self.execution_metrics[execution_id] = []

        self.execution_metrics[execution_id].append(exec_metric)

        # Detect anomalies - pass original metric
        anomalies = await self._detect_anomalies(execution_id, metric)

        # Initialize anomalies list if needed
        if execution_id not in self.execution_anomalies:
            self.execution_anomalies[execution_id] = []

        if anomalies:
            self.execution_anomalies[execution_id].extend(anomalies)

            # Record decision metrics
            self.record_decision(
                success=len(anomalies) == 0,
                decision_time_ms=5,
                confidence=0.9
            )

            return {
                "status": "success",
                "anomalies": [a.dict() for a in anomalies],
                "anomaly_count": len(anomalies)
            }

        return {
            "status": "success",
            "anomalies": [],
            "message": "Metrics recorded, no anomalies"
        }

    async def get_execution_metrics(self, execution_id: int) -> Dict[str, Any]:
        """
        Get all metrics for execution.

        Args:
            execution_id: ID of execution

        Returns:
            Metrics data
        """
        if execution_id not in self.execution_metrics:
            return {
                "status": "error",
                "error": "Unknown execution"
            }

        metrics = self.execution_metrics[execution_id]

        return {
            "status": "success",
            "execution_id": execution_id,
            "metrics": [m.dict() for m in metrics],
            "metric_count": len(metrics)
        }

    async def get_health_score(self, execution_id: int) -> Dict[str, Any]:
        """
        Calculate health score for execution.

        Args:
            execution_id: ID of execution

        Returns:
            Health metrics and score
        """
        if execution_id not in self.execution_baselines:
            return {
                "status": "error",
                "error": "Unknown execution"
            }

        baseline = self.execution_baselines[execution_id]
        metrics = self.execution_metrics.get(execution_id, [])
        anomalies = self.execution_anomalies.get(execution_id, [])

        # Calculate health components
        duration_health = await self._calculate_duration_health(execution_id)
        resource_health = await self._calculate_resource_health(execution_id)
        anomaly_health = 1.0 - min(len(anomalies) * 0.1, 1.0)

        # Weighted health score
        health_score = (
            0.4 * duration_health +
            0.35 * resource_health +
            0.25 * anomaly_health
        )

        # Determine status
        if health_score >= 0.75:
            status = "healthy"
        elif health_score >= 0.50:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": "success",
            "execution_id": execution_id,
            "health_score": max(0.0, min(1.0, health_score)),
            "health_status": status,
            "components": {
                "duration_health": duration_health,
                "resource_health": resource_health,
                "anomaly_health": anomaly_health
            },
            "metric_count": len(metrics),
            "anomaly_count": len(anomalies),
            "elapsed_seconds": (datetime.now() - baseline["start_time"]).total_seconds()
        }

    async def _detect_anomalies(self, execution_id: int,
                               metric: Dict[str, Any]) -> List[Anomaly]:
        """
        Detect anomalies in metric.

        Args:
            execution_id: ID of execution
            metric: New metric to analyze (raw dict)

        Returns:
            List of detected anomalies
        """
        anomalies = []
        baseline = self.execution_baselines.get(execution_id, {})

        metric_type = metric.get("type", "")
        metric_value = metric.get("value", 0.0)
        timestamp = int(datetime.now().timestamp())

        if metric_type == "duration":
            # Duration anomaly: if 50% over estimate
            estimated = baseline.get("estimated_duration", 0)
            elapsed = (datetime.now() - baseline.get("start_time", datetime.now())).total_seconds() * 1000

            if elapsed > estimated * 1.5:
                anomalies.append(Anomaly(
                    id=f"duration_overrun_{execution_id}",
                    type="duration",
                    severity="high",
                    message=f"Execution taking 50% longer than estimated",
                    value=elapsed,
                    baseline=estimated,
                    deviation_percent=(elapsed - estimated) / max(1, estimated) * 100,
                    timestamp=timestamp
                ))

        elif metric_type == "resource":
            # Resource anomaly: if 50% over estimate
            estimated_resources = baseline.get("estimated_resources", {})

            if isinstance(metric_value, dict):
                for resource_type, actual_usage in metric_value.items():
                    estimated_usage = estimated_resources.get(resource_type, 0)

                    if actual_usage > estimated_usage * 1.5:
                        anomalies.append(Anomaly(
                            id=f"resource_spike_{execution_id}_{resource_type}",
                            type="resource",
                            severity="medium",
                            message=f"{resource_type} usage 50% higher than estimated",
                            value=actual_usage,
                            baseline=estimated_usage,
                            deviation_percent=(actual_usage - estimated_usage) / max(1, estimated_usage) * 100,
                            timestamp=timestamp
                        ))

        elif metric_type == "error":
            # Error anomaly
            if metric_value > 0:
                anomalies.append(Anomaly(
                    id=f"error_detected_{execution_id}",
                    type="error",
                    severity="critical" if metric_value > 5 else "high",
                    message=f"Error occurred during execution",
                    value=metric_value,
                    baseline=0.0,
                    deviation_percent=100.0,
                    timestamp=timestamp
                ))

        return anomalies

    async def _calculate_duration_health(self, execution_id: int) -> float:
        """
        Calculate health based on duration vs estimate.

        Args:
            execution_id: ID of execution

        Returns:
            Health score (0.0-1.0)
        """
        baseline = self.execution_baselines.get(execution_id, {})
        estimated = baseline.get("estimated_duration", 1)
        elapsed = (datetime.now() - baseline.get("start_time", datetime.now())).total_seconds() * 1000

        # Perfect: on time (100%)
        # Poor: 2x over (0%)
        health = 1.0 - min(elapsed / (estimated * 2), 1.0)
        return max(0.0, health)

    async def _calculate_resource_health(self, execution_id: int) -> float:
        """
        Calculate health based on resource usage.

        Args:
            execution_id: ID of execution

        Returns:
            Health score (0.0-1.0)
        """
        # If no anomalies, assume good resource usage
        anomalies = self.execution_anomalies.get(execution_id, [])
        resource_anomalies = [a for a in anomalies if a.type == "resource"]

        if not resource_anomalies:
            return 1.0

        # Penalize for each resource anomaly
        health = 1.0 - (len(resource_anomalies) * 0.3)
        return max(0.0, health)
