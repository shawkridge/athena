"""Package.json parser for extracting npm/yarn dependencies and metadata.

Supports:
- Dependencies (runtime)
- DevDependencies (development)
- PeerDependencies (peer)
- OptionalDependencies (optional)
- Scripts extraction
- Version detection
- Type information (TypeScript, React, Expo, etc.)
"""

import json
from typing import Optional, Dict, Any
from .symbol_models import Symbol, SymbolType, create_symbol


class PackageJsonParser:
    """Parser for package.json files to extract dependency and metadata symbols."""

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a package.json file and extract symbols.

        Args:
            file_path: Path to package.json file
            code: Optional file content (if not provided, file will be read)

        Returns:
            List of extracted symbols (packages, scripts, metadata)
        """
        if code is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []

        try:
            data = json.loads(code)
        except json.JSONDecodeError:
            return []

        # Extract package metadata
        if "name" in data:
            name_symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="package.name",
                namespace="metadata",
                signature=data["name"],
                line_start=1,
                line_end=1,
                code="",
                docstring="Package name",
                language="json",
                visibility="public",
            )
            symbols.append(name_symbol)

        if "version" in data:
            version_symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="package.version",
                namespace="metadata",
                signature=data["version"],
                line_start=1,
                line_end=1,
                code="",
                docstring="Package version",
                language="json",
                visibility="public",
            )
            symbols.append(version_symbol)

        # Extract dependencies
        dependencies_symbols = self._extract_dependencies(
            data.get("dependencies", {}), file_path, "dependencies"
        )
        symbols.extend(dependencies_symbols)

        # Extract dev dependencies
        dev_deps_symbols = self._extract_dependencies(
            data.get("devDependencies", {}), file_path, "devDependencies"
        )
        symbols.extend(dev_deps_symbols)

        # Extract peer dependencies
        peer_deps_symbols = self._extract_dependencies(
            data.get("peerDependencies", {}), file_path, "peerDependencies"
        )
        symbols.extend(peer_deps_symbols)

        # Extract optional dependencies
        optional_deps_symbols = self._extract_dependencies(
            data.get("optionalDependencies", {}), file_path, "optionalDependencies"
        )
        symbols.extend(optional_deps_symbols)

        # Extract scripts
        scripts_symbols = self._extract_scripts(data.get("scripts", {}), file_path)
        symbols.extend(scripts_symbols)

        # Extract type information (engines, types field, etc.)
        type_info_symbols = self._extract_type_info(data, file_path)
        symbols.extend(type_info_symbols)

        return symbols

    def _extract_dependencies(
        self, deps: Dict[str, str], file_path: str, dep_type: str
    ) -> list[Symbol]:
        """Extract dependency symbols from dependencies object.

        Args:
            deps: Dictionary of dependencies {package_name: version_range}
            file_path: Path to package.json
            dep_type: Type of dependency (dependencies, devDependencies, etc.)

        Returns:
            List of dependency symbols
        """
        symbols = []

        for package_name, version_range in deps.items():
            # Determine visibility based on dev vs runtime
            visibility = "private" if dep_type == "devDependencies" else "public"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.IMPORT,
                name=package_name,
                namespace=dep_type,
                signature=version_range,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"{dep_type}: {package_name}@{version_range}",
                language="json",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_scripts(self, scripts: Dict[str, str], file_path: str) -> list[Symbol]:
        """Extract npm script symbols.

        Args:
            scripts: Dictionary of scripts {script_name: command}
            file_path: Path to package.json

        Returns:
            List of script symbols
        """
        symbols = []

        for script_name, command in scripts.items():
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.FUNCTION,
                name=script_name,
                namespace="scripts",
                signature=command,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"npm script: {script_name}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        return symbols

    def _extract_type_info(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract type information and engine requirements.

        Args:
            data: Parsed package.json data
            file_path: Path to package.json

        Returns:
            List of type/requirement symbols
        """
        symbols = []

        # Extract engines (Node version, npm version requirements)
        engines = data.get("engines", {})
        for engine_name, version_spec in engines.items():
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"engine.{engine_name}",
                namespace="engines",
                signature=version_spec,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Engine requirement: {engine_name} {version_spec}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract TypeScript type declaration field
        if "types" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="typescript.types",
                namespace="types",
                signature=data["types"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"TypeScript types file: {data['types']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract TypeScript config field
        if "typings" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="typescript.typings",
                namespace="types",
                signature=data["typings"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"TypeScript typings file: {data['typings']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract main entry point
        if "main" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="entry.main",
                namespace="entry",
                signature=data["main"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Main entry point: {data['main']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract module entry point (ES modules)
        if "module" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="entry.module",
                namespace="entry",
                signature=data["module"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"ES module entry point: {data['module']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract exports field (modern entry points)
        exports = data.get("exports", {})
        if isinstance(exports, dict):
            for export_key, export_value in exports.items():
                if isinstance(export_value, str):
                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.CONSTANT,
                        name=f"export.{export_key}",
                        namespace="exports",
                        signature=export_value,
                        line_start=1,
                        line_end=1,
                        code="",
                        docstring=f"Export condition '{export_key}': {export_value}",
                        language="json",
                        visibility="public",
                    )
                    symbols.append(symbol)

        return symbols
