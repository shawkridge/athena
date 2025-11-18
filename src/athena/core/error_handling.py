"""Unified error handling utilities for consistent exception management.

Consolidates error handling patterns across all memory layers.
Provides:
- Safe execution with error handling
- Multiple fallback handlers
- Consistent logging
- Default value returns
"""

import logging
from typing import Any, Callable, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def safe_execute(
    func: Callable, *args, default: Any = None, log_errors: bool = True, **kwargs
) -> Any:
    """Safely execute function with error handling.

    Args:
        func: Function to execute
        *args: Positional arguments
        default: Default value if function fails
        log_errors: Whether to log errors
        **kwargs: Keyword arguments

    Returns:
        Function result or default value if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Execution failed: {e}")
        return default


def try_multiple(handlers: List[Callable], default: Any = None, log_errors: bool = False) -> Any:
    """Try multiple handlers in sequence until one succeeds.

    Args:
        handlers: List of callable handlers to try in order
        default: Default value if all handlers fail
        log_errors: Whether to log errors for each handler

    Returns:
        Result from first successful handler or default value
    """
    for i, handler in enumerate(handlers):
        try:
            return handler()
        except Exception as e:
            if log_errors:
                logger.debug(f"Handler {i} failed: {e}")
            continue
    return default


def safe_json_loads(data: str, default: Optional[dict] = None) -> dict:
    """Safely parse JSON with fallback.

    Args:
        data: JSON string to parse
        default: Default dict if parsing fails

    Returns:
        Parsed dict or default
    """
    import json

    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return default or {}


def safe_json_dumps(obj: Any, default_str: str = "{}") -> str:
    """Safely convert object to JSON string.

    Args:
        obj: Object to serialize
        default_str: Default string if serialization fails

    Returns:
        JSON string or default
    """
    import json

    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        logger.warning(f"Could not serialize object: {type(obj)}")
        return default_str


def safe_float_parse(value: Any, default: float = 0.5) -> float:
    """Safely parse value to float.

    Args:
        value: Value to parse (string, int, float, etc.)
        default: Default float if parsing fails

    Returns:
        Parsed float or default
    """
    try:
        if isinstance(value, float):
            return value
        if isinstance(value, (int, str)):
            return float(value)
        if hasattr(value, "__float__"):
            return float(value)
        return default
    except (ValueError, TypeError, AttributeError):
        return default


def safe_int_parse(value: Any, default: int = 0) -> int:
    """Safely parse value to int.

    Args:
        value: Value to parse (string, int, float, etc.)
        default: Default int if parsing fails

    Returns:
        Parsed int or default
    """
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, (str, float)):
            return int(value)
        if hasattr(value, "__int__"):
            return int(value)
        return default
    except (ValueError, TypeError, AttributeError):
        return default


def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from object.

    Args:
        obj: Object to query
        attr: Attribute name
        default: Default value if attribute missing

    Returns:
        Attribute value or default
    """
    try:
        return getattr(obj, attr, default)
    except (AttributeError, TypeError):
        return default


def safe_dict_get(dct: Optional[dict], key: str, default: Any = None) -> Any:
    """Safely get value from dict.

    Args:
        dct: Dictionary (or None)
        key: Key to retrieve
        default: Default value if key missing

    Returns:
        Value or default
    """
    if not dct:
        return default
    return dct.get(key, default)


def safe_list_access(lst: Optional[list], index: int, default: Any = None) -> Any:
    """Safely access list index.

    Args:
        lst: List (or None)
        index: Index to access
        default: Default value if index out of range

    Returns:
        Value at index or default
    """
    if not lst:
        return default
    try:
        return lst[index]
    except (IndexError, TypeError):
        return default


class ErrorContext:
    """Context manager for error handling with logging."""

    def __init__(self, operation: str, log_errors: bool = True, re_raise: bool = False):
        """Initialize error context.

        Args:
            operation: Name of operation for logging
            log_errors: Whether to log errors
            re_raise: Whether to re-raise exceptions
        """
        self.operation = operation
        self.log_errors = log_errors
        self.re_raise = re_raise
        self.error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            if self.log_errors:
                logger.error(f"{self.operation} failed: {exc_type.__name__}: {exc_val}")
            if self.re_raise:
                return False  # Re-raise exception
            return True  # Suppress exception
        return False


def catch_exception(exception_type: type, handler: Optional[Callable] = None, default: Any = None):
    """Decorator to catch specific exceptions.

    Args:
        exception_type: Exception class to catch
        handler: Optional handler function for exception
        default: Default return value

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                if handler:
                    handler(e)
                return default

        return wrapper

    return decorator
