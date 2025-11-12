"""Base store class for standardized database operations.

Provides common CRUD patterns and database utilities to reduce duplication
across all 26 store implementations in the system.

Features:
- Centralized database connection management
- Generic CRUD helper methods
- Consistent error handling
- Row-to-model conversion patterns
- Schema validation helpers
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
import json
from datetime import datetime

from .database import Database, get_database
from .error_handling import safe_dict_get, safe_json_loads

T = TypeVar('T')  # Model type


class BaseStore(ABC, Generic[T]):
    """Abstract base store with common CRUD patterns.

    Subclasses should:
    1. Set table_name class variable
    2. Set model_class class variable
    3. Implement _row_to_model() for row conversion
    4. Implement domain-specific list_* methods
    """

    # Must be set by subclasses
    table_name: str = None
    model_class: Type[T] = None

    def __init__(self, db: Optional[Database] = None):
        """Initialize store with database.

        Args:
            db: Database instance (default: uses global singleton from get_database())

        Benefits of default singleton:
            - All stores share a single connection pool (not multiple pools)
            - Easy to change configuration in one place (database.py)
            - Reduces memory overhead significantly
            - Enables future improvements like caching and fallbacks

        If you need a custom database instance (e.g., for testing), pass it explicitly:
            store = MyStore(db=custom_db)
        """
        # Use singleton if not provided (centralized database access)
        self.db = db or get_database()
        if not self.table_name:
            raise ValueError(f"{self.__class__.__name__} must set table_name")
        if not self.model_class:
            raise ValueError(f"{self.__class__.__name__} must set model_class")

    @abstractmethod
    def _row_to_model(self, row: Dict[str, Any]) -> T:
        """Convert database row to model instance.

        Must be implemented by subclasses.

        Args:
            row: Database row as dict

        Returns:
            Model instance
        """
        pass

    # ========================================================================
    # Generic CRUD Helpers
    # ========================================================================

    def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Any:
        """Execute SQL query with consistent error handling.

        Args:
            query: SQL query string
            params: Query parameters (default None)
            fetch_one: Return first row only
            fetch_all: Return all rows as list
                (if False, returns cursor for custom handling)

        Returns:
            Query result (row, list, or cursor based on parameters)
        """
        cursor = self.db.get_cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor

        except Exception as e:
            # rollback handled by cursor context
            raise

    def commit(self):
        """Commit database transaction."""
        # commit handled by cursor context

    def create(
        self,
        table_name: Optional[str] = None,
        columns: List[str] = None,
        values: tuple = None
    ) -> int:
        """Generic insert with lastrowid return.

        Args:
            table_name: Table to insert into (default: self.table_name)
            columns: List of column names
            values: Tuple of values to insert

        Returns:
            ID of inserted row
        """
        if not table_name:
            table_name = self.table_name
        if not columns or not values:
            raise ValueError("columns and values required")

        placeholders = ', '.join('?' * len(columns))
        query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({placeholders})
        """

        cursor = self.execute(query, values)
        self.commit()
        return cursor.lastrowid

    def get(
        self,
        id: int,
        table_name: Optional[str] = None
    ) -> Optional[T]:
        """Generic get by ID.

        Args:
            id: Row ID
            table_name: Table to query (default: self.table_name)

        Returns:
            Model instance if found, None otherwise
        """
        if not table_name:
            table_name = self.table_name

        row = self.execute(
            f"SELECT * FROM {table_name} WHERE id = ?",
            (id,),
            fetch_one=True
        )

        return self._row_to_model(row) if row else None

    def list_all(
        self,
        table_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None
    ) -> List[T]:
        """Generic list all with pagination.

        Args:
            table_name: Table to query (default: self.table_name)
            limit: Maximum rows to return
            offset: Offset for pagination
            order_by: Column to order by (e.g., 'created_at DESC')

        Returns:
            List of model instances
        """
        if not table_name:
            table_name = self.table_name

        query = f"SELECT * FROM {table_name}"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT ? OFFSET ?"

        rows = self.execute(query, (limit, offset), fetch_all=True)
        return [self._row_to_model(row) for row in rows] if rows else []

    def update(
        self,
        id: int,
        updates: Dict[str, Any],
        table_name: Optional[str] = None
    ) -> bool:
        """Generic update by ID.

        Args:
            id: Row ID
            updates: Dict of column -> value
            table_name: Table to update (default: self.table_name)

        Returns:
            True if row was updated, False otherwise
        """
        if not table_name:
            table_name = self.table_name
        if not updates:
            return False

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = tuple(updates.values()) + (id,)

        query = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"

        cursor = self.execute(query, values)
        self.commit()
        return cursor.rowcount > 0

    def delete(
        self,
        id: int,
        table_name: Optional[str] = None
    ) -> bool:
        """Generic delete by ID.

        Args:
            id: Row ID
            table_name: Table to delete from (default: self.table_name)

        Returns:
            True if row was deleted, False otherwise
        """
        if not table_name:
            table_name = self.table_name

        cursor = self.execute(
            f"DELETE FROM {table_name} WHERE id = ?",
            (id,)
        )
        self.commit()
        return cursor.rowcount > 0

    def exists(
        self,
        id: int,
        table_name: Optional[str] = None
    ) -> bool:
        """Check if row exists by ID.

        Args:
            id: Row ID
            table_name: Table to check (default: self.table_name)

        Returns:
            True if row exists, False otherwise
        """
        if not table_name:
            table_name = self.table_name

        row = self.execute(
            f"SELECT 1 FROM {table_name} WHERE id = ? LIMIT 1",
            (id,),
            fetch_one=True
        )
        return row is not None

    def count(
        self,
        table_name: Optional[str] = None,
        where: Optional[str] = None,
        params: Optional[tuple] = None
    ) -> int:
        """Count rows in table.

        Args:
            table_name: Table to count (default: self.table_name)
            where: Optional WHERE clause
            params: Optional query parameters

        Returns:
            Row count
        """
        if not table_name:
            table_name = self.table_name

        query = f"SELECT COUNT(*) FROM {table_name}"
        if where:
            query += f" WHERE {where}"

        row = self.execute(query, params, fetch_one=True)
        return row[0] if row else 0

    # ========================================================================
    # Serialization Helpers
    # ========================================================================

    @staticmethod
    def serialize_json(obj: Any) -> str:
        """Safely serialize object to JSON.

        Args:
            obj: Object to serialize

        Returns:
            JSON string
        """
        return json.dumps(obj) if obj else '{}'

    @staticmethod
    def deserialize_json(data: str, default: Optional[dict] = None) -> dict:
        """Safely deserialize JSON string.

        Args:
            data: JSON string to deserialize
            default: Default dict if deserialization fails

        Returns:
            Deserialized dict or default
        """
        return safe_json_loads(data, default or {})

    # ========================================================================
    # Timestamp Helpers
    # ========================================================================

    @staticmethod
    def now_timestamp() -> int:
        """Get current Unix timestamp.

        Returns:
            Unix timestamp
        """
        return int(datetime.now().timestamp())

    @staticmethod
    def from_timestamp(ts: Optional[int]) -> Optional[datetime]:
        """Convert timestamp to datetime.

        Args:
            ts: Unix timestamp (or None)

        Returns:
            Datetime object or None
        """
        if ts is None:
            return None
        # Handle string timestamps from database
        if isinstance(ts, str):
            if not ts or ts == '{}':
                return None
            try:
                ts = float(ts)
            except (ValueError, TypeError):
                return None
        try:
            return datetime.fromtimestamp(ts)
        except (ValueError, TypeError, OSError):
            return None

    # ========================================================================
    # Query Helpers for Common Patterns
    # ========================================================================

    def find_by_column(
        self,
        column: str,
        value: Any,
        table_name: Optional[str] = None
    ) -> Optional[T]:
        """Find single row by column value.

        Args:
            column: Column name
            value: Value to search for
            table_name: Table to query (default: self.table_name)

        Returns:
            Model instance if found, None otherwise
        """
        if not table_name:
            table_name = self.table_name

        row = self.execute(
            f"SELECT * FROM {table_name} WHERE {column} = ? LIMIT 1",
            (value,),
            fetch_one=True
        )

        return self._row_to_model(row) if row else None

    def find_all_by_column(
        self,
        column: str,
        value: Any,
        table_name: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: int = 100
    ) -> List[T]:
        """Find all rows by column value.

        Args:
            column: Column name
            value: Value to search for
            table_name: Table to query (default: self.table_name)
            order_by: Optional ORDER BY clause
            limit: Maximum rows

        Returns:
            List of model instances
        """
        if not table_name:
            table_name = self.table_name

        query = f"SELECT * FROM {table_name} WHERE {column} = ?"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT ?"

        rows = self.execute(query, (value, limit), fetch_all=True)
        return [self._row_to_model(row) for row in rows] if rows else []

    def delete_by_column(
        self,
        column: str,
        value: Any,
        table_name: Optional[str] = None
    ) -> int:
        """Delete all rows matching column value.

        Args:
            column: Column name
            value: Value to match
            table_name: Table to delete from (default: self.table_name)

        Returns:
            Number of rows deleted
        """
        if not table_name:
            table_name = self.table_name

        cursor = self.execute(
            f"DELETE FROM {table_name} WHERE {column} = ?",
            (value,)
        )
        self.commit()
        return cursor.rowcount
