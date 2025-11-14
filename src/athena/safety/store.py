"""Safety policy and audit trail storage operations."""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEntry,
    ChangeRecommendation,
    ChangeRiskLevel,
    ChangeType,
    CodeSnapshot,
    SafetyPolicy,
)


class SafetyStore(BaseStore):
    """Manages safety policies, approvals, and audit trails."""

    table_name = "safety_policies"  # Primary table
    model_class = SafetyPolicy

    def __init__(self, db: Database):
        """Initialize safety store.

        Args:
            db: Database instance
        """
        super().__init__(db)
    def _row_to_model(self, row: Dict[str, Any]) -> Optional[SafetyPolicy]:
        """Convert database row to SafetyPolicy model.

        This method is required by BaseStore but SafetyStore manages multiple models.
        Use model-specific conversion methods (_row_to_policy, etc.) instead.

        Args:
            row: Database row as dict

        Returns:
            SafetyPolicy instance (for primary model)
        """
        if not row:
            return None
        # For the primary table (safety_policies), use _row_to_policy
        if "approval_required_for" in row:
            return self._row_to_policy(row)
        return None

    def _ensure_schema(self):
        """Ensure all safety tables exist."""
        cursor = self.db.get_cursor()

        # Safety policies table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_policies (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,

                approval_required_for TEXT NOT NULL,  -- JSON list of ChangeType
                auto_approve_threshold REAL DEFAULT 0.85,
                auto_reject_threshold REAL DEFAULT 0.2,

                require_tests_for TEXT NOT NULL,  -- JSON list of file patterns
                min_test_coverage REAL DEFAULT 0.0,

                audit_enabled INTEGER DEFAULT 1,
                keep_pre_modification_snapshot INTEGER DEFAULT 1,
                require_human_approval INTEGER DEFAULT 0,
                max_approval_time_hours INTEGER DEFAULT 24,

                enable_rollback INTEGER DEFAULT 1,
                keep_rollback_snapshots INTEGER DEFAULT 10,

                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, name)
            )
        """
        )

        # Approval requests table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_requests (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                agent_id TEXT,
                change_type TEXT NOT NULL,
                change_description TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                risk_level TEXT NOT NULL,

                affected_files TEXT NOT NULL,  -- JSON list
                affected_lines TEXT,  -- JSON [start, end]

                pre_snapshot_id INTEGER,
                status TEXT DEFAULT 'pending',
                requested_at INTEGER NOT NULL,
                approved_by TEXT,
                approved_at INTEGER,
                rejection_reason TEXT,

                auto_approved INTEGER DEFAULT 0,
                auto_approved_reason TEXT,

                policy_id INTEGER,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (policy_id) REFERENCES safety_policies(id) ON DELETE SET NULL,
                FOREIGN KEY (pre_snapshot_id) REFERENCES code_snapshots(id) ON DELETE SET NULL
            )
        """
        )

        # Audit entries table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_entries (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,

                agent_id TEXT,
                user_id TEXT,

                change_type TEXT NOT NULL,
                affected_files TEXT NOT NULL,  -- JSON list
                description TEXT NOT NULL,

                approval_request_id INTEGER,
                pre_snapshot_id INTEGER,
                post_snapshot_id INTEGER,

                success INTEGER DEFAULT 1,
                error_message TEXT,

                risk_level TEXT NOT NULL,
                confidence_score REAL NOT NULL,

                reverted INTEGER DEFAULT 0,
                reverted_at INTEGER,
                revert_reason TEXT,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (approval_request_id) REFERENCES approval_requests(id) ON DELETE SET NULL,
                FOREIGN KEY (pre_snapshot_id) REFERENCES code_snapshots(id) ON DELETE SET NULL,
                FOREIGN KEY (post_snapshot_id) REFERENCES code_snapshots(id) ON DELETE SET NULL
            )
        """
        )

        # Code snapshots table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS code_snapshots (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,

                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                content_preview TEXT NOT NULL,
                full_content TEXT,

                change_type TEXT NOT NULL,
                change_id INTEGER,
                agent_id TEXT,

                expires_at INTEGER,
                keep_indefinitely INTEGER DEFAULT 0,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """
        )

        # Change recommendations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS change_recommendations (
                id SERIAL PRIMARY KEY,
                approval_request_id INTEGER NOT NULL,

                recommendation TEXT NOT NULL,  -- "approve" | "reject" | "request_changes" | "escalate"
                reasoning TEXT NOT NULL,
                confidence REAL NOT NULL,

                suggested_tests TEXT NOT NULL,  -- JSON list
                suggested_reviewers TEXT NOT NULL,  -- JSON list
                risk_mitigation_steps TEXT NOT NULL,  -- JSON list

                created_at INTEGER NOT NULL,

                FOREIGN KEY (approval_request_id) REFERENCES approval_requests(id) ON DELETE CASCADE
            )
        """
        )

        # Create indexes for common queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_approval_requests_project ON approval_requests(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_entries_project ON audit_entries(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_entries_timestamp ON audit_entries(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_code_snapshots_project ON code_snapshots(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_code_snapshots_file ON code_snapshots(file_path)"
        )

        # commit handled by cursor context

    # SafetyPolicy operations

    def create_policy(self, policy: SafetyPolicy) -> SafetyPolicy:
        """Create a new safety policy."""
        now = self.now_timestamp()

        self.execute(
            """
            INSERT INTO safety_policies (
                project_id, name, description,
                approval_required_for, auto_approve_threshold, auto_reject_threshold,
                require_tests_for, min_test_coverage,
                audit_enabled, keep_pre_modification_snapshot, require_human_approval,
                max_approval_time_hours, enable_rollback, keep_rollback_snapshots,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                policy.project_id,
                policy.name,
                policy.description,
                self.serialize_json(policy.approval_required_for),
                policy.auto_approve_threshold,
                policy.auto_reject_threshold,
                self.serialize_json(policy.require_tests_for),
                policy.min_test_coverage,
                int(policy.audit_enabled),
                int(policy.keep_pre_modification_snapshot),
                int(policy.require_human_approval),
                policy.max_approval_time_hours,
                int(policy.enable_rollback),
                policy.keep_rollback_snapshots,
                now,
                now,
            ),
        )
        self.commit()
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        policy.id = result[0] if result else None
        return policy

    def get_policy(self, policy_id: int) -> Optional[SafetyPolicy]:
        """Get a safety policy by ID."""
        row = self.execute("SELECT * FROM safety_policies WHERE id = ?", (policy_id,), fetch_one=True)
        if not row:
            return None
        col_names = ["id", "project_id", "name", "description", "approval_required_for", "auto_approve_threshold", "auto_reject_threshold", "require_tests_for", "min_test_coverage", "audit_enabled", "keep_pre_modification_snapshot", "require_human_approval", "max_approval_time_hours", "enable_rollback", "keep_rollback_snapshots", "created_at", "updated_at"]
        return self._row_to_policy(dict(zip(col_names, row)))

    def get_policy_by_project(self, project_id: int) -> Optional[SafetyPolicy]:
        """Get default safety policy for a project."""
        row = self.execute(
            "SELECT * FROM safety_policies WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
            fetch_one=True,
        )
        if not row:
            return None
        col_names = ["id", "project_id", "name", "description", "approval_required_for", "auto_approve_threshold", "auto_reject_threshold", "require_tests_for", "min_test_coverage", "audit_enabled", "keep_pre_modification_snapshot", "require_human_approval", "max_approval_time_hours", "enable_rollback", "keep_rollback_snapshots", "created_at", "updated_at"]
        return self._row_to_policy(dict(zip(col_names, row)))

    def _row_to_policy(self, row: Dict[str, Any]) -> SafetyPolicy:
        """Convert database row to SafetyPolicy."""
        # Ensure JSON fields are lists, not dicts
        approval_required_for = []
        if row.get("approval_required_for"):
            parsed = self.deserialize_json(row.get("approval_required_for"), [])
            approval_required_for = parsed if isinstance(parsed, list) else []

        require_tests_for = []
        if row.get("require_tests_for"):
            parsed = self.deserialize_json(row.get("require_tests_for"), [])
            require_tests_for = parsed if isinstance(parsed, list) else []

        return SafetyPolicy(
            id=row.get("id"),
            project_id=row.get("project_id"),
            name=row.get("name"),
            description=row.get("description"),
            approval_required_for=approval_required_for,
            auto_approve_threshold=row.get("auto_approve_threshold"),
            auto_reject_threshold=row.get("auto_reject_threshold"),
            require_tests_for=require_tests_for,
            min_test_coverage=row.get("min_test_coverage"),
            audit_enabled=bool(row.get("audit_enabled")),
            keep_pre_modification_snapshot=bool(row.get("keep_pre_modification_snapshot")),
            require_human_approval=bool(row.get("require_human_approval")),
            max_approval_time_hours=row.get("max_approval_time_hours"),
            enable_rollback=bool(row.get("enable_rollback")),
            keep_rollback_snapshots=row.get("keep_rollback_snapshots"),
            created_at=self.from_timestamp(row.get("created_at")),
            updated_at=self.from_timestamp(row.get("updated_at")),
        )

    # ApprovalRequest operations

    def create_approval_request(self, request: ApprovalRequest) -> ApprovalRequest:
        """Create a new approval request."""
        now = self.now_timestamp()

        self.execute(
            """
            INSERT INTO approval_requests (
                project_id, agent_id, change_type, change_description,
                confidence_score, risk_level, affected_files, affected_lines,
                pre_snapshot_id, status, requested_at, auto_approved,
                auto_approved_reason, policy_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                request.project_id,
                request.agent_id,
                request.change_type,
                request.change_description,
                request.confidence_score,
                request.risk_level,
                self.serialize_json(request.affected_files),
                self.serialize_json(request.affected_lines) if request.affected_lines else None,
                request.pre_snapshot_id,
                request.status,
                now,
                int(request.auto_approved),
                request.auto_approved_reason,
                request.policy_id,
            ),
        )
        self.commit()
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        request.id = result[0] if result else None
        request.requested_at = self.from_timestamp(now)
        return request

    def get_approval_request(self, request_id: int) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        row = self.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,), fetch_one=True)
        if not row:
            return None
        col_names = ["id", "project_id", "agent_id", "change_type", "change_description", "confidence_score", "risk_level", "affected_files", "affected_lines", "pre_snapshot_id", "status", "requested_at", "approved_by", "approved_at", "rejection_reason", "auto_approved", "auto_approved_reason", "policy_id"]
        return self._row_to_approval_request(dict(zip(col_names, row)))

    def get_pending_requests(self, project_id: int) -> List[ApprovalRequest]:
        """Get all pending approval requests for a project."""
        rows = self.execute(
            """
            SELECT * FROM approval_requests
            WHERE project_id = ? AND status = 'pending'
            ORDER BY requested_at DESC
        """,
            (project_id,),
            fetch_all=True,
        )
        col_names = ["id", "project_id", "agent_id", "change_type", "change_description", "confidence_score", "risk_level", "affected_files", "affected_lines", "pre_snapshot_id", "status", "requested_at", "approved_by", "approved_at", "rejection_reason", "auto_approved", "auto_approved_reason", "policy_id"]
        return [self._row_to_approval_request(dict(zip(col_names, row))) for row in (rows or [])]

    def approve_request(
        self, request_id: int, approved_by: str, reason: Optional[str] = None
    ) -> bool:
        """Approve an approval request."""
        now = self.now_timestamp()

        self.execute(
            """
            UPDATE approval_requests
            SET status = ?, approved_by = ?, approved_at = ?
            WHERE id = ?
        """,
            (ApprovalStatus.APPROVED, approved_by, now, request_id),
        )
        self.commit()
        return True

    def reject_request(self, request_id: int, reason: str) -> bool:
        """Reject an approval request."""
        now = self.now_timestamp()

        self.execute(
            """
            UPDATE approval_requests
            SET status = ?, rejection_reason = ?, approved_at = ?
            WHERE id = ?
        """,
            (ApprovalStatus.REJECTED, reason, now, request_id),
        )
        self.commit()
        return True

    def _row_to_approval_request(self, row: Dict[str, Any]) -> ApprovalRequest:
        """Convert database row to ApprovalRequest."""
        # Ensure JSON fields are lists
        affected_files = []
        if row.get("affected_files"):
            parsed = self.deserialize_json(row.get("affected_files"), [])
            affected_files = parsed if isinstance(parsed, list) else []

        affected_lines = None
        if row.get("affected_lines"):
            parsed = self.deserialize_json(row.get("affected_lines"), [])
            affected_lines = parsed if isinstance(parsed, list) else None

        return ApprovalRequest(
            id=row.get("id"),
            project_id=row.get("project_id"),
            agent_id=row.get("agent_id"),
            change_type=row.get("change_type"),
            change_description=row.get("change_description"),
            confidence_score=row.get("confidence_score"),
            risk_level=row.get("risk_level"),
            affected_files=affected_files,
            affected_lines=affected_lines,
            pre_snapshot_id=row.get("pre_snapshot_id"),
            status=row.get("status"),
            requested_at=self.from_timestamp(row.get("requested_at")),
            approved_by=row.get("approved_by"),
            approved_at=self.from_timestamp(row.get("approved_at")) if row.get("approved_at") else None,
            rejection_reason=row.get("rejection_reason"),
            auto_approved=bool(row.get("auto_approved")),
            auto_approved_reason=row.get("auto_approved_reason"),
            policy_id=row.get("policy_id"),
        )

    # AuditEntry operations

    def create_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        """Create a new audit entry."""
        now = self.now_timestamp()

        self.execute(
            """
            INSERT INTO audit_entries (
                project_id, timestamp, agent_id, user_id, change_type,
                affected_files, description, approval_request_id,
                pre_snapshot_id, post_snapshot_id, success, error_message,
                risk_level, confidence_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                entry.project_id,
                now,
                entry.agent_id,
                entry.user_id,
                entry.change_type,
                self.serialize_json(entry.affected_files),
                entry.description,
                entry.approval_request_id,
                entry.pre_snapshot_id,
                entry.post_snapshot_id,
                int(entry.success),
                entry.error_message,
                entry.risk_level,
                entry.confidence_score,
            ),
        )
        self.commit()
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        entry.id = result[0] if result else None
        entry.timestamp = self.from_timestamp(now)
        return entry

    def get_audit_history(
        self, project_id: int, limit: int = 100, offset: int = 0
    ) -> List[AuditEntry]:
        """Get audit history for a project."""
        rows = self.execute(
            """
            SELECT * FROM audit_entries
            WHERE project_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """,
            (project_id, limit, offset),
            fetch_all=True,
        )
        col_names = ["id", "project_id", "timestamp", "agent_id", "user_id", "change_type", "affected_files", "description", "approval_request_id", "pre_snapshot_id", "post_snapshot_id", "success", "error_message", "risk_level", "confidence_score", "reverted", "reverted_at", "revert_reason"]
        return [self._row_to_audit_entry(dict(zip(col_names, row))) for row in (rows or [])]

    def _row_to_audit_entry(self, row: Dict[str, Any]) -> AuditEntry:
        """Convert database row to AuditEntry."""
        # Ensure JSON fields are lists
        affected_files = []
        if row.get("affected_files"):
            parsed = self.deserialize_json(row.get("affected_files"), [])
            affected_files = parsed if isinstance(parsed, list) else []

        return AuditEntry(
            id=row.get("id"),
            project_id=row.get("project_id"),
            timestamp=self.from_timestamp(row.get("timestamp")),
            agent_id=row.get("agent_id"),
            user_id=row.get("user_id"),
            change_type=row.get("change_type"),
            affected_files=affected_files,
            description=row.get("description"),
            approval_request_id=row.get("approval_request_id"),
            pre_snapshot_id=row.get("pre_snapshot_id"),
            post_snapshot_id=row.get("post_snapshot_id"),
            success=bool(row.get("success")),
            error_message=row.get("error_message"),
            risk_level=row.get("risk_level"),
            confidence_score=row.get("confidence_score"),
            reverted=bool(row.get("reverted")),
            reverted_at=self.from_timestamp(row.get("reverted_at")) if row.get("reverted_at") else None,
            revert_reason=row.get("revert_reason"),
        )

    # CodeSnapshot operations

    def create_snapshot(self, snapshot: CodeSnapshot) -> CodeSnapshot:
        """Create a code snapshot for rollback."""
        now = self.now_timestamp()

        self.execute(
            """
            INSERT INTO code_snapshots (
                project_id, created_at, file_path, file_hash, content_preview,
                full_content, change_type, change_id, agent_id,
                expires_at, keep_indefinitely
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                snapshot.project_id,
                now,
                snapshot.file_path,
                snapshot.file_hash,
                snapshot.content_preview,
                snapshot.full_content,
                snapshot.change_type,
                snapshot.change_id,
                snapshot.agent_id,
                int(snapshot.expires_at.timestamp()) if snapshot.expires_at else None,
                int(snapshot.keep_indefinitely),
            ),
        )
        self.commit()
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        snapshot.id = result[0] if result else None
        snapshot.created_at = self.from_timestamp(now)
        return snapshot

    def get_snapshot(self, snapshot_id: int) -> Optional[CodeSnapshot]:
        """Get a code snapshot."""
        row = self.execute("SELECT * FROM code_snapshots WHERE id = ?", (snapshot_id,), fetch_one=True)
        if not row:
            return None
        col_names = ["id", "project_id", "created_at", "file_path", "file_hash", "content_preview", "full_content", "change_type", "change_id", "agent_id", "expires_at", "keep_indefinitely"]
        return self._row_to_snapshot(dict(zip(col_names, row)))

    def _row_to_snapshot(self, row: Dict[str, Any]) -> CodeSnapshot:
        """Convert database row to CodeSnapshot."""
        return CodeSnapshot(
            id=row.get("id"),
            project_id=row.get("project_id"),
            created_at=self.from_timestamp(row.get("created_at")),
            file_path=row.get("file_path"),
            file_hash=row.get("file_hash"),
            content_preview=row.get("content_preview"),
            full_content=row.get("full_content"),
            change_type=row.get("change_type"),
            change_id=row.get("change_id"),
            agent_id=row.get("agent_id"),
            expires_at=self.from_timestamp(row.get("expires_at")) if row.get("expires_at") else None,
            keep_indefinitely=bool(row.get("keep_indefinitely")),
        )

    # ChangeRecommendation operations

    def create_recommendation(
        self, recommendation: ChangeRecommendation
    ) -> ChangeRecommendation:
        """Create a change recommendation."""
        now = self.now_timestamp()

        self.execute(
            """
            INSERT INTO change_recommendations (
                approval_request_id, recommendation, reasoning, confidence,
                suggested_tests, suggested_reviewers, risk_mitigation_steps,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                recommendation.approval_request_id,
                recommendation.recommendation,
                recommendation.reasoning,
                recommendation.confidence,
                self.serialize_json(recommendation.suggested_tests),
                self.serialize_json(recommendation.suggested_reviewers),
                self.serialize_json(recommendation.risk_mitigation_steps),
                now,
            ),
        )
        self.commit()
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        recommendation.id = result[0] if result else None
        recommendation.created_at = self.from_timestamp(now)
        return recommendation

    def get_recommendation(self, request_id: int) -> Optional[ChangeRecommendation]:
        """Get recommendation for an approval request."""
        row = self.execute(
            "SELECT * FROM change_recommendations WHERE approval_request_id = ? LIMIT 1",
            (request_id,),
            fetch_one=True,
        )
        if not row:
            return None
        col_names = ["id", "approval_request_id", "recommendation", "reasoning", "confidence", "suggested_tests", "suggested_reviewers", "risk_mitigation_steps", "created_at"]
        return self._row_to_recommendation(dict(zip(col_names, row)))

    def _row_to_recommendation(self, row: Dict[str, Any]) -> ChangeRecommendation:
        """Convert database row to ChangeRecommendation."""
        # Ensure JSON fields are lists
        suggested_tests = []
        if row.get("suggested_tests"):
            parsed = self.deserialize_json(row.get("suggested_tests"), [])
            suggested_tests = parsed if isinstance(parsed, list) else []

        suggested_reviewers = []
        if row.get("suggested_reviewers"):
            parsed = self.deserialize_json(row.get("suggested_reviewers"), [])
            suggested_reviewers = parsed if isinstance(parsed, list) else []

        risk_mitigation_steps = []
        if row.get("risk_mitigation_steps"):
            parsed = self.deserialize_json(row.get("risk_mitigation_steps"), [])
            risk_mitigation_steps = parsed if isinstance(parsed, list) else []

        return ChangeRecommendation(
            id=row.get("id"),
            approval_request_id=row.get("approval_request_id"),
            recommendation=row.get("recommendation"),
            reasoning=row.get("reasoning"),
            confidence=row.get("confidence"),
            suggested_tests=suggested_tests,
            suggested_reviewers=suggested_reviewers,
            risk_mitigation_steps=risk_mitigation_steps,
            created_at=self.from_timestamp(row.get("created_at")),
        )

    # Utility operations

    def cleanup_expired_snapshots(self, project_id: int) -> int:
        """Delete expired snapshots (unless marked keep_indefinitely)."""
        now = self.now_timestamp()

        self.execute(
            """
            DELETE FROM code_snapshots
            WHERE project_id = ? AND keep_indefinitely = 0
            AND expires_at IS NOT NULL AND expires_at < ?
        """,
            (project_id, now),
        )
        self.commit()
        return 0  # Placeholder - rowcount not available from execute()

    def cleanup_old_approvals(self, project_id: int, days: int = 30) -> int:
        """Delete old approval requests beyond retention period."""
        cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())

        self.execute(
            """
            DELETE FROM approval_requests
            WHERE project_id = ? AND status IN ('approved', 'rejected', 'cancelled')
            AND requested_at < ?
        """,
            (project_id, cutoff_time),
        )
        self.commit()
        return 0  # Placeholder - rowcount not available from execute()
