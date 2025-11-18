"""TypeScript config parser for extracting configuration metadata.

Supports:
- Compiler options (target, module, lib, etc.)
- TypeScript version detection
- Root configuration options
- Include/exclude patterns
- Path mappings (baseUrl, paths)
- Project references
"""

import json
from typing import Optional, Dict, Any
from .symbol_models import Symbol, SymbolType, create_symbol


class TsConfigParser:
    """Parser for tsconfig.json files to extract TypeScript configuration as symbols."""

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a tsconfig.json file and extract configuration symbols.

        Args:
            file_path: Path to tsconfig.json file
            code: Optional file content (if not provided, file will be read)

        Returns:
            List of extracted symbols (config options, paths, references)
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

        # Extract compiler options
        compiler_options = data.get("compilerOptions", {})
        option_symbols = self._extract_compiler_options(compiler_options, file_path)
        symbols.extend(option_symbols)

        # Extract root configuration options
        root_symbols = self._extract_root_options(data, file_path)
        symbols.extend(root_symbols)

        # Extract include/exclude patterns
        pattern_symbols = self._extract_patterns(data, file_path)
        symbols.extend(pattern_symbols)

        # Extract path mappings
        path_symbols = self._extract_path_mappings(data, file_path)
        symbols.extend(path_symbols)

        # Extract project references
        ref_symbols = self._extract_project_references(data, file_path)
        symbols.extend(ref_symbols)

        return symbols

    def _extract_compiler_options(self, options: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract TypeScript compiler options."""
        symbols = []

        for option_name, option_value in options.items():
            # Convert value to string for signature
            if isinstance(option_value, list):
                signature = ", ".join(str(v) for v in option_value)
            elif isinstance(option_value, dict):
                signature = json.dumps(option_value)
            else:
                signature = str(option_value)

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"compiler.{option_name}",
                namespace="compilerOptions",
                signature=signature,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Compiler option: {option_name}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        return symbols

    def _extract_root_options(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract root level TypeScript config options."""
        symbols = []

        # Extended config
        if "extends" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.extends",
                namespace="root",
                signature=data["extends"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Extended configuration: {data['extends']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Type acquisition
        if "typeAcquisition" in data:
            type_acq = data["typeAcquisition"]
            if isinstance(type_acq, dict):
                for key, value in type_acq.items():
                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.CONSTANT,
                        name=f"typeAcquisition.{key}",
                        namespace="root",
                        signature=str(value),
                        line_start=1,
                        line_end=1,
                        code="",
                        docstring=f"Type acquisition: {key}",
                        language="json",
                        visibility="public",
                    )
                    symbols.append(symbol)

        # Watch options
        if "watchOptions" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.watchOptions",
                namespace="root",
                signature=json.dumps(data["watchOptions"]),
                line_start=1,
                line_end=1,
                code="",
                docstring="Watch configuration for file changes",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        return symbols

    def _extract_patterns(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract include/exclude patterns."""
        symbols = []

        # Include patterns
        includes = data.get("include", [])
        if isinstance(includes, list):
            for pattern in includes:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"pattern.include.{pattern}",
                    namespace="patterns",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Include pattern: {pattern}",
                    language="json",
                    visibility="public",
                )
                symbols.append(symbol)

        # Exclude patterns
        excludes = data.get("exclude", [])
        if isinstance(excludes, list):
            for pattern in excludes:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"pattern.exclude.{pattern}",
                    namespace="patterns",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Exclude pattern: {pattern}",
                    language="json",
                    visibility="public",
                )
                symbols.append(symbol)

        return symbols

    def _extract_path_mappings(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract TypeScript path mappings (baseUrl and paths)."""
        symbols = []

        # Base URL
        if "compilerOptions" in data and "baseUrl" in data["compilerOptions"]:
            base_url = data["compilerOptions"]["baseUrl"]
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="paths.baseUrl",
                namespace="paths",
                signature=base_url,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Base URL for module resolution: {base_url}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Path mappings
        if "compilerOptions" in data and "paths" in data["compilerOptions"]:
            paths = data["compilerOptions"]["paths"]
            if isinstance(paths, dict):
                for alias, mapped_paths in paths.items():
                    if isinstance(mapped_paths, list):
                        paths_str = ", ".join(mapped_paths)
                    else:
                        paths_str = str(mapped_paths)

                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.CONSTANT,
                        name=f"paths.alias.{alias}",
                        namespace="paths",
                        signature=paths_str,
                        line_start=1,
                        line_end=1,
                        code="",
                        docstring=f"Path mapping for alias '{alias}'",
                        language="json",
                        visibility="public",
                    )
                    symbols.append(symbol)

        return symbols

    def _extract_project_references(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract TypeScript project references."""
        symbols = []

        references = data.get("references", [])
        if isinstance(references, list):
            for ref in references:
                if isinstance(ref, dict) and "path" in ref:
                    path = ref["path"]
                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.CONSTANT,
                        name=f"reference.{path}",
                        namespace="references",
                        signature=path,
                        line_start=1,
                        line_end=1,
                        code="",
                        docstring=f"Project reference: {path}",
                        language="json",
                        visibility="public",
                    )
                    symbols.append(symbol)

        return symbols
