"""Idempotency Tracker for Hook Safety.

Prevents duplicate hook executions by tracking:
- Hook invocation fingerprints (content hash + context)
- Execution window (prevents re-execution within N seconds)
- Idempotency keys for explicit duplicate detection
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IdempotencyRecord:
    """Record of a single hook execution."""
    hook_id: str
    invocation_fingerprint: str
    execution_time: datetime
    result: Optional[Any] = None
    is_duplicate: bool = False


class IdempotencyTracker:
    """Track hook executions to prevent duplicates.

    Uses three strategies:
    1. Content fingerprinting: Hash of hook input to detect identical calls
    2. Time windows: Prevent re-execution within grace period
    3. Explicit keys: User-provided idempotency keys for custom deduplication

    Attributes:
        execution_window_seconds: Grace period after execution (default: 30)
        max_history: Maximum executions to track (default: 1000)
    """

    def __init__(self, execution_window_seconds: int = 30, max_history: int = 1000):
        """Initialize idempotency tracker.

        Args:
            execution_window_seconds: Grace period to consider execution duplicate
            max_history: Maximum execution records to keep in memory
        """
        self.execution_window_seconds = execution_window_seconds
        self.max_history = max_history
        self._execution_history: Dict[str, list] = {}  # hook_id -> list of records
        self._idempotency_keys: Dict[str, IdempotencyRecord] = {}  # key -> record
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _compute_fingerprint(hook_id: str, context: Dict[str, Any]) -> str:
        """Compute fingerprint of hook invocation.

        Creates hash from hook_id and serialized context to detect
        identical invocations.

        Args:
            hook_id: Hook identifier
            context: Hook execution context

        Returns:
            SHA256 fingerprint (hex string)
        """
        try:
            # Serialize context to canonical JSON for consistency
            context_json = json.dumps(context, sort_keys=True, default=str)
            combined = f"{hook_id}:{context_json}"
            return hashlib.sha256(combined.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute fingerprint: {e}")
            return ""

    def is_duplicate(
        self,
        hook_id: str,
        context: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> bool:
        """Check if hook execution is a duplicate.

        Checks in order:
        1. Explicit idempotency key (if provided)
        2. Content fingerprint within execution window
        3. Time-window duplicates

        Args:
            hook_id: Hook identifier
            context: Hook execution context
            idempotency_key: Optional explicit idempotency key

        Returns:
            True if execution appears to be duplicate
        """
        # Check explicit idempotency key first
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                record = self._idempotency_keys[idempotency_key]
                age = (datetime.now() - record.execution_time).total_seconds()

                if age < self.execution_window_seconds:
                    self.logger.debug(
                        f"Idempotency key {idempotency_key} found within window ({age:.1f}s)"
                    )
                    return True

        # Check content fingerprint
        fingerprint = self._compute_fingerprint(hook_id, context)
        if not fingerprint:
            return False

        if hook_id in self._execution_history:
            for record in self._execution_history[hook_id]:
                if record.invocation_fingerprint == fingerprint:
                    age = (datetime.now() - record.execution_time).total_seconds()
                    if age < self.execution_window_seconds:
                        self.logger.debug(
                            f"Duplicate execution detected for {hook_id} "
                            f"(fingerprint match, age={age:.1f}s)"
                        )
                        return True

        return False

    def record_execution(
        self,
        hook_id: str,
        context: Dict[str, Any],
        result: Optional[Any] = None,
        idempotency_key: Optional[str] = None
    ) -> None:
        """Record successful hook execution.

        Args:
            hook_id: Hook identifier
            context: Hook execution context
            result: Execution result (for debugging)
            idempotency_key: Optional idempotency key for explicit deduplication
        """
        fingerprint = self._compute_fingerprint(hook_id, context)
        now = datetime.now()

        record = IdempotencyRecord(
            hook_id=hook_id,
            invocation_fingerprint=fingerprint,
            execution_time=now,
            result=result,
            is_duplicate=False
        )

        # Store in history
        if hook_id not in self._execution_history:
            self._execution_history[hook_id] = []

        self._execution_history[hook_id].append(record)

        # Prune old executions
        self._execution_history[hook_id] = [
            r for r in self._execution_history[hook_id]
            if (now - r.execution_time).total_seconds() < self.execution_window_seconds * 2
        ]

        # Limit total history
        if len(self._execution_history[hook_id]) > self.max_history:
            self._execution_history[hook_id] = self._execution_history[hook_id][-self.max_history:]

        # Store idempotency key if provided
        if idempotency_key:
            self._idempotency_keys[idempotency_key] = record

            # Prune old idempotency keys
            old_keys = [
                k for k, r in self._idempotency_keys.items()
                if (now - r.execution_time).total_seconds() >= self.execution_window_seconds * 2
            ]
            for k in old_keys:
                del self._idempotency_keys[k]

        self.logger.debug(f"Recorded execution for {hook_id} (key={idempotency_key})")

    def get_last_execution(self, hook_id: str) -> Optional[IdempotencyRecord]:
        """Get last recorded execution for hook.

        Args:
            hook_id: Hook identifier

        Returns:
            Last execution record or None
        """
        if hook_id not in self._execution_history:
            return None

        if not self._execution_history[hook_id]:
            return None

        return self._execution_history[hook_id][-1]

    def get_execution_count(self, hook_id: str, within_seconds: Optional[int] = None) -> int:
        """Get execution count for hook.

        Args:
            hook_id: Hook identifier
            within_seconds: Only count executions within this time window

        Returns:
            Number of executions
        """
        if hook_id not in self._execution_history:
            return 0

        records = self._execution_history[hook_id]

        if within_seconds is None:
            return len(records)

        now = datetime.now()
        cutoff = now - timedelta(seconds=within_seconds)
        return sum(1 for r in records if r.execution_time > cutoff)

    def clear_history(self, hook_id: Optional[str] = None) -> None:
        """Clear execution history.

        Args:
            hook_id: If provided, clear only this hook's history. Otherwise clear all.
        """
        if hook_id:
            if hook_id in self._execution_history:
                del self._execution_history[hook_id]
                self.logger.debug(f"Cleared history for {hook_id}")
        else:
            self._execution_history.clear()
            self._idempotency_keys.clear()
            self.logger.debug("Cleared all execution history")

    def get_stats(self) -> Dict[str, Any]:
        """Get idempotency tracking statistics.

        Returns:
            Dictionary with tracking stats
        """
        now = datetime.now()
        total_executions = sum(len(records) for records in self._execution_history.values())
        active_hooks = len(self._execution_history)
        recent_executions = sum(
            1 for records in self._execution_history.values()
            for r in records
            if (now - r.execution_time).total_seconds() < self.execution_window_seconds
        )

        return {
            'total_executions': total_executions,
            'active_hooks': active_hooks,
            'recent_executions': recent_executions,
            'tracked_idempotency_keys': len(self._idempotency_keys),
            'execution_window_seconds': self.execution_window_seconds
        }
