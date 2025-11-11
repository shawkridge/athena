"""API registry and discovery for MemoryAPI.

This module provides a dynamic registry of available APIs that agents can discover
through filesystem inspection. It enables progressive disclosure of capabilities
without exposing all APIs at once.

Usage:
    registry = APIRegistry.create()
    apis = registry.discover_apis()

    for api in apis:
        print(f"{api.name}: {api.description}")
        print(f"  Parameters: {api.parameters}")
"""

import inspect
import logging
from dataclasses import dataclass, asdict
from typing import Any, List, Dict, Optional, Type, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class APICategory(str, Enum):
    """API categories for organization and discovery."""

    CORE = "core"  # Core remember/recall/forget operations
    EPISODIC = "episodic"  # Event-based memories
    SEMANTIC = "semantic"  # Knowledge and facts
    PROCEDURAL = "procedural"  # Workflows and procedures
    PROSPECTIVE = "prospective"  # Tasks and goals
    GRAPH = "graph"  # Knowledge graph operations
    CONSOLIDATION = "consolidation"  # Pattern extraction
    META = "meta"  # Meta-memory and health
    UTILITY = "utility"  # Utility operations


class APISecurityLevel(str, Enum):
    """Security level for API access control."""

    PUBLIC = "public"  # Available to all agents
    PROTECTED = "protected"  # Requires authentication
    PRIVATE = "private"  # Internal only


@dataclass
class APIParameter:
    """API parameter specification."""

    name: str
    type_name: str
    required: bool
    default: Optional[Any] = None
    description: str = ""
    options: Optional[List[str]] = None  # For enum-like parameters

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class APISpecification:
    """Complete specification for an API method."""

    name: str  # Method name (e.g., "remember", "recall")
    category: APICategory  # API category
    description: str  # Human-readable description
    parameters: List[APIParameter]  # Parameters
    return_type: str  # Return type
    return_description: str  # What the return value represents
    security_level: APISecurityLevel = APISecurityLevel.PUBLIC
    tags: List[str] = None  # Keywords for search
    examples: List[str] = None  # Usage examples
    since_version: str = "1.0"  # Version when API was introduced
    deprecated: bool = False  # Deprecation flag

    def __post_init__(self):
        """Initialize defaults."""
        if self.tags is None:
            self.tags = []
        if self.examples is None:
            self.examples = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "return_description": self.return_description,
            "security_level": self.security_level.value,
            "tags": self.tags,
            "examples": self.examples,
            "since_version": self.since_version,
            "deprecated": self.deprecated,
        }


