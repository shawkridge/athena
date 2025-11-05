"""Unified time utilities for consistent datetime handling.

Consolidates timestamp operations across all memory layers.
Provides:
- Current time operations (Unix, ISO)
- Time difference calculations
- Recent timestamp checks
- Consistent time formatting
"""

import time
from datetime import datetime, timedelta
from typing import Optional


def now_timestamp() -> int:
    """Get current Unix timestamp (seconds since epoch).

    Returns:
        Current time as Unix timestamp
    """
    return int(time.time())


def now_iso() -> str:
    """Get current time as ISO 8601 string.

    Returns:
        Current time in ISO format (e.g., "2025-10-30T15:30:45.123456")
    """
    return datetime.now().isoformat()


def now_datetime() -> datetime:
    """Get current datetime object.

    Returns:
        Current datetime
    """
    return datetime.now()


def seconds_since(dt: Optional[datetime]) -> float:
    """Calculate seconds elapsed since datetime.

    Args:
        dt: Datetime to compare (or None for 0)

    Returns:
        Seconds elapsed since dt (or 0 if dt is None)
    """
    if dt is None:
        return 0.0
    return (datetime.now() - dt).total_seconds()


def seconds_between(dt1: datetime, dt2: datetime) -> float:
    """Calculate seconds between two datetimes.

    Args:
        dt1: First datetime
        dt2: Second datetime

    Returns:
        Seconds between dt1 and dt2 (positive if dt2 > dt1)
    """
    return (dt2 - dt1).total_seconds()


def is_recent(dt: Optional[datetime], max_seconds: int = 3600) -> bool:
    """Check if datetime is recent (within max_seconds).

    Args:
        dt: Datetime to check (or None for False)
        max_seconds: Maximum age in seconds (default: 1 hour)

    Returns:
        True if dt is recent, False otherwise
    """
    if dt is None:
        return False
    return seconds_since(dt) < max_seconds


def is_older_than(dt: Optional[datetime], min_seconds: int = 3600) -> bool:
    """Check if datetime is older than min_seconds.

    Args:
        dt: Datetime to check (or None for True)
        min_seconds: Minimum age in seconds (default: 1 hour)

    Returns:
        True if dt is older than min_seconds, False otherwise
    """
    if dt is None:
        return True
    return seconds_since(dt) > min_seconds


def time_category(dt: Optional[datetime]) -> str:
    """Categorize datetime by recency.

    Args:
        dt: Datetime to categorize

    Returns:
        Category: 'now' (<5 min), 'recent' (<1 hour), 'today' (<24 hours),
                 'this_week' (<7 days), 'older'
    """
    if dt is None:
        return 'unknown'

    seconds = seconds_since(dt)

    if seconds < 300:
        return 'now'
    elif seconds < 3600:
        return 'recent'
    elif seconds < 86400:
        return 'today'
    elif seconds < 604800:
        return 'this_week'
    else:
        return 'older'


def format_duration(seconds: float) -> str:
    """Format duration in seconds as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable string (e.g., "5m 30s", "2h 15m", "3d 2h")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h" if hours else f"{days}d"


def format_relative_time(dt: Optional[datetime]) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format (or None)

    Returns:
        Relative time string (e.g., "5 minutes ago", "2 days ago")
    """
    if dt is None:
        return 'unknown'

    duration = format_duration(seconds_since(dt))
    return f"{duration} ago"


def from_timestamp(timestamp: int) -> datetime:
    """Convert Unix timestamp to datetime.

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        Datetime object
    """
    return datetime.fromtimestamp(timestamp)


def from_iso(iso_string: str) -> datetime:
    """Parse ISO 8601 datetime string.

    Args:
        iso_string: ISO format string (e.g., "2025-10-30T15:30:45")

    Returns:
        Datetime object
    """
    return datetime.fromisoformat(iso_string)


def add_seconds(dt: datetime, seconds: int) -> datetime:
    """Add seconds to datetime.

    Args:
        dt: Base datetime
        seconds: Seconds to add (can be negative)

    Returns:
        New datetime object
    """
    return dt + timedelta(seconds=seconds)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """Add minutes to datetime.

    Args:
        dt: Base datetime
        minutes: Minutes to add (can be negative)

    Returns:
        New datetime object
    """
    return dt + timedelta(minutes=minutes)


def add_hours(dt: datetime, hours: int) -> datetime:
    """Add hours to datetime.

    Args:
        dt: Base datetime
        hours: Hours to add (can be negative)

    Returns:
        New datetime object
    """
    return dt + timedelta(hours=hours)


def add_days(dt: datetime, days: int) -> datetime:
    """Add days to datetime.

    Args:
        dt: Base datetime
        days: Days to add (can be negative)

    Returns:
        New datetime object
    """
    return dt + timedelta(days=days)


def time_window(start: Optional[datetime], end: Optional[datetime]) -> float:
    """Calculate time window in seconds between two datetimes.

    Args:
        start: Start datetime (or None for 0)
        end: End datetime (or None for now)

    Returns:
        Time window in seconds
    """
    if start is None or end is None:
        return 0.0
    return (end - start).total_seconds()
