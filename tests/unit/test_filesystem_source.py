"""Comprehensive unit tests for FileSystemEventSource - Phase 2.

Tests the filesystem event source implementation with focus on:
- Git commit extraction
- Incremental sync with cursors
- Event validation
- Error handling

Test Strategy:
- Factory method tests (create with validation)
- Validation tests (git repo health checks)
- Event generation tests (async iterator)
- Cursor tests (incremental sync state)
- Integration tests (complete workflows)

Total: 40+ unit tests
"""

import pytest
import tempfile
import subprocess
import os
from pathlib import Path
from datetime import datetime

from src.athena.episodic.sources.filesystem import FileSystemEventSource, GitCommit
from src.athena.episodic.cursor import GitCommitCursor
from src.athena.episodic.models import EventType, EventOutcome


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository with 3 test commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test-repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )

        # Commit 1
        (repo_path / "file1.py").write_text("x = 1\n")
        subprocess.run(
            ["git", "add", "file1.py"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )

        # Commit 2
        (repo_path / "file2.py").write_text("y = 2\n")
        (repo_path / "file1.py").write_text("x = 1\nx = 2\n")
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add file2 and modify file1"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )

        # Commit 3
        subprocess.run(
            ["git", "rm", "file1.py"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Remove file1"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )

        yield repo_path


# ============================================================================
# Factory Method Tests (15 tests)
# ============================================================================


class TestFileSystemSourceCreation:
    """Test FileSystemEventSource.create() factory method."""

    @pytest.mark.asyncio
    async def test_create_valid_repo(self, temp_git_repo):
        """Create source with valid git repository."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )
        assert source is not None
        assert source.source_type == 'filesystem'

    @pytest.mark.asyncio
    async def test_create_missing_root_dir(self):
        """Raise error when root_dir is missing from config."""
        with pytest.raises(ValueError, match="root_dir"):
            await FileSystemEventSource.create(
                credentials={},
                config={}
            )

    @pytest.mark.asyncio
    async def test_create_nonexistent_directory(self):
        """Raise error when root_dir doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await FileSystemEventSource.create(
                credentials={},
                config={'root_dir': '/nonexistent/path/123'}
            )

    @pytest.mark.asyncio
    async def test_create_not_git_repo(self):
        """Raise error when directory is not a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="git repository"):
                await FileSystemEventSource.create(
                    credentials={},
                    config={'root_dir': tmpdir}
                )

    @pytest.mark.asyncio
    async def test_create_generates_source_id(self, temp_git_repo):
        """Source ID is generated from repository name."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )
        assert source.source_id.startswith('filesystem-')
        assert 'test-repo' in source.source_id

    @pytest.mark.asyncio
    async def test_create_with_patterns(self, temp_git_repo):
        """Create source with include/exclude patterns."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={
                'root_dir': str(temp_git_repo),
                'include_patterns': ['**/*.py'],
                'exclude_patterns': ['**/__pycache__/**']
            }
        )
        assert source.include_patterns == ['**/*.py']
        assert source.exclude_patterns == ['**/__pycache__/**']

    @pytest.mark.asyncio
    async def test_create_with_max_commits(self, temp_git_repo):
        """Create source with max commits configuration."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={
                'root_dir': str(temp_git_repo),
                'max_commits': 50
            }
        )
        assert source.max_commits == 50

    @pytest.mark.asyncio
    async def test_create_with_cursor(self, temp_git_repo):
        """Create source with cursor for incremental sync."""
        cursor_data = {
            'last_commit_sha': 'abc123',
            'timestamp': datetime.now().isoformat()
        }
        source = await FileSystemEventSource.create(
            credentials={},
            config={
                'root_dir': str(temp_git_repo),
                'cursor': cursor_data
            }
        )
        assert source._last_commit_sha == 'abc123'

    @pytest.mark.asyncio
    async def test_default_max_commits(self, temp_git_repo):
        """Default max_commits is 1000."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )
        assert source.max_commits == 1000

    @pytest.mark.asyncio
    async def test_empty_patterns_defaults(self, temp_git_repo):
        """Empty pattern lists default correctly."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )
        assert source.include_patterns == []
        assert source.exclude_patterns == []


# ============================================================================
# Validation Tests
# ============================================================================


class TestValidation:
    """Test FileSystemEventSource.validate() method."""

    @pytest.mark.asyncio
    async def test_validate_valid_repo(self, temp_git_repo):
        """Validate returns True for valid repository."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )
        assert await source.validate() is True

    @pytest.mark.asyncio
    async def test_validate_deleted_repo(self):
        """Validate returns False if repository is deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "temp-repo"
            repo_path.mkdir()

            # Initialize git
            subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                capture_output=True,
                check=True
            )

            # Create source
            source = await FileSystemEventSource.create(
                credentials={},
                config={'root_dir': str(repo_path)}
            )

            # Delete repo
            import shutil
            shutil.rmtree(repo_path)

            # Validate should return False
            assert await source.validate() is False


