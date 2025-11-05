"""Database query optimizer and index management."""

from datetime import datetime
from typing import Optional

from athena.core.database import Database


class IndexDefinition:
    """Definition of a database index."""

    def __init__(
        self,
        name: str,
        table: str,
        columns: list[str],
        unique: bool = False,
        partial_where: Optional[str] = None,
    ):
        """Initialize index definition.

        Args:
            name: Index name
            table: Table name
            columns: Columns to index
            unique: Whether index is unique
            partial_where: Partial index WHERE clause
        """
        self.name = name
        self.table = table
        self.columns = columns
        self.unique = unique
        self.partial_where = partial_where

    def get_create_sql(self) -> str:
        """Generate CREATE INDEX SQL."""
        unique_clause = "UNIQUE " if self.unique else ""
        col_list = ", ".join(self.columns)

        sql = f"CREATE {unique_clause}INDEX IF NOT EXISTS {self.name} ON {self.table}({col_list})"

        if self.partial_where:
            sql += f" WHERE {self.partial_where}"

        return sql


class QueryOptimizer:
    """Optimizer for database queries and indexes."""

    # Recommended indexes for memory-mcp tables
    RECOMMENDED_INDEXES = [
        # CodeArtifact indexes
        IndexDefinition("idx_code_entities_project_file", "code_entities", ["project_id", "file_path"]),
        IndexDefinition("idx_code_entities_type", "code_entities", ["entity_type"]),
        IndexDefinition("idx_complexity_metrics_level", "complexity_metrics", ["cyclomatic_level"]),
        IndexDefinition("idx_code_diffs_entity", "code_diffs", ["entity_id", "created_at"]),
        IndexDefinition("idx_dependencies_from_to", "dependencies", ["from_entity_id", "to_entity_id"]),

        # IDEContext indexes
        IndexDefinition("idx_ide_files_open_status", "ide_files", ["project_id", "is_open"]),
        IndexDefinition("idx_cursor_positions_timestamp", "cursor_positions", ["file_id", "timestamp"]),
        IndexDefinition("idx_git_status_staged", "git_status", ["project_id", "is_staged"]),
        IndexDefinition("idx_git_diffs_file", "git_diffs", ["project_id", "file_path", "captured_at"]),
        IndexDefinition("idx_snapshots_project_time", "ide_context_snapshots", ["project_id", "captured_at"]),
        IndexDefinition("idx_activity_file_time", "ide_activity", ["project_id", "file_path", "timestamp"]),

        # Episodic memory indexes (if available)
        IndexDefinition("idx_episodic_session_type", "episodic_events", ["session_id", "event_type"], partial_where="session_id IS NOT NULL"),
        IndexDefinition("idx_episodic_timestamp_range", "episodic_events", ["timestamp"], partial_where="timestamp > datetime('now', '-7 days')"),

        # Semantic memory indexes (if available)
        IndexDefinition("idx_semantic_usefulness", "semantic_memories", ["usefulness"], partial_where="usefulness > 0.3"),

        # Safety indexes (if available)
        IndexDefinition("idx_approval_status", "approval_requests", ["status", "created_at"]),
        IndexDefinition("idx_audit_risk_level", "audit_entries", ["risk_level", "success"]),
    ]

    def __init__(self, db: Database):
        """Initialize query optimizer.

        Args:
            db: Database connection
        """
        self.db = db

    def create_indexes(self, skip_existing: bool = True) -> dict:
        """Create recommended indexes.

        Args:
            skip_existing: Skip if index already exists

        Returns:
            Dictionary with creation status
        """
        created = 0
        skipped = 0
        failed = 0

        cursor = self.db.conn.cursor()

        for index_def in self.RECOMMENDED_INDEXES:
            try:
                sql = index_def.get_create_sql()
                cursor.execute(sql)
                self.db.conn.commit()
                created += 1
            except Exception as e:
                if skip_existing and "already exists" in str(e).lower():
                    skipped += 1
                else:
                    failed += 1
                    print(f"Error creating index {index_def.name}: {e}")

        return {
            "created": created,
            "skipped": skipped,
            "failed": failed,
            "total": len(self.RECOMMENDED_INDEXES),
        }

    def analyze_performance(self) -> dict:
        """Analyze current database performance.

        Returns:
            Dictionary with performance metrics
        """
        cursor = self.db.conn.cursor()
        stats = {
            "timestamp": datetime.now().isoformat(),
            "tables": {},
            "indexes": {},
        }

        try:
            # Get table statistics
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = cursor.fetchall()

            for table_row in tables:
                table = table_row[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row_count = cursor.fetchone()[0]

                    # Get approximate size using PRAGMA page_count
                    try:
                        cursor.execute("PRAGMA page_count()")
                        page_count_row = cursor.fetchone()
                        page_count = page_count_row[0] if page_count_row else 0
                        cursor.execute("PRAGMA page_size()")
                        page_size_row = cursor.fetchone()
                        page_size = page_size_row[0] if page_size_row else 4096
                        size_kb = (page_count * page_size) // 1024
                    except:
                        size_kb = 0

                    stats["tables"][table] = {
                        "rows": row_count,
                        "size_kb": size_kb,
                    }
                except Exception as e:
                    print(f"Error analyzing table {table}: {e}")

            # Get index statistics
            cursor.execute(
                "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
            indexes = cursor.fetchall()

            for idx_row in indexes:
                idx_name, table = idx_row
                stats["indexes"][idx_name] = {
                    "table": table,
                }

        except Exception as e:
            print(f"Error analyzing performance: {e}")

        return stats

    def get_query_plan(self, query: str, params: tuple = ()) -> list[dict]:
        """Get EXPLAIN QUERY PLAN for query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            List of plan steps
        """
        cursor = self.db.conn.cursor()

        try:
            # Prepare query with parameters
            explain_query = f"EXPLAIN QUERY PLAN {query}"

            cursor.execute(explain_query, params)
            results = cursor.fetchall()

            plan = []
            for row in results:
                plan.append({
                    "id": row[0],
                    "parent": row[1],
                    "notused": row[2],
                    "detail": row[3],
                })

            return plan
        except Exception as e:
            print(f"Error getting query plan: {e}")
            return []

    def optimize_query(self, query: str, params: tuple = ()) -> dict:
        """Analyze query and suggest optimizations.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Dictionary with query analysis and suggestions
        """
        plan = self.get_query_plan(query, params)

        suggestions = []

        # Check for full table scans
        for step in plan:
            detail = step.get("detail", "").upper()
            if "SCAN" in detail and "SEARCH" not in detail:
                suggestions.append("Uses table scan - consider adding index")
            if "TEMP" in detail:
                suggestions.append("Uses temporary table - may need query restructuring")
            if "MATERIALIZE" in detail:
                suggestions.append("Materializes subquery - consider rewriting")

        return {
            "query": query,
            "plan": plan,
            "suggestions": suggestions,
            "is_optimized": len(suggestions) == 0,
        }

    def get_slow_queries(self, execution_times: dict[str, float], threshold_ms: float = 100.0) -> list[str]:
        """Identify slow queries.

        Args:
            execution_times: Dictionary of query -> execution_time_ms
            threshold_ms: Threshold for slow query (default: 100ms)

        Returns:
            List of slow queries
        """
        return [
            query for query, time_ms in execution_times.items()
            if time_ms > threshold_ms
        ]

    def suggest_indexes_for_query(self, query: str) -> list[dict]:
        """Suggest indexes that might help query.

        Args:
            query: SQL query

        Returns:
            List of suggested index definitions
        """
        suggestions = []

        # Parse WHERE clauses
        if "WHERE" in query.upper():
            # Extract column names from WHERE clause
            # This is simplified - real implementation would parse AST
            where_start = query.upper().find("WHERE")
            where_clause = query[where_start:].upper()

            common_columns = ["project_id", "file_path", "entity_type", "status", "timestamp"]

            for col in common_columns:
                if col.upper() in where_clause and f"INDEX ON {col}" not in query:
                    suggestions.append({
                        "column": col,
                        "reason": f"Used in WHERE clause of query",
                        "type": "single-column",
                    })

        # Suggest composite indexes for JOINs
        if "JOIN" in query.upper():
            suggestions.append({
                "reason": "Query uses JOIN - consider composite index on join keys",
                "type": "multi-column",
            })

        return suggestions

    def get_statistics(self) -> dict:
        """Get overall database statistics.

        Returns:
            Dictionary with stats
        """
        cursor = self.db.conn.cursor()
        stats = {}

        try:
            # Get page statistics
            cursor.execute("PRAGMA page_count()")
            page_count = cursor.fetchone()[0]

            cursor.execute("PRAGMA page_size()")
            page_size = cursor.fetchone()[0]

            stats["database_size_mb"] = (page_count * page_size) / (1024 * 1024)

            # Get index count
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
            stats["index_count"] = cursor.fetchone()[0]

            # Get table count
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            stats["table_count"] = cursor.fetchone()[0]

        except Exception as e:
            print(f"Error getting statistics: {e}")

        return stats
