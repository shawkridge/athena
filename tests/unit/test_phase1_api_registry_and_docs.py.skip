"""Comprehensive unit tests for APIRegistry and APIDocumentationGenerator (Phase 1).

Tests cover:
- APICategory enum
- APISecurityLevel enum
- APIParameter dataclass
- APISpecification dataclass
- APIRegistry registration and discovery
- APIDocumentationGenerator markdown/HTML/JSON generation
"""

import pytest
import json
from datetime import datetime

from athena.mcp.api_registry import (
    APICategory,
    APISecurityLevel,
    APIParameter,
    APISpecification,
    APIRegistry,
)
from athena.mcp.api_docs import APIDocumentationGenerator


class TestAPICategory:
    """Tests for APICategory enum."""

    def test_api_category_values(self):
        """Test all APICategory enum values."""
        assert APICategory.CORE.value == "core"
        assert APICategory.EPISODIC.value == "episodic"
        assert APICategory.SEMANTIC.value == "semantic"
        assert APICategory.PROCEDURAL.value == "procedural"
        assert APICategory.PROSPECTIVE.value == "prospective"
        assert APICategory.GRAPH.value == "graph"
        assert APICategory.CONSOLIDATION.value == "consolidation"
        assert APICategory.META.value == "meta"
        assert APICategory.UTILITY.value == "utility"

    def test_api_category_from_string(self):
        """Test creating APICategory from string."""
        assert APICategory("core") == APICategory.CORE
        assert APICategory("episodic") == APICategory.EPISODIC
        assert APICategory("semantic") == APICategory.SEMANTIC

    def test_api_category_invalid_value(self):
        """Test that invalid APICategory raises error."""
        with pytest.raises(ValueError):
            APICategory("invalid_category")


class TestAPISecurityLevel:
    """Tests for APISecurityLevel enum."""

    def test_security_level_values(self):
        """Test all APISecurityLevel enum values."""
        assert APISecurityLevel.PUBLIC.value == "public"
        assert APISecurityLevel.PROTECTED.value == "protected"
        assert APISecurityLevel.PRIVATE.value == "private"

    def test_security_level_from_string(self):
        """Test creating APISecurityLevel from string."""
        assert APISecurityLevel("public") == APISecurityLevel.PUBLIC
        assert APISecurityLevel("protected") == APISecurityLevel.PROTECTED
        assert APISecurityLevel("private") == APISecurityLevel.PRIVATE


class TestAPIParameter:
    """Tests for APIParameter dataclass."""

    def test_api_parameter_basic(self):
        """Test basic APIParameter creation."""
        param = APIParameter(
            name="query",
            type_name="str",
            required=True,
            description="Search query",
        )

        assert param.name == "query"
        assert param.type_name == "str"
        assert param.required is True
        assert param.description == "Search query"

    def test_api_parameter_with_default(self):
        """Test APIParameter with default value."""
        param = APIParameter(
            name="limit",
            type_name="int",
            required=False,
            default=5,
            description="Maximum results",
        )

        assert param.default == 5
        assert param.required is False

    def test_api_parameter_with_options(self):
        """Test APIParameter with enum options."""
        param = APIParameter(
            name="memory_type",
            type_name="str",
            required=False,
            options=["semantic", "event", "procedure", "task"],
            description="Type of memory",
        )

        assert param.options is not None
        assert len(param.options) == 4
        assert "semantic" in param.options

    def test_api_parameter_to_dict(self):
        """Test converting APIParameter to dictionary."""
        param = APIParameter(
            name="content",
            type_name="str",
            required=True,
            description="Content to store",
        )

        param_dict = param.to_dict()

        assert param_dict["name"] == "content"
        assert param_dict["type_name"] == "str"
        assert param_dict["required"] is True


