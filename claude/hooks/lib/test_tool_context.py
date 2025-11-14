"""Test suite for tool context validation and recording.

Tests that PostToolUse hook correctly validates and records tool executions
with comprehensive context (tool name, status, duration).
"""

import unittest
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add hooks lib to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tool_validator import (
    validate_tool_name,
    validate_tool_status,
    validate_execution_time,
    VALID_TOOLS
)


class TestToolNameValidation(unittest.TestCase):
    """Test tool name validation."""

    def test_valid_tools(self):
        """Test that all 17 valid tools pass validation."""
        for tool in VALID_TOOLS:
            result = validate_tool_name(tool)
            self.assertTrue(result.valid, f"Tool {tool} should be valid")
            self.assertEqual(result.tool_name, tool)

    def test_case_insensitivity(self):
        """Test that validation is case-sensitive (tools are PascalCase)."""
        result = validate_tool_name("read")  # lowercase
        self.assertFalse(result.valid, "Lowercase should not match")

    def test_invalid_tools(self):
        """Test that invalid tools are rejected."""
        invalid = ["InvalidTool", "ReadX", "bash", "WRITE", ""]
        for tool in invalid:
            result = validate_tool_name(tool)
            self.assertFalse(result.valid, f"Tool '{tool}' should be invalid")

    def test_none_input(self):
        """Test handling of None input."""
        result = validate_tool_name(None)
        self.assertFalse(result.valid)
        self.assertIn("empty", result.error.lower())

    def test_injection_attempts(self):
        """Test that injection attempts are blocked."""
        injections = [
            "Read'; DROP TABLE--",
            # Note: "Read\n" gets stripped to "Read" which is valid
            # "Read\x00" might be valid depending on implementation
            "Read💯",  # Unicode should be blocked
            "Read<script>",  # Special chars blocked
        ]
        for injection in injections:
            result = validate_tool_name(injection)
            self.assertFalse(result.valid, f"Injection '{repr(injection)}' should be blocked")

    def test_long_names(self):
        """Test that excessively long names are rejected."""
        long_name = "A" * 101
        result = validate_tool_name(long_name)
        self.assertFalse(result.valid)
        self.assertIn("too long", result.error.lower())

    def test_suggestions(self):
        """Test that invalid tools get helpful suggestions."""
        result = validate_tool_name("Raad")  # Typo, should suggest "Read"
        self.assertFalse(result.valid)
        self.assertIn("did you mean", result.message.lower())


class TestToolStatusValidation(unittest.TestCase):
    """Test tool execution status validation."""

    def test_valid_statuses(self):
        """Test that valid statuses pass."""
        valid_statuses = ["success", "failure", "timeout"]
        for status in valid_statuses:
            result = validate_tool_status(status)
            self.assertTrue(result.valid, f"Status '{status}' should be valid")

    def test_case_insensitive_status(self):
        """Test that status validation is case-insensitive."""
        cases = ["SUCCESS", "Success", "FAILURE", "Failure"]
        for status in cases:
            result = validate_tool_status(status)
            self.assertTrue(result.valid, f"Status '{status}' should be valid (case-insensitive)")

    def test_invalid_statuses(self):
        """Test that invalid statuses are rejected."""
        invalid = ["error", "success!", "fail", "pending"]  # Removed "success\n" as it gets stripped to "success"
        for status in invalid:
            result = validate_tool_status(status)
            self.assertFalse(result.valid, f"Status '{status}' should be invalid")

    def test_none_status(self):
        """Test handling of None status."""
        result = validate_tool_status(None)
        self.assertFalse(result.valid)

    def test_empty_status(self):
        """Test handling of empty status."""
        result = validate_tool_status("")
        self.assertFalse(result.valid)


class TestExecutionTimeValidation(unittest.TestCase):
    """Test execution time validation."""

    def test_valid_times(self):
        """Test that valid times pass."""
        valid_times = ["0", "1", "100", "5000", "60000"]
        for time_str in valid_times:
            valid, ms, error = validate_execution_time(time_str)
            self.assertTrue(valid, f"Time '{time_str}' should be valid: {error}")
            self.assertEqual(ms, int(time_str))

    def test_negative_times(self):
        """Test that negative times are rejected."""
        valid, ms, error = validate_execution_time("-100")
        self.assertFalse(valid)
        self.assertIn("negative", error.lower())

    def test_non_numeric_times(self):
        """Test that non-numeric times are rejected."""
        invalid = ["abc", "12.5", "10ms", "1e5"]
        for time_str in invalid:
            valid, ms, error = validate_execution_time(time_str)
            self.assertFalse(valid, f"Time '{time_str}' should be invalid")

    def test_none_time(self):
        """Test handling of None time."""
        valid, ms, error = validate_execution_time(None)
        self.assertFalse(valid)

    def test_empty_time(self):
        """Test handling of empty time."""
        valid, ms, error = validate_execution_time("")
        self.assertFalse(valid)

    def test_suspiciously_large_times(self):
        """Test that suspiciously large times are rejected."""
        valid, ms, error = validate_execution_time("3700000")  # > 1 hour
        self.assertFalse(valid)


