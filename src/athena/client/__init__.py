"""HTTP client for Athena API."""

from .http_client import (
    AthenaHTTPClient,
    AthenaHTTPAsyncClient,
    AthenaHTTPClientError,
    AthenaHTTPClientConnectionError,
    AthenaHTTPClientTimeoutError,
    AthenaHTTPClientOperationError,
    get_client,
    get_async_client,
)

__all__ = [
    "AthenaHTTPClient",
    "AthenaHTTPAsyncClient",
    "AthenaHTTPClientError",
    "AthenaHTTPClientConnectionError",
    "AthenaHTTPClientTimeoutError",
    "AthenaHTTPClientOperationError",
    "get_client",
    "get_async_client",
]
