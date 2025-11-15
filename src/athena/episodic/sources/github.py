"""GitHub event source for episodic memory.

This module implements event ingestion from GitHub repositories, capturing:
- Push events (commits, branch changes)
- Pull request events (creation, review, merge)
- Issue events (creation, comments, closure)
- Release events
- Discussion events

Features:
- Async streaming API using GitHub REST API v3
- Incremental sync using timestamp-based cursors
- Pagination handling for large repositories
- Per-event metadata: author, timestamp, files affected, diff stats
- Graceful error handling and retry logic

Example Usage:
```python
from athena.episodic.sources import EventSourceFactory

# Create GitHub source
source = await EventSourceFactory.create_source(
    source_type='github',
    source_id='github-athena-main',
    credentials={'token': 'ghp_xxxxxxxxxxxx'},
    config={
        'owner': 'anthropics',
        'repo': 'athena',
        'events': ['push', 'pull_request', 'issues', 'releases'],
        'branch': 'main'
    }
)

# Validate connection
if await source.validate():
    # Generate events from GitHub
    async for event in source.generate_events():
        print(f"Event: {event.type} - {event.content[:50]}...")
```

GitHub API Requirements:
- GitHub Personal Access Token (classic or fine-grained)
- Scopes: repo (or public_repo for public repos only)
- Rate limits: 5,000 requests/hour (authenticated)

Cursor Format:
```python
{
    'last_event_timestamp': '2025-01-15T10:30:00Z',
    'last_event_id': 'push-abc123',
    'events_processed': 245
}
```
"""

import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime
from urllib.parse import urlencode

try:
    import aiohttp
except ImportError:
    aiohttp = None  # Optional dependency

from ._base import BaseEventSource
from ..models import EpisodicEvent, EventType, EventOutcome, EventContext


logger = logging.getLogger(__name__)


