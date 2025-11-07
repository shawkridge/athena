"""Temporal analysis of code changes and evolution.

This module tracks code changes over time, analyzes evolution patterns,
and detects trends in code quality, complexity, and structure.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of code changes."""
    CREATION = "creation"       # New function/class
    MODIFICATION = "modification"  # Code changed
    DELETION = "deletion"        # Code removed
    REFACTORING = "refactoring"  # Code structure changed
    OPTIMIZATION = "optimization"  # Performance improvement
    BUGFIX = "bugfix"           # Bug fix
    DOCUMENTATION = "documentation"  # Doc/comment change
    UNKNOWN = "unknown"         # Unknown change


class TemporalTrend(Enum):
    """Types of temporal trends."""
    INCREASING = "increasing"   # Metric going up
    DECREASING = "decreasing"   # Metric going down
    STABLE = "stable"          # Metric stable
    VOLATILE = "volatile"      # Metric fluctuating


@dataclass
class CodeChange:
    """Represents a code change event."""
    entity_name: str
    entity_type: str
    change_type: ChangeType
    timestamp: datetime
    file_path: str
    author: Optional[str] = None
    commit_hash: Optional[str] = None
    description: Optional[str] = None
    metrics_before: Dict[str, float] = field(default_factory=dict)
    metrics_after: Dict[str, float] = field(default_factory=dict)
    impact: float = 0.5  # 0-1, estimated impact
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "change_type": self.change_type.value,
            "timestamp": self.timestamp.isoformat(),
            "file_path": self.file_path,
            "author": self.author,
            "commit_hash": self.commit_hash,
            "description": self.description,
            "metrics_before": self.metrics_before,
            "metrics_after": self.metrics_after,
            "impact": self.impact,
            "metadata": self.metadata,
        }


