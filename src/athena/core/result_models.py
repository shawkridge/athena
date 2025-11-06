"""Result models with confidence scoring for memory operations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Confidence levels for search results."""

    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"  # 0.7-0.9
    MEDIUM = "medium"  # 0.5-0.7
    LOW = "low"  # 0.3-0.5
    VERY_LOW = "very_low"  # 0.0-0.3


class ConfidenceScores(BaseModel):
    """Detailed confidence scoring breakdown."""

    semantic_relevance: float = Field(
        ..., ge=0, le=1, description="Semantic similarity score"
    )
    source_quality: float = Field(
        ..., ge=0, le=1, description="Quality of source memory"
    )
    recency: float = Field(
        ..., ge=0, le=1, description="Recency score (newer=higher)"
    )
    consistency: float = Field(
        ..., ge=0, le=1, description="Consistency with other memories"
    )
    completeness: float = Field(
        ..., ge=0, le=1, description="How complete the information is"
    )

    class Config:
        """Pydantic config."""

        use_enum_values = False

    def average(self) -> float:
        """Calculate average confidence score."""
        scores = [
            self.semantic_relevance,
            self.source_quality,
            self.recency,
            self.consistency,
            self.completeness,
        ]
        return sum(scores) / len(scores)

    def level(self) -> ConfidenceLevel:
        """Determine confidence level."""
        avg = self.average()
        if avg >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif avg >= 0.7:
            return ConfidenceLevel.HIGH
        elif avg >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif avg >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


class MemoryWithConfidence(BaseModel):
    """Memory result with confidence scoring."""

    memory_id: str = Field(..., description="Unique identifier for the memory")
    content: Any = Field(..., description="Memory content")
    confidence: float = Field(
        ..., ge=0, le=1, description="Overall confidence score (0-1)"
    )
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level")
    confidence_breakdown: ConfidenceScores = Field(
        ..., description="Detailed confidence scoring"
    )
    source_layer: str = Field(
        ..., description="Memory layer (episodic, semantic, etc.)"
    )
    retrieved_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic config."""

        use_enum_values = False


class SearchResultWithExplain(BaseModel):
    """Search result with explanation."""

    result: MemoryWithConfidence = Field(..., description="Search result")
    explanation: Optional[str] = Field(None, description="Explanation of ranking")
    reasoning: Optional[Dict[str, str]] = Field(
        None, description="Detailed reasoning breakdown"
    )

    class Config:
        """Pydantic config."""

        use_enum_values = False


class QueryExplanation(BaseModel):
    """Explanation of query routing and execution."""

    query: str = Field(..., description="Original query")
    query_type: str = Field(..., description="Classified query type")
    layers_queried: List[str] = Field(
        ..., description="Layers that were queried"
    )
    search_strategy: str = Field(..., description="Strategy used for search")
    total_candidates: int = Field(..., description="Total candidates considered")
    results_returned: int = Field(..., description="Final results returned")
    execution_time_ms: float = Field(..., description="Query execution time in ms")
    filtering_applied: List[str] = Field(
        default_factory=list, description="Filters applied to results"
    )
    ranking_method: Optional[str] = Field(None, description="Ranking method used")

    class Config:
        """Pydantic config."""

        use_enum_values = False
