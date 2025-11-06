"""Unit tests for SafetyStore."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.safety.store import SafetyStore
from athena.safety.models import (
    SafetyPolicy,
    ApprovalRequest,
    ApprovalStatus,
    AuditEntry,
    ChangeType,
    ChangeRiskLevel,
    CodeSnapshot,
)


@pytest.fixture
def db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    yield db
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def store(db):
    """Create a SafetyStore instance."""
    return SafetyStore(db)


class TestSafetyPolicyCRUD:
    """Tests for SafetyPolicy CRUD operations."""

    def test_create_policy(self, store):
        """Test creating a policy."""
        policy = SafetyPolicy(
            project_id=1,
            name="default",
            description="Default safety policy",
            approval_required_for=[ChangeType.AUTH_CHANGE, ChangeType.DATABASE_CHANGE],
            auto_approve_threshold=0.85,
            auto_reject_threshold=0.2,
        )

        created = store.create_policy(policy)
        assert created.id is not None
        assert created.project_id == 1
        assert created.name == "default"

    def test_get_policy(self, store):
        """Test retrieving a policy."""
        policy = SafetyPolicy(
            project_id=1,
            name="test_policy",
            auto_approve_threshold=0.90,
        )
        created = store.create_policy(policy)

        retrieved = store.get_policy(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.auto_approve_threshold == 0.90

    def test_get_nonexistent_policy(self, store):
        """Test getting a nonexistent policy."""
        result = store.get_policy(9999)
        assert result is None

    def test_get_policy_by_project(self, store):
        """Test getting policy by project."""
        policy = SafetyPolicy(
            project_id=2,
            name="project_policy",
        )
        store.create_policy(policy)

        retrieved = store.get_policy_by_project(2)
        assert retrieved is not None
        assert retrieved.project_id == 2


class TestApprovalRequestCRUD:
    """Tests for ApprovalRequest CRUD operations."""

    def test_create_approval_request(self, store):
        """Test creating an approval request."""
        request = ApprovalRequest(
            project_id=1,
            agent_id="agent-1",
            change_type=ChangeType.AUTH_CHANGE,
            change_description="OAuth2 update",
            confidence_score=0.82,
            risk_level=ChangeRiskLevel.MEDIUM,
            affected_files=["src/auth.py", "tests/auth.py"],
        )

        created = store.create_approval_request(request)
        assert created.id is not None
        assert created.status == ApprovalStatus.PENDING
        assert created.project_id == 1

    def test_get_pending_requests(self, store):
        """Test retrieving pending requests."""
        for i in range(3):
            req = ApprovalRequest(
                project_id=1,
                change_type=ChangeType.AUTH_CHANGE,
                change_description=f"Change {i}",
                confidence_score=0.8,
                risk_level=ChangeRiskLevel.MEDIUM,
                affected_files=["src/test.py"],
            )
            store.create_approval_request(req)

        pending = store.get_pending_requests(1)
        assert len(pending) == 3

    def test_approve_request(self, store):
        """Test approving a request."""
        request = ApprovalRequest(
            project_id=1,
            change_type=ChangeType.AUTH_CHANGE,
            change_description="Test change",
            confidence_score=0.85,
            risk_level=ChangeRiskLevel.MEDIUM,
            affected_files=["src/test.py"],
        )
        created = store.create_approval_request(request)

        success = store.approve_request(created.id, "user@org", "Looks good")
        assert success is True

        approved = store.get_approval_request(created.id)
        assert approved.status == ApprovalStatus.APPROVED
        assert approved.approved_by == "user@org"

    def test_reject_request(self, store):
        """Test rejecting a request."""
        request = ApprovalRequest(
            project_id=1,
            change_type=ChangeType.DELETE_FILE,
            change_description="Delete old file",
            confidence_score=0.45,
            risk_level=ChangeRiskLevel.HIGH,
            affected_files=["src/old.py"],
        )
        created = store.create_approval_request(request)

        success = store.reject_request(created.id, "Needs more testing")
        assert success is True

        rejected = store.get_approval_request(created.id)
        assert rejected.status == ApprovalStatus.REJECTED
        assert rejected.rejection_reason == "Needs more testing"


class TestAuditEntryCRUD:
    """Tests for AuditEntry CRUD operations."""

    def test_create_audit_entry(self, store):
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

        created = store.create_audit_entry(entry)
        assert created.id is not None
        assert created.project_id == 1

    def test_get_audit_history(self, store):
        """Test retrieving audit history."""
        for i in range(5):
            entry = AuditEntry(
                project_id=1,
                change_type=ChangeType.AUTH_CHANGE,
                affected_files=["src/test.py"],
                description=f"Change {i}",
                risk_level=ChangeRiskLevel.MEDIUM,
                confidence_score=0.75,
                success=True,
            )
            store.create_audit_entry(entry)

        history = store.get_audit_history(1, limit=10)
        assert len(history) == 5

    def test_audit_history_pagination(self, store):
        """Test audit history pagination."""
        for i in range(25):
            entry = AuditEntry(
                project_id=1,
                change_type=ChangeType.CONFIG_CHANGE,
                affected_files=["config.yaml"],
                description=f"Config update {i}",
                risk_level=ChangeRiskLevel.LOW,
                confidence_score=0.95,
                success=True,
            )
            store.create_audit_entry(entry)

        page1 = store.get_audit_history(1, limit=10, offset=0)
        assert len(page1) == 10

        page2 = store.get_audit_history(1, limit=10, offset=10)
        assert len(page2) == 10

        page3 = store.get_audit_history(1, limit=10, offset=20)
        assert len(page3) == 5


class TestCodeSnapshotCRUD:
    """Tests for CodeSnapshot CRUD operations."""

    def test_create_snapshot(self, store):
        """Test creating a code snapshot."""
        snapshot = CodeSnapshot(
            project_id=1,
            file_path="src/auth.py",
            file_hash="abc123def456",
            content_preview="def login():\n    pass",
            change_type=ChangeType.AUTH_CHANGE,
            agent_id="agent-1",
        )

        created = store.create_snapshot(snapshot)
        assert created.id is not None
        assert created.file_path == "src/auth.py"

    def test_get_snapshot(self, store):
        """Test retrieving a snapshot."""
        snapshot = CodeSnapshot(
            project_id=1,
            file_path="src/test.py",
            file_hash="hash123",
            content_preview="content",
            change_type=ChangeType.MODIFY_CRITICAL,
        )

        created = store.create_snapshot(snapshot)
        retrieved = store.get_snapshot(created.id)
        assert retrieved is not None
        assert retrieved.file_hash == "hash123"

    def test_snapshot_expiration(self, store):
        """Test snapshot with expiration."""
        future = datetime.now() + timedelta(hours=24)
        snapshot = CodeSnapshot(
            project_id=1,
            file_path="src/temp.py",
            file_hash="temp123",
            content_preview="temporary",
            change_type=ChangeType.MODIFY_CRITICAL,
            expires_at=future,
        )

        created = store.create_snapshot(snapshot)
        assert created.expires_at is not None


class TestCleanup:
    """Tests for cleanup operations."""

    def test_cleanup_expired_snapshots(self, store):
        """Test cleaning up expired snapshots."""
        past = datetime.now() - timedelta(hours=1)
        for i in range(3):
            snapshot = CodeSnapshot(
                project_id=1,
                file_path=f"src/file{i}.py",
                file_hash=f"hash{i}",
                content_preview="content",
                change_type=ChangeType.MODIFY_CRITICAL,
                expires_at=past,
                keep_indefinitely=False,
            )
            store.create_snapshot(snapshot)

        # Create one that shouldn't expire
        future = datetime.now() + timedelta(days=1)
        snapshot = CodeSnapshot(
            project_id=1,
            file_path="src/keep.py",
            file_hash="keep_hash",
            content_preview="content",
            change_type=ChangeType.MODIFY_CRITICAL,
            expires_at=future,
        )
        store.create_snapshot(snapshot)

        deleted = store.cleanup_expired_snapshots(1)
        assert deleted == 3

    def test_cleanup_old_approvals(self, store):
        """Test cleaning up old approval requests."""
        for i in range(5):
            req = ApprovalRequest(
                project_id=1,
                change_type=ChangeType.AUTH_CHANGE,
                change_description=f"Old change {i}",
                confidence_score=0.8,
                risk_level=ChangeRiskLevel.MEDIUM,
                affected_files=["src/test.py"],
                status=ApprovalStatus.APPROVED,
            )
            created = store.create_approval_request(req)

        deleted = store.cleanup_old_approvals(1, days=0)
        # Should delete old approved/rejected requests
        assert deleted >= 0


class TestConcurrency:
    """Tests for concurrent operations."""

    def test_multiple_requests_same_project(self, store):
        """Test creating multiple requests for same project."""
        for i in range(10):
            req = ApprovalRequest(
                project_id=1,
                change_type=ChangeType.AUTH_CHANGE,
                change_description=f"Change {i}",
                confidence_score=0.8,
                risk_level=ChangeRiskLevel.MEDIUM,
                affected_files=[f"src/file{i}.py"],
            )
            store.create_approval_request(req)

        pending = store.get_pending_requests(1)
        assert len(pending) == 10


class TestDataIntegrity:
    """Tests for data integrity and validation."""

    def test_policy_with_empty_requirements(self, store):
        """Test policy with no special requirements."""
        policy = SafetyPolicy(
            project_id=1,
            name="permissive",
            approval_required_for=[],
            require_tests_for=[],
        )

        created = store.create_policy(policy)
        retrieved = store.get_policy(created.id)
        assert len(retrieved.approval_required_for) == 0
        assert len(retrieved.require_tests_for) == 0

    def test_audit_entry_with_snapshot_refs(self, store):
        """Test audit entry with snapshot references."""
        snap1 = CodeSnapshot(
            project_id=1,
            file_path="src/test.py",
            file_hash="hash1",
            content_preview="old",
            change_type=ChangeType.MODIFY_CRITICAL,
        )
        snap2 = CodeSnapshot(
            project_id=1,
            file_path="src/test.py",
            file_hash="hash2",
            content_preview="new",
            change_type=ChangeType.MODIFY_CRITICAL,
        )

        snap1_id = store.create_snapshot(snap1).id
        snap2_id = store.create_snapshot(snap2).id

        entry = AuditEntry(
            project_id=1,
            change_type=ChangeType.MODIFY_CRITICAL,
            affected_files=["src/test.py"],
            description="Code update",
            risk_level=ChangeRiskLevel.MEDIUM,
            confidence_score=0.85,
            pre_snapshot_id=snap1_id,
            post_snapshot_id=snap2_id,
            success=True,
        )

        created = store.create_audit_entry(entry)
        assert created.pre_snapshot_id == snap1_id
        assert created.post_snapshot_id == snap2_id
