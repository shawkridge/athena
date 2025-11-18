"""Extract OpenAPI specifications from Python web frameworks."""

import ast
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from ..models import Specification, SpecType, SpecStatus
from .base import SpecExtractor, ExtractionResult, ExtractionConfig

logger = logging.getLogger(__name__)


class PythonAPIExtractor(SpecExtractor):
    """Extract OpenAPI specs from FastAPI and Flask applications.

    Supports:
    - FastAPI: Uses built-in app.openapi() method
    - Flask: Uses flask-smorest or APIFlask if available

    Example:
        >>> extractor = PythonAPIExtractor()
        >>> result = extractor.extract(Path("api/main.py"))
        >>> print(f"Extracted {result.spec.name}")
    """

    def can_extract(self, source: Any, config: Optional[ExtractionConfig] = None) -> bool:
        """Check if source is a Python API file.

        Args:
            source: Path to Python file
            config: Optional extraction configuration

        Returns:
            True if file contains FastAPI or Flask imports
        """
        if not isinstance(source, (str, Path)):
            return False

        path = Path(source)
        if not path.exists() or path.suffix != ".py":
            return False

        try:
            content = path.read_text()

            # Check for framework imports
            has_fastapi = "from fastapi import" in content or "import fastapi" in content
            has_flask = "from flask import" in content or "import flask" in content

            return has_fastapi or has_flask

        except Exception as e:
            logger.warning(f"Error reading {path}: {e}")
            return False

    def extract(
        self,
        source: Any,
        config: Optional[ExtractionConfig] = None
    ) -> ExtractionResult:
        """Extract OpenAPI spec from Python API file.

        Args:
            source: Path to Python file
            config: Optional extraction configuration

        Returns:
            ExtractionResult with OpenAPI spec

        Raises:
            ValueError: If extraction fails
        """
        path = Path(source)
        if not path.exists():
            raise ValueError(f"Source file not found: {path}")

        config = config or ExtractionConfig()

        # Detect framework
        content = path.read_text()
        is_fastapi = "from fastapi import" in content or "import fastapi" in content
        is_flask = "from flask import" in content or "import flask" in content

        if is_fastapi:
            return self._extract_fastapi(path, content, config)
        elif is_flask:
            return self._extract_flask(path, content, config)
        else:
            raise ValueError("No supported framework detected")

    def get_supported_spec_types(self) -> List[SpecType]:
        """Get supported spec types.

        Returns:
            [SpecType.OPENAPI]
        """
        return [SpecType.OPENAPI]

    def get_name(self) -> str:
        """Get extractor name."""
        return "Python API Extractor (FastAPI/Flask)"

    def _extract_fastapi(
        self,
        path: Path,
        content: str,
        config: ExtractionConfig
    ) -> ExtractionResult:
        """Extract OpenAPI spec from FastAPI application.

        FastAPI provides a built-in openapi() method that generates the spec.
        We'll try to import the app and call this method.

        Args:
            path: Path to FastAPI file
            content: File content
            config: Extraction configuration

        Returns:
            ExtractionResult with OpenAPI spec
        """
        warnings = []
        metadata = {"framework": "FastAPI", "source_file": str(path)}

        try:
            # Try to extract app name from AST
            app_name = self._find_fastapi_app_name(content)
            if not app_name:
                warnings.append("Could not find FastAPI app instance name")
                app_name = "app"  # Default

            metadata["app_name"] = app_name

            # Try to extract spec using dynamic import
            openapi_spec = self._extract_openapi_dynamically(path, app_name)

            if openapi_spec:
                # Successfully extracted
                spec_dict = openapi_spec if isinstance(openapi_spec, dict) else json.loads(openapi_spec)

                # Get metadata from spec
                info = spec_dict.get("info", {})
                title = info.get("title", config.output_name or path.stem.replace("_", " ").title())
                version = info.get("version", config.output_version)
                description = info.get("description", config.output_description or f"Extracted from {path.name}")

                # Count endpoints
                paths = spec_dict.get("paths", {})
                endpoint_count = sum(len(methods) for methods in paths.values())
                metadata["endpoint_count"] = endpoint_count

                # Create specification
                spec = Specification(
                    project_id=config.project_id,
                    name=title,
                    spec_type=SpecType.OPENAPI,
                    version=version,
                    status=SpecStatus.ACTIVE,
                    content=json.dumps(spec_dict, indent=2),
                    description=description,
                )

                return self.validate_result(ExtractionResult(
                    spec=spec,
                    confidence=0.95,  # High confidence for FastAPI built-in extraction
                    warnings=warnings,
                    coverage=1.0,
                    extraction_method="FastAPI built-in openapi() method",
                    metadata=metadata,
                ))

        except Exception as e:
            logger.error(f"Error extracting FastAPI spec: {e}")
            warnings.append(f"Extraction error: {str(e)}")

        # Fallback: Static analysis
        return self._extract_fastapi_static(path, content, config, warnings, metadata)

    def _find_fastapi_app_name(self, content: str) -> Optional[str]:
        """Find FastAPI app instance name using AST.

        Args:
            content: Python file content

        Returns:
            App variable name, or None
        """
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Look for: app = FastAPI()
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # Check if value is a FastAPI() call
                            if isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Name):
                                    if node.value.func.id == "FastAPI":
                                        return target.id

            return None

        except SyntaxError:
            return None

    def _extract_openapi_dynamically(self, path: Path, app_name: str) -> Optional[dict]:
        """Try to import app and call openapi() method.

        This is risky because it executes user code, so we do it in a try/except
        and with minimal imports.

        Args:
            path: Path to module
            app_name: Name of app instance

        Returns:
            OpenAPI spec dict, or None if extraction fails
        """
        try:
            # Add parent directory to path
            parent_dir = str(path.parent.resolve())
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)

            # Import module
            module_name = path.stem
            module = __import__(module_name)

            # Get app instance
            if not hasattr(module, app_name):
                logger.warning(f"Module {module_name} has no attribute {app_name}")
                return None

            app = getattr(module, app_name)

            # Check if it has openapi() method (FastAPI)
            if hasattr(app, "openapi"):
                return app.openapi()

            return None

        except Exception as e:
            logger.warning(f"Could not dynamically extract OpenAPI spec: {e}")
            return None
        finally:
            # Clean up sys.path
            if parent_dir in sys.path:
                sys.path.remove(parent_dir)

    def _extract_fastapi_static(
        self,
        path: Path,
        content: str,
        config: ExtractionConfig,
        warnings: List[str],
        metadata: dict
    ) -> ExtractionResult:
        """Extract FastAPI spec using static analysis as fallback.

        This is less accurate but doesn't require executing user code.

        Args:
            path: Path to file
            content: File content
            config: Extraction configuration
            warnings: Existing warnings list
            metadata: Existing metadata dict

        Returns:
            ExtractionResult with best-effort OpenAPI spec
        """
        warnings.append("Using static analysis (less accurate than dynamic extraction)")

        try:
            tree = ast.parse(content)

            # Find FastAPI app initialization
            app_title = config.output_name or path.stem.replace("_", " ").title()
            app_version = config.output_version

            # Extract route decorators
            routes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        route_info = self._parse_fastapi_route(decorator, node)
                        if route_info:
                            routes.append(route_info)

            # Build minimal OpenAPI spec
            openapi_spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": app_title,
                    "version": app_version,
                    "description": config.output_description or f"Extracted from {path.name} (static analysis)"
                },
                "paths": {}
            }

            # Add routes
            for route in routes:
                path_key = route["path"]
                method = route["method"].lower()

                if path_key not in openapi_spec["paths"]:
                    openapi_spec["paths"][path_key] = {}

                openapi_spec["paths"][path_key][method] = {
                    "summary": route.get("summary", route["function_name"]),
                    "responses": {
                        "200": {"description": "Successful response"}
                    }
                }

            metadata["endpoint_count"] = len(routes)
            metadata["extraction_method"] = "static_analysis"

            spec = Specification(
                project_id=config.project_id,
                name=app_title,
                spec_type=SpecType.OPENAPI,
                version=app_version,
                status=SpecStatus.ACTIVE,
                content=json.dumps(openapi_spec, indent=2),
                description=f"Extracted from {path.name} (static analysis)",
            )

            return self.validate_result(ExtractionResult(
                spec=spec,
                confidence=0.65,  # Lower confidence for static analysis
                warnings=warnings,
                coverage=0.8,  # May miss some dynamic routes
                extraction_method="Static AST analysis",
                metadata=metadata,
            ))

        except Exception as e:
            logger.error(f"Static analysis failed: {e}")
            raise ValueError(f"Failed to extract FastAPI spec: {e}")

    def _parse_fastapi_route(self, decorator: ast.expr, function: ast.FunctionDef) -> Optional[dict]:
        """Parse FastAPI route decorator.

        Args:
            decorator: AST decorator node
            function: Function being decorated

        Returns:
            Dict with route info, or None
        """
        try:
            # Handle @app.get("/path"), @app.post("/path"), etc.
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr  # get, post, put, delete, etc.

                    # Get path from first argument
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value

                        return {
                            "path": path,
                            "method": method.upper(),
                            "function_name": function.name
                        }

            return None

        except Exception:
            return None

    def _extract_flask(
        self,
        path: Path,
        content: str,
        config: ExtractionConfig
    ) -> ExtractionResult:
        """Extract OpenAPI spec from Flask application.

        Flask doesn't have built-in OpenAPI generation, so we use static analysis.

        Args:
            path: Path to Flask file
            content: File content
            config: Extraction configuration

        Returns:
            ExtractionResult with OpenAPI spec
        """
        warnings = ["Flask extraction uses static analysis (may be incomplete)"]
        metadata = {"framework": "Flask", "source_file": str(path)}

        try:
            tree = ast.parse(content)

            app_title = config.output_name or path.stem.replace("_", " ").title()
            app_version = config.output_version

            # Extract Flask routes
            routes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        route_info = self._parse_flask_route(decorator, node)
                        if route_info:
                            routes.append(route_info)

            # Build OpenAPI spec
            openapi_spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": app_title,
                    "version": app_version,
                    "description": config.output_description or f"Extracted from {path.name}"
                },
                "paths": {}
            }

            # Add routes
            for route in routes:
                path_key = route["path"]
                methods = route.get("methods", ["GET"])

                if path_key not in openapi_spec["paths"]:
                    openapi_spec["paths"][path_key] = {}

                for method in methods:
                    openapi_spec["paths"][path_key][method.lower()] = {
                        "summary": route["function_name"],
                        "responses": {
                            "200": {"description": "Successful response"}
                        }
                    }

            metadata["endpoint_count"] = len(routes)

            spec = Specification(
                project_id=config.project_id,
                name=app_title,
                spec_type=SpecType.OPENAPI,
                version=app_version,
                status=SpecStatus.ACTIVE,
                content=json.dumps(openapi_spec, indent=2),
                description=f"Extracted from {path.name} (Flask static analysis)",
            )

            return self.validate_result(ExtractionResult(
                spec=spec,
                confidence=0.60,  # Lower confidence for Flask without extensions
                warnings=warnings,
                coverage=0.7,
                extraction_method="Static AST analysis (Flask)",
                metadata=metadata,
            ))

        except Exception as e:
            logger.error(f"Flask extraction failed: {e}")
            raise ValueError(f"Failed to extract Flask spec: {e}")

    def _parse_flask_route(self, decorator: ast.expr, function: ast.FunctionDef) -> Optional[dict]:
        """Parse Flask route decorator.

        Args:
            decorator: AST decorator node
            function: Function being decorated

        Returns:
            Dict with route info, or None
        """
        try:
            # Handle @app.route("/path", methods=["GET", "POST"])
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "route":
                        # Get path from first argument
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            path = decorator.args[0].value

                            # Get methods from keyword arguments
                            methods = ["GET"]  # Default
                            for keyword in decorator.keywords:
                                if keyword.arg == "methods":
                                    if isinstance(keyword.value, ast.List):
                                        methods = [
                                            elt.value for elt in keyword.value.elts
                                            if isinstance(elt, ast.Constant)
                                        ]

                            return {
                                "path": path,
                                "methods": methods,
                                "function_name": function.name
                            }

            return None

        except Exception:
            return None
