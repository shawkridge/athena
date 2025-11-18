"""Database store for code artifact analysis and persistence."""

import json
from datetime import datetime
from typing import Any, Optional

from athena.core.database import Database

from .models import (
    CodeDependencyGraph,
    CodeDiff,
    CodeEntity,
    CodeQualityIssue,
    ComplexityMetrics,
    Dependency,
    EntityType,
    TestCoverage,
    TypeSignature,
)


class CodeArtifactStore:
    """Store for managing code artifacts, metrics, and analysis."""

    def __init__(self, db: Database):
        """Initialize store with database connection."""
        self.db = db

    # ==================== HELPER METHODS ====================

    def execute(
        self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False
    ) -> Any:
        """Execute SQL query with consistent error handling.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return first row only
            fetch_all: Return all rows as list

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

        except Exception:
            # rollback handled by cursor context
            raise

    def commit(self):
        """Commit database transaction."""
        # commit handled by cursor context

    @staticmethod
    def serialize_json(obj: Any) -> Optional[str]:
        """Safely serialize object to JSON.

        Args:
            obj: Object to serialize

        Returns:
            JSON string or None
        """
        return json.dumps(obj) if obj is not None else None

    @staticmethod
    def deserialize_json(json_str: str, default=None):
        """Safely deserialize JSON string.

        Args:
            json_str: JSON string to deserialize
            default: Default value if deserialization fails

        Returns:
            Deserialized object or default
        """
        if not json_str:
            return default
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default

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
        return datetime.fromtimestamp(ts)

    def _ensure_schema(self):
        """Create database tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Code entities table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS code_entities (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                column_offset INTEGER DEFAULT 0,
                docstring TEXT,
                is_public BOOLEAN DEFAULT 1,
                is_deprecated BOOLEAN DEFAULT 0,
                parent_entity_id INTEGER,
                module_id INTEGER,
                cyclomatic_complexity INTEGER DEFAULT 1,
                cognitive_complexity INTEGER DEFAULT 0,
                lines_of_code INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_modified_at INTEGER,
                FOREIGN KEY(parent_entity_id) REFERENCES code_entities(id),
                FOREIGN KEY(module_id) REFERENCES code_entities(id),
                UNIQUE(project_id, file_path, name, entity_type)
            )
            """
        )

        # Type signatures table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS type_signatures (
                id INTEGER PRIMARY KEY,
                entity_id INTEGER NOT NULL UNIQUE,
                parameters TEXT NOT NULL DEFAULT '[]',
                return_type TEXT,
                is_async BOOLEAN DEFAULT 0,
                is_classmethod BOOLEAN DEFAULT 0,
                is_staticmethod BOOLEAN DEFAULT 0,
                type_parameters TEXT NOT NULL DEFAULT '[]',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(entity_id) REFERENCES code_entities(id)
            )
            """
        )

        # Dependencies table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dependencies (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                from_entity_id INTEGER NOT NULL,
                to_entity_id INTEGER,
                dependency_type TEXT DEFAULT 'calls',
                line_number INTEGER,
                file_path TEXT NOT NULL,
                external_module TEXT,
                external_entity TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(from_entity_id) REFERENCES code_entities(id),
                FOREIGN KEY(to_entity_id) REFERENCES code_entities(id)
            )
            """
        )

        # Complexity metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS complexity_metrics (
                id INTEGER PRIMARY KEY,
                entity_id INTEGER NOT NULL UNIQUE,
                cyclomatic_complexity INTEGER NOT NULL,
                cyclomatic_level TEXT NOT NULL,
                cognitive_complexity INTEGER NOT NULL,
                cognitive_level TEXT NOT NULL,
                lines_of_code INTEGER NOT NULL,
                logical_lines INTEGER NOT NULL,
                comment_lines INTEGER DEFAULT 0,
                distinct_operators INTEGER DEFAULT 0,
                distinct_operands INTEGER DEFAULT 0,
                total_operators INTEGER DEFAULT 0,
                total_operands INTEGER DEFAULT 0,
                halstead_difficulty REAL DEFAULT 0.0,
                halstead_volume REAL DEFAULT 0.0,
                maintainability_index REAL DEFAULT 0.0,
                max_nesting_depth INTEGER DEFAULT 0,
                avg_nesting_depth REAL DEFAULT 0.0,
                parameter_count INTEGER DEFAULT 0,
                return_statements INTEGER DEFAULT 0,
                analyzed_at INTEGER NOT NULL,
                FOREIGN KEY(entity_id) REFERENCES code_entities(id)
            )
            """
        )

        # Code diffs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS code_diffs (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                entity_id INTEGER,
                file_path TEXT NOT NULL,
                change_type TEXT DEFAULT 'modified',
                old_content TEXT,
                new_content TEXT,
                lines_added INTEGER DEFAULT 0,
                lines_deleted INTEGER DEFAULT 0,
                lines_modified INTEGER DEFAULT 0,
                git_commit_hash TEXT,
                git_author TEXT,
                agent_id TEXT,
                complexity_delta INTEGER,
                test_coverage_delta REAL,
                affected_entities TEXT NOT NULL DEFAULT '[]',
                breaking_change BOOLEAN DEFAULT 0,
                breaking_reason TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(entity_id) REFERENCES code_entities(id)
            )
            """
        )

        # Dependency graph table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS code_dependency_graphs (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL UNIQUE,
                total_entities INTEGER NOT NULL,
                total_dependencies INTEGER NOT NULL,
                circular_dependencies INTEGER DEFAULT 0,
                orphaned_entities INTEGER DEFAULT 0,
                highly_coupled_pairs TEXT NOT NULL DEFAULT '[]',
                average_fan_in REAL DEFAULT 0.0,
                average_fan_out REAL DEFAULT 0.0,
                modularity_score REAL DEFAULT 0.0,
                external_dependencies_count INTEGER DEFAULT 0,
                external_modules TEXT NOT NULL DEFAULT '[]',
                analyzed_at INTEGER NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # Test coverage table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_coverage (
                id INTEGER PRIMARY KEY,
                entity_id INTEGER NOT NULL UNIQUE,
                lines_covered INTEGER NOT NULL,
                lines_total INTEGER NOT NULL,
                coverage_percentage REAL NOT NULL,
                test_count INTEGER DEFAULT 0,
                test_file_paths TEXT NOT NULL DEFAULT '[]',
                branches_covered INTEGER DEFAULT 0,
                branches_total INTEGER DEFAULT 0,
                measured_at INTEGER NOT NULL,
                FOREIGN KEY(entity_id) REFERENCES code_entities(id)
            )
            """
        )

        # Code quality issues table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS code_quality_issues (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                entity_id INTEGER,
                issue_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                column_number INTEGER,
                message TEXT NOT NULL,
                rule_id TEXT,
                fix_suggestion TEXT,
                documentation_url TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at INTEGER,
                resolution_notes TEXT,
                detected_at INTEGER NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(entity_id) REFERENCES code_entities(id)
            )
            """
        )

        # Create indexes for common queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_project ON code_entities(project_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_file ON code_entities(file_path)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dependencies_from ON dependencies(from_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dependencies_to ON dependencies(to_entity_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_diffs_entity ON code_diffs(entity_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_issues_project ON code_quality_issues(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_issues_severity ON code_quality_issues(severity)"
        )

        # commit handled by cursor context

    # CodeEntity CRUD operations

    def create_entity(self, entity: CodeEntity) -> CodeEntity:
        """Create a new code entity."""
        cursor = self.execute(
            """
            INSERT INTO code_entities (
                project_id, name, entity_type, file_path, start_line, end_line,
                column_offset, docstring, is_public, is_deprecated, parent_entity_id,
                module_id, cyclomatic_complexity, cognitive_complexity, lines_of_code,
                created_at, updated_at, last_modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.project_id,
                entity.name,
                entity.entity_type,
                entity.file_path,
                entity.start_line,
                entity.end_line,
                entity.column_offset,
                entity.docstring,
                entity.is_public,
                entity.is_deprecated,
                entity.parent_entity_id,
                entity.module_id,
                entity.cyclomatic_complexity,
                entity.cognitive_complexity,
                entity.lines_of_code,
                int(entity.created_at.timestamp()),
                int(entity.updated_at.timestamp()),
                int(entity.last_modified_at.timestamp()) if entity.last_modified_at else None,
            ),
        )
        self.commit()
        entity.id = cursor.lastrowid
        return entity

    def get_entity(self, entity_id: int) -> Optional[CodeEntity]:
        """Get a code entity by ID."""
        row = self.execute("SELECT * FROM code_entities WHERE id = ?", (entity_id,), fetch_one=True)
        return self._row_to_entity(row) if row else None

    def list_entities_in_project(self, project_id: int) -> list[CodeEntity]:
        """List all entities in a project."""
        rows = self.execute(
            "SELECT * FROM code_entities WHERE project_id = ? ORDER BY file_path, start_line",
            (project_id,),
            fetch_all=True,
        )
        return [self._row_to_entity(row) for row in (rows or [])]

    def list_entities_in_file(self, project_id: int, file_path: str) -> list[CodeEntity]:
        """List all entities in a specific file."""
        rows = self.execute(
            "SELECT * FROM code_entities WHERE project_id = ? AND file_path = ? ORDER BY start_line",
            (project_id, file_path),
            fetch_all=True,
        )
        return [self._row_to_entity(row) for row in (rows or [])]

    def list_by_type(self, project_id: int, entity_type: EntityType) -> list[CodeEntity]:
        """List entities of a specific type."""
        rows = self.execute(
            "SELECT * FROM code_entities WHERE project_id = ? AND entity_type = ? ORDER BY name",
            (project_id, entity_type),
            fetch_all=True,
        )
        return [self._row_to_entity(row) for row in (rows or [])]

    def update_entity(self, entity: CodeEntity) -> bool:
        """Update an existing code entity."""
        cursor = self.execute(
            """
            UPDATE code_entities SET
                name = ?, entity_type = ?, file_path = ?, start_line = ?, end_line = ?,
                column_offset = ?, docstring = ?, is_public = ?, is_deprecated = ?,
                parent_entity_id = ?, module_id = ?, cyclomatic_complexity = ?,
                cognitive_complexity = ?, lines_of_code = ?, updated_at = ?, last_modified_at = ?
            WHERE id = ?
            """,
            (
                entity.name,
                entity.entity_type,
                entity.file_path,
                entity.start_line,
                entity.end_line,
                entity.column_offset,
                entity.docstring,
                entity.is_public,
                entity.is_deprecated,
                entity.parent_entity_id,
                entity.module_id,
                entity.cyclomatic_complexity,
                entity.cognitive_complexity,
                entity.lines_of_code,
                int(entity.updated_at.timestamp()),
                int(entity.last_modified_at.timestamp()) if entity.last_modified_at else None,
                entity.id,
            ),
        )
        self.commit()
        return cursor.rowcount > 0

    def delete_entity(self, entity_id: int) -> bool:
        """Delete a code entity."""
        cursor = self.execute("DELETE FROM code_entities WHERE id = ?", (entity_id,))
        self.commit()
        return cursor.rowcount > 0

    # Type signature operations

    def create_type_signature(self, sig: TypeSignature) -> TypeSignature:
        """Create type signature for entity."""
        cursor = self.execute(
            """
            INSERT INTO type_signatures (
                entity_id, parameters, return_type, is_async, is_classmethod,
                is_staticmethod, type_parameters, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sig.entity_id,
                self.serialize_json(sig.parameters),
                sig.return_type,
                sig.is_async,
                sig.is_classmethod,
                sig.is_staticmethod,
                self.serialize_json(sig.type_parameters),
                int(sig.created_at.timestamp()),
            ),
        )
        self.commit()
        sig.id = cursor.lastrowid
        return sig

    def get_type_signature(self, entity_id: int) -> Optional[TypeSignature]:
        """Get type signature for entity."""
        row = self.execute(
            "SELECT * FROM type_signatures WHERE entity_id = ?", (entity_id,), fetch_one=True
        )
        return self._row_to_type_signature(row) if row else None

    # Dependency operations

    def create_dependency(self, dep: Dependency) -> Dependency:
        """Create a code dependency."""
        cursor = self.execute(
            """
            INSERT INTO dependencies (
                project_id, from_entity_id, to_entity_id, dependency_type,
                line_number, file_path, external_module, external_entity, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dep.project_id,
                dep.from_entity_id,
                dep.to_entity_id,
                dep.dependency_type,
                dep.line_number,
                dep.file_path,
                dep.external_module,
                dep.external_entity,
                int(dep.created_at.timestamp()),
            ),
        )
        self.commit()
        dep.id = cursor.lastrowid
        return dep

    def get_dependencies(self, entity_id: int, as_from: bool = True) -> list[Dependency]:
        """Get dependencies for an entity (as source or target)."""
        if as_from:
            rows = self.execute(
                "SELECT * FROM dependencies WHERE from_entity_id = ? ORDER BY created_at DESC",
                (entity_id,),
                fetch_all=True,
            )
        else:
            rows = self.execute(
                "SELECT * FROM dependencies WHERE to_entity_id = ? ORDER BY created_at DESC",
                (entity_id,),
                fetch_all=True,
            )
        return [self._row_to_dependency(row) for row in (rows or [])]

    # Complexity metrics operations

    def create_complexity_metrics(self, metrics: ComplexityMetrics) -> ComplexityMetrics:
        """Store complexity analysis for entity."""
        cursor = self.execute(
            """
            INSERT INTO complexity_metrics (
                entity_id, cyclomatic_complexity, cyclomatic_level, cognitive_complexity,
                cognitive_level, lines_of_code, logical_lines, comment_lines,
                distinct_operators, distinct_operands, total_operators, total_operands,
                halstead_difficulty, halstead_volume, maintainability_index,
                max_nesting_depth, avg_nesting_depth, parameter_count,
                return_statements, analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics.entity_id,
                metrics.cyclomatic_complexity,
                metrics.cyclomatic_level,
                metrics.cognitive_complexity,
                metrics.cognitive_level,
                metrics.lines_of_code,
                metrics.logical_lines,
                metrics.comment_lines,
                metrics.distinct_operators,
                metrics.distinct_operands,
                metrics.total_operators,
                metrics.total_operands,
                metrics.halstead_difficulty,
                metrics.halstead_volume,
                metrics.maintainability_index,
                metrics.max_nesting_depth,
                metrics.avg_nesting_depth,
                metrics.parameter_count,
                metrics.return_statements,
                int(metrics.analyzed_at.timestamp()),
            ),
        )
        self.commit()
        metrics.id = cursor.lastrowid
        return metrics

    def get_complexity_metrics(self, entity_id: int) -> Optional[ComplexityMetrics]:
        """Get complexity metrics for entity."""
        row = self.execute(
            "SELECT * FROM complexity_metrics WHERE entity_id = ?", (entity_id,), fetch_one=True
        )
        return self._row_to_complexity_metrics(row) if row else None

    # Code diff operations

    def create_diff(self, diff: CodeDiff) -> CodeDiff:
        """Record a code change."""
        # Ensure affected_entities is always a list (default to empty list)
        affected_entities = diff.affected_entities or []
        cursor = self.execute(
            """
            INSERT INTO code_diffs (
                project_id, entity_id, file_path, change_type, old_content, new_content,
                lines_added, lines_deleted, lines_modified, git_commit_hash, git_author,
                agent_id, complexity_delta, test_coverage_delta, affected_entities,
                breaking_change, breaking_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                diff.project_id,
                diff.entity_id,
                diff.file_path,
                diff.change_type,
                diff.old_content,
                diff.new_content,
                diff.lines_added,
                diff.lines_deleted,
                diff.lines_modified,
                diff.git_commit_hash,
                diff.git_author,
                diff.agent_id,
                diff.complexity_delta,
                diff.test_coverage_delta,
                self.serialize_json(affected_entities),
                diff.breaking_change,
                diff.breaking_reason,
                int(diff.created_at.timestamp()),
            ),
        )
        self.commit()
        diff.id = cursor.lastrowid
        return diff

    def get_diffs_for_entity(self, entity_id: int, limit: int = 10) -> list[CodeDiff]:
        """Get recent diffs for entity."""
        rows = self.execute(
            "SELECT * FROM code_diffs WHERE entity_id = ? ORDER BY created_at DESC LIMIT ?",
            (entity_id, limit),
            fetch_all=True,
        )
        return [self._row_to_diff(row) for row in (rows or [])]

    def get_diffs_for_file(self, project_id: int, file_path: str) -> list[CodeDiff]:
        """Get all diffs for a specific file."""
        rows = self.execute(
            "SELECT * FROM code_diffs WHERE project_id = ? AND file_path = ? ORDER BY created_at DESC",
            (project_id, file_path),
            fetch_all=True,
        )
        return [self._row_to_diff(row) for row in (rows or [])]

    # Dependency graph operations

    def create_or_update_dependency_graph(self, graph: CodeDependencyGraph) -> CodeDependencyGraph:
        """Store or update dependency graph snapshot."""
        existing = self.execute(
            "SELECT id FROM code_dependency_graphs WHERE project_id = ?",
            (graph.project_id,),
            fetch_one=True,
        )

        if existing:
            cursor = self.execute(
                """
                UPDATE code_dependency_graphs SET
                    total_entities = ?, total_dependencies = ?,
                    circular_dependencies = ?, orphaned_entities = ?,
                    highly_coupled_pairs = ?, average_fan_in = ?,
                    average_fan_out = ?, modularity_score = ?,
                    external_dependencies_count = ?, external_modules = ?,
                    analyzed_at = ?
                WHERE project_id = ?
                """,
                (
                    graph.total_entities,
                    graph.total_dependencies,
                    graph.circular_dependencies,
                    graph.orphaned_entities,
                    self.serialize_json(graph.highly_coupled_pairs),
                    graph.average_fan_in,
                    graph.average_fan_out,
                    graph.modularity_score,
                    graph.external_dependencies_count,
                    self.serialize_json(graph.external_modules),
                    int(graph.analyzed_at.timestamp()),
                    graph.project_id,
                ),
            )
            graph.id = existing[0]
        else:
            cursor = self.execute(
                """
                INSERT INTO code_dependency_graphs (
                    project_id, total_entities, total_dependencies,
                    circular_dependencies, orphaned_entities, highly_coupled_pairs,
                    average_fan_in, average_fan_out, modularity_score,
                    external_dependencies_count, external_modules, analyzed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    graph.project_id,
                    graph.total_entities,
                    graph.total_dependencies,
                    graph.circular_dependencies,
                    graph.orphaned_entities,
                    self.serialize_json(graph.highly_coupled_pairs),
                    graph.average_fan_in,
                    graph.average_fan_out,
                    graph.modularity_score,
                    graph.external_dependencies_count,
                    self.serialize_json(graph.external_modules),
                    int(graph.analyzed_at.timestamp()),
                ),
            )
            graph.id = cursor.lastrowid

        self.commit()
        return graph

    def get_dependency_graph(self, project_id: int) -> Optional[CodeDependencyGraph]:
        """Get latest dependency graph for project."""
        row = self.execute(
            "SELECT * FROM code_dependency_graphs WHERE project_id = ?",
            (project_id,),
            fetch_one=True,
        )
        return self._row_to_dependency_graph(row) if row else None

    # Test coverage operations

    def create_test_coverage(self, coverage: TestCoverage) -> TestCoverage:
        """Record test coverage for entity."""
        cursor = self.execute(
            """
            INSERT INTO test_coverage (
                entity_id, lines_covered, lines_total, coverage_percentage,
                test_count, test_file_paths, branches_covered, branches_total, measured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                coverage.entity_id,
                coverage.lines_covered,
                coverage.lines_total,
                coverage.coverage_percentage,
                coverage.test_count,
                self.serialize_json(coverage.test_file_paths),
                coverage.branches_covered,
                coverage.branches_total,
                int(coverage.measured_at.timestamp()),
            ),
        )
        self.commit()
        coverage.id = cursor.lastrowid
        return coverage

    def get_test_coverage(self, entity_id: int) -> Optional[TestCoverage]:
        """Get test coverage for entity."""
        row = self.execute(
            "SELECT * FROM test_coverage WHERE entity_id = ?", (entity_id,), fetch_one=True
        )
        return self._row_to_test_coverage(row) if row else None

    # Code quality issues operations

    def create_quality_issue(self, issue: CodeQualityIssue) -> CodeQualityIssue:
        """Record a code quality issue."""
        cursor = self.execute(
            """
            INSERT INTO code_quality_issues (
                project_id, entity_id, issue_type, severity, file_path,
                line_number, column_number, message, rule_id, fix_suggestion,
                documentation_url, resolved, resolved_at, resolution_notes, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue.project_id,
                issue.entity_id,
                issue.issue_type,
                issue.severity,
                issue.file_path,
                issue.line_number,
                issue.column_number,
                issue.message,
                issue.rule_id,
                issue.fix_suggestion,
                issue.documentation_url,
                issue.resolved,
                int(issue.resolved_at.timestamp()) if issue.resolved_at else None,
                issue.resolution_notes,
                int(issue.detected_at.timestamp()),
            ),
        )
        self.commit()
        issue.id = cursor.lastrowid
        return issue

    def get_quality_issues_for_entity(
        self, entity_id: int, resolved: Optional[bool] = None
    ) -> list[CodeQualityIssue]:
        """Get quality issues for entity."""
        if resolved is None:
            rows = self.execute(
                "SELECT * FROM code_quality_issues WHERE entity_id = ? ORDER BY severity DESC, detected_at DESC",
                (entity_id,),
                fetch_all=True,
            )
        else:
            rows = self.execute(
                "SELECT * FROM code_quality_issues WHERE entity_id = ? AND resolved = ? ORDER BY severity DESC",
                (entity_id, resolved),
                fetch_all=True,
            )
        return [self._row_to_quality_issue(row) for row in (rows or [])]

    def get_critical_issues(self, project_id: int) -> list[CodeQualityIssue]:
        """Get all critical/error severity issues."""
        rows = self.execute(
            "SELECT * FROM code_quality_issues WHERE project_id = ? AND severity IN ('critical', 'error') AND resolved = 0 ORDER BY detected_at DESC",
            (project_id,),
            fetch_all=True,
        )
        return [self._row_to_quality_issue(row) for row in (rows or [])]

    # Helper methods for row-to-model conversion

    def _row_to_entity(self, row) -> CodeEntity:
        """Convert database row to CodeEntity model."""
        return CodeEntity(
            id=row[0],
            project_id=row[1],
            name=row[2],
            entity_type=row[3],
            file_path=row[4],
            start_line=row[5],
            end_line=row[6],
            column_offset=row[7],
            docstring=row[8],
            is_public=bool(row[9]),
            is_deprecated=bool(row[10]),
            parent_entity_id=row[11],
            module_id=row[12],
            cyclomatic_complexity=row[13],
            cognitive_complexity=row[14],
            lines_of_code=row[15],
            created_at=self.from_timestamp(row[16]),
            updated_at=self.from_timestamp(row[17]),
            last_modified_at=self.from_timestamp(row[18]) if row[18] else None,
        )

    def _row_to_type_signature(self, row) -> TypeSignature:
        """Convert database row to TypeSignature model."""
        return TypeSignature(
            id=row[0],
            entity_id=row[1],
            parameters=self.deserialize_json(row[2]),
            return_type=row[3],
            is_async=bool(row[4]),
            is_classmethod=bool(row[5]),
            is_staticmethod=bool(row[6]),
            type_parameters=self.deserialize_json(row[7]),
            created_at=self.from_timestamp(row[8]),
        )

    def _row_to_dependency(self, row) -> Dependency:
        """Convert database row to Dependency model."""
        return Dependency(
            id=row[0],
            project_id=row[1],
            from_entity_id=row[2],
            to_entity_id=row[3],
            dependency_type=row[4],
            line_number=row[5],
            file_path=row[6],
            external_module=row[7],
            external_entity=row[8],
            created_at=self.from_timestamp(row[9]),
        )

    def _row_to_complexity_metrics(self, row) -> ComplexityMetrics:
        """Convert database row to ComplexityMetrics model."""
        return ComplexityMetrics(
            id=row[0],
            entity_id=row[1],
            cyclomatic_complexity=row[2],
            cyclomatic_level=row[3],
            cognitive_complexity=row[4],
            cognitive_level=row[5],
            lines_of_code=row[6],
            logical_lines=row[7],
            comment_lines=row[8],
            distinct_operators=row[9],
            distinct_operands=row[10],
            total_operators=row[11],
            total_operands=row[12],
            halstead_difficulty=row[13],
            halstead_volume=row[14],
            maintainability_index=row[15],
            max_nesting_depth=row[16],
            avg_nesting_depth=row[17],
            parameter_count=row[18],
            return_statements=row[19],
            analyzed_at=self.from_timestamp(row[20]),
        )

    def _row_to_diff(self, row) -> CodeDiff:
        """Convert database row to CodeDiff model."""
        return CodeDiff(
            id=row[0],
            project_id=row[1],
            entity_id=row[2],
            file_path=row[3],
            change_type=row[4],
            old_content=row[5],
            new_content=row[6],
            lines_added=row[7],
            lines_deleted=row[8],
            lines_modified=row[9],
            git_commit_hash=row[10],
            git_author=row[11],
            agent_id=row[12],
            complexity_delta=row[13],
            test_coverage_delta=row[14],
            affected_entities=self.deserialize_json(row[15], []),
            breaking_change=bool(row[16]),
            breaking_reason=row[17],
            created_at=self.from_timestamp(row[18]),
        )

    def _row_to_dependency_graph(self, row) -> CodeDependencyGraph:
        """Convert database row to CodeDependencyGraph model."""
        return CodeDependencyGraph(
            id=row[0],
            project_id=row[1],
            total_entities=row[2],
            total_dependencies=row[3],
            circular_dependencies=row[4],
            orphaned_entities=row[5],
            highly_coupled_pairs=self.deserialize_json(row[6], []),
            average_fan_in=row[7],
            average_fan_out=row[8],
            modularity_score=row[9],
            external_dependencies_count=row[10],
            external_modules=self.deserialize_json(row[11], []),
            analyzed_at=self.from_timestamp(row[12]),
        )

    def _row_to_test_coverage(self, row) -> TestCoverage:
        """Convert database row to TestCoverage model."""
        return TestCoverage(
            id=row[0],
            entity_id=row[1],
            lines_covered=row[2],
            lines_total=row[3],
            coverage_percentage=row[4],
            test_count=row[5],
            test_file_paths=self.deserialize_json(row[6], []),
            branches_covered=row[7],
            branches_total=row[8],
            measured_at=self.from_timestamp(row[9]),
        )

    def _row_to_quality_issue(self, row) -> CodeQualityIssue:
        """Convert database row to CodeQualityIssue model."""
        return CodeQualityIssue(
            id=row[0],
            project_id=row[1],
            entity_id=row[2],
            issue_type=row[3],
            severity=row[4],
            file_path=row[5],
            line_number=row[6],
            column_number=row[7],
            message=row[8],
            rule_id=row[9],
            fix_suggestion=row[10],
            documentation_url=row[11],
            resolved=bool(row[12]),
            resolved_at=self.from_timestamp(row[13]) if row[13] else None,
            resolution_notes=row[14],
            detected_at=self.from_timestamp(row[15]),
        )
