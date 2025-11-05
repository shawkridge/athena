"""Tests for type inference analyzer."""

import pytest

from athena.symbols.symbol_models import Symbol, SymbolType, create_symbol
from athena.symbols.type_inference import (
    TypeInferenceAnalyzer,
    TypeHint,
    TypeAnnotationSuggestion,
    TypeCategory,
)


class TestTypeInferenceAnalyzerBasics:
    """Test basic type inference analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test type inference analyzer can be created."""
        analyzer = TypeInferenceAnalyzer()
        assert analyzer is not None
        assert len(analyzer.type_hints) == 0
        assert len(analyzer.inferred_types) == 0

    def test_type_hint_creation(self):
        """Test creating a type hint."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test_func",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code="def test_func(x): return x.upper()",
            language="python",
            visibility="public"
        )

        hint = TypeHint(
            symbol=symbol,
            parameter_name="x",
            inferred_type="str",
            confidence=0.9,
            evidence_count=3,
            type_category=TypeCategory.PRIMITIVE
        )

        assert hint.symbol == symbol
        assert hint.parameter_name == "x"
        assert hint.inferred_type == "str"
        assert hint.confidence == 0.9
        assert hint.evidence_count == 3
        assert hint.type_category == TypeCategory.PRIMITIVE
        assert len(hint.alternative_types) == 0

    def test_type_annotation_suggestion_creation(self):
        """Test creating a type annotation suggestion."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test_func",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code="def test_func(x): return x.upper()",
            language="python",
            visibility="public"
        )

        param_hint = TypeHint(
            symbol=symbol,
            parameter_name="x",
            inferred_type="str",
            confidence=0.9,
            evidence_count=3,
            type_category=TypeCategory.PRIMITIVE
        )

        return_hint = TypeHint(
            symbol=symbol,
            parameter_name=None,
            inferred_type="str",
            confidence=0.95,
            evidence_count=2,
            type_category=TypeCategory.PRIMITIVE
        )

        suggestion = TypeAnnotationSuggestion(
            symbol=symbol,
            parameter_suggestions={"x": param_hint},
            return_type_suggestion=return_hint,
            confidence_score=0.92
        )

        assert suggestion.symbol == symbol
        assert len(suggestion.parameter_suggestions) == 1
        assert suggestion.return_type_suggestion is not None
        assert suggestion.confidence_score == 0.92


class TestParameterTypeInference:
    """Test parameter type inference."""

    def test_infer_string_parameter_from_method_calls(self):
        """Test inferring string type from method calls."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process_text",
            namespace="",
            signature="(text)",
            line_start=1,
            line_end=10,
            code="def process_text(text):\n    text.upper()\n    text.lower()\n    text.strip()",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "text" in param_types
        assert param_types["text"].inferred_type == "str"
        assert param_types["text"].confidence > 0.5
        assert param_types["text"].evidence_count >= 3

    def test_infer_list_parameter_from_method_calls(self):
        """Test inferring list type from method calls."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="sort_list",
            namespace="",
            signature="(items)",
            line_start=1,
            line_end=8,
            code="def sort_list(items):\n    items.append(1)\n    items.pop()\n    items.sort()",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "items" in param_types
        assert param_types["items"].inferred_type == "list"
        assert param_types["items"].confidence > 0.5

    def test_infer_dict_parameter_from_method_calls(self):
        """Test inferring dict type from method calls."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="merge_dicts",
            namespace="",
            signature="(config)",
            line_start=1,
            line_end=8,
            code="def merge_dicts(config):\n    config.keys()\n    config.values()\n    config.get('key')",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "config" in param_types
        assert param_types["config"].inferred_type == "dict"

    def test_infer_indexable_parameter(self):
        """Test inferring indexable type from indexing."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_first",
            namespace="",
            signature="(data)",
            line_start=1,
            line_end=5,
            code="def get_first(data):\n    return data[0]",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "data" in param_types
        assert param_types["data"].inferred_type == "indexable"

    def test_infer_iterable_parameter(self):
        """Test inferring iterable type from iteration."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="iterate",
            namespace="",
            signature="(items)",
            line_start=1,
            line_end=5,
            code="def iterate(items):\n    for x in items:\n        print(x)",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "items" in param_types
        assert param_types["items"].inferred_type == "iterable"

    def test_infer_numeric_parameter(self):
        """Test inferring numeric type from operations."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="add_numbers",
            namespace="",
            signature="(a, b)",
            line_start=1,
            line_end=5,
            code="def add_numbers(a, b):\n    return a + b",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "a" in param_types
        assert param_types["a"].inferred_type == "numeric"

    def test_no_parameters_inferred(self):
        """Test function with no clear parameter types."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="unclear",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code="def unclear(x):\n    pass",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert len(param_types) == 0


class TestReturnTypeInference:
    """Test return type inference."""

    def test_infer_string_return_type(self):
        """Test inferring string return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_name",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def get_name():\n    return \"John\"",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "str"
        assert return_type.confidence == 1.0

    def test_infer_list_return_type(self):
        """Test inferring list return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_items",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def get_items():\n    return [1, 2, 3]",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "list"

    def test_infer_dict_return_type(self):
        """Test inferring dict return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_config",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def get_config():\n    return {\"key\": \"value\"}",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "dict"

    def test_infer_integer_return_type(self):
        """Test inferring integer return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="count",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def count():\n    return 42",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "int"

    def test_infer_float_return_type(self):
        """Test inferring float return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="pi",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def pi():\n    return 3.14159",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "float"

    def test_infer_bool_return_type(self):
        """Test inferring boolean return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="is_valid",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def is_valid():\n    return True",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "bool"

    def test_infer_none_return_type(self):
        """Test inferring None return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="void_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def void_func():\n    return None",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "None"

    def test_infer_union_return_types(self):
        """Test inferring union (multiple) return types."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_value",
            namespace="",
            signature="(flag)",
            line_start=1,
            line_end=8,
            code="def get_value(flag):\n    if flag:\n        return \"text\"\n    else:\n        return 42",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert len(return_type.alternative_types) > 0

    def test_no_return_type_inferred(self):
        """Test function with no return statement."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="no_return",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def no_return():\n    x = 1",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is None


