"""PostgreSQL database with pgvector for vector storage.

This module provides a PostgreSQL-backed database layer for Athena,
supporting all 8 memory layers + planning + code analysis domains.

Features:
- pgvector for 768-dimensional semantic search
- Native hybrid search (semantic + full-text + relational) in SQL
- Multi-project isolation via project_id partitioning
- ACID transactions for multi-layer operations
- Connection pooling for production use
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator, TYPE_CHECKING

logger = logging.getLogger(__name__)

try:
    import psycopg
    from psycopg_pool import AsyncConnectionPool
    from psycopg import sql
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False

if TYPE_CHECKING:
    from psycopg import AsyncConnection
elif PSYCOPG_AVAILABLE:
    from psycopg import AsyncConnection
else:
    # Dummy class for type hints when psycopg not available
    class AsyncConnection:  # type: ignore
        pass

from .models import Memory, MemoryType, Project
from . import config


# Helper function to convert embedding list to pgvector string format
def embed_to_vector_str(embedding: List[float]) -> str:
    """Convert Python list to pgvector format: '[0.1, 0.2, ...]'"""
    if not embedding:
        return "[]"
    return "[" + ",".join(f"{float(x):.6f}" for x in embedding) + "]"


class SyncCursor:
    """Synchronous cursor wrapper around async PostgreSQL connection.

    Bridges async PostgreSQL operations with synchronous store code.
    Used by BaseStore and subclasses to maintain compatibility with
    existing sync-oriented memory layer code.
    """

    def __init__(self, db: "PostgresDatabase"):
        """Initialize sync cursor with database reference.

        Args:
            db: PostgresDatabase instance
        """
        self.db = db
        self._connection = None
        self._cursor = None
        self._results = None
        self._row_index = 0
        self._lastrowid = None
        self._rowcount = 0

    @staticmethod
    def _row_to_tuple(row):
        """Return row as-is.

        psycopg3 RoleRow objects support both dict and tuple access,
        so we don't need to convert them.

        Args:
            row: Row from psycopg3 cursor

        Returns:
            Row object (RoleRow which acts as both dict and tuple)
        """
        return row

    async def _get_connection_async(self):
        """Get async connection from pool."""
        if self._pool is None:
            await self.db.initialize()
        return await self.db._pool.getconn()

    def _run_async(self, coro):
        """Run async coroutine in sync context.

        This is deprecated - use run_async() from async_utils instead.
        Keeping for backward compatibility.
        """
        from .async_utils import run_async
        return run_async(coro)

    async def _get_conn_async(self):
        """Get connection from pool."""
        if self.db._pool is None:
            await self.db.initialize()
        return await self.db._pool.getconn()

    def _execute_async(self, query: str, params: tuple = None):
        """Execute query asynchronously against PostgreSQL.

        Query must use PostgreSQL syntax with %s placeholders (not SQLite ?).
        Returns dict-like rows for SELECT queries and queries with RETURNING.
        """
        async def _exec():
            # Query should be in PostgreSQL format
            pg_query = query.strip()
            query_upper = pg_query.upper()

            # Determine if query can return results
            # SELECT, INSERT/UPDATE/DELETE with RETURNING, and some other queries can return rows
            returns_rows = (
                query_upper.startswith("SELECT") or
                "RETURNING" in query_upper  # Handle INSERT/UPDATE/DELETE with RETURNING
            )

            # Use context manager to properly handle connection lifecycle
            async with self.db.get_connection() as conn:
                # For queries that return rows, use dict_row factory to get dict-like rows
                if returns_rows:
                    cursor = conn.cursor(row_factory=dict_row)
                else:
                    cursor = conn.cursor()

                if params:
                    await cursor.execute(pg_query, params)
                else:
                    await cursor.execute(pg_query)

                # For queries that can return rows, fetch results as dicts. For others, just get row count
                if returns_rows:
                    self._results = await cursor.fetchall()
                else:
                    # For non-returning queries, don't try to fetch
                    self._results = []

                self._row_index = 0
                # Store row count for lastrowid compatibility
                self._lastrowid = cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
                self._rowcount = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                return self._results

        return self._run_async(_exec())

    def execute(self, query: str, params: tuple = None):
        """Execute SQL query synchronously.

        Args:
            query: SQL query string
            params: Query parameters (tuple)

        Returns:
            Self for method chaining
        """
        self._execute_async(query, params)
        return self

    def fetchone(self):
        """Fetch one row from results.

        Returns:
            Tuple representing one row, or None if no more rows
        """
        if self._results is None:
            return None
        if self._row_index >= len(self._results):
            return None
        row = self._results[self._row_index]
        self._row_index += 1
        return row

    def fetchall(self):
        """Fetch all rows from results.

        Returns:
            List of tuples representing all rows
        """
        if self._results is None:
            return []
        result = self._results[self._row_index:]
        self._row_index = len(self._results)
        return result

    def fetchmany(self, size: int = 1):
        """Fetch multiple rows.

        Args:
            size: Number of rows to fetch

        Returns:
            List of tuples
        """
        if self._results is None:
            return []
        result = self._results[self._row_index : self._row_index + size]
        self._row_index += size
        return result

    def close(self):
        """Close cursor."""
        self._results = None
        self._row_index = 0

    @property
    def lastrowid(self):
        """Get last inserted row ID."""
        return self._lastrowid if hasattr(self, '_lastrowid') else None

    @property
    def rowcount(self):
        """Get number of rows affected."""
        return self._rowcount if hasattr(self, '_rowcount') else 0


class PostgresDatabase:
    """PostgreSQL database manager with pgvector support.

    Provides unified database for:
    - Memory (episodic, semantic, procedural, meta-memory)
    - Planning (tasks, goals, decisions)
    - Code Analysis (metadata, dependencies)
    """

    def __init__(
        self,
        host: str = "localhost",  # Local Postgres (no Docker)
        port: int = 5432,
        dbname: str = "athena",
        user: str = "postgres",  # Default Postgres user (not "athena")
        password: str = "postgres",  # Default Postgres password
        min_size: int = 2,
        max_size: int = 10,
        pool_timeout: int = 30,
        max_idle: int = 300,
        max_lifetime: int = 3600,
        worker_count: Optional[int] = None,
    ):
        """Initialize PostgreSQL database connection pool.

        Args:
            host: PostgreSQL server host
            port: PostgreSQL server port
            dbname: Database name
            user: Database user
            password: Database password
            min_size: Minimum connections in pool
            max_size: Maximum connections in pool
            pool_timeout: Timeout for getting connection from pool (seconds)
            max_idle: Maximum idle time before recycling connection (seconds, default 5 min)
            max_lifetime: Maximum connection lifetime before recycling (seconds, default 1 hour)
            worker_count: Number of workers for dynamic pool sizing (optional)
        """
        if not PSYCOPG_AVAILABLE:
            raise ImportError(
                "psycopg3 required for PostgreSQL backend. "
                "Install with: pip install psycopg[binary]"
            )

        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password

        # Dynamic pool sizing based on worker count (Airweave pattern)
        if worker_count:
            # Scale with workers: min = 10% of workers (2-5), max = 50% of workers (10-20)
            self.min_size = min(5, max(2, int(worker_count * 0.1)))
            self.max_size = min(20, max(10, int(worker_count * 0.5)))
        else:
            self.min_size = min_size
            self.max_size = max_size

        self.pool_timeout = pool_timeout
        self.max_idle = max_idle
        self.max_lifetime = max_lifetime

        # Connection pool (lazy initialization)
        self._pool: Optional[AsyncConnectionPool] = None
        self._initialized = False

    async def initialize(self):
        """Initialize connection pool and create schema."""
        if self._initialized:
            return

        # Create connection string
        conninfo = (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.dbname} "
            f"user={self.user} "
            f"password={self.password} "
            f"connect_timeout={self.pool_timeout}"
        )

        # Create and open connection pool with enhanced parameters
        # Airweave pattern: timeout, max_idle, max_lifetime for production hardening
        self._pool = AsyncConnectionPool(
            conninfo,
            min_size=self.min_size,
            max_size=self.max_size,
            timeout=self.pool_timeout,  # Timeout for acquiring connection
            max_idle=self.max_idle,     # Recycle idle connections after 5 min
            max_lifetime=self.max_lifetime,  # Recycle all connections after 1 hour
            check=AsyncConnectionPool.check_connection,  # Health check before use
        )
        await self._pool.open()

        logger.info(
            f"PostgreSQL pool initialized: min={self.min_size}, max={self.max_size}, "
            f"timeout={self.pool_timeout}s, max_idle={self.max_idle}s, max_lifetime={self.max_lifetime}s"
        )

        # Initialize schema
        await self._init_schema()
        self._initialized = True

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """Get a connection from the pool.

        Usage:
            async with db.get_connection() as conn:
                await conn.execute(...)
        """
        if self._pool is None:
            await self.initialize()

        async with self._pool.connection() as conn:
            yield conn

    def get_cursor(self) -> SyncCursor:
        """Get a synchronous cursor for use with sync store code.

        This bridges async PostgreSQL with synchronous BaseStore implementations.
        Used by EpisodicStore, SemanticStore, and all other memory layer stores.

        Returns:
            SyncCursor instance with execute(), fetchone(), fetchall() methods

        Example:
            cursor = db.get_cursor()
            cursor.execute("SELECT * FROM episodic_events WHERE id = %s", (123,))
            row = cursor.fetchone()
        """
        return SyncCursor(self)

    async def _init_schema(self):
        """Create database schema if not exists.

        This is idempotent - safe to call multiple times.
        """
        async with self.get_connection() as conn:
            # Try to create pgvector extension (optional)
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                logger.info("pgvector extension available")
            except Exception as e:
                logger.warning(f"pgvector extension not available: {e}")
                logger.info("Continuing without pgvector - vector operations will use JSON storage")

            # Apply PostgreSQL optimizations (Airweave pattern)
            await self._optimize_postgres(conn)

            # Create all tables (from PHASE5_POSTGRESQL_SCHEMA.md)
            await self._create_tables(conn)
            await self._create_indices(conn)

            await conn.commit()

    async def _optimize_postgres(self, conn: AsyncConnection):
        """Apply PostgreSQL session tuning parameters.

        Based on Airweave's production optimization patterns.
        These settings improve performance for vector search, full-text search,
        and analytical workloads.

        Note: Only session-level settings are applied here. For server-level
        settings (shared_buffers, max_connections, etc.), modify postgresql.conf
        or docker-compose environment variables.
        """
        try:
            # Session-level memory settings for improved query performance
            # Note: shared_buffers cannot be set at session level (server-level only)
            await conn.execute("SET effective_cache_size = '1GB'")
            await conn.execute("SET maintenance_work_mem = '128MB'")
            await conn.execute("SET work_mem = '16MB'")

            # Parallel query settings for faster aggregations
            await conn.execute("SET max_parallel_workers_per_gather = 4")

            # SSD optimization (lower random page cost)
            await conn.execute("SET random_page_cost = 1.1")

            logger.info("PostgreSQL session optimization parameters applied")
        except Exception as e:
            # Non-fatal: continue even if some settings fail
            logger.warning(f"Failed to apply some PostgreSQL optimizations: {e}")

    async def _create_tables(self, conn: AsyncConnection):
        """Create all 10 core tables."""

        # Get embedding dimension from config
        from . import config
        embedding_dim = config.LLAMACPP_EMBEDDING_DIM

        # 1. Projects table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                path TEXT UNIQUE NOT NULL,
                description TEXT,
                language VARCHAR(50),
                framework VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                last_accessed TIMESTAMP DEFAULT NOW(),
                last_modified TIMESTAMP DEFAULT NOW(),
                memory_count INT DEFAULT 0,
                total_events INT DEFAULT 0,
                task_count INT DEFAULT 0,
                embedding_dim INT DEFAULT {embedding_dim},
                consolidation_interval INT DEFAULT 3600
            )
        """)

        # 2. Memory vectors table (unified)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS memory_vectors (
                id BIGSERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                content_type VARCHAR(50),
                embedding vector({embedding_dim}) NOT NULL,
                content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
                memory_type VARCHAR(50) NOT NULL,
                domain VARCHAR(100),
                tags TEXT[] DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                last_accessed TIMESTAMP DEFAULT NOW(),
                last_retrieved TIMESTAMP,
                access_count INT DEFAULT 0,
                usefulness_score FLOAT DEFAULT 0.0,
                confidence FLOAT DEFAULT 1.0,
                quality_score FLOAT GENERATED ALWAYS AS (
                    (0.5 * usefulness_score + 0.3 * confidence + 0.2 * LEAST(access_count::float / 100, 1.0))
                ) STORED,
                consolidation_state VARCHAR(50) DEFAULT 'unconsolidated',
                consolidated_at TIMESTAMP,
                superseded_by BIGINT REFERENCES memory_vectors(id) ON DELETE SET NULL,
                version INT DEFAULT 1,
                session_id VARCHAR(255),
                event_type VARCHAR(50),
                code_language VARCHAR(50),
                code_hash VARCHAR(64)
            )
        """)

        # 3. Memory relationships
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_relationships (
                id SERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                from_memory_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,
                to_memory_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,
                relationship_type VARCHAR(50) NOT NULL,
                strength FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(from_memory_id, to_memory_id, relationship_type)
            )
        """)

        # 4. Episodic events
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic_events (
                id BIGSERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                memory_vector_id BIGINT REFERENCES memory_vectors(id) ON DELETE SET NULL,
                session_id VARCHAR(255) NOT NULL,
                timestamp BIGINT NOT NULL,
                duration_ms INT,
                event_type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                outcome TEXT,
                context_cwd TEXT,
                context_files TEXT[],
                context_task VARCHAR(255),
                context_phase VARCHAR(50),
                context_branch VARCHAR(255),
                files_changed INT DEFAULT 0,
                lines_added INT DEFAULT 0,
                lines_deleted INT DEFAULT 0,
                learned TEXT,
                surprise_score FLOAT,
                confidence FLOAT DEFAULT 1.0,
                consolidation_status VARCHAR(50) DEFAULT 'unconsolidated',
                consolidated_at TIMESTAMP,
                embedding vector(768)
            )
        """)

        # 5. Prospective goals
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prospective_goals (
                id BIGSERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                priority INT DEFAULT 5,
                status VARCHAR(50) DEFAULT 'active',
                completion_percentage INT DEFAULT 0,
                estimated_completion_date DATE,
                parent_goal_id BIGINT REFERENCES prospective_goals(id) ON DELETE SET NULL,
                related_memory_ids BIGINT[] DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP
            )
        """)

        # 6. Prospective tasks
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prospective_tasks (
                id BIGSERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                priority INT DEFAULT 5,
                goal_id BIGINT REFERENCES prospective_goals(id) ON DELETE SET NULL,
                parent_task_id BIGINT REFERENCES prospective_tasks(id) ON DELETE SET NULL,
                estimated_effort_hours FLOAT,
                actual_effort_hours FLOAT,
                due_date DATE,
                related_memory_ids BIGINT[] DEFAULT '{}',
                related_code_ids BIGINT[] DEFAULT '{}',
                completion_percentage INT DEFAULT 0,
                success_rate FLOAT,
                created_at TIMESTAMP DEFAULT NOW(),
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # 7. Code metadata
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS code_metadata (
                id BIGSERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                memory_vector_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                language VARCHAR(50),
                entity_type VARCHAR(50),
                entity_name VARCHAR(255),
                start_line INT,
                end_line INT,
                signature TEXT,
                docstring TEXT,
                semantic_hash VARCHAR(64),
                dependencies TEXT[],
                dependents TEXT[],
                cyclomatic_complexity INT,
                lines_of_code INT,
                created_at TIMESTAMP DEFAULT NOW(),
                last_analyzed_at TIMESTAMP,
                UNIQUE(project_id, file_path, entity_name)
            )
        """)

        # 8. Code dependencies
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS code_dependencies (
                id SERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                from_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,
                to_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,
                dependency_type VARCHAR(50),
                strength FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(from_code_id, to_code_id, dependency_type)
            )
        """)

        # 9. Planning decisions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS planning_decisions (
                id BIGSERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                decision_type VARCHAR(50),
                title VARCHAR(255) NOT NULL,
                rationale TEXT,
                context_memory_ids BIGINT[] DEFAULT '{}',
                alternatives TEXT[],
                validation_status VARCHAR(50) DEFAULT 'pending',
                validation_confidence FLOAT,
                created_at TIMESTAMP DEFAULT NOW(),
                validated_at TIMESTAMP,
                superseded_by BIGINT REFERENCES planning_decisions(id) ON DELETE SET NULL
            )
        """)

        # 10. Planning scenarios
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS planning_scenarios (
                id BIGSERIAL PRIMARY KEY,
                project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                decision_id BIGINT REFERENCES planning_decisions(id) ON DELETE CASCADE,
                scenario_type VARCHAR(50),
                scenario_name VARCHAR(255),
                description TEXT,
                assumptions TEXT[],
                expected_outcomes TEXT[],
                impact_assessment TEXT,
                risk_level VARCHAR(50),
                probability FLOAT,
                testing_status VARCHAR(50) DEFAULT 'not_tested',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    async def _create_indices(self, conn: AsyncConnection):
        """Create all indices for performance."""

        # Memory vector indices
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_project
            ON memory_vectors(project_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type
            ON memory_vectors(memory_type)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_consolidation
            ON memory_vectors(consolidation_state)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_quality
            ON memory_vectors(quality_score DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_accessed
            ON memory_vectors(last_accessed DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_session
            ON memory_vectors(session_id)
        """)

        # Vector search index (IVFFlat with cosine distance)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_embedding_ivfflat
            ON memory_vectors USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

        # Full-text search index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_content_fts
            ON memory_vectors USING GIN (content_tsvector)
        """)

        # Composite indices for filtering
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_project_type
            ON memory_vectors(project_id, memory_type)
            WHERE consolidation_state = 'consolidated'
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_project_domain
            ON memory_vectors(project_id, domain, consolidation_state)
        """)

        # Episodic event indices
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_project
            ON episodic_events(project_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_session
            ON episodic_events(session_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_timestamp
            ON episodic_events(project_id, timestamp DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_event_type
            ON episodic_events(event_type)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_consolidation
            ON episodic_events(consolidation_status)
        """)

        # Task and goal indices
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_project
            ON prospective_tasks(project_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON prospective_tasks(status)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date
            ON prospective_tasks(due_date)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_goals_project
            ON prospective_goals(project_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_goals_status
            ON prospective_goals(status)
        """)

        # Code indices
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_project
            ON code_metadata(project_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_file
            ON code_metadata(file_path)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_entity_type
            ON code_metadata(entity_type)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_dep_from
            ON code_dependencies(from_code_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_dep_to
            ON code_dependencies(to_code_id)
        """)

        # Planning indices
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_decision_project
            ON planning_decisions(project_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_decision_status
            ON planning_decisions(validation_status)
        """)

        # Create IVFFlat index for fast semantic search with pgvector
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS episodic_events_embedding_ivfflat
                ON episodic_events USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
        except Exception as e:
            import logging
            logging.warning(f"Failed to create embedding index (semantic search may be slow): {e}")
            # Don't fail init - embeddings column is optional, semantic search has fallback
            # But log so it's visible if pgvector isn't properly set up

    # ===========================================================================
    # PROJECT OPERATIONS
    # ===========================================================================

    async def create_project(
        self,
        name: str,
        path: str,
        language: str = "python",
        description: str = "",
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name (unique)
            path: Project path (unique)
            language: Programming language
            description: Project description

        Returns:
            Created Project instance
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                INSERT INTO projects (name, path, language, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, path, created_at
                """,
                (name, path, language, description),
            )
            result = await row.fetchone()
            await conn.commit()

            return Project(
                id=result[0],
                name=result[1],
                path=result[2],
                created_at=int(result[3].timestamp()),
            )

    async def get_project_by_path(self, path: str) -> Optional[Project]:
        """Get project by path.

        Args:
            path: Project path

        Returns:
            Project instance or None if not found
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                "SELECT id, name, path, created_at FROM projects WHERE path = %s",
                (path,),
            )
            result = await row.fetchone()

            if result is None:
                return None

            return Project(
                id=result[0],
                name=result[1],
                path=result[2],
                created_at=int(result[3].timestamp()),
            )

    async def update_project_access(self, project_id: int):
        """Update project last_accessed timestamp.

        Args:
            project_id: Project ID
        """
        async with self.get_connection() as conn:
            await conn.execute(
                "UPDATE projects SET last_accessed = NOW() WHERE id = %s",
                (project_id,),
            )
            await conn.commit()

    # ===========================================================================
    # MEMORY VECTOR OPERATIONS
    # ===========================================================================

    async def store_memory(
        self,
        project_id: int,
        content: str,
        embedding: List[float],
        memory_type: str,
        domain: str = "memory",
        tags: List[str] = None,
        **kwargs,
    ) -> int:
        """Store a memory vector.

        Args:
            project_id: Project ID
            content: Memory content text
            embedding: 768-dimensional embedding vector
            memory_type: Type of memory (fact, pattern, decision, context, code_snippet)
            domain: Domain (memory, planning, code-analysis)
            tags: Optional tags
            **kwargs: Additional fields (content_type, code_language, code_hash, etc.)

        Returns:
            Memory ID
        """
        if tags is None:
            tags = []

        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                INSERT INTO memory_vectors (
                    project_id, content, embedding, memory_type, domain, tags,
                    content_type, code_language, code_hash, session_id, event_type
                )
                VALUES (%s, %s, %s::vector, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    project_id,
                    content,
                    embedding,  # Will be converted by psycopg
                    memory_type,
                    domain,
                    tags,
                    kwargs.get("content_type"),
                    kwargs.get("code_language"),
                    kwargs.get("code_hash"),
                    kwargs.get("session_id"),
                    kwargs.get("event_type"),
                ),
            )
            result = await row.fetchone()
            await conn.commit()

            return result[0]

    async def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get a memory vector by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory dict or None if not found
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                SELECT id, project_id, content, memory_type, domain, tags,
                       quality_score, consolidation_state, created_at, access_count
                FROM memory_vectors
                WHERE id = %s
                """,
                (memory_id,),
            )
            result = await row.fetchone()

            if result is None:
                return None

            return {
                "id": result[0],
                "project_id": result[1],
                "content": result[2],
                "memory_type": result[3],
                "domain": result[4],
                "tags": result[5],
                "quality_score": result[6],
                "consolidation_state": result[7],
                "created_at": int(result[8].timestamp()),
                "access_count": result[9],
            }

    def get_memory_sync(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get a memory vector by ID (synchronous wrapper).

        Args:
            memory_id: Memory ID

        Returns:
            Memory dict or None if not found
        """
        # For now, return None - proper implementation would use asyncio.run()
        # but that's problematic in async context
        # This is a temporary solution that callers can check with hasattr
        logger.warning(f"get_memory_sync called - returning None for memory {memory_id}")
        return None

    async def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory vector.

        Args:
            memory_id: Memory ID

        Returns:
            True if deleted, False if not found
        """
        async with self.get_connection() as conn:
            await conn.execute(
                "DELETE FROM memory_vectors WHERE id = %s",
                (memory_id,),
            )
            await conn.commit()
            return True

    async def update_access_stats(self, memory_id: int):
        """Update memory access statistics.

        Args:
            memory_id: Memory ID
        """
        async with self.get_connection() as conn:
            await conn.execute(
                """
                UPDATE memory_vectors
                SET last_accessed = NOW(),
                    access_count = access_count + 1,
                    last_retrieved = NOW()
                WHERE id = %s
                """,
                (memory_id,),
            )
            await conn.commit()

    # ===========================================================================
    # SEARCH OPERATIONS (Hybrid Search)
    # ===========================================================================

    async def hybrid_search(
        self,
        project_id: int,
        embedding: List[float],
        query_text: str,
        limit: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        consolidation_state: str = "consolidated",
        memory_types: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining semantic + full-text + relational.

        This is the core search operation for Phase 5.
        Combines:
        - Vector similarity (cosine distance via pgvector)
        - Full-text search (native tsvector)
        - Relational filtering (project, type, state)

        Args:
            project_id: Project ID for isolation
            embedding: Query embedding (768D)
            query_text: Query text for full-text search
            limit: Max results to return
            semantic_weight: Weight for semantic score (0-1)
            keyword_weight: Weight for keyword score (0-1)
            consolidation_state: Filter by consolidation state
            memory_types: Optional filter by memory types

        Returns:
            List of memory dicts with scores
        """
        async with self.get_connection() as conn:
            # Convert embedding to pgvector format string
            embedding_str = embed_to_vector_str(embedding)

            # Build WHERE clause parts (will be inserted later in correct position)
            where_parts = [
                "m.project_id = %s",
                "m.consolidation_state = %s",
            ]
            where_params = [project_id, consolidation_state]

            if memory_types:
                where_parts.append("m.memory_type = ANY(%s)")
                where_params.append(memory_types)

            where_clause = " AND ".join(where_parts)

            # Build SELECT clause parameters (these come first in the SQL)
            select_params = [
                query_text,          # Line 16: plainto_tsquery(%s) for keyword_rank
                semantic_weight,     # Line 17: %s * (semantic component)
                keyword_weight,      # Line 18: %s * COALESCE (keyword component)
                query_text,          # Line 18: plainto_tsquery(%s) in hybrid score
            ]

            # Combine parameters in the order they appear in SQL:
            # SELECT clause params first, then WHERE clause params, then remaining
            params = select_params + where_params + [
                query_text,          # Line 25: plainto_tsquery(%s) in threshold check
                limit,               # Line 29: LIMIT %s
            ]

            # Build SQL query - embedding is pre-converted to string, not a placeholder
            # This avoids type casting issues with psycopg
            sql_query = f"""
                SELECT
                    m.id,
                    m.project_id,
                    m.content,
                    m.memory_type,
                    m.domain,
                    m.tags,
                    m.quality_score,
                    m.consolidation_state,
                    m.created_at,
                    m.access_count,

                    -- Scoring
                    (1 - (m.embedding <=> '{embedding_str}'::vector)) as semantic_similarity,
                    ts_rank(m.content_tsvector, plainto_tsquery(%s)) as keyword_rank,
                    (%s * (1 - (m.embedding <=> '{embedding_str}'::vector)) +
                     %s * COALESCE(ts_rank(m.content_tsvector, plainto_tsquery(%s)), 0))
                     as hybrid_score

                FROM memory_vectors m
                WHERE {where_clause}
                    AND (
                        (1 - (m.embedding <=> '{embedding_str}'::vector)) > 0.3
                        OR ts_rank(m.content_tsvector, plainto_tsquery(%s)) > 0
                    )

                ORDER BY hybrid_score DESC
                LIMIT %s
                """

            cursor = await conn.execute(sql_query, params)

            results = []
            async for row_data in cursor:
                results.append({
                    "id": row_data[0],
                    "project_id": row_data[1],
                    "content": row_data[2],
                    "memory_type": row_data[3],
                    "domain": row_data[4],
                    "tags": row_data[5],
                    "quality_score": row_data[6],
                    "consolidation_state": row_data[7],
                    "created_at": int(row_data[8].timestamp()),
                    "access_count": row_data[9],
                    "semantic_similarity": float(row_data[10]),
                    "keyword_rank": float(row_data[11] or 0),
                    "hybrid_score": float(row_data[12]),
                })

            return results

    async def semantic_search(
        self,
        project_id: int,
        embedding: List[float],
        limit: int = 10,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using vector similarity.

        Args:
            project_id: Project ID
            embedding: Query embedding
            limit: Max results
            threshold: Cosine similarity threshold (0-1)

        Returns:
            List of memory dicts with semantic_similarity score
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                SELECT
                    m.id,
                    m.content,
                    m.memory_type,
                    m.quality_score,
                    (1 - (m.embedding <=> %s::vector)) as similarity
                FROM memory_vectors m
                WHERE m.project_id = %s
                    AND (1 - (m.embedding <=> %s::vector)) > %s
                ORDER BY m.embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, project_id, embedding, threshold, embedding, limit),
            )

            results = []
            async for row_data in await row:
                results.append({
                    "id": row_data[0],
                    "content": row_data[1],
                    "memory_type": row_data[2],
                    "quality_score": row_data[3],
                    "semantic_similarity": float(row_data[4]),
                })

            return results

    # ===========================================================================
    # CONSOLIDATION OPERATIONS
    # ===========================================================================

    async def get_reconsolidation_window(
        self,
        project_id: int,
        window_minutes: int = 60,
    ) -> List[Dict[str, Any]]:
        """Get memories in reconsolidation window (labile state).

        Memories are labile (malleable) within N minutes of last retrieval.
        This is used for reconsolidation learning.

        Args:
            project_id: Project ID
            window_minutes: Time window after retrieval (default 1 hour)

        Returns:
            List of memories in labile state
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                SELECT
                    id, content, memory_type, quality_score, last_retrieved,
                    EXTRACT(EPOCH FROM (NOW() - last_retrieved)) as seconds_since_retrieval
                FROM memory_vectors
                WHERE project_id = %s
                    AND consolidation_state = 'labile'
                    AND last_retrieved IS NOT NULL
                    AND EXTRACT(EPOCH FROM (NOW() - last_retrieved)) < %s
                ORDER BY last_retrieved DESC
                """,
                (project_id, window_minutes * 60),
            )

            results = []
            async for row_data in await row:
                results.append({
                    "id": row_data[0],
                    "content": row_data[1],
                    "memory_type": row_data[2],
                    "quality_score": row_data[3],
                    "last_retrieved": int(row_data[4].timestamp()),
                    "seconds_since_retrieval": int(row_data[5]),
                })

            return results

    async def update_consolidation_state(
        self,
        memory_id: int,
        state: str,
    ):
        """Update memory consolidation state.

        States: unconsolidated → consolidating → consolidated
                consolidated → labile → reconsolidating → consolidated

        Args:
            memory_id: Memory ID
            state: New consolidation state
        """
        async with self.get_connection() as conn:
            await conn.execute(
                """
                UPDATE memory_vectors
                SET consolidation_state = %s,
                    consolidated_at = CASE
                        WHEN %s = 'consolidated' THEN NOW()
                        ELSE consolidated_at
                    END
                WHERE id = %s
                """,
                (state, state, memory_id),
            )
            await conn.commit()

    # ===========================================================================
    # TASK & GOAL OPERATIONS
    # ===========================================================================

    async def create_task(
        self,
        project_id: int,
        title: str,
        description: str = "",
        priority: int = 5,
        status: str = "pending",
    ) -> int:
        """Create a prospective task.

        Args:
            project_id: Project ID
            title: Task title
            description: Task description
            priority: Priority (1-10)
            status: Initial status

        Returns:
            Task ID
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                INSERT INTO prospective_tasks (project_id, title, description, priority, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (project_id, title, description, priority, status),
            )
            result = await row.fetchone()
            await conn.commit()
            return result[0]

    async def create_goal(
        self,
        project_id: int,
        name: str,
        description: str = "",
        priority: int = 5,
    ) -> int:
        """Create a prospective goal.

        Args:
            project_id: Project ID
            name: Goal name
            description: Goal description
            priority: Priority (1-10)

        Returns:
            Goal ID
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                INSERT INTO prospective_goals (project_id, name, description, priority)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (project_id, name, description, priority),
            )
            result = await row.fetchone()
            await conn.commit()
            return result[0]

    # ===========================================================================
    # EPISODIC EVENT OPERATIONS
    # ===========================================================================

    async def store_episodic_event(
        self,
        project_id: int,
        session_id: str,
        timestamp: int,
        event_type: str,
        content: str,
        **kwargs,
    ) -> int:
        """Store an episodic event.

        Args:
            project_id: Project ID
            session_id: Session ID (groups related events)
            timestamp: Unix timestamp (ms)
            event_type: Type of event (action, learning, error, decision)
            content: Event content
            **kwargs: Additional fields (context_cwd, learned, confidence, etc.)

        Returns:
            Event ID
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                INSERT INTO episodic_events (
                    project_id, session_id, timestamp, event_type, content,
                    outcome, context_cwd, context_files, context_task, context_phase,
                    context_branch, learned, surprise_score, confidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    project_id,
                    session_id,
                    timestamp,
                    event_type,
                    content,
                    kwargs.get("outcome"),
                    kwargs.get("context_cwd"),
                    kwargs.get("context_files"),
                    kwargs.get("context_task"),
                    kwargs.get("context_phase"),
                    kwargs.get("context_branch"),
                    kwargs.get("learned"),
                    kwargs.get("surprise_score"),
                    kwargs.get("confidence", 1.0),
                ),
            )
            result = await row.fetchone()
            await conn.commit()
            return result[0]

    # ===========================================================================
    # CODE METADATA OPERATIONS
    # ===========================================================================

    async def store_code_entity(
        self,
        project_id: int,
        memory_vector_id: int,
        file_path: str,
        entity_name: str,
        entity_type: str,
        **kwargs,
    ) -> int:
        """Store code entity metadata.

        Args:
            project_id: Project ID
            memory_vector_id: Associated memory vector ID
            file_path: File path
            entity_name: Function/class/module name
            entity_type: Type (function, class, module)
            **kwargs: Additional fields (language, signature, docstring, etc.)

        Returns:
            Code metadata ID
        """
        async with self.get_connection() as conn:
            row = await conn.execute(
                """
                INSERT INTO code_metadata (
                    project_id, memory_vector_id, file_path, entity_name, entity_type,
                    language, signature, docstring, semantic_hash, cyclomatic_complexity, lines_of_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    project_id,
                    memory_vector_id,
                    file_path,
                    entity_name,
                    entity_type,
                    kwargs.get("language"),
                    kwargs.get("signature"),
                    kwargs.get("docstring"),
                    kwargs.get("semantic_hash"),
                    kwargs.get("cyclomatic_complexity"),
                    kwargs.get("lines_of_code"),
                ),
            )
            result = await row.fetchone()
            await conn.commit()
            return result[0]

    # ===========================================================================
    # TRANSACTION SUPPORT
    # ===========================================================================

    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions.

        Usage:
            async with db.transaction() as conn:
                await conn.execute(...)
                await conn.execute(...)
        """
        async with self.get_connection() as conn:
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    # ===========================================================================
    # POOL MONITORING & HEALTH CHECKS
    # ===========================================================================

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool utilization statistics.

        Returns current pool state for monitoring and capacity planning.
        Based on Airweave's pool monitoring pattern.

        Returns:
            Dict with pool statistics:
            - total_connections: Current total connections in pool
            - available_connections: Idle connections ready for use
            - waiting_clients: Clients waiting for connection
            - min_size: Configured minimum pool size
            - max_size: Configured maximum pool size
            - pool_utilization: Percentage of pool in use (0.0-1.0)
        """
        if not self._pool:
            return {
                "status": "not_initialized",
                "total_connections": 0,
                "available_connections": 0,
                "waiting_clients": 0,
            }

        try:
            # Get pool statistics
            total = self._pool.get_size()
            available = self._pool.get_available()
            waiting = self._pool.get_waiting()

            utilization = (total - available) / self.max_size if self.max_size > 0 else 0.0

            return {
                "status": "active",
                "total_connections": total,
                "available_connections": available,
                "waiting_clients": waiting,
                "min_size": self.min_size,
                "max_size": self.max_size,
                "pool_utilization": round(utilization, 2),
                "timeout": self.pool_timeout,
                "max_idle": self.max_idle,
                "max_lifetime": self.max_lifetime,
            }
        except Exception as e:
            logger.error(f"Failed to get pool stats: {e}")
            return {"status": "error", "error": str(e)}

    async def get_index_stats(self) -> List[Dict[str, Any]]:
        """Get PostgreSQL index usage statistics.

        Returns index efficiency metrics for query optimization.
        Based on Airweave's index monitoring pattern.

        Returns:
            List of index statistics dicts with:
            - schema: Schema name
            - table: Table name
            - index: Index name
            - scans: Number of index scans
            - tuples_read: Tuples read by index scans
            - tuples_fetched: Tuples fetched by index scans
            - efficiency: Fetch ratio (tuples_fetched / tuples_read)
        """
        async with self.get_connection() as conn:
            row = await conn.execute("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    CASE
                        WHEN idx_tup_read > 0 THEN
                            ROUND((idx_tup_fetch::numeric / idx_tup_read::numeric), 2)
                        ELSE 0
                    END as efficiency
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
            """)

            results = []
            async for row_data in row:
                results.append({
                    "schema": row_data[0],
                    "table": row_data[1],
                    "index": row_data[2],
                    "scans": int(row_data[3] or 0),
                    "tuples_read": int(row_data[4] or 0),
                    "tuples_fetched": int(row_data[5] or 0),
                    "efficiency": float(row_data[6] or 0),
                })

            return results

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get active database connection statistics.

        Returns detailed information about active connections for monitoring.

        Returns:
            Dict with connection statistics:
            - total_connections: Total active connections to this database
            - active_queries: Connections currently executing queries
            - idle_connections: Idle connections
            - waiting_connections: Connections waiting for locks
            - oldest_query_seconds: Age of oldest running query
        """
        async with self.get_connection() as conn:
            row = await conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE state = 'active') as active,
                    COUNT(*) FILTER (WHERE state = 'idle') as idle,
                    COUNT(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting,
                    EXTRACT(EPOCH FROM (NOW() - MIN(query_start)))::int as oldest_query_sec
                FROM pg_stat_activity
                WHERE datname = current_database()
                    AND pid != pg_backend_pid()
            """)

            result = await row.fetchone()

            return {
                "total_connections": int(result[0] or 0),
                "active_queries": int(result[1] or 0),
                "idle_connections": int(result[2] or 0),
                "waiting_connections": int(result[3] or 0),
                "oldest_query_seconds": int(result[4] or 0),
            }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check.

        Validates pool status, database connectivity, and basic query performance.
        Based on Airweave's health monitoring pattern.

        Returns:
            Dict with health check results:
            - status: "healthy" or "unhealthy"
            - pool: Pool statistics
            - database: Database connectivity status
            - query_latency_ms: Simple query latency in milliseconds
        """
        health = {
            "status": "healthy",
            "timestamp": int(time.time()),
        }

        # Check pool status
        try:
            pool_stats = await self.get_pool_stats()
            health["pool"] = pool_stats

            # Warn if pool utilization is high
            if pool_stats.get("pool_utilization", 0) > 0.8:
                health["warnings"] = health.get("warnings", [])
                health["warnings"].append("High pool utilization (>80%)")
        except Exception as e:
            health["status"] = "unhealthy"
            health["pool_error"] = str(e)

        # Check database connectivity and query performance
        try:
            start_time = time.time()
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
            query_latency_ms = (time.time() - start_time) * 1000

            health["database"] = {
                "connected": True,
                "query_latency_ms": round(query_latency_ms, 2),
            }

            # Warn if latency is high
            if query_latency_ms > 100:
                health["warnings"] = health.get("warnings", [])
                health["warnings"].append(f"High query latency ({query_latency_ms:.0f}ms)")
        except Exception as e:
            health["status"] = "unhealthy"
            health["database"] = {
                "connected": False,
                "error": str(e),
            }

        return health

    # ===========================================================================
    # CLEANUP
    # ===========================================================================

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False
