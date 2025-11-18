"""Rule condition parsing and evaluation for Phase 9."""

import json
import logging
import re
from typing import Any, Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluates rule conditions against task/plan context."""

    # Pattern for simple comparisons (order matters: >= before >, <= before <)
    COMPARISON_PATTERN = r"(\w+)\s*(>=|<=|>|<|==|!=)\s*(.+)"

    # Pattern for boolean operators
    BOOLEAN_PATTERN = r"\s+(and|or)\s+"

    def __init__(self):
        """Initialize ConditionEvaluator."""
        self._condition_cache = {}

    def evaluate(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate rule condition against context.

        Supports:
        - JSON queries: {"field": "value"} matches context[field] == value
        - Expressions: "function_length > 50 and test_coverage < 80"
        - Patterns: "PATTERN: no_hardcoded_secrets"
        - Custom: Lambda expressions with context

        Args:
            condition: Condition string
            context: Context dictionary

        Returns:
            True if condition evaluates to True (rule applies)
        """
        if not condition:
            return True

        condition = condition.strip()

        # Empty after strip also returns True
        if not condition:
            return True

        # Handle pattern-based conditions
        if condition.startswith("PATTERN:"):
            return self._evaluate_pattern(condition[8:].strip(), context)

        # Handle JSON conditions
        if condition.startswith("{"):
            return self._evaluate_json(condition, context)

        # Handle expression-based conditions
        return self._evaluate_expression(condition, context)

    def _evaluate_json(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate JSON query condition.

        Supports MongoDB-style operators:
        - {"field": {"$gt": value}} - greater than
        - {"field": {"$lt": value}} - less than
        - {"field": {"$gte": value}} - greater than or equal
        - {"field": {"$lte": value}} - less than or equal
        - {"field": {"$eq": value}} - equal
        - {"field": {"$ne": value}} - not equal
        - {"field": value} - exact match

        Args:
            condition: JSON string
            context: Context dictionary

        Returns:
            True if all JSON fields match context
        """
        try:
            query = json.loads(condition)

            for key, expected_value in query.items():
                if key not in context:
                    logger.debug(f"Context missing key: {key}")
                    return False

                context_value = context[key]

                # Check if expected_value is a dict with operators
                if isinstance(expected_value, dict):
                    # MongoDB-style operators
                    for operator, op_value in expected_value.items():
                        try:
                            if operator == "$gt":
                                if not (context_value > op_value):
                                    return False
                            elif operator == "$lt":
                                if not (context_value < op_value):
                                    return False
                            elif operator == "$gte":
                                if not (context_value >= op_value):
                                    return False
                            elif operator == "$lte":
                                if not (context_value <= op_value):
                                    return False
                            elif operator == "$eq":
                                if not (context_value == op_value):
                                    return False
                            elif operator == "$ne":
                                if not (context_value != op_value):
                                    return False
                            else:
                                logger.warning(f"Unknown operator: {operator}")
                                return False
                        except TypeError as e:
                            logger.warning(
                                f"Type error comparing {context_value} {operator} {op_value}: {e}"
                            )
                            return False
                else:
                    # Exact match
                    if context_value != expected_value:
                        logger.debug(
                            f"Context value mismatch: {key} = {context_value}, "
                            f"expected {expected_value}"
                        )
                        return False

            return True

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON condition: {condition}: {e}")
            return False

    def _evaluate_expression(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate expression-based condition.

        Args:
            condition: Expression string (e.g., "x > 5 and y < 10")
            context: Context dictionary

        Returns:
            True if expression evaluates to True
        """
        try:
            # Split by boolean operators
            parts = re.split(self.BOOLEAN_PATTERN, condition, flags=re.IGNORECASE)

            if len(parts) == 1:
                # Single comparison
                return self._evaluate_comparison(parts[0].strip(), context)

            # Multiple comparisons with boolean operators
            result = self._evaluate_comparison(parts[0].strip(), context)

            i = 1
            while i < len(parts):
                operator = parts[i].lower()
                comparison = parts[i + 1].strip()

                next_result = self._evaluate_comparison(comparison, context)

                if operator == "and":
                    result = result and next_result
                elif operator == "or":
                    result = result or next_result

                i += 2

            return result

        except Exception as e:
            logger.warning(f"Error evaluating expression '{condition}': {e}")
            return False

    def _evaluate_comparison(self, comparison: str, context: Dict[str, Any]) -> bool:
        """Evaluate single comparison.

        Args:
            comparison: Comparison string (e.g., "x > 5")
            context: Context dictionary

        Returns:
            True if comparison is True
        """
        match = re.match(self.COMPARISON_PATTERN, comparison.strip())
        if not match:
            logger.warning(f"Invalid comparison format: {comparison}")
            return False

        field, operator, value = match.groups()

        if field not in context:
            logger.debug(f"Context missing field: {field}")
            return False

        context_value = context[field]

        # Try to parse value as number
        try:
            compare_value = float(value)
        except ValueError:
            # Keep as string
            compare_value = value.strip("\"'")

        try:
            if operator == ">":
                return context_value > compare_value
            elif operator == "<":
                return context_value < compare_value
            elif operator == ">=":
                return context_value >= compare_value
            elif operator == "<=":
                return context_value <= compare_value
            elif operator == "==":
                return context_value == compare_value
            elif operator == "!=":
                return context_value != compare_value

        except TypeError as e:
            logger.warning(f"Type error comparing {context_value} {operator} {compare_value}: {e}")
            return False

        return False

    def _evaluate_pattern(self, pattern: str, context: Dict[str, Any]) -> bool:
        """Evaluate pattern-based condition.

        Args:
            pattern: Pattern string
            context: Context dictionary

        Returns:
            True if pattern matches context
        """
        pattern_lower = pattern.lower().strip()

        # Convert context values to lowercase strings for pattern matching
        context_str = str(context).lower()

        # Simple substring matching for now
        # Can be enhanced with more sophisticated pattern matching
        if "without" in pattern_lower:
            # Pattern: "something without something_else"
            # Check if context contains key for positive part
            parts = pattern_lower.split("without")
            positive = parts[0].strip()
            negative = parts[1].strip()

            has_positive = positive in context_str
            has_negative = negative in context_str

            return has_positive and not has_negative

        # Simple pattern matching
        return pattern_lower in context_str

    def validate_condition(self, condition: str) -> Tuple[bool, Optional[str]]:
        """Validate condition syntax.

        Args:
            condition: Condition string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not condition:
            return False, "Condition cannot be empty"

        condition = condition.strip()

        # Try JSON
        if condition.startswith("{"):
            try:
                json.loads(condition)
                return True, None
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {e}"

        # Try pattern
        if condition.startswith("PATTERN:"):
            return True, None

        # Try expression
        try:
            # Basic validation: check if it has valid structure
            if re.search(self.COMPARISON_PATTERN, condition):
                return True, None

            return False, "Invalid expression format"

        except Exception as e:
            return False, f"Error validating condition: {e}"

    def suggest_context_keys(self, condition: str) -> List[str]:
        """Identify what context keys are needed for evaluation.

        Args:
            condition: Condition string

        Returns:
            List of required context keys
        """
        keys = set()

        condition = condition.strip()

        # Extract from JSON
        if condition.startswith("{"):
            try:
                query = json.loads(condition)
                keys.update(query.keys())
            except json.JSONDecodeError:
                pass

        # Extract from expression using regex
        matches = re.findall(r"\b(\w+)\s*[><=!]", condition)
        keys.update(matches)

        # Extract from pattern (simple heuristic)
        if "PATTERN:" in condition:
            pattern_part = condition.split("PATTERN:")[1].lower()
            # Extract common patterns
            if "test_coverage" in pattern_part:
                keys.add("test_coverage")
            if "function_length" in pattern_part:
                keys.add("function_length")
            if "hardcoded" in pattern_part:
                keys.add("has_hardcoded_secrets")

        return sorted(list(keys))