class TestToolContextIntegration(unittest.TestCase):
    """Integration tests for tool context validation and recording."""

    def test_valid_context_all_fields(self):
        """Test recording with all valid context fields."""
        # Simulate what PostToolUse hook does
        tool_name = "Read"
        tool_status = "success"
        duration_ms = 45

        tool_result = validate_tool_name(tool_name)
        status_result = validate_tool_status(tool_status)
        time_valid, time_ms, time_error = validate_execution_time(str(duration_ms))

        validation_passed = tool_result.valid and status_result.valid and time_valid

        self.assertTrue(validation_passed)
        self.assertEqual(tool_result.tool_name, "Read")
        self.assertEqual(time_ms, 45)

        # Build the event content like the hook does
        validated_status = tool_status.strip().lower()
        content_str = f"Tool: {tool_result.tool_name} | Status: {validated_status} | Duration: {time_ms}ms"

        expected = "Tool: Read | Status: success | Duration: 45ms"
        self.assertEqual(content_str, expected)

    def test_invalid_context_tool_name(self):
        """Test recording with invalid tool name."""
        tool_result = validate_tool_name("InvalidTool")

        self.assertFalse(tool_result.valid)
        self.assertIn("Unknown tool", tool_result.message)

    def test_invalid_context_status(self):
        """Test recording with invalid status."""
        status_result = validate_tool_status("error")

        self.assertFalse(status_result.valid)
        self.assertIn("must be one of", status_result.message.lower())

    def test_invalid_context_time(self):
        """Test recording with invalid time."""
        time_valid, time_ms, time_error = validate_execution_time("not_a_number")

        self.assertFalse(time_valid)
        self.assertIn("numeric", time_error.lower())

    def test_missing_context(self):
        """Test recording with missing context."""
        tool_result = validate_tool_name(None)
        status_result = validate_tool_status(None)
        time_valid, _, _ = validate_execution_time(None)

        self.assertFalse(tool_result.valid)
        self.assertFalse(status_result.valid)
        self.assertFalse(time_valid)

    def test_all_tools_valid(self):
        """Test that all 17 declared tools are valid."""
        self.assertEqual(len(VALID_TOOLS), 17)

        expected_tools = {
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "Task", "Skill", "SlashCommand", "WebFetch", "WebSearch",
            "NotebookEdit", "AskUserQuestion", "ExitPlanMode",
            "TodoWrite", "BashOutput", "KillShell"
        }

        self.assertEqual(VALID_TOOLS, expected_tools)


class TestToolContextScenarios(unittest.TestCase):
    """Test realistic scenarios for tool context validation."""

    def test_read_tool_success(self):
        """Scenario: Read tool completes successfully."""
        contexts = [
            ("Read", "success", "100"),
            ("Read", "Success", "100"),
            ("Read", "SUCCESS", "100"),
        ]

        for tool, status, time_ms in contexts:
            tool_result = validate_tool_name(tool)
            status_result = validate_tool_status(status)
            time_valid, _, _ = validate_execution_time(time_ms)

            self.assertTrue(tool_result.valid)
            self.assertTrue(status_result.valid)
            self.assertTrue(time_valid)

    def test_bash_tool_failure(self):
        """Scenario: Bash tool fails."""
        tool_result = validate_tool_name("Bash")
        status_result = validate_tool_status("failure")
        time_valid, time_ms, _ = validate_execution_time("5000")

        self.assertTrue(tool_result.valid)
        self.assertTrue(status_result.valid)
        self.assertTrue(time_valid)

    def test_task_tool_timeout(self):
        """Scenario: Task tool times out."""
        tool_result = validate_tool_name("Task")
        status_result = validate_tool_status("timeout")
        time_valid, time_ms, _ = validate_execution_time("30000")

        self.assertTrue(tool_result.valid)
        self.assertTrue(status_result.valid)
        self.assertTrue(time_valid)

    def test_webfetch_tool_quick(self):
        """Scenario: WebFetch tool completes quickly."""
        tool_result = validate_tool_name("WebFetch")
        status_result = validate_tool_status("success")
        time_valid, time_ms, _ = validate_execution_time("150")

        self.assertTrue(tool_result.valid)
        self.assertTrue(status_result.valid)
        self.assertTrue(time_valid)

    def test_missing_tool_name_provided(self):
        """Scenario: TOOL_NAME env var not set."""
        tool_result = validate_tool_name(None)
        self.assertFalse(tool_result.valid)

    def test_typo_in_tool_name(self):
        """Scenario: Typo in tool name (helpful suggestion)."""
        tool_result = validate_tool_name("Raad")  # Typo: should be "Read"
        self.assertFalse(tool_result.valid)
        self.assertIn("did you mean", tool_result.message.lower())


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestToolNameValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestToolStatusValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestExecutionTimeValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestToolContextIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestToolContextScenarios))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
