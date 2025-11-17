"""Tool-specific response parser for extracting metadata from Claude Code tool outputs.

Parses different tool response formats and extracts relevant metadata for
consolidation and memory recording.
"""

import json
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class ParsedResponse:
    """Result of parsing a tool response."""
    tool_name: str
    status: str
    success: bool
    metadata: Dict[str, Any]
    summary: str


class ToolResponseParser:
    """Parse tool responses and extract metadata."""

    @staticmethod
    def parse(tool_name: str, tool_response: Dict[str, Any]) -> ParsedResponse:
        """Parse a tool response based on tool type.

        Args:
            tool_name: Name of the tool that was executed
            tool_response: The response object from the tool

        Returns:
            ParsedResponse with extracted metadata
        """
        if not tool_response:
            return ParsedResponse(
                tool_name=tool_name,
                status="unknown",
                success=False,
                metadata={},
                summary=f"No response from {tool_name}"
            )

        # Claude Code provides no explicit status field
        # PostToolUse hooks are only called for successful executions
        # So we assume success=True if tool_response is present
        status = tool_response.get("status", "success")
        success = True  # PostToolUse = successful execution

        # Route to tool-specific parser
        parser_method = getattr(
            ToolResponseParser,
            f"_parse_{tool_name.lower()}",
            ToolResponseParser._parse_generic
        )

        return parser_method(tool_name, tool_response, status, success)

    @staticmethod
    def _parse_read(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse Read tool response."""
        # Claude Code nests file info under 'file' key
        file_info = response.get("file", {})
        content = file_info.get("content", "")
        line_count = file_info.get("numLines", 0)
        total_lines = file_info.get("totalLines", 0)
        file_path = file_info.get("filePath", response.get("file_path", "unknown"))

        metadata = {
            "content_length": len(content),
            "line_count": line_count,
            "total_lines": total_lines,
            "file_path": file_path,
        }

        if success:
            summary = f"Read {line_count} lines from file ({len(content)} bytes)"
        else:
            summary = f"Failed to read file"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_write(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse Write tool response."""
        file_path = response.get("filePath", response.get("file_path", "unknown"))
        content = response.get("content", "")
        bytes_written = len(content)
        write_type = response.get("type", "write")

        metadata = {
            "file_path": file_path,
            "bytes_written": bytes_written,
            "write_type": write_type,
        }

        if success:
            summary = f"Wrote {bytes_written} bytes to {file_path}"
        else:
            summary = f"Failed to write to {file_path}"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_edit(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse Edit tool response."""
        file_path = response.get("filePath", response.get("file_path", "unknown"))
        structured_patch = response.get("structuredPatch", [])
        replacements = len(structured_patch) if isinstance(structured_patch, list) else 0

        metadata = {
            "file_path": file_path,
            "replacements_made": replacements,
            "user_modified": response.get("userModified", False),
        }

        if success:
            summary = f"Made {replacements} edits to {file_path}"
        else:
            summary = f"Failed to edit {file_path}"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_bash(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse Bash tool response."""
        stdout = response.get("stdout", "")
        stderr = response.get("stderr", "")
        interrupted = response.get("interrupted", False)

        stdout_len = len(stdout)
        stderr_len = len(stderr)

        # Infer exit code from interruption status (Claude Code doesn't provide it)
        exit_code = -1 if interrupted else 0 if success else -1

        metadata = {
            "exit_code": exit_code,
            "stdout_length": stdout_len,
            "stderr_length": stderr_len,
            "interrupted": interrupted,
        }

        if success:
            summary = f"Command completed with exit code {exit_code}"
        else:
            summary = f"Command failed with exit code {exit_code}"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_glob(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse Glob tool response."""
        filenames = response.get("filenames", [])
        match_count = response.get("numFiles", len(filenames))
        truncated = response.get("truncated", False)
        duration_ms = response.get("durationMs", 0)

        metadata = {
            "match_count": match_count,
            "truncated": truncated,
            "duration_ms": duration_ms,
            "sample_files": filenames[:5],  # First 5 files
        }

        if success:
            summary = f"Found {match_count} files"
            if truncated:
                summary += " (results truncated)"
        else:
            summary = f"Glob search failed"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_grep(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse Grep tool response."""
        matches = response.get("matches", [])
        total_matches = response.get("total_matches", len(matches))
        pattern = response.get("pattern", "unknown")

        # Extract file count
        files_with_matches = set()
        for match in matches:
            files_with_matches.add(match.get("file", "unknown"))

        metadata = {
            "pattern": pattern,
            "total_matches": total_matches,
            "files_with_matches": len(files_with_matches),
            "sample_matches": matches[:5],  # First 5 matches
        }

        if success:
            summary = f"Found {total_matches} matches for '{pattern}' in {len(files_with_matches)} files"
        else:
            summary = f"Grep search failed for pattern: {pattern}"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_askuserquestion(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse AskUserQuestion tool response."""
        answers = response.get("answers", {})
        question_count = 1  # One question asked

        metadata = {
            "answers_received": len(answers),
            "response_keys": list(answers.keys()),
        }

        if success:
            summary = f"Collected {len(answers)} answer(s) from user"
        else:
            summary = f"Failed to collect user answers"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_todowrite(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse TodoWrite tool response."""
        new_todos = response.get("newTodos", [])
        old_todos = response.get("oldTodos", [])

        new_count = len(new_todos) if isinstance(new_todos, list) else 0
        old_count = len(old_todos) if isinstance(old_todos, list) else 0

        metadata = {
            "new_todos": new_count,
            "old_todos": old_count,
            "items": [t.get("content", "unknown")[:50] for t in new_todos[:3]],
        }

        if success:
            summary = f"Updated todo list ({new_count} new, {old_count} previous)"
        else:
            summary = f"Failed to update todo list"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def _parse_generic(
        tool_name: str, response: Dict, status: str, success: bool
    ) -> ParsedResponse:
        """Parse generic tool response (fallback)."""
        # For unknown tools, extract basic info
        metadata = {
            "response_keys": list(response.keys()),
            "response_size": len(json.dumps(response)),
        }

        if success:
            summary = f"{tool_name} executed successfully"
        else:
            summary = f"{tool_name} failed with status: {status}"

        return ParsedResponse(
            tool_name=tool_name,
            status=status,
            success=success,
            metadata=metadata,
            summary=summary,
        )

    @staticmethod
    def format_for_memory(parsed: ParsedResponse) -> Dict[str, Any]:
        """Format parsed response for storage in memory.

        Args:
            parsed: ParsedResponse object

        Returns:
            Dictionary suitable for storing in episodic memory
        """
        return {
            "tool_name": parsed.tool_name,
            "status": parsed.status,
            "success": parsed.success,
            "summary": parsed.summary,
            "metadata": parsed.metadata,
        }
