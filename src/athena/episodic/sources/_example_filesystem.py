"""Example implementation of a filesystem event source.

This is a reference implementation showing how to:
1. Extend BaseEventSource
2. Implement required abstract methods
3. Support incremental sync with cursors
4. Register with EventSourceFactory

This example extracts git commits from a repository as episodic events.

Usage:
```python
from athena.episodic.sources import EventSourceFactory
from athena.episodic.sources._example_filesystem import FilesystemEventSource

# Create source
source = await FilesystemEventSource.create(
    credentials={},  # No auth needed for local filesystem
    config={
        'root_dir': '/path/to/repo',
        'branch': 'main',
        'max_commits': 100
    }
)

# Generate events
async for event in source.generate_events():
    print(f"Commit: {event.content}")
    print(f"Files changed: {event.files_changed}")
```

Note: This is an EXAMPLE only. Production implementation should be in:
    src/athena/episodic/sources/filesystem.py
"""

import logging
import os
import subprocess
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime

from ._base import BaseEventSource
from ..models import EpisodicEvent, EventType, EventOutcome, EventContext


class FilesystemEventSource(BaseEventSource):
    """Example filesystem event source for git commits.

    Extracts git commit history as episodic events with:
    - Commit message as content
    - Author, timestamp, files changed
    - Code diff for analysis
    - Incremental sync support (via commit SHA cursor)

    Configuration:
    ```python
    config = {
        'root_dir': '/path/to/repo',     # Git repository path (required)
        'branch': 'main',                # Branch to extract (default: 'main')
        'max_commits': 100,              # Max commits to extract (default: 100)
        'cursor': {                      # Optional: for incremental sync
            'last_commit_sha': 'abc123'
        }
    }
    ```
    """

    def __init__(
        self,
        source_id: str,
        root_dir: str,
        branch: str = 'main',
        max_commits: int = 100,
        cursor: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        project_id: int = 1
    ):
        """Initialize filesystem source.

        Args:
            source_id: Unique identifier
            root_dir: Path to git repository
            branch: Git branch to extract
            max_commits: Maximum commits to extract
            cursor: Optional cursor for incremental sync
            logger: Optional logger
            project_id: Project context ID (default: 1)
        """
        super().__init__(
            source_id=source_id,
            source_type='filesystem',
            source_name=f'Filesystem: {os.path.basename(root_dir)}',
            config={
                'root_dir': root_dir,
                'branch': branch,
                'max_commits': max_commits
            },
            logger=logger
        )

        self.root_dir = root_dir
        self.branch = branch
        self.max_commits = max_commits
        self.project_id = project_id

        # Cursor state for incremental sync
        self._cursor = cursor or {}
        self._last_commit_sha: Optional[str] = self._cursor.get('last_commit_sha')

    # ========================================================================
    # Required Abstract Methods
    # ========================================================================

    @classmethod
    async def create(
        cls,
        credentials: Dict[str, Any],
        config: Dict[str, Any]
    ) -> "FilesystemEventSource":
        """Factory method to create filesystem source.

        Args:
            credentials: Not used (filesystem has no auth)
            config: Configuration dict with:
                - root_dir: Path to git repository (required)
                - branch: Git branch (default: 'main')
                - max_commits: Max commits to extract (default: 100)
                - cursor: Optional cursor dict

        Returns:
            Initialized FilesystemEventSource

        Raises:
            ValueError: Invalid config (missing root_dir, not a git repo)
        """
        # Validate config
        root_dir = config.get('root_dir')
        if not root_dir:
            raise ValueError("Config must include 'root_dir'")

        if not os.path.isdir(root_dir):
            raise ValueError(f"root_dir not found: {root_dir}")

        if not os.path.isdir(os.path.join(root_dir, '.git')):
            raise ValueError(f"root_dir is not a git repository: {root_dir}")

        # Extract config
        branch = config.get('branch', 'main')
        max_commits = config.get('max_commits', 100)
        cursor = config.get('cursor')

        # Generate source_id from root_dir
        source_id = f"filesystem-{os.path.basename(root_dir)}"

        # Create instance
        return cls(
            source_id=source_id,
            root_dir=root_dir,
            branch=branch,
            max_commits=max_commits,
            cursor=cursor
        )

    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from git commit history.

        Extracts commits in reverse chronological order (newest first).
        If cursor is set, only extracts commits after the cursor.

        Yields:
            EpisodicEvent for each commit
        """
        self._logger.info(
            f"Generating events from {self.root_dir} "
            f"(branch={self.branch}, max={self.max_commits})"
        )

        # Get commit history
        commits = self._fetch_git_commits()

        for commit_data in commits:
            # Transform commit to event
            event = self._commit_to_event(commit_data)

            # Validate event
            if await self._validate_event(event):
                self._log_event_generated(event)

                # Update cursor
                self._last_commit_sha = commit_data['sha']

                yield event
            else:
                self._events_failed += 1

        self._logger.info(
            f"Generated {self._events_generated} events "
            f"({self._events_failed} failed)"
        )

    async def validate(self) -> bool:
        """Validate filesystem source.

        Checks:
        1. root_dir exists
        2. root_dir is a git repository
        3. branch exists
        """
        try:
            # Check directory exists
            if not os.path.isdir(self.root_dir):
                self._logger.error(f"Directory not found: {self.root_dir}")
                return False

            # Check is git repo
            git_dir = os.path.join(self.root_dir, '.git')
            if not os.path.isdir(git_dir):
                self._logger.error(f"Not a git repository: {self.root_dir}")
                return False

            # Check branch exists
            result = subprocess.run(
                ['git', 'rev-parse', '--verify', self.branch],
                cwd=self.root_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self._logger.error(f"Branch not found: {self.branch}")
                return False

            return True

        except Exception as e:
            self._logger.error(f"Validation failed: {e}")
            return False

    # ========================================================================
    # Incremental Sync Support
    # ========================================================================

    async def supports_incremental(self) -> bool:
        """Filesystem source supports incremental sync."""
        return True

    async def get_cursor(self) -> Optional[Dict[str, Any]]:
        """Get current cursor (last processed commit SHA)."""
        if self._last_commit_sha:
            return {
                'last_commit_sha': self._last_commit_sha,
                'branch': self.branch,
                'updated_at': datetime.now().isoformat()
            }
        return None

    async def set_cursor(self, cursor: Dict[str, Any]) -> None:
        """Set cursor (for resuming from a previous sync)."""
        self._cursor = cursor
        self._last_commit_sha = cursor.get('last_commit_sha')
        self._logger.info(f"Cursor set to commit: {self._last_commit_sha}")

    # ========================================================================
    # Git Operations (Private)
    # ========================================================================

    def _fetch_git_commits(self) -> List[Dict[str, Any]]:
        """Fetch git commit history.

        Returns:
            List of commit dicts with:
            - sha: Commit SHA
            - author: Author name
            - date: Commit timestamp
            - message: Commit message
            - files: List of changed files
            - stats: {insertions, deletions}
        """
        # Build git log command
        cmd = [
            'git', 'log',
            f'--max-count={self.max_commits}',
            '--format=%H|%an|%at|%s',  # SHA|author|timestamp|subject
            '--numstat',  # File stats
            self.branch
        ]

        # If cursor is set, only get commits after it
        if self._last_commit_sha:
            cmd.append(f'{self._last_commit_sha}..{self.branch}')

        # Run git log
        result = subprocess.run(
            cmd,
            cwd=self.root_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self._logger.error(f"Git log failed: {result.stderr}")
            return []

        # Parse output
        return self._parse_git_log(result.stdout)

    def _parse_git_log(self, output: str) -> List[Dict[str, Any]]:
        """Parse git log output into commit dicts.

        Args:
            output: Git log output

        Returns:
            List of commit dicts
        """
        commits = []
        current_commit = None

        for line in output.strip().split('\n'):
            if not line:
                continue

            # Check if this is a commit header line
            if '|' in line and len(line.split('|')) == 4:
                # Save previous commit
                if current_commit:
                    commits.append(current_commit)

                # Start new commit
                sha, author, timestamp, message = line.split('|', 3)
                current_commit = {
                    'sha': sha,
                    'author': author,
                    'date': datetime.fromtimestamp(int(timestamp)),
                    'message': message,
                    'files': [],
                    'insertions': 0,
                    'deletions': 0
                }
            elif current_commit and '\t' in line:
                # Parse file stats (insertions, deletions, filename)
                parts = line.split('\t')
                if len(parts) == 3:
                    insertions, deletions, filename = parts
                    current_commit['files'].append(filename)

                    # Update stats (handle '-' for binary files)
                    if insertions != '-':
                        current_commit['insertions'] += int(insertions)
                    if deletions != '-':
                        current_commit['deletions'] += int(deletions)

        # Add last commit
        if current_commit:
            commits.append(current_commit)

        return commits

    def _commit_to_event(self, commit_data: Dict[str, Any]) -> EpisodicEvent:
        """Transform git commit to EpisodicEvent.

        Args:
            commit_data: Commit dict from _fetch_git_commits

        Returns:
            EpisodicEvent instance
        """
        # Generate session ID from date (group commits by day)
        session_id = f"git-{commit_data['date'].strftime('%Y-%m-%d')}"

        # Create event context
        context = EventContext(
            cwd=self.root_dir,
            files=commit_data['files'],
            branch=self.branch
        )

        # Create event
        return EpisodicEvent(
            project_id=self.project_id,
            session_id=session_id,
            timestamp=commit_data['date'],
            event_type=EventType.FILE_CHANGE,
            content=f"Commit: {commit_data['message']}",
            outcome=EventOutcome.SUCCESS,
            context=context,
            files_changed=len(commit_data['files']),
            lines_added=commit_data['insertions'],
            lines_deleted=commit_data['deletions'],
            git_commit=commit_data['sha'],
            git_author=commit_data['author']
        )


# ========================================================================
# Auto-Register with Factory (Optional)
# ========================================================================

# Uncomment to auto-register when module is imported:
# from .factory import EventSourceFactory
# EventSourceFactory.register_source('filesystem', FilesystemEventSource)
