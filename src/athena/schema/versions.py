"""Schema version tracking and metadata.

Maintains the schema version history and metadata for migrations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SchemaVersion:
    """Represents a schema version entry in the database."""

    version: str
    """Migration version (e.g., '001' from m001_initial_8layers.sql)"""

    filename: str
    """Migration filename"""

    description: str
    """Migration description from file comment"""

    applied_at: Optional[datetime] = None
    """Timestamp when migration was applied"""

    execution_time_ms: Optional[int] = None
    """Execution time in milliseconds"""

    def __repr__(self) -> str:
        return f"SchemaVersion({self.version}: {self.description})"
