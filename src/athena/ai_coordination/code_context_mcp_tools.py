"""MCP tool handlers for CodeContext layer."""

from mcp.types import Tool

from ..core.database import Database
from .code_context import (
    DependencyType,
    FileRole,
    IssueSeverity,
    IssueStatus,
)
from .code_context_store import CodeContextStore


class CodeContextMCPTools:
    """MCP tools for CodeContext layer."""

    def __init__(self, db: Database):
        """Initialize tools.

        Args:
            db: Database instance
        """
        self.store = CodeContextStore(db)

    def get_tools(self) -> list[Tool]:
        """Get CodeContext tools definitions.

        Returns:
            List of Tool definitions
        """
        return [
            Tool(
                name="create_code_context",
                description="Create a new code context for a task or goal",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "UUID of task this context is for"
                        },
                        "goal_id": {
                            "type": "string",
                            "description": "UUID of goal this context is for"
                        },
                        "architecture_notes": {
                            "type": "string",
                            "description": "Optional architecture notes"
                        },
                        "expires_in_hours": {
                            "type": "integer",
                            "description": "Hours until context expires (default: 24)"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="add_relevant_file",
                description="Add a relevant file to a code context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Relative file path"
                        },
                        "relevance": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Relevance score (0.0-1.0)"
                        },
                        "role": {
                            "type": "string",
                            "enum": ["implementation", "dependency", "test", "configuration", "documentation", "reference"],
                            "description": "Role of file in task"
                        },
                        "lines_changed": {
                            "type": "integer",
                            "description": "Lines changed in this file"
                        }
                    },
                    "required": ["context_id", "file_path"]
                }
            ),
            Tool(
                name="add_file_dependency",
                description="Add a dependency relationship between two files",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "from_file": {
                            "type": "string",
                            "description": "Source file path"
                        },
                        "to_file": {
                            "type": "string",
                            "description": "Target file path"
                        },
                        "dependency_type": {
                            "type": "string",
                            "enum": ["import", "reference", "config", "testing", "build"],
                            "description": "Type of dependency"
                        },
                        "description": {
                            "type": "string",
                            "description": "Why are they related?"
                        },
                        "strength": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Dependency strength (0.0-1.0)"
                        }
                    },
                    "required": ["context_id", "from_file", "to_file", "dependency_type"]
                }
            ),
            Tool(
                name="add_recent_change",
                description="Add a recent code change to context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "File that changed"
                        },
                        "change_summary": {
                            "type": "string",
                            "description": "Summary of what changed"
                        },
                        "author": {
                            "type": "string",
                            "description": "Who made the change"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session that made this change"
                        }
                    },
                    "required": ["context_id", "file_path", "change_summary"]
                }
            ),
            Tool(
                name="add_known_issue",
                description="Add a known issue in the code context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "File with the issue"
                        },
                        "issue": {
                            "type": "string",
                            "description": "Issue description"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Issue severity"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["open", "in_progress", "resolved", "wont_fix"],
                            "description": "Issue status"
                        },
                        "resolution_notes": {
                            "type": "string",
                            "description": "Optional resolution notes"
                        }
                    },
                    "required": ["context_id", "file_path", "issue", "severity"]
                }
            ),
            Tool(
                name="get_relevant_files",
                description="Get relevant files for a code context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "min_relevance": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Minimum relevance threshold"
                        }
                    },
                    "required": ["context_id"]
                }
            ),
            Tool(
                name="get_file_dependencies",
                description="Get dependency graph for a context or specific file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional: specific file to query dependencies for"
                        }
                    },
                    "required": ["context_id"]
                }
            ),
            Tool(
                name="get_recent_changes",
                description="Get recent changes in a code context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number to return (default: 20)"
                        }
                    },
                    "required": ["context_id"]
                }
            ),
            Tool(
                name="get_known_issues",
                description="Get known issues in a code context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["open", "in_progress", "resolved", "wont_fix"],
                            "description": "Optional: filter by status"
                        }
                    },
                    "required": ["context_id"]
                }
            ),
            Tool(
                name="get_code_context",
                description="Get full code context for task or retrieve by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID to retrieve"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Or: task ID to get context for"
                        }
                    }
                }
            ),
            Tool(
                name="refresh_code_context",
                description="Refresh a code context expiration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        },
                        "expires_in_hours": {
                            "type": "integer",
                            "description": "New expiration window (default: 24)"
                        }
                    },
                    "required": ["context_id"]
                }
            ),
            Tool(
                name="check_context_staleness",
                description="Check if a code context has expired",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {
                            "type": "integer",
                            "description": "Context ID"
                        }
                    },
                    "required": ["context_id"]
                }
            ),
        ]

    async def handle_tool_call(self, name: str, arguments: dict) -> str:
        """Handle a tool call.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            JSON string with results
        """
        try:
            if name == "create_code_context":
                return self._create_code_context(**arguments)
            elif name == "add_relevant_file":
                return self._add_relevant_file(**arguments)
            elif name == "add_file_dependency":
                return self._add_file_dependency(**arguments)
            elif name == "add_recent_change":
                return self._add_recent_change(**arguments)
            elif name == "add_known_issue":
                return self._add_known_issue(**arguments)
            elif name == "get_relevant_files":
                return self._get_relevant_files(**arguments)
            elif name == "get_file_dependencies":
                return self._get_file_dependencies(**arguments)
            elif name == "get_recent_changes":
                return self._get_recent_changes(**arguments)
            elif name == "get_known_issues":
                return self._get_known_issues(**arguments)
            elif name == "get_code_context":
                return self._get_code_context(**arguments)
            elif name == "refresh_code_context":
                return self._refresh_code_context(**arguments)
            elif name == "check_context_staleness":
                return self._check_context_staleness(**arguments)
            else:
                return '{"error": "Unknown tool"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _create_code_context(
        self,
        session_id: str,
        task_id: str = None,
        goal_id: str = None,
        architecture_notes: str = None,
        expires_in_hours: int = 24,
    ) -> str:
        """Create a new code context."""
        try:
            context_id = self.store.create_context(
                session_id=session_id,
                task_id=task_id,
                goal_id=goal_id,
                architecture_notes=architecture_notes,
                expires_in_hours=expires_in_hours,
            )
            return f'{{"status": "created", "context_id": {context_id}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _add_relevant_file(
        self,
        context_id: int,
        file_path: str,
        relevance: float = 0.5,
        role: str = "implementation",
        lines_changed: int = 0,
    ) -> str:
        """Add a relevant file to context."""
        try:
            self.store.add_relevant_file(
                context_id,
                file_path,
                relevance=relevance,
                role=FileRole(role),
                lines_changed=lines_changed,
            )
            return '{"status": "added"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _add_file_dependency(
        self,
        context_id: int,
        from_file: str,
        to_file: str,
        dependency_type: str,
        description: str = None,
        strength: float = 0.5,
    ) -> str:
        """Add a file dependency."""
        try:
            self.store.add_dependency(
                context_id,
                from_file,
                to_file,
                DependencyType(dependency_type),
                description=description,
                strength=strength,
            )
            return '{"status": "added"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _add_recent_change(
        self,
        context_id: int,
        file_path: str,
        change_summary: str,
        author: str = None,
        session_id: str = None,
    ) -> str:
        """Add a recent change."""
        try:
            self.store.add_recent_change(
                context_id,
                file_path,
                change_summary,
                author=author,
                session_id=session_id,
            )
            return '{"status": "added"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _add_known_issue(
        self,
        context_id: int,
        file_path: str,
        issue: str,
        severity: str,
        status: str = "open",
        resolution_notes: str = None,
    ) -> str:
        """Add a known issue."""
        try:
            self.store.add_known_issue(
                context_id,
                file_path,
                issue,
                IssueSeverity(severity),
                status=IssueStatus(status),
                resolution_notes=resolution_notes,
            )
            return '{"status": "added"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_relevant_files(self, context_id: int, min_relevance: float = 0.0) -> str:
        """Get relevant files."""
        try:
            files = self.store.get_relevant_files(context_id, min_relevance=min_relevance)
            return f'{{"count": {len(files)}, "files": {len(files)} files retrieved}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_file_dependencies(self, context_id: int, file_path: str = None) -> str:
        """Get file dependencies."""
        try:
            if file_path:
                deps = self.store.get_dependencies_for_file(context_id, file_path)
            else:
                deps = self.store.get_dependencies(context_id)
            return f'{{"count": {len(deps)}, "dependencies": {len(deps)} found}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_recent_changes(self, context_id: int, limit: int = 20) -> str:
        """Get recent changes."""
        try:
            changes = self.store.get_recent_changes(context_id, limit=limit)
            return f'{{"count": {len(changes)}, "recent": "{len(changes)} changes"}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_known_issues(self, context_id: int, status: str = None) -> str:
        """Get known issues."""
        try:
            status_filter = IssueStatus(status) if status else None
            issues = self.store.get_known_issues(context_id, status_filter=status_filter)
            return f'{{"count": {len(issues)}, "issues": {len(issues)} found}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _get_code_context(self, context_id: int = None, task_id: str = None) -> str:
        """Get code context."""
        try:
            if context_id:
                context = self.store.get_context(context_id)
            elif task_id:
                context = self.store.get_context_for_task(task_id)
            else:
                return '{"error": "Must provide context_id or task_id"}'

            if not context:
                return '{"error": "Context not found"}'

            return f'{{"status": "found", "context_id": {context.id}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _refresh_code_context(self, context_id: int, expires_in_hours: int = 24) -> str:
        """Refresh context expiration."""
        try:
            self.store.refresh_context(context_id, expires_in_hours=expires_in_hours)
            return '{"status": "refreshed"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _check_context_staleness(self, context_id: int) -> str:
        """Check if context is stale."""
        try:
            is_stale = self.store.is_context_stale(context_id)
            status = "stale" if is_stale else "fresh"
            return f'{{"status": "{status}", "is_stale": {str(is_stale).lower()}}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'
