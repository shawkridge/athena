"""Specification diffing and change detection.

This module provides tools for comparing specification versions and detecting changes.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import json
import difflib

from .models import Specification, SpecType

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of change detected in a specification."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ChangeSeverity(Enum):
    """Severity of a change (breaking vs non-breaking)."""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"
    UNKNOWN = "unknown"


@dataclass
class SpecChange:
    """Represents a single change in a specification."""
    path: str  # Path to the changed element (e.g., "/paths//api/users/get")
    change_type: ChangeType
    severity: ChangeSeverity
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str = ""


@dataclass
class DiffResult:
    """Result of comparing two specifications."""
    old_spec: Specification
    new_spec: Specification
    changes: List[SpecChange] = field(default_factory=list)
    compared_at: datetime = field(default_factory=datetime.now)

    @property
    def has_breaking_changes(self) -> bool:
        """Check if there are any breaking changes."""
        return any(c.severity == ChangeSeverity.BREAKING for c in self.changes)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.changes) > 0

    @property
    def breaking_changes(self) -> List[SpecChange]:
        """Get all breaking changes."""
        return [c for c in self.changes if c.severity == ChangeSeverity.BREAKING]

    @property
    def non_breaking_changes(self) -> List[SpecChange]:
        """Get all non-breaking changes."""
        return [c for c in self.changes if c.severity == ChangeSeverity.NON_BREAKING]

    @property
    def summary(self) -> Dict[str, int]:
        """Get summary statistics."""
        return {
            "total_changes": len(self.changes),
            "breaking_changes": len(self.breaking_changes),
            "non_breaking_changes": len(self.non_breaking_changes),
            "added": len([c for c in self.changes if c.change_type == ChangeType.ADDED]),
            "removed": len([c for c in self.changes if c.change_type == ChangeType.REMOVED]),
            "modified": len([c for c in self.changes if c.change_type == ChangeType.MODIFIED]),
        }


class SpecificationDiffer:
    """Compares specifications and detects changes."""

    def diff(self, old_spec: Specification, new_spec: Specification) -> DiffResult:
        """Compare two specifications and detect changes.

        Args:
            old_spec: The older version of the specification
            new_spec: The newer version of the specification

        Returns:
            DiffResult containing all detected changes
        """
        if old_spec.spec_type != new_spec.spec_type:
            logger.warning(
                f"Comparing specs of different types: {old_spec.spec_type} vs {new_spec.spec_type}"
            )

        result = DiffResult(old_spec=old_spec, new_spec=new_spec)

        # Dispatch to type-specific differ
        if old_spec.spec_type == SpecType.OPENAPI and new_spec.spec_type == SpecType.OPENAPI:
            result.changes = self._diff_openapi(old_spec, new_spec)
        elif old_spec.spec_type == SpecType.JSONSCHEMA and new_spec.spec_type == SpecType.JSONSCHEMA:
            result.changes = self._diff_jsonschema(old_spec, new_spec)
        elif old_spec.spec_type == SpecType.GRAPHQL and new_spec.spec_type == SpecType.GRAPHQL:
            result.changes = self._diff_graphql(old_spec, new_spec)
        else:
            # Generic text-based diff for other types
            result.changes = self._diff_generic(old_spec, new_spec)

        return result

    def _diff_openapi(self, old_spec: Specification, new_spec: Specification) -> List[SpecChange]:
        """Detect changes in OpenAPI specifications."""
        changes = []

        try:
            old_content = json.loads(old_spec.content)
            new_content = json.loads(new_spec.content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing OpenAPI JSON: {e}")
            return self._diff_generic(old_spec, new_spec)

        # Compare paths (endpoints)
        old_paths = set(old_content.get("paths", {}).keys())
        new_paths = set(new_content.get("paths", {}).keys())

        # Removed endpoints are breaking changes
        for path in old_paths - new_paths:
            changes.append(SpecChange(
                path=f"/paths{path}",
                change_type=ChangeType.REMOVED,
                severity=ChangeSeverity.BREAKING,
                old_value=old_content["paths"][path],
                description=f"Endpoint {path} was removed"
            ))

        # Added endpoints are non-breaking
        for path in new_paths - old_paths:
            changes.append(SpecChange(
                path=f"/paths{path}",
                change_type=ChangeType.ADDED,
                severity=ChangeSeverity.NON_BREAKING,
                new_value=new_content["paths"][path],
                description=f"Endpoint {path} was added"
            ))

        # Compare common endpoints
        for path in old_paths & new_paths:
            old_path_def = old_content["paths"][path]
            new_path_def = new_content["paths"][path]

            # Compare methods
            old_methods = set(old_path_def.keys())
            new_methods = set(new_path_def.keys())

            # Removed methods are breaking
            for method in old_methods - new_methods:
                changes.append(SpecChange(
                    path=f"/paths{path}/{method}",
                    change_type=ChangeType.REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    old_value=old_path_def[method],
                    description=f"Method {method.upper()} on {path} was removed"
                ))

            # Added methods are non-breaking
            for method in new_methods - old_methods:
                changes.append(SpecChange(
                    path=f"/paths{path}/{method}",
                    change_type=ChangeType.ADDED,
                    severity=ChangeSeverity.NON_BREAKING,
                    new_value=new_path_def[method],
                    description=f"Method {method.upper()} on {path} was added"
                ))

            # Compare parameters for common methods
            for method in old_methods & new_methods:
                old_params = old_path_def[method].get("parameters", [])
                new_params = new_path_def[method].get("parameters", [])

                param_changes = self._diff_openapi_parameters(
                    path, method, old_params, new_params
                )
                changes.extend(param_changes)

        # Compare schemas
        old_schemas = old_content.get("components", {}).get("schemas", {})
        new_schemas = new_content.get("components", {}).get("schemas", {})
        schema_changes = self._diff_openapi_schemas(old_schemas, new_schemas)
        changes.extend(schema_changes)

        return changes

    def _diff_openapi_parameters(
        self, path: str, method: str, old_params: List[Dict], new_params: List[Dict]
    ) -> List[SpecChange]:
        """Compare parameters for an OpenAPI endpoint."""
        changes = []

        # Build parameter maps by name and location
        old_param_map = {(p.get("name"), p.get("in")): p for p in old_params}
        new_param_map = {(p.get("name"), p.get("in")): p for p in new_params}

        old_keys = set(old_param_map.keys())
        new_keys = set(new_param_map.keys())

        # Removed required parameters are breaking
        for key in old_keys - new_keys:
            old_param = old_param_map[key]
            name, location = key
            severity = (
                ChangeSeverity.BREAKING if old_param.get("required", False)
                else ChangeSeverity.NON_BREAKING
            )
            changes.append(SpecChange(
                path=f"/paths{path}/{method}/parameters/{name}",
                change_type=ChangeType.REMOVED,
                severity=severity,
                old_value=old_param,
                description=f"Parameter {name} ({location}) was removed"
            ))

        # Added required parameters are breaking
        for key in new_keys - old_keys:
            new_param = new_param_map[key]
            name, location = key
            severity = (
                ChangeSeverity.BREAKING if new_param.get("required", False)
                else ChangeSeverity.NON_BREAKING
            )
            changes.append(SpecChange(
                path=f"/paths{path}/{method}/parameters/{name}",
                change_type=ChangeType.ADDED,
                severity=severity,
                new_value=new_param,
                description=f"Parameter {name} ({location}) was added"
            ))

        # Check for requirement changes in common parameters
        for key in old_keys & new_keys:
            old_param = old_param_map[key]
            new_param = new_param_map[key]
            name, location = key

            old_required = old_param.get("required", False)
            new_required = new_param.get("required", False)

            if not old_required and new_required:
                # Making a parameter required is breaking
                changes.append(SpecChange(
                    path=f"/paths{path}/{method}/parameters/{name}",
                    change_type=ChangeType.MODIFIED,
                    severity=ChangeSeverity.BREAKING,
                    old_value=old_param,
                    new_value=new_param,
                    description=f"Parameter {name} is now required"
                ))
            elif old_required and not new_required:
                # Making a parameter optional is non-breaking
                changes.append(SpecChange(
                    path=f"/paths{path}/{method}/parameters/{name}",
                    change_type=ChangeType.MODIFIED,
                    severity=ChangeSeverity.NON_BREAKING,
                    old_value=old_param,
                    new_value=new_param,
                    description=f"Parameter {name} is now optional"
                ))

        return changes

    def _diff_openapi_schemas(
        self, old_schemas: Dict[str, Any], new_schemas: Dict[str, Any]
    ) -> List[SpecChange]:
        """Compare OpenAPI schema definitions."""
        changes = []

        old_schema_names = set(old_schemas.keys())
        new_schema_names = set(new_schemas.keys())

        # Removed schemas might be breaking (depends on usage)
        for name in old_schema_names - new_schema_names:
            changes.append(SpecChange(
                path=f"/components/schemas/{name}",
                change_type=ChangeType.REMOVED,
                severity=ChangeSeverity.BREAKING,
                old_value=old_schemas[name],
                description=f"Schema {name} was removed"
            ))

        # Added schemas are non-breaking
        for name in new_schema_names - old_schema_names:
            changes.append(SpecChange(
                path=f"/components/schemas/{name}",
                change_type=ChangeType.ADDED,
                severity=ChangeSeverity.NON_BREAKING,
                new_value=new_schemas[name],
                description=f"Schema {name} was added"
            ))

        # Compare common schemas
        for name in old_schema_names & new_schema_names:
            old_schema = old_schemas[name]
            new_schema = new_schemas[name]

            # Check for removed required properties (breaking)
            old_required = set(old_schema.get("required", []))
            new_required = set(new_schema.get("required", []))

            for prop in old_required - new_required:
                changes.append(SpecChange(
                    path=f"/components/schemas/{name}/required/{prop}",
                    change_type=ChangeType.REMOVED,
                    severity=ChangeSeverity.NON_BREAKING,
                    description=f"Property {prop} is no longer required in {name}"
                ))

            for prop in new_required - old_required:
                changes.append(SpecChange(
                    path=f"/components/schemas/{name}/required/{prop}",
                    change_type=ChangeType.ADDED,
                    severity=ChangeSeverity.BREAKING,
                    description=f"Property {prop} is now required in {name}"
                ))

            # Check for removed properties (breaking)
            old_props = set(old_schema.get("properties", {}).keys())
            new_props = set(new_schema.get("properties", {}).keys())

            for prop in old_props - new_props:
                changes.append(SpecChange(
                    path=f"/components/schemas/{name}/properties/{prop}",
                    change_type=ChangeType.REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    description=f"Property {prop} was removed from {name}"
                ))

            for prop in new_props - old_props:
                changes.append(SpecChange(
                    path=f"/components/schemas/{name}/properties/{prop}",
                    change_type=ChangeType.ADDED,
                    severity=ChangeSeverity.NON_BREAKING,
                    description=f"Property {prop} was added to {name}"
                ))

        return changes

    def _diff_jsonschema(self, old_spec: Specification, new_spec: Specification) -> List[SpecChange]:
        """Detect changes in JSON Schema specifications."""
        changes = []

        try:
            old_content = json.loads(old_spec.content)
            new_content = json.loads(new_spec.content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON Schema: {e}")
            return self._diff_generic(old_spec, new_spec)

        # Compare required properties
        old_required = set(old_content.get("required", []))
        new_required = set(new_content.get("required", []))

        for prop in new_required - old_required:
            changes.append(SpecChange(
                path=f"/required/{prop}",
                change_type=ChangeType.ADDED,
                severity=ChangeSeverity.BREAKING,
                description=f"Property {prop} is now required"
            ))

        for prop in old_required - new_required:
            changes.append(SpecChange(
                path=f"/required/{prop}",
                change_type=ChangeType.REMOVED,
                severity=ChangeSeverity.NON_BREAKING,
                description=f"Property {prop} is no longer required"
            ))

        # Compare properties
        old_props = set(old_content.get("properties", {}).keys())
        new_props = set(new_content.get("properties", {}).keys())

        for prop in old_props - new_props:
            changes.append(SpecChange(
                path=f"/properties/{prop}",
                change_type=ChangeType.REMOVED,
                severity=ChangeSeverity.BREAKING,
                old_value=old_content["properties"][prop],
                description=f"Property {prop} was removed"
            ))

        for prop in new_props - old_props:
            changes.append(SpecChange(
                path=f"/properties/{prop}",
                change_type=ChangeType.ADDED,
                severity=ChangeSeverity.NON_BREAKING,
                new_value=new_content["properties"][prop],
                description=f"Property {prop} was added"
            ))

        return changes

    def _diff_graphql(self, old_spec: Specification, new_spec: Specification) -> List[SpecChange]:
        """Detect changes in GraphQL specifications."""
        changes = []

        # Parse GraphQL SDL to extract types and fields
        old_types = self._parse_graphql_types(old_spec.content)
        new_types = self._parse_graphql_types(new_spec.content)

        old_type_names = set(old_types.keys())
        new_type_names = set(new_types.keys())

        # Removed types are breaking
        for type_name in old_type_names - new_type_names:
            changes.append(SpecChange(
                path=f"/types/{type_name}",
                change_type=ChangeType.REMOVED,
                severity=ChangeSeverity.BREAKING,
                description=f"Type {type_name} was removed"
            ))

        # Added types are non-breaking
        for type_name in new_type_names - old_type_names:
            changes.append(SpecChange(
                path=f"/types/{type_name}",
                change_type=ChangeType.ADDED,
                severity=ChangeSeverity.NON_BREAKING,
                description=f"Type {type_name} was added"
            ))

        # Compare common types
        for type_name in old_type_names & new_type_names:
            old_fields = old_types[type_name]
            new_fields = new_types[type_name]

            old_field_names = set(old_fields)
            new_field_names = set(new_fields)

            # Removed fields are breaking
            for field in old_field_names - new_field_names:
                changes.append(SpecChange(
                    path=f"/types/{type_name}/fields/{field}",
                    change_type=ChangeType.REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    description=f"Field {field} was removed from {type_name}"
                ))

            # Added fields are non-breaking
            for field in new_field_names - old_field_names:
                changes.append(SpecChange(
                    path=f"/types/{type_name}/fields/{field}",
                    change_type=ChangeType.ADDED,
                    severity=ChangeSeverity.NON_BREAKING,
                    description=f"Field {field} was added to {type_name}"
                ))

        return changes

    def _parse_graphql_types(self, content: str) -> Dict[str, Set[str]]:
        """Parse GraphQL SDL to extract type definitions.

        Returns a dict mapping type names to sets of field names.
        This is a simple parser for basic type extraction.
        """
        types = {}
        current_type = None

        for line in content.split('\n'):
            line = line.strip()

            # Match type definitions
            if line.startswith('type '):
                current_type = line.split()[1].rstrip('{')
                types[current_type] = set()
            elif current_type and ':' in line and not line.startswith('#'):
                # Extract field name
                field_name = line.split(':')[0].strip()
                if field_name:
                    types[current_type].add(field_name)
            elif line == '}':
                current_type = None

        return types

    def _diff_generic(self, old_spec: Specification, new_spec: Specification) -> List[SpecChange]:
        """Generic text-based diff for specifications without type-specific logic."""
        changes = []

        # Use difflib to get line-by-line diff
        old_lines = old_spec.content.splitlines()
        new_lines = new_spec.content.splitlines()

        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"{old_spec.name} v{old_spec.version}",
            tofile=f"{new_spec.name} v{new_spec.version}",
            lineterm=''
        ))

        if len(diff) > 2:  # Skip header lines
            changes.append(SpecChange(
                path="/content",
                change_type=ChangeType.MODIFIED,
                severity=ChangeSeverity.UNKNOWN,
                old_value=old_spec.content,
                new_value=new_spec.content,
                description=f"Content modified ({len(diff) - 2} lines changed)"
            ))

        return changes


def diff_specifications(
    old_spec: Specification, new_spec: Specification
) -> DiffResult:
    """Convenience function to diff two specifications.

    Args:
        old_spec: The older version
        new_spec: The newer version

    Returns:
        DiffResult with detected changes
    """
    differ = SpecificationDiffer()
    return differ.diff(old_spec, new_spec)
