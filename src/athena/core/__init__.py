"""Core database and embedding functionality."""

# PostgreSQL only (local or Docker), no SQLite
from .database_postgres import PostgresDatabase as Database
from .models import Memory, Project, MemoryType

__all__ = ["Database", "Memory", "Project", "MemoryType"]
