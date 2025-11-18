"""High-level safety manager for agent safety operations."""

from typing import Optional

from ..core.database import Database
from .evaluator import SafetyEvaluator
from .models import (
    ApprovalRequest,
    AuditEntry,
    ChangeType,
    CodeSnapshot,
    SafetyPolicy,
)
from .store import SafetyStore


class SafetyManager:
    """High-level manager for agent safety policies and auditing."""

    def __init__(self, db: Database):
        """Initialize safety manager.

        Args:
            db: Database instance
        """
        self.db = db
        self.store = SafetyStore(db)
        self.evaluator = SafetyEvaluator(db)

    # Policy management

    def create_policy(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        **kwargs,
    ) -> SafetyPolicy:
        """Create a new safety policy.

        Args:
            project_id: Project ID
            name: Policy name
            description: Optional description
            **kwargs: Additional policy fields (approval_required_for, auto_approve_threshold, etc.)

        Returns:
            Created SafetyPolicy
        """
        policy = SafetyPolicy(
            project_id=project_id,
            name=name,
            description=description,
            **kwargs,
        )
        return self.store.create_policy(policy)

    def get_policy(self, project_id: int) -> Optional[SafetyPolicy]:
        """Get the default safety policy for a project.

        Args:
            project_id: Project ID

        Returns:
            SafetyPolicy or None
        """
        return self.store.get_policy_by_project(project_id)

    # Change approval workflow

    def evaluate_change(
        self,
        project_id: int,
        change_type: ChangeType,
        confidence_score: float,
        affected_files: list[str],
        change_description: str,
        agent_id: Optional[str] = None,
    ) -> dict:
        """Evaluate a proposed change and determine approval requirements.

        Args:
            project_id: Project ID
            change_type: Type of change
            confidence_score: Agent's confidence (0.0-1.0)
            affected_files: List of affected files
            change_description: Description of the change
            agent_id: Optional agent ID

        Returns:
            dict with decision, reason, risk_level, etc.
        """
        return self.evaluator.evaluate_change(
            project_id=project_id,
            change_type=change_type,
            confidence_score=confidence_score,
            affected_files=affected_files,
            agent_id=agent_id,
            description=change_description,
        )

    def request_approval(
        self,
        project_id: int,
        change_type: ChangeType,
        confidence_score: float,
        affected_files: list[str],
        change_description: str,
        agent_id: Optional[str] = None,
        affected_lines: Optional[tuple[int, int]] = None,
        pre_snapshot_id: Optional[int] = None,
    ) -> ApprovalRequest:
        """Create an approval request for a proposed change.

        Args:
            project_id: Project ID
            change_type: Type of change
            confidence_score: Agent's confidence (0.0-1.0)
            affected_files: List of affected files
            change_description: Description of the change
            agent_id: Optional agent ID
            affected_lines: Optional line range affected
            pre_snapshot_id: Optional snapshot ID of pre-modification state

        Returns:
            ApprovalRequest
        """
        return self.evaluator.create_approval_request(
            project_id=project_id,
            change_type=change_type,
            confidence_score=confidence_score,
            affected_files=affected_files,
            change_description=change_description,
            agent_id=agent_id,
            affected_lines=affected_lines,
            pre_snapshot_id=pre_snapshot_id,
        )

    def get_pending_approvals(self, project_id: int) -> list[ApprovalRequest]:
        """Get all pending approval requests for a project.

        Args:
            project_id: Project ID

        Returns:
            List of pending ApprovalRequest objects
        """
        return self.store.get_pending_requests(project_id)

    def approve_change(
        self, request_id: int, approved_by: str, reason: Optional[str] = None
    ) -> bool:
        """Approve a pending change request.

        Args:
            request_id: Approval request ID
            approved_by: User/entity approving
            reason: Optional reason

        Returns:
            True if approved
        """
        return self.store.approve_request(request_id, approved_by, reason)

    def reject_change(self, request_id: int, reason: str) -> bool:
        """Reject a pending change request.

        Args:
            request_id: Approval request ID
            reason: Rejection reason

        Returns:
            True if rejected
        """
        return self.store.reject_request(request_id, reason)

    # Risk assessment

    def assess_risk(
        self,
        confidence_score: float,
        change_type: ChangeType,
        affected_file_count: int,
    ) -> dict:
        """Assess the risk level of a proposed change.

        Args:
            confidence_score: Agent's confidence (0.0-1.0)
            change_type: Type of change
            affected_file_count: Number of affected files

        Returns:
            dict with risk assessment
        """
        return self.evaluator.assess_risk(confidence_score, change_type, affected_file_count)

    # Audit trail management

    def record_change(
        self,
        project_id: int,
        approval_request_id: int,
        change_type: ChangeType,
        affected_files: list[str],
        description: str,
        success: bool = True,
        error_message: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        pre_snapshot_id: Optional[int] = None,
        post_snapshot_id: Optional[int] = None,
    ) -> AuditEntry:
        """Record a change in the audit trail.

        Args:
            project_id: Project ID
            approval_request_id: Related approval request ID
            change_type: Type of change
            affected_files: Files affected
            description: Change description
            success: Whether change succeeded
            error_message: Error details if failed
            agent_id: Optional agent ID
            user_id: Optional user ID
            pre_snapshot_id: Optional pre-state snapshot ID
            post_snapshot_id: Optional post-state snapshot ID

        Returns:
            AuditEntry
        """
        return self.evaluator.record_change(
            project_id=project_id,
            approval_request_id=approval_request_id,
            change_type=change_type,
            affected_files=affected_files,
            description=description,
            success=success,
            error_message=error_message,
            agent_id=agent_id,
            user_id=user_id,
            pre_snapshot_id=pre_snapshot_id,
            post_snapshot_id=post_snapshot_id,
        )

    def get_audit_history(
        self, project_id: int, limit: int = 100, offset: int = 0
    ) -> list[AuditEntry]:
        """Get audit history for a project.

        Args:
            project_id: Project ID
            limit: Maximum number of entries
            offset: Offset for pagination

        Returns:
            List of AuditEntry objects
        """
        return self.store.get_audit_history(project_id, limit, offset)

    # Code snapshots (for rollback)

    def create_snapshot(
        self,
        project_id: int,
        file_path: str,
        file_hash: str,
        content_preview: str,
        change_type: ChangeType,
        agent_id: Optional[str] = None,
        full_content: Optional[str] = None,
        keep_indefinitely: bool = False,
        expires_in_hours: int = 24,
    ) -> CodeSnapshot:
        """Create a code snapshot for rollback capability.

        Args:
            project_id: Project ID
            file_path: Path to file
            file_hash: Hash of file content
            content_preview: First 1000 chars
            change_type: Type of change
            agent_id: Optional agent ID
            full_content: Optional full content
            keep_indefinitely: Keep indefinitely
            expires_in_hours: Expiration time in hours

        Returns:
            CodeSnapshot
        """
        return self.evaluator.create_snapshot(
            project_id=project_id,
            file_path=file_path,
            file_hash=file_hash,
            content_preview=content_preview,
            change_type=change_type,
            agent_id=agent_id,
            full_content=full_content,
            keep_indefinitely=keep_indefinitely,
            expires_in_hours=expires_in_hours,
        )

    def get_snapshot(self, snapshot_id: int) -> Optional[CodeSnapshot]:
        """Get a code snapshot.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            CodeSnapshot or None
        """
        return self.store.get_snapshot(snapshot_id)

    # Cleanup

    def cleanup_expired_snapshots(self, project_id: int) -> int:
        """Delete expired snapshots.

        Args:
            project_id: Project ID

        Returns:
            Number of deleted snapshots
        """
        return self.store.cleanup_expired_snapshots(project_id)

    def cleanup_old_approvals(self, project_id: int, days: int = 30) -> int:
        """Delete old approval requests beyond retention period.

        Args:
            project_id: Project ID
            days: Retention period in days

        Returns:
            Number of deleted approvals
        """
        return self.store.cleanup_old_approvals(project_id, days)

    # Summary reporting

    def get_summary(self, project_id: int) -> dict:
        """Get safety summary for a project.

        Args:
            project_id: Project ID

        Returns:
            dict with summary metrics
        """
        policy = self.get_policy(project_id)
        pending = self.get_pending_approvals(project_id)
        recent_audit = self.get_audit_history(project_id, limit=10)

        return {
            "project_id": project_id,
            "policy": {
                "id": policy.id if policy else None,
                "name": policy.name if policy else "default",
                "auto_approve_threshold": policy.auto_approve_threshold if policy else 0.85,
                "auto_reject_threshold": policy.auto_reject_threshold if policy else 0.2,
            },
            "pending_approvals": len(pending),
            "recent_changes": len(recent_audit),
            "approval_requests": [
                {
                    "id": req.id,
                    "change_type": req.change_type,
                    "confidence_score": req.confidence_score,
                    "risk_level": req.risk_level,
                    "requested_at": req.requested_at.isoformat(),
                }
                for req in pending
            ],
        }
