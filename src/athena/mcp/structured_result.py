"""Unified result format for MCP tool responses."""

import json
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime

from mcp.types import TextContent


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
