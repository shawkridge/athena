"""Metrics aggregation service for computing dashboard metrics."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from models.metrics import (
    DashboardOverview,
    SystemHealth,
    MemoryMetrics,
    CognitiveLoad,
    WorkingMemoryItem,
    HookMetrics,
    TaskMetrics,
    LearningMetrics,
    ConsolidationProgress,
)
from services.data_loader import DataLoader
from services.cache_manager import CacheManager
from config import settings

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """Aggregate metrics from multiple data sources."""

    def __init__(self, data_loader: DataLoader, cache: CacheManager):
        """Initialize aggregator.

        Args:
            data_loader: Data loader instance
            cache: Cache manager instance
        """
        self.data_loader = data_loader
        self.cache = cache

    # ========================================================================
    # OVERVIEW METRICS
    # ========================================================================

    async def get_dashboard_overview(self) -> DashboardOverview:
        """Get complete dashboard overview.

        Returns:
            DashboardOverview with all metrics
        """
        cache_key = CacheManager.cache_key("dashboard", "overview")

        return await self.cache.get_or_compute(
            cache_key,
            self._compute_dashboard_overview,
            ttl=30,  # 30 second cache
        )

    def _compute_dashboard_overview(self) -> DashboardOverview:
        """Compute dashboard overview synchronously."""
        # Get all metrics
        system_health = self._compute_system_health()
        memory_metrics = self._compute_memory_metrics()
        cognitive_load = self._compute_cognitive_load()
        consolidation = self._compute_consolidation_progress()
        task_metrics = self._compute_task_metrics()

        # Get recent events
        recent_events = self.data_loader.get_recent_events(limit=10)
        recent_events_formatted = [
            {
                "timestamp": e.get("timestamp", ""),
                "type": e.get("event_type", "unknown"),
                "status": "success",
            }
            for e in recent_events
        ]

        # Compile warnings
        warnings = []
        if cognitive_load.status == "critical":
            warnings.append("⚠️ Cognitive load at capacity - consolidation recommended")
        if memory_metrics.gap_count > 10:
            warnings.append(f"⚠️ {memory_metrics.gap_count} knowledge gaps identified")
        if not consolidation.status == "idle" and consolidation.status != "completed":
            warnings.append(f"🔄 Consolidation in progress ({consolidation.progress_percent}%)")

        return DashboardOverview(
            system_health=system_health,
            memory_metrics=memory_metrics,
            cognitive_load=cognitive_load,
            hook_count=6,  # Hard-coded for now
            hooks_active=6,
            consolidation=consolidation,
            active_goals=task_metrics.active_goals,
            active_tasks=task_metrics.active_tasks,
            completion_rate=task_metrics.completion_rate,
            learning_velocity=0.0,  # Compute if needed
            recent_events=recent_events_formatted,
            warnings=warnings,
            last_updated=datetime.utcnow(),
        )

    # ========================================================================
    # SYSTEM HEALTH
    # ========================================================================

    def _compute_system_health(self) -> SystemHealth:
        """Compute overall system health."""
        memory_metrics = self._compute_memory_metrics()
        cognitive_load = self._compute_cognitive_load()

        # Determine statuses
        quality_status = self._quality_status(memory_metrics.quality_score)
        load_status = cognitive_load.status
        hooks_status = "all_active"  # Would check actual hook status
        database_status = "healthy"  # Would check actual database

        return SystemHealth(
            quality_score=memory_metrics.quality_score,
            quality_status=quality_status,
            load_status=load_status,
            hooks_status=hooks_status,
            database_status=database_status,
            last_update=datetime.utcnow(),
        )

    # ========================================================================
    # MEMORY METRICS
    # ========================================================================

    def _compute_memory_metrics(self) -> MemoryMetrics:
        """Compute memory system metrics."""
        # Get data from database
        event_count = self.data_loader.count_events()
        semantic_count = self.data_loader.count_semantic_memories()
        procedure_count = self.data_loader.count_procedures()
        gap_count = self.data_loader.count_knowledge_gaps()
        last_consolidation = self.data_loader.get_last_consolidation()
        quality_data = self.data_loader.get_memory_metrics()

        # Use quality data or defaults
        quality_score = quality_data.get("quality_score", 0.75)
        compression = quality_data.get("compression_ratio", 0.78)
        recall = quality_data.get("recall_accuracy", 0.85)
        consistency = quality_data.get("consistency", 0.82)
        density = quality_data.get("density", 0.88)

        last_consol_dt = (
            datetime.fromisoformat(last_consolidation["timestamp"])
            if last_consolidation and last_consolidation.get("timestamp")
            else datetime.utcnow()
        )

        return MemoryMetrics(
            quality_score=quality_score,
            compression_ratio=compression,
            recall_accuracy=recall,
            consistency=consistency,
            density=density,
            event_count=event_count,
            semantic_count=semantic_count,
            procedure_count=procedure_count,
            gap_count=gap_count,
            last_consolidation=last_consol_dt,
            consolidation_in_progress=False,
        )

    # ========================================================================
    # COGNITIVE LOAD
    # ========================================================================

    def _compute_cognitive_load(self) -> CognitiveLoad:
        """Compute cognitive load metrics."""
        # Get working memory items
        items_data = self.data_loader.get_working_memory_items()
        current_load = len(items_data)
        max_capacity = 7
        utilization = (current_load / max_capacity) * 100

        # Convert to WorkingMemoryItem models
        active_items = [
            WorkingMemoryItem(
                item_id=item.get("id", ""),
                content=item.get("content", "")[:100],  # First 100 chars
                item_type=item.get("item_type", "fact"),
                freshness_percent=min(100, item.get("freshness", 50)),
                decay_rate_percent_per_hour=5.0,
                time_added=datetime.utcnow(),
                priority=item.get("priority", 5),
            )
            for item in items_data
        ]

        # Determine status
        if current_load >= 7:
            status = "critical"
        elif current_load >= 5:
            status = "warning"
        else:
            status = "healthy"

        warnings = []
        if status == "critical":
            warnings.append("🚨 CRITICAL: At capacity limit (7/7)")
        elif status == "warning":
            warnings.append(f"⚠️  Approaching capacity ({current_load}/7)")

        return CognitiveLoad(
            current_load=current_load,
            max_capacity=max_capacity,
            utilization_percent=utilization,
            active_items=active_items,
            avg_decay_rate_percent=5.0,
            warnings=warnings,
            status=status,
        )

    # ========================================================================
    # CONSOLIDATION PROGRESS
    # ========================================================================

    def _compute_consolidation_progress(self) -> ConsolidationProgress:
        """Compute consolidation pipeline progress."""
        last_consol = self.data_loader.get_last_consolidation()

        if not last_consol:
            return ConsolidationProgress(
                status="idle",
                events_processed=0,
                events_total=self.data_loader.count_events(),
                progress_percent=0.0,
                patterns_extracted=0,
                quality_score=0.0,
            )

        events_processed = last_consol.get("events_processed", 0)
        events_total = self.data_loader.count_events()
        patterns = last_consol.get("patterns_extracted", 0)
        quality = last_consol.get("quality_score", 0.75)

        progress_percent = (
            (events_processed / events_total * 100) if events_total > 0 else 0.0
        )

        return ConsolidationProgress(
            status="completed",
            events_processed=events_processed,
            events_total=events_total,
            progress_percent=progress_percent,
            patterns_extracted=patterns,
            quality_score=quality,
        )

    # ========================================================================
    # TASK METRICS
    # ========================================================================

    def _compute_task_metrics(self) -> TaskMetrics:
        """Compute task and project metrics."""
        active_goals = len(self.data_loader.get_active_goals())
        active_tasks = len(self.data_loader.get_active_tasks())
        project_stats = self.data_loader.get_project_stats()

        total_projects = project_stats.get("project_count", 0)
        completed = project_stats.get("completed_count", 0)
        completion_rate = (completed / total_projects) if total_projects > 0 else 0.0

        return TaskMetrics(
            active_goals=active_goals,
            active_tasks=active_tasks,
            total_projects=total_projects,
            completion_rate=completion_rate,
            on_time_rate=0.85,  # Would compute from actual data
            blocker_count=0,  # Would compute from actual data
            milestone_progress=0.75,  # Would compute from actual data
            estimated_vs_actual_ratio=1.1,  # Would compute from actual data
            projects=[],  # Would populate from database
            active_goals_list=[],  # Would populate from database
        )

    # ========================================================================
    # HOOK METRICS
    # ========================================================================

    async def get_hook_metrics(self) -> List[HookMetrics]:
        """Get metrics for all hooks."""
        cache_key = CacheManager.cache_key("hooks", "metrics")

        return await self.cache.get_or_compute(
            cache_key,
            self._compute_hook_metrics,
            ttl=60,  # 60 second cache
        )

    def _compute_hook_metrics(self) -> List[HookMetrics]:
        """Compute hook metrics synchronously."""
        hook_executions = self.data_loader.get_hook_executions(hours=24)

        metrics = []
        for hook in hook_executions:
            metrics.append(
                HookMetrics(
                    hook_name=hook.get("hook_name", "unknown"),
                    status="active",
                    execution_count=hook.get("count", 0),
                    avg_latency_ms=hook.get("avg_latency", 50.0),
                    p95_latency_ms=hook.get("avg_latency", 50.0) * 1.5,
                    p99_latency_ms=hook.get("avg_latency", 50.0) * 2.0,
                    success_rate=0.99,
                    error_count=0,
                    error_rate=0.01,
                    last_execution=datetime.utcnow(),
                    agents_invoked=[],
                )
            )

        return metrics

    # ========================================================================
    # LEARNING METRICS
    # ========================================================================

    def _compute_learning_metrics(self) -> LearningMetrics:
        """Compute learning and analytics metrics."""
        event_count = self.data_loader.count_events()
        last_consol = self.data_loader.get_last_consolidation()
        patterns = last_consol.get("patterns_extracted", 0) if last_consol else 0
        procedures = self.data_loader.get_top_procedures(limit=5)

        encoding_eff = (patterns / max(event_count, 1)) * 100
        encoding_eff = min(1.0, encoding_eff / 100)  # Normalize to 0-1

        return LearningMetrics(
            encoding_efficiency=encoding_eff,
            patterns_extracted=patterns,
            patterns_this_session=0,
            procedure_count=self.data_loader.count_procedures(),
            procedure_reuse_rate=0.34,
            strategy_effectiveness={},
            knowledge_gaps_remaining=self.data_loader.count_knowledge_gaps(),
            knowledge_gaps_resolved_this_week=0,
            learning_velocity=0.0,
            top_procedures=procedures,
        )

    # ========================================================================
    # HELPERS
    # ========================================================================

    @staticmethod
    def _quality_status(score: float) -> str:
        """Convert quality score to status string."""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        else:
            return "poor"
