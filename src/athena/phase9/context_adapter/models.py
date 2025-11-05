"""Data models for Phase 9.3: Infinite Context Adapter."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExternalSourceType(str, Enum):
    """Types of external systems to connect."""

    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    LINEAR = "linear"
    AZURE_DEVOPS = "azure_devops"
    CUSTOM = "custom"
    CONFLUENCE = "confluence"
    NOTION = "notion"


class SyncDirection(str, Enum):
    """Direction of data synchronization."""

    IMPORT = "import"  # External → Memory MCP
    EXPORT = "export"  # Memory MCP → External
    BIDIRECTIONAL = "bidirectional"  # Both directions


class ExternalSourceConnection(BaseModel):
    """Configuration for external source connection."""

    id: Optional[int] = None
    project_id: int
    source_type: ExternalSourceType
    source_name: str  # e.g., "MyCompany/RepoName" for GitHub
    api_endpoint: str  # API base URL
    api_key_encrypted: str  # Encrypted API key
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    enabled: bool = True
    last_sync_timestamp: Optional[int] = None
    sync_frequency_minutes: int = 60  # How often to sync
    auto_sync: bool = True  # Automatic synchronization
    filters: dict = Field(default_factory=dict)  # Source-specific filters
    mapping_config: dict = Field(default_factory=dict)  # Field mappings
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ExternalDataMapping(BaseModel):
    """Mapping between external data and memory entities."""

    id: Optional[int] = None
    source_id: int  # ExternalSourceConnection ID
    external_id: str  # ID in external system
    memory_id: int  # ID in memory system
    memory_type: str  # Type: "task", "event", "entity", "relation"
    last_synced_timestamp: int
    sync_status: str = "synced"  # "synced", "pending", "conflict", "error"
    sync_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ExternalDataSnapshot(BaseModel):
    """Snapshot of external data before/after sync."""

    id: Optional[int] = None
    source_id: int
    external_id: str
    data_type: str  # "github_pr", "jira_issue", "slack_message", etc.
    data_snapshot: dict  # Full data snapshot as JSON
    timestamp: int
    operation: str = "sync"  # "import", "export", "update"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ImportedData(BaseModel):
    """Data imported from external source."""

    id: Optional[int] = None
    source_id: int  # ExternalSourceConnection ID
    data_type: str  # "issue", "pr", "message", "ticket", etc.
    title: str
    content: str
    external_id: str
    external_url: str
    author: str
    created_date: int
    updated_date: int
    metadata: dict = Field(default_factory=dict)  # Source-specific metadata
    imported_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ExportedInsight(BaseModel):
    """Insight/finding exported to external system."""

    id: Optional[int] = None
    target_source_id: int  # Where to export
    insight_type: str  # "pattern", "recommendation", "summary", "prediction"
    title: str
    description: str
    relevant_tasks: list[int] = Field(default_factory=list)
    confidence_level: Optional[float] = None  # 0-1 confidence
    external_id: Optional[str] = None  # ID after export
    export_status: str = "pending"  # "pending", "exported", "updated", "failed"
    export_timestamp: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class SyncConflict(BaseModel):
    """Conflict detected during bidirectional sync."""

    id: Optional[int] = None
    source_id: int
    external_id: str
    memory_id: int
    conflict_type: str  # "data_divergence", "timestamp_conflict", "version_mismatch"
    external_version: dict  # External data version
    memory_version: dict  # Memory data version
    resolution_strategy: str = "manual"  # "manual", "prefer_external", "prefer_memory"
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolution_timestamp: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class SyncLog(BaseModel):
    """Log of synchronization activities."""

    id: Optional[int] = None
    source_id: int
    sync_type: str = "full"  # "full", "incremental", "manual"
    direction: str  # "import", "export"
    status: str = "in_progress"  # "in_progress", "completed", "failed", "partial"
    items_processed: int = 0
    items_imported: int = 0
    items_exported: int = 0
    items_updated: int = 0
    conflicts_detected: int = 0
    errors_count: int = 0
    error_messages: list[str] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[int] = None

    class Config:
        use_enum_values = True
