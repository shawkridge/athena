"""Tests for AI document generation."""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from athena.architecture.models import Specification, SpecType, SpecStatus, DocumentType
from athena.architecture.generators import (
    ContextAssembler,
    GenerationContext,
    PromptLibrary,
)


# ========================================================================
# Context Assembler Tests
# ========================================================================

def test_generation_context_to_dict():
    """Test converting generation context to dictionary."""
    spec = Specification(
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content='{"openapi": "3.0.0"}',
        description="User management API",
    )

    context = GenerationContext(
        primary_specs=[spec],
        doc_type=DocumentType.API_DOC,
        target_audience="technical",
        detail_level="comprehensive",
        custom_context={"custom_key": "custom_value"},
    )

    data = context.to_dict()

    assert data["doc_type"] == "api_doc"
    assert data["target_audience"] == "technical"
    assert data["detail_level"] == "comprehensive"
    assert data["custom_key"] == "custom_value"
    assert len(data["primary_specs"]) == 1
    assert data["primary_specs"][0]["name"] == "User API"


def test_generation_context_summary():
    """Test context summary generation."""
    context = GenerationContext()

    # Empty context
    assert context.get_summary() == "empty context"

    # With specs
    spec = Specification(
        project_id=1,
        name="Test",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content="{}",
    )
    context.primary_specs.append(spec)

    summary = context.get_summary()
    assert "1 primary spec" in summary


def test_context_assembler_initialization():
    """Test context assembler initializes correctly."""
    spec_store = Mock()
    assembler = ContextAssembler(spec_store=spec_store)

    assert assembler.spec_store == spec_store
    assert assembler.adr_store is None
    assert assembler.constraint_store is None


def test_context_assembler_for_single_spec():
    """Test assembling context for a single specification."""
    # Mock spec store
    spec_store = Mock()
    spec = Specification(
        id=5,
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content='{"openapi": "3.0.0"}',
    )
    spec_store.get.return_value = spec
    spec_store.list_by_project.return_value = []

    # Assemble context
    assembler = ContextAssembler(spec_store=spec_store)
    context = assembler.assemble_for_spec(
        spec_id=5,
        doc_type=DocumentType.API_DOC,
    )

    # Verify context
    assert len(context.primary_specs) == 1
    assert context.primary_specs[0].id == 5
    assert context.doc_type == DocumentType.API_DOC
    assert context.project_id == 1


def test_context_assembler_for_multiple_specs():
    """Test assembling context from multiple specifications."""
    # Mock spec store
    spec_store = Mock()

    specs = [
        Specification(
            id=i,
            project_id=1,
            name=f"API {i}",
            spec_type=SpecType.OPENAPI,
            version="1.0.0",
            status=SpecStatus.ACTIVE,
            content="{}",
        )
        for i in [5, 6, 7]
    ]

    spec_store.get.side_effect = specs
    spec_store.list_by_project.return_value = []

    # Assemble context
    assembler = ContextAssembler(spec_store=spec_store)
    context = assembler.assemble_for_multiple_specs(
        spec_ids=[5, 6, 7],
        doc_type=DocumentType.HLD,
    )

    # Verify context
    assert len(context.primary_specs) == 3
    assert context.doc_type == DocumentType.HLD
    assert context.project_id == 1


def test_context_assembler_no_include_related():
    """Test assembling context without related specs."""
    spec_store = Mock()
    spec = Specification(
        id=5,
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content="{}",
    )
    spec_store.get.return_value = spec

    assembler = ContextAssembler(spec_store=spec_store)
    context = assembler.assemble_for_spec(
        spec_id=5,
        doc_type=DocumentType.API_DOC,
        include_related=False,
    )

    # Should not call list_by_project when include_related=False
    spec_store.list_by_project.assert_not_called()
    assert len(context.related_specs) == 0


# ========================================================================
# Prompt Library Tests
# ========================================================================

def test_prompt_library_api_doc():
    """Test API documentation prompt generation."""
    context = {
        "primary_specs": [
            {
                "name": "User API",
                "version": "1.0.0",
                "type": "openapi",
                "status": "active",
                "description": "User management",
                "content": '{"openapi": "3.0.0"}',
            }
        ],
        "target_audience": "developers",
        "detail_level": "comprehensive",
    }

    prompt = PromptLibrary.get_prompt(DocumentType.API_DOC, context)

    # Check prompt structure
    assert "API documentation" in prompt
    assert "User API" in prompt
    assert "comprehensive" in prompt
    assert "developers" in prompt


