"""Request/response models for Athena HTTP API."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class OperationRequest(BaseModel):
    """Generic request model for any operation."""

    operation: str = Field(..., description="Operation name (e.g., 'recall', 'remember')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")

    class Config:
        schema_extra = {
            "example": {
                "operation": "recall",
                "params": {
                    "query": "authentication patterns",
                    "k": 5
                }
            }
        }


class OperationResponse(BaseModel):
    """Generic response model for any operation."""

    success: bool = Field(..., description="Whether operation succeeded")
    data: Any = Field(default=None, description="Operation result data")
    error: Optional[str] = Field(default=None, description="Error message if operation failed")
    operation: str = Field(..., description="Name of operation that was executed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {"result": "some data"},
                "error": None,
                "operation": "recall",
                "timestamp": "2025-11-06T09:00:00",
                "execution_time_ms": 45.2
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status (healthy/degraded/unhealthy)")
    version: str = Field(..., description="Athena version")
    uptime_seconds: float = Field(..., description="Uptime in seconds")
    database_size_mb: float = Field(..., description="Database size in MB")
    operations_count: int = Field(..., description="Total operations supported")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime_seconds": 3600.0,
                "database_size_mb": 50.2,
                "operations_count": 228,
                "timestamp": "2025-11-06T09:00:00"
            }
        }


class InfoResponse(BaseModel):
    """API info response."""

    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    documentation_url: str = Field(..., description="URL to documentation")
    supported_operations: List[str] = Field(..., description="List of supported operations")

    class Config:
        schema_extra = {
            "example": {
                "name": "Athena HTTP API",
                "version": "1.0.0",
                "description": "HTTP interface to Athena memory system",
                "documentation_url": "/docs",
                "supported_operations": ["recall", "remember", "forget", "consolidate", "..."]
            }
        }


class ErrorDetail(BaseModel):
    """Error detail in response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Specific operation request/response models for better type safety

class RecallRequest(BaseModel):
    """Request for recall operation."""

    query: str = Field(..., description="Search query")
    k: int = Field(default=5, description="Number of results to return")
    memory_type: Optional[str] = Field(default=None, description="Filter by memory type")


class RememberRequest(BaseModel):
    """Request for remember operation."""

    content: str = Field(..., description="Content to remember")
    memory_type: str = Field(..., description="Type of memory (fact/pattern/decision/context)")
    tags: List[str] = Field(default_factory=list, description="Tags for the memory")
    importance: Optional[float] = Field(default=None, description="Importance score 0-1")


class ConsolidateRequest(BaseModel):
    """Request for consolidation operation."""

    strategy: str = Field(default="balanced", description="Consolidation strategy")
    days_back: Optional[int] = Field(default=7, description="Days to consolidate")
    dry_run: bool = Field(default=False, description="Preview consolidation without executing")


class RecallEventsRequest(BaseModel):
    """Request for recall events operation."""

    query: str = Field(..., description="Search query")
    days: int = Field(default=7, description="Number of days to search")
    limit: int = Field(default=10, description="Maximum results to return")


class TaskCreateRequest(BaseModel):
    """Request for task creation."""

    content: str = Field(..., description="Task description")
    priority: str = Field(default="medium", description="Task priority")
    project_id: Optional[int] = Field(default=None, description="Associated project ID")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")


class GoalSetRequest(BaseModel):
    """Request for goal setting."""

    content: str = Field(..., description="Goal description")
    priority: str = Field(default="medium", description="Goal priority")
    deadline: Optional[datetime] = Field(default=None, description="Goal deadline")
