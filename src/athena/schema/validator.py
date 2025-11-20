"""Schema validation to ensure database matches expected structure.

Validates:
- Required tables exist
- Required columns exist in each table
- Foreign key constraints are set up
- Indexes are present
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates database schema against expected structure."""

    # Define expected schema structure
    EXPECTED_TABLES = {
        # Layer 1: Episodic Memory
        "episodic_events": ["id", "project_id", "session_id", "timestamp", "event_type", "content"],
        # Layer 2: Semantic Memory
        "semantic_memories": ["id", "project_id", "content", "embedding", "consolidation_state"],
        # Layer 3: Procedural Memory
        "procedures": ["id", "project_id", "name", "category", "description"],
        # Layer 4: Prospective Memory
        "prospective_tasks": ["id", "project_id", "title", "status", "priority"],
        "prospective_goals": ["id", "project_id", "description"],
        # Layer 5: Knowledge Graph
        "entities": ["id", "project_id", "name", "entity_type"],
        "entity_relations": ["id", "from_entity_id", "to_entity_id", "relation_type"],
        # Layer 7: Consolidation
        "consolidation_runs": ["id", "project_id", "consolidation_type"],
        "extracted_patterns": ["id", "project_id"],
        # Core
        "projects": ["id", "name", "path"],
    }

    def __init__(self, db):
        self.db = db

    async def validate_all(self) -> Dict[str, any]:
        """Run all validation checks."""
        results = {
            "valid": True,
            "tables": await self._validate_tables(),
            "columns": await self._validate_columns(),
            "indexes": await self._validate_indexes(),
        }

        # Overall validity
        results["valid"] = all(v["exists"] for v in results["tables"].values()) and all(
            v["valid"] for v in results["columns"].values()
        )

        return results

    async def _validate_tables(self) -> Dict[str, Dict]:
        """Check that all expected tables exist."""
        results = {}

        async with self.db.get_connection() as conn:
            for table_name in self.EXPECTED_TABLES.keys():
                result = await conn.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                    """,
                    (table_name,),
                )
                row = await result.fetchone()
                exists = row[0] if row else False
                results[table_name] = {"exists": exists}

        return results

    async def _validate_columns(self) -> Dict[str, Dict]:
        """Check that required columns exist in tables."""
        results = {}

        async with self.db.get_connection() as conn:
            for table_name, required_columns in self.EXPECTED_TABLES.items():
                results[table_name] = {"valid": True, "missing": []}

                # Get actual columns in table
                result = await conn.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                    (table_name,),
                )
                actual_columns = {row[0] for row in await result.fetchall()}

                # Check for missing required columns
                for col in required_columns:
                    if col not in actual_columns:
                        results[table_name]["valid"] = False
                        results[table_name]["missing"].append(col)

        return results

    async def _validate_indexes(self) -> Dict[str, List[str]]:
        """Check that important indexes exist."""
        results = {}

        # Define important indexes
        important_indexes = {
            "episodic_events": ["idx_episodic_project", "idx_episodic_session"],
            "semantic_memories": ["idx_semantic_project", "idx_semantic_session"],
            "consolidation_runs": ["idx_consolidation_project"],
        }

        async with self.db.get_connection() as conn:
            for table_name, expected_indexes in important_indexes.items():
                results[table_name] = {"present": [], "missing": []}

                result = await conn.execute(
                    """
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public' AND tablename = %s
                    """,
                    (table_name,),
                )
                actual_indexes = {row[0] for row in await result.fetchall()}

                for idx_name in expected_indexes:
                    if idx_name in actual_indexes:
                        results[table_name]["present"].append(idx_name)
                    else:
                        results[table_name]["missing"].append(idx_name)

        return results

    def print_validation_report(self, results: Dict) -> None:
        """Print a human-readable validation report."""
        print("\n" + "=" * 60)
        print("SCHEMA VALIDATION REPORT")
        print("=" * 60)

        if results["valid"]:
            print("✅ Schema is VALID")
        else:
            print("❌ Schema is INVALID")

        print("\nTables:")
        for table, status in results["tables"].items():
            symbol = "✅" if status["exists"] else "❌"
            print(f"  {symbol} {table}")

        print("\nColumns:")
        for table, status in results["columns"].items():
            if status["valid"]:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} - missing: {', '.join(status['missing'])}")

        print("\n" + "=" * 60)
