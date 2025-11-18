"""Template manager for document generation.

Handles Jinja2 template rendering with context data from specifications and other sources.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

try:
    from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from ..models import Specification, Document, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


@dataclass
class TemplateContext:
    """Context data for template rendering.

    Provides all the data needed to render a document template from a specification.
    """
    # Source specification
    spec: Optional[Specification] = None

    # Document metadata
    project_id: int = 1
    version: str = "1.0.0"
    author: Optional[str] = None

    # Custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)

    # Generated timestamp
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dict for template rendering.

        Returns:
            Dictionary with all context data
        """
        data = {
            "project_id": self.project_id,
            "version": self.version,
            "author": self.author or "Unknown",
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "spec": None,
        }

        # Add spec data if available
        if self.spec:
            data["spec"] = {
                "name": self.spec.name,
                "version": self.spec.version,
                "spec_type": self.spec.spec_type,
                "description": self.spec.description or "",
                "content": self.spec.content,
            }

        # Merge custom data
        data.update(self.custom_data)

        return data


class TemplateManager:
    """Manages document templates and rendering.

    Uses Jinja2 for template rendering with built-in templates for common document types.

    Example:
        >>> manager = TemplateManager()
        >>> context = TemplateContext(
        ...     spec=openapi_spec,
        ...     version="1.0.0",
        ...     author="Team"
        ... )
        >>> content = manager.render(DocumentType.API_DOC, context)
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize template manager.

        Args:
            templates_dir: Custom templates directory (default: built-in templates)
        """
        if not JINJA2_AVAILABLE:
            raise ImportError("jinja2 is required for template rendering. Install with: pip install jinja2")

        # Use built-in templates if no custom directory provided
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "builtin"

        self.templates_dir = templates_dir
        self._ensure_templates_directory()

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters['to_snake_case'] = self._to_snake_case
        self.env.filters['to_title_case'] = self._to_title_case
        self.env.filters['from_json'] = self._from_json

        logger.info(f"Template manager initialized with templates from: {self.templates_dir}")

    def _ensure_templates_directory(self):
        """Create templates directory and subdirectories if they don't exist."""
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created templates directory: {self.templates_dir}")

        # Create subdirectories for different document categories
        categories = ["product", "technical", "architecture", "api", "operational", "change"]
        for category in categories:
            category_dir = self.templates_dir / category
            if not category_dir.exists():
                category_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        doc_type: DocumentType,
        context: TemplateContext,
        custom_template: Optional[str] = None
    ) -> str:
        """Render a document from a template.

        Args:
            doc_type: Type of document to generate
            context: Context data for rendering
            custom_template: Optional custom template name (overrides default)

        Returns:
            Rendered document content as Markdown string

        Raises:
            ValueError: If template not found

        Example:
            >>> manager = TemplateManager()
            >>> context = TemplateContext(spec=spec, version="1.0.0")
            >>> content = manager.render(DocumentType.API_DOC, context)
        """
        # Get template name
        template_name = custom_template or self._get_default_template_name(doc_type)

        # Load template
        try:
            template = self.env.get_template(template_name)
        except Exception as e:
            logger.error(f"Template not found: {template_name}")
            raise ValueError(f"Template not found: {template_name}") from e

        # Render with context
        context_dict = context.to_dict()
        rendered = template.render(**context_dict)

        logger.info(f"Rendered document using template: {template_name}")
        return rendered

    def render_string(self, template_string: str, context: TemplateContext) -> str:
        """Render a document from a template string.

        Args:
            template_string: Jinja2 template as string
            context: Context data for rendering

        Returns:
            Rendered document content

        Example:
            >>> manager = TemplateManager()
            >>> template = "# {{ spec.name }}\\n\\n{{ spec.description }}"
            >>> content = manager.render_string(template, context)
        """
        template = self.env.from_string(template_string)
        context_dict = context.to_dict()
        return template.render(**context_dict)

    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """List available templates.

        Args:
            category: Optional category filter (e.g., "api", "technical")

        Returns:
            List of template names

        Example:
            >>> manager.list_templates(category="api")
            ['api/openapi.md.j2', 'api/rest-guide.md.j2']
        """
        templates = []

        if category:
            category_dir = self.templates_dir / category
            if category_dir.exists():
                for template_file in category_dir.glob("*.j2"):
                    templates.append(f"{category}/{template_file.name}")
        else:
            # List all templates
            for template_file in self.templates_dir.rglob("*.j2"):
                relative_path = template_file.relative_to(self.templates_dir)
                templates.append(str(relative_path))

        return sorted(templates)

    def _get_default_template_name(self, doc_type: DocumentType) -> str:
        """Get default template name for a document type.

        Args:
            doc_type: Document type

        Returns:
            Template file name (e.g., "api/openapi.md.j2")
        """
        # Map document types to template files
        template_map = {
            # API Documentation
            DocumentType.API_DOC: "api/openapi.md.j2",
            DocumentType.API_GUIDE: "api/integration-guide.md.j2",
            DocumentType.SDK_DOC: "api/sdk-reference.md.j2",

            # Product Documents
            DocumentType.PRD_LEAN: "product/prd-lean.md.j2",
            DocumentType.PRD_AGILE: "product/prd-agile.md.j2",
            DocumentType.PRD_PROBLEM: "product/prd-problem.md.j2",
            DocumentType.MRD: "product/mrd.md.j2",

            # Technical Documents
            DocumentType.TDD: "technical/tdd.md.j2",
            DocumentType.HLD: "technical/hld.md.j2",
            DocumentType.LLD: "technical/lld.md.j2",

            # Architecture Documents
            DocumentType.ARC42: "architecture/arc42.md.j2",
            DocumentType.C4_CONTEXT: "architecture/c4-context.md.j2",
            DocumentType.C4_CONTAINER: "architecture/c4-container.md.j2",
            DocumentType.C4_COMPONENT: "architecture/c4-component.md.j2",

            # Operational Documents
            DocumentType.RUNBOOK: "operational/runbook.md.j2",
            DocumentType.DEPLOYMENT_GUIDE: "operational/deployment.md.j2",
            DocumentType.TROUBLESHOOTING: "operational/troubleshooting.md.j2",

            # Change Documents
            DocumentType.CHANGELOG: "change/changelog.md.j2",
            DocumentType.MIGRATION_GUIDE: "change/migration.md.j2",
            DocumentType.UPGRADE_GUIDE: "change/upgrade.md.j2",
        }

        return template_map.get(doc_type, "default.md.j2")

    @staticmethod
    def _to_snake_case(text: str) -> str:
        """Convert text to snake_case.

        Args:
            text: Input text

        Returns:
            snake_case version
        """
        import re
        # Replace spaces and hyphens with underscores
        text = text.replace(" ", "_").replace("-", "_")
        # Insert underscore before uppercase letters (handles acronyms)
        # Pattern: insert _ before uppercase that follows lowercase OR before uppercase that precedes lowercase
        text = re.sub(r'([a-z])([A-Z])', r'\1_\2', text)  # camelCase -> camel_Case
        text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', text)  # APIEndpoint -> API_Endpoint
        # Convert to lowercase
        text = text.lower()
        # Remove duplicate underscores
        text = re.sub(r'_+', '_', text).strip('_')
        return text

    @staticmethod
    def _to_title_case(text: str) -> str:
        """Convert text to Title Case.

        Args:
            text: Input text

        Returns:
            Title Case version
        """
        return text.title()

    @staticmethod
    def _from_json(json_string: str) -> Any:
        """Parse JSON string to Python object.

        Args:
            json_string: JSON string

        Returns:
            Parsed Python object (dict/list)
        """
        import json
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            return {}
