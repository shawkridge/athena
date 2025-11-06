"""Pydantic models for memory system."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class MemoryType(str, Enum):
    """Memory classification types."""

    FACT = "fact"  # Concrete information
    PATTERN = "pattern"  # Coding conventions
    DECISION = "decision"  # Architectural decisions
    CONTEXT = "context"  # Project state


class ConsolidationState(str, Enum):
    """Memory consolidation state (based on neuroscience research)."""

    UNCONSOLIDATED = "unconsolidated"  # New memory, not yet stable
    CONSOLIDATING = "consolidating"    # Being processed for long-term storage
    CONSOLIDATED = "consolidated"      # Stable long-term memory
    LABILE = "labile"                 # Retrieved, temporarily open for modification
    RECONSOLIDATING = "reconsolidating"  # Being updated/strengthened
    SUPERSEDED = "superseded"          # Replaced by newer version


class Memory(BaseModel):
    """Memory record with metadata."""

    id: Optional[int] = None
    project_id: int
    content: str
    memory_type: MemoryType
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    last_retrieved: Optional[datetime] = None  # For reconsolidation window tracking
    access_count: int = 0
    usefulness_score: float = 0.0
    embedding: Optional[list[float]] = None

    # Reconsolidation fields
    consolidation_state: ConsolidationState = ConsolidationState.CONSOLIDATED
    superseded_by: Optional[int] = None  # ID of memory that replaced this one
    version: int = 1  # Version number for tracking history

    model_config = ConfigDict(use_enum_values=True)


class Project(BaseModel):
    """Project with memory space."""

    id: Optional[int] = None
    name: str
    path: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    memory_count: int = 0


class MemorySearchResult(BaseModel):
    """Search result with relevance score."""

    memory: Memory
    similarity: float
    rank: int
    metadata: Optional[dict] = None  # For storing additional context (e.g., reranking scores)