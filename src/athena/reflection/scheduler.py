"""Automatic reflection scheduling and trend monitoring.

Implements background reflection cycles with metric tracking,
trend analysis, and proactive alerting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class ReflectionMetrics:
    """Metrics captured during reflection cycle."""

    project_id: int
    timestamp: datetime
    accuracy: float  # 0.0-1.0
    false_positive_rate: float  # 0.0-1.0
    gap_count: int
    contradiction_count: int
    memory_size_bytes: int
    query_latency_ms: float
    wm_utilization: float  # 0.0-1.0
    cognitive_load: str  # "healthy", "saturated", "overloaded"
    workload_trend: str  # "stable", "growing", "degrading"


@dataclass
class ReflectionAlert:
    """Alert generated from reflection analysis."""

    project_id: int
    alert_type: str  # "quality_degradation", "gap_expansion", "load_trend"
    severity: str  # "low", "medium", "high"
    message: str
    recommended_action: str
    created_at: datetime


class ReflectionMetricsStore:
    """Store and retrieve reflection metrics."""

    def __init__(self, db):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create metrics table if not exists."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflection_metrics (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                accuracy REAL,
                false_positive_rate REAL,
                gap_count INTEGER,
                contradiction_count INTEGER,
                memory_size_bytes INTEGER,
                query_latency_ms REAL,
                wm_utilization REAL,
                cognitive_load TEXT,
                workload_trend TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflection_alerts (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                recommended_action TEXT,
                created_at DATETIME NOT NULL,
                dismissed_at DATETIME,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)
        self.db.conn.commit()

    def record_metrics(self, metrics: ReflectionMetrics) -> int:
        """Record reflection metrics."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO reflection_metrics (
                project_id, timestamp, accuracy, false_positive_rate,
                gap_count, contradiction_count, memory_size_bytes,
                query_latency_ms, wm_utilization, cognitive_load,
                workload_trend
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.project_id, metrics.timestamp, metrics.accuracy,
            metrics.false_positive_rate, metrics.gap_count,
            metrics.contradiction_count, metrics.memory_size_bytes,
            metrics.query_latency_ms, metrics.wm_utilization,
            metrics.cognitive_load, metrics.workload_trend
        ))
        self.db.conn.commit()
        return cursor.lastrowid

    def get_recent_metrics(self, project_id: int, hours: int = 168) -> List[ReflectionMetrics]:
        """Get metrics from last N hours."""
        cursor = self.db.conn.cursor()
        cutoff = datetime.now() - timedelta(hours=hours)
        cursor.execute("""
            SELECT * FROM reflection_metrics
            WHERE project_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (project_id, cutoff))
        return [self._row_to_metrics(row) for row in cursor.fetchall()]

    def _row_to_metrics(self, row) -> ReflectionMetrics:
        """Convert database row to ReflectionMetrics."""
        return ReflectionMetrics(
            project_id=row['project_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            accuracy=row['accuracy'],
            false_positive_rate=row['false_positive_rate'],
            gap_count=row['gap_count'],
            contradiction_count=row['contradiction_count'],
            memory_size_bytes=row['memory_size_bytes'],
            query_latency_ms=row['query_latency_ms'],
            wm_utilization=row['wm_utilization'],
            cognitive_load=row['cognitive_load'],
            workload_trend=row['workload_trend']
        )

    def record_alert(self, alert: ReflectionAlert) -> int:
        """Record a reflection alert."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO reflection_alerts (
                project_id, alert_type, severity, message,
                recommended_action, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alert.project_id, alert.alert_type, alert.severity,
            alert.message, alert.recommended_action, alert.created_at
        ))
        self.db.conn.commit()
        return cursor.lastrowid

    def get_active_alerts(self, project_id: int) -> List[ReflectionAlert]:
        """Get unaddressed alerts."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM reflection_alerts
            WHERE project_id = ? AND dismissed_at IS NULL
            ORDER BY created_at DESC
        """, (project_id,))
        return [self._row_to_alert(row) for row in cursor.fetchall()]

    def _row_to_alert(self, row) -> ReflectionAlert:
        """Convert database row to ReflectionAlert."""
        return ReflectionAlert(
            project_id=row['project_id'],
            alert_type=row['alert_type'],
            severity=row['severity'],
            message=row['message'],
            recommended_action=row['recommended_action'],
            created_at=datetime.fromisoformat(row['created_at'])
        )


