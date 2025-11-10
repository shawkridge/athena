"""Data models for knowledge graph."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""

    PROJECT = "Project"
    PHASE = "Phase"
    TASK = "Task"
    FILE = "File"
    FUNCTION = "Function"
    CONCEPT = "Concept"
    COMPONENT = "Component"
    PERSON = "Person"
    DECISION = "Decision"
    PATTERN = "Pattern"
    AGENT = "Agent"
    SKILL = "Skill"


class RelationType(str, Enum):
    """Types of relations between entities."""

    CONTAINS = "contains"  # A contains B (project contains phase)
    DEPENDS_ON = "depends_on"  # A depends on B
    IMPLEMENTS = "implements"  # A implements B
    TESTS = "tests"  # A tests B
    CAUSED_BY = "caused_by"  # A caused by B
    RESULTED_IN = "resulted_in"  # A resulted in B
    RELATES_TO = "relates_to"  # General relation
    ACTIVE_IN = "active_in"  # Project active in directory
    ASSIGNED_TO = "assigned_to"  # Task assigned to agent
    HAS_SKILL = "has_skill"  # Agent has skill


class Entity(BaseModel):
    """Entity in knowledge graph (node)."""

    id: Optional[int] = None
    name: str
    entity_type: EntityType
    project_id: Optional[int] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class Relation(BaseModel):
    """Relation between entities (edge)."""

    id: Optional[int] = None
    from_entity_id: int
    to_entity_id: int
    relation_type: RelationType
    strength: float = 1.0
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=datetime.now)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class Observation(BaseModel):
    """Observation about an entity (fact)."""

    id: Optional[int] = None
    entity_id: int
    content: str
    observation_type: Optional[str] = None  # status|property|note|metric
    confidence: float = 1.0
    source: str = "user"  # user|inferred|learned|imported
    timestamp: datetime = Field(default_factory=datetime.now)
    superseded_by: Optional[int] = None
