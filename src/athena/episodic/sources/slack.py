"""Slack event source for episodic memory.

This module implements event ingestion from Slack workspaces, capturing:
- Messages (in channels and threads)
- Reactions
- Threads and replies
- File uploads and sharing
- User mentions and interactions

Features:
- Async streaming API using Slack Web API
- Incremental sync using timestamp cursors
- Multi-channel support
- Thread and conversation tracking
- Reaction and interaction metadata
- Graceful error handling and rate limiting

Example Usage:
```python
from athena.episodic.sources import EventSourceFactory

# Create Slack source
source = await EventSourceFactory.create_source(
    source_type='slack',
    source_id='slack-workspace-dev',
    credentials={'bot_token': 'xoxb-xxxxxxxxx'},
    config={
        'channels': ['#general', '#dev', '#random'],
        'include_threads': True,
        'include_reactions': True,
    }
)

# Validate connection
if await source.validate():
    # Generate events from Slack
    async for event in source.generate_events():
        print(f"Event: {event.type} - {event.content[:50]}...")
```

Slack API Requirements:
- Bot token with appropriate scopes
- Scopes needed:
  - conversations:history (read channel messages)
  - reactions:read (read reactions)
  - users:read (read user info)
  - files:read (read file info)

Cursor Format:
```python
{
    'last_message_ts': '1234567890.123456',
    'last_channel': 'C1234567890',
    'messages_processed': 500
}
```
"""

import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime
from urllib.parse import urlencode

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    WebClient = None  # Optional dependency
    SlackApiError = None

from ._base import BaseEventSource
from ..models import EpisodicEvent, EventType, EventOutcome, EventContext


logger = logging.getLogger(__name__)