class TrendAnalyzer:
    """Analyze trends in reflection metrics."""

    @staticmethod
    def detect_quality_degradation(metrics: List[ReflectionMetrics]) -> Optional[str]:
        """Detect if quality is degrading."""
        if len(metrics) < 2:
            return None

        # Check accuracy trend
        recent = metrics[0].accuracy if metrics else 0.9
        older = metrics[-1].accuracy if len(metrics) > 1 else 0.9

        if recent < older - 0.05:  # Dropped 5%+ points
            return f"Accuracy degraded from {older:.1%} to {recent:.1%}"

        # Check false positive rate
        if metrics[0].false_positive_rate > 0.05:
            return f"False positive rate high: {metrics[0].false_positive_rate:.1%}"

        return None

    @staticmethod
    def detect_gap_expansion(metrics: List[ReflectionMetrics]) -> Optional[str]:
        """Detect if knowledge gaps are expanding."""
        if len(metrics) < 2:
            return None

        recent_gaps = metrics[0].gap_count
        older_gaps = metrics[-1].gap_count

        if recent_gaps > older_gaps + 3:  # Increased by 3+
            return f"Knowledge gaps expanded from {older_gaps} to {recent_gaps}"

        if metrics[0].contradiction_count > 5:
            return f"Contradictions detected: {metrics[0].contradiction_count}"

        return None

    @staticmethod
    def detect_load_trend(metrics: List[ReflectionMetrics]) -> Optional[str]:
        """Detect cognitive load trends."""
        if not metrics:
            return None

        if metrics[0].cognitive_load == "overloaded":
            return "System is overloaded"

        # Check WM utilization trend
        recent_util = metrics[0].wm_utilization
        if recent_util > 0.85:
            return f"Working memory at {recent_util:.0%} capacity"

        return None

    @staticmethod
    def calculate_workload_trend(metrics: List[ReflectionMetrics]) -> str:
        """Calculate overall workload trend."""
        if len(metrics) < 3:
            return "stable"

        # Simple trend: compare recent vs older
        recent_avg = sum(m.query_latency_ms for m in metrics[:3]) / 3
        older_avg = sum(m.query_latency_ms for m in metrics[-3:]) / 3

        if recent_avg > older_avg * 1.2:  # 20% increase
            return "growing"
        elif recent_avg < older_avg * 0.8:  # 20% decrease
            return "degrading"
        return "stable"


class ReflectionScheduler:
    """Schedule and manage automatic reflection cycles."""

    def __init__(self, db, quality_monitor, gap_detector, load_monitor):
        self.db = db
        self.quality_monitor = quality_monitor
        self.gap_detector = gap_detector
        self.load_monitor = load_monitor
        self.metrics_store = ReflectionMetricsStore(db)
        self.trend_analyzer = TrendAnalyzer()

    async def run_reflection_cycle(self, project_id: int) -> Dict:
        """Run a complete reflection cycle."""
        try:
            # Collect current metrics
            quality = self.quality_monitor.evaluate_memory_quality(project_id)
            unresolved_gaps = self.gap_detector.get_unresolved_gaps(project_id)
            contradictions = self.gap_detector.detect_direct_contradictions(project_id)
            load = self.load_monitor.get_cognitive_load_report(project_id)

            # Convert to metrics
            metrics = ReflectionMetrics(
                project_id=project_id,
                timestamp=datetime.now(),
                accuracy=quality.get('accuracy', 0.9),
                false_positive_rate=quality.get('false_positive_rate', 0.02),
                gap_count=len(unresolved_gaps),
                contradiction_count=len(contradictions),
                memory_size_bytes=self._estimate_memory_size(project_id),
                query_latency_ms=load.get('avg_query_latency_ms', 50),
                wm_utilization=load.get('utilization_percent', 0) / 100,
                cognitive_load=load.get('saturation_level', 'healthy'),
                workload_trend='stable'
            )

            # Record metrics
            self.metrics_store.record_metrics(metrics)

            # Analyze trends
            recent = self.metrics_store.get_recent_metrics(project_id, hours=168)
            metrics.workload_trend = self.trend_analyzer.calculate_workload_trend(recent)

            # Generate alerts
            alerts = []
            quality_issue = self.trend_analyzer.detect_quality_degradation(recent)
            if quality_issue:
                alert = ReflectionAlert(
                    project_id=project_id,
                    alert_type="quality_degradation",
                    severity="high" if "accuracy" in quality_issue else "medium",
                    message=quality_issue,
                    recommended_action="/consolidate",
                    created_at=datetime.now()
                )
                self.metrics_store.record_alert(alert)
                alerts.append(alert)

            gap_issue = self.trend_analyzer.detect_gap_expansion(recent)
            if gap_issue:
                alert = ReflectionAlert(
                    project_id=project_id,
                    alert_type="gap_expansion",
                    severity="medium",
                    message=gap_issue,
                    recommended_action="/research",
                    created_at=datetime.now()
                )
                self.metrics_store.record_alert(alert)
                alerts.append(alert)

            load_issue = self.trend_analyzer.detect_load_trend(recent)
            if load_issue:
                alert = ReflectionAlert(
                    project_id=project_id,
                    alert_type="load_trend",
                    severity="high",
                    message=load_issue,
                    recommended_action="/focus consolidate all true",
                    created_at=datetime.now()
                )
                self.metrics_store.record_alert(alert)
                alerts.append(alert)

            return {
                "status": "completed",
                "metrics_recorded": 1,
                "alerts_generated": len(alerts),
                "quality": {
                    "accuracy": metrics.accuracy,
                    "false_positive_rate": metrics.false_positive_rate
                },
                "gaps": {
                    "count": metrics.gap_count,
                    "contradictions": metrics.contradiction_count
                },
                "load": {
                    "utilization": metrics.wm_utilization,
                    "cognitive_load": metrics.cognitive_load
                },
                "trend": metrics.workload_trend
            }

        except Exception as e:
            logger.error(f"Error in reflection cycle: {e}")
            return {"status": "error", "error": str(e)}

    def _estimate_memory_size(self, project_id: int) -> int:
        """Estimate total memory database size."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
        result = cursor.fetchone()
        return result[0] if result else 0
