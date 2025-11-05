"""Babel config parser for extracting Babel configuration metadata.

Supports:
- Presets (targets, includes)
- Plugins (plugin names and options)
- Env presets (per-environment configuration)
- Source maps and input source maps
- Module configuration
- Root configurations
"""

import json
import re
from typing import Optional, Dict, Any, List
from .symbol_models import Symbol, SymbolType, create_symbol


class BabelConfigParser:
    """Parser for babel.config.js/json files to extract Babel configuration as symbols."""

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a babel.config.js or babel.config.json file and extract symbols.

        Args:
            file_path: Path to babel.config.js or babel.config.json
            code: Optional file content (if not provided, file will be read)

        Returns:
            List of extracted symbols (presets, plugins, configuration)
        """
        if code is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []

        # Try JSON parsing first (for babel.config.json)
        if file_path.endswith('.json'):
            try:
                data = json.loads(code)
                symbols.extend(self._extract_from_json(data, file_path))
                return symbols
            except json.JSONDecodeError:
                return []
        else:
            # For JS files, use regex-based extraction
            symbols.extend(self._extract_from_js(code, file_path))
            return symbols

    def _extract_from_json(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract configuration from JSON data."""
        symbols = []

        # Extract presets
        presets = data.get("presets", [])
        preset_symbols = self._extract_presets(presets, file_path)
        symbols.extend(preset_symbols)

        # Extract plugins
        plugins = data.get("plugins", [])
        plugin_symbols = self._extract_plugins(plugins, file_path)
        symbols.extend(plugin_symbols)

        # Extract env presets
        env_config = data.get("env", {})
        if isinstance(env_config, dict):
            for env_name, env_data in env_config.items():
                if isinstance(env_data, dict):
                    env_presets = env_data.get("presets", [])
                    for preset in env_presets:
                        preset_name = preset if isinstance(preset, str) else preset[0] if isinstance(preset, list) else str(preset)
                        symbol = create_symbol(
                            file_path=file_path,
                            symbol_type=SymbolType.CONSTANT,
                            name=f"env.{env_name}.preset.{preset_name}",
                            namespace="presets",
                            signature=preset_name,
                            line_start=1,
                            line_end=1,
                            code="",
                            docstring=f"Preset for environment '{env_name}'",
                            language="json",
                            visibility="public"
                        )
                        symbols.append(symbol)

        # Extract root configuration options
        if "sourceMap" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.sourceMap",
                namespace="root",
                signature=str(data["sourceMap"]),
                line_start=1,
                line_end=1,
                code="",
                docstring="Source map generation",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        if "minified" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.minified",
                namespace="root",
                signature=str(data["minified"]),
                line_start=1,
                line_end=1,
                code="",
                docstring="Minify output",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        return symbols

    def _extract_from_js(self, code: str, file_path: str) -> list[Symbol]:
        """Extract configuration from JavaScript code using regex."""
        symbols = []

        # Extract presets array
        preset_pattern = r'presets\s*:\s*\[(.*?)\]'
        preset_matches = re.findall(preset_pattern, code, re.DOTALL)
        for match in preset_matches:
            # Extract individual preset names
            presets = re.findall(r'["\']([^"\']+)["\']', match)
            for preset in presets:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"preset.{preset}",
                    namespace="presets",
                    signature=preset,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Babel preset: {preset}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract plugins array
        plugin_pattern = r'plugins\s*:\s*\[(.*?)\]'
        plugin_matches = re.findall(plugin_pattern, code, re.DOTALL)
        for match in plugin_matches:
            # Extract individual plugin names
            plugins = re.findall(r'["\']([^"\']+)["\']', match)
            for plugin in plugins:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"plugin.{plugin}",
                    namespace="plugins",
                    signature=plugin,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Babel plugin: {plugin}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract env configurations
        env_pattern = r'env\s*:\s*{(.*?)}'
        env_match = re.search(env_pattern, code, re.DOTALL)
        if env_match:
            env_content = env_match.group(1)
            # Find environment names and their configurations
            env_configs = re.findall(r'([a-z_]+)\s*:\s*{', env_content)
            for env_name in env_configs:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"env.{env_name}",
                    namespace="environments",
                    signature=env_name,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Environment configuration: {env_name}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        return symbols

    def _extract_presets(self, presets: List[Any], file_path: str) -> list[Symbol]:
        """Extract Babel presets."""
        symbols = []

        for preset in presets:
            # Handle string presets
            if isinstance(preset, str):
                preset_name = preset
                options_str = ""
            # Handle array-based presets with options
            elif isinstance(preset, list) and len(preset) > 0:
                preset_name = preset[0] if isinstance(preset[0], str) else str(preset[0])
                options = preset[1] if len(preset) > 1 else {}
                options_str = json.dumps(options) if isinstance(options, dict) else str(options)
            else:
                continue

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"preset.{preset_name}",
                namespace="presets",
                signature=options_str if options_str else preset_name,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Babel preset: {preset_name}",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        return symbols

    def _extract_plugins(self, plugins: List[Any], file_path: str) -> list[Symbol]:
        """Extract Babel plugins."""
        symbols = []

        for plugin in plugins:
            # Handle string plugins
            if isinstance(plugin, str):
                plugin_name = plugin
                options_str = ""
            # Handle array-based plugins with options
            elif isinstance(plugin, list) and len(plugin) > 0:
                plugin_name = plugin[0] if isinstance(plugin[0], str) else str(plugin[0])
                options = plugin[1] if len(plugin) > 1 else {}
                options_str = json.dumps(options) if isinstance(options, dict) else str(options)
            else:
                continue

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"plugin.{plugin_name}",
                namespace="plugins",
                signature=options_str if options_str else plugin_name,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Babel plugin: {plugin_name}",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        return symbols
