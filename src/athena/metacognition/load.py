"""Cognitive load monitoring (7±2 working memory capacity)."""

from typing import Any, Optional, Dict
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import time
from collections import deque


class SaturationLevel(Enum):
    """Cognitive load saturation levels."""
    IDLE = "idle"              # < 20% capacity
    LIGHT = "light"            # 20-40% capacity
    MODERATE = "moderate"      # 40-60% capacity
    HEAVY = "heavy"            # 60-80% capacity
    SATURATED = "saturated"    # 80-95% capacity
    OVERLOADED = "overloaded"  # > 95% capacity


class SaturationRisk(Enum):
    """Risk level for saturation."""
    LOW = "LOW"           # Plenty of capacity
    MEDIUM = "MEDIUM"     # Some pressure
    HIGH = "HIGH"         # Near capacity
    CRITICAL = "CRITICAL" # Beyond capacity


@dataclass
class LoadSnapshot:
    """A snapshot of cognitive load at a point in time."""
    timestamp: datetime
    query_latency_ms: float           # Time to execute last query (ms)
    active_items: int                 # Currently active items in working memory
    utilization_percent: float        # Percent of 7±2 capacity used
    saturation_level: SaturationLevel # Categorical saturation level
    operation_count: int              # Total operations recorded


class CognitiveLoadMonitor:
    """Monitors cognitive load using 7±2 working memory model.

    Tracks:
    - Query latency (proxy for processing load)
    - Active working memory items (7±2 Baddeley limit)
    - Operation complexity accumulation
    - Saturation trends over time
    """

    WORKING_MEMORY_CAPACITY = 7  # Baddeley's 7±2 limit
    HISTORY_WINDOW_SIZE = 100    # Keep last 100 measurements
    LATENCY_THRESHOLD_MS = 500   # Query latency > 500ms = high load

    def __init__(self, db: Any):
        """Initialize with Database object."""
        self.db = db
        self.operation_history: deque = deque(maxlen=self.HISTORY_WINDOW_SIZE)
        self.latency_history: deque = deque(maxlen=self.HISTORY_WINDOW_SIZE)
        self.last_measurement_time = datetime.now()
        self.total_operations = 0
        self.active_items = 0

    def record_operation(self, operation_type: str, complexity: float = 1.0) -> None:
        """Record an operation affecting cognitive load.

        Args:
            operation_type: Type of operation (e.g., 'search', 'consolidate', 'plan')
            complexity: Complexity score (0.0-1.0, affects load calculation)
        """
        self.operation_history.append({
            'type': operation_type,
            'complexity': complexity,
            'timestamp': datetime.now()
        })
        self.total_operations += 1

        # Estimate active items based on recent operations
        # More operations = more active working memory items
        self.active_items = min(
            self.WORKING_MEMORY_CAPACITY,
            len(self.operation_history) // 10
        )

    def record_latency(self, latency_ms: float) -> None:
        """Record a query latency measurement.

        Args:
            latency_ms: Query execution time in milliseconds
        """
        self.latency_history.append({
            'latency': latency_ms,
            'timestamp': datetime.now()
        })

    def get_current_load(self, project_id: Optional[int] = None) -> Optional[Dict]:
        """Get current cognitive load report.

        Args:
            project_id: Optional project ID (for context)

        Returns:
            Load report dict with saturation_level and utilization_percent
        """
        snapshot = self._compute_snapshot()
        if snapshot is None:
            return None

        return {
            'saturation_level': snapshot.saturation_level,
            'utilization_percent': snapshot.utilization_percent,
            'query_latency_ms': snapshot.query_latency_ms,
            'active_items': snapshot.active_items,
            'timestamp': snapshot.timestamp
        }

    def is_overloaded(self, threshold: float = 7.0) -> bool:
        """Check if cognitive load exceeds threshold.

        Args:
            threshold: Saturation threshold (default 7.0 = 100% of capacity)

        Returns:
            True if current load exceeds threshold
        """
        snapshot = self._compute_snapshot()
        if snapshot is None:
            return False

        # Convert saturation level to numeric value (0-10 scale)
        saturation_values = {
            SaturationLevel.IDLE: 1.0,
            SaturationLevel.LIGHT: 2.5,
            SaturationLevel.MODERATE: 4.0,
            SaturationLevel.HEAVY: 6.0,
            SaturationLevel.SATURATED: 8.0,
            SaturationLevel.OVERLOADED: 10.0,
        }

        current_saturation = saturation_values.get(snapshot.saturation_level, 4.0)
        return current_saturation >= threshold

    def get_load_report(self) -> Dict:
        """Get detailed load report with saturation risk assessment.

        Returns:
            Comprehensive load report with trends and risk assessment
        """
        snapshot = self._compute_snapshot()
        if snapshot is None:
            return {
                "current_load": {"utilization_percent": 0.0, "saturation_level": "idle"},
                "saturation_risk": "LOW",
                "recommendations": []
            }

        # Assess saturation risk based on trends
        risk = self._assess_saturation_risk(snapshot)

        recommendations = self._get_recommendations(snapshot, risk)

        return {
            "current_load": {
                "utilization_percent": snapshot.utilization_percent,
                "saturation_level": snapshot.saturation_level.value,
                "query_latency_ms": snapshot.query_latency_ms,
                "active_items": snapshot.active_items,
            },
            "saturation_risk": risk.value,
            "operations_recorded": snapshot.operation_count,
            "capacity_remaining": max(0, self.WORKING_MEMORY_CAPACITY - snapshot.active_items),
            "recommendations": recommendations,
            "timestamp": snapshot.timestamp
        }

    def get_cognitive_load_report(self, project_id: Optional[int] = None) -> Dict:
        """Get cognitive load report (alternate API for handler compatibility).

        Args:
            project_id: Optional project ID (for context)

        Returns:
            Comprehensive load report
        """
        return self.get_load_report()

    def _compute_snapshot(self) -> Optional[LoadSnapshot]:
        """Compute current load snapshot from history."""
        if not self.operation_history and not self.latency_history:
            return LoadSnapshot(
                timestamp=datetime.now(),
                query_latency_ms=0.0,
                active_items=0,
                utilization_percent=0.0,
                saturation_level=SaturationLevel.IDLE,
                operation_count=0
            )

        # Calculate average latency from recent measurements
        avg_latency = 0.0
        if self.latency_history:
            avg_latency = sum(m['latency'] for m in self.latency_history) / len(self.latency_history)

        # Calculate utilization as percentage of capacity
        utilization = (self.active_items / self.WORKING_MEMORY_CAPACITY) * 100

        # Determine saturation level
        saturation_level = self._compute_saturation_level(utilization, avg_latency)

        return LoadSnapshot(
            timestamp=datetime.now(),
            query_latency_ms=avg_latency,
            active_items=self.active_items,
            utilization_percent=utilization,
            saturation_level=saturation_level,
            operation_count=self.total_operations
        )

    def _compute_saturation_level(self, utilization_percent: float, latency_ms: float) -> SaturationLevel:
        """Compute saturation level from utilization and latency."""
        # Combined score: 40% utilization, 40% latency, 20% history trend
        utilization_score = utilization_percent / 100.0  # 0-1
        latency_score = min(latency_ms / self.LATENCY_THRESHOLD_MS, 1.0)  # 0-1

        combined_score = (utilization_score * 0.4 + latency_score * 0.4)

        # Map to saturation level
        if combined_score < 0.2:
            return SaturationLevel.IDLE
        elif combined_score < 0.4:
            return SaturationLevel.LIGHT
        elif combined_score < 0.6:
            return SaturationLevel.MODERATE
        elif combined_score < 0.8:
            return SaturationLevel.HEAVY
        elif combined_score < 0.95:
            return SaturationLevel.SATURATED
        else:
            return SaturationLevel.OVERLOADED

    def _assess_saturation_risk(self, snapshot: LoadSnapshot) -> SaturationRisk:
        """Assess saturation risk from snapshot."""
        if snapshot.saturation_level in [SaturationLevel.OVERLOADED]:
            return SaturationRisk.CRITICAL
        elif snapshot.saturation_level in [SaturationLevel.SATURATED]:
            return SaturationRisk.HIGH
        elif snapshot.saturation_level in [SaturationLevel.HEAVY]:
            return SaturationRisk.MEDIUM
        else:
            return SaturationRisk.LOW

    def _get_recommendations(self, snapshot: LoadSnapshot, risk: SaturationRisk) -> list:
        """Get recommendations based on current state."""
        recommendations = []

        if risk == SaturationRisk.CRITICAL:
            recommendations.append("⚠️ CRITICAL: Consolidate to free memory immediately")
            recommendations.append("⚠️ Consider breaking task into smaller steps")
            recommendations.append("⚠️ Run sleep-like consolidation: `/consolidate all true`")
        elif risk == SaturationRisk.HIGH:
            recommendations.append("Run consolidation to extract patterns: `/consolidate`")
            recommendations.append("Consider deferring non-urgent tasks")
        elif risk == SaturationRisk.MEDIUM:
            recommendations.append("Monitor load levels")
            recommendations.append("Consider consolidation if load continues rising")

        if snapshot.query_latency_ms > self.LATENCY_THRESHOLD_MS:
            recommendations.append(f"High query latency ({snapshot.query_latency_ms:.0f}ms) - optimize searches")

        return recommendations
