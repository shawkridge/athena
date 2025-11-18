"""Tests for specification validation."""

import pytest

from athena.architecture.models import Specification, SpecType, SpecStatus
from athena.architecture.spec_validator import (
    SpecificationValidator,
    ValidationResult,
    validate_specification,
)


@pytest.fixture
def validator():
    """Create specification validator."""
    return SpecificationValidator()


@pytest.fixture
def valid_openapi_spec():
    """Create a valid OpenAPI specification."""
    return Specification(
        project_id=1,
        name="Valid OpenAPI",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="""openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: List of users
""",
    )


@pytest.fixture
def invalid_openapi_spec():
    """Create an invalid OpenAPI specification."""
    return Specification(
        project_id=1,
        name="Invalid OpenAPI",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="""openapi: 3.0.0
info:
  title: Test API
# Missing version in info
paths:
  /users:
    get:
      summary: List users
""",
    )


@pytest.fixture
def valid_graphql_spec():
    """Create a valid GraphQL specification."""
    return Specification(
        project_id=1,
        name="Valid GraphQL",
        spec_type=SpecType.GRAPHQL,
        version="1.0.0",
        content="""type Query {
  hello: String
  user(id: ID!): User
}

type User {
  id: ID!
  name: String!
  email: String
}
""",
    )


@pytest.fixture
def invalid_graphql_spec():
    """Create an invalid GraphQL specification."""
    return Specification(
        project_id=1,
        name="Invalid GraphQL",
        spec_type=SpecType.GRAPHQL,
        version="1.0.0",
        content="""type Query {
  hello String  # Missing colon
}
""",
    )


@pytest.fixture
def valid_jsonschema_spec():
    """Create a valid JSON Schema specification."""
    return Specification(
        project_id=1,
        name="Valid JSON Schema",
        spec_type=SpecType.JSONSCHEMA,
        version="1.0.0",
        content="""{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "name": {
      "type": "string"
    },
    "age": {
      "type": "integer",
      "minimum": 0
    }
  },
  "required": ["name"]
}
""",
    )


@pytest.fixture
def markdown_spec():
    """Create a markdown specification (no validator)."""
    return Specification(
        project_id=1,
        name="Markdown Spec",
        spec_type=SpecType.MARKDOWN,
        version="1.0.0",
        content="""# Test Specification

This is a test specification in markdown format.
""",
    )


def test_validation_result_status(validator):
    """Test ValidationResult status property."""
    # Valid with no warnings
    result1 = ValidationResult(is_valid=True, errors=[], warnings=[])
    assert result1.status == "valid"

    # Valid with warnings
    result2 = ValidationResult(is_valid=True, errors=[], warnings=["Warning"])
    assert result2.status == "valid_with_warnings"

    # Invalid
    result3 = ValidationResult(is_valid=False, errors=["Error"], warnings=[])
    assert result3.status == "invalid"


def test_validate_openapi_valid(validator, valid_openapi_spec):
    """Test validating a valid OpenAPI specification."""
    result = validator.validate(valid_openapi_spec)

    # May pass with warnings if library not installed, or pass cleanly
    assert result.is_valid
    if result.validator_used == "openapi-spec-validator":
        # Library is installed, should have no errors
        assert len(result.errors) == 0


def test_validate_openapi_invalid(validator, invalid_openapi_spec):
    """Test validating an invalid OpenAPI specification."""
    result = validator.validate(invalid_openapi_spec)

    # If library is installed, should detect the error
    if result.validator_used == "openapi-spec-validator":
        assert not result.is_valid
        assert len(result.errors) > 0
    else:
        # Library not installed, should have warning
        assert len(result.warnings) > 0


def test_validate_graphql_valid(validator, valid_graphql_spec):
    """Test validating a valid GraphQL specification."""
    result = validator.validate(valid_graphql_spec)

    assert result.is_valid
    if result.validator_used == "graphql-core":
        assert len(result.errors) == 0


def test_validate_graphql_invalid(validator, invalid_graphql_spec):
    """Test validating an invalid GraphQL specification."""
    result = validator.validate(invalid_graphql_spec)

    if result.validator_used == "graphql-core":
        assert not result.is_valid
        assert len(result.errors) > 0


def test_validate_jsonschema_valid(validator, valid_jsonschema_spec):
    """Test validating a valid JSON Schema specification."""
    result = validator.validate(valid_jsonschema_spec)

    assert result.is_valid
    if result.validator_used == "jsonschema":
        assert len(result.errors) == 0


def test_validate_markdown(validator, markdown_spec):
    """Test validating markdown specification (no validator available)."""
    result = validator.validate(markdown_spec)

    # Should pass with warning that no validator available
    assert result.is_valid
    assert len(result.warnings) > 0
    assert "no validator available" in result.warnings[0].lower()
    assert result.validator_used == "none"


def test_validate_specification_convenience_function(valid_openapi_spec):
    """Test convenience function for validation."""
    result = validate_specification(valid_openapi_spec)

    assert result.is_valid
    assert isinstance(result, ValidationResult)


def test_validation_result_has_timestamp(validator, valid_openapi_spec):
    """Test that validation result includes timestamp."""
    result = validator.validate(valid_openapi_spec)

    assert result.validated_at is not None
    assert result.validated_at.year >= 2025


def test_asyncapi_validation(validator):
    """Test AsyncAPI validation (not yet implemented)."""
    spec = Specification(
        project_id=1,
        name="AsyncAPI Spec",
        spec_type=SpecType.ASYNCAPI,
        version="1.0.0",
        content="asyncapi: 2.6.0",
    )

    result = validator.validate(spec)

    # Should pass with warning
    assert result.is_valid
    assert len(result.warnings) > 0
    assert "not yet implemented" in result.warnings[0].lower()


def test_validation_handles_empty_content(validator):
    """Test validation with empty content."""
    spec = Specification(
        project_id=1,
        name="Empty Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="",
    )

    result = validator.validate(spec)

    # Should fail validation
    if result.validator_used != "none":
        assert not result.is_valid
        assert len(result.errors) > 0


def test_validation_handles_malformed_json(validator):
    """Test validation with malformed JSON."""
    spec = Specification(
        project_id=1,
        name="Malformed JSON",
        spec_type=SpecType.JSONSCHEMA,
        version="1.0.0",
        content="{invalid json",
    )

    result = validator.validate(spec)

    if result.validator_used != "none":
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "json" in str(result.errors[0]).lower()
