"""Spatial graph storage and query operations."""

from datetime import datetime
from typing import Any, List, Optional

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import SpatialNode, SpatialRelation


class SpatialStore:
    """Manages spatial hierarchy storage and queries."""

    def __init__(self, db: Database):
        """
        Initialize spatial store.

        Args:
            db: Database instance
        """
        self.db = db
        self._ensure_schema()

    # ==================== HELPER METHODS ====================

    def execute(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False) -> Any:
        """Execute SQL query with consistent error handling.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return first row only
            fetch_all: Return all rows as list

        Returns:
            Query result (row, list, or cursor based on parameters)
        """
        cursor = self.db.conn.cursor()

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
            self.db.conn.rollback()
            raise

    def commit(self):
        """Commit database transaction."""
        self.db.conn.commit()

    @staticmethod
    def now_timestamp() -> int:
        """Get current Unix timestamp.

        Returns:
            Unix timestamp
        """
        return int(datetime.now().timestamp())

    def _ensure_schema(self):
        """Ensure spatial tables exist."""
        cursor = self.db.conn.cursor()

        # Spatial nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spatial_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                full_path TEXT NOT NULL,
                depth INTEGER NOT NULL,
                parent_path TEXT,
                node_type TEXT NOT NULL,
                language TEXT,
                symbol_kind TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE(project_id, full_path),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Spatial relations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spatial_relations (
                from_path TEXT NOT NULL,
                to_path TEXT NOT NULL,
                project_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_path, to_path, project_id, relation_type),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Symbol nodes table (code-level symbols: functions, classes, methods)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbol_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                symbol_kind TEXT NOT NULL,
                language TEXT NOT NULL,
                full_path TEXT NOT NULL UNIQUE,
                parent_class TEXT,
                signature TEXT,
                docstring TEXT,
                complexity_score REAL,
                created_at INTEGER NOT NULL,
                UNIQUE(project_id, file_path, name, line_number),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Symbol relations (calls, inherits, implements, etc)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbol_relations (
                from_symbol_id INTEGER NOT NULL,
                to_symbol_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_symbol_id, to_symbol_id, relation_type),
                FOREIGN KEY (from_symbol_id) REFERENCES symbol_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (to_symbol_id) REFERENCES symbol_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Add columns to spatial_nodes if they don't exist
        cursor.execute("PRAGMA table_info(spatial_nodes)")
        columns = {row[1] for row in cursor.fetchall()}
        if "language" not in columns:
            cursor.execute("ALTER TABLE spatial_nodes ADD COLUMN language TEXT")
        if "symbol_kind" not in columns:
            cursor.execute("ALTER TABLE spatial_nodes ADD COLUMN symbol_kind TEXT")

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spatial_nodes_project ON spatial_nodes(project_id, full_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spatial_nodes_depth ON spatial_nodes(project_id, depth)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spatial_nodes_type ON spatial_nodes(project_id, node_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spatial_relations_from ON spatial_relations(project_id, from_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spatial_relations_to ON spatial_relations(project_id, to_path)")

        # Symbol node indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_nodes_file ON symbol_nodes(project_id, file_path, line_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_nodes_kind ON symbol_nodes(project_id, symbol_kind)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_nodes_language ON symbol_nodes(project_id, language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_relations_from ON symbol_relations(from_symbol_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_relations_to ON symbol_relations(to_symbol_id)")

        self.db.conn.commit()

    def store_node(self, project_id: int, node: SpatialNode) -> int:
        """
        Store a spatial node.

        Args:
            project_id: Project ID
            node: Spatial node to store

        Returns:
            Node ID
        """
        cursor = self.execute("""
            INSERT OR IGNORE INTO spatial_nodes
            (project_id, name, full_path, depth, parent_path, node_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            node.name,
            node.full_path,
            node.depth,
            node.parent_path,
            node.node_type,
            self.now_timestamp()
        ))

        self.commit()

        # Get the ID
        row = self.execute(
            "SELECT id FROM spatial_nodes WHERE project_id = ? AND full_path = ?",
            (project_id, node.full_path),
            fetch_one=True,
        )
        return row['id'] if row else cursor.lastrowid

    def store_relation(self, project_id: int, relation: SpatialRelation):
        """
        Store a spatial relation.

        Args:
            project_id: Project ID
            relation: Spatial relation to store
        """
        self.execute("""
            INSERT OR REPLACE INTO spatial_relations
            (from_path, to_path, project_id, relation_type, strength)
            VALUES (?, ?, ?, ?, ?)
        """, (
            relation.from_path,
            relation.to_path,
            project_id,
            relation.relation_type,
            relation.strength
        ))

        self.commit()

    def batch_store_nodes(self, project_id: int, nodes: List[SpatialNode]) -> int:
        """
        Store multiple spatial nodes in a single transaction (optimized).

        Args:
            project_id: Project ID
            nodes: List of spatial nodes to store

        Returns:
            Number of nodes stored
        """
        if not nodes:
            return 0

        cursor = self.db.conn.cursor()
        now = self.now_timestamp()

        # De-duplicate nodes by full_path
        seen_paths = set()
        unique_nodes = []
        for node in nodes:
            if node.full_path not in seen_paths:
                seen_paths.add(node.full_path)
                unique_nodes.append(node)

        # Batch insert all nodes in single transaction
        try:
            data = [(
                project_id,
                node.name,
                node.full_path,
                node.depth,
                node.parent_path,
                node.node_type,
                now
            ) for node in unique_nodes]

            cursor.executemany("""
                INSERT OR IGNORE INTO spatial_nodes
                (project_id, name, full_path, depth, parent_path, node_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data)

            self.commit()
            return len(unique_nodes)
        except Exception as e:
            self.db.conn.rollback()
            raise e

    def batch_store_relations(self, project_id: int, relations: List[SpatialRelation]) -> int:
        """
        Store multiple spatial relations in a single transaction (optimized).

        Args:
            project_id: Project ID
            relations: List of spatial relations to store

        Returns:
            Number of relations stored
        """
        if not relations:
            return 0

        cursor = self.db.conn.cursor()

        # De-duplicate relations by (from_path, to_path, type)
        seen_relations = set()
        unique_relations = []
        for relation in relations:
            key = (relation.from_path, relation.to_path, relation.relation_type)
            if key not in seen_relations:
                seen_relations.add(key)
                unique_relations.append(relation)

        # Batch insert all relations in single transaction
        try:
            data = [(
                relation.from_path,
                relation.to_path,
                project_id,
                relation.relation_type,
                relation.strength
            ) for relation in unique_relations]

            cursor.executemany("""
                INSERT OR REPLACE INTO spatial_relations
                (from_path, to_path, project_id, relation_type, strength)
                VALUES (?, ?, ?, ?, ?)
            """, data)

            self.commit()
            return len(unique_relations)
        except Exception as e:
            self.db.conn.rollback()
            raise e

    def get_node(self, project_id: int, full_path: str) -> Optional[SpatialNode]:
        """
        Get spatial node by path.

        Args:
            project_id: Project ID
            full_path: Full file path

        Returns:
            Spatial node if found
        """
        row = self.execute("""
            SELECT name, full_path, depth, parent_path, node_type
            FROM spatial_nodes
            WHERE project_id = ? AND full_path = ?
        """, (project_id, full_path), fetch_one=True)

        if not row:
            return None

        return SpatialNode(
            name=row['name'],
            full_path=row['full_path'],
            depth=row['depth'],
            parent_path=row['parent_path'],
            node_type=row['node_type']
        )

    def get_children(self, project_id: int, parent_path: str) -> List[SpatialNode]:
        """
        Get all direct children of a spatial node.

        Args:
            project_id: Project ID
            parent_path: Parent path

        Returns:
            List of child nodes
        """
        rows = self.execute("""
            SELECT name, full_path, depth, parent_path, node_type
            FROM spatial_nodes
            WHERE project_id = ? AND parent_path = ?
            ORDER BY name
        """, (project_id, parent_path), fetch_all=True)

        nodes = []
        for row in (rows or []):
            nodes.append(SpatialNode(
                name=row['name'],
                full_path=row['full_path'],
                depth=row['depth'],
                parent_path=row['parent_path'],
                node_type=row['node_type']
            ))

        return nodes

    def get_neighbors(
        self,
        project_id: int,
        center_path: str,
        max_depth: int = 2
    ) -> List[str]:
        """
        Get spatial neighbors within max_depth hops.

        Uses BFS to traverse spatial relations up to max_depth.

        Args:
            project_id: Project ID
            center_path: Path to center search around
            max_depth: Maximum traversal depth

        Returns:
            List of neighboring paths
        """
        visited = {center_path}
        queue = [(center_path, 0)]  # (path, depth)
        neighbors = []

        while queue:
            current_path, depth = queue.pop(0)

            if depth < max_depth:
                # Get all related paths (both directions)
                rows = self.execute("""
                    SELECT to_path FROM spatial_relations
                    WHERE project_id = ? AND from_path = ?
                    UNION
                    SELECT from_path FROM spatial_relations
                    WHERE project_id = ? AND to_path = ?
                """, (project_id, current_path, project_id, current_path), fetch_all=True)

                for row in (rows or []):
                    related_path = row[0]

                    if related_path not in visited:
                        visited.add(related_path)
                        neighbors.append(related_path)
                        queue.append((related_path, depth + 1))

        return neighbors

    def get_all_paths(self, project_id: int) -> List[str]:
        """
        Get all spatial paths for a project.

        Args:
            project_id: Project ID

        Returns:
            List of all paths
        """
        rows = self.execute("""
            SELECT full_path FROM spatial_nodes
            WHERE project_id = ?
            ORDER BY depth, full_path
        """, (project_id,), fetch_all=True)

        return [row['full_path'] for row in (rows or [])]

    # ========================================================================
    # Symbol Node Methods
    # ========================================================================

    def store_symbol_node(self, project_id: int, symbol: "SymbolNode") -> int:
        """Store a code symbol node (function, class, method).

        Args:
            project_id: Project ID
            symbol: SymbolNode instance

        Returns:
            Symbol node ID
        """
        from .models import SymbolNode

        cursor = self.execute("""
            INSERT OR IGNORE INTO symbol_nodes
            (project_id, name, file_path, line_number, symbol_kind, language,
             full_path, parent_class, signature, docstring, complexity_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            symbol.name,
            symbol.file_path,
            symbol.line_number,
            symbol.symbol_kind,
            symbol.language,
            symbol.full_path,
            symbol.parent_class,
            symbol.signature,
            symbol.docstring,
            symbol.complexity_score,
            self.now_timestamp()
        ))

        self.commit()

        # Get the ID
        row = self.execute(
            "SELECT id FROM symbol_nodes WHERE project_id = ? AND full_path = ?",
            (project_id, symbol.full_path),
            fetch_one=True,
        )
        return row['id'] if row else cursor.lastrowid

    def store_symbol_relation(self, project_id: int, from_symbol_id: int, to_symbol_id: int,
                             relation_type: str = "calls", strength: float = 1.0):
        """Store a relation between two symbols (calls, inherits, implements, etc).

        Args:
            project_id: Project ID
            from_symbol_id: Source symbol ID
            to_symbol_id: Target symbol ID
            relation_type: Type of relation (calls, inherits, implements, uses)
            strength: Strength score (0.0-1.0)
        """
        self.execute("""
            INSERT OR REPLACE INTO symbol_relations
            (from_symbol_id, to_symbol_id, project_id, relation_type, strength)
            VALUES (?, ?, ?, ?, ?)
        """, (
            from_symbol_id,
            to_symbol_id,
            project_id,
            relation_type,
            strength
        ))

        self.commit()

    def batch_store_symbol_nodes(self, project_id: int, symbols: List) -> int:
        """Store multiple symbol nodes in a single transaction.

        Args:
            project_id: Project ID
            symbols: List of SymbolNode instances

        Returns:
            Number of symbols stored
        """
        if not symbols:
            return 0

        cursor = self.db.conn.cursor()
        now = self.now_timestamp()

        # De-duplicate by full_path
        seen_paths = set()
        unique_symbols = []
        for symbol in symbols:
            if symbol.full_path not in seen_paths:
                seen_paths.add(symbol.full_path)
                unique_symbols.append(symbol)

        try:
            data = [(
                project_id,
                s.name,
                s.file_path,
                s.line_number,
                s.symbol_kind,
                s.language,
                s.full_path,
                s.parent_class,
                s.signature,
                s.docstring,
                s.complexity_score,
                now
            ) for s in unique_symbols]

            cursor.executemany("""
                INSERT OR IGNORE INTO symbol_nodes
                (project_id, name, file_path, line_number, symbol_kind, language,
                 full_path, parent_class, signature, docstring, complexity_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)

            self.commit()
            return len(unique_symbols)
        except Exception as e:
            self.db.conn.rollback()
            raise e

    def list_symbols_by_file(self, project_id: int, file_path: str) -> List:
        """List all symbols in a specific file.

        Args:
            project_id: Project ID
            file_path: File path

        Returns:
            List of symbol nodes (as dicts)
        """
        rows = self.execute("""
            SELECT * FROM symbol_nodes
            WHERE project_id = ? AND file_path = ?
            ORDER BY line_number
        """, (project_id, file_path), fetch_all=True)

        return [dict(row) for row in (rows or [])]

    def list_symbols_by_kind(self, project_id: int, symbol_kind: str) -> List:
        """List all symbols of a specific kind (function, class, method).

        Args:
            project_id: Project ID
            symbol_kind: Symbol kind (function, class, method, etc)

        Returns:
            List of symbol nodes (as dicts)
        """
        rows = self.execute("""
            SELECT * FROM symbol_nodes
            WHERE project_id = ? AND symbol_kind = ?
            ORDER BY file_path, line_number
        """, (project_id, symbol_kind), fetch_all=True)

        return [dict(row) for row in (rows or [])]

    def list_symbols_by_language(self, project_id: int, language: str) -> List:
        """List all symbols in a specific language.

        Args:
            project_id: Project ID
            language: Language (python, typescript, go, etc)

        Returns:
            List of symbol nodes (as dicts)
        """
        rows = self.execute("""
            SELECT * FROM symbol_nodes
            WHERE project_id = ? AND language = ?
            ORDER BY file_path, line_number
        """, (project_id, language), fetch_all=True)

        return [dict(row) for row in (rows or [])]

    def get_symbol_by_name(self, project_id: int, name: str, file_path: Optional[str] = None):
        """Get a specific symbol by name (optionally filtered by file).

        Args:
            project_id: Project ID
            name: Symbol name
            file_path: Optional file path filter

        Returns:
            Symbol node dict or None
        """
        if file_path:
            row = self.execute("""
                SELECT * FROM symbol_nodes
                WHERE project_id = ? AND name = ? AND file_path = ?
                LIMIT 1
            """, (project_id, name, file_path), fetch_one=True)
        else:
            row = self.execute("""
                SELECT * FROM symbol_nodes
                WHERE project_id = ? AND name = ?
                ORDER BY file_path, line_number
                LIMIT 1
            """, (project_id, name), fetch_one=True)

        return dict(row) if row else None

    def find_symbol_calls(self, project_id: int, from_symbol_id: int) -> List:
        """Find all symbols called by a given symbol.

        Args:
            project_id: Project ID
            from_symbol_id: Source symbol ID

        Returns:
            List of called symbol IDs
        """
        rows = self.execute("""
            SELECT to_symbol_id FROM symbol_relations
            WHERE project_id = ? AND from_symbol_id = ? AND relation_type = 'calls'
        """, (project_id, from_symbol_id), fetch_all=True)

        return [row['to_symbol_id'] for row in (rows or [])]

    def find_symbol_callers(self, project_id: int, to_symbol_id: int) -> List:
        """Find all symbols that call a given symbol.

        Args:
            project_id: Project ID
            to_symbol_id: Target symbol ID

        Returns:
            List of calling symbol IDs
        """
        rows = self.execute("""
            SELECT from_symbol_id FROM symbol_relations
            WHERE project_id = ? AND to_symbol_id = ? AND relation_type = 'calls'
        """, (project_id, to_symbol_id), fetch_all=True)

        return [row['from_symbol_id'] for row in (rows or [])]

    def find_complexity_hotspots(self, project_id: int, threshold: float = 10.0, limit: int = 20) -> List:
        """Find symbols with high cyclomatic complexity.

        Args:
            project_id: Project ID
            threshold: Complexity threshold
            limit: Maximum results

        Returns:
            List of high-complexity symbols
        """
        rows = self.execute("""
            SELECT * FROM symbol_nodes
            WHERE project_id = ? AND complexity_score >= ?
            ORDER BY complexity_score DESC
            LIMIT ?
        """, (project_id, threshold, limit), fetch_all=True)

        return [dict(row) for row in (rows or [])]
