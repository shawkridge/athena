"""Unit tests for SafetyEvaluator."""

import pytest
from pathlib import Path

from src.memory_mcp.core.database import Database
from src.memory_mcp.safety.evaluator import SafetyEvaluator
from src.memory_mcp.safety.models import (
    ChangeType,
    ChangeRiskLevel,
    ApprovalStatus,
)


@pytest.fixture
def db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    yield db
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def evaluator(db):
    """Create a SafetyEvaluator instance."""
    return SafetyEvaluator(db)


class TestRiskAssessment:
    """Tests for risk assessment logic."""

    def test_assess_risk_low(self, evaluator):
        """Test low-risk assessment."""
        risk = evaluator._assess_risk_level(0.95)  # High confidence = low risk
        assert risk == ChangeRiskLevel.LOW

    def test_assess_risk_medium(self, evaluator):
        """Test medium-risk assessment."""
        risk = evaluator._assess_risk_level(0.65)
        assert risk == ChangeRiskLevel.MEDIUM

    def test_assess_risk_high(self, evaluator):
        """Test high-risk assessment."""
        risk = evaluator._assess_risk_level(0.35)
        assert risk == ChangeRiskLevel.HIGH

    def test_assess_risk_critical(self, evaluator):
        """Test critical-risk assessment."""
        risk = evaluator._assess_risk_level(0.05)
        assert risk == ChangeRiskLevel.CRITICAL

    def test_assess_change_risk(self, evaluator):
        """Test comprehensive risk assessment."""
        risk = evaluator.assess_risk(0.75, ChangeType.AUTH_CHANGE, 2)
        assert risk["base_risk_level"] == ChangeRiskLevel.MEDIUM
        assert risk["severity_multiplier"] > 1.0  # Auth changes increase severity
        assert risk["confidence_score"] == 0.75


class TestDecisionMaking:
    """Tests for approval decision logic."""

    def test_requires_approval_for_critical_type(self, evaluator):
        """Test approval required for critical change types."""
        policy = evaluator._get_default_policy(1)
        requires = evaluator._requires_approval(
            ChangeType.DELETE_FILE,
            policy,
            ChangeRiskLevel.MEDIUM,
            0.80,
        )
        assert requires is True

    def test_requires_approval_for_low_confidence(self, evaluator):
        """Test approval required for low confidence."""
        policy = evaluator._get_default_policy(1)
        requires = evaluator._requires_approval(
            ChangeType.MODIFY_CRITICAL,
            policy,
            ChangeRiskLevel.MEDIUM,
            0.60,  # Below threshold
        )
        assert requires is True

    def test_no_approval_for_high_confidence(self, evaluator):
        """Test no approval needed for high confidence."""
        policy = evaluator._get_default_policy(1)
        policy.approval_required_for = []
        requires = evaluator._requires_approval(
            ChangeType.MODIFY_CRITICAL,
            policy,
            ChangeRiskLevel.LOW,
            0.92,  # Above threshold
        )
        assert requires is False

    def test_make_decision_auto_approve(self, evaluator):
        """Test auto-approve decision."""
        policy = evaluator._get_default_policy(1)
        decision = evaluator._make_decision(
            policy,
            ChangeRiskLevel.LOW,
            0.92,
            requires_approval=False,
        )
        assert decision == "auto_approve"

    def test_make_decision_auto_reject(self, evaluator):
        """Test auto-reject decision."""
        policy = evaluator._get_default_policy(1)
        decision = evaluator._make_decision(
            policy,
            ChangeRiskLevel.CRITICAL,
            0.10,  # Below rejection threshold
            requires_approval=True,
        )
        assert decision == "auto_reject"

    def test_make_decision_require_approval(self, evaluator):
        """Test require approval decision."""
        policy = evaluator._get_default_policy(1)
        decision = evaluator._make_decision(
            policy,
            ChangeRiskLevel.HIGH,
            0.70,  # In approval range
            requires_approval=True,
        )
        assert decision == "require_approval"


class TestChangeEvaluation:
    """Tests for full change evaluation."""

    def test_evaluate_high_confidence_change(self, evaluator):
        """Test evaluation of high-confidence change."""
        result = evaluator.evaluate_change(
            project_id=1,
            change_type=ChangeType.CONFIG_CHANGE,
            confidence_score=0.95,
            affected_files=["config.yaml"],
            agent_id="agent-1",
            description="Update config settings",
        )
        assert result["decision"] == "auto_approve"
        assert result["confidence_score"] == 0.95

    def test_evaluate_low_confidence_change(self, evaluator):
        """Test evaluation of low-confidence change."""
        result = evaluator.evaluate_change(
            project_id=1,
            change_type=ChangeType.AUTH_CHANGE,
            confidence_score=0.15,
            affected_files=["src/auth.py"],
            agent_id="agent-1",
            description="Auth update",
        )
        assert result["decision"] == "auto_reject"

    def test_evaluate_critical_change(self, evaluator):
        """Test evaluation of critical change."""
        result = evaluator.evaluate_change(
            project_id=1,
            change_type=ChangeType.DATABASE_CHANGE,
            confidence_score=0.75,
            affected_files=["migrations/001.sql"],
            agent_id="agent-1",
            description="Database migration",
        )
        assert result["decision"] == "require_approval"
        assert result["risk_level"] == ChangeRiskLevel.MEDIUM


