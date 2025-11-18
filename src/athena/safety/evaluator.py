"""Safety evaluation and decision making for agent changes."""

from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from .models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEntry,
    ChangeRiskLevel,
    ChangeType,
    CodeSnapshot,
    SafetyPolicy,
)
from .store import SafetyStore


class SafetyEvaluator:
    """Evaluates changes and determines approval requirements."""

    def __init__(self, db: Database):
        """Initialize safety evaluator.

        Args:
            db: Database instance
        """
        self.db = db
        self.store = SafetyStore(db)

    def evaluate_change(
        self,
        project_id: int,
        change_type: ChangeType,
        confidence_score: float,
        affected_files: list[str],
        agent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """Evaluate a proposed change and determine approval requirements.

        Args:
            project_id: Project ID
            change_type: Type of change
            confidence_score: Agent's confidence in the change (0.0-1.0)
            affected_files: List of affected files
            agent_id: Optional agent ID
            description: Optional change description

        Returns:
            dict with decision, recommendation, risk_level, etc.
        """
        # Get policy for project
        policy = self.store.get_policy_by_project(project_id)
        if not policy:
            # Default policy: require approval for critical changes
            policy = self._get_default_policy(project_id)

        # Assess risk level
        risk_level = self._assess_risk_level(confidence_score)

        # Determine if approval is required
        requires_approval = self._requires_approval(
            change_type, policy, risk_level, confidence_score
        )

        # Make decision
        decision = self._make_decision(policy, risk_level, confidence_score, requires_approval)

        return {
            "decision": decision,  # "auto_approve" | "require_approval" | "auto_reject"
            "requires_human_approval": requires_approval,
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "policy_id": policy.id,
            "reason": self._explain_decision(decision, policy, risk_level, confidence_score),
        }

    def create_approval_request(
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
            affected_files: Files affected by change
            change_description: Description of the change
            agent_id: Optional agent ID
            affected_lines: Optional line range (start, end)
            pre_snapshot_id: Optional snapshot of pre-modification state

        Returns:
            ApprovalRequest object
        """
        risk_level = self._assess_risk_level(confidence_score)
        policy = self.store.get_policy_by_project(project_id)
        if not policy:
            policy = self._get_default_policy(project_id)

        requires_approval = self._requires_approval(
            change_type, policy, risk_level, confidence_score
        )

        request = ApprovalRequest(
            project_id=project_id,
            agent_id=agent_id,
            change_type=change_type,
            change_description=change_description,
            confidence_score=confidence_score,
            risk_level=risk_level,
            affected_files=affected_files,
            affected_lines=affected_lines,
            pre_snapshot_id=pre_snapshot_id,
            policy_id=policy.id,
        )

        # Auto-approve if conditions are met
        if not requires_approval and confidence_score >= policy.auto_approve_threshold:
            request.status = ApprovalStatus.APPROVED
            request.auto_approved = True
            request.auto_approved_reason = f"Auto-approved: confidence {confidence_score:.2f} >= threshold {policy.auto_approve_threshold}"
            request.approved_by = "system:auto"
            request.approved_at = datetime.now()

        # Auto-reject if confidence too low
        elif confidence_score < policy.auto_reject_threshold:
            request.status = ApprovalStatus.REJECTED
            request.rejection_reason = f"Auto-rejected: confidence {confidence_score:.2f} < threshold {policy.auto_reject_threshold}"

        return self.store.create_approval_request(request)

    def assess_risk(
        self, confidence_score: float, change_type: ChangeType, affected_file_count: int
    ) -> dict:
        """Assess risk level of a proposed change.

        Args:
            confidence_score: Agent's confidence (0.0-1.0)
            change_type: Type of change
            affected_file_count: Number of files affected

        Returns:
            dict with risk assessment details
        """
        risk_level = self._assess_risk_level(confidence_score)

        # Factor in change type severity
        if change_type in [
            ChangeType.DELETE_FILE,
            ChangeType.DATABASE_CHANGE,
            ChangeType.AUTH_CHANGE,
        ]:
            severity_multiplier = 1.5
        elif change_type in [
            ChangeType.INFRASTRUCTURE_CHANGE,
            ChangeType.SECURITY_CHANGE,
        ]:
            severity_multiplier = 1.3
        else:
            severity_multiplier = 1.0

        # Factor in scope
        if affected_file_count > 10:
            scope_multiplier = 1.2
        elif affected_file_count > 5:
            scope_multiplier = 1.1
        else:
            scope_multiplier = 1.0

        adjusted_risk_score = confidence_score * severity_multiplier * scope_multiplier
        adjusted_risk_level = self._assess_risk_level(min(adjusted_risk_score, 1.0))

        return {
            "base_risk_level": risk_level,
            "adjusted_risk_level": adjusted_risk_level,
            "confidence_score": confidence_score,
            "severity_multiplier": severity_multiplier,
            "scope_multiplier": scope_multiplier,
            "severity_factors": (
                [
                    "delete_file",
                    "database_changes",
                    "auth_changes",
                ]
                if change_type
                in [
                    ChangeType.DELETE_FILE,
                    ChangeType.DATABASE_CHANGE,
                    ChangeType.AUTH_CHANGE,
                ]
                else []
            ),
            "scope_factors": ["many_files"] if affected_file_count > 10 else [],
        }

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
            error_message: If failed, error details
            agent_id: Optional agent ID
            user_id: Optional user ID
            pre_snapshot_id: Optional pre-state snapshot
            post_snapshot_id: Optional post-state snapshot

        Returns:
            AuditEntry object
        """
        # Get approval request to get risk info
        approval_req = self.store.get_approval_request(approval_request_id)
        if not approval_req:
            risk_level = ChangeRiskLevel.MEDIUM
            confidence_score = 0.5
        else:
            risk_level = approval_req.risk_level
            confidence_score = approval_req.confidence_score

        entry = AuditEntry(
            project_id=project_id,
            agent_id=agent_id,
            user_id=user_id,
            change_type=change_type,
            affected_files=affected_files,
            description=description,
            approval_request_id=approval_request_id,
            pre_snapshot_id=pre_snapshot_id,
            post_snapshot_id=post_snapshot_id,
            success=success,
            error_message=error_message,
            risk_level=risk_level,
            confidence_score=confidence_score,
        )

        return self.store.create_audit_entry(entry)

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
        """Create a code snapshot for potential rollback.

        Args:
            project_id: Project ID
            file_path: Path to file
            file_hash: Hash of file content
            content_preview: First 1000 chars of content
            change_type: Type of change being made
            agent_id: Optional agent ID
            full_content: Optional full content
            keep_indefinitely: Keep snapshot indefinitely
            expires_in_hours: Hours until snapshot expires

        Returns:
            CodeSnapshot object
        """
        snapshot = CodeSnapshot(
            project_id=project_id,
            file_path=file_path,
            file_hash=file_hash,
            content_preview=content_preview,
            full_content=full_content,
            change_type=change_type,
            agent_id=agent_id,
            keep_indefinitely=keep_indefinitely,
            expires_at=(
                datetime.now() + timedelta(hours=expires_in_hours)
                if not keep_indefinitely
                else None
            ),
        )

        return self.store.create_snapshot(snapshot)

    # Private helper methods

    def _assess_risk_level(self, confidence_score: float) -> ChangeRiskLevel:
        """Assess risk level based on confidence score.

        Args:
            confidence_score: Confidence score (0.0-1.0)

        Returns:
            ChangeRiskLevel enum
        """
        # Lower confidence = higher risk
        inverted_confidence = 1.0 - confidence_score

        if inverted_confidence >= 0.8:
            return ChangeRiskLevel.CRITICAL
        elif inverted_confidence >= 0.6:
            return ChangeRiskLevel.HIGH
        elif inverted_confidence >= 0.4:
            return ChangeRiskLevel.MEDIUM
        else:
            return ChangeRiskLevel.LOW

    def _requires_approval(
        self,
        change_type: ChangeType,
        policy: SafetyPolicy,
        risk_level: ChangeRiskLevel,
        confidence_score: float,
    ) -> bool:
        """Determine if change requires approval.

        Args:
            change_type: Type of change
            policy: Safety policy
            risk_level: Assessed risk level
            confidence_score: Agent's confidence

        Returns:
            True if approval required
        """
        # Always require approval for critical changes
        if risk_level == ChangeRiskLevel.CRITICAL:
            return True

        # Check if change type requires approval
        if change_type in policy.approval_required_for:
            return True

        # Check if policy requires human approval
        if policy.require_human_approval:
            return True

        # Check if confidence below auto-approve threshold
        if confidence_score < policy.auto_approve_threshold:
            return True

        return False

    def _make_decision(
        self,
        policy: SafetyPolicy,
        risk_level: ChangeRiskLevel,
        confidence_score: float,
        requires_approval: bool,
    ) -> str:
        """Make approval decision.

        Args:
            policy: Safety policy
            risk_level: Risk level
            confidence_score: Confidence score
            requires_approval: Whether approval is required

        Returns:
            "auto_approve" | "require_approval" | "auto_reject"
        """
        # Auto-reject if confidence too low
        if confidence_score < policy.auto_reject_threshold:
            return "auto_reject"

        # Auto-approve if meets criteria
        if (
            not requires_approval
            and confidence_score >= policy.auto_approve_threshold
            and risk_level != ChangeRiskLevel.CRITICAL
        ):
            return "auto_approve"

        # Otherwise require approval
        return "require_approval"

    def _explain_decision(
        self,
        decision: str,
        policy: SafetyPolicy,
        risk_level: ChangeRiskLevel,
        confidence_score: float,
    ) -> str:
        """Explain the decision rationale.

        Args:
            decision: Decision made
            policy: Safety policy
            risk_level: Risk level
            confidence_score: Confidence score

        Returns:
            Explanation string
        """
        if decision == "auto_approve":
            return (
                f"Auto-approved: confidence {confidence_score:.2f} meets threshold "
                f"{policy.auto_approve_threshold} and risk level is {risk_level}"
            )
        elif decision == "auto_reject":
            return (
                f"Auto-rejected: confidence {confidence_score:.2f} below minimum threshold "
                f"{policy.auto_reject_threshold}"
            )
        else:
            reasons = []
            if risk_level == ChangeRiskLevel.CRITICAL:
                reasons.append("critical risk level")
            if confidence_score < policy.auto_approve_threshold:
                reasons.append(
                    f"confidence {confidence_score:.2f} below threshold {policy.auto_approve_threshold}"
                )
            return f"Human approval required: {', '.join(reasons)}"

    def _get_default_policy(self, project_id: int) -> SafetyPolicy:
        """Get or create default safety policy for a project.

        Args:
            project_id: Project ID

        Returns:
            Default SafetyPolicy
        """
        policy = SafetyPolicy(
            project_id=project_id,
            name="default",
            description="Default safety policy",
            approval_required_for=[
                ChangeType.DELETE_FILE,
                ChangeType.AUTH_CHANGE,
                ChangeType.DATABASE_CHANGE,
            ],
            auto_approve_threshold=0.85,
            auto_reject_threshold=0.2,
            require_tests_for=[
                "**/*.py",
                "**/*.js",
                "**/*.ts",
            ],
            min_test_coverage=0.7,
            audit_enabled=True,
            keep_pre_modification_snapshot=True,
            enable_rollback=True,
        )
        return self.store.create_policy(policy)
