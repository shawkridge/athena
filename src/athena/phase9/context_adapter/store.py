"""Database store for Phase 9.3: Infinite Context Adapter."""

from typing import Optional

from athena.core.database import Database
from athena.phase9.context_adapter.models import (
    ExternalDataMapping,
    ExternalSourceConnection,
    ImportedData,
    SyncLog,
)


class ContextAdapterStore:
    """Store for external system connections and data mappings."""

    def __init__(self, db: Database):
        """Initialize store with database connection."""
        self.db = db

    def _ensure_schema(self):
        """Create tables on first use."""
        cursor = self.db.get_cursor()

        # External source connections table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS external_source_connections (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                api_endpoint TEXT,
                api_key_encrypted TEXT,
                sync_direction TEXT,
                enabled INTEGER,
                last_sync_timestamp INTEGER,
                sync_frequency_minutes INTEGER,
                auto_sync INTEGER,
                filters TEXT,
                mapping_config TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        # External data mappings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS external_data_mappings (
                id SERIAL PRIMARY KEY,
                source_id INTEGER NOT NULL,
                external_id TEXT NOT NULL,
                memory_id INTEGER,
                memory_type TEXT,
                last_synced_timestamp INTEGER,
                sync_status TEXT,
                sync_notes TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                FOREIGN KEY(source_id) REFERENCES external_source_connections(id)
            )
            """
        )

        # External data snapshots table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS external_data_snapshots (
                id SERIAL PRIMARY KEY,
                source_id INTEGER NOT NULL,
                external_id TEXT NOT NULL,
                data_type TEXT,
                data_snapshot TEXT,
                timestamp INTEGER,
                operation TEXT,
                created_at INTEGER,
                FOREIGN KEY(source_id) REFERENCES external_source_connections(id)
            )
            """
        )

        # Imported data table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS imported_data (
                id SERIAL PRIMARY KEY,
                source_id INTEGER NOT NULL,
                data_type TEXT,
                title TEXT,
                content TEXT,
                external_id TEXT NOT NULL,
                external_url TEXT,
                author TEXT,
                created_date INTEGER,
                updated_date INTEGER,
                metadata TEXT,
                imported_at INTEGER,
                FOREIGN KEY(source_id) REFERENCES external_source_connections(id)
            )
            """
        )

        # Exported insights table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exported_insights (
                id SERIAL PRIMARY KEY,
                target_source_id INTEGER NOT NULL,
                insight_type TEXT,
                title TEXT,
                description TEXT,
                relevant_tasks TEXT,
                confidence_level REAL,
                external_id TEXT,
                export_status TEXT,
                export_timestamp INTEGER,
                created_at INTEGER,
                FOREIGN KEY(target_source_id) REFERENCES external_source_connections(id)
            )
            """
        )

        # Sync conflicts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id SERIAL PRIMARY KEY,
                source_id INTEGER NOT NULL,
                external_id TEXT NOT NULL,
                memory_id INTEGER,
                conflict_type TEXT,
                external_version TEXT,
                memory_version TEXT,
                resolution_strategy TEXT,
                resolved INTEGER,
                resolved_by TEXT,
                resolution_timestamp INTEGER,
                created_at INTEGER,
                FOREIGN KEY(source_id) REFERENCES external_source_connections(id)
            )
            """
        )

        # Sync logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_logs (
                id SERIAL PRIMARY KEY,
                source_id INTEGER NOT NULL,
                sync_type TEXT,
                direction TEXT,
                status TEXT,
                items_processed INTEGER,
                items_imported INTEGER,
                items_exported INTEGER,
                items_updated INTEGER,
                conflicts_detected INTEGER,
                errors_count INTEGER,
                error_messages TEXT,
                duration_seconds REAL,
                created_at INTEGER,
                completed_at INTEGER,
                FOREIGN KEY(source_id) REFERENCES external_source_connections(id)
            )
            """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_external_connections_project ON external_source_connections(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_external_data_mappings_source ON external_data_mappings(source_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_external_data_mappings_memory ON external_data_mappings(memory_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_imported_data_source ON imported_data(source_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_exported_insights_source ON exported_insights(target_source_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sync_logs_source ON sync_logs(source_id, created_at DESC)"
        )

        # commit handled by cursor context

    def create_connection(self, connection: ExternalSourceConnection) -> ExternalSourceConnection:
        """Create external source connection."""
        from datetime import datetime

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())
        import json

        cursor.execute(
            """
            INSERT INTO external_source_connections
            (project_id, source_type, source_name, api_endpoint, api_key_encrypted,
             sync_direction, enabled, last_sync_timestamp, sync_frequency_minutes,
             auto_sync, filters, mapping_config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                connection.project_id,
                connection.source_type,
                connection.source_name,
                connection.api_endpoint,
                connection.api_key_encrypted,
                connection.sync_direction,
                1 if connection.enabled else 0,
                connection.last_sync_timestamp,
                connection.sync_frequency_minutes,
                1 if connection.auto_sync else 0,
                json.dumps(connection.filters),
                json.dumps(connection.mapping_config),
                now,
                now,
            ),
        )
        # commit handled by cursor context
        connection.id = cursor.lastrowid
        return connection

    def get_connection(self, id: int) -> Optional[ExternalSourceConnection]:
        """Get connection by ID."""

        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM external_source_connections WHERE id = ?",
            (id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_connection_row(row)

    def list_connections(
        self, project_id: int, enabled_only: bool = True
    ) -> list[ExternalSourceConnection]:
        """List connections for project."""

        cursor = self.db.get_cursor()
        if enabled_only:
            cursor.execute(
                "SELECT * FROM external_source_connections WHERE project_id = ? AND enabled = 1 ORDER BY created_at DESC",
                (project_id,),
            )
        else:
            cursor.execute(
                "SELECT * FROM external_source_connections WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
        rows = cursor.fetchall()
        return [self._parse_connection_row(row) for row in rows]

    def create_data_mapping(self, mapping: ExternalDataMapping) -> ExternalDataMapping:
        """Create external data mapping."""
        from datetime import datetime

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO external_data_mappings
            (source_id, external_id, memory_id, memory_type, last_synced_timestamp,
             sync_status, sync_notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mapping.source_id,
                mapping.external_id,
                mapping.memory_id,
                mapping.memory_type,
                mapping.last_synced_timestamp,
                mapping.sync_status,
                mapping.sync_notes,
                int(datetime.now().timestamp()),
                int(datetime.now().timestamp()),
            ),
        )
        # commit handled by cursor context
        mapping.id = cursor.lastrowid
        return mapping

    def get_data_mapping(self, source_id: int, external_id: str) -> Optional[ExternalDataMapping]:
        """Get data mapping."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM external_data_mappings WHERE source_id = ? AND external_id = ?",
            (source_id, external_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._parse_mapping_row(row)

    def list_data_mappings(self, source_id: int) -> list[ExternalDataMapping]:
        """List data mappings for source."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM external_data_mappings WHERE source_id = ? ORDER BY created_at DESC",
            (source_id,),
        )
        rows = cursor.fetchall()
        return [self._parse_mapping_row(row) for row in rows]

    def create_imported_data(self, data: ImportedData) -> ImportedData:
        """Create imported data record."""
        import json
        from datetime import datetime

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            INSERT INTO imported_data
            (source_id, data_type, title, content, external_id, external_url,
             author, created_date, updated_date, metadata, imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.source_id,
                data.data_type,
                data.title,
                data.content,
                data.external_id,
                data.external_url,
                data.author,
                data.created_date,
                data.updated_date,
                json.dumps(data.metadata),
                int(datetime.now().timestamp()),
            ),
        )
        # commit handled by cursor context
        data.id = cursor.lastrowid
        return data

    def list_imported_data(self, source_id: int, limit: int = 100) -> list[ImportedData]:
        """List imported data from source."""

        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM imported_data WHERE source_id = ? ORDER BY imported_at DESC LIMIT ?",
            (source_id, limit),
        )
        rows = cursor.fetchall()
        return [self._parse_imported_data_row(row) for row in rows]

    def create_sync_log(self, log: SyncLog) -> SyncLog:
        """Create sync log entry."""
        import json
        from datetime import datetime

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())
        cursor.execute(
            """
            INSERT INTO sync_logs
            (source_id, sync_type, direction, status, items_processed,
             items_imported, items_exported, items_updated, conflicts_detected,
             errors_count, error_messages, duration_seconds, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log.source_id,
                log.sync_type,
                log.direction,
                log.status,
                log.items_processed,
                log.items_imported,
                log.items_exported,
                log.items_updated,
                log.conflicts_detected,
                log.errors_count,
                json.dumps(log.error_messages),
                log.duration_seconds,
                now,
                log.completed_at,
            ),
        )
        # commit handled by cursor context
        log.id = cursor.lastrowid
        return log

    def get_sync_history(self, source_id: int, limit: int = 50) -> list[SyncLog]:
        """Get sync history for source."""

        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM sync_logs WHERE source_id = ? ORDER BY created_at DESC LIMIT ?",
            (source_id, limit),
        )
        rows = cursor.fetchall()
        return [self._parse_sync_log_row(row) for row in rows]

    # Helper parsing methods

    @staticmethod
    def _parse_connection_row(row) -> ExternalSourceConnection:
        """Parse connection row."""
        import json

        return ExternalSourceConnection(
            id=row[0],
            project_id=row[1],
            source_type=row[2],
            source_name=row[3],
            api_endpoint=row[4],
            api_key_encrypted=row[5],
            sync_direction=row[6],
            enabled=bool(row[7]),
            last_sync_timestamp=row[8],
            sync_frequency_minutes=row[9],
            auto_sync=bool(row[10]),
            filters=json.loads(row[11]) if row[11] else {},
            mapping_config=json.loads(row[12]) if row[12] else {},
            created_at=row[13],
            updated_at=row[14],
        )

    @staticmethod
    def _parse_mapping_row(row) -> ExternalDataMapping:
        """Parse data mapping row."""
        return ExternalDataMapping(
            id=row[0],
            source_id=row[1],
            external_id=row[2],
            memory_id=row[3],
            memory_type=row[4],
            last_synced_timestamp=row[5],
            sync_status=row[6],
            sync_notes=row[7],
            created_at=row[8],
            updated_at=row[9],
        )

    @staticmethod
    def _parse_imported_data_row(row) -> ImportedData:
        """Parse imported data row."""
        import json

        return ImportedData(
            id=row[0],
            source_id=row[1],
            data_type=row[2],
            title=row[3],
            content=row[4],
            external_id=row[5],
            external_url=row[6],
            author=row[7],
            created_date=row[8],
            updated_date=row[9],
            metadata=json.loads(row[10]) if row[10] else {},
            imported_at=row[11],
        )

    @staticmethod
    def _parse_sync_log_row(row) -> SyncLog:
        """Parse sync log row."""
        import json

        return SyncLog(
            id=row[0],
            source_id=row[1],
            sync_type=row[2],
            direction=row[3],
            status=row[4],
            items_processed=row[5],
            items_imported=row[6],
            items_exported=row[7],
            items_updated=row[8],
            conflicts_detected=row[9],
            errors_count=row[10],
            error_messages=json.loads(row[11]) if row[11] else [],
            duration_seconds=row[12],
            created_at=row[13],
            completed_at=row[14],
        )
