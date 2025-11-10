"""Security module for Athena memory system (Phase 3).

Provides:
- Input validation (validators.py)
- Rate limiting (rate_limiter.py)
- Audit logging (audit.py)
"""

from .validators import (
    ValidationError,
    RecallRequest,
    RememberRequest,
    CreateTaskRequest,
    CreateEntityRequest,
    validate_project_id,
    validate_query,
    validate_memory_type,
    validate_priority,
    validate_limit,
    validate_entity_name,
)

from .rate_limiter import (
    RateLimiter,
    OperationRateLimiter,
    RateLimitError,
    get_rate_limiter,
    initialize_rate_limiter,
    check_rate_limit,
)

from .audit import (
    AuditAction,
    AuditLogger,
    get_audit_logger,
    initialize_audit_logger,
)

__all__ = [
    # Validators
    'ValidationError',
    'RecallRequest',
    'RememberRequest',
    'CreateTaskRequest',
    'CreateEntityRequest',
    'validate_project_id',
    'validate_query',
    'validate_memory_type',
    'validate_priority',
    'validate_limit',
    'validate_entity_name',
    # Rate limiting
    'RateLimiter',
    'OperationRateLimiter',
    'RateLimitError',
    'get_rate_limiter',
    'initialize_rate_limiter',
    'check_rate_limit',
    # Audit logging
    'AuditAction',
    'AuditLogger',
    'get_audit_logger',
    'initialize_audit_logger',
]
