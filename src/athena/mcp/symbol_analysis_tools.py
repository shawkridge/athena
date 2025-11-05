"""MCP tools for symbol analysis operations.

Exposes symbol analysis functionality via MCP:
- Parse and analyze source files for symbols
- Retrieve detailed symbol information and metrics
- Find symbol dependencies and dependents
- Generate refactoring suggestions based on complexity and patterns
- Generate comprehensive quality reports for symbols
"""

import json
from typing import Any
from mcp.types import Tool

from ..symbols.symbol_tools import SymbolTools
from ..symbols.symbol_store import SymbolStore


def get_symbol_analysis_tools() -> list[Tool]:
    """Get symbol analysis operation tools."""
    return [
        Tool(
            name="analyze_symbols",
            description="Analyze a source file and extract symbols",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to source file",
                    },
                    "code": {
                        "type": "string",
                        "description": "Source code (if None, file is read from disk)",
                    },
                    "include_metrics": {
                        "type": "boolean",
                        "description": "Whether to compute metrics for each symbol",
                        "default": True,
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_symbol_info",
            description="Retrieve detailed information about a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Full qualified name of symbol",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path filter",
                    },
                },
                "required": ["symbol_name"],
            },
        ),
        Tool(
            name="find_symbol_dependencies",
            description="Find symbols that a given symbol depends on",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Full qualified name of symbol",
                    },
                    "relation_type": {
                        "type": "string",
                        "description": "Optional filter (calls, imports, depends_on, etc.)",
                    },
                },
                "required": ["symbol_name"],
            },
        ),
        Tool(
            name="find_symbol_dependents",
            description="Find symbols that depend on a given symbol (reverse lookup)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Full qualified name of symbol",
                    },
                },
                "required": ["symbol_name"],
            },
        ),
        Tool(
            name="suggest_symbol_refactorings",
            description="Suggest refactorings for a symbol based on complexity metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Full qualified name of symbol",
                    },
                    "pattern_type": {
                        "type": "string",
                        "description": "Optional pattern type to filter suggestions",
                    },
                },
                "required": ["symbol_name"],
            },
        ),
        Tool(
            name="get_symbol_quality_report",
            description="Get comprehensive quality report for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Full qualified name of symbol",
                    },
                },
                "required": ["symbol_name"],
            },
        ),
    ]


