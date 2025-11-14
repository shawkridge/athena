"""Tool name validation and sanitization.

Validates that tool names come from a whitelist of known Claude Code tools.
Prevents injection attacks and ensures data quality.
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass


# Whitelist of valid Claude Code tools
VALID_TOOLS = {
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "Task",
    "Skill",
    "SlashCommand",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "AskUserQuestion",
    "ExitPlanMode",
    "TodoWrite",
    "BashOutput",
    "KillShell",
}


@dataclass
class ValidationResult:
    """Result of tool validation."""
    valid: bool
    tool_name: str
    error: Optional[str] = None
    message: str = ""


def validate_tool_name(tool_name: Optional[str]) -> ValidationResult:
    """Validate that tool name is in whitelist.

    Args:
        tool_name: Tool name to validate

    Returns:
        ValidationResult with validation status
    """
    # Check for None/empty
    if not tool_name:
        return ValidationResult(
            valid=False,
            tool_name="",
            error="Tool name is empty",
            message="Tool name was not provided"
        )

    # Check type
    if not isinstance(tool_name, str):
        return ValidationResult(
            valid=False,
            tool_name=str(tool_name),
            error="Tool name must be a string",
            message=f"Tool name has type {type(tool_name).__name__}"
        )

    # Check length (reasonable limit to prevent abuse)
    if len(tool_name) > 100:
        return ValidationResult(
            valid=False,
            tool_name=tool_name[:50] + "...",
            error="Tool name too long (max 100 characters)",
            message=f"Tool name is {len(tool_name)} characters"
        )

    # Strip whitespace
    tool_name_stripped = tool_name.strip()

    # Check for suspicious characters
    if not re.match(r'^[A-Za-z0-9_-]+$', tool_name_stripped):
        return ValidationResult(
            valid=False,
            tool_name=tool_name_stripped,
            error="Tool name contains invalid characters",
            message="Tool name must contain only alphanumeric, underscore, or hyphen"
        )

    # Check against whitelist
    if tool_name_stripped in VALID_TOOLS:
        return ValidationResult(
            valid=True,
            tool_name=tool_name_stripped,
            message=f"Tool '{tool_name_stripped}' is valid"
        )
    else:
        # Suggest closest match for debugging
        suggestions = _find_suggestions(tool_name_stripped)
        suggestion_text = ""
        if suggestions:
            suggestion_text = f" (did you mean {suggestions[0]}?)"

        return ValidationResult(
            valid=False,
            tool_name=tool_name_stripped,
            error="Tool not in whitelist",
            message=f"Unknown tool '{tool_name_stripped}'{suggestion_text}. Valid tools: {', '.join(sorted(VALID_TOOLS))}"
        )


def validate_tool_status(status: Optional[str]) -> ValidationResult:
    """Validate tool execution status.

    Args:
        status: Status to validate (success, failure, timeout)

    Returns:
        ValidationResult with validation status
    """
    valid_statuses = {"success", "failure", "timeout"}

    if not status:
        return ValidationResult(
            valid=False,
            tool_name="",
            error="Status is empty",
            message="Tool status was not provided"
        )

    status_stripped = status.strip().lower()

    if status_stripped in valid_statuses:
        return ValidationResult(
            valid=True,
            tool_name="",
            message=f"Status '{status_stripped}' is valid"
        )
    else:
        return ValidationResult(
            valid=False,
            tool_name="",
            error="Invalid status",
            message=f"Status must be one of: {', '.join(valid_statuses)}. Got: {status_stripped}"
        )


def validate_execution_time(time_ms: Optional[str]) -> Tuple[bool, int, Optional[str]]:
    """Validate execution time in milliseconds.

    Args:
        time_ms: Execution time as string

    Returns:
        Tuple of (valid, time_value, error_message)
    """
    if not time_ms:
        return False, 0, "Execution time not provided"

    try:
        time_int = int(time_ms)

        if time_int < 0:
            return False, 0, f"Execution time cannot be negative: {time_int}"

        if time_int > 3_600_000:  # 1 hour max
            return False, 0, f"Execution time suspiciously high: {time_int}ms"

        return True, time_int, None

    except ValueError:
        return False, 0, f"Execution time must be numeric: {time_ms}"


def _find_suggestions(tool_name: str, limit: int = 3) -> list:
    """Find similar tool names (for helpful error messages).

    Uses simple character overlap heuristic.

    Args:
        tool_name: Input tool name
        limit: Max suggestions to return

    Returns:
        List of similar tool names
    """
    def similarity(a: str, b: str) -> int:
        """Count matching characters (case-insensitive)."""
        a_lower = a.lower()
        b_lower = b.lower()
        return sum(1 for c in a_lower if c in b_lower)

    scored = [
        (tool, similarity(tool_name, tool))
        for tool in VALID_TOOLS
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [tool for tool, score in scored[:limit] if score > 0]


def get_safe_tool_name(tool_name: Optional[str]) -> str:
    """Get a safe, validated tool name or empty string.

    Args:
        tool_name: Tool name to validate

    Returns:
        Valid tool name or empty string
    """
    result = validate_tool_name(tool_name)
    return result.tool_name if result.valid else ""


# For easy import
__all__ = [
    "VALID_TOOLS",
    "ValidationResult",
    "validate_tool_name",
    "validate_tool_status",
    "validate_execution_time",
    "get_safe_tool_name",
]