@dataclass
class TemporalMetrics:
    """Metrics tracked over time for an entity."""
    entity_name: str
    metric_name: str
    values: List[Tuple[datetime, float]] = field(default_factory=list)

    def add_value(self, timestamp: datetime, value: float):
        """Add a metric value."""
        self.values.append((timestamp, value))

    def get_trend(self) -> TemporalTrend:
        """Determine trend direction."""
        if len(self.values) < 2:
            return TemporalTrend.STABLE

        # Calculate simple linear trend
        values = [v for _, v in self.values]
        first_half = sum(values[: len(values) // 2]) / max(len(values) // 2, 1)
        second_half = sum(values[len(values) // 2 :]) / max(len(values) - len(values) // 2, 1)

        threshold = 0.05  # 5% change threshold
        if second_half > first_half * (1 + threshold):
            return TemporalTrend.INCREASING
        elif second_half < first_half * (1 - threshold):
            return TemporalTrend.DECREASING
        else:
            return TemporalTrend.STABLE

    def get_volatility(self) -> float:
        """Calculate metric volatility (0-1)."""
        if len(self.values) < 2:
            return 0.0

        values = [v for _, v in self.values]
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)

        # Normalize to 0-1
        std_dev = variance ** 0.5
        return min(std_dev / (avg + 1), 1.0)

    def get_change_rate(self) -> float:
        """Calculate rate of change per unit time."""
        if len(self.values) < 2:
            return 0.0

        first_time, first_val = self.values[0]
        last_time, last_val = self.values[-1]

        time_diff = (last_time - first_time).total_seconds()
        if time_diff == 0:
            return 0.0

        return (last_val - first_val) / time_diff


class CodeChangeTracker:
    """Tracks code changes over time."""

    def __init__(self):
        """Initialize tracker."""
        self.changes: List[CodeChange] = []
        self.metrics: Dict[str, TemporalMetrics] = {}

    def record_change(self, change: CodeChange) -> int:
        """Record a code change."""
        self.changes.append(change)
        return len(self.changes) - 1

    def record_metric(
        self,
        entity_name: str,
        metric_name: str,
        timestamp: datetime,
        value: float,
    ):
        """Record a metric value for an entity."""
        key = f"{entity_name}:{metric_name}"
        if key not in self.metrics:
            self.metrics[key] = TemporalMetrics(entity_name, metric_name)
        self.metrics[key].add_value(timestamp, value)

    def get_entity_history(self, entity_name: str) -> List[CodeChange]:
        """Get all changes for an entity."""
        return [c for c in self.changes if c.entity_name == entity_name]

    def get_changes_by_type(self, change_type: ChangeType) -> List[CodeChange]:
        """Get changes by type."""
        return [c for c in self.changes if c.change_type == change_type]

    def get_changes_in_timeframe(
        self, start: datetime, end: datetime
    ) -> List[CodeChange]:
        """Get changes within timeframe."""
        return [c for c in self.changes if start <= c.timestamp <= end]

    def get_entity_metrics(self, entity_name: str) -> Dict[str, TemporalMetrics]:
        """Get all metrics for an entity."""
        prefix = f"{entity_name}:"
        return {
            k: v for k, v in self.metrics.items() if k.startswith(prefix)
        }

    def calculate_change_frequency(self, entity_name: str) -> float:
        """Calculate how frequently an entity changes (changes per day)."""
        history = self.get_entity_history(entity_name)
        if len(history) < 2:
            return 0.0

        first_time = min(c.timestamp for c in history)
        last_time = max(c.timestamp for c in history)
        days = (last_time - first_time).days + 1

        return len(history) / days if days > 0 else 0.0

    def calculate_code_stability(self) -> Dict[str, float]:
        """Calculate stability score for each entity (inverse of change frequency)."""
        stability = {}
        all_entities = set(c.entity_name for c in self.changes)

        for entity in all_entities:
            frequency = self.calculate_change_frequency(entity)
            # Stability: 1 - (frequency / max_frequency)
            stability[entity] = 1.0 / (1.0 + frequency)

        return stability

    def get_high_churn_entities(self, threshold: float = 0.5) -> List[str]:
        """Find entities with high change frequency."""
        all_entities = set(c.entity_name for c in self.changes)
        frequencies = {e: self.calculate_change_frequency(e) for e in all_entities}

        if not frequencies:
            return []

        max_freq = max(frequencies.values())
        threshold_freq = max_freq * threshold

        return [e for e, freq in frequencies.items() if freq >= threshold_freq]

    def detect_change_patterns(self) -> Dict[str, Any]:
        """Detect patterns in code changes."""
        if not self.changes:
            return {}

        patterns = {
            "total_changes": len(self.changes),
            "change_types": {},
            "most_changed_entities": [],
            "change_velocity": 0.0,
        }

        # Count by change type
        for change_type in ChangeType:
            count = len(self.get_changes_by_type(change_type))
            if count > 0:
                patterns["change_types"][change_type.value] = count

        # Most changed entities
        entity_change_counts = {}
        for change in self.changes:
            entity_change_counts[change.entity_name] = (
                entity_change_counts.get(change.entity_name, 0) + 1
            )

        patterns["most_changed_entities"] = sorted(
            entity_change_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Change velocity
        if len(self.changes) > 1:
            first = min(c.timestamp for c in self.changes)
            last = max(c.timestamp for c in self.changes)
            days = (last - first).days + 1
            patterns["change_velocity"] = len(self.changes) / days

        return patterns


class TemporalAnalyzer:
    """Analyzes temporal trends in code metrics."""

    def __init__(self, tracker: CodeChangeTracker):
        """Initialize analyzer."""
        self.tracker = tracker

    def detect_metric_trends(
        self, entity_name: str
    ) -> Dict[str, TemporalTrend]:
        """Detect trends for all metrics of an entity."""
        metrics = self.tracker.get_entity_metrics(entity_name)
        trends = {}

        for metric_key, metric in metrics.items():
            metric_name = metric_key.split(":")[-1]
            trends[metric_name] = metric.get_trend()

        return trends

    def detect_volatility_issues(self, threshold: float = 0.5) -> Dict[str, float]:
        """Find metrics with high volatility."""
        volatile_metrics = {}

        for key, metric in self.tracker.metrics.items():
            volatility = metric.get_volatility()
            if volatility >= threshold:
                volatile_metrics[key] = volatility

        return volatile_metrics

    def predict_quality_decline(self) -> Optional[str]:
        """Predict if code quality is declining."""
        # Heuristic: if complexity increasing and quality decreasing, flag it
        insights = []

        for entity_metrics in self.tracker.metrics.values():
            trend = entity_metrics.get_trend()
            if "complexity" in entity_metrics.metric_name and trend == TemporalTrend.INCREASING:
                insights.append(f"{entity_metrics.entity_name}: Increasing complexity")
            elif "quality" in entity_metrics.metric_name and trend == TemporalTrend.DECREASING:
                insights.append(f"{entity_metrics.entity_name}: Declining quality")

        if insights:
            return "; ".join(insights)

        return None

    def find_high_change_concentration(self) -> Dict[str, Any]:
        """Find where changes are concentrated."""
        file_changes = {}
        for change in self.tracker.changes:
            if change.file_path not in file_changes:
                file_changes[change.file_path] = 0
            file_changes[change.file_path] += 1

        if not file_changes:
            return {}

        total_changes = sum(file_changes.values())
        percentages = {
            f: (count / total_changes) * 100 for f, count in file_changes.items()
        }

        # Find files with >20% of changes
        concentrated_files = {
            f: pct for f, pct in percentages.items() if pct > 20
        }

        return {
            "file_distribution": file_changes,
            "percentages": percentages,
            "concentrated_files": concentrated_files,
        }

    def estimate_refactoring_need(self) -> List[Tuple[str, float]]:
        """Estimate which entities need refactoring."""
        needs_refactoring = []

        for entity_name in set(c.entity_name for c in self.tracker.changes):
            # Score based on: frequency + change types + churn
            frequency = self.tracker.calculate_change_frequency(entity_name)
            changes = self.tracker.get_entity_history(entity_name)

            refactoring_changes = len(
                [c for c in changes if c.change_type == ChangeType.REFACTORING]
            )

            # Score: high frequency + few refactorings = needs refactoring
            refactoring_score = frequency * (1 - refactoring_changes / max(len(changes), 1))

            if refactoring_score > 0.3:
                needs_refactoring.append((entity_name, refactoring_score))

        return sorted(needs_refactoring, key=lambda x: x[1], reverse=True)

    def generate_temporal_report(self) -> str:
        """Generate temporal analysis report."""
        report = "TEMPORAL CODE ANALYSIS REPORT\n"
        report += "=" * 50 + "\n\n"

        patterns = self.tracker.detect_change_patterns()
        report += f"Total Changes: {patterns.get('total_changes', 0)}\n"
        report += f"Change Velocity: {patterns.get('change_velocity', 0):.2f} changes/day\n\n"

        report += "Change Type Distribution:\n"
        for change_type, count in patterns.get("change_types", {}).items():
            report += f"  {change_type}: {count}\n"

        report += "\nMost Changed Entities:\n"
        for entity, count in patterns.get("most_changed_entities", [])[:5]:
            report += f"  {entity}: {count} changes\n"

        # Trends
        report += "\nDetected Trends:\n"
        quality_decline = self.predict_quality_decline()
        if quality_decline:
            report += f"  Quality Issues: {quality_decline}\n"
        else:
            report += "  Quality: Stable\n"

        # Volatility
        volatile = self.detect_volatility_issues()
        if volatile:
            report += f"\nVolatile Metrics: {len(volatile)}\n"
            for key in list(volatile.keys())[:3]:
                report += f"  {key}\n"

        # Refactoring needs
        refactoring = self.estimate_refactoring_need()
        if refactoring:
            report += f"\nRefactoring Candidates:\n"
            for entity, score in refactoring[:5]:
                report += f"  {entity} (score: {score:.2f})\n"

        return report
