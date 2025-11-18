"""Context assembly for document generation.

Intelligently gathers relevant specifications, ADRs, and constraints
to provide comprehensive context for AI-powered document generation.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..models import (
    Specification,
    DocumentType,
    SpecType,
    SpecStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerationContext:
    """Complete context for document generation.

    Assembles all relevant information needed to generate high-quality documentation.
    """
    # Primary sources
    primary_specs: List[Specification] = field(default_factory=list)

    # Supporting context
    related_specs: List[Specification] = field(default_factory=list)
    adrs: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)

    # Project metadata
    project_id: int = 1
    project_name: Optional[str] = None

    # Document metadata
    doc_type: Optional[DocumentType] = None
    target_audience: str = "technical"  # "technical", "business", "executive"
    detail_level: str = "comprehensive"  # "brief", "standard", "comprehensive"

    # Custom context
    custom_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for prompt rendering.

        Returns:
            Dictionary with all context data formatted for prompts
        """
        return {
            "project_id": self.project_id,
            "project_name": self.project_name or f"Project {self.project_id}",
            "doc_type": self.doc_type.value if self.doc_type else "unknown",
            "target_audience": self.target_audience,
            "detail_level": self.detail_level,
            "primary_specs": [self._spec_to_dict(spec) for spec in self.primary_specs],
            "related_specs": [self._spec_to_dict(spec) for spec in self.related_specs],
            "adrs": self.adrs,
            "constraints": self.constraints,
            **self.custom_context,
        }

    def _spec_to_dict(self, spec: Specification) -> Dict[str, Any]:
        """Convert specification to dictionary.

        Args:
            spec: Specification object

        Returns:
            Dictionary with spec data
        """
        # Handle both enum and string values
        spec_type_value = spec.spec_type.value if hasattr(spec.spec_type, 'value') else str(spec.spec_type)
        status_value = spec.status.value if hasattr(spec.status, 'value') else str(spec.status)

        return {
            "id": spec.id,
            "name": spec.name,
            "type": spec_type_value if spec.spec_type else "unknown",
            "version": spec.version,
            "description": spec.description or "",
            "content": spec.content,
            "status": status_value if spec.status else "unknown",
        }

    def get_summary(self) -> str:
        """Get a brief summary of the context.

        Returns:
            Summary string
        """
        parts = []

        if self.primary_specs:
            parts.append(f"{len(self.primary_specs)} primary spec(s)")
        if self.related_specs:
            parts.append(f"{len(self.related_specs)} related spec(s)")
        if self.adrs:
            parts.append(f"{len(self.adrs)} ADR(s)")
        if self.constraints:
            parts.append(f"{len(self.constraints)} constraint(s)")

        return ", ".join(parts) if parts else "empty context"