class SymbolAnalysisMCPHandlers:
    """MCP handlers for symbol analysis operations."""

    def __init__(self, db_path: str = None):
        """Initialize symbol analysis handlers.

        Args:
            db_path: Database path for symbol store
        """
        self.store = SymbolStore(db_path)
        self.tools = SymbolTools(store=self.store)

    async def analyze_symbols(self, arguments: dict[str, Any]) -> str:
        """Handle analyze_symbols tool."""
        try:
            file_path = arguments["file_path"]
            code = arguments.get("code")
            include_metrics = arguments.get("include_metrics", True)

            result = self.tools.analyze_symbols(
                file_path=file_path,
                code=code,
                include_metrics=include_metrics
            )

            # Format output
            summary = f"📊 Symbol Analysis: {file_path}\n\n"
            summary += f"Status: {result.get('status', 'unknown')}\n"
            summary += f"Language: {result.get('language', 'unknown')}\n"
            summary += f"Total Symbols: {result.get('total_symbols', 0)}\n"

            if result.get("symbols"):
                summary += f"\n📝 Symbols Found:\n"
                for sym in result["symbols"][:10]:  # Top 10
                    summary += f"  - {sym['name']} ({sym['type']})\n"
                if len(result["symbols"]) > 10:
                    summary += f"  ... and {len(result['symbols']) - 10} more\n"

            if result.get("errors"):
                summary += f"\n⚠️ Errors: {', '.join(result['errors'])}\n"

            return summary
        except Exception as e:
            return f"✗ Error analyzing symbols: {str(e)}"

    async def get_symbol_info(self, arguments: dict[str, Any]) -> str:
        """Handle get_symbol_info tool."""
        try:
            symbol_name = arguments["symbol_name"]

            result = self.tools.get_symbol_info(symbol_name)

            if result.get("status") != "success":
                return f"✗ {result.get('error', 'Symbol not found')}"

            # Format output
            summary = f"ℹ️ Symbol Information: {symbol_name}\n\n"
            summary += f"Type: {result.get('symbol_type')}\n"
            summary += f"File: {result.get('file_path')}\n"
            summary += f"Lines: {result.get('line_range', '')}\n"

            if result.get("metrics"):
                metrics = result["metrics"]
                summary += f"\n📈 Metrics:\n"
                summary += f"  - LOC: {metrics.get('lines_of_code', 0)}\n"
                summary += f"  - Cyclomatic Complexity: {metrics.get('cyclomatic_complexity', 0)}\n"
                summary += f"  - Cognitive Complexity: {metrics.get('cognitive_complexity', 0)}\n"
                summary += f"  - Maintainability Index: {metrics.get('maintainability_index', 0):.1f}\n"

            if result.get("relationships"):
                rels = result["relationships"]
                summary += f"\n🔗 Relationships:\n"
                summary += f"  - Dependencies: {rels.get('dependencies_count', 0)}\n"
                summary += f"  - Dependents: {rels.get('dependents_count', 0)}\n"

            return summary
        except Exception as e:
            return f"✗ Error getting symbol info: {str(e)}"

    async def find_symbol_dependencies(self, arguments: dict[str, Any]) -> str:
        """Handle find_symbol_dependencies tool."""
        try:
            symbol_name = arguments["symbol_name"]
            relation_type = arguments.get("relation_type")

            result = self.tools.find_symbol_dependencies(symbol_name, relation_type)

            if result.get("status") != "success":
                return f"✗ {result.get('error', 'Symbol not found')}"

            # Format output
            summary = f"🔍 Dependencies of {symbol_name}\n\n"
            summary += f"Count: {result.get('dependencies_count', 0)}\n"

            if result.get("dependencies"):
                summary += f"\n📋 Dependencies:\n"
                for dep in result["dependencies"][:10]:
                    summary += f"  - {dep['target']} ({dep['type']})\n"
                if len(result["dependencies"]) > 10:
                    summary += f"  ... and {len(result['dependencies']) - 10} more\n"

            return summary
        except Exception as e:
            return f"✗ Error finding dependencies: {str(e)}"

    async def find_symbol_dependents(self, arguments: dict[str, Any]) -> str:
        """Handle find_symbol_dependents tool."""
        try:
            symbol_name = arguments["symbol_name"]

            result = self.tools.find_symbol_dependents(symbol_name)

            if result.get("status") != "success":
                return f"✗ {result.get('error', 'Symbol not found')}"

            # Format output
            summary = f"🔍 Dependents of {symbol_name}\n\n"
            summary += f"Count: {result.get('dependents_count', 0)}\n"

            if result.get("dependents"):
                summary += f"\n📋 Dependent Symbols:\n"
                for dep in result["dependents"][:10]:
                    summary += f"  - {dep['full_qualified_name']} ({dep['type']})\n"
                if len(result["dependents"]) > 10:
                    summary += f"  ... and {len(result['dependents']) - 10} more\n"

            return summary
        except Exception as e:
            return f"✗ Error finding dependents: {str(e)}"

    async def suggest_symbol_refactorings(self, arguments: dict[str, Any]) -> str:
        """Handle suggest_symbol_refactorings tool."""
        try:
            symbol_name = arguments["symbol_name"]
            pattern_type = arguments.get("pattern_type")

            result = self.tools.suggest_symbol_refactorings(symbol_name, pattern_type)

            if result.get("status") != "success":
                return f"✗ {result.get('error', 'Symbol not found')}"

            # Format output
            summary = f"💡 Refactoring Suggestions for {symbol_name}\n\n"
            summary += f"Count: {result.get('suggestions_count', 0)}\n"

            if result.get("metrics_summary"):
                metrics = result["metrics_summary"]
                summary += f"\n📈 Current Metrics:\n"
                summary += f"  - Complexity: {metrics.get('complexity', 0)}\n"
                summary += f"  - Maintainability Index: {metrics.get('maintainability', 0):.1f}\n"
                summary += f"  - Quality Issues: {metrics.get('quality_issues', 0)}\n"

            if result.get("suggestions"):
                summary += f"\n💭 Suggestions:\n"
                for sug in result["suggestions"][:5]:
                    priority = sug.get("priority", "medium").upper()
                    summary += f"  [{priority}] {sug.get('title', 'Unknown')}\n"
                    summary += f"    → {sug.get('description', '')}\n"

            return summary
        except Exception as e:
            return f"✗ Error generating suggestions: {str(e)}"

    async def get_symbol_quality_report(self, arguments: dict[str, Any]) -> str:
        """Handle get_symbol_quality_report tool."""
        try:
            symbol_name = arguments["symbol_name"]

            result = self.tools.get_symbol_quality_report(symbol_name)

            if result.get("status") != "success":
                return f"✗ {result.get('error', 'Symbol not found')}"

            # Format output
            summary = f"🎯 Quality Report for {symbol_name}\n\n"

            # Grade
            grade = result.get("grade", "N/A")
            summary += f"Grade: {grade}\n"

            # Metrics
            if result.get("metrics"):
                metrics = result["metrics"]
                summary += f"\n📊 Metrics:\n"
                summary += f"  - LOC: {metrics.get('lines_of_code', 0)}\n"
                summary += f"  - Complexity: {metrics.get('cyclomatic_complexity', 0)}\n"
                summary += f"  - Maintainability Index: {metrics.get('maintainability_index', 0):.1f}\n"

            # Issues
            if result.get("issues"):
                issues = result["issues"]
                summary += f"\n⚠️ Issues Found: {len(issues)}\n"
                for issue in issues[:5]:
                    summary += f"  - {issue}\n"
                if len(issues) > 5:
                    summary += f"  ... and {len(issues) - 5} more\n"

            # Coverage
            if result.get("coverage"):
                cov = result["coverage"]
                summary += f"\n📋 Coverage:\n"
                summary += f"  - Has docstring: {cov.get('has_docstring', False)}\n"
                summary += f"  - Has type hints: {cov.get('has_type_hints', False)}\n"

            # Recommendations
            if result.get("recommendations"):
                recs = result["recommendations"]
                summary += f"\n💡 Recommendations:\n"
                for rec in recs[:3]:
                    summary += f"  - {rec}\n"

            return summary
        except Exception as e:
            return f"✗ Error generating quality report: {str(e)}"
