"""Audit logging for sensitive Athena operations (Phase 3).

Logs:
- Memory operations (store, delete)
- Consolidations
- Project management
- Goal/task creation
- Configuration changes
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class AuditAction(str, Enum):
    """Audit action types."""

    # Memory operations
    MEMORY_STORE = "memory_store"
    MEMORY_DELETE = "memory_delete"
    MEMORY_RETRIEVE = "memory_retrieve"
    MEMORY_FORGET = "memory_forget"

    # Consolidation
    CONSOLIDATION_START = "consolidation_start"
    CONSOLIDATION_COMPLETE = "consolidation_complete"
    CONSOLIDATION_ERROR = "consolidation_error"

    # Project management
    PROJECT_CREATE = "project_create"
    PROJECT_DELETE = "project_delete"
    PROJECT_UPDATE = "project_update"

    # Task/Goal management
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    GOAL_SET = "goal_set"
    GOAL_UPDATE = "goal_update"

    # Configuration
    CONFIG_CHANGE = "config_change"
    RATE_LIMIT_CHANGE = "rate_limit_change"

    # Security
    FAILED_AUTH = "failed_auth"
    PERMISSION_DENIED = "permission_denied"


class AuditLogger:
    """Audit logger for security-relevant events."""

    def __init__(self, name: str = "athena.audit"):
        """Initialize audit logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)

    def log_action(
        self,
        action: AuditAction,
        project_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        status: str = "success",
    ):
        """Log audit action.

        Args:
            action: Audit action
            project_id: Project identifier
            resource_type: Type of resource (memory, task, entity, etc.)
            resource_id: Resource identifier
            details: Additional details
            user_id: User identifier if applicable
            status: Status (success, failure)
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action.value,
            "status": status,
            "project_id": project_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }

        if user_id:
            audit_entry["user_id"] = user_id

        if details:
            audit_entry["details"] = details

        self.logger.info(json.dumps(audit_entry))

    # Memory operations

    def log_memory_store(
        self, project_id: str, memory_id: str, memory_type: str, size_bytes: int, **kwargs
    ):
        """Log memory storage.

        Args:
            project_id: Project ID
            memory_id: Memory ID
            memory_type: Memory type (fact, pattern, etc.)
            size_bytes: Memory size
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.MEMORY_STORE,
            project_id=project_id,
            resource_type="memory",
            resource_id=memory_id,
            details={"memory_type": memory_type, "size_bytes": size_bytes, **kwargs},
        )

    def log_memory_delete(
        self, project_id: str, memory_id: str, reason: str = "user_request", **kwargs
    ):
        """Log memory deletion.

        Args:
            project_id: Project ID
            memory_id: Memory ID
            reason: Deletion reason
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.MEMORY_DELETE,
            project_id=project_id,
            resource_type="memory",
            resource_id=memory_id,
            details={"reason": reason, **kwargs},
        )

    def log_memory_retrieve(self, project_id: str, query: str, result_count: int, **kwargs):
        """Log memory retrieval.

        Args:
            project_id: Project ID
            query: Search query
            result_count: Number of results
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.MEMORY_RETRIEVE,
            project_id=project_id,
            details={
                "query": query[:100],  # Truncate for logging
                "result_count": result_count,
                **kwargs,
            },
        )

    # Consolidation operations

    def log_consolidation_start(self, project_id: str, strategy: str, event_count: int, **kwargs):
        """Log consolidation start.

        Args:
            project_id: Project ID
            strategy: Consolidation strategy
            event_count: Number of events to consolidate
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.CONSOLIDATION_START,
            project_id=project_id,
            details={"strategy": strategy, "event_count": event_count, **kwargs},
        )

    def log_consolidation_complete(
        self,
        project_id: str,
        strategy: str,
        patterns_extracted: int,
        duration_seconds: float,
        **kwargs,
    ):
        """Log consolidation completion.

        Args:
            project_id: Project ID
            strategy: Consolidation strategy
            patterns_extracted: Number of patterns extracted
            duration_seconds: Duration in seconds
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.CONSOLIDATION_COMPLETE,
            project_id=project_id,
            details={
                "strategy": strategy,
                "patterns_extracted": patterns_extracted,
                "duration_seconds": duration_seconds,
                **kwargs,
            },
        )

    def log_consolidation_error(self, project_id: str, strategy: str, error_message: str, **kwargs):
        """Log consolidation error.

        Args:
            project_id: Project ID
            strategy: Consolidation strategy
            error_message: Error message
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.CONSOLIDATION_ERROR,
            project_id=project_id,
            status="failure",
            details={"strategy": strategy, "error": error_message, **kwargs},
        )

    # Project management

    def log_project_create(self, project_id: str, project_name: str, **kwargs):
        """Log project creation.

        Args:
            project_id: Project ID
            project_name: Project name
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.PROJECT_CREATE,
            project_id=project_id,
            resource_type="project",
            resource_id=project_id,
            details={"name": project_name, **kwargs},
        )

    def log_project_delete(self, project_id: str, project_name: str, **kwargs):
        """Log project deletion.

        Args:
            project_id: Project ID
            project_name: Project name
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.PROJECT_DELETE,
            project_id=project_id,
            resource_type="project",
            resource_id=project_id,
            details={"name": project_name, **kwargs},
        )

    # Task/Goal management

    def log_task_create(
        self, project_id: str, task_id: str, title: str, priority: str = "medium", **kwargs
    ):
        """Log task creation.

        Args:
            project_id: Project ID
            task_id: Task ID
            title: Task title
            priority: Task priority
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.TASK_CREATE,
            project_id=project_id,
            resource_type="task",
            resource_id=task_id,
            details={"title": title, "priority": priority, **kwargs},
        )

    def log_task_delete(
        self, project_id: str, task_id: str, reason: str = "user_request", **kwargs
    ):
        """Log task deletion.

        Args:
            project_id: Project ID
            task_id: Task ID
            reason: Deletion reason
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.TASK_DELETE,
            project_id=project_id,
            resource_type="task",
            resource_id=task_id,
            details={"reason": reason, **kwargs},
        )

    def log_goal_set(
        self, project_id: str, goal_id: str, goal_name: str, priority: str = "medium", **kwargs
    ):
        """Log goal setting.

        Args:
            project_id: Project ID
            goal_id: Goal ID
            goal_name: Goal name
            priority: Goal priority
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.GOAL_SET,
            project_id=project_id,
            resource_type="goal",
            resource_id=goal_id,
            details={"name": goal_name, "priority": priority, **kwargs},
        )

    # Configuration

    def log_config_change(self, config_key: str, old_value: Any, new_value: Any, **kwargs):
        """Log configuration change.

        Args:
            config_key: Configuration key
            old_value: Old value
            new_value: New value
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.CONFIG_CHANGE,
            details={
                "key": config_key,
                "old_value": str(old_value)[:100],
                "new_value": str(new_value)[:100],
                **kwargs,
            },
        )

    def log_rate_limit_change(self, operation: str, old_limit: int, new_limit: int, **kwargs):
        """Log rate limit change.

        Args:
            operation: Operation name
            old_limit: Old limit
            new_limit: New limit
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.RATE_LIMIT_CHANGE,
            details={
                "operation": operation,
                "old_limit": old_limit,
                "new_limit": new_limit,
                **kwargs,
            },
        )

    # Security events

    def log_permission_denied(self, action: str, resource: str, reason: str, **kwargs):
        """Log permission denied event.

        Args:
            action: Attempted action
            resource: Resource accessed
            reason: Reason for denial
            **kwargs: Additional fields
        """
        self.log_action(
            AuditAction.PERMISSION_DENIED,
            status="failure",
            details={"action": action, "resource": resource, "reason": reason, **kwargs},
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger.

    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def initialize_audit_logger(name: str = "athena.audit") -> AuditLogger:
    """Initialize global audit logger.

    Args:
        name: Logger name

    Returns:
        AuditLogger instance
    """
    global _audit_logger
    _audit_logger = AuditLogger(name)
    return _audit_logger
