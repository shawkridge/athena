"""
Symbol Analysis MCP Tools (Phase 1C)

Exposes symbol analysis functionality via MCP tools for external integration.
Provides tools for parsing, analyzing, and querying symbol data.

Author: Claude Code
Date: 2025-10-31
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from athena.symbols.symbol_models import SymbolType, RelationType
from athena.symbols.symbol_parser import SymbolParser
from athena.symbols.symbol_store import SymbolStore
from athena.symbols.symbol_analyzer import SymbolAnalyzer


class SymbolTools:
    """MCP tool handlers for symbol analysis.

    Provides tools for parsing files, analyzing symbols, and querying
    symbol relationships and metrics.
    """

    def __init__(self, store: Optional[SymbolStore] = None, db_path: str = None):
        """Initialize symbol tools.

        Args:
            store: SymbolStore instance (created if None)
            db_path: Database path (uses in-memory if None)
        """
        if store is None:
            self.store = SymbolStore(db_path)
        else:
            self.store = store

        self.analyzer = SymbolAnalyzer(self.store)
        self.parser = SymbolParser()

    # =========================================================================
    # Tool 1: analyze_symbols
    # =========================================================================

    def analyze_symbols(
        self,
        file_path: str,
        code: Optional[str] = None,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """Analyze a source file and extract symbols.

        Parses a file and extracts all symbols (functions, classes, methods, etc.)
        with full metadata, metrics, and relationships.

        Args:
            file_path: Path to source file
            code: Source code (if None, file is read from disk)
            include_metrics: Whether to compute metrics for each symbol

        Returns:
            Dict with:
            - symbols: List of extracted symbols with metadata
            - total_symbols: Count of symbols found
            - language: Detected language
            - success: Whether parsing succeeded
            - errors: Any parsing errors encountered
        """
        try:
            # Read file if code not provided
            if code is None:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                except FileNotFoundError:
                    return {
                        "status": "error",
                        "error": f"File not found: {file_path}",
                        "symbols": [],
                        "total_symbols": 0
                    }

            # Parse file
            result = self.parser.parse_file(file_path, code)

            if not result.success:
                return {
                    "status": "partial",
                    "symbols": [],
                    "total_symbols": 0,
                    "language": result.language,
                    "errors": result.parse_errors
                }

            # Prepare symbol data
            symbols = []
            for symbol in result.symbols:
                symbol_data = {
                    "name": symbol.name,
                    "full_qualified_name": symbol.full_qualified_name,
                    "type": symbol.symbol_type,
                    "file_path": symbol.file_path,
                    "line_start": symbol.line_start,
                    "line_end": symbol.line_end,
                    "signature": symbol.signature,
                    "docstring": symbol.docstring or "",
                    "visibility": symbol.visibility,
                }

                # Add metrics if requested
                if include_metrics and symbol.metrics:
                    symbol_data["metrics"] = {
                        "lines_of_code": symbol.metrics.lines_of_code,
                        "cyclomatic_complexity": symbol.metrics.cyclomatic_complexity,
                        "cognitive_complexity": symbol.metrics.cognitive_complexity,
                        "maintainability_index": symbol.metrics.maintainability_index,
                        "parameters": symbol.metrics.parameters,
                        "nesting_depth": symbol.metrics.nesting_depth,
                    }

                symbols.append(symbol_data)

            return {
                "status": "success",
                "symbols": symbols,
                "total_symbols": len(symbols),
                "language": result.language,
                "file_path": file_path,
                "total_lines": result.total_lines,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "symbols": [],
                "total_symbols": 0
            }

    # =========================================================================
    # Tool 2: get_symbol_info
    # =========================================================================

    def get_symbol_info(
        self,
        symbol_name: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed information about a symbol.

        Retrieves full metadata, metrics, relationships, and dependencies
        for a specific symbol.

        Args:
            symbol_name: Full qualified name or simple name of symbol
            file_path: Optional file path to narrow search

        Returns:
            Dict with symbol details or error message
        """
        try:
            # Try to get by full qualified name first
            symbol = self.store.get_symbol_by_qname(symbol_name)

            # If not found, search by simple name in file
            if not symbol and file_path:
                symbols = self.store.get_symbols_in_file(file_path)
                for s in symbols:
                    if s.name == symbol_name:
                        symbol = s
                        break

            if not symbol:
                return {
                    "status": "not_found",
                    "error": f"Symbol not found: {symbol_name}"
                }

            # Gather comprehensive info
            analysis = self.analyzer.analyze_symbol(symbol)
            relationships = self.store.get_relationships(symbol.id or 0)
            dependents = self.store.get_dependents(symbol.full_qualified_name)

            return {
                "status": "success",
                "symbol": {
                    "id": symbol.id,
                    "name": symbol.name,
                    "full_qualified_name": symbol.full_qualified_name,
                    "type": symbol.symbol_type,
                    "file_path": symbol.file_path,
                    "line_start": symbol.line_start,
                    "line_end": symbol.line_end,
                    "signature": symbol.signature,
                    "docstring": symbol.docstring or "",
                    "namespace": symbol.namespace or "",
                    "visibility": symbol.visibility,
                },
                "metrics": {
                    "lines_of_code": symbol.metrics.lines_of_code if symbol.metrics else 0,
                    "cyclomatic_complexity": analysis.cyclomatic_complexity,
                    "cognitive_complexity": analysis.cognitive_complexity,
                    "maintainability_index": analysis.maintainability_index,
                    "maintainability_rating": self._rate_maintainability(analysis.maintainability_index),
                },
                "analysis": {
                    "branch_count": analysis.branch_count,
                    "quality_issues": analysis.quality_issues,
                    "is_complex": symbol.is_complex(),
                    "is_large": symbol.is_large(),
                    "is_poorly_maintained": symbol.is_poorly_maintained(),
                },
                "relationships": {
                    "dependencies_count": len(relationships),
                    "dependents_count": len(dependents),
                    "dependencies": [r["to_symbol_name"] for r in relationships],
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    # =========================================================================
    # Tool 3: find_symbol_dependencies
    # =========================================================================

    def find_symbol_dependencies(
        self,
        symbol_name: str,
        relation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Find symbols that a given symbol depends on.

        Returns all symbols that are called, imported, or referenced
        by the given symbol.

        Args:
            symbol_name: Full qualified name of symbol
            relation_type: Optional filter (calls, imports, depends_on, etc.)

        Returns:
            Dict with list of dependencies
        """
        try:
            symbol = self.store.get_symbol_by_qname(symbol_name)

            if not symbol:
                return {
                    "status": "not_found",
                    "error": f"Symbol not found: {symbol_name}",
                    "dependencies": []
                }

            # Get relationships
            relationships = self.store.get_relationships(symbol.id or 0, relation_type)

            dependencies = []
            for rel in relationships:
                dependencies.append({
                    "target": rel["to_symbol_name"],
                    "type": rel["relation_type"],
                    "strength": rel["strength"],
                })

            return {
                "status": "success",
                "symbol": symbol_name,
                "dependencies_count": len(dependencies),
                "dependencies": dependencies,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "dependencies": []
            }

    # =========================================================================
    # Tool 4: find_symbol_dependents
    # =========================================================================

    def find_symbol_dependents(
        self,
        symbol_name: str
    ) -> Dict[str, Any]:
        """Find symbols that depend on a given symbol (reverse lookup).

        Returns all symbols that call, import, or reference
        the given symbol.

        Args:
            symbol_name: Full qualified name of symbol

        Returns:
            Dict with list of dependents
        """
        try:
            # Verify symbol exists
            symbol = self.store.get_symbol_by_qname(symbol_name)
            if not symbol:
                return {
                    "status": "not_found",
                    "error": f"Symbol not found: {symbol_name}",
                    "dependents": []
                }

            # Get dependents (reverse lookup)
            dependent_ids = self.store.get_dependents(symbol_name)

            dependents = []
            for dep_id in dependent_ids:
                dep_symbol = self.store.get_symbol(dep_id)
                if dep_symbol:
                    dependents.append({
                        "name": dep_symbol.name,
                        "full_qualified_name": dep_symbol.full_qualified_name,
                        "type": dep_symbol.symbol_type,
                        "file_path": dep_symbol.file_path,
                    })

            return {
                "status": "success",
                "symbol": symbol_name,
                "dependents_count": len(dependents),
                "dependents": dependents,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "dependents": []
            }

    # =========================================================================
    # Tool 5: suggest_symbol_refactorings
    # =========================================================================

    def suggest_symbol_refactorings(
        self,
        symbol_name: str,
        pattern_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Suggest refactorings for a symbol.

        Provides refactoring suggestions based on complexity metrics,
        code patterns, and quality issues. Integrates with Phase 4
        procedural learning.

        Args:
            symbol_name: Full qualified name of symbol
            pattern_type: Optional pattern type to filter suggestions

        Returns:
            Dict with ranked refactoring suggestions
        """
        try:
            symbol = self.store.get_symbol_by_qname(symbol_name)

            if not symbol:
                return {
                    "status": "not_found",
                    "error": f"Symbol not found: {symbol_name}",
                    "suggestions": []
                }

            # Analyze symbol
            analysis = self.analyzer.analyze_symbol(symbol)

            # Compute parameter count from signature if not in metrics
            param_count = 0
            if symbol.metrics and symbol.metrics.parameters:
                param_count = symbol.metrics.parameters
            else:
                # Count parameters from signature
                if symbol.signature:
                    # Extract parameters from signature like "(a, b, c)"
                    sig = symbol.signature.strip()
                    if sig.startswith("(") and sig.endswith(")"):
                        params_str = sig[1:-1].strip()
                        if params_str:
                            param_count = len([p.strip() for p in params_str.split(",") if p.strip()])

            suggestions = []

            # Suggestion 1: High complexity
            if analysis.cyclomatic_complexity > 10:
                suggestions.append({
                    "priority": "high",
                    "category": "complexity",
                    "title": "Reduce cyclomatic complexity",
                    "description": f"Complexity is {analysis.cyclomatic_complexity}. Consider breaking into smaller functions.",
                    "impact": "maintainability",
                    "effort": "medium"
                })

            # Suggestion 2: Large function
            if symbol.metrics and symbol.metrics.lines_of_code > 100:
                suggestions.append({
                    "priority": "medium",
                    "category": "size",
                    "title": "Extract method",
                    "description": f"Function is {symbol.metrics.lines_of_code} LOC. Consider splitting into smaller functions.",
                    "impact": "maintainability",
                    "effort": "medium"
                })

            # Suggestion 3: Many parameters
            if param_count > 5:
                suggestions.append({
                    "priority": "medium",
                    "category": "parameters",
                    "title": "Reduce parameters",
                    "description": f"Function has {param_count} parameters. Consider using a class or dict.",
                    "impact": "usability",
                    "effort": "small"
                })

            # Suggestion 4: Missing documentation
            if not symbol.docstring or len(symbol.docstring) < 20:
                suggestions.append({
                    "priority": "low",
                    "category": "documentation",
                    "title": "Add docstring",
                    "description": "Add comprehensive docstring explaining purpose, parameters, and return value.",
                    "impact": "maintainability",
                    "effort": "small"
                })

            # Suggestion 5: Deep nesting
            if symbol.metrics and symbol.metrics.nesting_depth > 4:
                suggestions.append({
                    "priority": "medium",
                    "category": "nesting",
                    "title": "Reduce nesting",
                    "description": f"Nesting depth is {symbol.metrics.nesting_depth}. Use early returns or extract functions.",
                    "impact": "readability",
                    "effort": "medium"
                })

            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            suggestions.sort(key=lambda s: priority_order.get(s["priority"], 3))

            return {
                "status": "success",
                "symbol": symbol_name,
                "symbol_type": symbol.symbol_type,
                "suggestions_count": len(suggestions),
                "suggestions": suggestions[:5],  # Top 5 suggestions
                "metrics_summary": {
                    "complexity": analysis.cyclomatic_complexity,
                    "maintainability": analysis.maintainability_index,
                    "quality_issues": len(analysis.quality_issues),
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "suggestions": []
            }

    # =========================================================================
    # Tool 6: get_symbol_quality_report
    # =========================================================================

    def get_symbol_quality_report(self, symbol_name: str) -> Dict[str, Any]:
        """Get comprehensive quality report for a symbol.

        Generates a quality report with metrics, issues, and recommendations
        for improvement.

        Args:
            symbol_name: Full qualified name of symbol

        Returns:
            Dict with detailed quality report
        """
        try:
            symbol = self.store.get_symbol_by_qname(symbol_name)

            if not symbol:
                return {
                    "status": "not_found",
                    "error": f"Symbol not found: {symbol_name}"
                }

            # Full analysis
            analysis = self.analyzer.analyze_symbol(symbol)

            # Quality grade
            grade = self._compute_quality_grade(
                analysis.maintainability_index,
                analysis.cyclomatic_complexity,
                len(analysis.quality_issues)
            )

            return {
                "status": "success",
                "symbol": symbol_name,
                "type": symbol.symbol_type,
                "grade": grade,
                "metrics": {
                    "lines_of_code": symbol.metrics.lines_of_code if symbol.metrics else 0,
                    "cyclomatic_complexity": analysis.cyclomatic_complexity,
                    "cognitive_complexity": analysis.cognitive_complexity,
                    "maintainability_index": round(analysis.maintainability_index, 1),
                    "parameters": symbol.metrics.parameters if symbol.metrics else 0,
                    "nesting_depth": symbol.metrics.nesting_depth if symbol.metrics else 0,
                },
                "issues": {
                    "count": len(analysis.quality_issues),
                    "issues": analysis.quality_issues
                },
                "coverage": {
                    "has_docstring": bool(symbol.docstring and len(symbol.docstring) > 10),
                    "visibility": symbol.visibility,
                    "is_public": symbol.visibility == "public",
                },
                "recommendations": self._generate_recommendations(analysis, symbol),
                "summary": self._generate_summary(analysis, symbol)
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _rate_maintainability(self, index: float) -> str:
        """Rate maintainability on A-F scale."""
        if index >= 85:
            return "A"
        elif index >= 70:
            return "B"
        elif index >= 55:
            return "C"
        elif index >= 40:
            return "D"
        elif index >= 20:
            return "E"
        else:
            return "F"

    def _compute_quality_grade(
        self,
        maintainability: float,
        complexity: int,
        issue_count: int
    ) -> str:
        """Compute overall quality grade (A-F)."""
        score = 100.0
        score -= maintainability * 0.4  # Maintainability weight
        score -= min(complexity * 5, 40)  # Complexity weight (capped)
        score -= min(issue_count * 5, 20)  # Issues weight (capped)

        if score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self, analysis, symbol) -> List[str]:
        """Generate actionable recommendations."""
        recs = []

        if analysis.cyclomatic_complexity > 10:
            recs.append("Refactor to reduce cyclomatic complexity")
        if symbol.is_large():
            recs.append("Consider breaking into smaller functions")
        if symbol.is_poorly_maintained():
            recs.append("Improve code clarity and add documentation")
        if analysis.cognitive_complexity > 20:
            recs.append("Simplify logic and reduce nesting")

        return recs

    def _generate_summary(self, analysis, symbol) -> str:
        """Generate human-readable quality summary."""
        if symbol.is_complex() and symbol.is_large():
            return "Symbol is large and complex. High refactoring priority."
        elif symbol.is_complex():
            return "Symbol has high complexity. Consider simplification."
        elif symbol.is_large():
            return "Symbol is large. Consider breaking into smaller parts."
        elif analysis.maintainability_index < 50:
            return "Maintainability is poor. Add documentation and simplify."
        else:
            return "Symbol quality is acceptable."