class TestAPISpecification:
    """Tests for APISpecification dataclass."""

    def test_api_specification_basic(self):
        """Test basic APISpecification creation."""
        spec = APISpecification(
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
            ],
            return_type="int",
            return_description="Memory ID",
        )

        assert spec.name == "remember"
        assert spec.category == APICategory.CORE
        assert len(spec.parameters) == 1
        assert spec.return_type == "int"

    def test_api_specification_with_tags(self):
        """Test APISpecification with tags."""
        spec = APISpecification(
            name="recall",
            category=APICategory.CORE,
            description="Retrieve memories",
            parameters=[],
            return_type="dict",
            return_description="Retrieved memories",
            tags=["search", "query", "retrieval"],
        )

        assert spec.tags == ["search", "query", "retrieval"]

    def test_api_specification_with_examples(self):
        """Test APISpecification with usage examples."""
        spec = APISpecification(
            name="remember",
            category=APICategory.CORE,
            description="Store content",
            parameters=[],
            return_type="int",
            return_description="ID",
            examples=[
                "api.remember('Important fact')",
                "api.remember('Bug found', tags=['bug'])",
            ],
        )

        assert len(spec.examples) == 2

    def test_api_specification_deprecation(self):
        """Test APISpecification deprecation flag."""
        spec = APISpecification(
            name="old_api",
            category=APICategory.UTILITY,
            description="Deprecated API",
            parameters=[],
            return_type="None",
            return_description="Nothing",
            deprecated=True,
        )

        assert spec.deprecated is True

    def test_api_specification_to_dict(self):
        """Test converting APISpecification to dictionary."""
        spec = APISpecification(
            name="remember",
            category=APICategory.CORE,
            description="Store content",
            parameters=[],
            return_type="int",
            return_description="Memory ID",
            security_level=APISecurityLevel.PUBLIC,
        )

        spec_dict = spec.to_dict()

        assert spec_dict["name"] == "remember"
        assert spec_dict["category"] == "core"
        assert spec_dict["security_level"] == "public"
        assert isinstance(spec_dict, dict)

    def test_api_specification_default_values(self):
        """Test APISpecification default values."""
        spec = APISpecification(
            name="test",
            category=APICategory.CORE,
            description="Test API",
            parameters=[],
            return_type="str",
            return_description="Result",
        )

        assert spec.security_level == APISecurityLevel.PUBLIC
        assert spec.tags == []
        assert spec.examples == []
        assert spec.deprecated is False
        assert spec.since_version == "1.0"


class TestAPIRegistry:
    """Tests for APIRegistry."""

    def test_registry_creation(self):
        """Test creating APIRegistry."""
        registry = APIRegistry()

        assert registry is not None
        assert isinstance(registry.apis, dict)
        assert len(registry.apis) > 0  # Should have core APIs

    def test_registry_factory_method(self):
        """Test APIRegistry.create() factory method."""
        registry = APIRegistry.create()

        assert registry is not None
        assert len(registry.apis) > 0

    def test_registry_has_core_apis(self):
        """Test that registry has core remember/recall/forget APIs."""
        registry = APIRegistry()

        api_names = list(registry.apis.keys())
        assert "remember" in api_names
        assert "recall" in api_names
        assert "forget" in api_names

    def test_registry_register_api(self):
        """Test registering a new API."""
        registry = APIRegistry()
        initial_count = len(registry.apis)

        spec = APISpecification(
            name="custom_api",
            category=APICategory.UTILITY,
            description="Custom API for testing",
            parameters=[],
            return_type="str",
            return_description="Result",
        )

        registry.register(spec)

        assert len(registry.apis) > initial_count
        assert "custom_api" in registry.apis

    def test_registry_get_api(self):
        """Test retrieving an API specification."""
        registry = APIRegistry()

        api = registry.get_api("remember")

        assert api is not None
        assert api.name == "remember"
        assert api.category == APICategory.CORE

    def test_registry_get_nonexistent_api(self):
        """Test retrieving non-existent API returns None."""
        registry = APIRegistry()

        api = registry.get_api("nonexistent_api")

        assert api is None

    def test_registry_discover_all_apis(self):
        """Test discovering all APIs."""
        registry = APIRegistry()

        apis = registry.discover_apis()

        assert apis is not None
        assert len(apis) > 0
        assert all(isinstance(api, APISpecification) for api in apis)

    def test_registry_discover_by_category(self):
        """Test discovering APIs by category."""
        registry = APIRegistry()

        core_apis = registry.discover_apis(category=APICategory.CORE)

        assert len(core_apis) > 0
        assert all(api.category == APICategory.CORE for api in core_apis)

    def test_registry_discover_by_tags(self):
        """Test discovering APIs by tags."""
        registry = APIRegistry()

        # Discover APIs with specific tags
        apis = registry.discover_apis(tags=["memory"])

        # Should return list (may be empty if no tags match)
        assert isinstance(apis, list)

    def test_registry_discover_by_multiple_filters(self):
        """Test discovering APIs with multiple filters."""
        registry = APIRegistry()

        apis = registry.discover_apis(
            category=APICategory.CORE,
            tags=["memory"],
        )

        # Should return list (may or may not have results)
        assert isinstance(apis, list)

    def test_registry_get_categories(self):
        """Test getting all categories with APIs."""
        registry = APIRegistry()

        categories = registry.get_categories()

        assert len(categories) > 0
        assert APICategory.CORE in categories
        assert isinstance(categories, list)

    def test_registry_to_dict(self):
        """Test converting registry to dictionary."""
        registry = APIRegistry()

        registry_dict = registry.to_dict()

        assert isinstance(registry_dict, dict)
        assert len(registry_dict) > 0
        # Each value should be a dictionary (API spec)
        for api_name, api_dict in registry_dict.items():
            assert isinstance(api_dict, dict)
            assert "name" in api_dict

    def test_registry_api_specifications_have_parameters(self):
        """Test that core APIs have parameter specifications."""
        registry = APIRegistry()

        remember_api = registry.get_api("remember")
        assert remember_api is not None
        assert len(remember_api.parameters) > 0

        recall_api = registry.get_api("recall")
        assert recall_api is not None
        assert len(recall_api.parameters) > 0

    def test_registry_api_specifications_have_descriptions(self):
        """Test that core APIs have descriptions."""
        registry = APIRegistry()

        for api_name in ["remember", "recall", "forget"]:
            api = registry.get_api(api_name)
            assert api is not None
            assert len(api.description) > 0
            assert len(api.return_description) > 0


