"""Athena schema management system.

Centralized schema definition and migration management for the 8-layer memory system.
Schema is treated as infrastructure, not application code.

Architecture:
- migrations/: Discrete, versioned schema changes
- versions.py: Schema version tracking and metadata
- validator.py: Runtime schema validation
- runner.py: Migration execution and rollback

All schema changes go through migrations, never embedded in modules.
"""

from .runner import MigrationRunner
from .versions import SchemaVersion
from .validator import SchemaValidator

__all__ = ["MigrationRunner", "SchemaVersion", "SchemaValidator"]
