"""MCP Tool Rate Limiting System.

Implements per-tool rate limiting with three tiers:
- Read tools: 100 calls/min (10 per second)
- Write tools: 30 calls/min (0.5 per second)
- Admin tools: 10 calls/min (high-cost operations)

Uses token bucket algorithm with burst capacity.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Tool execution categories for rate limiting."""
    READ = "read"      # Queries, searches, list operations (100/min)
    WRITE = "write"    # Create, update, record operations (30/min)
    ADMIN = "admin"    # Delete, optimize, cleanup operations (10/min)


@dataclass
class ToolRateLimit:
    """Rate limit configuration for a single tool."""
    tool_name: str
    category: ToolCategory
    max_per_minute: int
    burst_size: int = 0  # Will be calculated if 0

    def __post_init__(self):
        """Validate and calculate burst size."""
        if self.burst_size == 0:
            # Default: allow burst of 20% of per-minute rate, minimum 2
            self.burst_size = max(2, self.max_per_minute // 5)

    @property
    def refill_rate(self) -> float:
        """Tokens per second."""
        return self.max_per_minute / 60.0


@dataclass
class TokenBucket:
    """Token bucket for rate limiting a single tool."""
    config: ToolRateLimit
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize with full capacity."""
        self.tokens = float(self.config.burst_size)
        self.last_refill = time.time()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.config.refill_rate

        self.tokens = min(
            float(self.config.burst_size),
            self.tokens + tokens_to_add
        )
        self.last_refill = now

    def try_consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens.

        Args:
            tokens: Number of tokens to consume (default 1)

        Returns:
            True if consumed, False if rate limited
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_wait_time(self, tokens: float = 1.0) -> float:
        """Get time to wait before next request.

        Args:
            tokens: Number of tokens needed (default 1)

        Returns:
            Wait time in seconds
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        needed = tokens - self.tokens
        return needed / self.config.refill_rate


class MCPRateLimiter:
    """Rate limiter for MCP tool execution.

    Implements per-tool rate limiting with three tiers:
    - Read tools: 100/min
    - Write tools: 30/min
    - Admin tools: 10/min

    Attributes:
        buckets: Per-tool token buckets
        metrics: Tracking stats (requests, limited, allowed)
        callbacks: Optional callbacks for rate limit events
    """

    # Default rate limits by category
    DEFAULT_LIMITS = {
        ToolCategory.READ: ToolRateLimit("", ToolCategory.READ, max_per_minute=100),
        ToolCategory.WRITE: ToolRateLimit("", ToolCategory.WRITE, max_per_minute=30),
        ToolCategory.ADMIN: ToolRateLimit("", ToolCategory.ADMIN, max_per_minute=10),
    }

    # Tool categorization patterns
    READ_PATTERNS = {
        "recall", "search", "list", "get", "query", "analyze", "find",
        "validate", "check", "evaluate", "measure", "extract", "detect",
        "summarize", "scan", "browse", "inspect", "examine", "review"
    }

    WRITE_PATTERNS = {
        "create", "record", "update", "add", "set", "remember",
        "store", "insert", "modify", "edit", "link", "attach",
        "strengthen", "consolidate", "connect", "establish"
    }

    ADMIN_PATTERNS = {
        "delete", "forget", "remove", "optimize", "clear", "prune",
        "reset", "clean", "override", "dismiss", "ignore"
    }

    def __init__(
        self,
        read_limit: int = 100,
        write_limit: int = 30,
        admin_limit: int = 10,
    ):
        """Initialize MCP rate limiter.

        Args:
            read_limit: Max read operations per minute (default 100)
            write_limit: Max write operations per minute (default 30)
            admin_limit: Max admin operations per minute (default 10)
        """
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.admin_limit = admin_limit

        # Per-tool token buckets
        self.buckets: Dict[str, TokenBucket] = {}

        # Tool categorizations (auto-detected)
        self.tool_categories: Dict[str, ToolCategory] = {}

        # Rate limit metrics
        self.metrics = {
            "total_requests": 0,
            "allowed": 0,
            "rate_limited": 0,
            "by_category": {
                "read": {"total": 0, "allowed": 0, "limited": 0},
                "write": {"total": 0, "allowed": 0, "limited": 0},
                "admin": {"total": 0, "allowed": 0, "limited": 0},
            }
        }

        # Callbacks
        self.on_rate_limit: Optional[Callable[[str, float], None]] = None

        logger.info(
            f"MCPRateLimiter initialized: "
            f"read={read_limit}/min, write={write_limit}/min, admin={admin_limit}/min"
        )

    def _categorize_tool(self, tool_name: str) -> ToolCategory:
        """Auto-categorize tool by name.

        Args:
            tool_name: Name of the tool (e.g., "recall", "create_task")

        Returns:
            ToolCategory
        """
        if tool_name in self.tool_categories:
            return self.tool_categories[tool_name]

        # Check patterns (case-insensitive, underscore-aware)
        tool_lower = tool_name.lower().replace("_", " ")

        for pattern in self.ADMIN_PATTERNS:
            if pattern in tool_lower:
                self.tool_categories[tool_name] = ToolCategory.ADMIN
                return ToolCategory.ADMIN

        for pattern in self.WRITE_PATTERNS:
            if pattern in tool_lower:
                self.tool_categories[tool_name] = ToolCategory.WRITE
                return ToolCategory.WRITE

        for pattern in self.READ_PATTERNS:
            if pattern in tool_lower:
                self.tool_categories[tool_name] = ToolCategory.READ
                return ToolCategory.READ

        # Default to read for unknown tools
        self.tool_categories[tool_name] = ToolCategory.READ
        return ToolCategory.READ

    def _get_bucket(self, tool_name: str) -> TokenBucket:
        """Get or create token bucket for tool.

        Args:
            tool_name: Name of the tool

        Returns:
            TokenBucket for the tool
        """
        if tool_name in self.buckets:
            return self.buckets[tool_name]

        # Auto-categorize
        category = self._categorize_tool(tool_name)

        # Get rate limit for category
        if category == ToolCategory.READ:
            max_per_minute = self.read_limit
        elif category == ToolCategory.WRITE:
            max_per_minute = self.write_limit
        else:  # ADMIN
            max_per_minute = self.admin_limit

        # Create config and bucket
        config = ToolRateLimit(
            tool_name=tool_name,
            category=category,
            max_per_minute=max_per_minute
        )

        bucket = TokenBucket(config=config)
        self.buckets[tool_name] = bucket

        logger.debug(f"Created rate limit for {tool_name}: {category.value} ({max_per_minute}/min)")

        return bucket

    def allow_request(self, tool_name: str) -> bool:
        """Check if request is allowed for tool.

        Args:
            tool_name: Name of the tool

        Returns:
            True if allowed, False if rate limited
        """
        bucket = self._get_bucket(tool_name)
        category = bucket.config.category

        # Update total metrics
        self.metrics["total_requests"] += 1
        self.metrics["by_category"][category.value]["total"] += 1

        # Try to consume token
        if bucket.try_consume():
            self.metrics["allowed"] += 1
            self.metrics["by_category"][category.value]["allowed"] += 1
            return True

        # Rate limited
        self.metrics["rate_limited"] += 1
        self.metrics["by_category"][category.value]["limited"] += 1

        # Call callback if set
        if self.on_rate_limit:
            wait_time = bucket.get_wait_time()
            self.on_rate_limit(tool_name, wait_time)

        return False

    def get_retry_after(self, tool_name: str) -> float:
        """Get seconds to wait before retrying.

        Args:
            tool_name: Name of the tool

        Returns:
            Seconds to wait (0 if request would be allowed)
        """
        bucket = self._get_bucket(tool_name)
        return bucket.get_wait_time()

    def get_stats(self) -> dict:
        """Get rate limiting statistics.

        Returns:
            Statistics dict with request counts and rates
        """
        total = self.metrics["total_requests"]
        allowed = self.metrics["allowed"]
        limited = self.metrics["rate_limited"]

        return {
            "total_requests": total,
            "allowed": allowed,
            "rate_limited": limited,
            "rate_limited_percentage": (limited / total * 100) if total > 0 else 0,
            "tools_registered": len(self.buckets),
            "by_category": self.metrics["by_category"],
            "limits": {
                "read_per_minute": self.read_limit,
                "write_per_minute": self.write_limit,
                "admin_per_minute": self.admin_limit,
            }
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters (useful for testing)."""
        self.metrics = {
            "total_requests": 0,
            "allowed": 0,
            "rate_limited": 0,
            "by_category": {
                "read": {"total": 0, "allowed": 0, "limited": 0},
                "write": {"total": 0, "allowed": 0, "limited": 0},
                "admin": {"total": 0, "allowed": 0, "limited": 0},
            }
        }


def rate_limit_response(retry_after: float) -> dict:
    """Create standardized rate limit error response.

    Args:
        retry_after: Seconds to wait before retry

    Returns:
        Error response dict for MCP
    """
    return {
        "status": "error",
        "error": "Rate limit exceeded",
        "retry_after": round(retry_after, 2),
        "message": f"Too many requests. Please retry after {retry_after:.1f} seconds."
    }
