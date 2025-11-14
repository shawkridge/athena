"""Procedural memory storage and query operations."""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import (
    ParameterType,
    Procedure,
    ProcedureCategory,
    ProcedureExecution,
    ProcedureParameter,
)


class ProceduralStore(BaseStore[Procedure]):
    """Manages procedure storage and execution tracking."""

    table_name = "procedures"
    model_class = Procedure

    def __init__(self, db: Database):
        """Initialize procedural store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        # Schema is initialized centrally in database.py
        #
    def _row_to_model(self, row: Dict[str, Any]) -> Procedure:
        """Convert database row to Procedure model.

        Args:
            row: Database row as dict

        Returns:
            Procedure instance
        """
        # Parse JSON fields, ensuring lists remain lists
        applicable_contexts = []
        if row.get("applicable_contexts"):
            parsed = self.deserialize_json(row.get("applicable_contexts"), [])
            applicable_contexts = parsed if isinstance(parsed, list) else []

        steps = []
        if row.get("steps"):
            parsed = self.deserialize_json(row.get("steps"), [])
            steps = parsed if isinstance(parsed, list) else []

        examples = []
        if row.get("examples"):
            parsed = self.deserialize_json(row.get("examples"), [])
            examples = parsed if isinstance(parsed, list) else []

        return Procedure(
            id=row.get("id"),
            name=row.get("name"),
            category=ProcedureCategory(row.get("category")) if row.get("category") else None,
            description=row.get("description"),
            trigger_pattern=row.get("trigger_pattern"),
            applicable_contexts=applicable_contexts,
            template=row.get("template"),
            steps=steps,
            examples=examples,
            success_rate=row.get("success_rate"),
            usage_count=row.get("usage_count"),
            avg_completion_time_ms=row.get("avg_completion_time_ms"),
            created_at=self.from_timestamp(row.get("created_at")),
            last_used=self.from_timestamp(row.get("last_used")) if row.get("last_used") else None,
            created_by=row.get("created_by"),
        )

    def _ensure_schema(self):
        """Ensure procedural memory tables exist."""

        # For PostgreSQL async databases, skip sync schema initialization
        if not hasattr(self.db, 'conn'):
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"{self.__class__.__name__}: PostgreSQL async database detected. Schema management handled by _init_schema().")
            return
        cursor = self.db.get_cursor()

        # Procedures table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                description TEXT,

                trigger_pattern TEXT,
                applicable_contexts TEXT,

                template TEXT NOT NULL,
                steps TEXT,
                examples TEXT,

                success_rate REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                avg_completion_time_ms INTEGER,

                created_at INTEGER NOT NULL,
                last_used INTEGER,
                created_by TEXT DEFAULT 'user'
            )
        """)

        # Procedure parameters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_type TEXT NOT NULL,
                required BOOLEAN DEFAULT 1,
                default_value TEXT,
                description TEXT,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE
            )
        """)

        # Execution history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                outcome TEXT NOT NULL,
                duration_ms INTEGER,
                variables TEXT,
                learned TEXT,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedures_category ON procedures(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedures_usage ON procedures(usage_count DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_procedure ON procedure_executions(procedure_id)")

        # commit handled by cursor context

    def create_procedure(self, procedure: Procedure) -> int:
        """Create a new procedure.

        Args:
            procedure: Procedure to create

        Returns:
            ID of created procedure
        """
        category_str = (
            procedure.category.value
            if isinstance(procedure.category, ProcedureCategory)
            else procedure.category
        )

        self.execute(
            """
            INSERT INTO procedures (
                name, category, description,
                trigger_pattern, applicable_contexts,
                template, steps, examples,
                success_rate, usage_count, avg_completion_time_ms,
                created_at, last_used, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                procedure.name,
                category_str,
                procedure.description,
                procedure.trigger_pattern,
                self.serialize_json(procedure.applicable_contexts),
                procedure.template,
                self.serialize_json(procedure.steps),
                self.serialize_json(procedure.examples),
                procedure.success_rate,
                procedure.usage_count,
                procedure.avg_completion_time_ms,
                int(procedure.created_at.timestamp()),
                int(procedure.last_used.timestamp()) if procedure.last_used else None,
                procedure.created_by,
            ),
        )
        self.commit()
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        return result[0] if result else None

    def get_procedure(self, procedure_id: int) -> Optional[Procedure]:
        """Get procedure by ID.

        Args:
            procedure_id: Procedure ID

        Returns:
            Procedure if found, None otherwise
        """
        row = self.execute("SELECT * FROM procedures WHERE id = %s", (procedure_id,), fetch_one=True)

        if not row:
            return None

        col_names = ["id", "name", "category", "description", "trigger_pattern", "applicable_contexts",
                     "template", "steps", "examples", "success_rate", "usage_count", "avg_completion_time_ms",
                     "created_at", "last_used", "created_by"]
        return self._row_to_model(dict(zip(col_names, row)))

    def find_procedure(self, name: str) -> Optional[Procedure]:
        """Find procedure by name.

        Args:
            name: Procedure name

        Returns:
            Procedure if found, None otherwise
        """
        row = self.execute("SELECT * FROM procedures WHERE name = %s", (name,), fetch_one=True)

        if not row:
            return None

        col_names = ["id", "name", "category", "description", "trigger_pattern", "applicable_contexts",
                     "template", "steps", "examples", "success_rate", "usage_count", "avg_completion_time_ms",
                     "created_at", "last_used", "created_by"]
        return self._row_to_model(dict(zip(col_names, row)))

    def list_procedures(
        self, category: Optional[ProcedureCategory] = None, limit: int = 50
    ) -> list[Procedure]:
        """List procedures.

        Args:
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of procedures
        """
        col_names = ["id", "name", "category", "description", "trigger_pattern", "applicable_contexts",
                     "template", "steps", "examples", "success_rate", "usage_count", "avg_completion_time_ms",
                     "created_at", "last_used", "created_by"]

        if category:
            category_str = category.value if isinstance(category, ProcedureCategory) else category
            rows = self.execute(
                """
                SELECT * FROM procedures
                WHERE category = %s
                ORDER BY execution_count DESC, success_rate DESC
                LIMIT %s
            """,
                (category_str, limit),
                fetch_all=True,
            )
        else:
            rows = self.execute(
                """
                SELECT * FROM procedures
                ORDER BY execution_count DESC, success_rate DESC
                LIMIT %s
            """,
                (limit,),
                fetch_all=True,
            )

        return [self._row_to_model(dict(zip(col_names, row))) for row in (rows or [])]

    def search_procedures(self, query: str, context: Optional[list[str]] = None) -> list[Procedure]:
        """Search procedures by name/description and context.

        Args:
            query: Search query
            context: Optional context tags (e.g., ["react", "typescript"])

        Returns:
            List of matching procedures
        """
        # Split query into words for flexible matching
        query_words = query.lower().split()

        # Build OR conditions for each word
        where_clauses = []
        params = []
        for word in query_words:
            where_clauses.append("(LOWER(name) LIKE %s OR LOWER(description) LIKE %s)")
            params.extend([f"%{word}%", f"%{word}%"])

        if not where_clauses:
            # Empty query - return all
            where_clauses.append("1=1")

        sql = f"SELECT * FROM procedures WHERE ({' OR '.join(where_clauses)})"

        if context:
            # Filter by applicable contexts (check if any context tag matches)
            for ctx in context[:3]:  # Check up to 3 context tags
                sql += " AND applicable_contexts LIKE %s"
                params.append(f"%{ctx}%")

        sql += " ORDER BY usage_count DESC, success_rate DESC LIMIT 20"

        rows = self.execute(sql, params, fetch_all=True)
        col_names = ["id", "name", "category", "description", "trigger_pattern", "applicable_contexts",
                     "template", "steps", "examples", "success_rate", "usage_count", "avg_completion_time_ms",
                     "created_at", "last_used", "created_by"]
        return [self._row_to_model(dict(zip(col_names, row))) for row in (rows or [])]

    def update_procedure_stats(
        self,
        procedure_id: int,
        outcome: str,
        duration_ms: Optional[int] = None,
    ):
        """Update procedure usage statistics.

        Args:
            procedure_id: Procedure ID
            outcome: Execution outcome (success|failure|partial)
            duration_ms: Execution duration
        """
        # Get current stats
        row = self.execute(
            "SELECT success_rate, usage_count, avg_completion_time_ms FROM procedures WHERE id = %s",
            (procedure_id,),
            fetch_one=True,
        )
        if not row:
            return

        success_rate = row[0]
        usage_count = row[1]
        avg_time = row[2]

        # Update success rate (exponential moving average)
        new_success = 1.0 if outcome == "success" else 0.0
        success_rate = success_rate * 0.9 + new_success * 0.1

        # Update usage count
        usage_count += 1

        # Update average completion time
        if duration_ms and avg_time:
            avg_time = int(avg_time * 0.8 + duration_ms * 0.2)
        elif duration_ms:
            avg_time = duration_ms

        # Update database
        self.execute(
            """
            UPDATE procedures
            SET success_rate = ?, usage_count = ?, avg_completion_time_ms = ?, last_used = ?
            WHERE id = %s
        """,
            (success_rate, usage_count, avg_time, int(time.time()), procedure_id),
        )
        self.commit()

    def record_execution(self, execution: ProcedureExecution) -> int:
        """Record a procedure execution.

        Args:
            execution: Execution record

        Returns:
            ID of created execution record
        """
        self.execute(
            """
            INSERT INTO procedure_executions (
                procedure_id, project_id, timestamp, outcome,
                duration_ms, variables, learned
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
            (
                execution.procedure_id,
                execution.project_id,
                int(execution.timestamp.timestamp()),
                execution.outcome,
                execution.duration_ms,
                self.serialize_json(execution.variables),
                execution.learned,
            ),
        )

        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        execution_id = result[0] if result else None
        self.commit()

        # Update procedure stats
        self.update_procedure_stats(
            execution.procedure_id, execution.outcome, execution.duration_ms
        )

        return execution_id

    def get_execution_history(
        self, procedure_id: int, limit: int = 20
    ) -> list[ProcedureExecution]:
        """Get execution history for a procedure.

        Args:
            procedure_id: Procedure ID
            limit: Maximum results

        Returns:
            List of executions
        """
        rows = self.execute(
            """
            SELECT * FROM procedure_executions
            WHERE procedure_id = %s
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (procedure_id, limit),
            fetch_all=True,
        )

        executions = []
        for row in (rows or []):
            executions.append(
                ProcedureExecution(
                    id=row[0],
                    procedure_id=row[1],
                    project_id=row[2],
                    timestamp=datetime.fromtimestamp(row[3]),
                    outcome=row[4],
                    duration_ms=row[5],
                    variables=self.deserialize_json(row[6], {}) if row[6] else {},
                    learned=row[7],
                )
            )

        return executions

    def add_parameter(self, parameter: ProcedureParameter) -> int:
        """Add a parameter to a procedure.

        Args:
            parameter: Parameter to add

        Returns:
            ID of created parameter
        """
        param_type_str = (
            parameter.param_type.value
            if isinstance(parameter.param_type, ParameterType)
            else parameter.param_type
        )

        self.execute(
            """
            INSERT INTO procedure_params (
                procedure_id, param_name, param_type, required, default_value, description
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (
                parameter.procedure_id,
                parameter.param_name,
                param_type_str,
                parameter.required,
                parameter.default_value,
                parameter.description,
            ),
        )
        self.commit()
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        return result[0] if result else None

    def get_parameters(self, procedure_id: int) -> list[ProcedureParameter]:
        """Get all parameters for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            List of parameters
        """
        rows = self.execute(
            "SELECT * FROM procedure_params WHERE procedure_id = %s", (procedure_id,),
            fetch_all=True,
        )

        parameters = []
        for row in (rows or []):
            parameters.append(
                ProcedureParameter(
                    id=row[0],
                    procedure_id=row[1],
                    param_name=row[2],
                    param_type=ParameterType(row[3]),
                    required=bool(row[4]),
                    default_value=row[5],
                    description=row[6],
                )
            )

        return parameters

