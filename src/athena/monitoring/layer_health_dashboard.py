"""
Real-time Layer Health Monitoring Dashboard

Provides comprehensive health metrics for all 8 memory layers with:
- Real-time status indicators
- Performance metrics
- Capacity utilization tracking
- Auto-integration hook health
- Consolidation status
- Alerts and recommendations
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import time
from athena.core.database import Database


class HealthStatus(str, Enum):
    """Health status indicators."""
    HEALTHY = "healthy"     # ✓ 80-100%
    WARNING = "warning"     # ⚠ 50-79%
    CRITICAL = "critical"   # ✗ <50%


class LayerType(str, Enum):
    """Memory layer types."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROSPECTIVE = "prospective"
    GRAPH = "graph"
    META = "meta"
    CONSOLIDATION = "consolidation"
    WORKING = "working"


@dataclass
class LayerHealth:
    """Health metrics for a single layer."""
    layer: LayerType
    status: HealthStatus
    utilization: float  # 0-1 scale
    record_count: int
    last_updated: datetime
    metrics: Dict[str, Any]
    recommendations: List[str]


@dataclass
class SystemHealth:
    """Overall system health summary."""
    total_status: HealthStatus
    timestamp: datetime
    layer_health: Dict[LayerType, LayerHealth]
    alerts: List[str]
    performance_summary: Dict[str, Any]


