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

        status = tool_response.get("status", "unknown")
        success = status == "success"

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
        content = response.get("content", "")
        line_count = response.get("line_count", 0)
        encoding = response.get("encoding", "utf-8")

        metadata = {
            "content_length": len(content),
            "line_count": line_count,
            "encoding": encoding,
            "file_path": response.get("file_path", "unknown"),
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
        file_path = response.get("file_path", "unknown")
        bytes_written = response.get("bytes_written", 0)
        content_length = response.get("content_length", 0)

        metadata = {
            "file_path": file_path,
            "bytes_written": bytes_written,
            "content_length": content_length,
            "mode": response.get("mode", "write"),
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
        file_path = response.get("file_path", "unknown")
        replacements = response.get("replacements_made", 0)
        content_changed = response.get("content_changed", False)

        metadata = {
            "file_path": file_path,
            "replacements_made": replacements,
            "content_changed": content_changed,
            "lines_affected": response.get("lines_affected", 0),
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
        exit_code = response.get("exit_code", -1)
        stdout_len = len(response.get("stdout", ""))
        stderr_len = len(response.get("stderr", ""))
        duration_ms = response.get("duration_ms", 0)

        metadata = {
            "exit_code": exit_code,
            "stdout_length": stdout_len,
            "stderr_length": stderr_len,
            "duration_ms": duration_ms,
            "command": response.get("command", "unknown")[:100],  # First 100 chars
        }

        if success:
            summary = f"Command completed with exit code {exit_code} ({duration_ms}ms)"
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
        matches = response.get("matches", [])
        match_count = response.get("match_count", len(matches))
        pattern = response.get("pattern", "unknown")

        metadata = {
            "pattern": pattern,
            "match_count": match_count,
            "matches": matches[:10],  # First 10 matches
        }

        if success:
            summary = f"Found {match_count} matches for pattern: {pattern}"
        else:
            summary = f"Glob search failed for pattern: {pattern}"

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
