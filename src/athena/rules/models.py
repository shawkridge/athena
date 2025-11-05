"""Pydantic models for Phase 9 Project Rules Engine."""

from enum import Enum
from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RuleCategory(str, Enum):
    """Rule categories for organization."""
    CODING_STANDARD = "coding_standard"
    PROCESS = "process"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    RESOURCE = "resource"
    QUALITY = "quality"
    CUSTOM = "custom"


class SeverityLevel(str, Enum):
    """Rule violation severity."""
    INFO = "info"           # Suggestion only
    WARNING = "warning"     # Should comply, not required
    ERROR = "error"         # Must comply, blocks execution
    CRITICAL = "critical"   # Must comply, requires escalation


class RuleType(str, Enum):
    """Types of rules."""
    CONSTRAINT = "constraint"      # Must/must not do something
    PATTERN = "pattern"            # Should follow pattern
    THRESHOLD = "threshold"        # Numeric limit
    APPROVAL = "approval"          # Requires sign-off
    SCHEDULE = "schedule"          # Time-based constraint
    DEPENDENCY = "dependency"      # Must depend on/avoid
    CUSTOM = "custom"              # Custom validation logic


class Rule(BaseModel):
    """Represents a single project rule."""
    id: Optional[int] = None
    project_id: int

    name: str = Field(..., description="Rule identifier (e.g., 'no_unreviewed_deploy')")
    description: str = Field(..., description="Human-readable rule description")
    category: RuleCategory
    rule_type: RuleType
    severity: SeverityLevel = SeverityLevel.WARNING

    # Rule definition
    condition: str = Field(..., description="Rule condition (JSON or expression)")
    exception_condition: Optional[str] = None  # When rule doesn't apply

    # Metadata
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    created_by: str = "system"
    enabled: bool = True

    # Enforcement
    auto_block: bool = True  # If True, blocks execution; if False, warns
    can_override: bool = True  # Allow user override with justification
    override_requires_approval: bool = False

    # Metadata
    tags: List[str] = Field(default_factory=list)  # For filtering/grouping
    related_rules: List[int] = Field(default_factory=list)  # Rule IDs
    documentation_url: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class RuleTemplate(BaseModel):
    """Reusable rule templates for onboarding projects."""
    id: Optional[int] = None

    name: str  # e.g., "DataProcessingPipeline", "WebService"
    description: str
    category: str  # Problem domain
    rules: List[Rule]  # Pre-configured rules

    usage_count: int = 0
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    model_config = ConfigDict(use_enum_values=True)


class RuleValidationResult(BaseModel):
    """Result of validating task against rules."""
    task_id: int
    project_id: int
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    # Overall status
    is_compliant: bool
    violation_count: int
    warning_count: int

    # Detailed violations
    violations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of {rule_id, rule_name, severity, message, suggestion}"
    )

    # Suggestions
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions to make task compliant"
    )

    # Blocks
    blocking_violations: List[int] = Field(
        default_factory=list,
        description="Rule IDs that block execution"
    )

    model_config = ConfigDict(use_enum_values=True)


class RuleOverride(BaseModel):
    """Record of rule override with justification."""
    id: Optional[int] = None
    project_id: int
    rule_id: int
    task_id: int

    overridden_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    overridden_by: str  # User/agent ID
    justification: str  # Why this override?
    approved_by: Optional[str] = None
    approval_at: Optional[int] = None

    expires_at: Optional[int] = None  # Temporary override?
    status: str = "active"  # active, expired, revoked

    model_config = ConfigDict(use_enum_values=True)


class ProjectRuleConfig(BaseModel):
    """Project-level rule configuration."""
    id: Optional[int] = None
    project_id: int

    # Enforcement policy
    enforcement_level: SeverityLevel = SeverityLevel.WARNING
    auto_suggest_compliant_alternatives: bool = True
    auto_block_violations: bool = False  # If True, auto-block critical/error

    # Approval settings
    require_approval_for_override: bool = False
    min_approvers: int = 1
    approval_ttl_hours: int = 24

    # Notifications
    notify_on_violation: bool = True
    notify_channels: List[str] = Field(default_factory=list)  # email, slack, etc

    # Learning
    auto_generate_rules_from_patterns: bool = False
    confidence_threshold_for_auto_rules: float = 0.85

    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    model_config = ConfigDict(use_enum_values=True)
