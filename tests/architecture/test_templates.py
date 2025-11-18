"""Tests for document template system."""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add parent directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from athena.architecture.models import Specification, SpecType, SpecStatus, DocumentType
from athena.architecture.templates import TemplateManager, TemplateContext


@pytest.fixture
def template_manager(tmp_path):
    """Create template manager with temp directory."""
    # Use built-in templates
    return TemplateManager()


@pytest.fixture
def sample_spec():
    """Create sample OpenAPI specification."""
    openapi_content = """{
        "openapi": "3.0.0",
        "info": {
            "title": "User API",
            "version": "1.0.0",
            "description": "API for user management"
        },
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "description": "Get all users",
                    "responses": {
                        "200": {"description": "Success"}
                    }
                },
                "post": {
                    "summary": "Create user",
                    "responses": {
                        "201": {"description": "Created"}
                    }
                }
            }
        }
    }"""

    return Specification(
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content=openapi_content,
        description="API for user management",
    )


def test_template_manager_initialization(template_manager):
    """Test template manager initializes correctly."""
    assert template_manager is not None
    assert template_manager.templates_dir.exists()


def test_list_templates(template_manager):
    """Test listing available templates."""
    # Should have at least a few built-in templates
    all_templates = template_manager.list_templates()
    assert len(all_templates) >= 1

    # Should have default template
    assert any("default.md.j2" in t for t in all_templates)

    # Test category filtering
    api_templates = template_manager.list_templates(category="api")
    assert isinstance(api_templates, list)


def test_render_default_template(template_manager):
    """Test rendering default template."""
    context = TemplateContext(
        version="1.0.0",
        author="Test Author",
    )

    # Render using template string
    template_str = "# {{ version }}\n\n**Author:** {{ author }}"
    content = template_manager.render_string(template_str, context)

    assert "1.0.0" in content
    assert "Test Author" in content


def test_render_with_spec(template_manager, sample_spec):
    """Test rendering template with specification context."""
    context = TemplateContext(
        spec=sample_spec,
        version="2.0.0",
        author="API Team",
    )

    # Render using template string
    template_str = "# {{ spec.name }}\n\n{{ spec.description }}"
    content = template_manager.render_string(template_str, context)

    assert "User API" in content
    assert "API for user management" in content


def test_context_to_dict(sample_spec):
    """Test context conversion to dict."""
    context = TemplateContext(
        spec=sample_spec,
        project_id=5,
        version="3.0.0",
        author="Test",
        custom_data={"key": "value"},
    )

    data = context.to_dict()

    assert data["project_id"] == 5
    assert data["version"] == "3.0.0"
    assert data["author"] == "Test"
    assert data["key"] == "value"
    assert data["spec"]["name"] == "User API"


def test_custom_filters(template_manager):
    """Test custom Jinja2 filters."""
    context = TemplateContext()

    # Test to_snake_case filter
    template_str = "{{ 'UserAPIEndpoint' | to_snake_case }}"
    content = template_manager.render_string(template_str, context)
    assert "user_api_endpoint" in content

    # Test to_title_case filter
    template_str = "{{ 'hello world' | to_title_case }}"
    content = template_manager.render_string(template_str, context)
    assert "Hello World" in content


def test_from_json_filter(template_manager, sample_spec):
    """Test from_json filter."""
    context = TemplateContext(spec=sample_spec)

    # Parse spec content and extract info
    template_str = """
{% set spec_data = spec.content | from_json %}
Title: {{ spec_data.info.title }}
Version: {{ spec_data.info.version }}
"""
    content = template_manager.render_string(template_str, context)

    assert "Title: User API" in content
    assert "Version: 1.0.0" in content


def test_render_api_doc_template(template_manager, sample_spec):
    """Test rendering API documentation template."""
    # Skip if template doesn't exist
    try:
        context = TemplateContext(
            spec=sample_spec,
            version="1.0.0",
            author="API Team",
        )

        # This will use the default API template if it exists
        content = template_manager.render(DocumentType.API_DOC, context)

        # Check that key content is present
        assert "User API" in content
        assert "1.0.0" in content

    except ValueError:
        # Template not found - skip test
        pytest.skip("API documentation template not available")


def test_template_not_found(template_manager):
    """Test error when template doesn't exist."""
    context = TemplateContext()

    with pytest.raises(ValueError, match="Template not found"):
        template_manager.render(
            DocumentType.API_DOC,
            context,
            custom_template="nonexistent.md.j2"
        )


def test_render_with_empty_context(template_manager):
    """Test rendering with minimal context."""
    context = TemplateContext()

    template_str = "Version: {{ version }}"
    content = template_manager.render_string(template_str, context)

    assert "1.0.0" in content  # Default version


def test_render_technical_doc(template_manager, sample_spec):
    """Test rendering technical design document."""
    try:
        context = TemplateContext(
            spec=sample_spec,
            version="2.0.0",
            author="Engineering Team",
        )

        content = template_manager.render(DocumentType.TDD, context)

        # Should contain TDD structure
        assert "Technical Design Document" in content or "TDD" in content
        assert "User API" in content

    except ValueError:
        # Template not found - skip test
        pytest.skip("TDD template not available")
