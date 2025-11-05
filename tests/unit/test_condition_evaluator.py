"""Unit tests for ConditionEvaluator in Phase 9."""

import pytest
from athena.rules.condition_evaluator import ConditionEvaluator


class TestConditionEvaluator:
    """Test ConditionEvaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ConditionEvaluator()

    # JSON Condition Tests
    def test_json_condition_exact_match(self, evaluator):
        """Test JSON condition with exact match."""
        condition = '{"field": "value"}'
        context = {"field": "value"}
        assert evaluator.evaluate(condition, context) is True

    def test_json_condition_mismatch(self, evaluator):
        """Test JSON condition with mismatch."""
        condition = '{"field": "value"}'
        context = {"field": "other"}
        assert evaluator.evaluate(condition, context) is False

    def test_json_condition_missing_key(self, evaluator):
        """Test JSON condition with missing key."""
        condition = '{"field": "value"}'
        context = {"other": "value"}
        assert evaluator.evaluate(condition, context) is False

    def test_json_condition_multiple_fields(self, evaluator):
        """Test JSON condition with multiple fields."""
        condition = '{"field1": "value1", "field2": "value2"}'
        context = {"field1": "value1", "field2": "value2"}
        assert evaluator.evaluate(condition, context) is True

    def test_json_condition_multiple_fields_partial_match(self, evaluator):
        """Test JSON condition with partial match fails."""
        condition = '{"field1": "value1", "field2": "value2"}'
        context = {"field1": "value1", "field2": "other"}
        assert evaluator.evaluate(condition, context) is False

    def test_json_condition_invalid_json(self, evaluator):
        """Test invalid JSON condition."""
        condition = '{"field": invalid}'
        context = {"field": "value"}
        assert evaluator.evaluate(condition, context) is False

    # Expression Condition Tests
    def test_expression_greater_than(self, evaluator):
        """Test > comparison."""
        condition = "value > 50"
        context = {"value": 60}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 40}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_less_than(self, evaluator):
        """Test < comparison."""
        condition = "value < 50"
        context = {"value": 40}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 60}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_greater_equal(self, evaluator):
        """Test >= comparison."""
        condition = "value >= 50"
        context = {"value": 50}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 60}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 40}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_less_equal(self, evaluator):
        """Test <= comparison."""
        condition = "value <= 50"
        context = {"value": 50}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 40}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 60}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_equal(self, evaluator):
        """Test == comparison."""
        condition = "value == 50"
        context = {"value": 50}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 60}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_not_equal(self, evaluator):
        """Test != comparison."""
        condition = "value != 50"
        context = {"value": 60}
        assert evaluator.evaluate(condition, context) is True

        context = {"value": 50}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_string_values(self, evaluator):
        """Test expression with string values."""
        condition = 'status == "active"'
        context = {"status": "active"}
        assert evaluator.evaluate(condition, context) is True

        context = {"status": "inactive"}
        assert evaluator.evaluate(condition, context) is False

    # Boolean Operator Tests
    def test_expression_and_operator_both_true(self, evaluator):
        """Test AND operator with both true."""
        condition = "a > 5 and b < 10"
        context = {"a": 6, "b": 9}
        assert evaluator.evaluate(condition, context) is True

    def test_expression_and_operator_one_false(self, evaluator):
        """Test AND operator with one false."""
        condition = "a > 5 and b < 10"
        context = {"a": 4, "b": 9}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_or_operator_both_true(self, evaluator):
        """Test OR operator with both true."""
        condition = "a > 5 or b < 10"
        context = {"a": 6, "b": 9}
        assert evaluator.evaluate(condition, context) is True

    def test_expression_or_operator_one_true(self, evaluator):
        """Test OR operator with one true."""
        condition = "a > 5 or b < 10"
        context = {"a": 4, "b": 9}
        assert evaluator.evaluate(condition, context) is True

    def test_expression_or_operator_both_false(self, evaluator):
        """Test OR operator with both false."""
        condition = "a > 5 or b < 10"
        context = {"a": 4, "b": 11}
        assert evaluator.evaluate(condition, context) is False

    def test_expression_complex_boolean(self, evaluator):
        """Test complex boolean expression."""
        condition = "a > 5 and b < 10 or c == 20"
        context = {"a": 6, "b": 15, "c": 20}
        assert evaluator.evaluate(condition, context) is True

        context = {"a": 4, "b": 9, "c": 20}
        assert evaluator.evaluate(condition, context) is True

    # Pattern Condition Tests
    def test_pattern_simple_contains(self, evaluator):
        """Test simple pattern matching."""
        condition = "PATTERN: test"
        context = {"content": "this is a test"}
        # Pattern matching is case-insensitive
        assert evaluator.evaluate(condition, context) is True

    def test_pattern_matching_true(self, evaluator):
        """Test simple pattern matching."""
        condition = "PATTERN: test_coverage"
        context = {"metric": "test_coverage", "value": 0.8}
        assert evaluator.evaluate(condition, context) is True

    def test_pattern_matching_false(self, evaluator):
        """Test simple pattern matching failure."""
        condition = "PATTERN: deployment"
        context = {"metric": "coverage", "value": 0.8}
        assert evaluator.evaluate(condition, context) is False

    # Validation Tests
    def test_validate_json_condition(self, evaluator):
        """Test validating JSON condition."""
        condition = '{"field": "value"}'
        is_valid, error = evaluator.validate_condition(condition)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_json(self, evaluator):
        """Test validating invalid JSON."""
        condition = '{"field": invalid}'
        is_valid, error = evaluator.validate_condition(condition)
        assert is_valid is False
        assert error is not None

    def test_validate_expression(self, evaluator):
        """Test validating expression."""
        condition = "value > 50"
        is_valid, error = evaluator.validate_condition(condition)
        assert is_valid is True
        assert error is None

    def test_validate_pattern(self, evaluator):
        """Test validating pattern."""
        condition = "PATTERN: test"
        is_valid, error = evaluator.validate_condition(condition)
        assert is_valid is True
        assert error is None

    def test_validate_empty_condition(self, evaluator):
        """Test validating empty condition."""
        condition = ""
        is_valid, error = evaluator.validate_condition(condition)
        assert is_valid is False
        assert error is not None

    # Context Keys Tests
    def test_suggest_context_keys_json(self, evaluator):
        """Test suggesting context keys from JSON."""
        condition = '{"field1": "value", "field2": "value"}'
        keys = evaluator.suggest_context_keys(condition)
        assert "field1" in keys
        assert "field2" in keys

    def test_suggest_context_keys_expression(self, evaluator):
        """Test suggesting context keys from expression."""
        condition = "field1 > 50 and field2 < 10"
        keys = evaluator.suggest_context_keys(condition)
        assert "field1" in keys
        assert "field2" in keys

    def test_suggest_context_keys_pattern(self, evaluator):
        """Test suggesting context keys from pattern."""
        condition = "PATTERN: test_coverage"
        keys = evaluator.suggest_context_keys(condition)
        assert "test_coverage" in keys

    # Edge Cases
    def test_evaluate_empty_condition(self, evaluator):
        """Test empty condition evaluates to True."""
        condition = ""
        context = {"field": "value"}
        assert evaluator.evaluate(condition, context) is True

    def test_evaluate_whitespace_condition(self, evaluator):
        """Test whitespace-only condition evaluates to True."""
        condition = "   "
        context = {"field": "value"}
        assert evaluator.evaluate(condition, context) is True

    def test_evaluate_missing_context_key(self, evaluator):
        """Test expression with missing context key."""
        condition = "value > 50"
        context = {"other": 60}
        assert evaluator.evaluate(condition, context) is False

    def test_evaluate_type_mismatch_numeric(self, evaluator):
        """Test type mismatch with numeric comparison."""
        condition = "value > 50"
        context = {"value": "not a number"}
        assert evaluator.evaluate(condition, context) is False

    def test_case_insensitive_boolean_operators(self, evaluator):
        """Test case-insensitive AND/OR operators."""
        condition1 = "a > 5 AND b < 10"
        condition2 = "a > 5 And b < 10"

        context = {"a": 6, "b": 9}
        assert evaluator.evaluate(condition1, context) is True
        assert evaluator.evaluate(condition2, context) is True