class TestApprovalRequests:
    """Tests for approval request creation."""

    def test_create_auto_approved_request(self, evaluator):
        """Test creating an auto-approved request."""
        request = evaluator.create_approval_request(
            project_id=1,
            change_type=ChangeType.CONFIG_CHANGE,
            confidence_score=0.92,
            affected_files=["config.yaml"],
            change_description="Config update",
            agent_id="agent-1",
        )
        assert request.status == ApprovalStatus.APPROVED
        assert request.auto_approved is True

    def test_create_auto_rejected_request(self, evaluator):
        """Test creating an auto-rejected request."""
        request = evaluator.create_approval_request(
            project_id=1,
            change_type=ChangeType.AUTH_CHANGE,
            confidence_score=0.10,
            affected_files=["src/auth.py"],
            change_description="Auth change",
            agent_id="agent-1",
        )
        assert request.status == ApprovalStatus.REJECTED

    def test_create_pending_request(self, evaluator):
        """Test creating a pending approval request."""
        request = evaluator.create_approval_request(
            project_id=1,
            change_type=ChangeType.AUTH_CHANGE,
            confidence_score=0.65,
            affected_files=["src/auth.py"],
            change_description="Auth update",
            agent_id="agent-1",
        )
        assert request.status == ApprovalStatus.PENDING


class TestSnapshotCreation:
    """Tests for code snapshot creation."""

    def test_create_basic_snapshot(self, evaluator):
        """Test creating a basic snapshot."""
        snapshot = evaluator.create_snapshot(
            project_id=1,
            file_path="src/auth.py",
            file_hash="abc123",
            content_preview="def login():\n    pass",
            change_type=ChangeType.AUTH_CHANGE,
            agent_id="agent-1",
        )
        assert snapshot.id is not None
        assert snapshot.file_path == "src/auth.py"
        assert snapshot.keep_indefinitely is False

    def test_create_snapshot_indefinite(self, evaluator):
        """Test creating snapshot with indefinite retention."""
        snapshot = evaluator.create_snapshot(
            project_id=1,
            file_path="src/critical.py",
            file_hash="hash123",
            content_preview="critical",
            change_type=ChangeType.MODIFY_CRITICAL,
            keep_indefinitely=True,
        )
        assert snapshot.keep_indefinitely is True
        assert snapshot.expires_at is None

    def test_create_snapshot_with_full_content(self, evaluator):
        """Test creating snapshot with full content."""
        full_content = "def login():\n    return authenticate()\n" * 100
        snapshot = evaluator.create_snapshot(
            project_id=1,
            file_path="src/auth.py",
            file_hash="hash456",
            content_preview="def login():\n    return authenticate()",
            change_type=ChangeType.AUTH_CHANGE,
            full_content=full_content,
        )
        assert snapshot.full_content == full_content


class TestChangeRecording:
    """Tests for recording changes."""

    def test_record_successful_change(self, evaluator):
        """Test recording a successful change."""
        audit = evaluator.record_change(
            project_id=1,
            approval_request_id=1,
            change_type=ChangeType.AUTH_CHANGE,
            affected_files=["src/auth.py"],
            description="OAuth2 implementation complete",
            success=True,
            agent_id="agent-1",
        )
        assert audit.id is not None
        assert audit.success is True

    def test_record_failed_change(self, evaluator):
        """Test recording a failed change."""
        audit = evaluator.record_change(
            project_id=1,
            approval_request_id=1,
            change_type=ChangeType.DATABASE_CHANGE,
            affected_files=["migrations/001.sql"],
            description="Migration failed",
            success=False,
            error_message="Database locked",
            agent_id="agent-1",
        )
        assert audit.success is False
        assert audit.error_message == "Database locked"


class TestPolicyCreation:
    """Tests for policy creation."""

    def test_get_default_policy(self, evaluator):
        """Test creating default policy."""
        policy = evaluator._get_default_policy(1)
        assert policy.project_id == 1
        assert policy.name == "default"
        assert ChangeType.DELETE_FILE in policy.approval_required_for
        assert ChangeType.AUTH_CHANGE in policy.approval_required_for

    def test_default_policy_thresholds(self, evaluator):
        """Test default policy thresholds."""
        policy = evaluator._get_default_policy(1)
        assert policy.auto_approve_threshold == 0.85
        assert policy.auto_reject_threshold == 0.2


class TestExplanations:
    """Tests for decision explanations."""

    def test_explain_auto_approve(self, evaluator):
        """Test explanation for auto-approve."""
        policy = evaluator._get_default_policy(1)
        explanation = evaluator._explain_decision(
            "auto_approve",
            policy,
            ChangeRiskLevel.LOW,
            0.92,
        )
        assert "auto-approved" in explanation.lower()
        assert "0.92" in explanation

    def test_explain_auto_reject(self, evaluator):
        """Test explanation for auto-reject."""
        policy = evaluator._get_default_policy(1)
        explanation = evaluator._explain_decision(
            "auto_reject",
            policy,
            ChangeRiskLevel.CRITICAL,
            0.10,
        )
        assert "auto-rejected" in explanation.lower()

    def test_explain_require_approval(self, evaluator):
        """Test explanation for requiring approval."""
        policy = evaluator._get_default_policy(1)
        explanation = evaluator._explain_decision(
            "require_approval",
            policy,
            ChangeRiskLevel.HIGH,
            0.65,
        )
        assert "approval required" in explanation.lower()
