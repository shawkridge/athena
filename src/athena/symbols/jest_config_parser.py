"""Jest config parser for extracting Jest testing configuration metadata.

Supports:
- Test patterns (testMatch, testPathIgnorePatterns, testNamePattern)
- Coverage configuration (collectCoverageFrom, coverageThreshold, coveragePathIgnorePatterns)
- Module paths and aliases (moduleNameMapper, modulePaths, baseUrl)
- Presets and preset configurations
- Transform and preprocessor settings
- Setup files (setupFilesAfterEnv, setupFiles)
- Reporters and report configurations
- Environment configuration (testEnvironment, nodejs/jsdom/etc)
- Globals and test variables
- Timeout settings
- Snapshot configuration
"""

import json
import re
from typing import Optional, Dict, Any, List
from .symbol_models import Symbol, SymbolType, create_symbol


class JestConfigParser:
    """Parser for jest.config.js/json files to extract Jest configuration as symbols."""

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a jest.config.js or jest.config.json file and extract symbols.

        Args:
            file_path: Path to jest.config.js or jest.config.json
            code: Optional file content (if not provided, file will be read)

        Returns:
            List of extracted symbols (test config, coverage, presets, transforms)
        """
        if code is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []

        # Try JSON parsing first (for jest.config.json)
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

        # Extract test environment
        if "testEnvironment" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.testEnvironment",
                namespace="root",
                signature=data["testEnvironment"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Test environment: {data['testEnvironment']}",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        # Extract presets
        if "preset" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.preset",
                namespace="root",
                signature=data["preset"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Jest preset: {data['preset']}",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        # Extract test patterns
        test_patterns = self._extract_test_patterns(data, file_path)
        symbols.extend(test_patterns)

        # Extract coverage configuration
        coverage_symbols = self._extract_coverage_config(data, file_path)
        symbols.extend(coverage_symbols)

        # Extract module paths and aliases
        module_symbols = self._extract_module_paths(data, file_path)
        symbols.extend(module_symbols)

        # Extract transforms
        if "transform" in data and isinstance(data["transform"], dict):
            for pattern, transformer in data["transform"].items():
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"transform.{pattern}",
                    namespace="transforms",
                    signature=transformer,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Transform {pattern} with {transformer}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract setup files
        if "setupFilesAfterEnv" in data and isinstance(data["setupFilesAfterEnv"], list):
            for setup_file in data["setupFilesAfterEnv"]:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"setupFile.{setup_file}",
                    namespace="setupFiles",
                    signature=setup_file,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Setup file: {setup_file}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract test timeout
        if "testTimeout" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.testTimeout",
                namespace="root",
                signature=str(data["testTimeout"]),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Test timeout: {data['testTimeout']}ms",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        # Extract reporters
        if "reporters" in data and isinstance(data["reporters"], list):
            for reporter in data["reporters"]:
                if isinstance(reporter, str):
                    reporter_name = reporter
                elif isinstance(reporter, list) and len(reporter) > 0:
                    reporter_name = reporter[0]
                else:
                    continue

                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"reporter.{reporter_name}",
                    namespace="reporters",
                    signature=reporter_name,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Jest reporter: {reporter_name}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        return symbols

    def _extract_from_js(self, code: str, file_path: str) -> list[Symbol]:
        """Extract configuration from JavaScript code using regex."""
        symbols = []

        # Extract testEnvironment
        env_match = re.search(r'testEnvironment\s*:\s*["\']([^\'"]+)["\']', code)
        if env_match:
            env = env_match.group(1)
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.testEnvironment",
                namespace="root",
                signature=env,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Test environment: {env}",
                language="javascript",
                visibility="public"
            )
            symbols.append(symbol)

        # Extract preset
        preset_match = re.search(r'preset\s*:\s*["\']([^\'"]+)["\']', code)
        if preset_match:
            preset = preset_match.group(1)
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.preset",
                namespace="root",
                signature=preset,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Jest preset: {preset}",
                language="javascript",
                visibility="public"
            )
            symbols.append(symbol)

        # Extract testMatch patterns
        test_match_pattern = r'testMatch\s*:\s*\[([^\]]+)\]'
        test_match = re.search(test_match_pattern, code)
        if test_match:
            patterns_str = test_match.group(1)
            patterns = re.findall(r'["\']([^\'"]+)["\']', patterns_str)
            for pattern in patterns:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"pattern.testMatch.{pattern}",
                    namespace="testPatterns",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Test match pattern: {pattern}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract testPathIgnorePatterns
        ignore_pattern = r'testPathIgnorePatterns\s*:\s*\[([^\]]+)\]'
        ignore_match = re.search(ignore_pattern, code)
        if ignore_match:
            patterns_str = ignore_match.group(1)
            patterns = re.findall(r'["\']([^\'"]+)["\']', patterns_str)
            for pattern in patterns:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"pattern.ignore.{pattern}",
                    namespace="testPatterns",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Test ignore pattern: {pattern}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract moduleNameMapper (aliases)
        module_map_pattern = r'moduleNameMapper\s*:\s*{([^}]+)}'
        module_map = re.search(module_map_pattern, code)
        if module_map:
            mapper_content = module_map.group(1)
            # Match patterns like "@/*": "<rootDir>/src/*"
            alias_pattern = r'["\']([^\'"]+)["\'](?:\s*:\s*)["\']([^\'"]+)["\']'
            for alias_match in re.finditer(alias_pattern, mapper_content):
                alias = alias_match.group(1)
                target = alias_match.group(2)
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"alias.{alias}",
                    namespace="moduleNameMapper",
                    signature=target,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Module alias: {alias} -> {target}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract coverage configuration
        coverage_threshold_pattern = r'coverageThreshold\s*:\s*{([^}]+)}'
        coverage_match = re.search(coverage_threshold_pattern, code)
        if coverage_match:
            coverage_content = coverage_match.group(1)
            # Extract coverage metrics (lines, functions, branches, statements)
            metrics = re.findall(r'(\w+)\s*:\s*(\d+)', coverage_content)
            for metric, value in metrics:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"coverage.threshold.{metric}",
                    namespace="coverage",
                    signature=value,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Coverage threshold {metric}: {value}%",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract transform patterns
        transform_pattern = r'transform\s*:\s*{([^}]+)}'
        transform_match = re.search(transform_pattern, code)
        if transform_match:
            transform_content = transform_match.group(1)
            # Match patterns like "\\.(js|jsx)$": "babel-jest"
            tf_pattern = r'["\']([^\'"]+)["\'](?:\s*:\s*)["\']([^\'"]+)["\']'
            for tf_match in re.finditer(tf_pattern, transform_content):
                pattern = tf_match.group(1)
                transformer = tf_match.group(2)
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"transform.{pattern}",
                    namespace="transforms",
                    signature=transformer,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Transform {pattern} with {transformer}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract setupFilesAfterEnv
        setup_pattern = r'setupFilesAfterEnv\s*:\s*\[([^\]]+)\]'
        setup_match = re.search(setup_pattern, code)
        if setup_match:
            setup_content = setup_match.group(1)
            setup_files = re.findall(r'["\']([^\'"]+)["\']', setup_content)
            for setup_file in setup_files:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"setupFile.{setup_file}",
                    namespace="setupFiles",
                    signature=setup_file,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Setup file: {setup_file}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        # Extract testTimeout
        timeout_match = re.search(r'testTimeout\s*:\s*(\d+)', code)
        if timeout_match:
            timeout = timeout_match.group(1)
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.testTimeout",
                namespace="root",
                signature=timeout,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Test timeout: {timeout}ms",
                language="javascript",
                visibility="public"
            )
            symbols.append(symbol)

        # Extract collectCoverageFrom
        collect_pattern = r'collectCoverageFrom\s*:\s*\[([^\]]+)\]'
        collect_match = re.search(collect_pattern, code)
        if collect_match:
            collect_content = collect_match.group(1)
            patterns = re.findall(r'["\']([^\'"]+)["\']', collect_content)
            for pattern in patterns:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"coverage.collectFrom.{pattern}",
                    namespace="coverage",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Collect coverage from: {pattern}",
                    language="javascript",
                    visibility="public"
                )
                symbols.append(symbol)

        return symbols

    def _extract_test_patterns(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract test pattern configurations."""
        symbols = []

        # testMatch patterns
        if "testMatch" in data and isinstance(data["testMatch"], list):
            for pattern in data["testMatch"]:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"pattern.testMatch.{pattern}",
                    namespace="testPatterns",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Test match pattern: {pattern}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        # testPathIgnorePatterns
        if "testPathIgnorePatterns" in data and isinstance(data["testPathIgnorePatterns"], list):
            for pattern in data["testPathIgnorePatterns"]:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"pattern.ignore.{pattern}",
                    namespace="testPatterns",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Test ignore pattern: {pattern}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        # testNamePattern
        if "testNamePattern" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="pattern.testNamePattern",
                namespace="testPatterns",
                signature=data["testNamePattern"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Test name pattern: {data['testNamePattern']}",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        return symbols

    def _extract_coverage_config(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract Jest coverage configuration."""
        symbols = []

        # collectCoverageFrom
        if "collectCoverageFrom" in data and isinstance(data["collectCoverageFrom"], list):
            for pattern in data["collectCoverageFrom"]:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"coverage.collectFrom.{pattern}",
                    namespace="coverage",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Collect coverage from: {pattern}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        # coveragePathIgnorePatterns
        if "coveragePathIgnorePatterns" in data and isinstance(data["coveragePathIgnorePatterns"], list):
            for pattern in data["coveragePathIgnorePatterns"]:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"coverage.ignorePattern.{pattern}",
                    namespace="coverage",
                    signature=pattern,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Ignore coverage for: {pattern}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        # coverageThreshold
        if "coverageThreshold" in data and isinstance(data["coverageThreshold"], dict):
            for scope, thresholds in data["coverageThreshold"].items():
                if isinstance(thresholds, dict):
                    for metric, value in thresholds.items():
                        symbol = create_symbol(
                            file_path=file_path,
                            symbol_type=SymbolType.CONSTANT,
                            name=f"coverage.threshold.{scope}.{metric}",
                            namespace="coverage",
                            signature=str(value),
                            line_start=1,
                            line_end=1,
                            code="",
                            docstring=f"Coverage threshold {metric} ({scope}): {value}%",
                            language="json",
                            visibility="public"
                        )
                        symbols.append(symbol)

        return symbols

    def _extract_module_paths(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract module path and alias configurations."""
        symbols = []

        # baseUrl
        if "baseUrl" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="paths.baseUrl",
                namespace="moduleConfig",
                signature=data["baseUrl"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Base URL: {data['baseUrl']}",
                language="json",
                visibility="public"
            )
            symbols.append(symbol)

        # moduleNameMapper
        if "moduleNameMapper" in data and isinstance(data["moduleNameMapper"], dict):
            for alias, target in data["moduleNameMapper"].items():
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"alias.{alias}",
                    namespace="moduleNameMapper",
                    signature=target if isinstance(target, str) else json.dumps(target),
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Module alias: {alias}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        # modulePaths
        if "modulePaths" in data and isinstance(data["modulePaths"], list):
            for path in data["modulePaths"]:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"paths.module.{path}",
                    namespace="moduleConfig",
                    signature=path,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Module path: {path}",
                    language="json",
                    visibility="public"
                )
                symbols.append(symbol)

        return symbols
