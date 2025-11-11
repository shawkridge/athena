"""API specification models for discovery and documentation."""

from dataclasses import dataclass, asdict
from typing import Any, List, Optional, Dict


@dataclass
class APIParameter:
    """Specification for function parameter."""

    name: str
    type: str
    default: Any = None
    description: str = ""
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "default": None if self.default is None else str(self.default),
            "description": self.description,
            "required": self.required,
        }


@dataclass
class APIExample:
    """Example usage of an API function."""

    description: str
    code: str
    expected_output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "code": self.code,
            "expected_output": self.expected_output,
        }


@dataclass
class APISpec:
    """Full specification of an API function."""

    name: str
    module: str
    signature: str
    docstring: str
    parameters: List[APIParameter]
    return_type: str
    examples: List[APIExample]
    category: Optional[str] = None
    deprecated: bool = False
    version: str = "1.0.0"

    def to_markdown(self) -> str:
        """Generate markdown documentation."""
        doc = f"## {self.name}\n\n"

        if self.docstring:
            doc += f"{self.docstring}\n\n"

        doc += f"### Signature\n```python\n{self.signature}\n```\n\n"

        if self.parameters:
            doc += f"### Parameters\n"
            for param in self.parameters:
                required_str = "required" if param.required else "optional"
                doc += f"- `{param.name}` ({param.type}, {required_str}): {param.description}\n"
            doc += "\n"

        doc += f"### Return\n```\n{self.return_type}\n```\n\n"

        if self.examples:
            doc += f"### Examples\n"
            for example in self.examples:
                doc += f"#### {example.description}\n"
                doc += f"```python\n{example.code}\n```\n"
                if example.expected_output:
                    doc += f"Output: `{example.expected_output}`\n"
                doc += "\n"

        if self.deprecated:
            doc += "⚠️ **Deprecated**: This API is deprecated and will be removed in a future version.\n\n"

        doc += f"**Version**: {self.version}\n"

        return doc

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "module": self.module,
            "signature": self.signature,
            "docstring": self.docstring,
            "category": self.category,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "examples": [e.to_dict() for e in self.examples],
            "deprecated": self.deprecated,
            "version": self.version,
        }

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation for listing APIs (without examples)."""
        return {
            "name": self.name,
            "module": self.module,
            "category": self.category,
            "signature": self.signature,
            "docstring": self.docstring,
            "parameters": [{"name": p.name, "type": p.type} for p in self.parameters],
            "return_type": self.return_type,
        }
