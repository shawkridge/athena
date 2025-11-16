"""
Custom exception hierarchy for Athena memory system.

Organizes exceptions by layer and operation type to replace broad
exception handlers (bare except: and except Exception:) with
specific, actionable error types.

Hierarchy:
    AthenaError (base)
    ├── StorageError
    │   ├── DatabaseError
    │   ├── ConnectionError
    │   └── SchemaError
    ├── DataError
    │   ├── ParseError
    │   ├── ValidationError
    │   └── EncodingError
    ├── OperationError
    │   ├── QueryError
    │   ├── TransactionError
    │   └── TimeoutError
    ├── LayerError
    │   ├── EpisodicError
    │   ├── SemanticError
    │   ├── ProceduralError
    │   ├── ProspectiveError
    │   ├── GraphError
    │   ├── MetaError
    │   └── ConsolidationError
    ├── IntegrationError
    │   ├── BridgeError
    │   └── LayerCommunicationError
    └── SystemError
        ├── ConfigurationError
        ├── ResourceError
        └── StateError
"""

import logging
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# BASE EXCEPTION
# ============================================================================

class AthenaError(Exception):
    """Base exception for all Athena errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now()
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.original_error:
            return f"{self.error_code}: {self.message} (caused by {type(self.original_error).__name__})"
        return f"{self.error_code}: {self.message}"

    def with_context(self, **kwargs) -> "AthenaError":
        """Add context information to error."""
        self.context.update(kwargs)
        return self


# ============================================================================
# STORAGE ERRORS
# ============================================================================

class StorageError(AthenaError):
    """Base exception for storage-related errors."""
    pass


class DatabaseError(StorageError):
    """Database operation failed (query, transaction, etc.)."""
    pass


class ConnectionError(StorageError):
    """Failed to connect to database or storage backend."""
    pass


class SchemaError(StorageError):
    """Database schema is invalid or missing required tables."""
    pass


# ============================================================================
# DATA ERRORS
# ============================================================================

class DataError(AthenaError):
    """Base exception for data-related errors."""
    pass


class ParseError(DataError):
    """Failed to parse data (JSON, CSV, AST, etc.)."""
    pass


class ValidationError(DataError):
    """Data validation failed."""
    pass


class EncodingError(DataError):
    """Text encoding/decoding failed."""
    pass


# ============================================================================
# OPERATION ERRORS
# ============================================================================

class OperationError(AthenaError):
    """Base exception for operation-related errors."""
    pass


class QueryError(OperationError):
    """Query execution or result processing failed."""
    pass


class TransactionError(OperationError):
    """Transaction commit/rollback failed."""
    pass


class TimeoutError(OperationError):
    """Operation exceeded timeout limit."""
    pass


# ============================================================================
# LAYER-SPECIFIC ERRORS
# ============================================================================

class LayerError(AthenaError):
    """Base exception for layer-specific errors."""
    pass


class EpisodicError(LayerError):
    """Error in episodic memory (Layer 1)."""
    pass


class SemanticError(LayerError):
    """Error in semantic memory (Layer 2)."""
    pass


class ProceduralError(LayerError):
    """Error in procedural memory (Layer 3)."""
    pass


class ProspectiveError(LayerError):
    """Error in prospective memory (Layer 4)."""
    pass


class GraphError(LayerError):
    """Error in knowledge graph (Layer 5)."""
    pass


class MetaError(LayerError):
    """Error in meta-memory (Layer 6)."""
    pass


class ConsolidationError(LayerError):
    """Error in consolidation (Layer 7)."""
    pass


# ============================================================================
# INTEGRATION ERRORS
# ============================================================================

class IntegrationError(AthenaError):
    """Base exception for cross-layer integration errors."""
    pass


class BridgeError(IntegrationError):
    """Error in bridge/adapter between layers."""
    pass


class LayerCommunicationError(IntegrationError):
    """Failed to communicate between layers."""
    pass


# ============================================================================
# SYSTEM ERRORS
# ============================================================================

class SystemError(AthenaError):
    """Base exception for system-level errors."""
    pass


class ConfigurationError(SystemError):
    """Configuration is invalid or missing required settings."""
    pass


class ResourceError(SystemError):
    """Required resource is unavailable (memory, file, etc.)."""
    pass


class StateError(SystemError):
    """System is in an invalid state for the requested operation."""
    pass


# ============================================================================
# ERROR CONTEXT BUILDER
# ============================================================================

@dataclass
class ErrorContext:
    """Builder for collecting error context information."""

    operation: str = ""
    layer: Optional[str] = None
    resource: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "operation": self.operation,
            "layer": self.layer,
            "resource": self.resource,
            "params": self.params,
            "additional_info": self.additional_info,
        }


# ============================================================================
# ERROR HANDLER UTILITIES
# ============================================================================

def handle_database_error(
    error: Exception,
    operation: str = "database operation",
    context: Optional[Dict[str, Any]] = None,
) -> DatabaseError:
    """Convert database exception to DatabaseError with context."""
    import psycopg

    error_type = type(error).__name__

    if isinstance(error, psycopg.DatabaseError):
        return DatabaseError(
            message=f"Database operation failed: {str(error)}",
            error_code="DB_OPERATION_FAILED",
            context={
                "operation": operation,
                "error_type": error_type,
                **(context or {}),
            },
            original_error=error,
        )
    elif isinstance(error, psycopg.OperationalError):
        return ConnectionError(
            message=f"Database connection failed: {str(error)}",
            error_code="DB_CONNECTION_FAILED",
            context={
                "operation": operation,
                "error_type": error_type,
                **(context or {}),
            },
            original_error=error,
        )
    elif isinstance(error, psycopg.ProgrammingError):
        return SchemaError(
            message=f"Database schema error: {str(error)}",
            error_code="DB_SCHEMA_ERROR",
            context={
                "operation": operation,
                "error_type": error_type,
                **(context or {}),
            },
            original_error=error,
        )

    return DatabaseError(
        message=f"Database error: {str(error)}",
        error_code="DB_ERROR",
        context={
            "operation": operation,
            "error_type": error_type,
            **(context or {}),
        },
        original_error=error,
    )


def handle_parse_error(
    error: Exception,
    data_type: str = "data",
    context: Optional[Dict[str, Any]] = None,
) -> ParseError:
    """Convert parsing exception to ParseError with context."""
    error_type = type(error).__name__

    if isinstance(error, (ValueError, TypeError, KeyError)):
        return ParseError(
            message=f"Failed to parse {data_type}: {str(error)}",
            error_code="PARSE_FAILED",
            context={
                "data_type": data_type,
                "error_type": error_type,
                **(context or {}),
            },
            original_error=error,
        )

    import json
    if isinstance(error, json.JSONDecodeError):
        return ParseError(
            message=f"Invalid JSON: {str(error)} at line {error.lineno}",
            error_code="JSON_PARSE_FAILED",
            context={
                "data_type": "json",
                "line": error.lineno,
                "column": error.colno,
                **(context or {}),
            },
            original_error=error,
        )

    return ParseError(
        message=f"Failed to parse {data_type}: {str(error)}",
        error_code="PARSE_FAILED",
        context={
            "data_type": data_type,
            "error_type": error_type,
            **(context or {}),
        },
        original_error=error,
    )


def handle_io_error(
    error: Exception,
    operation: str = "file operation",
    context: Optional[Dict[str, Any]] = None,
) -> StorageError:
    """Convert I/O exception to StorageError with context."""
    error_type = type(error).__name__

    if isinstance(error, FileNotFoundError):
        return ResourceError(
            message=f"File not found: {str(error)}",
            error_code="FILE_NOT_FOUND",
            context={
                "operation": operation,
                "error_type": error_type,
                **(context or {}),
            },
            original_error=error,
        )
    elif isinstance(error, PermissionError):
        return ResourceError(
            message=f"Permission denied: {str(error)}",
            error_code="PERMISSION_DENIED",
            context={
                "operation": operation,
                "error_type": error_type,
                **(context or {}),
            },
            original_error=error,
        )

    return ResourceError(
        message=f"I/O error during {operation}: {str(error)}",
        error_code="IO_ERROR",
        context={
            "operation": operation,
            "error_type": error_type,
            **(context or {}),
        },
        original_error=error,
    )


# ============================================================================
# GRACEFUL DEGRADATION UTILITIES
# ============================================================================

def ignore_error(error: Exception, logger_obj=None, operation: str = "operation") -> None:
    """Log error at debug level for graceful degradation."""
    if logger_obj:
        logger_obj.debug(
            f"Gracefully ignoring {operation}: {type(error).__name__}: {error}"
        )
    else:
        logger.debug(
            f"Gracefully ignoring {operation}: {type(error).__name__}: {error}"
        )


def log_and_continue(
    error: Exception,
    default_value: Any = None,
    logger_obj=None,
    operation: str = "operation",
) -> Any:
    """Log error and return default value for graceful degradation."""
    if logger_obj:
        logger_obj.warning(
            f"Error in {operation}, returning default: {type(error).__name__}: {error}"
        )
    else:
        logger.warning(
            f"Error in {operation}, returning default: {type(error).__name__}: {error}"
        )
    return default_value
