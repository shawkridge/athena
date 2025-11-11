"""Async/sync bridging utilities for PostgreSQL async operations.

This module provides robust methods to run async coroutines from synchronous contexts.
It handles the complexity of multiple event loop scenarios and provides safe bridging
between async and sync code paths.

Usage:
    from athena.core.async_utils import run_async, run_async_in_thread

    # Simple case: no existing event loop
    result = run_async(some_async_function())

    # Thread pool case: if already in async context
    result = run_async_in_thread(some_async_function())
"""

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_async(coro: Any, timeout: Optional[float] = None) -> Any:
    """Run an async coroutine synchronously.

    This function intelligently handles multiple scenarios:
    1. No event loop: Creates new loop with asyncio.run()
    2. Event loop exists but not running: Uses loop.run_until_complete()
    3. Event loop is running: Uses thread pool executor

    Args:
        coro: Coroutine to run
        timeout: Optional timeout in seconds

    Returns:
        Result of the coroutine

    Raises:
        TimeoutError: If timeout is exceeded
        RuntimeError: If coroutine execution fails
    """
    import inspect

    # If not a coroutine, return as-is
    if not inspect.iscoroutine(coro):
        return coro

    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Event loop is running (e.g., in async context, Jupyter, etc.)
            # We must use a thread pool to avoid "This event loop is already running" error
            logger.debug("Event loop running; using thread pool executor")
            return run_async_in_thread(coro, timeout=timeout)
        else:
            # Event loop exists but not running
            logger.debug("Event loop exists; using run_until_complete")
            if timeout:
                return asyncio.wait_for(coro, timeout=timeout)
            return loop.run_until_complete(coro)

    except RuntimeError:
        # No event loop exists, create new one
        logger.debug("No event loop; creating new one with asyncio.run")
        if timeout:
            # Create wrapper with timeout
            async def wrapped_coro():
                return await asyncio.wait_for(coro, timeout=timeout)
            return asyncio.run(wrapped_coro())
        else:
            return asyncio.run(coro)


def run_async_in_thread(coro: Any, timeout: Optional[float] = None) -> Any:
    """Run an async coroutine in a separate thread.

    This is used when an event loop is already running in the current thread.
    Creates a new thread with its own event loop to execute the coroutine.

    Args:
        coro: Coroutine to run
        timeout: Optional timeout in seconds

    Returns:
        Result of the coroutine

    Raises:
        TimeoutError: If timeout is exceeded
        RuntimeError: If execution fails
    """
    import inspect

    if not inspect.iscoroutine(coro):
        return coro

    def run_in_new_loop():
        """Run coroutine in a new event loop in this thread."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            if timeout:
                return new_loop.run_until_complete(
                    asyncio.wait_for(coro, timeout=timeout)
                )
            else:
                return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    logger.debug("Running async coroutine in separate thread")
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_new_loop)
        return future.result(timeout=timeout)


def sync_wrapper(async_func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to create a sync wrapper for an async function.

    Usage:
        class MyStore:
            async def remember(self, ...):
                # async implementation
                ...

            @sync_wrapper(remember)
            def remember_sync(self, ...):
                pass  # Decorator handles the implementation
    """

    @wraps(async_func)
    def wrapper(self, *args, **kwargs):
        coro = async_func(self, *args, **kwargs)
        return run_async(coro)

    return wrapper


def ensure_sync(func_name: str) -> Callable:
    """Create a sync version of an async method.

    Args:
        func_name: Name of the async method to wrap

    Returns:
        Decorator that creates a sync wrapper method
    """

    def decorator(cls):
        # Get the async method
        async_method = getattr(cls, func_name, None)
        if not async_method:
            raise AttributeError(f"Method {func_name} not found on {cls.__name__}")

        # Create sync wrapper name
        sync_method_name = f"{func_name}_sync"

        # Create wrapper function
        def sync_method(self, *args, **kwargs):
            coro = async_method(self, *args, **kwargs)
            return run_async(coro)

        # Copy docstring and update it
        if async_method.__doc__:
            sync_method.__doc__ = (
                f"Synchronous wrapper for {func_name}.\n\n"
                f"{async_method.__doc__}"
            )

        # Add method to class
        setattr(cls, sync_method_name, sync_method)
        return cls

    return decorator


class AsyncContextBridge:
    """Context manager for switching between async and sync contexts.

    Usage:
        with AsyncContextBridge() as bridge:
            result = bridge.run(some_async_function())
    """

    def __init__(self):
        """Initialize the bridge."""
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def __enter__(self):
        """Enter context, prepare for async execution."""
        try:
            self.loop = asyncio.get_event_loop()
            if self.loop.is_running():
                # Will use thread pool in run()
                self.loop = None
        except RuntimeError:
            self.loop = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        return False

    def run(self, coro: Any, timeout: Optional[float] = None) -> Any:
        """Run coroutine in this bridge context."""
        return run_async(coro, timeout=timeout)


def get_sync_method_name(async_method_name: str) -> str:
    """Get the sync wrapper method name for an async method.

    Args:
        async_method_name: Name of async method (e.g., 'remember')

    Returns:
        Name of sync wrapper method (e.g., 'remember_sync')
    """
    if async_method_name.startswith("async_"):
        return async_method_name.replace("async_", "", 1) + "_sync"
    return async_method_name + "_sync"


# Module-level convenience functions
async_to_sync = run_async  # Alias for clarity
run_coroutine_sync = run_async  # Another alias
