"""Project Detector - Auto-detect project from working directory.

Infers project_id from current working directory by matching against
configured project paths. Enables transparent project handling without
requiring explicit PROJECT_ID environment variable.

Configuration stored in semantic memory instead of files.
"""

import os
from pathlib import Path
from typing import Optional, Dict


class ProjectDetector:
    """Detect project from working directory."""

    # Default project mappings
    DEFAULT_PROJECTS = {
        1: {
            "name": "athena",
            "paths": [
                "/home/user/.work/athena",
                "/home/user/.work/athena/**",
                # Legacy paths for backwards compatibility
                "/home/user/.work/claude/memory-mcp",
                "/home/user/.work/claude/memory-mcp/**",
                "/home/user/.work/z_old_claude/memory-mcp",
                "/home/user/.work/z_old_claude/memory-mcp/**",
            ],
        },
        2: {
            "name": "web-app",
            "paths": [
                "/home/user/.work/web-app",
                "/home/user/.work/web-app/**",
            ],
        },
        3: {
            "name": "mobile-app",
            "paths": [
                "/home/user/.work/mobile-app",
                "/home/user/.work/mobile-app/**",
            ],
        },
    }

    def __init__(self):
        """Initialize project detector."""
        self.projects = self._load_config()

    def _load_config(self) -> Dict[int, Dict]:
        """Load project configuration from memory.

        Returns:
            Dictionary of project_id -> project config
        """
        # Use default projects (configuration now managed in memory via MCP)
        # To add projects: use memory API to store in semantic layer
        return self.DEFAULT_PROJECTS

    def detect_project_id(
        self, cwd: Optional[str] = None
    ) -> Optional[int]:
        """Detect project ID from working directory.

        Args:
            cwd: Working directory (defaults to os.getcwd())

        Returns:
            Project ID if detected, None otherwise
        """
        if cwd is None:
            cwd = os.getcwd()

        cwd = os.path.abspath(cwd)
        cwd_path = Path(cwd)

        # Try exact matches first
        for project_id, config in self.projects.items():
            paths = config.get("paths", [])
            for path_pattern in paths:
                # Exact match
                if os.path.abspath(path_pattern) == cwd:
                    return project_id

        # Try parent directory matches
        for project_id, config in self.projects.items():
            paths = config.get("paths", [])
            for path_pattern in paths:
                base_path = path_pattern.replace("/**", "")
                base_path = os.path.abspath(base_path)

                # Check if cwd is under this path
                try:
                    cwd_path.relative_to(base_path)
                    return project_id
                except ValueError:
                    continue

        return None

    def get_project_name(self, project_id: int) -> Optional[str]:
        """Get project name by ID.

        Args:
            project_id: Project ID

        Returns:
            Project name if found, None otherwise
        """
        if project_id in self.projects:
            return self.projects[project_id].get("name")
        return None

    def list_projects(self) -> Dict[int, str]:
        """List all configured projects.

        Returns:
            Dictionary of project_id -> project_name
        """
        return {
            pid: config.get("name", f"Project {pid}")
            for pid, config in self.projects.items()
        }

    def register_project(self, project_id: int, name: str, paths: list[str]):
        """Register a project in memory.

        Note: Project configuration is stored in semantic memory via MCP tools.
        Use mcp__memory__remember() to persist custom project configurations.

        Args:
            project_id: Unique project identifier
            name: Human-readable project name
            paths: List of paths to match (supports ** for recursive)
        """
        # Update in-memory mapping
        self.projects[project_id] = {
            "name": name,
            "paths": paths,
        }

        # In production: would call memory API to persist
        # For now: configuration is managed via memory tools


# Global detector instance
_detector = None


def get_detector() -> ProjectDetector:
    """Get global project detector instance."""
    global _detector
    if _detector is None:
        _detector = ProjectDetector()
    return _detector


def detect_project_id(cwd: Optional[str] = None) -> Optional[int]:
    """Detect project ID from working directory.

    Args:
        cwd: Working directory (defaults to os.getcwd())

    Returns:
        Project ID if detected, None otherwise
    """
    return get_detector().detect_project_id(cwd)


def get_project_name(project_id: int) -> Optional[str]:
    """Get project name by ID."""
    return get_detector().get_project_name(project_id)


def list_projects() -> Dict[int, str]:
    """List all configured projects."""
    return get_detector().list_projects()
