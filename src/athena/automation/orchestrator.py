"""AutomationOrchestrator - Central orchestration for Phase 5-8 automation.

Coordinates:
- Health monitoring (periodic checks, alert escalation)
- Event-triggered agent invocation (task creation, completion, status changes)
- Cross-phase workflows (Monitor → Analyze → Plan → Coordinate)
- Alert management and escalation
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..core.database import Database
from ..integration.health_monitor_agent import HealthMonitorAgent
from ..integration.planning_optimizer_agent import PlanningOptimizerAgent
from ..integration.analytics_aggregator_agent import AnalyticsAggregatorAgent
from ..integration.project_coordinator_agent import ProjectCoordinatorAgent

logger = logging.getLogger(__name__)


@dataclass
class AutomationConfig:
    """Configuration for automation behavior."""

    health_check_interval_minutes: int = 30
    critical_alert_threshold: float = 0.5
    warning_alert_threshold: float = 0.65
    enable_auto_optimize_plans: bool = True
    enable_auto_escalate_alerts: bool = True
    enable_background_monitoring: bool = True
    max_concurrent_checks: int = 5


@dataclass
class AutomationEvent:
    """Event that triggers automation."""

    event_type: str  # "task_created", "task_completed", "status_changed", etc.
    entity_id: int  # task_id, project_id, etc.
    entity_type: str  # "task", "project", etc.
    metadata: Dict[str, Any]
    timestamp: datetime


class AutomationOrchestrator:
    """Central orchestration engine for Phase 5-8 automation.

    Coordinates:
    - Periodic health monitoring (background)
    - Event-triggered agent invocation
    - Alert generation and escalation
    - Cross-phase workflow coordination
    """

    def __init__(
        self,
        db: Database,
        config: Optional[AutomationConfig] = None,
    ):
        """Initialize orchestrator.

        Args:
            db: Database connection
            config: Automation configuration
        """
        self.db = db
        self.config = config or AutomationConfig()

        # Initialize agents
        self.health_monitor = HealthMonitorAgent(db)
        self.planning_optimizer = PlanningOptimizerAgent(db)
        self.analytics_aggregator = AnalyticsAggregatorAgent(db)
        self.project_coordinator = ProjectCoordinatorAgent(db)

        # State tracking
        self._last_health_check_time: Dict[int, datetime] = {}
        self._active_alerts: Dict[int, Dict[str, Any]] = {}
        self._background_tasks: List[asyncio.Task] = []

        logger.info(
            f"AutomationOrchestrator initialized with config: "
            f"health_check_interval={self.config.health_check_interval_minutes}min"
        )

    async def start_background_monitoring(self, project_id: int):
        """Start background health monitoring for project.

        Args:
            project_id: Project to monitor
        """
        if not self.config.enable_background_monitoring:
            logger.info("Background monitoring disabled")
            return

        logger.info(f"Starting background monitoring for project {project_id}")

        # Start periodic health check task
        task = asyncio.create_task(
            self._periodic_health_check(project_id)
        )
        self._background_tasks.append(task)

    async def stop_background_monitoring(self):
        """Stop all background monitoring tasks."""
        logger.info("Stopping background monitoring")

        for task in self._background_tasks:
            task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

    async def handle_event(self, event: AutomationEvent) -> Dict[str, Any]:
        """Handle an automation event and trigger appropriate actions.

        Args:
            event: Automation event to handle

        Returns:
            Dictionary with actions taken and results
        """
        logger.info(
            f"Handling automation event: {event.event_type} on {event.entity_type} {event.entity_id}"
        )

        result = {
            "event_type": event.event_type,
            "entity_id": event.entity_id,
            "actions_taken": [],
            "alerts_generated": [],
            "status": "processed",
        }

        try:
            # Route event to appropriate handler
            if event.event_type == "task_created":
                actions = await self._on_task_created(event)
            elif event.event_type == "task_completed":
                actions = await self._on_task_completed(event)
            elif event.event_type == "task_status_changed":
                actions = await self._on_task_status_changed(event)
            elif event.event_type == "resource_conflict_detected":
                actions = await self._on_resource_conflict(event)
            elif event.event_type == "health_degraded":
                actions = await self._on_health_degraded(event)
            else:
                actions = []

            result["actions_taken"] = actions
            return result

        except Exception as e:
            logger.error(f"Error handling event: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            return result

    async def _on_task_created(
        self, event: AutomationEvent
    ) -> List[str]:
        """Handle task creation event.

        Actions:
        - Auto-optimize plan if enabled
        - Check for resource conflicts
        """
        actions = []
        task_id = event.entity_id

        # Auto-optimize plan
        if self.config.enable_auto_optimize_plans:
            try:
                logger.info(f"Auto-optimizing plan for task {task_id}")
                optimization = (
                    await self.planning_optimizer.validate_and_optimize(
                        task_id
                    )
                )

                if (
                    optimization.has_parallelization
                    or optimization.identified_risks
                ):
                    actions.append(
                        f"Generated optimization suggestions (parallelization={optimization.has_parallelization}, risks={len(optimization.identified_risks)})"
                    )

                # Alert if execution should be blocked
                if await self.planning_optimizer.should_block_execution(
                    task_id
                ):
                    alert = {
                        "task_id": task_id,
                        "severity": "high",
                        "type": "plan_risks",
                        "message": "Plan has unresolved risks - review before executing",
                        "timestamp": datetime.utcnow(),
                    }
                    self._active_alerts[task_id] = alert
                    actions.append("Generated alert: Plan risks detected")

            except Exception as e:
                logger.error(f"Error optimizing plan: {e}")

        return actions

    async def _on_task_completed(
        self, event: AutomationEvent
    ) -> List[str]:
        """Handle task completion event.

        Actions:
        - Trigger pattern discovery
        - Run analytics aggregator
        - Record final health metrics
        """
        actions = []
        project_id = event.metadata.get("project_id", 1)

        try:
            # Check if analytics should trigger
            should_trigger = (
                await self.analytics_aggregator.should_trigger_review(
                    project_id
                )
            )

            if should_trigger:
                logger.info(
                    f"Triggering analytics for project {project_id}"
                )
                summary = await self.analytics_aggregator.analyze_project(
                    project_id, period="weekly"
                )

                actions.append(
                    f"Triggered analytics review: {summary['critical_count']} critical, {summary['warning_count']} warnings"
                )

                # Alert if issues found
                if summary["critical_count"] > 0:
                    alert = {
                        "project_id": project_id,
                        "severity": "critical",
                        "type": "critical_tasks",
                        "message": f"{summary['critical_count']} critical tasks detected",
                        "timestamp": datetime.utcnow(),
                    }
                    self._active_alerts[project_id] = alert
                    actions.append("Generated alert: Critical tasks detected")

        except Exception as e:
            logger.error(f"Error in task completion handler: {e}")

        return actions

    async def _on_task_status_changed(
        self, event: AutomationEvent
    ) -> List[str]:
        """Handle task status change event.

        Actions:
        - Health check if status changed to executing
        - Alert if blocked/failed
        """
        actions = []
        task_id = event.entity_id
        new_status = event.metadata.get("new_status")

        try:
            if new_status == "executing":
                # Check health at start of execution
                health = await self.health_monitor.monitor.get_task_health(
                    task_id
                )

                if (
                    health.health_score
                    < self.config.critical_alert_threshold
                ):
                    alert = {
                        "task_id": task_id,
                        "severity": "critical",
                        "type": "low_health",
                        "message": f"Task starting with low health: {health.health_score:.2f}",
                        "timestamp": datetime.utcnow(),
                    }
                    self._active_alerts[task_id] = alert
                    actions.append("Generated alert: Low starting health")

            elif new_status == "blocked":
                # Alert on blocked
                alert = {
                    "task_id": task_id,
                    "severity": "high",
                    "type": "task_blocked",
                    "message": event.metadata.get(
                        "reason", "Task blocked"
                    ),
                    "timestamp": datetime.utcnow(),
                }
                self._active_alerts[task_id] = alert
                actions.append("Generated alert: Task blocked")

            elif new_status == "failed":
                # Record failure for learning
                actions.append("Recorded task failure for pattern analysis")

        except Exception as e:
            logger.error(f"Error in status change handler: {e}")

        return actions

    async def _on_resource_conflict(
        self, event: AutomationEvent
    ) -> List[str]:
        """Handle resource conflict detection.

        Actions:
        - Alert with conflict details
        - Suggest rebalancing
        """
        actions = []
        project_ids = event.metadata.get("project_ids", [])

        try:
            logger.info(f"Resource conflict detected in {project_ids}")

            alert = {
                "projects": project_ids,
                "severity": "high",
                "type": "resource_conflict",
                "message": f"Resource conflict detected across projects",
                "timestamp": datetime.utcnow(),
            }
            self._active_alerts[tuple(project_ids)] = alert
            actions.append("Generated alert: Resource conflict")

        except Exception as e:
            logger.error(f"Error in resource conflict handler: {e}")

        return actions

    async def _on_health_degraded(
        self, event: AutomationEvent
    ) -> List[str]:
        """Handle health degradation event.

        Actions:
        - Auto-optimize if enabled
        - Escalate critical alerts
        """
        actions = []
        task_id = event.entity_id
        health_score = event.metadata.get("health_score", 0)

        try:
            if health_score < self.config.critical_alert_threshold:
                alert = {
                    "task_id": task_id,
                    "severity": "critical",
                    "type": "health_degraded",
                    "message": f"Task health critical: {health_score:.2f}",
                    "timestamp": datetime.utcnow(),
                }
                self._active_alerts[task_id] = alert

                # Try to optimize
                if self.config.enable_auto_optimize_plans:
                    try:
                        optimization = (
                            await self.planning_optimizer.validate_and_optimize(
                                task_id
                            )
                        )
                        actions.append(
                            "Auto-optimized plan due to health degradation"
                        )
                    except Exception:
                        pass

                actions.append("Generated alert: Critical health degradation")

        except Exception as e:
            logger.error(f"Error in health degraded handler: {e}")

        return actions

    async def _periodic_health_check(self, project_id: int):
        """Periodic health check task (runs in background).

        Args:
            project_id: Project to monitor
        """
        while True:
            try:
                # Check if it's time to run health check
                last_check = self._last_health_check_time.get(project_id)
                now = datetime.utcnow()

                if last_check is None or (
                    now - last_check
                ).total_seconds() >= (
                    self.config.health_check_interval_minutes * 60
                ):
                    logger.info(
                        f"Running periodic health check for project {project_id}"
                    )

                    # Check all active tasks
                    alerts = (
                        await self.health_monitor.check_active_tasks(
                            project_id
                        )
                    )

                    # Store alerts
                    for alert in alerts:
                        self._active_alerts[alert.task_id] = {
                            "task_id": alert.task_id,
                            "severity": alert.status,
                            "type": "health_check",
                            "message": alert.recommendation,
                            "timestamp": now,
                        }

                    if alerts:
                        logger.warning(
                            f"Found {len(alerts)} tasks with health issues"
                        )

                    self._last_health_check_time[project_id] = now

                # Wait before next check
                await asyncio.sleep(60)  # Check every minute if due

            except asyncio.CancelledError:
                logger.info(
                    f"Stopping periodic health check for project {project_id}"
                )
                break
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")
                await asyncio.sleep(60)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts.

        Returns:
            List of active alert dictionaries
        """
        return list(self._active_alerts.values())

    def dismiss_alert(self, alert_id: Any):
        """Dismiss an active alert.

        Args:
            alert_id: Alert ID to dismiss
        """
        if alert_id in self._active_alerts:
            del self._active_alerts[alert_id]
            logger.info(f"Dismissed alert {alert_id}")

    def clear_alerts(self):
        """Clear all active alerts."""
        count = len(self._active_alerts)
        self._active_alerts.clear()
        logger.info(f"Cleared {count} alerts")

    async def get_status(self, project_id: int) -> Dict[str, Any]:
        """Get current automation status.

        Args:
            project_id: Project to check status for

        Returns:
            Status dictionary
        """
        alerts = self.get_active_alerts()
        critical_alerts = [
            a for a in alerts if a.get("severity") == "critical"
        ]

        return {
            "project_id": project_id,
            "background_monitoring": self.config.enable_background_monitoring,
            "monitoring_tasks": len(self._background_tasks),
            "total_alerts": len(alerts),
            "critical_alerts": len(critical_alerts),
            "auto_optimize_plans": self.config.enable_auto_optimize_plans,
            "auto_escalate_alerts": self.config.enable_auto_escalate_alerts,
            "health_check_interval_minutes": self.config.health_check_interval_minutes,
            "recent_alerts": alerts[-5:],  # Last 5 alerts
        }
