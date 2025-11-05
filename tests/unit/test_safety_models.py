"""Unit tests for safety models."""

import pytest
from datetime import datetime

from src.memory_mcp.safety.models import (
    SafetyPolicy,
    ApprovalRequest,
    ApprovalStatus,
    AuditEntry,
    ChangeType,
    ChangeRiskLevel,
    CodeSnapshot,
    ChangeRecommendation,
)


class TestSafetyPolicy:
    """Tests for SafetyPolicy model."""

    def test_create_policy(self):
        """Test creating a policy."""
        policy = SafetyPolicy(
            project_id=1,
            name="default",
            approval_required_for=[ChangeType.AUTH_CHANGE],
            auto_approve_threshold=0.85,
        )
        assert policy.project_id == 1
        assert policy.name == "default"
        assert policy.auto_approve_threshold == 0.85
        assert policy.audit_enabled is True

    def test_policy_thresholds(self):
        """Test threshold validation."""
        policy = SafetyPolicy(
            project_id=1,
            name="strict",
            auto_approve_threshold=0.95,
            auto_reject_threshold=0.1,
        )
        assert policy.auto_approve_threshold == 0.95
        assert policy.auto_reject_threshold == 0.1

    def test_policy_defaults(self):
        """Test default values."""
        policy = SafetyPolicy(project_id=1, name="test")
        assert policy.audit_enabled is True
        assert policy.keep_pre_modification_snapshot is True
        assert policy.enable_rollback is True
        assert policy.require_human_approval is False


class TestApprovalRequest:
    """Tests for ApprovalRequest model."""

    def test_create_request(self):
        """Test creating an approval request."""
        request = ApprovalRequest(
            project_id=1,
            change_type=ChangeType.AUTH_CHANGE,
            change_description="Update JWT logic",
            confidence_score=0.82,
            risk_level=ChangeRiskLevel.MEDIUM,
            affected_files=["src/auth.py"],
        )
        assert request.project_id == 1
        assert request.change_type == ChangeType.AUTH_CHANGE
        assert request.status == ApprovalStatus.PENDING

    def test_auto_approved_request(self):
        """Test auto-approved request."""
        request = ApprovalRequest(
            project_id=1,
            change_type=ChangeType.MODIFY_CRITICAL,
            change_description="Fix bug",
            confidence_score=0.92,
            risk_level=ChangeRiskLevel.LOW,
            affected_files=["src/utils.py"],
            status=ApprovalStatus.APPROVED,
            auto_approved=True,
            auto_approved_reason="High confidence",
        )
        assert request.auto_approved is True
        assert request.status == ApprovalStatus.APPROVED

    def test_confidence_score_validation(self):
        """Test confidence score bounds."""
        # Valid range: 0.0-1.0
        request = ApprovalRequest(
            project_id=1,
            change_type=ChangeType.DELETE_FILE,
            change_description="Delete old file",
            confidence_score=0.0,  # Min
            risk_level=ChangeRiskLevel.CRITICAL,
            affected_files=["src/old.py"],
        )
        assert request.confidence_score == 0.0

        request = ApprovalRequest(
            project_id=1,
            change_type=ChangeType.DELETE_FILE,
            change_description="Delete old file",
            confidence_score=1.0,  # Max
            risk_level=ChangeRiskLevel.LOW,
            affected_files=["src/old.py"],
        )
        assert request.confidence_score == 1.0


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_create_audit_entry(self):
        """Test creating an audit entry."""
        entry = AuditEntry(
            project_id=1,
            agent_id="agent-1",
            change_type=ChangeType.AUTH_CHANGE,
            affected_files=["src/auth.py"],
            description="OAuth2 implementation",
            risk_level=ChangeRiskLevel.HIGH,
            confidence_score=0.88,
            success=True,
        )
        assert entry.project_id == 1
        assert entry.success is True
        assert entry.reverted is False

    def test_failed_audit_entry(self):
        """Test failed change audit."""
        entry = AuditEntry(
            project_id=1,
            change_type=ChangeType.DATABASE_CHANGE,
            affected_files=["migrations/001_users.sql"],
            description="Add users table",
            risk_level=ChangeRiskLevel.CRITICAL,
            confidence_score=0.45,
            success=False,
            error_message="Database locked",
        )
        assert entry.success is False
        assert entry.error_message == "Database locked"

    def test_reverted_entry(self):
        """Test reverted change."""
        entry = AuditEntry(
            project_id=1,
            change_type=ChangeType.CONFIG_CHANGE,
            affected_files=["config.yaml"],
            description="Update config",
            risk_level=ChangeRiskLevel.MEDIUM,
            confidence_score=0.70,
            reverted=True,
            revert_reason="Caused performance degradation",
        )
        assert entry.reverted is True
        assert entry.revert_reason == "Caused performance degradation"


