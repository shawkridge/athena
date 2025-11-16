"""API discovery system for dynamic API introspection and cataloging."""

import inspect
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import re
from .models import APISpec, APIParameter, APIExample


class APIDiscovery:
    """Discover and catalog available APIs at runtime."""

    def __init__(self, api_root: Optional[str] = None):
        """Initialize API discovery system.

        Args:
            api_root: Root directory to search for APIs. If None, uses src/athena/api
        """
        if api_root is None:
            # Auto-detect api_root from current file location
            current_dir = Path(__file__).parent
            api_root = str(current_dir)

        self.api_root = Path(api_root)
        self._cache: Dict[str, List[APISpec]] = {}
        self._all_apis_cache: Optional[Dict[str, List[APISpec]]] = None

    def discover_all(self, use_cache: bool = True) -> Dict[str, List[APISpec]]:
        """Discover all available APIs by category.

        Args:
            use_cache: Whether to use cached results

        Returns:
            Dictionary mapping category names to lists of APISpec objects
        """
        if use_cache and self._all_apis_cache is not None:
            return self._all_apis_cache

        apis: Dict[str, List[APISpec]] = {}

        if not self.api_root.exists():
            return apis

        for item in self.api_root.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            category = item.name
            apis[category] = self._discover_category(item, use_cache=use_cache)

        self._all_apis_cache = apis
        return apis

    def _discover_category(self, category_dir: Path, use_cache: bool = True) -> List[APISpec]:
        """Discover APIs in a specific category directory.

        Args:
            category_dir: Directory containing API modules
            use_cache: Whether to use cached results

        Returns:
            List of APISpec objects for the category
        """
        category_name = category_dir.name

        if use_cache and category_name in self._cache:
            return self._cache[category_name]

        specs: List[APISpec] = []

        for file_path in sorted(category_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue

            try:
                module = self._import_module(file_path)
                if module is None:
                    continue

                for name, obj in inspect.getmembers(module):
                    if self._is_api_function(obj):
                        spec = self._extract_spec(name, obj, category_name)
                        if spec is not None:
                            specs.append(spec)
            except Exception as e:
                # Log error but continue with other modules
                print(f"Warning: Failed to discover APIs in {file_path}: {e}")
                continue

        self._cache[category_name] = specs
        return specs

    def _import_module(self, file_path: Path) -> Optional[Any]:
        """Import a Python module from file path.

        Args:
            file_path: Path to Python file

        Returns:
            Imported module or None if import fails
        """
        try:
            module_name = f"_athena_api_{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)

            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            return module
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def _is_api_function(self, obj: Any) -> bool:
        """Check if object is an API function.

        Args:
            obj: Object to check

        Returns:
            True if object is a callable API function (not private)
        """
        if not callable(obj):
            return False

        # Skip private/magic methods
        if hasattr(obj, "__name__") and obj.__name__.startswith("_"):
            return False

        # Skip built-ins and imports
        if inspect.isbuiltin(obj) or inspect.ismethod(obj):
            return False

        # Accept functions and coroutines
        return inspect.isfunction(obj) or inspect.iscoroutinefunction(obj)

    def _extract_spec(self, name: str, func: Callable, category: str) -> Optional[APISpec]:
        """Extract API specification from a function.

        Args:
            name: Function name
            func: Function object
            category: API category

        Returns:
            APISpec object or None if extraction fails
        """
        try:
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""

            # Extract first line as short docstring
            docstring = doc.split("\n")[0] if doc else ""

            parameters = self._extract_parameters(func, sig, doc)
            return_type = self._extract_return_type(sig)
            examples = self._extract_examples(doc)

            return APISpec(
                name=name,
                module=func.__module__,
                signature=str(sig),
                docstring=docstring,
                parameters=parameters,
                return_type=return_type,
                examples=examples,
                category=category,
            )
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def _extract_parameters(self, func: Callable, sig: inspect.Signature, doc: str) -> List[APIParameter]:
        """Extract parameter specifications from function.

        Args:
            func: Function object
            sig: Function signature
            doc: Function docstring

        Returns:
            List of APIParameter objects
        """
        parameters: List[APIParameter] = []
        param_docs = self._parse_param_docs(doc)

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = self._format_type(param.annotation)
            description = param_docs.get(param_name, "")
            required = param.default == inspect.Parameter.empty

            parameters.append(
                APIParameter(
                    name=param_name,
                    type=param_type,
                    default=param.default if param.default != inspect.Parameter.empty else None,
                    description=description,
                    required=required,
                )
            )

        return parameters

    def _extract_return_type(self, sig: inspect.Signature) -> str:
        """Extract return type from signature.

        Args:
            sig: Function signature

        Returns:
            Formatted return type string
        """
        if sig.return_annotation == inspect.Signature.empty:
            return "Any"
        return self._format_type(sig.return_annotation)

    def _format_type(self, annotation: Any) -> str:
        """Format type annotation as string.

        Args:
            annotation: Type annotation

        Returns:
            Formatted type string
        """
        if annotation == inspect.Parameter.empty:
            return "Any"

        if hasattr(annotation, "__name__"):
            return annotation.__name__

        return str(annotation).replace("typing.", "")

    def _parse_param_docs(self, doc: str) -> Dict[str, str]:
        """Parse parameter descriptions from docstring.

        Args:
            doc: Function docstring

        Returns:
            Dictionary mapping parameter names to descriptions
        """
        params: Dict[str, str] = {}

        # Simple pattern matching for "Args:" or "Parameters:" section
        lines = doc.split("\n")
        in_args = False
        current_param = None

        for line in lines:
            if line.strip().lower().startswith(("args:", "parameters:")):
                in_args = True
                continue

            if in_args:
                if line.startswith("    "):
                    # Parameter line
                    match = re.match(r"\s+(\w+)\s*:\s*(.*)", line)
                    if match:
                        current_param = match.group(1)
                        params[current_param] = match.group(2).strip()
                elif line.strip() and not line.startswith(" "):
                    # End of Args section
                    in_args = False

        return params

    def _extract_examples(self, doc: str) -> List[APIExample]:
        """Extract usage examples from docstring.

        Args:
            doc: Function docstring

        Returns:
            List of APIExample objects
        """
        from .models import APIExample

        examples: List[APIExample] = []

        # Simple pattern matching for "Examples:" section
        lines = doc.split("\n")
        in_examples = False
        current_code = []
        current_desc = None

        for line in lines:
            if line.strip().lower().startswith("examples:"):
                in_examples = True
                current_desc = "Example"
                continue

            if in_examples:
                if line.startswith("    "):
                    current_code.append(line[4:])
                elif line.strip() and not line.startswith(" "):
                    # End of Examples section
                    if current_code:
                        examples.append(
                            APIExample(
                                description=current_desc or "Example",
                                code="\n".join(current_code),
                            )
                        )
                    in_examples = False

        if in_examples and current_code:
            examples.append(
                APIExample(
                    description=current_desc or "Example",
                    code="\n".join(current_code),
                )
            )

        return examples

    def get_api(self, path: str) -> Optional[APISpec]:
        """Get specific API spec by path (e.g., 'memory/recall').

        Args:
            path: API path in format "category/function"

        Returns:
            APISpec object or None if not found
        """
        parts = path.split("/")
        if len(parts) != 2:
            return None

        category, function_name = parts
        all_apis = self.discover_all()

        if category not in all_apis:
            return None

        for spec in all_apis[category]:
            if spec.name == function_name:
                return spec

        return None

    def get_apis_by_category(self, category: str) -> List[APISpec]:
        """Get all APIs in a specific category.

        Args:
            category: Category name

        Returns:
            List of APISpec objects in the category
        """
        all_apis = self.discover_all()
        return all_apis.get(category, [])

    def search_apis(self, query: str, limit: int = 5) -> List[APISpec]:
        """Search for APIs matching query.

        Simple text-based search on function names and docstrings.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching APISpec objects
        """
        query_lower = query.lower()
        all_apis = self.discover_all()
        matches: List[APISpec] = []

        for specs in all_apis.values():
            for spec in specs:
                # Score based on name and docstring match
                name_match = query_lower in spec.name.lower()
                doc_match = query_lower in spec.docstring.lower()

                if name_match or doc_match:
                    matches.append(spec)

        # Sort by relevance (name match > docstring match)
        matches.sort(
            key=lambda s: (
                query_lower not in s.name.lower(),  # Name matches first
                s.name,  # Then alphabetically
            )
        )

        return matches[:limit]

    def get_api_categories(self) -> List[str]:
        """Get all available API categories.

        Returns:
            List of category names
        """
        return sorted(self.discover_all().keys())

    def clear_cache(self) -> None:
        """Clear discovery cache."""
        self._cache.clear()
        self._all_apis_cache = None
