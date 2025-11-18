"""Tests for specification diffing functionality."""

import json
import pytest
from datetime import datetime

from athena.architecture.spec_differ import (
    SpecificationDiffer,
    DiffResult,
    SpecChange,
    ChangeType,
    ChangeSeverity,
    diff_specifications,
)
from athena.architecture.models import Specification, SpecType, SpecStatus


@pytest.fixture
def differ():
    """Create a SpecificationDiffer instance."""
    return SpecificationDiffer()


@pytest.fixture
def openapi_v1():
    """Create a simple OpenAPI v1 specification."""
    content = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "User API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "limit", "in": "query", "required": False}
                    ],
                    "responses": {"200": {"description": "Success"}}
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    }
                }
            }
        }
    })

    return Specification(
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content=content,
    )


@pytest.fixture
def openapi_v2_breaking():
    """Create OpenAPI v2 with breaking changes."""
    content = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "User API", "version": "2.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "limit", "in": "query", "required": True},  # Now required (breaking)
                        {"name": "offset", "in": "query", "required": False}  # Added (non-breaking)
                    ],
                    "responses": {"200": {"description": "Success"}}
                }
            }
            # /users/{id} endpoint removed (breaking)
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "name", "email"],  # email now required (breaking)
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "created_at": {"type": "string"}  # Added (non-breaking)
                    }
                }
            }
        }
    })

    return Specification(
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="2.0.0",
        status=SpecStatus.ACTIVE,
        content=content,
    )


@pytest.fixture
def openapi_v2_non_breaking():
    """Create OpenAPI v2 with only non-breaking changes."""
    content = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "User API", "version": "2.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "limit", "in": "query", "required": False}
                    ],
                    "responses": {"200": {"description": "Success"}}
                },
                "post": {  # New endpoint (non-breaking)
                    "responses": {"201": {"description": "Created"}}
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "name"],  # Same as before
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "created_at": {"type": "string"}  # Added (non-breaking)
                    }
                },
                "Post": {  # New schema (non-breaking)
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"}
                    }
                }
            }
        }
    })

    return Specification(
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="2.0.0",
        status=SpecStatus.ACTIVE,
        content=content,
    )


@pytest.fixture
def jsonschema_v1():
    """Create a simple JSON Schema v1."""
    content = json.dumps({
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        }
    })

    return Specification(
        project_id=1,
        name="Person Schema",
        spec_type=SpecType.JSONSCHEMA,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content=content,
    )


@pytest.fixture
def jsonschema_v2_breaking():
    """Create JSON Schema v2 with breaking changes."""
    content = json.dumps({
        "type": "object",
        "required": ["name", "email"],  # email now required (breaking)
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"}  # Added and required (breaking)
            # age removed (breaking)
        }
    })

    return Specification(
        project_id=1,
        name="Person Schema",
        spec_type=SpecType.JSONSCHEMA,
        version="2.0.0",
        status=SpecStatus.ACTIVE,
        content=content,
    )


@pytest.fixture
def graphql_v1():
    """Create a simple GraphQL schema v1."""
    content = """
    type User {
        id: ID!
        name: String!
        email: String
    }

    type Query {
        user(id: ID!): User
        users: [User!]!
    }
    """

    return Specification(
        project_id=1,
        name="GraphQL API",
        spec_type=SpecType.GRAPHQL,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content=content,
    )


@pytest.fixture
def graphql_v2_breaking():
    """Create GraphQL schema v2 with breaking changes."""
    content = """
    type User {
        id: ID!
        name: String!
        # email removed (breaking)
    }

    type Query {
        user(id: ID!): User
        # users removed (breaking)
    }
    """

    return Specification(
        project_id=1,
        name="GraphQL API",
        spec_type=SpecType.GRAPHQL,
        version="2.0.0",
        status=SpecStatus.ACTIVE,
        content=content,
    )