class TestCodeSnapshot:
    """Tests for CodeSnapshot model."""

    def test_create_snapshot(self):
        """Test creating a code snapshot."""
        snapshot = CodeSnapshot(
            project_id=1,
            file_path="src/auth.py",
            file_hash="abc123def456",
            content_preview="def login():\n    pass",
            change_type=ChangeType.AUTH_CHANGE,
            agent_id="agent-1",
        )
        assert snapshot.project_id == 1
        assert snapshot.file_path == "src/auth.py"
        assert snapshot.keep_indefinitely is False

    def test_snapshot_with_full_content(self):
        """Test snapshot with full content."""
        full_content = "def login():\n    return authenticate()\n" * 100
        snapshot = CodeSnapshot(
            project_id=1,
            file_path="src/auth.py",
            file_hash="hash123",
            content_preview="def login():\n    return authenticate()",
            full_content=full_content,
            change_type=ChangeType.AUTH_CHANGE,
        )
        assert snapshot.full_content == full_content

    def test_snapshot_expiration(self):
        """Test snapshot expiration."""
        from datetime import timedelta

        future = datetime.now() + timedelta(hours=24)
        snapshot = CodeSnapshot(
            project_id=1,
            file_path="src/test.py",
            file_hash="hash",
            content_preview="content",
            change_type=ChangeType.MODIFY_CRITICAL,
            expires_at=future,
            keep_indefinitely=False,
        )
        assert snapshot.expires_at == future
        assert snapshot.keep_indefinitely is False


class TestChangeRecommendation:
    """Tests for ChangeRecommendation model."""

    def test_create_recommendation(self):
        """Test creating a recommendation."""
        rec = ChangeRecommendation(
            approval_request_id=1,
            recommendation="approve",
            reasoning="High confidence and low risk",
            confidence=0.92,
            suggested_tests=["test_auth.py::test_login"],
            suggested_reviewers=["lead-dev@org"],
            risk_mitigation_steps=["Add integration tests", "Monitor metrics"],
        )
        assert rec.approval_request_id == 1
        assert rec.recommendation == "approve"
        assert len(rec.suggested_tests) == 1

    def test_rejection_recommendation(self):
        """Test rejection recommendation."""
        rec = ChangeRecommendation(
            approval_request_id=2,
            recommendation="reject",
            reasoning="Insufficient test coverage",
            confidence=0.88,
            suggested_tests=["Add unit tests for new feature"],
            risk_mitigation_steps=["Increase test coverage to >80%"],
        )
        assert rec.recommendation == "reject"


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_all_change_types(self):
        """Test all change types are defined."""
        types = [
            ChangeType.AUTH_CHANGE,
            ChangeType.DATABASE_CHANGE,
            ChangeType.DELETE_FILE,
            ChangeType.CONFIG_CHANGE,
            ChangeType.SECURITY_CHANGE,
            ChangeType.INFRASTRUCTURE_CHANGE,
            ChangeType.DEPLOY,
            ChangeType.DATA_LOSS_RISK,
            ChangeType.EXTERNAL_API_CHANGE,
            ChangeType.MODIFY_CRITICAL,
        ]
        assert len(types) == 10


class TestChangeRiskLevel:
    """Tests for ChangeRiskLevel enum."""

    def test_risk_levels(self):
        """Test risk level ordering."""
        levels = [
            ChangeRiskLevel.LOW,
            ChangeRiskLevel.MEDIUM,
            ChangeRiskLevel.HIGH,
            ChangeRiskLevel.CRITICAL,
        ]
        assert len(levels) == 4


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_approval_statuses(self):
        """Test all approval statuses."""
        statuses = [
            ApprovalStatus.PENDING,
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        ]
        assert len(statuses) == 5


class TestModelSerialization:
    """Tests for model serialization."""

    def test_policy_to_dict(self):
        """Test policy serialization."""
        policy = SafetyPolicy(
            project_id=1,
            name="test",
            approval_required_for=[ChangeType.AUTH_CHANGE],
        )
        data = policy.dict()
        assert data["project_id"] == 1
        assert data["name"] == "test"
        assert ChangeType.AUTH_CHANGE in data["approval_required_for"]

    def test_request_to_json(self):
        """Test request JSON serialization."""
        request = ApprovalRequest(
            project_id=1,
            change_type=ChangeType.AUTH_CHANGE,
            change_description="Update JWT",
            confidence_score=0.92,
            risk_level=ChangeRiskLevel.MEDIUM,
            affected_files=["src/auth.py"],
        )
        json_str = request.json()
        assert "auth.py" in json_str
        assert "0.92" in json_str
