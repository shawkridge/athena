"""
Notification and alert models for real-time notification system.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts that can be triggered."""
    PERFORMANCE = "performance"
    SYSTEM = "system"
    MEMORY = "memory"
    CPU = "cpu"
    LATENCY = "latency"
    DISK = "disk"
    DATABASE = "database"
    HOOK = "hook"
    CONSOLIDATION = "consolidation"
    ERROR = "error"
    CUSTOM = "custom"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    ARCHIVED = "archived"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    """Channels for delivering notifications."""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


# Models for API
class AlertRule(BaseModel):
    """Alert rule configuration."""
    id: Optional[int] = None
    name: str
    alert_type: AlertType
    condition: str  # e.g., "cpu_usage > 80"
    severity: AlertLevel
    enabled: bool = True
    channels: list[NotificationChannel] = [NotificationChannel.IN_APP]
    project_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Notification(BaseModel):
    """A notification instance."""
    id: Optional[int] = None
    alert_type: AlertType
    title: str
    message: str
    level: AlertLevel
    status: NotificationStatus = NotificationStatus.PENDING
    channels: list[NotificationChannel]
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    project_id: Optional[int] = None

    class Config:
        from_attributes = True


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    id: Optional[int] = None
    user_id: Optional[str] = None
    project_id: Optional[int] = None

    # Channel preferences
    enable_in_app: bool = True
    enable_email: bool = False
    enable_webhook: bool = False
    enable_slack: bool = False

    # Alert type preferences
    alert_types: list[AlertType] = [
        AlertType.PERFORMANCE,
        AlertType.SYSTEM,
        AlertType.ERROR,
    ]

    # Alert level preferences
    min_level: AlertLevel = AlertLevel.WARNING

    # Email settings
    email_address: Optional[str] = None
    email_digest: bool = False  # Daily digest vs immediate
    email_digest_time: str = "09:00"  # HH:MM format

    # Webhook settings
    webhook_url: Optional[str] = None
    webhook_events: list[AlertType] = []

    # Slack settings
    slack_webhook: Optional[str] = None
    slack_channel: str = "#alerts"

    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"  # HH:MM format
    quiet_hours_end: str = "08:00"

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    """Request model for creating a notification."""
    alert_type: AlertType
    title: str
    message: str
    level: AlertLevel
    channels: list[NotificationChannel] = [NotificationChannel.IN_APP]
    metadata: Dict[str, Any] = {}
    project_id: Optional[int] = None


class NotificationUpdate(BaseModel):
    """Request model for updating a notification."""
    status: Optional[NotificationStatus] = None
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


class AlertRuleCreate(BaseModel):
    """Request model for creating an alert rule."""
    name: str
    alert_type: AlertType
    condition: str
    severity: AlertLevel
    enabled: bool = True
    channels: list[NotificationChannel] = [NotificationChannel.IN_APP]
    project_id: Optional[int] = None


class AlertRuleUpdate(BaseModel):
    """Request model for updating an alert rule."""
    name: Optional[str] = None
    condition: Optional[str] = None
    severity: Optional[AlertLevel] = None
    enabled: Optional[bool] = None
    channels: Optional[list[NotificationChannel]] = None


class NotificationResponse(BaseModel):
    """Response model for notification."""
    id: int
    alert_type: AlertType
    title: str
    message: str
    level: AlertLevel
    status: NotificationStatus
    channels: list[NotificationChannel]
    metadata: Dict[str, Any]
    created_at: datetime
    read_at: Optional[datetime]
    archived_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response model for notification list."""
    notifications: list[NotificationResponse]
    total: int
    unread_count: int
    critical_count: int


class WebSocketNotification(BaseModel):
    """WebSocket notification message."""
    type: str = "notification"
    notification: NotificationResponse
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def dict_for_json(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for JSON serialization."""
        data = self.dict()
        data['timestamp'] = data['timestamp'].isoformat()
        data['notification']['created_at'] = data['notification']['created_at'].isoformat()
        if data['notification']['read_at']:
            data['notification']['read_at'] = data['notification']['read_at'].isoformat()
        if data['notification']['archived_at']:
            data['notification']['archived_at'] = data['notification']['archived_at'].isoformat()
        return data