class ContextAssembler:
    """Assembles generation context from specifications and related artifacts.

    Intelligently selects relevant information based on document type and
    specification relationships.

    Example:
        >>> assembler = ContextAssembler(spec_store, adr_store)
        >>> context = assembler.assemble_for_spec(
        ...     spec_id=5,
        ...     doc_type=DocumentType.API_DOC,
        ...     include_related=True
        ... )
        >>> print(context.get_summary())
        "1 primary spec(s), 2 related spec(s), 3 ADR(s)"
    """

    def __init__(
        self,
        spec_store=None,
        adr_store=None,
        constraint_store=None
    ):
        """Initialize context assembler.

        Args:
            spec_store: Specification store instance
            adr_store: ADR store instance (optional)
            constraint_store: Constraint store instance (optional)
        """
        self.spec_store = spec_store
        self.adr_store = adr_store
        self.constraint_store = constraint_store

    def assemble_for_spec(
        self,
        spec_id: int,
        doc_type: DocumentType,
        include_related: bool = True,
        include_adrs: bool = True,
        include_constraints: bool = True,
        target_audience: str = "technical",
        detail_level: str = "comprehensive",
    ) -> GenerationContext:
        """Assemble context for generating documentation from a specification.

        Args:
            spec_id: Primary specification ID
            doc_type: Type of document to generate
            include_related: Include related specifications
            include_adrs: Include architecture decision records
            include_constraints: Include architectural constraints
            target_audience: Target audience level
            detail_level: Level of detail to include

        Returns:
            Generation context with all relevant information

        Example:
            >>> context = assembler.assemble_for_spec(
            ...     spec_id=5,
            ...     doc_type=DocumentType.API_DOC,
            ...     target_audience="technical"
            ... )
        """
        context = GenerationContext(
            doc_type=doc_type,
            target_audience=target_audience,
            detail_level=detail_level,
        )

        # Load primary specification
        if self.spec_store:
            primary_spec = self.spec_store.get(spec_id)
            if primary_spec:
                context.primary_specs.append(primary_spec)
                context.project_id = primary_spec.project_id

                # Include related specs if requested
                if include_related:
                    related = self._find_related_specs(primary_spec)
                    context.related_specs.extend(related)

                # Include ADRs if requested
                if include_adrs and self.adr_store:
                    adrs = self._find_related_adrs(primary_spec)
                    context.adrs.extend(adrs)

                # Include constraints if requested
                if include_constraints and self.constraint_store:
                    constraints = self._find_related_constraints(primary_spec)
                    context.constraints.extend(constraints)

        logger.info(f"Assembled context: {context.get_summary()}")
        return context

    def assemble_for_multiple_specs(
        self,
        spec_ids: List[int],
        doc_type: DocumentType,
        **kwargs
    ) -> GenerationContext:
        """Assemble context from multiple specifications.

        Useful for generating consolidated documentation like system architecture
        docs that span multiple specs.

        Args:
            spec_ids: List of specification IDs
            doc_type: Type of document to generate
            **kwargs: Additional arguments passed to assemble_for_spec

        Returns:
            Generation context with all specifications

        Example:
            >>> context = assembler.assemble_for_multiple_specs(
            ...     spec_ids=[5, 6, 7],
            ...     doc_type=DocumentType.HLD
            ... )
        """
        context = GenerationContext(
            doc_type=doc_type,
            target_audience=kwargs.get("target_audience", "technical"),
            detail_level=kwargs.get("detail_level", "comprehensive"),
        )

        if not self.spec_store:
            return context

        # Load all primary specs
        for spec_id in spec_ids:
            spec = self.spec_store.get(spec_id)
            if spec:
                context.primary_specs.append(spec)
                if not context.project_id or context.project_id == 1:
                    context.project_id = spec.project_id

        # Find common related specs, ADRs, and constraints
        if kwargs.get("include_related", True):
            for spec in context.primary_specs:
                related = self._find_related_specs(spec)
                # Only add if not already in primary specs
                for r in related:
                    if r.id not in [s.id for s in context.primary_specs]:
                        if r not in context.related_specs:
                            context.related_specs.append(r)

        if kwargs.get("include_adrs", True) and self.adr_store:
            for spec in context.primary_specs:
                adrs = self._find_related_adrs(spec)
                for adr in adrs:
                    if adr not in context.adrs:
                        context.adrs.append(adr)

        if kwargs.get("include_constraints", True) and self.constraint_store:
            for spec in context.primary_specs:
                constraints = self._find_related_constraints(spec)
                for constraint in constraints:
                    if constraint not in context.constraints:
                        context.constraints.append(constraint)

        logger.info(f"Assembled multi-spec context: {context.get_summary()}")
        return context

    def _find_related_specs(self, spec: Specification) -> List[Specification]:
        """Find specifications related to the given spec.

        Args:
            spec: Primary specification

        Returns:
            List of related specifications
        """
        related = []

        if not self.spec_store:
            return related

        # For API specs, find related database schemas
        if spec.spec_type == SpecType.OPENAPI:
            # Find Prisma/database specs in same project
            all_specs = self.spec_store.list_by_project(
                project_id=spec.project_id,
                spec_type=SpecType.PRISMA,
                limit=10
            )
            related.extend(all_specs)

        # For database specs, find related API specs
        elif spec.spec_type == SpecType.PRISMA:
            all_specs = self.spec_store.list_by_project(
                project_id=spec.project_id,
                spec_type=SpecType.OPENAPI,
                limit=10
            )
            related.extend(all_specs)

        # Use explicit relationships if available
        if hasattr(spec, 'related_spec_ids') and spec.related_spec_ids:
            for related_id in spec.related_spec_ids:
                related_spec = self.spec_store.get(related_id)
                if related_spec:
                    related.append(related_spec)

        return related

    def _find_related_adrs(self, spec: Specification) -> List[Dict[str, Any]]:
        """Find ADRs related to the specification.

        Args:
            spec: Primary specification

        Returns:
            List of related ADR dictionaries
        """
        adrs = []

        if not self.adr_store:
            return adrs

        # Use explicit relationships if available
        if hasattr(spec, 'related_adr_ids') and spec.related_adr_ids:
            for adr_id in spec.related_adr_ids:
                try:
                    adr = self.adr_store.get(adr_id)
                    if adr:
                        adrs.append({
                            "id": adr.id,
                            "title": getattr(adr, 'title', f"ADR {adr.id}"),
                            "decision": getattr(adr, 'decision', ""),
                            "status": getattr(adr, 'status', "accepted"),
                        })
                except Exception as e:
                    logger.warning(f"Failed to load ADR {adr_id}: {e}")

        return adrs

    def _find_related_constraints(self, spec: Specification) -> List[Dict[str, Any]]:
        """Find constraints related to the specification.

        Args:
            spec: Primary specification

        Returns:
            List of related constraint dictionaries
        """
        constraints = []

        if not self.constraint_store:
            return constraints

        # Use explicit relationships if available
        if hasattr(spec, 'implements_constraint_ids') and spec.implements_constraint_ids:
            for constraint_id in spec.implements_constraint_ids:
                try:
                    constraint = self.constraint_store.get(constraint_id)
                    if constraint:
                        constraints.append({
                            "id": constraint.id,
                            "name": getattr(constraint, 'name', f"Constraint {constraint.id}"),
                            "description": getattr(constraint, 'description', ""),
                            "type": getattr(constraint, 'type', "unknown"),
                        })
                except Exception as e:
                    logger.warning(f"Failed to load constraint {constraint_id}: {e}")

        return constraints