class APIRegistry:
    """Registry of available APIs with discovery capabilities.

    This registry maintains specifications for all MemoryAPI methods,
    enabling dynamic discovery by agents.
    """

    def __init__(self):
        """Initialize API registry."""
        self.apis: Dict[str, APISpecification] = {}
        self._init_core_apis()

    def _init_core_apis(self):
        """Initialize specification for all core APIs."""

        # ===== CORE OPERATIONS =====

        self.register(
            APISpecification(
                name="remember",
                category=APICategory.CORE,
                description="Store content in memory",
                parameters=[
                    APIParameter(
                        name="content",
                        type_name="str",
                        required=True,
                        description="Content to store",
                    ),
                    APIParameter(
                        name="memory_type",
                        type_name="str",
                        required=False,
                        default="semantic",
                        description="Type of memory",
                        options=["semantic", "event", "procedure", "task"],
                    ),
                    APIParameter(
                        name="context",
                        type_name="Dict[str, Any]",
                        required=False,
                        description="Optional metadata context",
                    ),
                    APIParameter(
                        name="tags",
                        type_name="List[str]",
                        required=False,
                        description="Tags for categorization",
                    ),
                ],
                return_type="int",
                return_description="Memory ID",
                tags=["store", "memory", "basic"],
                examples=[
                    'api.remember("Important finding")',
                    'api.remember("Bug report", tags=["bug", "critical"])',
                ],
            )
        )

        self.register(
            APISpecification(
                name="recall",
                category=APICategory.CORE,
                description="Retrieve memories matching query",
                parameters=[
                    APIParameter(
                        name="query",
                        type_name="str",
                        required=True,
                        description="Search query",
                    ),
                    APIParameter(
                        name="limit",
                        type_name="int",
                        required=False,
                        default=5,
                        description="Maximum results",
                    ),
                    APIParameter(
                        name="context",
                        type_name="Dict[str, Any]",
                        required=False,
                        description="Optional context for routing",
                    ),
                ],
                return_type="Dict[str, Any]",
                return_description="Retrieved memories with scores",
                tags=["retrieve", "search", "basic"],
                examples=[
                    'api.recall("recent findings")',
                    'api.recall("parser bugs", limit=10)',
                ],
            )
        )

        self.register(
            APISpecification(
                name="forget",
                category=APICategory.CORE,
                description="Delete a memory",
                parameters=[
                    APIParameter(
                        name="memory_id",
                        type_name="int",
                        required=True,
                        description="Memory ID to delete",
                    ),
                ],
                return_type="bool",
                return_description="True if deletion successful",
                tags=["delete", "memory"],
                examples=['api.forget(42)'],
            )
        )

        # ===== EPISODIC OPERATIONS =====

        self.register(
            APISpecification(
                name="remember_event",
                category=APICategory.EPISODIC,
                description="Store a temporal event",
                parameters=[
                    APIParameter(
                        name="event_type",
                        type_name="str",
                        required=True,
                        description="Type of event",
                        options=["action", "decision", "observation", "error", "success"],
                    ),
                    APIParameter(
                        name="content",
                        type_name="str",
                        required=True,
                        description="Event description",
                    ),
                    APIParameter(
                        name="outcome",
                        type_name="str",
                        required=False,
                        description="Event outcome",
                        options=["success", "failure", "partial", "unknown"],
                    ),
                    APIParameter(
                        name="context",
                        type_name="Dict[str, Any]",
                        required=False,
                        description="Event context (files, metadata)",
                    ),
                ],
                return_type="int",
                return_description="Event ID",
                tags=["event", "temporal"],
                examples=[
                    'api.remember_event("action", "Ran tests", outcome="success")',
                ],
            )
        )

        self.register(
            APISpecification(
                name="recall_events",
                category=APICategory.EPISODIC,
                description="Retrieve events from episodic memory",
                parameters=[
                    APIParameter(
                        name="query",
                        type_name="str",
                        required=False,
                        description="Search query",
                    ),
                    APIParameter(
                        name="event_type",
                        type_name="str",
                        required=False,
                        description="Filter by event type",
                    ),
                    APIParameter(
                        name="limit",
                        type_name="int",
                        required=False,
                        default=10,
                        description="Maximum results",
                    ),
                ],
                return_type="List[Dict[str, Any]]",
                return_description="List of events",
                tags=["event", "temporal"],
                examples=['api.recall_events(event_type="action", limit=20)'],
            )
        )

        # ===== PROCEDURAL OPERATIONS =====

        self.register(
            APISpecification(
                name="remember_procedure",
                category=APICategory.PROCEDURAL,
                description="Store a reusable procedure/workflow",
                parameters=[
                    APIParameter(
                        name="name",
                        type_name="str",
                        required=True,
                        description="Procedure name",
                    ),
                    APIParameter(
                        name="steps",
                        type_name="List[str]",
                        required=True,
                        description="List of steps",
                    ),
                    APIParameter(
                        name="category",
                        type_name="str",
                        required=False,
                        default="general",
                        description="Procedure category",
                        options=["general", "analysis", "optimization", "debugging", "testing"],
                    ),
                    APIParameter(
                        name="context",
                        type_name="Dict[str, Any]",
                        required=False,
                        description="Optional metadata",
                    ),
                ],
                return_type="int",
                return_description="Procedure ID",
                tags=["procedure", "workflow", "reuse"],
                examples=['api.remember_procedure("run_tests", ["pytest tests/", "check coverage"])'],
            )
        )

        self.register(
            APISpecification(
                name="recall_procedures",
                category=APICategory.PROCEDURAL,
                description="Find procedures matching query",
                parameters=[
                    APIParameter(
                        name="query",
                        type_name="str",
                        required=True,
                        description="Search query",
                    ),
                    APIParameter(
                        name="limit",
                        type_name="int",
                        required=False,
                        default=5,
                        description="Maximum results",
                    ),
                ],
                return_type="List[Dict[str, Any]]",
                return_description="List of procedures",
                tags=["procedure", "workflow"],
                examples=['api.recall_procedures("testing workflow")'],
            )
        )

        # ===== PROSPECTIVE OPERATIONS =====

        self.register(
            APISpecification(
                name="remember_task",
                category=APICategory.PROSPECTIVE,
                description="Store a task or goal",
                parameters=[
                    APIParameter(
                        name="name",
                        type_name="str",
                        required=True,
                        description="Task name",
                    ),
                    APIParameter(
                        name="deadline",
                        type_name="datetime",
                        required=False,
                        description="Optional deadline",
                    ),
                    APIParameter(
                        name="priority",
                        type_name="str",
                        required=False,
                        default="medium",
                        description="Priority level",
                        options=["low", "medium", "high", "critical"],
                    ),
                    APIParameter(
                        name="context",
                        type_name="Dict[str, Any]",
                        required=False,
                        description="Optional metadata",
                    ),
                ],
                return_type="int",
                return_description="Task ID",
                tags=["task", "goal", "prospective"],
                examples=['api.remember_task("Review code", priority="high")'],
            )
        )

        self.register(
            APISpecification(
                name="recall_tasks",
                category=APICategory.PROSPECTIVE,
                description="Retrieve tasks with optional filters",
                parameters=[
                    APIParameter(
                        name="status",
                        type_name="str",
                        required=False,
                        description="Filter by status",
                        options=["pending", "active", "completed", "blocked"],
                    ),
                    APIParameter(
                        name="limit",
                        type_name="int",
                        required=False,
                        default=10,
                        description="Maximum results",
                    ),
                ],
                return_type="List[Dict[str, Any]]",
                return_description="List of tasks",
                tags=["task", "goal"],
                examples=['api.recall_tasks(status="pending")'],
            )
        )

        # ===== GRAPH OPERATIONS =====

        self.register(
            APISpecification(
                name="remember_entity",
                category=APICategory.GRAPH,
                description="Store entity in knowledge graph",
                parameters=[
                    APIParameter(
                        name="name",
                        type_name="str",
                        required=True,
                        description="Entity name",
                    ),
                    APIParameter(
                        name="entity_type",
                        type_name="str",
                        required=True,
                        description="Entity type",
                        options=["concept", "person", "place", "artifact", "system", "process"],
                    ),
                    APIParameter(
                        name="context",
                        type_name="Dict[str, Any]",
                        required=False,
                        description="Optional metadata",
                    ),
                ],
                return_type="int",
                return_description="Entity ID",
                tags=["graph", "entity", "knowledge"],
                examples=['api.remember_entity("parser.py", "artifact")'],
            )
        )

        self.register(
            APISpecification(
                name="relate_entities",
                category=APICategory.GRAPH,
                description="Create relation between entities",
                parameters=[
                    APIParameter(
                        name="source_id",
                        type_name="int",
                        required=True,
                        description="Source entity ID",
                    ),
                    APIParameter(
                        name="target_id",
                        type_name="int",
                        required=True,
                        description="Target entity ID",
                    ),
                    APIParameter(
                        name="relation_type",
                        type_name="str",
                        required=True,
                        description="Type of relation",
                        options=["calls", "depends_on", "contains", "belongs_to"],
                    ),
                    APIParameter(
                        name="context",
                        type_name="Dict[str, Any]",
                        required=False,
                        description="Optional context",
                    ),
                ],
                return_type="int",
                return_description="Relation ID",
                tags=["graph", "relation"],
                examples=['api.relate_entities(1, 2, "calls")'],
            )
        )

        self.register(
            APISpecification(
                name="query_graph",
                category=APICategory.GRAPH,
                description="Query knowledge graph",
                parameters=[
                    APIParameter(
                        name="query",
                        type_name="str",
                        required=True,
                        description="Search query",
                    ),
                    APIParameter(
                        name="limit",
                        type_name="int",
                        required=False,
                        default=5,
                        description="Maximum results",
                    ),
                ],
                return_type="Dict[str, Any]",
                return_description="Graph entities and relations",
                tags=["graph", "query"],
                examples=['api.query_graph("parser implementation")'],
            )
        )

        # ===== CONSOLIDATION OPERATIONS =====

        self.register(
            APISpecification(
                name="consolidate",
                category=APICategory.CONSOLIDATION,
                description="Extract patterns from episodic memory",
                parameters=[
                    APIParameter(
                        name="strategy",
                        type_name="str",
                        required=False,
                        default="balanced",
                        description="Consolidation strategy",
                        options=["balanced", "speed", "quality", "minimal"],
                    ),
                    APIParameter(
                        name="days_back",
                        type_name="int",
                        required=False,
                        default=7,
                        description="Days of history to consolidate",
                    ),
                ],
                return_type="Dict[str, Any]",
                return_description="Consolidation results",
                tags=["consolidation", "patterns"],
                examples=['api.consolidate(strategy="balanced", days_back=7)'],
            )
        )

        # ===== META OPERATIONS =====

        self.register(
            APISpecification(
                name="get_memory_stats",
                category=APICategory.META,
                description="Get memory system statistics",
                parameters=[],
                return_type="Dict[str, Any]",
                return_description="Stats about all memory layers",
                tags=["meta", "stats"],
                examples=['stats = api.get_memory_stats()'],
            )
        )

        self.register(
            APISpecification(
                name="health_check",
                category=APICategory.META,
                description="Check health of memory system",
                parameters=[],
                return_type="Dict[str, Any]",
                return_description="Health status",
                tags=["meta", "health"],
                examples=['health = api.health_check()'],
            )
        )

    def register(self, spec: APISpecification) -> None:
        """Register an API specification.

        Args:
            spec: APISpecification to register
        """
        self.apis[spec.name] = spec
        logger.debug(f"Registered API: {spec.name}")

    def discover_apis(
        self,
        category: Optional[APICategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[APISpecification]:
        """Discover available APIs.

        Args:
            category: Optional category filter
            tags: Optional tag filters (match any)

        Returns:
            List of matching API specifications
        """
        results = list(self.apis.values())

        # Filter by category
        if category:
            results = [api for api in results if api.category == category]

        # Filter by tags
        if tags:
            results = [api for api in results if any(tag in api.tags for tag in tags)]

        # Sort by category then name
        results.sort(key=lambda api: (api.category.value, api.name))

        return results

    def get_api(self, name: str) -> Optional[APISpecification]:
        """Get specific API by name.

        Args:
            name: API method name

        Returns:
            APISpecification or None if not found
        """
        return self.apis.get(name)

    def get_categories(self) -> List[APICategory]:
        """Get all API categories with APIs.

        Returns:
            Sorted list of categories
        """
        categories = set(api.category for api in self.apis.values())
        return sorted(categories, key=lambda c: c.value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire registry to dictionary.

        Returns:
            Dictionary representation of all APIs
        """
        return {
            name: spec.to_dict()
            for name, spec in self.apis.items()
        }

    @staticmethod
    def create() -> "APIRegistry":
        """Create and initialize API registry.

        Returns:
            Initialized APIRegistry instance
        """
        return APIRegistry()
