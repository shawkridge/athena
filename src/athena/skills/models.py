"""Data models for skills system.

Defines Skill, SkillMetadata, and related data structures for representing
reusable code patterns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json


class SkillDomain(Enum):
    """Domain of skill application."""

    MEMORY = "memory"
    PLANNING = "planning"
    ANALYSIS = "analysis"
    INTEGRATION = "integration"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    GENERAL = "general"


@dataclass
class SkillParameter:
    """Definition of a skill parameter."""

    name: str
    type: str                              # 'str', 'int', 'List[str]', etc.
    description: str
    required: bool = True
    default: Optional[Any] = None
    example: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'required': self.required,
            'default': self.default,
            'example': self.example,
        }


@dataclass
class SkillMetadata:
    """Metadata describing a skill.

    Attributes:
        name: Unique skill identifier
        description: What the skill does
        domain: Primary domain of application
        parameters: Input parameters
        return_type: What the skill returns
        examples: Usage examples
        dependencies: Skills or modules this depends on
        quality_score: Confidence in skill (0-1)
        times_used: Number of times invoked
        success_rate: % successful invocations
        learned_from: Event ID or task that led to skill creation
        tags: Searchable tags
    """

    name: str
    description: str
    domain: SkillDomain
    parameters: List[SkillParameter]
    return_type: str
    examples: List[str]
    dependencies: List[str] = field(default_factory=list)
    quality_score: float = 0.8
    times_used: int = 0
    success_rate: float = 1.0
    learned_from: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            'name': self.name,
            'description': self.description,
            'domain': self.domain.value,
            'parameters': [p.to_dict() for p in self.parameters],
            'return_type': self.return_type,
            'examples': self.examples,
            'dependencies': self.dependencies,
            'quality_score': self.quality_score,
            'times_used': self.times_used,
            'success_rate': self.success_rate,
            'learned_from': self.learned_from,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> 'SkillMetadata':
        """Create from dictionary."""
        return cls(
            name=data['name'],
            description=data['description'],
            domain=SkillDomain(data['domain']),
            parameters=[SkillParameter(**p) for p in data['parameters']],
            return_type=data['return_type'],
            examples=data['examples'],
            dependencies=data.get('dependencies', []),
            quality_score=data.get('quality_score', 0.8),
            times_used=data.get('times_used', 0),
            success_rate=data.get('success_rate', 1.0),
            learned_from=data.get('learned_from'),
            tags=data.get('tags', []),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
        )


@dataclass
class Skill:
    """A reusable code pattern.

    Attributes:
        metadata: Skill metadata
        code: The actual implementation (Python source)
        entry_point: Function name to invoke
    """

    metadata: SkillMetadata
    code: str                              # Python source code
    entry_point: str                       # Function name to call

    @property
    def id(self) -> str:
        """Unique skill ID."""
        return self.metadata.name

    @property
    def quality(self) -> float:
        """Quality metric (0-1)."""
        return self.metadata.quality_score

    @property
    def usage_stats(self) -> Dict:
        """Usage statistics."""
        return {
            'times_used': self.metadata.times_used,
            'success_rate': self.metadata.success_rate,
            'quality': self.metadata.quality_score,
        }

    def update_usage(self, success: bool) -> None:
        """Update usage statistics after execution.

        Args:
            success: Whether execution succeeded
        """
        self.metadata.times_used += 1
        self.metadata.updated_at = datetime.now()

        # Update success rate
        old_rate = self.metadata.success_rate
        new_rate = (old_rate * (self.metadata.times_used - 1) + (1.0 if success else 0.0)) / self.metadata.times_used
        self.metadata.success_rate = new_rate

        # Update quality based on success rate
        if new_rate >= 0.9:
            self.metadata.quality_score = 0.9 + (new_rate - 0.9) * 0.11
        else:
            self.metadata.quality_score = 0.7 + new_rate * 0.2

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'metadata': self.metadata.to_dict(),
            'code': self.code,
            'entry_point': self.entry_point,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Skill':
        """Create from dictionary."""
        return cls(
            metadata=SkillMetadata.from_dict(data['metadata']),
            code=data['code'],
            entry_point=data['entry_point'],
        )

    def __repr__(self) -> str:
        return f"Skill({self.id}, quality={self.quality:.2f}, used={self.metadata.times_used})"


@dataclass
class SkillMatch:
    """Result of skill matching against a task."""

    skill: Skill
    relevance: float                       # 0-1 confidence
    reason: str                            # Why this skill matches
    parameters: Dict[str, Any] = field(default_factory=dict)  # Suggested parameter values

    def __repr__(self) -> str:
        return f"SkillMatch({self.skill.id}, relevance={self.relevance:.2f})"
