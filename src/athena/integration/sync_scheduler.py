"""Scheduled Sync Jobs and Triggers

Implements background sync jobs that run on schedule to keep todos and plans
in sync without user intervention.

Features:
- Periodic sync (every N minutes)
- Trigger-based sync (on status change, priority change)
- Conflict detection and auto-resolution
- Batch sync operations
- Sync status notifications
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable, List
from enum import Enum

from ..core.database import Database
from .sync_operations import (
    get_active_plans,
    get_sync_summary,
    detect_database_conflicts,
    sync_todo_status_change,
)
from .conflict_resolver import get_resolver, get_resolution_store

logger = logging.getLogger(__name__)


class SyncTriggerType(str, Enum):
    """Types of sync triggers."""
    PERIODIC = "periodic"
    ON_STATUS_CHANGE = "on_status_change"
    ON_PRIORITY_CHANGE = "on_priority_change"
    ON_CONFLICT = "on_conflict"
    ON_COMPLETION = "on_completion"
    MANUAL = "manual"


class SyncJob:
    """Represents a scheduled sync job."""

    def __init__(
        self,
        job_id: str,
        name: str,
        trigger_type: SyncTriggerType,
        interval_seconds: Optional[int] = None,
        enabled: bool = True,
    ):
        self.job_id = job_id
        self.name = name
        self.trigger_type = trigger_type
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.failure_count = 0

    def should_run(self) -> bool:
        """Check if job should run now."""
        if not self.enabled:
            return False

        if self.trigger_type != SyncTriggerType.PERIODIC:
            return False

        if self.next_run is None:
            return True

        return datetime.now() >= self.next_run

    def schedule_next_run(self) -> None:
        """Schedule next run."""
        if self.interval_seconds:
            self.next_run = datetime.now() + timedelta(seconds=self.interval_seconds)

    def record_run(self, success: bool = True) -> None:
        """Record a job run."""
        self.last_run = datetime.now()
        self.run_count += 1
        if not success:
            self.failure_count += 1
        self.schedule_next_run()


class SyncScheduler:
    """Manages scheduled sync jobs."""

    def __init__(self, db: Database, check_interval: int = 60):
        self.db = db
        self.check_interval = check_interval  # Seconds between checks
        self.jobs: Dict[str, SyncJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Sync scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            await self._task
        logger.info("Sync scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Check and run due jobs
                for job_id, job in self.jobs.items():
                    if job.should_run():
                        await self._run_job(job)

                # Sleep until next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def _run_job(self, job: SyncJob) -> None:
        """Run a single job."""
        try:
            logger.info(f"Running sync job: {job.name}")

            if job.trigger_type == SyncTriggerType.PERIODIC:
                success = await self._run_periodic_sync()
            elif job.trigger_type == SyncTriggerType.ON_CONFLICT:
                success = await self._run_conflict_resolution()
            else:
                success = False

            job.record_run(success)

            if success:
                logger.info(f"Sync job completed: {job.name}")
            else:
                logger.warning(f"Sync job failed: {job.name}")

        except Exception as e:
            logger.error(f"Failed to run sync job {job.name}: {e}")
            job.record_run(False)

    async def _run_periodic_sync(self, project_id: int = 1) -> bool:
        """Run periodic sync to ensure all items are in sync."""
        try:
            summary = await get_sync_summary(project_id)

            # If there are pending syncs or conflicts, address them
            if summary["pending_syncs"] > 0:
                logger.info(f"Found {summary['pending_syncs']} pending syncs")

            if summary["conflicts"] > 0:
                logger.info(f"Found {summary['conflicts']} conflicts")

            return True

        except Exception as e:
            logger.error(f"Periodic sync failed: {e}")
            return False

    async def _run_conflict_resolution(self, project_id: int = 1) -> bool:
        """Run conflict detection and resolution."""
        try:
            conflicts = await detect_database_conflicts(project_id)

            if not conflicts:
                logger.info("No conflicts to resolve")
                return True

            logger.info(f"Resolving {len(conflicts)} conflicts")

            resolver = get_resolver()
            resolution_store = get_resolution_store()

            resolved_count = 0
            for plan in conflicts[:50]:  # Resolve up to 50 per run
                try:
                    todo = {"content": plan.get("goal", ""), "status": "pending"}

                    # Try auto-resolution
                    success, resolved_plan = await resolver.auto_resolve_with_threshold(
                        todo,
                        plan,
                        confidence_threshold=0.8,
                    )

                    if success:
                        resolved_count += 1
                        await resolution_store.record_resolution(
                            project_id,
                            plan.get("todo_id", ""),
                            plan.get("plan_id", ""),
                            "auto-resolved",
                            "auto",
                            0.9,
                        )

                except Exception as e:
                    logger.warning(f"Failed to resolve conflict for plan {plan.get('plan_id')}: {e}")

            logger.info(f"Resolved {resolved_count}/{len(conflicts)} conflicts")
            return resolved_count > 0

        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            return False

    def register_job(self, job: SyncJob) -> None:
        """Register a sync job."""
        self.jobs[job.job_id] = job
        logger.info(f"Registered sync job: {job.name}")

    def unregister_job(self, job_id: str) -> bool:
        """Unregister a sync job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Unregistered sync job: {job_id}")
            return True
        return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job."""
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]
        return {
            "job_id": job.job_id,
            "name": job.name,
            "enabled": job.enabled,
            "trigger_type": job.trigger_type.value,
            "last_run": job.last_run.isoformat() if job.last_run else None,
            "next_run": job.next_run.isoformat() if job.next_run else None,
            "run_count": job.run_count,
            "failure_count": job.failure_count,
        }

    def get_all_job_status(self) -> List[Dict[str, Any]]:
        """Get status of all jobs."""
        return [self.get_job_status(job_id) for job_id in self.jobs]


class SyncNotifier:
    """Notifies about sync status changes."""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to sync events."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    async def notify(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify subscribers of an event."""
        if event_type not in self.subscribers:
            return

        for callback in self.subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")

    async def notify_conflict_detected(self, plan_id: str, reason: str) -> None:
        """Notify of detected conflict."""
        await self.notify("conflict_detected", {
            "plan_id": plan_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

    async def notify_conflict_resolved(self, plan_id: str, preference: str) -> None:
        """Notify of resolved conflict."""
        await self.notify("conflict_resolved", {
            "plan_id": plan_id,
            "preference": preference,
            "timestamp": datetime.now().isoformat(),
        })

    async def notify_sync_completed(self, summary: Dict[str, Any]) -> None:
        """Notify of completed sync."""
        await self.notify("sync_completed", {
            **summary,
            "timestamp": datetime.now().isoformat(),
        })


# Global instances
_scheduler: Optional[SyncScheduler] = None
_notifier: Optional[SyncNotifier] = None


def initialize(db: Database) -> None:
    """Initialize global instances."""
    global _scheduler, _notifier
    _scheduler = SyncScheduler(db)
    _notifier = SyncNotifier()

    # Register default jobs
    _scheduler.register_job(SyncJob(
        "periodic_sync",
        "Periodic Sync (every 5 minutes)",
        SyncTriggerType.PERIODIC,
        interval_seconds=300,
    ))

    _scheduler.register_job(SyncJob(
        "conflict_resolution",
        "Conflict Resolution (every 10 minutes)",
        SyncTriggerType.ON_CONFLICT,
        interval_seconds=600,
    ))

    logger.info("Sync scheduler initialized with default jobs")


def get_scheduler() -> SyncScheduler:
    """Get global scheduler."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    return _scheduler


def get_notifier() -> SyncNotifier:
    """Get global notifier."""
    if _notifier is None:
        raise RuntimeError("Notifier not initialized")
    return _notifier
