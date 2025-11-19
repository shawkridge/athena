"""Project detection and management."""

import os
from pathlib import Path
from typing import Optional

from ..core.models import Project
from ..core.async_utils import run_async
from ..semantic import SemanticStore


class ProjectManager:
    """Manage project detection and context."""

    def __init__(self, store: SemanticStore):
        """Initialize project manager.

        Args:
            store: Memory store instance
        """
        self.store = store
        self._current_project: Optional[Project] = None

    async def detect_current_project(self) -> Optional[Project]:
        """Detect current project from working directory.

        Returns:
            Current project if detected, None otherwise
        """
        cwd = os.getcwd()
        project = await self.store.get_project_by_path(cwd)

        if project:
            self.store.db.update_project_access(project.id)
            self._current_project = project

        return project

    async def get_or_create_project(self, name: Optional[str] = None) -> Project:
        """Get current project or create if doesn't exist.

        Args:
            name: Optional project name (defaults to directory name)

        Returns:
            Current or newly created project
        """
        cwd = os.getcwd()
        project = await self.store.get_project_by_path(cwd)

        if project:
            self._current_project = project
            return project

        # Create new project
        if not name:
            name = Path(cwd).name

        project = await self.store.create_project(name, cwd)
        self._current_project = project
        return project

    @property
    def current_project(self) -> Optional[Project]:
        """Get currently active project."""
        return self._current_project

    async def require_project(self) -> Project:
        """Get current project or raise error.

        Returns:
            Current project

        Raises:
            RuntimeError: If no project is active
        """
        if not self._current_project:
            self._current_project = await self.detect_current_project()

        if not self._current_project:
            raise RuntimeError(
                "No project detected. Run from a project directory or register one first."
            )

        return self._current_project

    # Sync wrappers for async methods (Phase 2: Executable Procedures)
    def detect_current_project_sync(self) -> Optional[Project]:
        """Synchronous wrapper for detect_current_project().

        Detect current project from working directory in sync context.

        Returns:
            Current project if detected, None otherwise
        """
        coro = self.detect_current_project()
        return run_async(coro)

    def get_or_create_project_sync(self, name: Optional[str] = None) -> Project:
        """Synchronous wrapper for get_or_create_project().

        Get current project or create if doesn't exist in sync context.

        Args:
            name: Optional project name (defaults to directory name)

        Returns:
            Current or newly created project
        """
        coro = self.get_or_create_project(name)
        return run_async(coro)

    def require_project_sync(self) -> Project:
        """Synchronous wrapper for require_project().

        Get current project or raise error in sync context.

        Returns:
            Current project

        Raises:
            RuntimeError: If no project is active
        """
        coro = self.require_project()
        return run_async(coro)