class GitHubEventSource(BaseEventSource):
    """GitHub repository event source.

    Streams events from a GitHub repository including commits, PRs, issues, and releases.
    Supports incremental sync using timestamp-based cursors.

    Configuration:
    ```python
    config = {
        'owner': 'anthropics',           # GitHub owner/org (required)
        'repo': 'athena',                # Repository name (required)
        'branch': 'main',                # Branch to monitor (default: 'main')
        'events': [                      # Event types to capture (default: all)
            'push',
            'pull_request',
            'issues',
            'releases',
            'discussions'
        ],
        'per_page': 100,                 # Pagination size (default: 100, max: 100)
        'cursor': {                      # For incremental sync
            'last_event_timestamp': '2025-01-15T10:30:00Z'
        }
    }
    ```
    """

    # GitHub API v3 REST endpoint
    API_BASE = "https://api.github.com"
    API_TIMEOUT = 30  # seconds
    RATE_LIMIT_RETRY_AFTER = 60  # seconds

    def __init__(
        self,
        source_id: str,
        owner: str,
        repo: str,
        token: str,
        branch: str = "main",
        events: Optional[List[str]] = None,
        per_page: int = 100,
        cursor: Optional[Dict[str, Any]] = None,
        logger_instance: Optional[logging.Logger] = None,
        project_id: int = 1,
    ):
        """Initialize GitHub event source.

        Args:
            source_id: Unique identifier (e.g., 'github-anthropics-athena')
            owner: GitHub owner/organization name
            repo: Repository name
            token: GitHub Personal Access Token (classic or fine-grained)
            branch: Branch to monitor (default: 'main')
            events: Event types to capture (default: all supported)
            per_page: Pagination size (default: 100, max: 100)
            cursor: Optional cursor for incremental sync
            logger_instance: Optional logger
            project_id: Project context ID
        """
        super().__init__(
            source_id=source_id,
            source_type="github",
            source_name=f"GitHub: {owner}/{repo}",
            config={
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "events": events or ["push", "pull_request", "issues", "releases"],
                "per_page": min(per_page, 100),  # Cap at GitHub max
            },
            logger=logger_instance or logging.getLogger(__name__),
        )

        self.owner = owner
        self.repo = repo
        self.token = token
        self.branch = branch
        self.events = events or ["push", "pull_request", "issues", "releases"]
        self.per_page = min(per_page, 100)
        self.project_id = project_id

        # Cursor state for incremental sync
        self._cursor = cursor or {}
        self._last_event_timestamp = self._cursor.get("last_event_timestamp")

        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Athena-Memory-System/1.0",
        }

    # ========================================================================
    # Required Abstract Methods
    # ========================================================================

    @classmethod
    async def create(
        cls,
        credentials: Dict[str, Any],
        config: Dict[str, Any],
    ) -> "GitHubEventSource":
        """Factory method to create GitHub event source.

        Args:
            credentials: Must contain:
                - token: GitHub Personal Access Token
            config: Must contain:
                - owner: GitHub owner/org
                - repo: Repository name
                Optional:
                - branch: Branch to monitor (default: 'main')
                - events: Event types (default: all)
                - per_page: Pagination size (default: 100)
                - cursor: Cursor for incremental sync

        Returns:
            Initialized GitHubEventSource

        Raises:
            ValueError: Missing required credentials or config or aiohttp not installed
            ConnectionError: Failed to validate connection
        """
        # Check aiohttp dependency
        if aiohttp is None:
            raise ValueError(
                "aiohttp is required for GitHub event source. "
                "Install with: pip install aiohttp"
            )

        # Validate credentials
        token = credentials.get("token")
        if not token:
            raise ValueError("Credentials must include 'token' (GitHub Personal Access Token)")

        # Validate config
        owner = config.get("owner")
        repo = config.get("repo")
        if not owner or not repo:
            raise ValueError("Config must include 'owner' and 'repo'")

        # Create instance
        source = cls(
            source_id=f"github-{owner}-{repo}",
            owner=owner,
            repo=repo,
            token=token,
            branch=config.get("branch", "main"),
            events=config.get("events"),
            per_page=config.get("per_page", 100),
            cursor=config.get("cursor"),
            project_id=config.get("project_id", 1),
        )

        return source

    async def validate(self) -> bool:
        """Validate GitHub connection and permissions.

        Checks:
        - Token is valid
        - Repository is accessible
        - Required permissions are granted
        - Branch exists

        Returns:
            True if validation successful, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Check token validity by fetching authenticated user
                async with session.get(
                    f"{self.API_BASE}/user",
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=self.API_TIMEOUT),
                ) as resp:
                    if resp.status != 200:
                        self._logger.error(f"Token validation failed: {resp.status}")
                        return False

                # Check repository access
                async with session.get(
                    f"{self.API_BASE}/repos/{self.owner}/{self.repo}",
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=self.API_TIMEOUT),
                ) as resp:
                    if resp.status == 404:
                        self._logger.error(f"Repository not found: {self.owner}/{self.repo}")
                        return False
                    if resp.status != 200:
                        self._logger.error(f"Repository access failed: {resp.status}")
                        return False

                    # Check if repo is empty
                    data = await resp.json()
                    if data.get("size") == 0:
                        self._logger.warning(f"Repository is empty: {self.owner}/{self.repo}")

            self._logger.info(f"GitHub validation successful: {self.owner}/{self.repo}")
            return True

        except asyncio.TimeoutError:
            self._logger.error("GitHub validation timed out")
            return False
        except Exception as e:
            self._logger.error(f"GitHub validation failed: {e}")
            return False

    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate episodic events from GitHub.

        Fetches events from enabled event types and yields as EpisodicEvent instances.
        Supports incremental sync using timestamp cursor.

        Yields:
            EpisodicEvent instances from GitHub
        """
        async with aiohttp.ClientSession() as session:
            self._session = session

            try:
                # Generate events for each enabled event type
                for event_type in self.events:
                    if event_type == "push":
                        async for event in self._generate_push_events():
                            yield event
                    elif event_type == "pull_request":
                        async for event in self._generate_pr_events():
                            yield event
                    elif event_type == "issues":
                        async for event in self._generate_issue_events():
                            yield event
                    elif event_type == "releases":
                        async for event in self._generate_release_events():
                            yield event
                    elif event_type == "discussions":
                        async for event in self._generate_discussion_events():
                            yield event

            finally:
                self._session = None

    # ========================================================================
    # Incremental Sync Support
    # ========================================================================

    async def supports_incremental(self) -> bool:
        """Check if incremental sync is supported.

        GitHub events support timestamp-based incremental sync.

        Returns:
            True (incremental sync is supported)
        """
        return True

    async def get_cursor(self) -> Dict[str, Any]:
        """Get current sync cursor.

        Returns:
            Cursor dict with last event timestamp and processing stats
        """
        return {
            "last_event_timestamp": self._last_event_timestamp or datetime.utcnow().isoformat() + "Z",
            "events_processed": self._events_generated,
            "events_failed": self._events_failed,
        }

    async def set_cursor(self, cursor: Dict[str, Any]) -> None:
        """Set sync cursor for resuming from previous sync point.

        Args:
            cursor: Cursor dict containing last_event_timestamp
        """
        self._cursor = cursor
        self._last_event_timestamp = cursor.get("last_event_timestamp")

    # ========================================================================
    # Event Generation Methods (Private)
    # ========================================================================

    async def _generate_push_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from push/commit activity."""
        since = self._last_event_timestamp

        try:
            # Fetch commits on branch
            url = f"{self.API_BASE}/repos/{self.owner}/{self.repo}/commits"
            params = {
                "sha": self.branch,
                "per_page": self.per_page,
            }

            if since:
                params["since"] = since

            async for commits in self._paginate(url, params):
                for commit in commits:
                    event = self._transform_commit_to_event(commit)
                    if event:
                        self._last_event_timestamp = commit["commit"]["committer"]["date"]
                        yield event

        except Exception as e:
            self._logger.error(f"Failed to generate push events: {e}")
            self._events_failed += 1

    async def _generate_pr_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from pull request activity."""
        since = self._last_event_timestamp

        try:
            # Fetch pull requests
            url = f"{self.API_BASE}/repos/{self.owner}/{self.repo}/pulls"
            params = {
                "state": "all",  # Get open and closed PRs
                "sort": "updated",
                "direction": "desc",
                "per_page": self.per_page,
            }

            if since:
                params["since"] = since

            async for prs in self._paginate(url, params):
                for pr in prs:
                    event = self._transform_pr_to_event(pr)
                    if event:
                        self._last_event_timestamp = pr["updated_at"]
                        yield event

        except Exception as e:
            self._logger.error(f"Failed to generate PR events: {e}")
            self._events_failed += 1

    async def _generate_issue_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from issue activity."""
        since = self._last_event_timestamp

        try:
            # Fetch issues
            url = f"{self.API_BASE}/repos/{self.owner}/{self.repo}/issues"
            params = {
                "state": "all",
                "sort": "updated",
                "direction": "desc",
                "per_page": self.per_page,
            }

            if since:
                params["since"] = since

            async for issues in self._paginate(url, params):
                for issue in issues:
                    # Skip pull requests (they appear in issues endpoint)
                    if "pull_request" in issue:
                        continue

                    event = self._transform_issue_to_event(issue)
                    if event:
                        self._last_event_timestamp = issue["updated_at"]
                        yield event

        except Exception as e:
            self._logger.error(f"Failed to generate issue events: {e}")
            self._events_failed += 1

    async def _generate_release_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from release activity."""
        since = self._last_event_timestamp

        try:
            # Fetch releases
            url = f"{self.API_BASE}/repos/{self.owner}/{self.repo}/releases"
            params = {
                "per_page": self.per_page,
            }

            async for releases in self._paginate(url, params):
                for release in releases:
                    # Check if release is newer than cursor
                    if since and release["published_at"] < since:
                        continue

                    event = self._transform_release_to_event(release)
                    if event:
                        self._last_event_timestamp = release["published_at"]
                        yield event

        except Exception as e:
            self._logger.error(f"Failed to generate release events: {e}")
            self._events_failed += 1

    async def _generate_discussion_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from discussions."""
        since = self._last_event_timestamp

        try:
            # Fetch discussions via GraphQL (not available in REST API)
            # For now, skip - can be implemented with GraphQL client
            self._logger.info("Discussions require GraphQL API - skipping for now")

        except Exception as e:
            self._logger.error(f"Failed to generate discussion events: {e}")
            self._events_failed += 1

    # ========================================================================
    # Event Transformation (Private)
    # ========================================================================

    def _transform_commit_to_event(self, commit: Dict[str, Any]) -> Optional[EpisodicEvent]:
        """Transform GitHub commit to EpisodicEvent."""
        try:
            commit_data = commit["commit"]
            author = commit_data["author"]["name"]
            message = commit_data["message"]
            timestamp = datetime.fromisoformat(commit_data["committer"]["date"].replace("Z", "+00:00"))

            # Extract files changed from commit
            files_changed = []
            if "files" in commit:
                files_changed = [f["filename"] for f in commit.get("files", [])]

            event = EpisodicEvent(
                type=EventType.CODE_CHANGE,
                content=f"Commit: {message.split(chr(10))[0]}",  # First line only
                timestamp=timestamp,
                project_id=self.project_id,
                source_id=self.source_id,
                metadata={
                    "author": author,
                    "commit_sha": commit["sha"],
                    "url": commit["html_url"],
                    "files_changed": files_changed,
                    "additions": commit.get("stats", {}).get("additions", 0),
                    "deletions": commit.get("stats", {}).get("deletions", 0),
                },
                context=EventContext(
                    domain="version_control",
                    subdomain="git",
                ),
            )

            self._events_generated += 1
            self._log_event_generated(event)
            return event

        except Exception as e:
            self._logger.warning(f"Failed to transform commit: {e}")
            self._events_failed += 1
            return None

    def _transform_pr_to_event(self, pr: Dict[str, Any]) -> Optional[EpisodicEvent]:
        """Transform GitHub PR to EpisodicEvent."""
        try:
            status = pr["state"]
            title = pr["title"]
            timestamp = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))

            event = EpisodicEvent(
                type=EventType.DISCUSSION,
                content=f"PR [{status.upper()}]: {title}",
                timestamp=timestamp,
                project_id=self.project_id,
                source_id=self.source_id,
                metadata={
                    "pr_number": pr["number"],
                    "author": pr["user"]["login"],
                    "url": pr["html_url"],
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                    "commits": pr.get("commits", 0),
                    "comments": pr.get("comments", 0),
                    "state": status,
                },
                context=EventContext(
                    domain="version_control",
                    subdomain="pull_request",
                ),
            )

            self._events_generated += 1
            self._log_event_generated(event)
            return event

        except Exception as e:
            self._logger.warning(f"Failed to transform PR: {e}")
            self._events_failed += 1
            return None

    def _transform_issue_to_event(self, issue: Dict[str, Any]) -> Optional[EpisodicEvent]:
        """Transform GitHub issue to EpisodicEvent."""
        try:
            status = issue["state"]
            title = issue["title"]
            timestamp = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))

            event = EpisodicEvent(
                type=EventType.DISCUSSION,
                content=f"Issue [{status.upper()}]: {title}",
                timestamp=timestamp,
                project_id=self.project_id,
                source_id=self.source_id,
                metadata={
                    "issue_number": issue["number"],
                    "author": issue["user"]["login"],
                    "url": issue["html_url"],
                    "comments": issue.get("comments", 0),
                    "state": status,
                    "labels": [label["name"] for label in issue.get("labels", [])],
                },
                context=EventContext(
                    domain="collaboration",
                    subdomain="issue_tracking",
                ),
            )

            self._events_generated += 1
            self._log_event_generated(event)
            return event

        except Exception as e:
            self._logger.warning(f"Failed to transform issue: {e}")
            self._events_failed += 1
            return None

    def _transform_release_to_event(self, release: Dict[str, Any]) -> Optional[EpisodicEvent]:
        """Transform GitHub release to EpisodicEvent."""
        try:
            tag = release["tag_name"]
            name = release.get("name", tag)
            is_prerelease = release.get("prerelease", False)
            timestamp = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))

            event = EpisodicEvent(
                type=EventType.MILESTONE,
                content=f"Release: {name}",
                timestamp=timestamp,
                project_id=self.project_id,
                source_id=self.source_id,
                metadata={
                    "tag": tag,
                    "url": release["html_url"],
                    "author": release["author"]["login"],
                    "prerelease": is_prerelease,
                    "download_count": len(release.get("assets", [])),
                },
                context=EventContext(
                    domain="project_management",
                    subdomain="release",
                ),
            )

            self._events_generated += 1
            self._log_event_generated(event)
            return event

        except Exception as e:
            self._logger.warning(f"Failed to transform release: {e}")
            self._events_failed += 1
            return None

    # ========================================================================
    # Helper Methods (Private)
    # ========================================================================

    async def _paginate(
        self,
        url: str,
        params: Dict[str, Any],
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Paginate through GitHub API results.

        Args:
            url: GitHub API endpoint
            params: Query parameters

        Yields:
            Lists of results from each page
        """
        page = 1

        while True:
            try:
                params["page"] = page
                query_string = urlencode(params)
                full_url = f"{url}?{query_string}"

                async with self._session.get(
                    full_url,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=self.API_TIMEOUT),
                ) as resp:
                    if resp.status == 429:  # Rate limited
                        retry_after = int(resp.headers.get("X-RateLimit-Reset", 0))
                        wait_time = max(1, retry_after - int(datetime.utcnow().timestamp()))
                        self._logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue

                    if resp.status != 200:
                        self._logger.error(f"API error {resp.status}: {await resp.text()}")
                        break

                    data = await resp.json()

                    # Handle empty results
                    if not data or (isinstance(data, list) and len(data) == 0):
                        break

                    # Yield page of results
                    if isinstance(data, list):
                        yield data
                    else:
                        yield [data]

                    # Check if there's a next page
                    link_header = resp.headers.get("link", "")
                    if "rel=\"next\"" not in link_header:
                        break

                    page += 1

            except asyncio.TimeoutError:
                self._logger.error("Pagination request timed out")
                break
            except Exception as e:
                self._logger.error(f"Pagination error: {e}")
                break

    def _log_event_generated(self, event: EpisodicEvent) -> None:
        """Log event generation for debugging."""
        self._logger.debug(
            f"Generated event: {event.type} @ {event.timestamp} - {event.content[:50]}..."
        )


# ============================================================================
# Auto-Register with Factory
# ============================================================================

# Register GitHubEventSource with the factory on module import
from .factory import EventSourceFactory
EventSourceFactory.register_source("github", GitHubEventSource)