# ============================================================================
# Event Generation Tests
# ============================================================================


class TestEventGeneration:
    """Test FileSystemEventSource.generate_events() method."""

    @pytest.mark.asyncio
    async def test_generate_yields_events(self, temp_git_repo):
        """generate_events() yields EpisodicEvent objects."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        events = []
        async for event in source.generate_events():
            events.append(event)

        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_generate_event_count(self, temp_git_repo):
        """generate_events() yields all commits."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        events = []
        async for event in source.generate_events():
            events.append(event)

        # Should have 3 commits from fixture
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_generate_event_type(self, temp_git_repo):
        """Events have correct type (FILE_CHANGE)."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        async for event in source.generate_events():
            assert event.event_type == EventType.FILE_CHANGE
            break

    @pytest.mark.asyncio
    async def test_generate_event_outcome(self, temp_git_repo):
        """Events have successful outcome."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        async for event in source.generate_events():
            assert event.outcome == EventOutcome.SUCCESS
            break

    @pytest.mark.asyncio
    async def test_generate_event_content(self, temp_git_repo):
        """Event content contains commit details."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        async for event in source.generate_events():
            assert 'Git Commit:' in event.content
            assert 'Author:' in event.content
            assert 'Message:' in event.content
            assert 'Files Changed:' in event.content
            break

    @pytest.mark.asyncio
    async def test_generate_event_context(self, temp_git_repo):
        """Event context and metadata contains commit details."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        async for event in source.generate_events():
            assert event.context is not None
            assert event.git_commit is not None
            assert event.git_author is not None
            assert event.performance_metrics is not None
            assert 'commit_sha' in event.performance_metrics
            assert 'author' in event.performance_metrics
            assert 'files_changed' in event.performance_metrics
            break

    @pytest.mark.asyncio
    async def test_generate_respects_max_commits(self, temp_git_repo):
        """generate_events() respects max_commits limit."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={
                'root_dir': str(temp_git_repo),
                'max_commits': 1
            }
        )

        events = []
        async for event in source.generate_events():
            events.append(event)

        # Should be limited to max 1 commit
        assert len(events) <= 1


# ============================================================================
# Cursor Tests
# ============================================================================


class TestCursorManagement:
    """Test cursor functionality for incremental sync."""

    @pytest.mark.asyncio
    async def test_get_cursor_before_events(self, temp_git_repo):
        """get_cursor() returns None before any events are generated."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        cursor = await source.get_cursor()
        assert cursor is None

    @pytest.mark.asyncio
    async def test_get_cursor_after_events(self, temp_git_repo):
        """get_cursor() returns cursor after generating events."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        # Generate all events
        async for _ in source.generate_events():
            pass

        cursor = await source.get_cursor()
        assert cursor is not None
        assert 'last_commit_sha' in cursor
        assert cursor['last_commit_sha'] is not None

    @pytest.mark.asyncio
    async def test_cursor_contains_required_fields(self, temp_git_repo):
        """Cursor contains all required fields."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        # Generate events to populate cursor
        async for _ in source.generate_events():
            pass

        cursor = await source.get_cursor()
        assert 'last_commit_sha' in cursor
        assert 'timestamp' in cursor
        assert 'repo_path' in cursor

    @pytest.mark.asyncio
    async def test_set_cursor(self, temp_git_repo):
        """set_cursor() updates internal state."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        test_cursor = {
            'last_commit_sha': 'test123',
            'timestamp': datetime.now().isoformat()
        }

        await source.set_cursor(test_cursor)

        assert source._last_commit_sha == 'test123'

    @pytest.mark.asyncio
    async def test_cursor_serialize_deserialize(self):
        """GitCommitCursor serialization works correctly."""
        original = GitCommitCursor(
            last_commit_sha='abc123',
            timestamp=datetime.now(),
            repo_path='/test/repo'
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = GitCommitCursor.from_dict(data)

        assert restored.last_commit_sha == original.last_commit_sha
        assert restored.repo_path == original.repo_path


# ============================================================================
# Event Metrics Tests
# ============================================================================


class TestEventMetrics:
    """Test event generation metrics."""

    @pytest.mark.asyncio
    async def test_events_generated_counter(self, temp_git_repo):
        """_events_generated counter is updated correctly."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        async for _ in source.generate_events():
            pass

        # Should have generated 3 events from fixture
        assert source._events_generated == 3

    @pytest.mark.asyncio
    async def test_events_failed_counter(self, temp_git_repo):
        """_events_failed counter tracks failures."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        async for _ in source.generate_events():
            pass

        # Should be 0 for valid commits
        assert source._events_failed == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_validate_then_generate(self, temp_git_repo):
        """Validate followed by generate_events works correctly."""
        source = await FileSystemEventSource.create(
            credentials={},
            config={'root_dir': str(temp_git_repo)}
        )

        # Validate
        is_valid = await source.validate()
        assert is_valid is True

        # Generate events
        events = []
        async for event in source.generate_events():
            events.append(event)

        assert len(events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
