"""Unit tests for Phase 9.3: Infinite Context Adapter."""

import pytest

from athena.core.database import Database
from athena.phase9.context_adapter import (
    ContextAdapterStore,
    ExportedInsight,
    ExternalDataMapping,
    ExternalSourceConnection,
    ExternalSourceType,
    ExternalSystemBridge,
    ImportedData,
    SyncDirection,
    SyncLog,
)


@pytest.fixture
def context_store(tmp_path):
    """Create context adapter store for testing."""
    db = Database(str(tmp_path / "test_context.db"))
    return ContextAdapterStore(db)


@pytest.fixture
def bridge(context_store):
    """Create external system bridge for testing."""
    return ExternalSystemBridge(context_store)


class TestExternalSourceConnection:
    """Test external source connection functionality."""

    def test_create_connection(self, context_store):
        """Test creating external source connection."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="MyCompany/RepoName",
            api_endpoint="https://api.github.com",
            api_key_encrypted="encrypted_key_123",
            sync_direction=SyncDirection.BIDIRECTIONAL,
            enabled=True,
        )

        saved = context_store.create_connection(connection)
        assert saved.id is not None
        assert saved.source_type == ExternalSourceType.GITHUB
        assert saved.enabled is True

    def test_get_connection(self, context_store):
        """Test retrieving connection."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.JIRA,
            source_name="MyCompany/Project",
            api_endpoint="https://jira.example.com",
            api_key_encrypted="key",
        )
        saved = context_store.create_connection(connection)

        retrieved = context_store.get_connection(saved.id)
        assert retrieved is not None
        assert retrieved.source_type == ExternalSourceType.JIRA

    def test_list_connections(self, context_store):
        """Test listing connections."""
        for source_type in [ExternalSourceType.GITHUB, ExternalSourceType.JIRA, ExternalSourceType.SLACK]:
            connection = ExternalSourceConnection(
                project_id=1,
                source_type=source_type,
                source_name=f"connection_{source_type}",
                api_endpoint="https://example.com",
                api_key_encrypted="key",
                enabled=True,
            )
            context_store.create_connection(connection)

        connections = context_store.list_connections(1)
        assert len(connections) == 3

    def test_list_connections_enabled_only(self, context_store):
        """Test listing only enabled connections."""
        # Create enabled connection
        enabled_conn = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="enabled",
            api_endpoint="https://api.github.com",
            api_key_encrypted="key",
            enabled=True,
        )
        context_store.create_connection(enabled_conn)

        # Create disabled connection
        disabled_conn = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.JIRA,
            source_name="disabled",
            api_endpoint="https://jira.example.com",
            api_key_encrypted="key",
            enabled=False,
        )
        context_store.create_connection(disabled_conn)

        # List enabled only
        enabled_list = context_store.list_connections(1, enabled_only=True)
        assert len(enabled_list) == 1
        assert enabled_list[0].source_type == ExternalSourceType.GITHUB

        # List all
        all_list = context_store.list_connections(1, enabled_only=False)
        assert len(all_list) == 2