class TestSpecificationDiffer:
    """Tests for SpecificationDiffer class."""

    def test_diff_openapi_no_changes(self, differ, openapi_v1):
        """Test diffing identical OpenAPI specs returns no changes."""
        result = differ.diff(openapi_v1, openapi_v1)

        assert isinstance(result, DiffResult)
        assert result.old_spec == openapi_v1
        assert result.new_spec == openapi_v1
        assert len(result.changes) == 0
        assert not result.has_changes
        assert not result.has_breaking_changes

    def test_diff_openapi_breaking_changes(self, differ, openapi_v1, openapi_v2_breaking):
        """Test diffing OpenAPI specs with breaking changes."""
        result = differ.diff(openapi_v1, openapi_v2_breaking)

        assert result.has_changes
        assert result.has_breaking_changes
        assert len(result.breaking_changes) > 0

        # Check that parameter requirement change is detected as breaking
        breaking_paths = [c.path for c in result.breaking_changes]
        assert any("limit" in path for path in breaking_paths)

    def test_diff_openapi_non_breaking_changes(self, differ, openapi_v1, openapi_v2_non_breaking):
        """Test diffing OpenAPI specs with only non-breaking changes."""
        result = differ.diff(openapi_v1, openapi_v2_non_breaking)

        assert result.has_changes
        assert not result.has_breaking_changes
        assert len(result.non_breaking_changes) > 0

        # Check that new endpoint is detected as non-breaking
        non_breaking_paths = [c.path for c in result.non_breaking_changes]
        assert any("post" in path.lower() for path in non_breaking_paths)

    def test_diff_openapi_endpoint_removal(self, differ, openapi_v1, openapi_v2_breaking):
        """Test that removing endpoints is detected as breaking."""
        # Add an endpoint to v1
        v1_content = json.loads(openapi_v1.content)
        v1_content["paths"]["/users/{id}"] = {
            "get": {"responses": {"200": {"description": "Success"}}}
        }
        openapi_v1.content = json.dumps(v1_content)

        result = differ.diff(openapi_v1, openapi_v2_breaking)

        # Should detect removed endpoint as breaking
        breaking_changes = [c for c in result.breaking_changes if "/users/{id}" in c.path]
        assert len(breaking_changes) > 0

    def test_diff_jsonschema_breaking_changes(self, differ, jsonschema_v1, jsonschema_v2_breaking):
        """Test diffing JSON Schema with breaking changes."""
        result = differ.diff(jsonschema_v1, jsonschema_v2_breaking)

        assert result.has_changes
        assert result.has_breaking_changes

        # Check that new required property is breaking
        breaking = [c for c in result.breaking_changes if "email" in c.path.lower()]
        assert len(breaking) > 0

        # Check that removed property is breaking
        breaking_removed = [c for c in result.breaking_changes if "age" in c.path.lower()]
        assert len(breaking_removed) > 0

    def test_diff_graphql_breaking_changes(self, differ, graphql_v1, graphql_v2_breaking):
        """Test diffing GraphQL schemas with breaking changes."""
        result = differ.diff(graphql_v1, graphql_v2_breaking)

        assert result.has_changes
        assert result.has_breaking_changes

        # Should detect removed field as breaking
        breaking = [c for c in result.breaking_changes if "email" in c.path.lower() or "email" in c.description.lower()]
        assert len(breaking) > 0

    def test_diff_result_summary(self, differ, openapi_v1, openapi_v2_breaking):
        """Test DiffResult summary property."""
        result = differ.diff(openapi_v1, openapi_v2_breaking)

        summary = result.summary
        assert "total_changes" in summary
        assert "breaking_changes" in summary
        assert "non_breaking_changes" in summary
        assert "added" in summary
        assert "removed" in summary
        assert "modified" in summary

        assert summary["total_changes"] == len(result.changes)
        assert summary["breaking_changes"] == len(result.breaking_changes)
        assert summary["non_breaking_changes"] == len(result.non_breaking_changes)

    def test_diff_generic_fallback(self, differ):
        """Test generic text diff for unsupported spec types."""
        old_spec = Specification(
            project_id=1,
            name="Test Doc",
            spec_type=SpecType.MARKDOWN,
            version="1.0.0",
            status=SpecStatus.ACTIVE,
            content="# Hello World\n\nThis is version 1.",
        )

        new_spec = Specification(
            project_id=1,
            name="Test Doc",
            spec_type=SpecType.MARKDOWN,
            version="2.0.0",
            status=SpecStatus.ACTIVE,
            content="# Hello World\n\nThis is version 2 with changes.",
        )

        result = differ.diff(old_spec, new_spec)

        assert result.has_changes
        # Generic diff should mark severity as UNKNOWN
        assert any(c.severity == ChangeSeverity.UNKNOWN for c in result.changes)

    def test_diff_specifications_convenience_function(self, openapi_v1, openapi_v2_breaking):
        """Test convenience function for diffing."""
        result = diff_specifications(openapi_v1, openapi_v2_breaking)

        assert isinstance(result, DiffResult)
        assert result.has_changes

    def test_diff_different_spec_types(self, differ, openapi_v1, jsonschema_v1):
        """Test diffing specs of different types."""
        # Should still work but use generic diff
        result = differ.diff(openapi_v1, jsonschema_v1)

        assert isinstance(result, DiffResult)
        # Will likely detect changes due to different content
        assert result.has_changes

    def test_change_type_enum(self):
        """Test ChangeType enum values."""
        assert ChangeType.ADDED.value == "added"
        assert ChangeType.REMOVED.value == "removed"
        assert ChangeType.MODIFIED.value == "modified"
        assert ChangeType.UNCHANGED.value == "unchanged"

    def test_change_severity_enum(self):
        """Test ChangeSeverity enum values."""
        assert ChangeSeverity.BREAKING.value == "breaking"
        assert ChangeSeverity.NON_BREAKING.value == "non_breaking"
        assert ChangeSeverity.UNKNOWN.value == "unknown"

    def test_spec_change_dataclass(self):
        """Test SpecChange dataclass creation."""
        change = SpecChange(
            path="/test/path",
            change_type=ChangeType.MODIFIED,
            severity=ChangeSeverity.BREAKING,
            description="Test change"
        )

        assert change.path == "/test/path"
        assert change.change_type == ChangeType.MODIFIED
        assert change.severity == ChangeSeverity.BREAKING
        assert change.description == "Test change"

    def test_diff_result_properties(self, differ, openapi_v1, openapi_v2_breaking):
        """Test DiffResult computed properties."""
        result = differ.diff(openapi_v1, openapi_v2_breaking)

        # Test has_breaking_changes
        assert result.has_breaking_changes == (len(result.breaking_changes) > 0)

        # Test has_changes
        assert result.has_changes == (len(result.changes) > 0)

        # Test breaking_changes filter
        for change in result.breaking_changes:
            assert change.severity == ChangeSeverity.BREAKING

        # Test non_breaking_changes filter
        for change in result.non_breaking_changes:
            assert change.severity == ChangeSeverity.NON_BREAKING
