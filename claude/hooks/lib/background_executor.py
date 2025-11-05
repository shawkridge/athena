#!/usr/bin/env python3
"""
Background Hook Executor - Phase 8 Implementation

Executes non-critical hooks in background threads/processes.

Features:
- Schedule hooks to run in background
- Non-blocking execution
- Optional result collection via futures
- Configurable delays
- Graceful shutdown

Usage:
    executor = BackgroundExecutor()

    # Schedule hook to run in background
    future = executor.schedule_background_hook(
        "post-health-check",
        hook_input,
        delay_ms=100
    )

    # Optionally wait for result
    result = future.result(timeout=5.0)

    # Wait for all background hooks on shutdown
    executor.wait_for_all(timeout_ms=5000)
"""

import subprocess
import json
import logging
import time
import threading
import queue
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("background_executor")


class BackgroundTaskStatus(Enum):
    """Status of background task"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BackgroundTask:
    """Background task information"""
    task_id: str
    hook_name: str
    hook_input: Dict
    status: BackgroundTaskStatus
    scheduled_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    delay_ms: int = 0
    timeout_ms: int = 3000
    result: Optional[str] = None
    error: Optional[str] = None

    def duration_ms(self) -> int:
        """Get task duration in milliseconds"""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at) * 1000)
        return 0

    def total_time_ms(self) -> int:
        """Get total time from scheduling to completion"""
        if self.completed_at:
            return int((self.completed_at - self.scheduled_at) * 1000)
        return 0


class BackgroundExecutor:
    """
    Executes hooks in background with optional result collection

    Design:
    - Use ThreadPoolExecutor for I/O-bound hooks
    - Non-blocking scheduling
    - Optional result collection via futures
    - Graceful shutdown with timeout
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize background executor

        Args:
            max_workers: Maximum number of background threads
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="hook-bg")
        self.active_tasks: Dict[str, BackgroundTask] = {}
        self.completed_tasks: list = []
        self.task_counter = 0
        self.lock = threading.Lock()

    def schedule_background_hook(self, hook_name: str, hook_file: str,
                                 hook_input: Dict,
                                 delay_ms: int = 0,
                                 timeout_ms: int = 3000) -> Future:
        """
        Schedule hook to run in background

        Args:
            hook_name: Name of hook
            hook_file: Path to hook script
            hook_input: Input JSON for hook
            delay_ms: Delay before execution (milliseconds)
            timeout_ms: Execution timeout (milliseconds)

        Returns:
            Future object to optionally get result
        """
        with self.lock:
            self.task_counter += 1
            task_id = f"{hook_name}-{self.task_counter}"

        task = BackgroundTask(
            task_id=task_id,
            hook_name=hook_name,
            hook_input=hook_input,
            status=BackgroundTaskStatus.QUEUED,
            scheduled_at=time.time(),
            delay_ms=delay_ms,
            timeout_ms=timeout_ms
        )

        with self.lock:
            self.active_tasks[task_id] = task

        # Submit to executor
        future = self.executor.submit(
            self._run_background_task,
            task,
            hook_file
        )

        logger.debug(f"Scheduled background hook: {hook_name} (task_id={task_id}, delay={delay_ms}ms)")

        return future

    def _run_background_task(self, task: BackgroundTask, hook_file: str) -> Dict:
        """
        Run background task (executed by ThreadPoolExecutor)

        Args:
            task: Background task
            hook_file: Path to hook script

        Returns:
            Result dictionary
        """
        try:
            # Apply delay if specified
            if task.delay_ms > 0:
                time.sleep(task.delay_ms / 1000.0)

            task.status = BackgroundTaskStatus.RUNNING
            task.started_at = time.time()

            logger.debug(f"Running background hook: {task.hook_name}")

            # Execute hook
            input_data = json.dumps(task.hook_input)
            timeout_sec = task.timeout_ms / 1000.0

            result = subprocess.run(
                ["/bin/bash", hook_file],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )

            task.completed_at = time.time()

            if result.returncode == 0:
                task.status = BackgroundTaskStatus.COMPLETED
                task.result = result.stdout
                logger.debug(f"Background hook completed: {task.hook_name}")
            else:
                task.status = BackgroundTaskStatus.FAILED
                task.error = result.stderr
                logger.warning(f"Background hook failed: {task.hook_name} (exit_code={result.returncode})")

            return {
                "hook_name": task.hook_name,
                "status": task.status.value,
                "duration_ms": task.duration_ms(),
                "exit_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            task.completed_at = time.time()
            task.status = BackgroundTaskStatus.TIMEOUT
            task.error = "Execution timeout"
            logger.error(f"Background hook timeout: {task.hook_name}")
            return {
                "hook_name": task.hook_name,
                "status": "timeout",
                "duration_ms": task.duration_ms()
            }

        except Exception as e:
            task.completed_at = time.time()
            task.status = BackgroundTaskStatus.FAILED
            task.error = str(e)
            logger.error(f"Background hook error: {task.hook_name}: {e}")
            return {
                "hook_name": task.hook_name,
                "status": "failed",
                "error": str(e)
            }

        finally:
            # Move task to completed
            with self.lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
                self.completed_tasks.append(task)

    def wait_for_all(self, timeout_ms: int = 5000) -> Dict:
        """
        Wait for all background hooks to complete

        Call this on shutdown/session-end to ensure all hooks finish.

        Args:
            timeout_ms: Maximum time to wait in milliseconds

        Returns:
            Summary of completed tasks
        """
        timeout_sec = timeout_ms / 1000.0
        logger.info(f"Waiting for {len(self.active_tasks)} background hooks (timeout={timeout_ms}ms)")

        start_time = time.time()
        remaining = dict(self.active_tasks)

        while remaining and (time.time() - start_time) < timeout_sec:
            completed_in_this_iteration = []

            with self.lock:
                for task_id in list(remaining.keys()):
                    if task_id not in self.active_tasks:
                        completed_in_this_iteration.append(task_id)
                        del remaining[task_id]

            if completed_in_this_iteration:
                logger.debug(f"Completed {len(completed_in_this_iteration)} background tasks")

            if remaining:
                time.sleep(0.1)  # Check every 100ms

        elapsed_ms = int((time.time() - start_time) * 1000)

        if remaining:
            logger.warning(f"Timeout waiting for background hooks: {len(remaining)} still running")
        else:
            logger.info(f"All background hooks completed in {elapsed_ms}ms")

        return self.get_stats()

    def get_active_tasks(self) -> Dict[str, BackgroundTask]:
        """Get currently active background tasks"""
        with self.lock:
            return dict(self.active_tasks)

    def get_completed_tasks(self) -> list:
        """Get all completed tasks"""
        with self.lock:
            return list(self.completed_tasks)

    def get_stats(self) -> Dict:
        """Get executor statistics"""
        with self.lock:
            completed = self.completed_tasks
            active = len(self.active_tasks)

            if not completed:
                return {
                    "active_tasks": active,
                    "completed_tasks": 0,
                    "failed_tasks": 0,
                    "avg_duration_ms": 0,
                    "total_duration_ms": 0
                }

            failed = sum(1 for t in completed if t.status == BackgroundTaskStatus.FAILED)
            total_duration = sum(t.duration_ms() for t in completed)
            avg_duration = total_duration / len(completed) if completed else 0

            return {
                "active_tasks": active,
                "completed_tasks": len(completed),
                "failed_tasks": failed,
                "avg_duration_ms": int(avg_duration),
                "total_duration_ms": int(total_duration),
                "by_status": {
                    status.value: sum(1 for t in completed if t.status == status)
                    for status in BackgroundTaskStatus
                }
            }

    def shutdown(self, wait: bool = True, timeout_sec: float = 5.0):
        """
        Shutdown executor gracefully

        Args:
            wait: Wait for background hooks to complete
            timeout_sec: Maximum time to wait
        """
        logger.info("Shutting down background executor")

        if wait:
            self.wait_for_all(int(timeout_sec * 1000))

        self.executor.shutdown(wait=wait, timeout=timeout_sec)
        logger.info("Background executor shutdown complete")


class SmartBackgroundScheduler:
    """
    Smart scheduler for background hooks

    Automatically schedules hooks marked as background=true
    in the manifest with optimal delays and timeout values.
    """

    def __init__(self, manifest: Dict, executor: Optional[BackgroundExecutor] = None):
        """
        Initialize scheduler

        Args:
            manifest: Hook manifest dictionary
            executor: BackgroundExecutor instance (creates new if None)
        """
        self.manifest = manifest
        self.executor = executor or BackgroundExecutor()
        self.hook_map = {h["name"]: h for h in manifest.get("hooks", [])}

    def schedule_background_hooks(self, phase: str, hook_input: Dict) -> Dict[str, Future]:
        """
        Schedule all background hooks for a phase

        Args:
            phase: Phase name
            hook_input: Input for hooks

        Returns:
            Dictionary of hook_name -> Future
        """
        futures = {}

        for hook in self.manifest.get("hooks", []):
            if hook.get("phase") != phase:
                continue

            if not hook.get("background", False):
                continue

            hook_name = hook["name"]
            hook_file = hook["filePath"]
            delay_ms = hook.get("background_delay_ms", 0)
            timeout_ms = hook.get("timeout", 3000)

            future = self.executor.schedule_background_hook(
                hook_name,
                hook_file,
                hook_input,
                delay_ms=delay_ms,
                timeout_ms=timeout_ms
            )

            futures[hook_name] = future
            logger.debug(f"Scheduled background hook: {hook_name}")

        return futures

    def get_stats(self) -> Dict:
        """Get scheduler statistics"""
        return self.executor.get_stats()

    def shutdown(self, timeout_sec: float = 5.0):
        """Shutdown scheduler"""
        self.executor.shutdown(wait=True, timeout_sec=timeout_sec)


def main():
    """CLI for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Background Executor")
    parser.add_argument("--test", action="store_true", help="Run test")

    args = parser.parse_args()

    if args.test:
        # Simple test
        executor = BackgroundExecutor(max_workers=2)

        # Simulate background task
        def dummy_hook():
            time.sleep(0.5)
            return {"result": "success"}

        future = executor.executor.submit(dummy_hook)
        result = future.result(timeout=2.0)
        print(f"Test result: {result}")

        stats = executor.get_stats()
        print(f"Stats: {json.dumps(stats, indent=2)}")

        executor.shutdown()


if __name__ == "__main__":
    main()
