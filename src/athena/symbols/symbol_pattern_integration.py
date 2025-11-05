"""
Symbol-to-Pattern Integration (Phase 1C - Phase 4 Bridge)

Bridges symbol analysis (Phase 1) with procedural learning patterns (Phase 4).
Enables pattern-specific refactoring suggestions and effectiveness measurement.

Author: Claude Code
Date: 2025-10-31
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from athena.symbols.symbol_models import Symbol, SymbolType
from athena.symbols.symbol_store import SymbolStore
from athena.symbols.symbol_analyzer import SymbolAnalyzer


@dataclass
class PatternApplication:
    """Record of a pattern applied to a symbol."""
    symbol_id: int
    symbol_name: str
    pattern_name: str
    pattern_type: str
    match_score: float
    suggestion: str
    applied: bool = False
    effectiveness_rating: Optional[float] = None


class SymbolPatternLinker:
    """Links symbols to patterns from Phase 4.

    Provides:
    - Pattern matching against symbols
    - Symbol-specific refactoring suggestions
    - Pattern effectiveness measurement per symbol
    - Integration with procedural learning system
    """

    def __init__(self, store: SymbolStore, analyzer: SymbolAnalyzer):
        """Initialize pattern linker.

        Args:
            store: SymbolStore for data access
            analyzer: SymbolAnalyzer for metrics
        """
        self.store = store
        self.analyzer = analyzer

    def link_patterns_to_symbols(
        self,
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, List[PatternApplication]]:
        """Link Phase 4 patterns to all symbols in store.

        Matches available patterns against each symbol and scores relevance.

        Args:
            patterns: List of pattern dicts from Phase 4 with:
            - name: Pattern name
            - type: Pattern type (e.g., 'refactoring', 'architecture')
            - applicability_rules: How to detect if pattern applies

        Returns:
            Dict mapping symbol names to list of applicable patterns
        """
        all_symbols = self.store.get_all_symbols()
        linked = {}

        for symbol in all_symbols:
            matched_patterns = []

            for pattern in patterns:
                score = self._compute_pattern_match_score(symbol, pattern)

                if score > 0.3:  # Threshold for inclusion
                    matched_patterns.append(
                        PatternApplication(
                            symbol_id=symbol.id or 0,
                            symbol_name=symbol.full_qualified_name,
                            pattern_name=pattern.get("name", "unknown"),
                            pattern_type=pattern.get("type", "general"),
                            match_score=score,
                            suggestion=self._generate_pattern_suggestion(symbol, pattern),
                        )
                    )

            if matched_patterns:
                # Sort by match score (highest first)
                matched_patterns.sort(key=lambda p: p.match_score, reverse=True)
                linked[symbol.full_qualified_name] = matched_patterns

        return linked

    def suggest_refactorings_for_symbol(
        self,
        symbol: Symbol,
        patterns: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Generate refactoring suggestions for a symbol based on patterns.

        Provides ranked refactoring suggestions tailored to this symbol's
        characteristics and applicable patterns.

        Args:
            symbol: Symbol to suggest refactorings for
            patterns: Patterns from Phase 4 (if None, uses default heuristics)

        Returns:
            List of refactoring suggestions with scoring
        """
        suggestions = []

        # Get analysis
        analysis = self.analyzer.analyze_symbol(symbol)

        # Compute parameter count from signature if not in metrics
        param_count = 0
        if symbol.metrics and symbol.metrics.parameters:
            param_count = symbol.metrics.parameters
        else:
            # Count parameters from signature
            if symbol.signature:
                sig = symbol.signature.strip()
                if sig.startswith("(") and sig.endswith(")"):
                    params_str = sig[1:-1].strip()
                    if params_str:
                        param_count = len([p.strip() for p in params_str.split(",") if p.strip()])

        # Pattern-based suggestions
        if patterns:
            for pattern in patterns:
                score = self._compute_pattern_match_score(symbol, pattern)
                if score > 0.3:
                    suggestion = {
                        "type": "pattern",
                        "pattern": pattern.get("name", "unknown"),
                        "title": pattern.get("title", "Apply pattern"),
                        "description": self._generate_pattern_suggestion(symbol, pattern),
                        "score": round(score, 2),
                        "applicability": self._explain_applicability(symbol, pattern),
                    }
                    suggestions.append(suggestion)

        # Heuristic-based suggestions
        if analysis.cyclomatic_complexity > 8:  # Lowered from 15
            suggestions.append({
                "type": "heuristic",
                "category": "complexity_reduction",
                "title": "Extract methods",
                "description": "High cyclomatic complexity detected. Split function into smaller units.",
                "score": min(1.0, analysis.cyclomatic_complexity / 20),
                "priority": "high",
            })

        if symbol.metrics and symbol.metrics.lines_of_code > 75:  # Lowered from 150
            suggestions.append({
                "type": "heuristic",
                "category": "size_reduction",
                "title": "Break into smaller functions",
                "description": f"Function is {symbol.metrics.lines_of_code} LOC. Extract related logic.",
                "score": min(1.0, symbol.metrics.lines_of_code / 300),
                "priority": "medium",
            })

        if param_count > 4:  # Lowered from 6
            suggestions.append({
                "type": "heuristic",
                "category": "parameter_reduction",
                "title": "Use parameter object",
                "description": f"Function has {param_count} parameters. Group into a class.",
                "score": min(1.0, param_count / 10),
                "priority": "medium",
            })

        # Sort by score (highest first)
        suggestions.sort(key=lambda s: s.get("score", 0), reverse=True)

        return suggestions

    def measure_pattern_effectiveness_by_symbol(
        self,
        pattern_name: str
    ) -> Dict[str, Any]:
        """Measure which symbols benefit most from a pattern.

        Identifies symbols where a specific pattern would be most effective,
        enabling targeted learning and improvement.

        Args:
            pattern_name: Name of pattern from Phase 4

        Returns:
            Dict with effectiveness analysis per symbol type and category
        """
        all_symbols = self.store.get_all_symbols()
        effectiveness_scores = {}

        for symbol in all_symbols:
            if not symbol.id:
                continue

            score = self._compute_symbol_pattern_effectiveness(symbol, pattern_name)

            if score > 0:
                effectiveness_scores[symbol.full_qualified_name] = {
                    "symbol_type": symbol.symbol_type,
                    "file_path": symbol.file_path,
                    "effectiveness_score": round(score, 3),
                    "would_improve": self._what_would_improve(symbol, pattern_name),
                }

        # Compute statistics
        if effectiveness_scores:
            scores = [s["effectiveness_score"] for s in effectiveness_scores.values()]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            candidates = len([s for s in scores if s > 0.7])
        else:
            avg_score = 0
            max_score = 0
            candidates = 0

        return {
            "pattern": pattern_name,
            "total_symbols_analyzed": len(all_symbols),
            "symbols_affected": len(effectiveness_scores),
            "avg_effectiveness": round(avg_score, 3),
            "max_effectiveness": round(max_score, 3),
            "high_value_candidates": candidates,
            "top_symbols": sorted(
                effectiveness_scores.items(),
                key=lambda x: x[1]["effectiveness_score"],
                reverse=True
            )[:5],
            "symbol_distribution": self._analyze_symbol_distribution(
                effectiveness_scores
            ),
        }

    def compute_pattern_applicability_matrix(
        self,
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """Compute applicability matrix: patterns vs symbol types.

        Useful for understanding which patterns apply to which symbol types
        (functions, classes, methods, etc.)

        Args:
            patterns: Patterns from Phase 4

        Returns:
            Matrix of pattern_name -> {symbol_type: applicability_score}
        """
        matrix = {}
        all_symbols = self.store.get_all_symbols()

        for pattern in patterns:
            pattern_name = pattern.get("name", "unknown")
            scores_by_type = {}

            # For each symbol type, compute average applicability
            type_groups = {}
            for symbol in all_symbols:
                sym_type = symbol.symbol_type
                if sym_type not in type_groups:
                    type_groups[sym_type] = []

                score = self._compute_pattern_match_score(symbol, pattern)
                type_groups[sym_type].append(score)

            # Compute averages per type
            for sym_type, scores in type_groups.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    scores_by_type[sym_type] = round(avg_score, 3)

            if scores_by_type:
                matrix[pattern_name] = scores_by_type

        return matrix

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _compute_pattern_match_score(
        self,
        symbol: Symbol,
        pattern: Dict[str, Any]
    ) -> float:
        """Compute how well a pattern matches a symbol (0.0-1.0)."""
        score = 0.0

        # Check pattern type applicability
        pattern_type = pattern.get("type", "general")
        applicable_types = pattern.get("applicable_to", [])

        if applicable_types and symbol.symbol_type not in applicable_types:
            return 0.0

        # Base score from pattern applicability rules
        base_score = pattern.get("base_applicability", 0.5)
        score += base_score * 0.4  # Increased from 0.3 to 0.4

        # Complexity-based applicability
        analysis = self.analyzer.analyze_symbol(symbol)

        # More lenient thresholds for complexity triggers
        if "high_complexity" in pattern.get("triggers", []):
            if analysis.cyclomatic_complexity > 5:  # Lowered from 10
                score += 0.25  # Increased from 0.2

        if "large_function" in pattern.get("triggers", []):
            if symbol.metrics and symbol.metrics.lines_of_code > 50:  # Lowered from 100
                score += 0.25  # Increased from 0.2

        if "many_parameters" in pattern.get("triggers", []):
            if symbol.metrics and symbol.metrics.parameters > 3:  # Lowered from 4
                score += 0.2  # Increased from 0.15

        if "missing_docs" in pattern.get("triggers", []):
            if not symbol.docstring or len(symbol.docstring) < 20:
                score += 0.15  # Increased from 0.1

        # Symbol type bonus
        if pattern_type == "refactoring":
            if symbol.symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD):
                score += 0.15  # Increased from 0.1

        return min(1.0, score)

    def _compute_symbol_pattern_effectiveness(
        self,
        symbol: Symbol,
        pattern_name: str
    ) -> float:
        """Compute effectiveness score: how much would this pattern help?"""
        score = 0.0

        # Get current metrics
        analysis = self.analyzer.analyze_symbol(symbol)

        # Patterns that reduce complexity
        if "complexity" in pattern_name.lower():
            if analysis.cyclomatic_complexity > 10:
                score = min(1.0, (analysis.cyclomatic_complexity - 10) / 20)

        # Patterns that reduce size
        if "extract" in pattern_name.lower() or "split" in pattern_name.lower():
            if symbol.metrics and symbol.metrics.lines_of_code > 100:
                score = min(1.0, (symbol.metrics.lines_of_code - 100) / 200)

        # Patterns for parameters
        if "parameter" in pattern_name.lower() or "object" in pattern_name.lower():
            if symbol.metrics and symbol.metrics.parameters > 4:
                score = min(1.0, (symbol.metrics.parameters - 4) / 6)

        # Patterns for documentation
        if "doc" in pattern_name.lower() or "document" in pattern_name.lower():
            if not symbol.docstring or len(symbol.docstring) < 20:
                score = 0.7

        return score

    def _generate_pattern_suggestion(
        self,
        symbol: Symbol,
        pattern: Dict[str, Any]
    ) -> str:
        """Generate natural language suggestion for applying a pattern."""
        pattern_name = pattern.get("name", "unknown")
        pattern_description = pattern.get("description", "")

        if symbol.symbol_type == SymbolType.METHOD:
            return f"Apply '{pattern_name}' to this method. {pattern_description}"
        elif symbol.symbol_type == SymbolType.FUNCTION:
            return f"This function would benefit from '{pattern_name}'. {pattern_description}"
        elif symbol.symbol_type == SymbolType.CLASS:
            return f"Consider applying '{pattern_name}' to this class structure. {pattern_description}"
        else:
            return f"This symbol could use '{pattern_name}'. {pattern_description}"

    def _explain_applicability(
        self,
        symbol: Symbol,
        pattern: Dict[str, Any]
    ) -> str:
        """Explain why a pattern applies to this symbol."""
        analysis = self.analyzer.analyze_symbol(symbol)
        reasons = []

        if analysis.cyclomatic_complexity > 10:
            reasons.append(f"High complexity ({analysis.cyclomatic_complexity})")

        if symbol.metrics and symbol.metrics.lines_of_code > 100:
            reasons.append(f"Large size ({symbol.metrics.lines_of_code} LOC)")

        if symbol.metrics and symbol.metrics.parameters > 4:
            reasons.append(f"Many parameters ({symbol.metrics.parameters})")

        if not symbol.docstring:
            reasons.append("Lacks documentation")

        if reasons:
            return ", ".join(reasons) + " - this pattern addresses these issues"
        else:
            return "Pattern matches symbol characteristics"

    def _what_would_improve(
        self,
        symbol: Symbol,
        pattern_name: str
    ) -> List[str]:
        """List what would improve if pattern is applied."""
        improvements = []

        if "complexity" in pattern_name.lower():
            improvements.append("Reduce code complexity")
            improvements.append("Easier to test")

        if "extract" in pattern_name.lower():
            improvements.append("Reduce function size")
            improvements.append("Better separation of concerns")

        if "parameter" in pattern_name.lower():
            improvements.append("Simpler function signature")
            improvements.append("Easier to add parameters later")

        if "doc" in pattern_name.lower():
            improvements.append("Better documentation")
            improvements.append("Easier maintenance")

        return improvements or ["Improve code quality"]

    def _analyze_symbol_distribution(
        self,
        effectiveness_scores: Dict[str, Dict]
    ) -> Dict[str, int]:
        """Analyze distribution of symbol types with high effectiveness."""
        distribution = {}

        for data in effectiveness_scores.values():
            sym_type = data.get("symbol_type", "unknown")
            if sym_type not in distribution:
                distribution[sym_type] = 0
            distribution[sym_type] += 1

        return distribution
