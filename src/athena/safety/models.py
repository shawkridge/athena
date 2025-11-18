"""Data models for safety policy and audit trail management."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ChangeType(str, Enum):
    """Types of changes that trigger safety policies."""

    DELETE_FILE = "delete_file"
    MODIFY_CRITICAL = "modify_critical"
    DATABASE_CHANGE = "database_change"
    AUTH_CHANGE = "auth_change"
    DEPLOY = "deploy"
    CONFIG_CHANGE = "config_change"
    SECURITY_CHANGE = "security_change"
    INFRASTRUCTURE_CHANGE = "infrastructure_change"
    DATA_LOSS_RISK = "data_loss_risk"
    EXTERNAL_API_CHANGE = "external_api_change"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ChangeRiskLevel(str, Enum):
    """Risk level assessment for a change."""

    LOW = "low"  # < 0.2 confidence
    MEDIUM = "medium"  # 0.2-0.6 confidence
    HIGH = "high"  # 0.6-0.85 confidence
    CRITICAL = "critical"  # > 0.85 confidence (dangerous)


class SafetyPolicy(BaseModel):
    """Policy definition for agent safety."""

    id: Optional[int] = None
    project_id: int
    name: str = Field(..., description="Policy name")
    description: Optional[str] = None

    # Changes requiring approval
    approval_required_for: list[ChangeType] = Field(
        default_factory=list,
        description="Change types that require approval",
    )

    # Confidence thresholds
    auto_approve_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Auto-approve changes above this confidence",
    )
    auto_reject_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Auto-reject changes below this confidence",
    )

    # Test requirements
    require_tests_for: list[str] = Field(
        default_factory=list,
        description="File patterns requiring test coverage before approval",
    )
    min_test_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum test coverage required",
    )

    # Audit
    audit_enabled: bool = Field(default=True, description="Enable audit trail")
    keep_pre_modification_snapshot: bool = Field(
        default=True, description="Keep snapshot of pre-modification state"
    )

    # Approval workflow
    require_human_approval: bool = Field(default=False, description="Always require human approval")
    max_approval_time_hours: int = Field(default=24, description="Approval request expiration time")

    # Rollback
    enable_rollback: bool = Field(default=True, description="Enable rollback capability")
    keep_rollback_snapshots: int = Field(
        default=10, description="Number of rollback snapshots to keep"
    )

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)


class ApprovalRequest(BaseModel):
    """Request for approval of a change."""

    id: Optional[int] = None
    project_id: int
    agent_id: Optional[str] = None  # Which agent triggered this
    change_type: ChangeType
    change_description: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_level: ChangeRiskLevel

    # File/code involved
    affected_files: list[str] = Field(default_factory=list)
    affected_lines: Optional[tuple[int, int]] = None

    # Pre-modification state
    pre_snapshot_id: Optional[int] = None

    # Approval status
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime = Field(default_factory=datetime.now)
    approved_by: Optional[str] = None  # Human reviewer
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Auto-approval details
    auto_approved: bool = False
    auto_approved_reason: Optional[str] = None

    # Safety policy applied
    policy_id: Optional[int] = None

    model_config = ConfigDict(use_enum_values=True)


class AuditEntry(BaseModel):
    """Audit log entry for change tracking."""

    id: Optional[int] = None
    project_id: int
    timestamp: datetime = Field(default_factory=datetime.now)

    # Who/what made the change
    agent_id: Optional[str] = None
    user_id: Optional[str] = None

    # What changed
    change_type: ChangeType
    affected_files: list[str] = Field(default_factory=list)
    description: str

    # Change details
    approval_request_id: Optional[int] = None
    pre_snapshot_id: Optional[int] = None
    post_snapshot_id: Optional[int] = None

    # Status
    success: bool = True
    error_message: Optional[str] = None

    # Risk assessment
    risk_level: ChangeRiskLevel
    confidence_score: float = Field(ge=0.0, le=1.0)

    # Revert info
    reverted: bool = False
    reverted_at: Optional[datetime] = None
    revert_reason: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class CodeSnapshot(BaseModel):
    """Snapshot of code state for rollback capability."""

    id: Optional[int] = None
    project_id: int
    created_at: datetime = Field(default_factory=datetime.now)

    # File content
    file_path: str
    file_hash: str  # Hash of original content
    content_preview: str  # First 1000 chars
    full_content: Optional[str] = None  # Full content (can be large)

    # Context
    change_type: ChangeType
    change_id: Optional[int] = None  # Reference to approval/audit entry
    agent_id: Optional[str] = None

    # Retention
    expires_at: Optional[datetime] = None
    keep_indefinitely: bool = False

    model_config = ConfigDict(use_enum_values=True)


class ChangeRecommendation(BaseModel):
    """AI-generated recommendation for handling a change."""

    id: Optional[int] = None
    approval_request_id: int

    # Recommendation
    recommendation: str  # "approve" | "reject" | "request_changes" | "escalate"
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    # Suggested actions
    suggested_tests: list[str] = Field(default_factory=list)
    suggested_reviewers: list[str] = Field(default_factory=list)
    risk_mitigation_steps: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)
