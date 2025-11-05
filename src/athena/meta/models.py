"""Data models for meta-memory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExpertiseLevel(str, Enum):
    """Expertise levels for domains."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class DomainCoverage(BaseModel):
    """Coverage tracking for a knowledge domain."""

    id: Optional[int] = None
    domain: str  # react|authentication|testing|graphql|etc
    category: str  # technology|pattern|project-area|skill

    # Coverage metrics
    memory_count: int = 0
    episodic_count: int = 0
    procedural_count: int = 0
    entity_count: int = 0

    # Quality metrics
    avg_confidence: float = 0.0
    avg_usefulness: float = 0.0
    last_updated: Optional[datetime] = None

    # Gap analysis
    gaps: list[str] = Field(default_factory=list)  # Identified knowledge gaps
    strength_areas: list[str] = Field(default_factory=list)  # Strong areas

    # Metadata
    first_encounter: Optional[datetime] = None
    expertise_level: ExpertiseLevel = ExpertiseLevel.BEGINNER

    class Config:
        use_enum_values = True


class MemoryQuality(BaseModel):
    """Quality tracking for a memory."""

    memory_id: int
    memory_layer: str  # semantic|episodic|procedural|prospective|graph

    # Usage metrics
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    useful_count: int = 0

    # Quality scores
    usefulness_score: float = 0.0  # 0-1
    confidence: float = 1.0  # 0-1
    relevance_decay: float = 1.0  # 0-1

    # Provenance
    source: str = "user"  # user|inferred|learned|imported
    verified: bool = False


class KnowledgeTransfer(BaseModel):
    """Cross-project knowledge transfer tracking."""

    id: Optional[int] = None
    from_project_id: int
    to_project_id: int
    knowledge_item_id: int
    knowledge_layer: str
    transferred_at: datetime = Field(default_factory=datetime.now)
    applicability_score: float = 0.0  # How well it transferred
