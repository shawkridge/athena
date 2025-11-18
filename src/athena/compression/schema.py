"""Schema validation for compression features.

This module validates that the database has all required compression columns
and provides utilities for schema verification.
"""

from typing import Dict, List, Tuple


class CompressionSchema:
    """Validation for compression-related schema."""

    # Required columns for each compression feature
    REQUIRED_COLUMNS = {
        "temporal_decay": [
            "content_compressed",
            "compression_level",
            "compression_timestamp",
            "compression_tokens_saved",
        ],
        "consolidation": [
            "content_executive",
            "compression_source_events",
            "compression_generated_at",
        ],
    }

    # Required indices for performance
    REQUIRED_INDICES = {
        "temporal_decay": [
            "idx_semantic_memories_compression_level",
            "idx_semantic_memories_compression_timestamp",
            "idx_semantic_memories_created_at",
        ],
        "consolidation": [
            "idx_semantic_memories_compression_generated_at",
            "idx_semantic_memories_has_executive",
        ],
    }

    # Required tables
    REQUIRED_TABLES = {
        "consolidation": [
            "consolidation_metrics",
        ],
    }

    @staticmethod
    def validate_migration(db_path: str) -> Tuple[bool, List[str]]:
        """
        Verify all required columns exist in the database.

        Args:
            db_path: Path to SQLite database

        Returns:
            Tuple of (is_valid, list_of_missing_items)
        """
        try:
            # PostgreSQL connection should be used instead
            cursor = conn.cursor()

            missing = []

            # Check semantic_memories table exists
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='semantic_memories'"
            )
            if not cursor.fetchone():
                conn.close()
                return False, ["semantic_memories table does not exist"]

            # Get actual columns in semantic_memories
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='semantic_memories' AND table_schema='public'"
            )
            actual_columns = {row[0] for row in cursor.fetchall()}

            # Check temporal decay columns
            for col in CompressionSchema.REQUIRED_COLUMNS["temporal_decay"]:
                if col not in actual_columns:
                    missing.append(f"temporal_decay: missing column '{col}'")

            # Check consolidation columns
            for col in CompressionSchema.REQUIRED_COLUMNS["consolidation"]:
                if col not in actual_columns:
                    missing.append(f"consolidation: missing column '{col}'")

            # Check indices
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='semantic_memories'"
            )
            actual_indices = {row[0] for row in cursor.fetchall()}

            for idx in CompressionSchema.REQUIRED_INDICES["temporal_decay"]:
                if idx not in actual_indices:
                    missing.append(f"temporal_decay: missing index '{idx}'")

            for idx in CompressionSchema.REQUIRED_INDICES["consolidation"]:
                if idx not in actual_indices:
                    missing.append(f"consolidation: missing index '{idx}'")

            # Check consolidation_metrics table
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='consolidation_metrics'"
            )
            if not cursor.fetchone():
                missing.append("consolidation: missing table 'consolidation_metrics'")

            conn.close()

            is_valid = len(missing) == 0
            return is_valid, missing

        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    @staticmethod
    def get_schema_info(db_path: str) -> Dict:
        """
        Get detailed schema information for debugging.

        Args:
            db_path: Path to SQLite database

        Returns:
            Dictionary with schema details
        """
        info = {
            "temporal_decay": {
                "columns": {},
                "indices": [],
                "valid": False,
            },
            "consolidation": {
                "columns": {},
                "indices": [],
                "tables": [],
                "valid": False,
            },
        }

        try:
            # PostgreSQL connection should be used instead
            cursor = conn.cursor()

            # Get column info (PostgreSQL)
            cursor.execute(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='semantic_memories' AND table_schema='public'"
            )
            all_columns = {row[0]: row[1] for row in cursor.fetchall()}  # name: type

            # Check temporal decay columns
            for col in CompressionSchema.REQUIRED_COLUMNS["temporal_decay"]:
                if col in all_columns:
                    info["temporal_decay"]["columns"][col] = all_columns[col]

            # Check consolidation columns
            for col in CompressionSchema.REQUIRED_COLUMNS["consolidation"]:
                if col in all_columns:
                    info["consolidation"]["columns"][col] = all_columns[col]

            # Get indices
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='semantic_memories'"
            )
            all_indices = {row[0] for row in cursor.fetchall()}

            info["temporal_decay"]["indices"] = [
                idx
                for idx in CompressionSchema.REQUIRED_INDICES["temporal_decay"]
                if idx in all_indices
            ]

            info["consolidation"]["indices"] = [
                idx
                for idx in CompressionSchema.REQUIRED_INDICES["consolidation"]
                if idx in all_indices
            ]

            # Check consolidation_metrics table
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='consolidation_metrics'"
            )
            if cursor.fetchone():
                info["consolidation"]["tables"] = ["consolidation_metrics"]

            # Validate
            info["temporal_decay"]["valid"] = len(info["temporal_decay"]["columns"]) == len(
                CompressionSchema.REQUIRED_COLUMNS["temporal_decay"]
            ) and len(info["temporal_decay"]["indices"]) == len(
                CompressionSchema.REQUIRED_INDICES["temporal_decay"]
            )

            info["consolidation"]["valid"] = (
                len(info["consolidation"]["columns"])
                == len(CompressionSchema.REQUIRED_COLUMNS["consolidation"])
                and len(info["consolidation"]["indices"])
                == len(CompressionSchema.REQUIRED_INDICES["consolidation"])
                and len(info["consolidation"]["tables"]) > 0
            )

            conn.close()

        except Exception as e:
            info["error"] = str(e)

        return info