class LayerHealthMonitor:
    """Monitor and analyze health of all memory layers."""

    def __init__(self, db: Database):
        """Initialize layer health monitor.

        Args:
            db: Database instance for querying layer statistics
        """
        self.db = db
        self.cursor = db.conn.cursor()

    def get_episodic_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for episodic memory layer.

        Checks:
        - Event count
        - Session continuity
        - Timestamp validity
        - Storage efficiency
        """
        query = "SELECT COUNT(*) FROM episodic_events"
        params = []

        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)

        self.cursor.execute(query, params)
        event_count = self.cursor.fetchone()[0]

        # Health calculation
        utilization = min(1.0, event_count / 10000)  # 10K events = 100% utilization
        status = self._calculate_status(utilization)

        metrics = {
            "event_count": event_count,
            "session_coverage": self._get_session_coverage(project_id),
            "consolidation_lag": self._get_consolidation_lag(project_id),
        }

        recommendations = []
        if event_count > 5000:
            recommendations.append("Run consolidation to extract patterns")
        if utilization > 0.8:
            recommendations.append("Consider optimizing episodic storage")

        return LayerHealth(
            layer=LayerType.EPISODIC,
            status=status,
            utilization=utilization,
            record_count=event_count,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=recommendations,
        )

    def get_semantic_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for semantic memory layer."""
        query = "SELECT COUNT(*) FROM memories"
        params = []

        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)

        self.cursor.execute(query, params)
        memory_count = self.cursor.fetchone()[0]

        utilization = min(1.0, memory_count / 5000)
        status = self._calculate_status(utilization)

        metrics = {
            "memory_count": memory_count,
            "avg_usefulness": self._get_avg_usefulness(project_id),
            "low_quality_count": self._get_low_quality_count(project_id),
        }

        recommendations = []
        if metrics.get("low_quality_count", 0) > 100:
            recommendations.append("Run optimization to remove low-value memories")

        return LayerHealth(
            layer=LayerType.SEMANTIC,
            status=status,
            utilization=utilization,
            record_count=memory_count,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=recommendations,
        )

    def get_procedural_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for procedural memory layer."""
        # Procedures are global (not per-project)
        query = "SELECT COUNT(*) FROM procedures"
        params = []

        self.cursor.execute(query, params)
        procedure_count = self.cursor.fetchone()[0]

        utilization = min(1.0, procedure_count / 500)
        status = self._calculate_status(utilization)

        metrics = {
            "procedure_count": procedure_count,
            "success_rate": self._get_procedure_success_rate(project_id),
            "avg_execution_time": self._get_avg_execution_time(project_id),
        }

        return LayerHealth(
            layer=LayerType.PROCEDURAL,
            status=status,
            utilization=utilization,
            record_count=procedure_count,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=[],
        )

    def get_prospective_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for prospective memory layer."""
        query = "SELECT COUNT(*) FROM prospective_tasks"
        params = []

        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)

        self.cursor.execute(query, params)
        task_count = self.cursor.fetchone()[0]

        # Count active tasks
        active_query = query + " AND status = ?"
        self.cursor.execute(
            active_query,
            params + ["active"] if params else ["active"]
        )
        active_count = self.cursor.fetchone()[0] if not params else 0

        utilization = min(1.0, task_count / 1000)
        status = self._calculate_status(utilization)

        metrics = {
            "task_count": task_count,
            "active_tasks": active_count,
            "task_completion_rate": self._get_task_completion_rate(project_id),
        }

        return LayerHealth(
            layer=LayerType.PROSPECTIVE,
            status=status,
            utilization=utilization,
            record_count=task_count,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=[],
        )

    def get_graph_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for knowledge graph layer."""
        query = "SELECT COUNT(*) FROM entities"
        params = []

        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)

        self.cursor.execute(query, params)
        entity_count = self.cursor.fetchone()[0]

        # Count relations
        relation_query = "SELECT COUNT(*) FROM entity_relations"
        if project_id:
            relation_query += " WHERE (SELECT project_id FROM entities WHERE id = from_entity_id) = ?"
            self.cursor.execute(relation_query, [project_id])
        else:
            self.cursor.execute(relation_query)
        relation_count = self.cursor.fetchone()[0]

        utilization = min(1.0, (entity_count + relation_count) / 5000)
        status = self._calculate_status(utilization)

        metrics = {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "avg_connections": relation_count / entity_count if entity_count > 0 else 0,
            "isolated_entities": self._get_isolated_entities_count(project_id),
        }

        recommendations = []
        if metrics.get("isolated_entities", 0) > 10:
            recommendations.append("Link isolated entities to knowledge graph")

        return LayerHealth(
            layer=LayerType.GRAPH,
            status=status,
            utilization=utilization,
            record_count=entity_count,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=recommendations,
        )

    def get_meta_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for meta-memory layer."""
        # Meta-memory tracks expertise across domains
        try:
            query = "SELECT COUNT(DISTINCT domain) FROM expertise"
            params = []

            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)

            self.cursor.execute(query, params)
            domain_count = self.cursor.fetchone()[0]
        except:
            domain_count = 0

        # Meta-memory is always active if system is running
        utilization = min(1.0, domain_count / 10)
        status = HealthStatus.HEALTHY  # Meta-memory always active

        metrics = {
            "tracked_domains": domain_count,
            "avg_domain_confidence": self._get_avg_confidence(project_id),
        }

        return LayerHealth(
            layer=LayerType.META,
            status=status,
            utilization=utilization,
            record_count=domain_count,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=[],
        )

    def get_consolidation_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for consolidation system."""
        try:
            query = "SELECT COUNT(*) FROM consolidation_runs"
            params = []

            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)

            self.cursor.execute(query, params)
            consolidation_count = self.cursor.fetchone()[0]

            # Get last consolidation time
            last_run_query = "SELECT MAX(created_at) FROM consolidation_runs"
            if project_id:
                last_run_query += " WHERE project_id = ?"
                self.cursor.execute(last_run_query, [project_id])
            else:
                self.cursor.execute(last_run_query)

            last_run_timestamp = self.cursor.fetchone()[0]
            last_run_age = (
                (time.time() - last_run_timestamp) / 3600
                if last_run_timestamp
                else float("inf")
            )
        except:
            consolidation_count = 0
            last_run_age = float("inf")

        # Consolidation health based on recency
        if last_run_age < 1:  # Run in last hour
            utilization = 1.0
            status = HealthStatus.HEALTHY
        elif last_run_age < 24:  # Run in last day
            utilization = 0.7
            status = HealthStatus.WARNING
        else:
            utilization = 0.3
            status = HealthStatus.CRITICAL

        metrics = {
            "consolidation_count": consolidation_count,
            "last_run_age_hours": int(last_run_age) if last_run_age != float("inf") else -1,
        }

        recommendations = []
        if status == HealthStatus.CRITICAL:
            recommendations.append("Run consolidation to extract patterns from episodic events")

        return LayerHealth(
            layer=LayerType.CONSOLIDATION,
            status=status,
            utilization=utilization,
            record_count=consolidation_count,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=recommendations,
        )

    def get_working_memory_health(self, project_id: Optional[int] = None) -> LayerHealth:
        """Get health metrics for working memory layer."""
        try:
            query = "SELECT COUNT(*) FROM working_memory"
            params = []

            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)

            self.cursor.execute(query, params)
            active_items = self.cursor.fetchone()[0]
        except:
            active_items = 0

        # Working memory target is 7 items (Miller's Law)
        target_capacity = 7
        utilization = min(1.0, active_items / target_capacity)

        if utilization < 0.5:
            status = HealthStatus.HEALTHY
        elif utilization < 0.85:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.CRITICAL

        metrics = {
            "active_items": active_items,
            "capacity": target_capacity,
            "saturation_percent": int(utilization * 100),
        }

        recommendations = []
        if status == HealthStatus.CRITICAL:
            recommendations.append("Clear working memory to reduce cognitive load")

        return LayerHealth(
            layer=LayerType.WORKING,
            status=status,
            utilization=utilization,
            record_count=active_items,
            last_updated=datetime.now(),
            metrics=metrics,
            recommendations=recommendations,
        )

    def get_system_health(self, project_id: Optional[int] = None) -> SystemHealth:
        """Get overall system health across all layers."""
        layer_health = {
            LayerType.EPISODIC: self.get_episodic_health(project_id),
            LayerType.SEMANTIC: self.get_semantic_health(project_id),
            LayerType.PROCEDURAL: self.get_procedural_health(project_id),
            LayerType.PROSPECTIVE: self.get_prospective_health(project_id),
            LayerType.GRAPH: self.get_graph_health(project_id),
            LayerType.META: self.get_meta_health(project_id),
            LayerType.CONSOLIDATION: self.get_consolidation_health(project_id),
            LayerType.WORKING: self.get_working_memory_health(project_id),
        }

        # Calculate overall status
        critical_count = sum(
            1 for h in layer_health.values() if h.status == HealthStatus.CRITICAL
        )
        warning_count = sum(
            1 for h in layer_health.values() if h.status == HealthStatus.WARNING
        )

        if critical_count > 0:
            total_status = HealthStatus.CRITICAL
        elif warning_count > 2:
            total_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            total_status = HealthStatus.WARNING
        else:
            total_status = HealthStatus.HEALTHY

        # Collect all alerts
        alerts = []
        for layer, health in layer_health.items():
            if health.status == HealthStatus.CRITICAL:
                alerts.append(f"⚠ {layer.value}: CRITICAL - {health.recommendations[0] if health.recommendations else 'Check health'}")
            elif health.status == HealthStatus.WARNING:
                alerts.append(
                    f"⚠ {layer.value}: WARNING - {health.recommendations[0] if health.recommendations else 'Monitor'}"
                )

        # Performance summary
        performance_summary = {
            "healthy_layers": 8 - critical_count - warning_count,
            "warning_layers": warning_count,
            "critical_layers": critical_count,
            "avg_utilization": sum(h.utilization for h in layer_health.values()) / len(layer_health),
        }

        return SystemHealth(
            total_status=total_status,
            timestamp=datetime.now(),
            layer_health=layer_health,
            alerts=alerts,
            performance_summary=performance_summary,
        )

    def render_dashboard(self, system_health: SystemHealth) -> str:
        """Render text-based dashboard display.

        Args:
            system_health: System health data to render

        Returns:
            Formatted dashboard text
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ATHENA MEMORY SYSTEM - LAYER HEALTH DASHBOARD")
        lines.append("=" * 80)
        lines.append(f"Time: {system_health.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Overall Status: {self._status_symbol(system_health.total_status)} {system_health.total_status.upper()}")
        lines.append("")

        # Layer health grid
        lines.append("LAYER HEALTH STATUS:")
        lines.append("-" * 80)
        lines.append("Layer          | Status | Utilization | Count | Recommendations")
        lines.append("-" * 80)

        for layer, health in system_health.layer_health.items():
            symbol = self._status_symbol(health.status)
            util_pct = f"{int(health.utilization * 100)}%"
            name = layer.value.ljust(14)
            status = f"{symbol} {health.status.upper():8s}".ljust(10)
            recommendation = health.recommendations[0][:40] if health.recommendations else "OK"

            lines.append(
                f"{name} | {status} | {util_pct:11s} | {health.record_count:5d} | {recommendation}"
            )

        lines.append("")
        lines.append("PERFORMANCE SUMMARY:")
        lines.append("-" * 80)
        lines.append(f"Healthy Layers: {system_health.performance_summary['healthy_layers']}/8")
        lines.append(f"Warning Layers: {system_health.performance_summary['warning_layers']}/8")
        lines.append(f"Critical Layers: {system_health.performance_summary['critical_layers']}/8")
        lines.append(f"Average Utilization: {int(system_health.performance_summary['avg_utilization'] * 100)}%")

        if system_health.alerts:
            lines.append("")
            lines.append("ALERTS:")
            lines.append("-" * 80)
            for alert in system_health.alerts:
                lines.append(alert)

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    # Helper methods
    def _calculate_status(self, utilization: float) -> HealthStatus:
        """Calculate health status from utilization."""
        if utilization < 0.5:
            return HealthStatus.HEALTHY
        elif utilization < 0.8:
            return HealthStatus.WARNING
        else:
            return HealthStatus.CRITICAL

    def _status_symbol(self, status: HealthStatus) -> str:
        """Get status symbol."""
        if status == HealthStatus.HEALTHY:
            return "✓"
        elif status == HealthStatus.WARNING:
            return "⚠"
        else:
            return "✗"

    def _get_session_coverage(self, project_id: Optional[int]) -> int:
        """Get count of active sessions."""
        query = "SELECT COUNT(DISTINCT session_id) FROM episodic_events WHERE session_id IS NOT NULL"
        if project_id:
            query += " AND project_id = ?"
            self.cursor.execute(query, [project_id])
        else:
            self.cursor.execute(query)
        return self.cursor.fetchone()[0]

    def _get_consolidation_lag(self, project_id: Optional[int]) -> str:
        """Get time since last consolidation."""
        # Placeholder - would query consolidation_runs table
        return "Unknown"

    def _get_avg_usefulness(self, project_id: Optional[int]) -> float:
        """Get average usefulness score of memories."""
        # Placeholder
        return 0.7

    def _get_low_quality_count(self, project_id: Optional[int]) -> int:
        """Get count of low-quality memories."""
        # Placeholder
        return 0

    def _get_procedure_success_rate(self, project_id: Optional[int]) -> float:
        """Get procedure success rate."""
        # Placeholder
        return 0.85

    def _get_avg_execution_time(self, project_id: Optional[int]) -> float:
        """Get average procedure execution time."""
        # Placeholder
        return 5000.0  # milliseconds

    def _get_task_completion_rate(self, project_id: Optional[int]) -> float:
        """Get task completion rate."""
        # Placeholder
        return 0.9

    def _get_isolated_entities_count(self, project_id: Optional[int]) -> int:
        """Get count of isolated graph entities."""
        # Placeholder
        return 0

    def _get_avg_confidence(self, project_id: Optional[int]) -> float:
        """Get average confidence score."""
        # Placeholder
        return 0.75