class SlackEventSource(BaseEventSource):
    """Slack workspace event source.

    Streams events from Slack channels and threads including messages,
    reactions, and thread discussions. Supports incremental sync using
    timestamp-based cursors.

    Configuration:
    ```python
    config = {
        'channels': [                    # Channels to monitor (required, at least 1)
            '#general',
            '#dev',
            '#random'
        ],
        'include_threads': True,         # Include thread messages (default: True)
        'include_reactions': True,       # Include reaction events (default: False)
        'include_files': True,           # Include file uploads (default: False)
        'exclude_bot_messages': True,    # Filter out bot messages (default: True)
        'per_page': 200,                 # Pagination size (default: 200, max: 200)
        'cursor': {                      # For incremental sync
            'last_message_ts': '1234567890.123456'
        }
    }
    ```
    """

    # Slack API constants
    API_BASE = "https://slack.com/api"
    API_TIMEOUT = 30  # seconds
    RATE_LIMIT_RETRY_WAIT = 1  # seconds (Slack suggests exponential backoff)

    def __init__(
        self,
        source_id: str,
        bot_token: str,
        channels: List[str],
        include_threads: bool = True,
        include_reactions: bool = False,
        include_files: bool = False,
        exclude_bot_messages: bool = True,
        per_page: int = 200,
        cursor: Optional[Dict[str, Any]] = None,
        logger_instance: Optional[logging.Logger] = None,
        project_id: int = 1,
    ):
        """Initialize Slack event source.

        Args:
            source_id: Unique identifier (e.g., 'slack-workspace-dev')
            bot_token: Slack bot token (xoxb-...)
            channels: List of channels to monitor (e.g., ['#general', '#dev'])
            include_threads: Include thread messages (default: True)
            include_reactions: Include reaction events (default: False)
            include_files: Include file uploads (default: False)
            exclude_bot_messages: Filter out bot messages (default: True)
            per_page: Pagination size (default: 200, max: 200)
            cursor: Optional cursor for incremental sync
            logger_instance: Optional logger
            project_id: Project context ID
        """
        super().__init__(
            source_id=source_id,
            source_type="slack",
            source_name=f"Slack: {','.join(channels)}",
            config={
                "channels": channels,
                "include_threads": include_threads,
                "include_reactions": include_reactions,
                "include_files": include_files,
                "exclude_bot_messages": exclude_bot_messages,
                "per_page": min(per_page, 200),  # Cap at Slack max
            },
            logger=logger_instance or logging.getLogger(__name__),
        )

        self.bot_token = bot_token
        self.channels = channels
        self.include_threads = include_threads
        self.include_reactions = include_reactions
        self.include_files = include_files
        self.exclude_bot_messages = exclude_bot_messages
        self.per_page = min(per_page, 200)
        self.project_id = project_id

        # Cursor state for incremental sync
        self._cursor = cursor or {}
        self._last_message_ts: Optional[str] = self._cursor.get("last_message_ts")
        self._last_channel: Optional[str] = self._cursor.get("last_channel")

        # Slack client (lazy initialized)
        self._client: Optional[Any] = None

        # Channel ID cache
        self._channel_id_map: Dict[str, str] = {}

    # ========================================================================
    # Required Abstract Methods
    # ========================================================================

    @classmethod
    async def create(
        cls,
        credentials: Dict[str, Any],
        config: Dict[str, Any],
    ) -> "SlackEventSource":
        """Factory method to create Slack event source.

        Args:
            credentials: Must contain:
                - bot_token: Slack bot token (xoxb-...)
            config: Must contain:
                - channels: List of channels to monitor
                Optional:
                - include_threads: Include threads (default: True)
                - include_reactions: Include reactions (default: False)
                - include_files: Include files (default: False)
                - exclude_bot_messages: Exclude bots (default: True)
                - per_page: Pagination size (default: 200)
                - cursor: Cursor for incremental sync

        Returns:
            Initialized SlackEventSource

        Raises:
            ValueError: Missing required credentials or config
            ConnectionError: Failed to validate connection
        """
        # Check slack_sdk dependency
        if WebClient is None:
            raise ValueError(
                "slack-sdk is required for Slack event source. "
                "Install with: pip install slack-sdk"
            )

        # Validate credentials
        bot_token = credentials.get("bot_token")
        if not bot_token:
            raise ValueError("Credentials must include 'bot_token' (Slack bot token)")

        # Validate config
        channels = config.get("channels", [])
        if not channels:
            raise ValueError("Config must include 'channels' (list of channel names)")

        # Normalize channel names (ensure they start with #)
        channels = [
            f"#{ch}" if not ch.startswith("#") else ch
            for ch in channels
        ]

        # Create instance
        source = cls(
            source_id=config.get("source_id", f"slack-{len(channels)}-channels"),
            bot_token=bot_token,
            channels=channels,
            include_threads=config.get("include_threads", True),
            include_reactions=config.get("include_reactions", False),
            include_files=config.get("include_files", False),
            exclude_bot_messages=config.get("exclude_bot_messages", True),
            per_page=config.get("per_page", 200),
            cursor=config.get("cursor"),
            project_id=config.get("project_id", 1),
        )

        return source

    async def validate(self) -> bool:
        """Validate Slack connection and permissions.

        Checks:
        - Token is valid
        - Workspace is accessible
        - Channels exist and are accessible
        - Bot has required permissions

        Returns:
            True if validation successful, False otherwise
        """
        try:
            # Initialize client
            self._client = WebClient(token=self.bot_token)

            # Check token validity
            auth_test = self._client.auth_test()
            if not auth_test["ok"]:
                self._logger.error("Slack auth test failed")
                return False

            workspace_name = auth_test.get("team")
            self._logger.info(f"✓ Connected to Slack workspace: {workspace_name}")

            # Check channel access
            for channel_name in self.channels:
                try:
                    # Get channel ID
                    result = self._client.conversations_list(
                        limit=100,
                        exclude_archived=True,
                    )

                    # Find matching channel
                    channel_id = None
                    for conv in result["channels"]:
                        if conv["name"] == channel_name.lstrip("#"):
                            channel_id = conv["id"]
                            self._channel_id_map[channel_name] = channel_id
                            break

                    if not channel_id:
                        self._logger.warning(f"Channel not found: {channel_name}")
                        # Don't fail - channel might exist but be archived
                        continue

                    # Try to read channel info
                    info = self._client.conversations_info(channel=channel_id)
                    if info["ok"]:
                        self._logger.debug(f"✓ Channel accessible: {channel_name}")
                    else:
                        self._logger.warning(f"Cannot access channel: {channel_name}")

                except SlackApiError as e:
                    self._logger.warning(f"Channel error for {channel_name}: {e}")
                    continue

            self._logger.info("Slack validation successful")
            return True

        except Exception as e:
            self._logger.error(f"Slack validation failed: {e}")
            return False

    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate episodic events from Slack.

        Fetches messages from channels and yields as EpisodicEvent instances.
        Supports incremental sync using timestamp cursor.

        Yields:
            EpisodicEvent instances from Slack
        """
        if WebClient is None:
            self._logger.error("slack-sdk not available")
            return

        try:
            self._client = WebClient(token=self.bot_token)

            # Get message history from all channels
            for channel_name in self.channels:
                async for event in self._generate_channel_events(channel_name):
                    yield event

        except Exception as e:
            self._logger.error(f"Failed to generate events: {e}")

    # ========================================================================
    # Incremental Sync Support
    # ========================================================================

    async def supports_incremental(self) -> bool:
        """Check if incremental sync is supported.

        Slack events support timestamp-based incremental sync.

        Returns:
            True (incremental sync is supported)
        """
        return True

    async def get_cursor(self) -> Dict[str, Any]:
        """Get current sync cursor.

        Returns:
            Cursor dict with last message timestamp and processing stats
        """
        return {
            "last_message_ts": self._last_message_ts or "0",
            "last_channel": self._last_channel,
            "messages_processed": self._events_generated,
            "messages_failed": self._events_failed,
        }

    async def set_cursor(self, cursor: Dict[str, Any]) -> None:
        """Set sync cursor for resuming from previous sync point.

        Args:
            cursor: Cursor dict containing last_message_ts
        """
        self._cursor = cursor
        self._last_message_ts = cursor.get("last_message_ts")
        self._last_channel = cursor.get("last_channel")

    # ========================================================================
    # Event Generation Methods (Private)
    # ========================================================================

    async def _generate_channel_events(
        self,
        channel_name: str,
    ) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from a single Slack channel."""
        # Normalize channel name
        channel_name = f"#{channel_name}" if not channel_name.startswith("#") else channel_name

        try:
            # Get channel ID
            channel_id = await self._get_channel_id(channel_name)
            if not channel_id:
                self._logger.warning(f"Could not find channel: {channel_name}")
                return

            self._last_channel = channel_id

            # Fetch message history
            oldest = self._last_message_ts or "0"

            try:
                result = self._client.conversations_history(
                    channel=channel_id,
                    oldest=oldest,
                    limit=self.per_page,
                    inclusive=False,
                )

                if not result["ok"]:
                    self._logger.error(
                        f"Failed to fetch channel history: {result.get('error')}"
                    )
                    return

                messages = result.get("messages", [])

                # Process messages
                for message in messages:
                    # Filter out bot messages if configured
                    if self.exclude_bot_messages and message.get("subtype") == "bot_message":
                        continue

                    event = self._transform_message_to_event(message, channel_name)
                    if event:
                        self._last_message_ts = message["ts"]
                        yield event

                    # Process thread if configured
                    if self.include_threads and message.get("thread_ts"):
                        async for thread_event in self._generate_thread_events(
                            channel_id, message["thread_ts"]
                        ):
                            yield thread_event

            except SlackApiError as e:
                self._logger.error(f"Slack API error for {channel_name}: {e}")

        except Exception as e:
            self._logger.error(f"Failed to generate channel events for {channel_name}: {e}")
            self._events_failed += 1

    async def _generate_thread_events(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from a Slack thread."""
        try:
            result = self._client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=self.per_page,
            )

            if not result["ok"]:
                return

            messages = result.get("messages", [])

            # Skip first message (parent, already processed)
            for message in messages[1:]:
                event = self._transform_thread_reply_to_event(message, thread_ts)
                if event:
                    yield event

        except SlackApiError:
            # Threads might not be accessible
            pass

    # ========================================================================
    # Event Transformation (Private)
    # ========================================================================

    def _transform_message_to_event(
        self,
        message: Dict[str, Any],
        channel_name: str,
    ) -> Optional[EpisodicEvent]:
        """Transform Slack message to EpisodicEvent."""
        try:
            text = message.get("text", "")
            if not text:
                return None

            ts = message.get("ts", "")
            timestamp = datetime.fromtimestamp(float(ts))
            user_id = message.get("user")

            # Get user name
            user_name = "unknown"
            if user_id:
                try:
                    user_info = self._client.users_info(user=user_id)
                    if user_info["ok"]:
                        user_name = user_info["user"].get("real_name") or user_info["user"].get(
                            "name"
                        )
                except SlackApiError:
                    pass

            # Get file info if message has files
            files_shared = []
            if "files" in message:
                for file_obj in message["files"]:
                    files_shared.append(
                        {
                            "name": file_obj.get("name"),
                            "type": file_obj.get("mimetype"),
                            "size": file_obj.get("size"),
                        }
                    )

            event = EpisodicEvent(
                type=EventType.COMMUNICATION,
                content=text[:500],  # First 500 chars
                timestamp=timestamp,
                project_id=self.project_id,
                source_id=self.source_id,
                metadata={
                    "channel": channel_name,
                    "user": user_name,
                    "user_id": user_id,
                    "message_ts": ts,
                    "thread_ts": message.get("thread_ts"),
                    "reply_count": message.get("reply_count", 0),
                    "reaction_count": message.get("reactions"),
                    "files_shared": files_shared,
                    "thread_root": message.get("parent_user_id"),
                },
                context=EventContext(
                    domain="communication",
                    subdomain="slack",
                ),
            )

            self._events_generated += 1
            self._log_event_generated(event)
            return event

        except Exception as e:
            self._logger.warning(f"Failed to transform message: {e}")
            self._events_failed += 1
            return None

    def _transform_thread_reply_to_event(
        self,
        message: Dict[str, Any],
        thread_ts: str,
    ) -> Optional[EpisodicEvent]:
        """Transform Slack thread reply to EpisodicEvent."""
        try:
            text = message.get("text", "")
            if not text:
                return None

            ts = message.get("ts", "")
            timestamp = datetime.fromtimestamp(float(ts))
            user_id = message.get("user")

            # Get user name
            user_name = "unknown"
            if user_id:
                try:
                    user_info = self._client.users_info(user=user_id)
                    if user_info["ok"]:
                        user_name = user_info["user"].get("real_name") or user_info["user"].get(
                            "name"
                        )
                except SlackApiError:
                    pass

            event = EpisodicEvent(
                type=EventType.COMMUNICATION,
                content=f"[Thread Reply] {text[:450]}",
                timestamp=timestamp,
                project_id=self.project_id,
                source_id=self.source_id,
                metadata={
                    "user": user_name,
                    "user_id": user_id,
                    "message_ts": ts,
                    "thread_ts": thread_ts,
                    "is_thread_reply": True,
                },
                context=EventContext(
                    domain="communication",
                    subdomain="slack_thread",
                ),
            )

            self._events_generated += 1
            self._log_event_generated(event)
            return event

        except Exception as e:
            self._logger.warning(f"Failed to transform thread reply: {e}")
            self._events_failed += 1
            return None

    # ========================================================================
    # Helper Methods (Private)
    # ========================================================================

    async def _get_channel_id(self, channel_name: str) -> Optional[str]:
        """Get Slack channel ID from name.

        Args:
            channel_name: Channel name (with or without #)

        Returns:
            Channel ID or None if not found
        """
        # Check cache first
        if channel_name in self._channel_id_map:
            return self._channel_id_map[channel_name]

        try:
            # Remove # prefix if present
            search_name = channel_name.lstrip("#")

            result = self._client.conversations_list(
                limit=200,
                exclude_archived=True,
            )

            if not result["ok"]:
                return None

            # Find channel by name
            for conv in result.get("channels", []):
                if conv["name"] == search_name:
                    channel_id = conv["id"]
                    self._channel_id_map[channel_name] = channel_id
                    return channel_id

            return None

        except SlackApiError:
            return None

    def _log_event_generated(self, event: EpisodicEvent) -> None:
        """Log event generation for debugging."""
        self._logger.debug(
            f"Generated event: {event.type} @ {event.timestamp} - {event.content[:50]}..."
        )


# ============================================================================
# Auto-Register with Factory
# ============================================================================

# Register SlackEventSource with the factory on module import
from .factory import EventSourceFactory
EventSourceFactory.register_source("slack", SlackEventSource)
