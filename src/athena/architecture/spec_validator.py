"""Specification validation for different spec types.

This module provides validation for specifications to ensure they are well-formed
and conform to their respective standards. Validation is optional and gracefully
degrades if validation libraries are not installed.

Supported Validators:
- OpenAPI 3.0/3.1 (requires: openapi-spec-validator)
- JSON Schema (requires: jsonschema)
- GraphQL (requires: graphql-core)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import Specification, SpecType

logger = logging.getLogger(__name__)

# Optional validation library imports with graceful degradation
try:
    from openapi_spec_validator import validate_spec
    from openapi_spec_validator.validation.exceptions import OpenAPIValidationError
    OPENAPI_AVAILABLE = True
except ImportError:
    OPENAPI_AVAILABLE = False

try:
    import jsonschema
    from jsonschema import validate as validate_json_schema
    from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

try:
    from graphql import build_schema, GraphQLError
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False


@dataclass
class ValidationResult:
    """Result of specification validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validator_used: Optional[str] = None
    validated_at: datetime = field(default_factory=datetime.now)

    @property
    def status(self) -> str:
        """Get validation status string."""
        if self.is_valid and not self.warnings:
            return "valid"
        elif self.is_valid and self.warnings:
            return "valid_with_warnings"
        else:
            return "invalid"


class SpecificationValidator:
    """Validates specifications based on their type."""

    def validate(self, spec: Specification) -> ValidationResult:
        """Validate a specification based on its type.

        Args:
            spec: Specification to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        # Route to appropriate validator based on spec type
        if spec.spec_type == SpecType.OPENAPI:
            return self._validate_openapi(spec)
        elif spec.spec_type == SpecType.JSONSCHEMA:
            return self._validate_jsonschema(spec)
        elif spec.spec_type == SpecType.GRAPHQL:
            return self._validate_graphql(spec)
        elif spec.spec_type == SpecType.ASYNCAPI:
            return self._validate_asyncapi(spec)
        else:
            # No validator available for this type
            return ValidationResult(
                is_valid=True,
                warnings=[f"No validator available for {spec.spec_type} specifications"],
                validator_used="none"
            )

    def _validate_openapi(self, spec: Specification) -> ValidationResult:
        """Validate OpenAPI specification.

        Uses openapi-spec-validator to validate against OpenAPI 3.0/3.1 spec.
        """
        if not OPENAPI_AVAILABLE:
            return ValidationResult(
                is_valid=True,
                warnings=[
                    "OpenAPI validation library not installed. "
                    "Install with: pip install 'athena[validation]'"
                ],
                validator_used="none"
            )

        try:
            # Parse spec content as YAML/JSON
            import yaml
            spec_dict = yaml.safe_load(spec.content)

            # Validate against OpenAPI spec
            validate_spec(spec_dict)

            return ValidationResult(
                is_valid=True,
                validator_used="openapi-spec-validator"
            )

        except OpenAPIValidationError as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
                validator_used="openapi-spec-validator"
            )
        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid YAML/JSON: {e}"],
                validator_used="openapi-spec-validator"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                validator_used="openapi-spec-validator"
            )

    def _validate_jsonschema(self, spec: Specification) -> ValidationResult:
        """Validate JSON Schema specification.

        Validates that the content is valid JSON Schema.
        """
        if not JSONSCHEMA_AVAILABLE:
            return ValidationResult(
                is_valid=True,
                warnings=[
                    "JSON Schema validation library not installed. "
                    "Install with: pip install 'athena[validation]'"
                ],
                validator_used="none"
            )

        try:
            # Parse as JSON
            schema = json.loads(spec.content)

            # Validate it's a valid JSON Schema
            # We validate against the meta-schema
            validator_class = jsonschema.validators.validator_for(schema)
            validator_class.check_schema(schema)

            return ValidationResult(
                is_valid=True,
                validator_used="jsonschema"
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid JSON: {e}"],
                validator_used="jsonschema"
            )
        except jsonschema.exceptions.SchemaError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid JSON Schema: {e}"],
                validator_used="jsonschema"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                validator_used="jsonschema"
            )

    def _validate_graphql(self, spec: Specification) -> ValidationResult:
        """Validate GraphQL schema specification.

        Validates that the content is valid GraphQL SDL (Schema Definition Language).
        """
        if not GRAPHQL_AVAILABLE:
            return ValidationResult(
                is_valid=True,
                warnings=[
                    "GraphQL validation library not installed. "
                    "Install with: pip install 'athena[validation]'"
                ],
                validator_used="none"
            )

        try:
            # Try to build the schema
            build_schema(spec.content)

            return ValidationResult(
                is_valid=True,
                validator_used="graphql-core"
            )

        except GraphQLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
                validator_used="graphql-core"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                validator_used="graphql-core"
            )

    def _validate_asyncapi(self, spec: Specification) -> ValidationResult:
        """Validate AsyncAPI specification.

        Currently returns warning that AsyncAPI validation is not yet implemented.
        """
        return ValidationResult(
            is_valid=True,
            warnings=["AsyncAPI validation not yet implemented (planned for Phase 5)"],
            validator_used="none"
        )


def validate_specification(spec: Specification) -> ValidationResult:
    """Convenience function to validate a specification.

    Args:
        spec: Specification to validate

    Returns:
        ValidationResult with validation status

    Example:
        >>> from athena.architecture.spec_validator import validate_specification
        >>> result = validate_specification(spec)
        >>> if result.is_valid:
        ...     print("Spec is valid!")
        >>> else:
        ...     print(f"Errors: {result.errors}")
    """
    validator = SpecificationValidator()
    return validator.validate(spec)