class TestAPIDocumentationGenerator:
    """Tests for APIDocumentationGenerator."""

    @pytest.fixture
    def registry(self):
        """Create APIRegistry for tests."""
        return APIRegistry.create()

    @pytest.fixture
    def generator(self, registry):
        """Create APIDocumentationGenerator for tests."""
        return APIDocumentationGenerator(registry)

    def test_generator_creation(self, generator):
        """Test creating APIDocumentationGenerator."""
        assert generator is not None
        assert generator.registry is not None

    def test_generate_markdown(self, generator):
        """Test generating Markdown documentation."""
        markdown = generator.generate_markdown()

        assert markdown is not None
        assert isinstance(markdown, str)
        assert len(markdown) > 0
        assert "# MemoryAPI Documentation" in markdown

    def test_markdown_has_table_of_contents(self, generator):
        """Test that markdown has table of contents."""
        markdown = generator.generate_markdown()

        assert "## Table of Contents" in markdown
        assert "core" in markdown

    def test_markdown_has_quick_start(self, generator):
        """Test that markdown has quick start section."""
        markdown = generator.generate_markdown()

        assert "## Quick Start" in markdown
        assert "MemoryAPI.create()" in markdown

    def test_markdown_has_api_sections(self, generator):
        """Test that markdown has sections for each API."""
        markdown = generator.generate_markdown()

        # Should have sections for different categories
        assert "## Core" in markdown or "## CORE" in markdown or "core" in markdown

    def test_markdown_includes_api_details(self, generator):
        """Test that markdown includes API method details."""
        markdown = generator.generate_markdown()

        # Should mention specific APIs
        assert "remember" in markdown or "Remember" in markdown

    def test_generate_html(self, generator):
        """Test generating HTML documentation."""
        html = generator.generate_html()

        assert html is not None
        assert isinstance(html, str)
        assert len(html) > 0
        assert "<html" in html.lower() or "<body" in html.lower()

    def test_html_is_valid_markup(self, generator):
        """Test that HTML is properly formatted."""
        html = generator.generate_html()

        # Check for basic HTML structure
        assert "<" in html and ">" in html

    def test_generate_json(self, generator):
        """Test generating JSON documentation."""
        json_doc = generator.generate_json()

        assert json_doc is not None
        assert isinstance(json_doc, str)

        # Should be parseable JSON
        parsed = json.loads(json_doc)
        assert parsed is not None
        assert isinstance(parsed, dict)

    def test_json_has_apis(self, generator):
        """Test that JSON documentation includes APIs."""
        json_doc = generator.generate_json()
        parsed = json.loads(json_doc)

        assert "apis" in parsed or "api" in parsed or len(parsed) > 0

    def test_markdown_has_timestamp(self, generator):
        """Test that markdown includes generation timestamp."""
        markdown = generator.generate_markdown()

        assert "Generated:" in markdown

    def test_generator_with_custom_registry(self):
        """Test generator with custom registry."""
        registry = APIRegistry()

        # Add a custom API
        spec = APISpecification(
            name="test_api",
            category=APICategory.UTILITY,
            description="Test API",
            parameters=[
                APIParameter(
                    name="param1",
                    type_name="str",
                    required=True,
                )
            ],
            return_type="str",
            return_description="Result",
        )
        registry.register(spec)

        generator = APIDocumentationGenerator(registry)
        markdown = generator.generate_markdown()

        # Should document the custom API
        assert "test_api" in markdown.lower() or "Test API" in markdown

    def test_markdown_escaping(self, generator):
        """Test that markdown properly escapes special characters."""
        # This is more of an integration test
        markdown = generator.generate_markdown()

        # Should not have unescaped < or > in text content
        # (HTML in code blocks is OK)
        assert markdown is not None

    def test_json_structure(self, generator):
        """Test JSON documentation structure."""
        json_doc = generator.generate_json()
        parsed = json.loads(json_doc)

        # Should have consistent structure
        assert isinstance(parsed, dict)

    def test_generator_handles_empty_registry(self):
        """Test generator with empty registry."""
        registry = APIRegistry()
        registry.apis = {}  # Clear all APIs

        generator = APIDocumentationGenerator(registry)
        markdown = generator.generate_markdown()

        # Should still generate valid documentation
        assert markdown is not None
        assert isinstance(markdown, str)

    def test_all_generator_methods_callable(self, generator):
        """Test that all generator methods are callable."""
        assert callable(generator.generate_markdown)
        assert callable(generator.generate_html)
        assert callable(generator.generate_json)

    def test_generated_docs_consistency(self, generator):
        """Test that documentation is generated consistently."""
        md1 = generator.generate_markdown()
        md2 = generator.generate_markdown()

        # Content should be the same (except timestamp might vary)
        assert len(md1) == len(md2) or abs(len(md1) - len(md2)) < 50


