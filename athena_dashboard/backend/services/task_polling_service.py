"""
Task polling service for real-time task updates without WebSocket.

Polls Phase 3 task data at regular intervals and notifies subscribers of changes.
Safer alternative to WebSocket with proper connection lifecycle management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


class TaskPollingService:
    """
    Polls task data from Phase 3 endpoints and broadcasts changes to subscribers.

    Uses polling instead of WebSocket for reliability:
    - No connection leaks (polling is stateless)
    - Automatic reconnection (just retry the HTTP request)
    - Simple to test and debug
    - Compatible with existing infrastructure
    """

    def __init__(self, poll_interval_seconds: int = 5, history_size: int = 100):
        """
        Initialize task polling service.

        Args:
            poll_interval_seconds: How often to poll task endpoints
            history_size: Number of updates to keep in history
        """
        self.poll_interval = poll_interval_seconds
        self.history_size = history_size
        self.is_running = False

        # Last known state (for change detection)
        self.last_state = {
            "tasks": {},
            "predictions": {},
            "suggestions": {},
            "metrics": {},
        }

        # History of changes
        self.update_history: List[Dict[str, Any]] = []

        # Subscribers (callbacks that get called when changes happen)
        self.subscribers: Dict[str, List[Callable]] = {
            "task_status": [],
            "predictions": [],
            "suggestions": [],
            "metrics": [],
            "all": [],  # Called for any update
        }

        # Polling task reference
        self._poll_task: Optional[asyncio.Task] = None

    def subscribe(
        self,
        event_type: str,  # task_status | predictions | suggestions | metrics | all
        callback: Callable
    ) -> str:
        """
        Subscribe to task update notifications.

        Args:
            event_type: Type of events to subscribe to
            callback: Async function to call when updates occur

        Returns:
            Subscription ID (can be used to unsubscribe)
        """
        if event_type not in self.subscribers:
            event_type = "all"

        self.subscribers[event_type].append(callback)

        # Return a subscription ID (for simplicity, just the index)
        return f"{event_type}_{len(self.subscribers[event_type])}"

    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """
        Unsubscribe from task update notifications.

        Args:
            event_type: Event type to unsubscribe from
            callback: The callback function to remove

        Returns:
            True if callback was found and removed
        """
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
                return True
            except ValueError:
                return False
        return False

    async def start(self, data_loader=None) -> None:
        """
        Start the polling service.

        Args:
            data_loader: Optional data loader for polling task data
        """
        if self.is_running:
            logger.warning("Task polling service already running")
            return

        self.is_running = True
        self.data_loader = data_loader
        logger.info(f"Starting task polling service (interval: {self.poll_interval}s)")

        # Start polling loop
        self._poll_task = asyncio.create_task(self._polling_loop())

    async def stop(self) -> None:
        """Stop the polling service."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping task polling service")

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

    async def _polling_loop(self) -> None:
        """Main polling loop - runs continuously when service is active."""
        while self.is_running:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._poll_task_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                # Continue polling even if one cycle fails

    async def _poll_task_data(self) -> None:
        """Poll task data from Phase 3 endpoints and detect changes."""
        try:
            # In a real implementation, this would query the task routes
            # For now, we'll simulate polling by checking for state changes

            # Simulate fetching data
            current_state = {
                "tasks": await self._get_mock_tasks(),
                "predictions": await self._get_mock_predictions(),
                "suggestions": await self._get_mock_suggestions(),
                "metrics": await self._get_mock_metrics(),
            }

            # Detect changes
            changes = self._detect_changes(current_state)

            # Notify subscribers if there are changes
            if changes:
                await self._notify_subscribers(changes)

                # Update state
                self.last_state = current_state

                # Record in history
                self._record_update(changes)

        except Exception as e:
            logger.error(f"Error polling task data: {e}")

    def _detect_changes(self, new_state: Dict) -> Dict[str, Any]:
        """
        Detect what changed between last state and new state.

        Returns:
            Dictionary of detected changes
        """
        changes = {}

        # Check task status changes
        if new_state.get("tasks") != self.last_state.get("tasks"):
            changes["task_status"] = {
                "previous": self.last_state.get("tasks"),
                "current": new_state.get("tasks"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Check prediction changes
        if new_state.get("predictions") != self.last_state.get("predictions"):
            changes["predictions"] = {
                "previous": self.last_state.get("predictions"),
                "current": new_state.get("predictions"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Check suggestion changes
        if new_state.get("suggestions") != self.last_state.get("suggestions"):
            changes["suggestions"] = {
                "previous": self.last_state.get("suggestions"),
                "current": new_state.get("suggestions"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Check metric changes
        if new_state.get("metrics") != self.last_state.get("metrics"):
            changes["metrics"] = {
                "previous": self.last_state.get("metrics"),
                "current": new_state.get("metrics"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        return changes

    async def _notify_subscribers(self, changes: Dict[str, Any]) -> None:
        """
        Notify all relevant subscribers of changes.

        Args:
            changes: Dictionary of detected changes
        """
        # Notify specific event subscribers
        for event_type, change in changes.items():
            if event_type in self.subscribers:
                for callback in self.subscribers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(change)
                        else:
                            callback(change)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")

        # Also notify "all" subscribers
        for callback in self.subscribers.get("all", []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(changes)
                else:
                    callback(changes)
            except Exception as e:
                logger.error(f"Error in 'all' subscriber callback: {e}")

    def _record_update(self, changes: Dict[str, Any]) -> None:
        """Record update in history."""
        self.update_history.append({
            "timestamp": datetime.utcnow(),
            "changes": changes,
        })

        # Keep history size bounded
        if len(self.update_history) > self.history_size:
            self.update_history.pop(0)

    async def _get_mock_tasks(self) -> Dict:
        """Mock task data (will be replaced with real API calls)."""
        return {
            "total": 2,
            "tasks": [
                {"id": "t1", "status": "in_progress"},
                {"id": "t2", "status": "pending"},
            ]
        }

    async def _get_mock_predictions(self) -> Dict:
        """Mock prediction data."""
        return {
            "total": 2,
            "predictions": [
                {"id": "t1", "confidence": 0.87},
                {"id": "t2", "confidence": 0.91},
            ]
        }

    async def _get_mock_suggestions(self) -> Dict:
        """Mock suggestion data."""
        return {
            "suggestions": [
                {"id": "t2", "confidence": 0.92},
            ]
        }

    async def _get_mock_metrics(self) -> Dict:
        """Mock metrics data."""
        return {
            "completion_rate": 0.64,
            "accuracy": 0.85,
        }

    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get update history."""
        if limit:
            return self.update_history[-limit:]
        return self.update_history

    def get_last_update(self) -> Optional[Dict]:
        """Get the most recent update."""
        if self.update_history:
            return self.update_history[-1]
        return None

    def get_state(self) -> Dict:
        """Get current cached state."""
        return self.last_state.copy()
