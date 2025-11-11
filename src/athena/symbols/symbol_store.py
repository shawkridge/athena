"""
Symbol Store - Database Persistence Layer (Phase 1B)

Provides database schema and CRUD operations for symbol analysis:
- Symbols table: Core symbol data with full qualified names
- Symbol Relationships table: Dependencies and references between symbols
- Symbol Metrics table: Performance and quality metrics per symbol

Author: Claude Code
Date: 2025-10-31
"""

from typing import Optional, List, Dict, Any
from dataclasses import asdict
from pathlib import Path

from athena.symbols.symbol_models import (
    Symbol, SymbolType, RelationType, SymbolMetrics, SymbolDependency
)


class SymbolStore:
    """Database persistence layer for symbol analysis results.

    Manages SQLite schema for storing symbols, relationships, and metrics.
    All queries use parameterized statements to prevent SQL injection.
    """

    def __init__(self, db_path: str = None):
        """Initialize store with database connection.

        Args:
            db_path: Path to SQLite database. If None, uses in-memory database.
        """
        if db_path is None:
            self.db_path = ":memory:"
        else:
            # Ensure parent directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self.db_path = db_path

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name

        # Enable foreign key constraints
        self.conn.execute("PRAGMA foreign_keys = ON")
    def _ensure_schema(self) -> None:
        """Create database schema on first use.

        Creates three main tables:
        - symbols: Core symbol data
        - symbol_relationships: Dependencies between symbols
        - symbol_metrics: Performance metrics per symbol
        """
        cursor = self.conn.cursor()

        # Main symbols table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                symbol_type TEXT NOT NULL,
                name TEXT NOT NULL,
                namespace TEXT,
                full_qualified_name TEXT NOT NULL UNIQUE,
                signature TEXT,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                code TEXT,
                docstring TEXT,
                visibility TEXT DEFAULT 'public',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        # Symbol relationships table (dependencies and references)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbol_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_symbol_id INTEGER NOT NULL,
                to_symbol_name TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (from_symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
                UNIQUE(from_symbol_id, to_symbol_name, relation_type)
            )
        """)

        # Symbol metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbol_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER NOT NULL UNIQUE,
                lines_of_code INTEGER,
                cyclomatic_complexity INTEGER,
                cognitive_complexity INTEGER,
                parameters INTEGER,
                nesting_depth INTEGER,
                maintainability_index REAL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for common queries
        # Index 1: Query by file and type (common queries)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbols_file_type
            ON symbols(file_path, symbol_type)
        """)

        # Index 2: Query by full qualified name
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbols_qname
            ON symbols(full_qualified_name)
        """)

        # Index 3: Query by namespace (for scope-based analysis)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbols_namespace
            ON symbols(namespace)
        """)

        # Index 4: Relationship queries (from_symbol lookup)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_from
            ON symbol_relationships(from_symbol_id, relation_type)
        """)

        # Index 5: Reverse dependency lookup (to_symbol lookup)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationships_to
            ON symbol_relationships(to_symbol_name)
        """)

        self.conn.commit()

    def create_symbol(self, symbol: Symbol) -> Symbol:
        """Insert a symbol into the database.

        Args:
            symbol: Symbol instance to store

        Returns:
            Symbol with populated id field

        Raises:
            Exception: If full_qualified_name already exists
        """
        import time
        now = int(time.time())

        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO symbols (
                    file_path, symbol_type, name, namespace, full_qualified_name,
                    signature, line_start, line_end, code, docstring, visibility,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol.file_path,
                symbol.symbol_type,
                symbol.name,
                symbol.namespace,
                symbol.full_qualified_name,
                symbol.signature,
                symbol.line_start,
                symbol.line_end,
                symbol.code,
                symbol.docstring,
                symbol.visibility,
                now,
                now
            ))

            # Get the inserted ID
            symbol_id = cursor.lastrowid

            # Insert metrics if present
            if symbol.metrics:
                cursor.execute("""
                    INSERT INTO symbol_metrics (
                        symbol_id, lines_of_code, cyclomatic_complexity,
                        cognitive_complexity, parameters, nesting_depth,
                        maintainability_index, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol_id,
                    symbol.metrics.lines_of_code,
                    symbol.metrics.cyclomatic_complexity,
                    symbol.metrics.cognitive_complexity,
                    symbol.metrics.parameters,
                    symbol.metrics.nesting_depth,
                    symbol.metrics.maintainability_index,
                    now
                ))

            # Insert dependencies
            for dep in symbol.dependencies:
                self.create_relationship(
                    symbol_id,
                    dep.target_symbol_name,
                    dep.relation_type,
                    dep.strength
                )

            self.conn.commit()

            # Return symbol with ID set
            symbol.id = symbol_id
            return symbol

        except Exception as e:
            self.conn.rollback()
            raise Exception(
                f"Symbol {symbol.full_qualified_name} already exists: {e}"
            )

    def get_symbol(self, symbol_id: int) -> Optional[Symbol]:
        """Retrieve a symbol by ID.

        Args:
            symbol_id: Database ID of the symbol

        Returns:
            Symbol instance or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, m.* FROM symbols s
            LEFT JOIN symbol_metrics m ON s.id = m.symbol_id
            WHERE s.id = ?
        """, (symbol_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_symbol(row)

    def get_symbol_by_qname(self, full_qualified_name: str) -> Optional[Symbol]:
        """Retrieve a symbol by full qualified name.

        Args:
            full_qualified_name: Full qualified name (e.g., "auth.jwt.JWTHandler.encode")

        Returns:
            Symbol instance or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, m.* FROM symbols s
            LEFT JOIN symbol_metrics m ON s.id = m.symbol_id
            WHERE s.full_qualified_name = ?
        """, (full_qualified_name,))

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_symbol(row)

    def get_symbols_in_file(self, file_path: str) -> List[Symbol]:
        """Retrieve all symbols from a specific file.

        Args:
            file_path: Path to source file

        Returns:
            List of Symbol instances
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, m.* FROM symbols s
            LEFT JOIN symbol_metrics m ON s.id = m.symbol_id
            WHERE s.file_path = ?
            ORDER BY s.line_start
        """, (file_path,))

        rows = cursor.fetchall()
        return [self._row_to_symbol(row) for row in rows]

    def get_symbols_by_type(self, symbol_type: str) -> List[Symbol]:
        """Retrieve all symbols of a specific type.

        Args:
            symbol_type: Symbol type (e.g., "function", "class")

        Returns:
            List of Symbol instances
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, m.* FROM symbols s
            LEFT JOIN symbol_metrics m ON s.id = m.symbol_id
            WHERE s.symbol_type = ?
            ORDER BY s.full_qualified_name
        """, (symbol_type,))

        rows = cursor.fetchall()
        return [self._row_to_symbol(row) for row in rows]

    def get_symbols_by_namespace(self, namespace: str) -> List[Symbol]:
        """Retrieve all symbols in a specific namespace.

        Args:
            namespace: Namespace to search (e.g., "auth.jwt")

        Returns:
            List of Symbol instances
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, m.* FROM symbols s
            LEFT JOIN symbol_metrics m ON s.id = m.symbol_id
            WHERE s.namespace = ?
            ORDER BY s.name
        """, (namespace,))

        rows = cursor.fetchall()
        return [self._row_to_symbol(row) for row in rows]

    def create_relationship(
        self,
        from_symbol_id: int,
        to_symbol_name: str,
        relation_type: str,
        strength: float = 1.0
    ) -> None:
        """Create a relationship between two symbols.

        Args:
            from_symbol_id: Database ID of source symbol
            to_symbol_name: Full qualified name of target symbol
            relation_type: Type of relationship (e.g., "calls", "imports")
            strength: Relationship strength (0.0-1.0)

        Raises:
            ValueError: If strength is not in valid range
        """
        if not 0.0 <= strength <= 1.0:
            raise ValueError("Strength must be between 0.0 and 1.0")

        import time
        now = int(time.time())

        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO symbol_relationships (
                    from_symbol_id, to_symbol_name, relation_type, strength, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (from_symbol_id, to_symbol_name, relation_type, strength, now))

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Relationship creation failed: {e}")

    def get_relationships(
        self,
        from_symbol_id: int,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all relationships from a symbol.

        Args:
            from_symbol_id: Database ID of source symbol
            relation_type: Optional filter by relationship type

        Returns:
            List of relationship dictionaries
        """
        cursor = self.conn.cursor()

        if relation_type:
            cursor.execute("""
                SELECT * FROM symbol_relationships
                WHERE from_symbol_id = ? AND relation_type = ?
                ORDER BY strength DESC
            """, (from_symbol_id, relation_type))
        else:
            cursor.execute("""
                SELECT * FROM symbol_relationships
                WHERE from_symbol_id = ?
                ORDER BY strength DESC
            """, (from_symbol_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_dependencies(self, from_symbol_id: int) -> List[str]:
        """Get all symbols that a given symbol depends on.

        Args:
            from_symbol_id: Database ID of symbol

        Returns:
            List of target symbol names
        """
        relationships = self.get_relationships(from_symbol_id)
        return [rel["to_symbol_name"] for rel in relationships]

    def get_dependents(self, to_symbol_name: str) -> List[int]:
        """Get all symbols that depend on a given symbol (reverse lookup).

        Args:
            to_symbol_name: Full qualified name of target symbol

        Returns:
            List of source symbol IDs
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT from_symbol_id FROM symbol_relationships
            WHERE to_symbol_name = ?
        """, (to_symbol_name,))

        return [row[0] for row in cursor.fetchall()]

    def update_symbol_metrics(self, symbol_id: int, metrics: SymbolMetrics) -> None:
        """Update or create metrics for a symbol.

        Args:
            symbol_id: Database ID of symbol
            metrics: Updated SymbolMetrics instance
        """
        import time
        now = int(time.time())

        cursor = self.conn.cursor()

        # Check if metrics exist
        cursor.execute("SELECT id FROM symbol_metrics WHERE symbol_id = ?", (symbol_id,))
        existing = cursor.fetchone()

        if existing:
            # Update existing
            cursor.execute("""
                UPDATE symbol_metrics SET
                    lines_of_code = ?,
                    cyclomatic_complexity = ?,
                    cognitive_complexity = ?,
                    parameters = ?,
                    nesting_depth = ?,
                    maintainability_index = ?
                WHERE symbol_id = ?
            """, (
                metrics.lines_of_code,
                metrics.cyclomatic_complexity,
                metrics.cognitive_complexity,
                metrics.parameters,
                metrics.nesting_depth,
                metrics.maintainability_index,
                symbol_id
            ))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO symbol_metrics (
                    symbol_id, lines_of_code, cyclomatic_complexity,
                    cognitive_complexity, parameters, nesting_depth,
                    maintainability_index, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol_id,
                metrics.lines_of_code,
                metrics.cyclomatic_complexity,
                metrics.cognitive_complexity,
                metrics.parameters,
                metrics.nesting_depth,
                metrics.maintainability_index,
                now
            ))

        self.conn.commit()

    def get_all_symbols(self) -> List[Symbol]:
        """Retrieve all symbols in the database.

        Returns:
            List of all Symbol instances
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, m.* FROM symbols s
            LEFT JOIN symbol_metrics m ON s.id = m.symbol_id
            ORDER BY s.full_qualified_name
        """)

        rows = cursor.fetchall()
        return [self._row_to_symbol(row) for row in rows]

    def delete_symbol(self, symbol_id: int) -> bool:
        """Delete a symbol and all its relationships.

        Args:
            symbol_id: Database ID of symbol to delete

        Returns:
            True if symbol was deleted, False if not found
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT id FROM symbols WHERE id = ?", (symbol_id,))
        if not cursor.fetchone():
            return False

        # Delete cascades to metrics and relationships via FK constraints
        cursor.execute("DELETE FROM symbols WHERE id = ?", (symbol_id,))
        self.conn.commit()

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with counts and metrics
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM symbols")
        symbol_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM symbol_relationships")
        relationship_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT symbol_type) FROM symbols")
        type_count = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(cyclomatic_complexity) FROM symbol_metrics")
        avg_complexity = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(maintainability_index) FROM symbol_metrics")
        avg_maintainability = cursor.fetchone()[0]

        return {
            "total_symbols": symbol_count,
            "total_relationships": relationship_count,
            "symbol_types": type_count,
            "avg_cyclomatic_complexity": avg_complexity,
            "avg_maintainability_index": avg_maintainability,
        }

    def _row_to_symbol(self, row: sqlite3.Row) -> Symbol:
        """Convert database row to Symbol instance.

        Args:
            row: sqlite3.Row from symbols table (with optional metrics join)

        Returns:
            Reconstructed Symbol instance
        """
        # Reconstruct metrics
        metrics = None
        if row["lines_of_code"] is not None:
            metrics = SymbolMetrics(
                lines_of_code=row["lines_of_code"],
                cyclomatic_complexity=row["cyclomatic_complexity"],
                cognitive_complexity=row["cognitive_complexity"],
                parameters=row["parameters"],
                nesting_depth=row["nesting_depth"],
                maintainability_index=row["maintainability_index"],
            )

        # Get dependencies
        dependencies = []
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT to_symbol_name, relation_type, strength
            FROM symbol_relationships
            WHERE from_symbol_id = ?
        """, (row["id"],))

        for dep_row in cursor.fetchall():
            dependencies.append(
                SymbolDependency(
                    target_symbol_name=dep_row[0],
                    relation_type=dep_row[1],
                    strength=dep_row[2],
                )
            )

        # Reconstruct full_qualified_name from namespace and name
        namespace = row["namespace"] or ""
        name = row["name"]
        full_qualified_name = f"{namespace}.{name}" if namespace else name

        # Reconstruct symbol
        symbol = Symbol(
            file_path=row["file_path"],
            symbol_type=row["symbol_type"],
            name=name,
            namespace=namespace,
            full_qualified_name=full_qualified_name,
            signature=row["signature"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            code=row["code"],
            docstring=row["docstring"],
            metrics=metrics,
            dependencies=dependencies,
            visibility=row["visibility"],
        )
        # Set ID from database
        symbol.id = row["id"]
        return symbol

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