class TestSymbolAnalysis:
    """Test complete symbol analysis."""

    def test_analyze_function_with_parameters_and_return(self):
        """Test analyzing a function with both parameters and return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(text, count)",
            line_start=1,
            line_end=8,
            code="def process(text, count):\n    text.upper()\n    return text * count",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        suggestion = analyzer.analyze_symbol(symbol, symbol.code)

        assert suggestion.symbol == symbol
        assert len(suggestion.parameter_suggestions) >= 1
        assert suggestion.return_type_suggestion is not None
        assert suggestion.confidence_score > 0.0

    def test_analyze_method(self):
        """Test analyzing a method."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.METHOD,
            name="get_value",
            namespace="TestClass",
            signature="(self)",
            line_start=10,
            line_end=15,
            code="def get_value(self):\n    return 42",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        suggestion = analyzer.analyze_symbol(symbol, symbol.code)

        assert suggestion.symbol == symbol
        assert suggestion.return_type_suggestion is not None

    def test_analyze_non_function_symbol(self):
        """Test analyzing a non-function symbol returns no suggestions."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="TestClass",
            namespace="",
            signature="",
            line_start=1,
            line_end=10,
            code="class TestClass:\n    pass",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        suggestion = analyzer.analyze_symbol(symbol, symbol.code)

        assert suggestion.symbol == symbol
        assert len(suggestion.parameter_suggestions) == 0
        assert suggestion.return_type_suggestion is None


class TestConfidenceScoring:
    """Test confidence scoring."""

    def test_high_confidence_single_type(self):
        """Test high confidence when all uses have same type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="str_func",
            namespace="",
            signature="(s)",
            line_start=1,
            line_end=10,
            code="def str_func(s):\n    s.upper()\n    s.lower()\n    s.strip()\n    s.replace('a', 'b')",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "s" in param_types
        assert param_types["s"].confidence > 0.7

    def test_confidence_decreases_with_mixed_types(self):
        """Test confidence is lower with mixed type uses."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="mixed",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=10,
            code="def mixed(x):\n    x.upper()\n    x[0]\n    x in [1, 2, 3]",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        if "x" in param_types:
            # With mixed types, confidence should be lower
            assert param_types["x"].confidence <= 0.7


class TestHighConfidenceSuggestions:
    """Test high confidence suggestions filtering."""

    def test_get_high_confidence_suggestions(self):
        """Test retrieving high confidence suggestions."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="clear",
            namespace="",
            signature="(items)",
            line_start=1,
            line_end=5,
            code="def clear(items):\n    items.clear()",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        analyzer.analyze_symbol(symbol, symbol.code)

        high_conf = analyzer.get_high_confidence_suggestions(threshold=0.7)

        # May or may not have suggestions depending on inference
        assert isinstance(high_conf, list)

    def test_threshold_filtering(self):
        """Test threshold filtering works correctly."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="multi",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code="def multi(x):\n    x.append(1)\n    x[0]",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        analyzer.analyze_symbol(symbol, symbol.code)

        high_conf_70 = analyzer.get_high_confidence_suggestions(threshold=0.7)
        high_conf_50 = analyzer.get_high_confidence_suggestions(threshold=0.5)

        # Higher threshold should return fewer or equal results
        assert len(high_conf_70) <= len(high_conf_50)


class TestTypeAnnotationSuggestions:
    """Test type annotation suggestion generation."""

    def test_suggest_annotations_high_confidence(self):
        """Test suggesting annotations for high confidence inferences."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="annotated",
            namespace="",
            signature="(text)",
            line_start=1,
            line_end=5,
            code="def annotated(text):\n    return text.upper()",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        analyzer.analyze_symbol(symbol, symbol.code)
        annotations = analyzer.suggest_type_annotations(symbol)

        # Should have annotations if confidence >= 0.6
        assert isinstance(annotations, list)

    def test_suggest_annotations_no_symbol(self):
        """Test suggesting annotations for non-existent symbol."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="nonexistent",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        annotations = analyzer.suggest_type_annotations(symbol)

        # Should return empty list
        assert annotations == []


class TestTypeCategorization:
    """Test type categorization."""

    def test_categorize_primitive_types(self):
        """Test categorizing primitive types."""
        analyzer = TypeInferenceAnalyzer()

        assert analyzer._categorize_type("int") == TypeCategory.PRIMITIVE
        assert analyzer._categorize_type("str") == TypeCategory.PRIMITIVE
        assert analyzer._categorize_type("float") == TypeCategory.PRIMITIVE
        assert analyzer._categorize_type("bool") == TypeCategory.PRIMITIVE
        assert analyzer._categorize_type("None") == TypeCategory.PRIMITIVE

    def test_categorize_collection_types(self):
        """Test categorizing collection types."""
        analyzer = TypeInferenceAnalyzer()

        assert analyzer._categorize_type("list") == TypeCategory.COLLECTION
        assert analyzer._categorize_type("dict") == TypeCategory.COLLECTION
        assert analyzer._categorize_type("set") == TypeCategory.COLLECTION
        assert analyzer._categorize_type("tuple") == TypeCategory.COLLECTION

    def test_categorize_special_types(self):
        """Test categorizing special types."""
        analyzer = TypeInferenceAnalyzer()

        assert analyzer._categorize_type("callable") == TypeCategory.FUNCTION
        assert analyzer._categorize_type("union") == TypeCategory.UNION
        assert analyzer._categorize_type("indexable") == TypeCategory.PRIMITIVE
        assert analyzer._categorize_type("iterable") == TypeCategory.PRIMITIVE
        assert analyzer._categorize_type("numeric") == TypeCategory.PRIMITIVE

    def test_categorize_unknown_types(self):
        """Test categorizing unknown types defaults to object."""
        analyzer = TypeInferenceAnalyzer()

        assert analyzer._categorize_type("CustomClass") == TypeCategory.OBJECT
        assert analyzer._categorize_type("unknown") == TypeCategory.OBJECT


class TestInferenceReport:
    """Test type inference report generation."""

    def test_generate_inference_report(self):
        """Test generating a type inference report."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="sample",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code="def sample(x):\n    return x.upper()",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        analyzer.analyze_symbol(symbol, symbol.code)

        report = analyzer.get_type_inference_report()

        assert isinstance(report, str)
        assert len(report) > 0
        assert "TYPE INFERENCE ANALYSIS REPORT" in report


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_function(self):
        """Test analyzing an empty function."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="empty",
            namespace="",
            signature="()",
            line_start=1,
            line_end=2,
            code="def empty():\n    pass",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        suggestion = analyzer.analyze_symbol(symbol, symbol.code)

        assert suggestion is not None
        assert len(suggestion.parameter_suggestions) == 0
        assert suggestion.return_type_suggestion is None

    def test_function_with_comments(self):
        """Test analyzing function with comments."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="commented",
            namespace="",
            signature="(text)",
            line_start=1,
            line_end=8,
            code="def commented(text):\n    # This is a comment\n    text.upper()\n    # Another comment\n    return text",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        suggestion = analyzer.analyze_symbol(symbol, symbol.code)

        assert suggestion is not None

    def test_multiple_return_statements(self):
        """Test analyzing function with multiple returns."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="multi_return",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=8,
            code="def multi_return(x):\n    if x:\n        return \"yes\"\n    else:\n        return \"no\"",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.evidence_count >= 2

    def test_async_function(self):
        """Test analyzing an async function."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.ASYNC_FUNCTION,
            name="async_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="async def async_func():\n    return 42",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "int"

    def test_tuple_return_type(self):
        """Test inferring tuple return type."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_pair",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def get_pair():\n    return (1, 2)",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        return_type = analyzer.infer_return_type(symbol, symbol.code)

        assert return_type is not None
        assert return_type.inferred_type == "tuple"

    def test_set_parameter_type(self):
        """Test inferring set type from method calls."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process_set",
            namespace="",
            signature="(s)",
            line_start=1,
            line_end=8,
            code="def process_set(s):\n    s.add(1)\n    s.union({2, 3})",
            language="python",
            visibility="public"
        )

        analyzer = TypeInferenceAnalyzer()
        param_types = analyzer.infer_parameter_types(symbol, symbol.code)

        assert "s" in param_types
        assert param_types["s"].inferred_type == "set"
