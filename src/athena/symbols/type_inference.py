"""Type Inference Engine for inferring function parameter and return types.

Provides:
- Parameter type inference from usage
- Return type inference from assignments
- Type annotation suggestions
- Type confidence scoring
- Cross-language type inference
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from .symbol_models import Symbol, SymbolType


class TypeCategory(str, Enum):
    """Categories of inferred types."""

    PRIMITIVE = "primitive"  # int, str, bool, float
    COLLECTION = "collection"  # list, dict, set, tuple
    OBJECT = "object"  # class instances
    FUNCTION = "function"  # callable
    UNION = "union"  # multiple possible types
    UNKNOWN = "unknown"


@dataclass
class TypeHint:
    """A type hint suggestion."""

    symbol: Symbol
    parameter_name: Optional[str]  # None for return type
    inferred_type: str
    confidence: float  # 0.0 - 1.0
    evidence_count: int
    type_category: TypeCategory
    alternative_types: List[str] = None

    def __post_init__(self):
        if self.alternative_types is None:
            self.alternative_types = []


@dataclass
class TypeAnnotationSuggestion:
    """A suggestion for type annotation."""

    symbol: Symbol
    parameter_suggestions: Dict[str, TypeHint]
    return_type_suggestion: Optional[TypeHint]
    confidence_score: float  # Average confidence


class TypeInferenceAnalyzer:
    """Analyzes code to infer types from usage patterns."""

    def __init__(self):
        """Initialize the type inference analyzer."""
        self.type_hints: Dict[str, List[TypeHint]] = {}
        self.inferred_types: Dict[str, TypeAnnotationSuggestion] = {}

    def infer_parameter_types(self, symbol: Symbol, code: str) -> Dict[str, TypeHint]:
        """Infer parameter types from function usage.

        Args:
            symbol: Function/method symbol
            code: Source code content

        Returns:
            Dictionary mapping parameter names to TypeHint
        """
        parameter_types: Dict[str, TypeHint] = {}

        # Parse function signature
        params = self._extract_parameters(symbol)

        for param_name in params:
            inferred = self._analyze_parameter_usage(symbol, code, param_name)
            if inferred:
                parameter_types[param_name] = inferred

        return parameter_types

    def infer_return_type(self, symbol: Symbol, code: str) -> Optional[TypeHint]:
        """Infer return type from function implementation.

        Args:
            symbol: Function/method symbol
            code: Source code content

        Returns:
            TypeHint for return type, or None
        """
        if symbol.symbol_type not in [
            SymbolType.FUNCTION,
            SymbolType.METHOD,
            SymbolType.ASYNC_FUNCTION,
        ]:
            return None

        # Extract return statements
        return_types = self._analyze_return_statements(code)

        if not return_types:
            return None

        # Find most common return type
        type_counts: Dict[str, int] = {}
        for ret_type in return_types:
            type_counts[ret_type] = type_counts.get(ret_type, 0) + 1

        most_common_type = max(type_counts, key=type_counts.get)
        confidence = type_counts[most_common_type] / len(return_types)

        alternative_types = [t for t in type_counts.keys() if t != most_common_type]

        return TypeHint(
            symbol=symbol,
            parameter_name=None,
            inferred_type=most_common_type,
            confidence=confidence,
            evidence_count=len(return_types),
            type_category=self._categorize_type(most_common_type),
            alternative_types=alternative_types,
        )

    def _extract_parameters(self, symbol: Symbol) -> List[str]:
        """Extract parameter names from function signature."""
        if not symbol.signature:
            return []

        # Parse signature: "param1, param2: int, param3=default"
        sig = symbol.signature.strip("()")
        if not sig:
            return []

        params = []
        for param in sig.split(","):
            param = param.strip()
            # Remove type annotations and defaults
            param_name = param.split(":")[0].split("=")[0].strip()
            if param_name and param_name != "self":
                params.append(param_name)

        return params

    def _analyze_parameter_usage(
        self, symbol: Symbol, code: str, param_name: str
    ) -> Optional[TypeHint]:
        """Analyze how a parameter is used to infer its type."""
        inferred_types: Dict[str, int] = {}

        lines = code.split("\n")
        for line in lines:
            # Look for parameter usage
            if param_name not in line:
                continue

            # Detect type from method calls
            if f"{param_name}." in line:
                methods = self._extract_method_calls(line, param_name)
                for method in methods:
                    inferred_type = self._infer_type_from_method(method)
                    inferred_types[inferred_type] = inferred_types.get(inferred_type, 0) + 1

            # Detect type from indexing
            if f"{param_name}[" in line:
                inferred_types["indexable"] = inferred_types.get("indexable", 0) + 1

            # Detect type from iteration
            if "for " in line and f" in {param_name}" in line:
                inferred_types["iterable"] = inferred_types.get("iterable", 0) + 1

            # Detect type from numeric operations
            if any(op in line and param_name in line.split(op)[0] for op in ["+", "-", "*", "/"]):
                inferred_types["numeric"] = inferred_types.get("numeric", 0) + 1

        if not inferred_types:
            return None

        most_common_type = max(inferred_types, key=inferred_types.get)
        total_uses = sum(inferred_types.values())
        confidence = inferred_types[most_common_type] / total_uses

        alternative_types = [t for t in inferred_types.keys() if t != most_common_type]

        return TypeHint(
            symbol=symbol,
            parameter_name=param_name,
            inferred_type=most_common_type,
            confidence=confidence,
            evidence_count=total_uses,
            type_category=self._categorize_type(most_common_type),
            alternative_types=alternative_types,
        )

    def _analyze_return_statements(self, code: str) -> List[str]:
        """Extract return value types from code."""
        return_types = []
        lines = code.split("\n")

        for line in lines:
            if "return" not in line:
                continue

            line = line.strip()
            if not line.startswith("return"):
                continue

            # Extract what's being returned
            return_value = line[6:].strip()

            # Infer type from return value
            inferred_type = self._infer_type_from_value(return_value)
            if inferred_type:
                return_types.append(inferred_type)

        return return_types

    def _extract_method_calls(self, line: str, param_name: str) -> List[str]:
        """Extract method names called on a parameter."""
        methods = []
        pattern = f"{param_name}."

        if pattern not in line:
            return methods

        start = line.find(pattern) + len(pattern)
        # Find method name (until '(' or whitespace)
        end = start
        while end < len(line) and line[end] not in ("(", " ", "\n"):
            end += 1

        if end > start:
            method = line[start:end]
            methods.append(method)

        return methods

    def _infer_type_from_method(self, method: str) -> str:
        """Infer type from method name."""
        # Common string methods
        if method in ["upper", "lower", "strip", "split", "replace", "format"]:
            return "str"

        # Common list methods
        if method in ["append", "pop", "extend", "remove", "insert", "sort"]:
            return "list"

        # Common dict methods
        if method in ["keys", "values", "items", "get", "update", "pop"]:
            return "dict"

        # Common set methods
        if method in ["add", "remove", "union", "intersection", "difference"]:
            return "set"

        # Default
        return "object"

    def _infer_type_from_value(self, value: str) -> Optional[str]:
        """Infer type from a return value."""
        value = value.strip()

        # Literals
        if value.startswith('"') or value.startswith("'"):
            return "str"
        if value.startswith("["):
            return "list"
        if value.startswith("{"):
            return "dict"
        if value.startswith("("):
            return "tuple"
        if value in ["True", "False"]:
            return "bool"
        if value == "None":
            return "None"

        # Numeric
        try:
            if "." in value:
                float(value)
                return "float"
            else:
                int(value)
                return "int"
        except ValueError:
            pass

        # Variable/expression - could be anything
        return "object"

    def _categorize_type(self, type_str: str) -> TypeCategory:
        """Categorize a type string."""
        type_str = type_str.lower()

        if type_str in ["int", "float", "str", "bool", "bytes", "none"]:
            return TypeCategory.PRIMITIVE
        elif type_str in ["list", "dict", "set", "tuple"]:
            return TypeCategory.COLLECTION
        elif type_str == "callable":
            return TypeCategory.FUNCTION
        elif type_str == "union":
            return TypeCategory.UNION
        elif type_str in ["indexable", "iterable", "numeric"]:
            return TypeCategory.PRIMITIVE
        else:
            return TypeCategory.OBJECT

    def analyze_symbol(self, symbol: Symbol, code: str) -> TypeAnnotationSuggestion:
        """Analyze a symbol and suggest type annotations.

        Args:
            symbol: Symbol to analyze
            code: Source code content

        Returns:
            TypeAnnotationSuggestion with parameter and return type hints
        """
        parameter_suggestions = {}
        return_type_suggestion = None

        if symbol.symbol_type in [
            SymbolType.FUNCTION,
            SymbolType.METHOD,
            SymbolType.ASYNC_FUNCTION,
        ]:
            # Infer parameter types
            param_types = self.infer_parameter_types(symbol, code)
            parameter_suggestions = param_types

            # Infer return type
            return_type_suggestion = self.infer_return_type(symbol, code)

        # Calculate average confidence
        all_hints = list(parameter_suggestions.values())
        if return_type_suggestion:
            all_hints.append(return_type_suggestion)

        avg_confidence = sum(h.confidence for h in all_hints) / len(all_hints) if all_hints else 0.0

        suggestion = TypeAnnotationSuggestion(
            symbol=symbol,
            parameter_suggestions=parameter_suggestions,
            return_type_suggestion=return_type_suggestion,
            confidence_score=avg_confidence,
        )

        self.inferred_types[symbol.full_qualified_name or symbol.name] = suggestion
        return suggestion

    def get_high_confidence_suggestions(
        self, threshold: float = 0.7
    ) -> List[TypeAnnotationSuggestion]:
        """Get type suggestions with high confidence.

        Args:
            threshold: Minimum confidence score (0.0 - 1.0)

        Returns:
            List of suggestions above threshold
        """
        return [
            suggestion
            for suggestion in self.inferred_types.values()
            if suggestion.confidence_score >= threshold
        ]

    def get_type_hints_for_symbol(self, symbol: Symbol) -> Optional[TypeAnnotationSuggestion]:
        """Get type hints for a specific symbol.

        Args:
            symbol: Symbol to get hints for

        Returns:
            TypeAnnotationSuggestion or None
        """
        key = symbol.full_qualified_name or symbol.name
        return self.inferred_types.get(key)

    def get_type_inference_report(self) -> str:
        """Generate a type inference report.

        Returns:
            Formatted report string
        """
        report = "═" * 70 + "\n"
        report += "                    TYPE INFERENCE ANALYSIS REPORT\n"
        report += "═" * 70 + "\n\n"

        report += f"Total Symbols Analyzed:   {len(self.inferred_types)}\n"

        high_confidence = self.get_high_confidence_suggestions(threshold=0.7)
        report += f"High Confidence Hints:    {len(high_confidence)}\n\n"

        # Show high confidence suggestions
        if high_confidence:
            report += "─" * 70 + "\n"
            report += "High Confidence Type Suggestions:\n"
            report += "─" * 70 + "\n"
            for suggestion in high_confidence[:10]:
                report += f"\n{suggestion.symbol.name}:\n"
                report += f"  Confidence: {suggestion.confidence_score:.2f}\n"

                if suggestion.parameter_suggestions:
                    report += "  Parameters:\n"
                    for param_name, hint in suggestion.parameter_suggestions.items():
                        report += f"    {param_name}: {hint.inferred_type} (confidence: {hint.confidence:.2f})\n"

                if suggestion.return_type_suggestion:
                    hint = suggestion.return_type_suggestion
                    report += (
                        f"  Return Type: {hint.inferred_type} (confidence: {hint.confidence:.2f})\n"
                    )

        return report

    def suggest_type_annotations(self, symbol: Symbol) -> List[str]:
        """Suggest type annotations for a symbol.

        Args:
            symbol: Symbol to generate annotations for

        Returns:
            List of suggested annotation strings
        """
        suggestions = self.get_type_hints_for_symbol(symbol)
        if not suggestions:
            return []

        annotations = []

        # Parameter annotations
        for param_name, hint in suggestions.parameter_suggestions.items():
            if hint.confidence >= 0.6:
                annotations.append(f"{param_name}: {hint.inferred_type}")

        # Return annotation
        if (
            suggestions.return_type_suggestion
            and suggestions.return_type_suggestion.confidence >= 0.6
        ):
            hint = suggestions.return_type_suggestion
            annotations.append(f"-> {hint.inferred_type}")

        return annotations
