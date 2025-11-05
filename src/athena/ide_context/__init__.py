"""IDE context integration - tracking editor state, cursor position, and git changes."""

from .api import IDEContextAPI
from .git_tracker import GitTracker
from .manager import IDEContextManager
from .models import (
    CursorPosition,
    FileOpenMode,
    GitChangeType,
    GitDiff,
    GitStatus,
    IDEActivity,
    IDEContextSnapshot,
    IDEFile,
)
from .store import IDEContextStore

__all__ = [
    "IDEContextAPI",
    "IDEContextManager",
    "IDEContextStore",
    "GitTracker",
    "IDEFile",
    "CursorPosition",
    "GitStatus",
    "GitDiff",
    "IDEContextSnapshot",
    "IDEActivity",
    "FileOpenMode",
    "GitChangeType",
]