def test_prompt_library_tdd():
    """Test TDD prompt generation."""
    context = {
        "primary_specs": [
            {
                "name": "Auth System",
                "version": "2.0.0",
                "type": "openapi",
                "status": "active",
                "description": "Authentication",
                "content": "{}",
            }
        ],
        "adrs": [],
        "constraints": [],
    }

    prompt = PromptLibrary.get_prompt(DocumentType.TDD, context)

    assert "Technical Design Document" in prompt or "TDD" in prompt
    assert "Auth System" in prompt


def test_prompt_library_default():
    """Test default prompt for unknown doc types."""
    context = {
        "primary_specs": [],
    }

    # Should not raise error for any doc type
    for doc_type in DocumentType:
        prompt = PromptLibrary.get_prompt(doc_type, context)
        assert len(prompt) > 0


def test_prompt_library_format_specs():
    """Test spec formatting helper."""
    specs = [
        {
            "name": "Test API",
            "version": "1.0.0",
            "type": "openapi",
            "status": "active",
            "description": "Test description",
            "content": "test content",
        }
    ]

    formatted = PromptLibrary._format_specs(specs)

    assert "Test API" in formatted
    assert "1.0.0" in formatted
    assert "test content" in formatted


def test_prompt_library_format_empty_specs():
    """Test formatting with no specs."""
    formatted = PromptLibrary._format_specs([])
    assert "No specifications" in formatted


# ========================================================================
# AI Generator Tests (Mocked)
# ========================================================================

@pytest.mark.skipif(
    True,  # Skip by default since it requires anthropic package
    reason="Requires anthropic package and API key"
)
def test_ai_generator_initialization():
    """Test AI generator initialization."""
    from athena.architecture.generators import AIDocGenerator

    generator = AIDocGenerator(api_key="test-key")

    assert generator.model == "claude-3-5-sonnet-20241022"
    assert generator.max_tokens == 8000
    assert generator.temperature == 0.7


@pytest.mark.skipif(
    True,  # Skip by default
    reason="Requires anthropic package and API key"
)
def test_ai_generator_compute_confidence():
    """Test confidence computation."""
    from athena.architecture.generators import AIDocGenerator

    generator = AIDocGenerator(api_key="test-key")

    # Good content
    good_content = """
# API Documentation

## Overview
This is a comprehensive API documentation with multiple sections.

## Authentication
Details about authentication...

## Endpoints
Example endpoints...

## Examples
Code examples...
"""
    confidence = generator._compute_confidence(good_content, DocumentType.API_DOC)
    assert confidence > 0.6

    # Poor content (too short)
    poor_content = "# API"
    confidence = generator._compute_confidence(poor_content, DocumentType.API_DOC)
    assert confidence < 0.7


@pytest.mark.skipif(
    True,  # Skip by default
    reason="Requires anthropic package and API key"
)
def test_ai_generator_check_quality():
    """Test quality checking."""
    from athena.architecture.generators import AIDocGenerator

    generator = AIDocGenerator(api_key="test-key")

    # Content with issues
    content_with_issues = "# TODO: Write documentation"
    warnings = generator._check_quality(content_with_issues, DocumentType.API_DOC)

    assert len(warnings) > 0
    assert any("placeholder" in w.lower() or "short" in w.lower() for w in warnings)

    # Good content
    good_content = """
# API Documentation

## Overview
Complete documentation with proper structure.

## Endpoints
```python
# Code example
response = api.get('/users')
```

## Diagrams
System architecture diagram showing components.
"""
    warnings = generator._check_quality(good_content, DocumentType.API_DOC)
    # May have some warnings but should have fewer
    assert isinstance(warnings, list)


def test_generation_result_to_document():
    """Test converting generation result to document."""
    from athena.architecture.generators.ai_generator import GenerationResult

    result = GenerationResult(
        content="# Test Documentation\n\nContent here.",
        doc_type=DocumentType.API_DOC,
        model="claude-3-5-sonnet-20241022",
        prompt="Generate API docs...",
        prompt_tokens=100,
        completion_tokens=500,
        total_tokens=600,
        confidence=0.85,
    )

    doc = result.to_document(
        project_id=1,
        name="Test API Docs",
        version="1.0.0",
        file_path="docs/api/test.md",
    )

    assert doc.name == "Test API Docs"
    assert doc.doc_type == DocumentType.API_DOC
    assert doc.version == "1.0.0"
    assert doc.generated_by == "ai"
    assert doc.generation_model == "claude-3-5-sonnet-20241022"
    assert doc.sync_hash is not None
    assert len(doc.sync_hash) == 16
