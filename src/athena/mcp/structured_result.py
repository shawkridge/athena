"""Unified result format for MCP tool responses with TOON support."""

import json
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class ResultStatus(str, Enum):
    """Status of operation result."""
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class PaginationMetadata:
    """Pagination information for list results."""
    returned: int
    total: Optional[int] = None
    limit: Optional[int] = None
    has_more: bool = False
    offset: int = 0


@dataclass
class StructuredResult:
    """Unified result format for all MCP tools.

    Enables tool composition, better error handling, and consistent pagination.
    Backward compatible: as_text_content() converts to TextContent for existing callers.
    """
    status: ResultStatus
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    pagination: Optional[PaginationMetadata] = None
    confidence: Optional[float] = None  # 0.0-1.0
    reasoning: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dict, handling non-serializable objects."""
        result = {
            "status": self.status.value,
            "data": self.data,
            "metadata": self.metadata,
        }

        if self.pagination:
            result["pagination"] = asdict(self.pagination)

        if self.confidence is not None:
            result["confidence"] = self.confidence

        if self.reasoning is not None:
            result["reasoning"] = self.reasoning

        return result

    def as_json(self, indent: Optional[int] = None) -> str:
        """Convert to JSON string.

        Args:
            indent: Number of spaces for indentation. None = compact format.
        """
        return json.dumps(self.as_dict(), default=str, indent=indent)

    def as_text_content(self, indent: Optional[int] = None) -> TextContent:
        """Convert to TextContent for MCP compatibility.

        This maintains backward compatibility with existing MCP clients.
        Compact format (no indent) by default to reduce token usage.
        """
        return TextContent(
            type="text",
            text=self.as_json(indent=indent)
        )

    def as_toon_content(
        self,
        schema_name: Optional[str] = None,
        fallback_to_json: bool = True,
    ) -> TextContent:
        """Convert to TextContent using TOON format (if available).

        Attempts to encode response using TOON format for token efficiency.
        Automatically falls back to compact JSON if TOON is unavailable.

        Args:
            schema_name: TOON schema name (e.g., 'semantic_search_results')
            fallback_to_json: If True, fall back to compact JSON on TOON failure

        Returns:
            TextContent with TOON or JSON-encoded data
        """
        try:
            from athena.serialization.integration import TOONIntegrator

            # Try to use TOON if enabled
            result_dict = self.as_dict()
            serialized = TOONIntegrator.serialize(
                result_dict,
                schema_name=schema_name or self.metadata.get("operation"),
                use_toon=None,  # Let TOONIntegrator decide
            )
            return TextContent(type="text", text=serialized)
        except Exception as e:
            logger.debug(f"TOON encoding failed ({e}), falling back to JSON")
            if fallback_to_json:
                return self.as_text_content(indent=None)
            else:
                raise

    def as_optimized_content(
        self,
        schema_name: Optional[str] = None,
    ) -> TextContent:
        """Convert to TextContent with automatic format optimization.

        Tries TOON first (for 40-60% token savings), falls back to compact JSON.
        Recommended for handlers with large result sets.

        Args:
            schema_name: TOON schema name for format hints

        Returns:
            TextContent with optimized encoding (TOON or JSON)
        """
        return self.as_toon_content(
            schema_name=schema_name,
            fallback_to_json=True,
        )

    @classmethod
    def success(
        cls,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        pagination: Optional[PaginationMetadata] = None,
        confidence: Optional[float] = None,
        reasoning: Optional[str] = None,
    ) -> "StructuredResult":
        """Create success result."""
        return cls(
            status=ResultStatus.SUCCESS,
            data=data,
            metadata=metadata or {},
            pagination=pagination,
            confidence=confidence,
            reasoning=reasoning,
        )

    @classmethod
    def partial(
        cls,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        pagination: Optional[PaginationMetadata] = None,
        reasoning: Optional[str] = None,
    ) -> "StructuredResult":
        """Create partial result (incomplete but valid data)."""
        return cls(
            status=ResultStatus.PARTIAL,
            data=data,
            metadata={**(metadata or {}), "partial": True},
            pagination=pagination,
            reasoning=reasoning,
        )

    @classmethod
    def error(
        cls,
        error_msg: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "StructuredResult":
        """Create error result."""
        return cls(
            status=ResultStatus.ERROR,
            data=None,
            metadata={
                **(metadata or {}),
                "error": error_msg,
                "timestamp": datetime.now().isoformat(),
            },
        )


# ============================================================================
# Global Pagination Utility - Used by all handlers (Anthropic alignment)
# ============================================================================

def create_paginated_result(
    items: List[Any],
    total_count: Optional[int] = None,
    offset: int = 0,
    limit: int = 10,
    max_limit: int = 100,
    operation: Optional[str] = None,
    drill_down_hint: Optional[str] = None,
) -> StructuredResult:
    """Create a paginated result following Anthropic pattern.

    This is the STANDARD pattern for all list-returning handlers.

    Args:
        items: List of items to return (should be limited by query)
        total_count: Total count (from database COUNT query)
        offset: Current offset/page start position
        limit: Requested limit (will be capped at max_limit)
        max_limit: Maximum allowed limit (default 100)
        operation: Handler operation name for logging
        drill_down_hint: Hint text for drilling down (e.g., "/recall-memory")

    Returns:
        StructuredResult with pagination metadata and summary

    Example:
        # In handler
        limit = min(args.get("limit", 10), 100)
        offset = args.get("offset", 0)
        items = await db.fetch_items(offset=offset, limit=limit)
        total_count = await db.count_items()

        return create_paginated_result(
            items=items,
            total_count=total_count,
            offset=offset,
            limit=limit,
            operation="list_tasks",
            drill_down_hint="/recall-memory with task_id for full details"
        )
    """
    # Cap limit at maximum
    limit = min(limit, max_limit)

    # If total_count is None, infer it from items
    if total_count is None:
        total_count = len(items)

    # Calculate pagination state
    has_more = (offset + len(items)) < total_count

    # Build pagination metadata
    pagination = PaginationMetadata(
        returned=len(items),
        total=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )

    # Build summary (keep under 300 tokens total with data)
    summary_lines = [
        f"Returned {len(items)} of {total_count} items",
    ]
    if offset > 0:
        summary_lines.append(f"(showing items {offset}-{offset + len(items)})")
    if has_more:
        summary_lines.append(
            f"More available. "
            f"Use offset={offset + len(items)} limit={limit} for next page."
        )
    if drill_down_hint:
        summary_lines.append(f"💡 {drill_down_hint}")

    summary = " | ".join(summary_lines)

    # Build metadata
    metadata = {
        "operation": operation,
        "pagination_applied": True,
        "summary": summary,
    }

    return StructuredResult.success(
        data=items,
        metadata=metadata,
        pagination=pagination,
    )


def paginate_results(
    results: List[Any],
    args: dict,
    total_count: Optional[int] = None,
    operation: Optional[str] = None,
    drill_down_hint: Optional[str] = None,
    default_limit: int = 10,
    max_limit: int = 100,
) -> StructuredResult:
    """Convenience wrapper for paginating handler results from args dict.

    Args:
        results: List of items to paginate
        args: Handler args dict (expected to have 'limit' and 'offset' keys)
        total_count: Total count from database (if None, inferred from results)
        operation: Handler operation name
        drill_down_hint: Guidance for drilling down
        default_limit: Default limit if not in args (default 10)
        max_limit: Maximum allowed limit (default 100)

    Returns:
        StructuredResult with pagination

    Example:
        # In handler - super simple!
        results = await db.list_items(
            limit=min(args.get("limit", 10), 100),
            offset=args.get("offset", 0)
        )
        total = await db.count_items()
        return paginate_results(results, args, total_count=total)
    """
    limit = min(args.get("limit", default_limit), max_limit)
    offset = max(args.get("offset", 0), 0)

    return create_paginated_result(
        items=results,
        total_count=total_count,
        offset=offset,
        limit=limit,
        max_limit=max_limit,
        operation=operation,
        drill_down_hint=drill_down_hint,
    )
