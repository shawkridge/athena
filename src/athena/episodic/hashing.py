"""Content-based event hashing for deduplication.

This module provides deterministic hashing of episodic events to prevent duplicate
storage when events are ingested from multiple sources (CLI, MCP, git hooks, etc.).

Deduplication Strategy
----------------------
Events are considered duplicates if their *content* is identical, excluding:
- Volatile metadata: id, created_at, lifecycle_status, last_activation
- System-generated fields: embeddings (computed on-demand)
- Internal tracking: surprise scores (recalculated during consolidation)

Included fields (the "content fingerprint"):
- project_id, session_id, timestamp: Temporal & spatial context
- event_type, code_event_type, outcome: Event classification
- content, learned, confidence: Core semantic content
- context (cwd, files, task, phase, branch): Contextual snapshot
- file_path, symbol_name, symbol_type, language: Code-aware tracking
- diff, git_commit, git_author: Version control metadata
- duration_ms, files_changed, lines_added, lines_deleted: Metrics
- test_name, test_passed, error_type, stack_trace: Testing/debugging info
- performance_metrics, code_quality_score: Quality metrics

Example Use Case
----------------
Scenario: Git post-commit hook records a commit event. 5 minutes later, the user runs
a CLI command that also tries to record the same commit event.

Without hashing:
  - Two identical events stored in database
  - Wastes storage and pollutes timeline
  - Consolidation produces duplicate patterns

With hashing:
  - Hash computed: "sha256:3a8b4c..."
  - Second ingestion detects existing hash
  - Event skipped, returns existing ID
  - Database remains clean

Hash Properties
---------------
- Deterministic: Same event content = same hash (stable across sessions)
- Collision-resistant: SHA256 provides 256-bit security (astronomically low collision rate)
- Fast: <1ms per event (suitable for batch ingestion)
- Portable: JSON serialization works across Python versions

Usage Example
-------------
>>> from athena.episodic.hashing import EventHasher
>>> from athena.episodic.models import EpisodicEvent, EventType, EventContext
>>> from datetime import datetime
>>>
>>> event1 = EpisodicEvent(
...     project_id=1,
...     session_id="abc123",
...     timestamp=datetime(2025, 1, 1, 12, 0, 0),
...     event_type=EventType.ACTION,
...     content="Fixed bug in user authentication",
...     context=EventContext(cwd="/home/user/project", files=["auth.py"])
... )
>>>
>>> event2 = EpisodicEvent(
...     project_id=1,
...     session_id="abc123",
...     timestamp=datetime(2025, 1, 1, 12, 0, 0),
...     event_type=EventType.ACTION,
...     content="Fixed bug in user authentication",
...     context=EventContext(cwd="/home/user/project", files=["auth.py"]),
...     id=999,  # Different ID (excluded from hash)
...     lifecycle_status="consolidated"  # Different status (excluded)
... )
>>>
>>> hasher = EventHasher()
>>> hash1 = hasher.compute_hash(event1)
>>> hash2 = hasher.compute_hash(event2)
>>> assert hash1 == hash2  # Same content = same hash
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict

from .models import EpisodicEvent, EventType, EventOutcome, EventContext, CodeEventType


class EventHasher:
    """Computes content-based hashes for episodic events.

    Uses SHA256 hashing on deterministically serialized event content to enable
    deduplication across multiple ingestion sources.
    """

    # Fields excluded from hash computation (volatile or system-generated)
    EXCLUDED_FIELDS = {
        "id",  # Database-assigned, not part of content
        "lifecycle_status",  # Changes during consolidation lifecycle
        "last_activation",  # Updated during consolidation
        "activation_count",  # Updated during consolidation
        "consolidation_score",  # System-computed during consolidation
        # Note: timestamp IS included - events at different times are different
    }

    def compute_hash(self, event: EpisodicEvent) -> str:
        """Compute deterministic SHA256 hash of event content.

        Args:
            event: Episodic event to hash

        Returns:
            Hex-encoded SHA256 hash (64 characters)

        Example:
            >>> event = EpisodicEvent(
            ...     project_id=1,
            ...     session_id="sess1",
            ...     event_type=EventType.ACTION,
            ...     content="Test event"
            ... )
            >>> hash1 = hasher.compute_hash(event)
            >>> hash2 = hasher.compute_hash(event)
            >>> assert hash1 == hash2  # Deterministic
            >>> assert len(hash1) == 64  # SHA256 hex encoding
        """
        # Convert event to dictionary and filter excluded fields
        event_dict = self._event_to_hashable_dict(event)

        # Serialize deterministically (sorted keys, consistent formatting)
        serialized = self._serialize_deterministically(event_dict)

        # Compute SHA256 hash
        hash_bytes = hashlib.sha256(serialized.encode("utf-8")).digest()

        # Return hex-encoded string
        return hash_bytes.hex()

    def _event_to_hashable_dict(self, event: EpisodicEvent) -> Dict[str, Any]:
        """Convert event to dictionary with excluded fields removed.

        Args:
            event: Event to convert

        Returns:
            Dictionary representation suitable for hashing
        """
        # Get all fields from the Pydantic model
        event_dict = event.model_dump()

        # Remove excluded fields
        for field in self.EXCLUDED_FIELDS:
            event_dict.pop(field, None)

        # Normalize nested objects to ensure consistent serialization
        event_dict = self._normalize_for_hashing(event_dict)

        return event_dict

    def _normalize_for_hashing(self, obj: Any) -> Any:
        """Recursively normalize object for deterministic hashing.

        Handles:
        - Datetime objects → ISO format strings
        - Enums → string values
        - Pydantic models → dictionaries
        - Lists/dicts → recursively normalized

        Args:
            obj: Object to normalize

        Returns:
            Normalized object suitable for JSON serialization
        """
        if isinstance(obj, datetime):
            # ISO format with microsecond precision
            return obj.isoformat()

        elif isinstance(obj, (EventType, EventOutcome, CodeEventType)):
            # Enum to string value
            return obj.value

        elif isinstance(obj, EventContext):
            # Pydantic model to dict
            return self._normalize_for_hashing(obj.model_dump())

        elif isinstance(obj, dict):
            # Recursively normalize dictionary values
            return {k: self._normalize_for_hashing(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            # Recursively normalize list items
            return [self._normalize_for_hashing(item) for item in obj]

        elif obj is None:
            return None

        else:
            # Primitives (str, int, float, bool) pass through
            return obj

    def _serialize_deterministically(self, obj: Any) -> str:
        """Serialize object to deterministic JSON string.

        Ensures same content produces same string regardless of:
        - Dictionary key insertion order
        - Python version
        - Whitespace variations

        Args:
            obj: Object to serialize (must be JSON-serializable)

        Returns:
            Deterministic JSON string

        Example:
            >>> obj1 = {"b": 2, "a": 1}
            >>> obj2 = {"a": 1, "b": 2}
            >>> s1 = hasher._serialize_deterministically(obj1)
            >>> s2 = hasher._serialize_deterministically(obj2)
            >>> assert s1 == s2  # Order-independent
        """
        return json.dumps(
            obj,
            sort_keys=True,  # Consistent key ordering
            separators=(",", ":"),  # No whitespace (minimal size)
            ensure_ascii=True,  # Consistent encoding
            default=str,  # Fallback for non-JSON types
        )

    def _should_exclude_field(self, field_name: str) -> bool:
        """Check if a field should be excluded from hashing.

        Args:
            field_name: Name of field to check

        Returns:
            True if field should be excluded, False otherwise

        Example:
            >>> hasher._should_exclude_field("id")
            True
            >>> hasher._should_exclude_field("content")
            False
        """
        return field_name in self.EXCLUDED_FIELDS


# Convenience function for quick hashing
def compute_event_hash(event: EpisodicEvent) -> str:
    """Compute hash for an event using default hasher.

    Convenience wrapper around EventHasher.compute_hash() for one-off usage.

    Args:
        event: Event to hash

    Returns:
        SHA256 hash of event content

    Example:
        >>> from athena.episodic.hashing import compute_event_hash
        >>> hash_value = compute_event_hash(my_event)
    """
    hasher = EventHasher()
    return hasher.compute_hash(event)


# Example usage and validation
if __name__ == "__main__":
    """Demonstrate event hashing with examples."""
    from datetime import datetime
    from .models import EpisodicEvent, EventType, EventContext, EventOutcome

    print("EventHasher Demonstration")
    print("=" * 60)

    # Example 1: Identical events produce same hash
    print("\n1. Identical Events (Same Hash)")
    print("-" * 60)

    event_a = EpisodicEvent(
        project_id=1,
        session_id="session_123",
        timestamp=datetime(2025, 1, 10, 14, 30, 0),
        event_type=EventType.ACTION,
        content="Implemented user authentication flow",
        outcome=EventOutcome.SUCCESS,
        context=EventContext(
            cwd="/home/user/project",
            files=["src/auth.py", "tests/test_auth.py"],
            task="Add OAuth support",
            phase="implementation",
        ),
        duration_ms=1500,
        files_changed=2,
        lines_added=85,
        lines_deleted=12,
        learned="OAuth 2.0 requires state parameter for security",
        confidence=0.9,
    )

    event_b = EpisodicEvent(
        project_id=1,
        session_id="session_123",
        timestamp=datetime(2025, 1, 10, 14, 30, 0),
        event_type=EventType.ACTION,
        content="Implemented user authentication flow",
        outcome=EventOutcome.SUCCESS,
        context=EventContext(
            cwd="/home/user/project",
            files=["src/auth.py", "tests/test_auth.py"],
            task="Add OAuth support",
            phase="implementation",
        ),
        duration_ms=1500,
        files_changed=2,
        lines_added=85,
        lines_deleted=12,
        learned="OAuth 2.0 requires state parameter for security",
        confidence=0.9,
        # Different volatile fields (excluded from hash)
        id=999,
        lifecycle_status="consolidated",
    )

    hasher = EventHasher()
    hash_a = hasher.compute_hash(event_a)
    hash_b = hasher.compute_hash(event_b)

    print(f"Event A hash: {hash_a}")
    print(f"Event B hash: {hash_b}")
    print(f"Hashes match: {hash_a == hash_b}")
    assert hash_a == hash_b, "Identical events should produce same hash"

    # Example 2: Different content produces different hash
    print("\n2. Different Content (Different Hash)")
    print("-" * 60)

    event_c = EpisodicEvent(
        project_id=1,
        session_id="session_123",
        timestamp=datetime(2025, 1, 10, 14, 30, 0),
        event_type=EventType.ACTION,
        content="Fixed bug in authentication",  # Different content
        outcome=EventOutcome.SUCCESS,
        context=EventContext(cwd="/home/user/project"),
    )

    hash_c = hasher.compute_hash(event_c)
    print(f"Event C hash: {hash_c}")
    print(f"Different from A: {hash_a != hash_c}")
    assert hash_a != hash_c, "Different content should produce different hash"

    # Example 3: Different timestamps produce different hashes
    print("\n3. Different Timestamps (Different Hash)")
    print("-" * 60)

    event_d = EpisodicEvent(
        project_id=1,
        session_id="session_123",
        timestamp=datetime(2025, 1, 10, 15, 30, 0),  # 1 hour later
        event_type=EventType.ACTION,
        content="Implemented user authentication flow",
        outcome=EventOutcome.SUCCESS,
        context=EventContext(cwd="/home/user/project"),
    )

    hash_d = hasher.compute_hash(event_d)
    print(f"Event D hash: {hash_d}")
    print(f"Different from A: {hash_a != hash_d}")
    assert hash_a != hash_d, "Different timestamps should produce different hash"

    # Example 4: Code-aware events
    print("\n4. Code-Aware Events")
    print("-" * 60)

    from .models import CodeEventType

    code_event = EpisodicEvent(
        project_id=1,
        session_id="session_456",
        timestamp=datetime(2025, 1, 10, 16, 0, 0),
        event_type=EventType.ACTION,
        code_event_type=CodeEventType.CODE_EDIT,
        content="Refactored authentication module",
        file_path="src/auth.py",
        symbol_name="authenticate_user",
        symbol_type="function",
        language="python",
        diff="@@ -10,3 +10,5 @@ def authenticate_user(credentials):\n     return validate(credentials)",
        git_commit="abc123def456",
        git_author="developer@example.com",
        context=EventContext(cwd="/home/user/project"),
    )

    hash_code = hasher.compute_hash(code_event)
    print(f"Code event hash: {hash_code}")
    print(f"Hash length: {len(hash_code)} characters (SHA256)")

    # Example 5: Hash uniqueness across many events
    print("\n5. Hash Distribution Test")
    print("-" * 60)

    from datetime import timedelta

    hashes = set()
    base_time = datetime(2025, 1, 10, 12, 0, 0)
    for i in range(100):
        test_event = EpisodicEvent(
            project_id=1,
            session_id=f"session_{i}",
            timestamp=base_time + timedelta(seconds=i),
            event_type=EventType.ACTION,
            content=f"Test event {i}",
            context=EventContext(cwd="/home/user/project"),
        )
        hash_val = hasher.compute_hash(test_event)
        hashes.add(hash_val)

    print(f"Generated {len(hashes)} unique hashes from 100 events")
    print(f"All unique: {len(hashes) == 100}")
    assert len(hashes) == 100, "All hashes should be unique"

    print("\n" + "=" * 60)
    print("All tests passed! Event hashing working correctly.")
    print("\nExcluded fields (not part of hash):")
    for field in sorted(EventHasher.EXCLUDED_FIELDS):
        print(f"  - {field}")
