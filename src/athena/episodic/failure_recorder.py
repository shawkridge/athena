"""Failure Event Recorder - Captures system failures into episodic memory.

Design Principle: "Crash hard, fail loudly" means failures must be:
1. **Visible** - Logged to stdout/stderr
2. **Recordable** - Stored in episodic memory (persistent)
3. **Learnable** - Consolidatable into patterns
4. **Discoverable** - Searchable from memory system

Without recording failures, they disappear when logs rotate. With recording,
the system learns from every failure and improves over time.

Example Usage:
```python
from athena.episodic.failure_recorder import FailureEventRecorder

recorder = FailureEventRecorder(episodic_store, db)

# Record an import failure
await recorder.record_failure(
    component="episodic.sources",
    failure_type="import_error",
    message="Failed to import SlackEventSource",
    details={
        "dependency": "slack-sdk",
        "solution": "pip install slack-sdk"
    },
    severity="warning"
)

# Record data inconsistency
await recorder.record_failure(
    component="episodic.store",
    failure_type="data_corruption",
    message="Unknown evidence_type in database",
    details={
        "event_id": 12345,
        "invalid_value": "UNKNOWN_TYPE",
        "field": "evidence_type"
    },
    severity="warning"
)

# Record permission failure
await recorder.record_failure(
    component="core.production",
    failure_type="permission_error",
    message="Failed to cleanup expired locks",
    details={
        "table": "advisory_locks",
        "operation": "DELETE"
    },
    severity="error"
)
```

The consolidation system will automatically:
- Extract patterns: "Missing dependencies cause 40% of failures"
- Create strategies: "Check dependencies before importing"
- Update knowledge graph: Link failures to root causes
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .models import EpisodicEvent, EventType
from .store import EpisodicStore
from ..core.database import Database


@dataclass
class FailureRecord:
    """Represents a recorded failure for consolidation learning."""

    component: str  # e.g., "episodic.sources", "core.production"
    failure_type: str  # e.g., "import_error", "data_corruption", "permission_error"
    message: str  # Human-readable failure description
    severity: str  # "info", "warning", "error", "critical"
    details: Dict[str, Any]  # Structured failure data for analysis
    timestamp: int  # Unix timestamp


class FailureEventRecorder:
    """Records failures into episodic memory for learning and analysis.

    This enables the memory system to:
    1. Learn what fails and why
    2. Extract patterns from failure modes
    3. Improve over time by avoiding known failure causes
    4. Provide operators with searchable failure history
    """

    def __init__(self, episodic_store: EpisodicStore, db: Database):
        """Initialize failure recorder.

        Args:
            episodic_store: EpisodicStore for recording events
            db: Database instance
        """
        self.episodic_store = episodic_store
        self.db = db
        self.logger = logging.getLogger(__name__)

    async def record_failure(
        self,
        component: str,
        failure_type: str,
        message: str,
        severity: str = "warning",
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Record a failure event for consolidation learning.

        Args:
            component: Component that failed (e.g., "episodic.sources")
            failure_type: Type of failure (e.g., "import_error")
            message: Human-readable description
            severity: "info", "warning", "error", or "critical"
            details: Structured data about the failure
            session_id: Optional session ID for context

        Returns:
            Event ID of recorded failure
        """
        details = details or {}

        # Create failure event for episodic memory
        failure_record = FailureRecord(
            component=component,
            failure_type=failure_type,
            message=message,
            severity=severity,
            details=details,
            timestamp=int(datetime.now().timestamp() * 1000),
        )

        # Format content for readability
        content = f"[{severity.upper()}] {component}: {message}"
        if details:
            content += f"\nDetails: {details}"

        try:
            # Record in episodic memory
            event_id = await self.episodic_store.store(
                EpisodicEvent(
                    project_id=None,  # System-level failure
                    session_id=session_id or "system",
                    timestamp=failure_record.timestamp,
                    event_type=EventType.SYSTEM_ERROR,
                    content=content,
                    outcome=f"failure:{failure_type}",
                    context_cwd=None,
                    context_files=None,
                    context_task="system_monitoring",
                    context_phase="execution",
                )
            )

            self.logger.info(
                f"Recorded failure event: {component}/{failure_type} (id={event_id})"
            )

            return event_id

        except Exception as e:
            # Even recording failures must fail loudly
            self.logger.error(
                f"Failed to record failure event: {type(e).__name__}: {e}. "
                f"Original failure: {component}/{failure_type}: {message}"
            )
            raise

    async def record_import_failure(
        self, module: str, dependency: str, solution: str = ""
    ) -> int:
        """Record an import failure (missing dependency).

        Args:
            module: Module that failed to import (e.g., "slack_sdk")
            dependency: Required dependency name
            solution: How to fix it (e.g., "pip install slack-sdk")

        Returns:
            Event ID
        """
        return await self.record_failure(
            component="imports",
            failure_type="import_error",
            message=f"Failed to import {module}",
            severity="warning",
            details={
                "module": module,
                "dependency": dependency,
                "solution": solution,
            },
        )

    async def record_data_corruption(
        self, table: str, field: str, event_id: int, invalid_value: Any
    ) -> int:
        """Record a data inconsistency/corruption event.

        Args:
            table: Table name where corruption detected
            field: Field with invalid data
            event_id: Event ID with bad data
            invalid_value: The invalid value

        Returns:
            Event ID
        """
        return await self.record_failure(
            component="data_integrity",
            failure_type="data_corruption",
            message=f"Data inconsistency in {table}.{field}",
            severity="warning",
            details={
                "table": table,
                "field": field,
                "event_id": event_id,
                "invalid_value": str(invalid_value),
            },
        )

    async def record_permission_failure(
        self, operation: str, resource: str, error_msg: str = ""
    ) -> int:
        """Record a permission/access failure.

        Args:
            operation: Operation that failed (e.g., "DELETE")
            resource: Resource being accessed (e.g., "advisory_locks")
            error_msg: Error message from exception

        Returns:
            Event ID
        """
        return await self.record_failure(
            component="database_access",
            failure_type="permission_error",
            message=f"Permission denied for {operation} on {resource}",
            severity="error",
            details={
                "operation": operation,
                "resource": resource,
                "error": error_msg,
            },
        )

    async def get_failures_by_type(
        self, failure_type: str, limit: int = 100
    ) -> list:
        """Get all failures of a specific type.

        Used by consolidation system to extract patterns.

        Args:
            failure_type: Type of failure to search for
            limit: Max results

        Returns:
            List of failure events
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT * FROM episodic_events
                WHERE event_type = 'system_error' AND outcome LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (f"failure:{failure_type}%", limit),
            )
            return await result.fetchall()

    async def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about recorded failures.

        Returns:
            Dict with failure counts by type, severity, component
        """
        async with self.db.get_connection() as conn:
            # Get failures by type
            result = await conn.execute(
                """
                SELECT
                    outcome,
                    COUNT(*) as count,
                    MAX(timestamp) as last_seen
                FROM episodic_events
                WHERE event_type = 'system_error'
                GROUP BY outcome
                ORDER BY count DESC
                """
            )
            failures_by_type = await result.fetchall()

            # Get failures by component (extract from content)
            result = await conn.execute(
                """
                SELECT
                    SUBSTRING(content, 1, POSITION(':' IN content) - 1) as component,
                    COUNT(*) as count
                FROM episodic_events
                WHERE event_type = 'system_error'
                GROUP BY component
                ORDER BY count DESC
                """
            )
            failures_by_component = await result.fetchall()

            return {
                "total_failures": sum(row[1] for row in failures_by_type),
                "by_type": failures_by_type,
                "by_component": failures_by_component,
            }