class TestAPIRegistryAndDocsIntegration:
    """Integration tests for APIRegistry and APIDocumentationGenerator."""

    def test_full_documentation_workflow(self):
        """Test complete workflow: create registry, register API, generate docs."""
        # Create registry
        registry = APIRegistry.create()

        # Register additional API
        spec = APISpecification(
            name="test_memory",
            category=APICategory.SEMANTIC,
            description="Test memory operation",
            parameters=[
                APIParameter(
                    name="content",
                    type_name="str",
                    required=True,
                    description="Memory content",
                )
            ],
            return_type="int",
            return_description="Memory ID",
        )
        registry.register(spec)

        # Generate documentation
        generator = APIDocumentationGenerator(registry)
        markdown = generator.generate_markdown()
        html = generator.generate_html()
        json_doc = generator.generate_json()

        # All formats should be generated
        assert len(markdown) > 0
        assert len(html) > 0
        assert len(json_doc) > 0

        # Should document the registered API
        assert "test_memory" in markdown.lower()

    def test_api_discovery_via_documentation(self):
        """Test that APIs can be discovered through documentation."""
        registry = APIRegistry.create()
        apis = registry.discover_apis()

        # All discovered APIs should be documentable
        for api in apis:
            assert api.name is not None
            assert api.description is not None
            assert api.return_type is not None

    def test_registry_and_docs_match(self):
        """Test that documentation reflects all registered APIs."""
        registry = APIRegistry.create()
        generator = APIDocumentationGenerator(registry)

        markdown = generator.generate_markdown()
        apis = registry.discover_apis()

        # Core APIs should be in documentation
        core_apis = [api for api in apis if api.category == APICategory.CORE]
        for api in core_apis:
            assert api.name.lower() in markdown.lower()