class TestExternalDataMapping:
    """Test external data mapping functionality."""

    def test_create_data_mapping(self, context_store):
        """Test creating data mapping."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="repo",
            api_endpoint="https://api.github.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        mapping = ExternalDataMapping(
            source_id=saved_conn.id,
            external_id="gh_pr_123",
            memory_id=42,
            memory_type="task",
            last_synced_timestamp=int(__import__("time").time()),
        )

        saved = context_store.create_data_mapping(mapping)
        assert saved.id is not None
        assert saved.external_id == "gh_pr_123"

    def test_get_data_mapping(self, context_store):
        """Test retrieving data mapping."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.JIRA,
            source_name="project",
            api_endpoint="https://jira.example.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        mapping = ExternalDataMapping(
            source_id=saved_conn.id,
            external_id="jira_issue_456",
            memory_id=43,
            memory_type="task",
            last_synced_timestamp=int(__import__("time").time()),
        )
        context_store.create_data_mapping(mapping)

        retrieved = context_store.get_data_mapping(saved_conn.id, "jira_issue_456")
        assert retrieved is not None
        assert retrieved.memory_id == 43

    def test_list_data_mappings(self, context_store):
        """Test listing data mappings."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="repo",
            api_endpoint="https://api.github.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        for i in range(3):
            mapping = ExternalDataMapping(
                source_id=saved_conn.id,
                external_id=f"id_{i}",
                memory_id=100 + i,
                memory_type="task",
                last_synced_timestamp=int(__import__("time").time()),
            )
            context_store.create_data_mapping(mapping)

        mappings = context_store.list_data_mappings(saved_conn.id)
        assert len(mappings) == 3


class TestImportedData:
    """Test imported data functionality."""

    def test_create_imported_data(self, context_store):
        """Test creating imported data record."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="repo",
            api_endpoint="https://api.github.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        data = ImportedData(
            source_id=saved_conn.id,
            data_type="pull_request",
            title="Add new feature",
            content="This PR adds a new authentication system",
            external_id="pr_789",
            external_url="https://github.com/MyCompany/repo/pull/789",
            author="alice@example.com",
            created_date=int(__import__("time").time()),
            updated_date=int(__import__("time").time()),
        )

        saved = context_store.create_imported_data(data)
        assert saved.id is not None
        assert saved.title == "Add new feature"

    def test_list_imported_data(self, context_store):
        """Test listing imported data."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.JIRA,
            source_name="project",
            api_endpoint="https://jira.example.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        for i in range(3):
            data = ImportedData(
                source_id=saved_conn.id,
                data_type="issue",
                title=f"Issue {i}",
                content=f"Description of issue {i}",
                external_id=f"issue_{i}",
                external_url=f"https://jira.example.com/browse/PROJ-{i}",
                author="bob@example.com",
                created_date=int(__import__("time").time()),
                updated_date=int(__import__("time").time()),
            )
            context_store.create_imported_data(data)

        imported = context_store.list_imported_data(saved_conn.id)
        assert len(imported) == 3


class TestSyncLog:
    """Test sync log functionality."""

    def test_create_sync_log(self, context_store):
        """Test creating sync log entry."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="repo",
            api_endpoint="https://api.github.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        log = SyncLog(
            source_id=saved_conn.id,
            sync_type="full",
            direction="import",
            status="completed",
            items_processed=50,
            items_imported=48,
            items_exported=0,
            items_updated=2,
            conflicts_detected=0,
            errors_count=0,
            duration_seconds=15.5,
        )

        saved = context_store.create_sync_log(log)
        assert saved.id is not None
        assert saved.items_imported == 48

    def test_get_sync_history(self, context_store):
        """Test retrieving sync history."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.JIRA,
            source_name="project",
            api_endpoint="https://jira.example.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        for i in range(5):
            log = SyncLog(
                source_id=saved_conn.id,
                sync_type="incremental",
                direction="import",
                status="completed",
                items_processed=10 + i,
                items_imported=9 + i,
                duration_seconds=5.0 + i,
            )
            context_store.create_sync_log(log)

        history = context_store.get_sync_history(saved_conn.id)
        assert len(history) == 5
        # Verify we get all the sync logs back
        assert all(log.sync_type == "incremental" for log in history)
        assert all(log.direction == "import" for log in history)


class TestExternalSystemBridge:
    """Test external system bridge functionality."""

    def test_map_external_to_memory(self, bridge, context_store):
        """Test mapping external data to memory."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="repo",
            api_endpoint="https://api.github.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        mapping = bridge.map_external_to_memory(
            source_id=saved_conn.id,
            external_id="gh_issue_123",
            memory_id=42,
            memory_type="task",
        )

        assert mapping.source_id == saved_conn.id
        assert mapping.external_id == "gh_issue_123"
        assert mapping.memory_id == 42
        assert mapping.sync_status == "synced"

    def test_get_sync_status(self, bridge, context_store):
        """Test getting sync status."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.SLACK,
            source_name="workspace",
            api_endpoint="https://slack.com/api",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        status = bridge.get_sync_status(saved_conn.id)
        assert status["source_id"] == saved_conn.id
        assert status["source_type"] == ExternalSourceType.SLACK
        assert status["last_sync"] is None  # Never synced

    def test_get_sync_status_with_history(self, bridge, context_store):
        """Test sync status with history."""
        connection = ExternalSourceConnection(
            project_id=1,
            source_type=ExternalSourceType.GITHUB,
            source_name="repo",
            api_endpoint="https://api.github.com",
            api_key_encrypted="key",
        )
        saved_conn = context_store.create_connection(connection)

        log = SyncLog(
            source_id=saved_conn.id,
            sync_type="full",
            direction="import",
            status="completed",
            items_imported=25,
        )
        context_store.create_sync_log(log)

        status = bridge.get_sync_status(saved_conn.id)
        assert status["last_sync_status"] == "completed"
        assert status["last_items_imported"] == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
