"""CLI commands for safety policy and audit management."""

import json
from datetime import datetime
from typing import Optional

from ..core.database import Database
from .manager import SafetyManager
from .models import ChangeType


class SafetyCLI:
    """Command-line interface for safety management."""

    def __init__(self, db: Database):
        """Initialize CLI.

        Args:
            db: Database instance
        """
        self.db = db
        self.manager = SafetyManager(db)

    # Policy Management Commands

    def create_policy(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Create a new safety policy.

        Args:
            project_id: Project ID
            name: Policy name
            description: Optional description
            **kwargs: Policy configuration

        Returns:
            Output string
        """
        try:
            policy = self.manager.create_policy(
                project_id=project_id,
                name=name,
                description=description,
                **kwargs,
            )
            return f"""
✓ Safety policy created
  ID: {policy.id}
  Project: {project_id}
  Name: {name}
  Auto-approve threshold: {policy.auto_approve_threshold}
  Auto-reject threshold: {policy.auto_reject_threshold}
  Audit enabled: {policy.audit_enabled}
"""
        except Exception as e:
            return f"✗ Error creating policy: {str(e)}"

    def show_policy(self, project_id: int) -> str:
        """Display safety policy for a project.

        Args:
            project_id: Project ID

        Returns:
            Formatted output string
        """
        try:
            policy = self.manager.get_policy(project_id)
            if not policy:
                return f"No policy found for project {project_id}"

            approval_types = ", ".join(policy.approval_required_for) if policy.approval_required_for else "none"

            return f"""
╔══════════════════════════════════════════════════════════════╗
║                    SAFETY POLICY SUMMARY                     ║
╚══════════════════════════════════════════════════════════════╝

Policy Name:                {policy.name}
Description:               {policy.description or 'N/A'}
Project ID:                {project_id}

APPROVAL THRESHOLDS
  Auto-approve if:         confidence >= {policy.auto_approve_threshold * 100:.0f}%
  Auto-reject if:          confidence < {policy.auto_reject_threshold * 100:.0f}%
  Require approval for:     {approval_types}

TESTING REQUIREMENTS
  Minimum coverage:        {policy.min_test_coverage * 100:.1f}%
  Test patterns:           {', '.join(policy.require_tests_for) if policy.require_tests_for else 'none'}

AUDIT & ROLLBACK
  Audit enabled:           {policy.audit_enabled}
  Keep pre-mod snapshots:  {policy.keep_pre_modification_snapshot}
  Enable rollback:         {policy.enable_rollback}
  Snapshots retained:      {policy.keep_rollback_snapshots}

APPROVAL WORKFLOW
  Require human approval:  {policy.require_human_approval}
  Approval timeout:        {policy.max_approval_time_hours} hours

Created: {policy.created_at.isoformat()}
Updated: {policy.updated_at.isoformat()}
"""
        except Exception as e:
            return f"✗ Error retrieving policy: {str(e)}"

    # Approval Management Commands

    def list_pending(self, project_id: int) -> str:
        """List pending approval requests.

        Args:
            project_id: Project ID

        Returns:
            Formatted output string
        """
        try:
            pending = self.manager.get_pending_approvals(project_id)
            if not pending:
                return f"✓ No pending approvals for project {project_id}"

            output = f"\n{'PENDING APPROVAL REQUESTS':^70}\n"
            output += "=" * 70 + "\n"

            for req in pending:
                files_str = ", ".join(req.affected_files[:2])
                if len(req.affected_files) > 2:
                    files_str += f", +{len(req.affected_files) - 2} more"

                status_icon = "⏳" if req.status == "pending" else "✓"
                risk_colors = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }
                risk_icon = risk_colors.get(req.risk_level, "?")

                output += f"""
{status_icon} Request #{req.id}
  Change:       {req.change_type}
  Risk:         {risk_icon} {req.risk_level.upper()}
  Confidence:   {req.confidence_score * 100:.1f}%
  Files:        {files_str}
  Requested:    {req.requested_at.strftime('%Y-%m-%d %H:%M:%S')}
  Expires:      {(req.requested_at.timestamp() + 86400).__str__() if req.requested_at else 'N/A'}
  Description:  {req.change_description[:60]}...
"""

            return output
        except Exception as e:
            return f"✗ Error listing approvals: {str(e)}"

    def approve(self, request_id: int, approved_by: str, reason: Optional[str] = None) -> str:
        """Approve a pending request.

        Args:
            request_id: Approval request ID
            approved_by: User approving
            reason: Optional reason

        Returns:
            Output string
        """
        try:
            success = self.manager.approve_change(request_id, approved_by, reason)
            if success:
                return f"✓ Approval #{request_id} approved by {approved_by}"
            else:
                return f"✗ Could not approve request #{request_id}"
        except Exception as e:
            return f"✗ Error approving request: {str(e)}"

    def reject(self, request_id: int, reason: str) -> str:
        """Reject a pending request.

        Args:
            request_id: Approval request ID
            reason: Rejection reason

        Returns:
            Output string
        """
        try:
            success = self.manager.reject_change(request_id, reason)
            if success:
                return f"✓ Approval #{request_id} rejected: {reason}"
            else:
                return f"✗ Could not reject request #{request_id}"
        except Exception as e:
            return f"✗ Error rejecting request: {str(e)}"

    # Risk Assessment Commands

    def assess_risk(
        self,
        confidence_score: float,
        change_type: str,
        affected_file_count: int,
    ) -> str:
        """Assess risk of a proposed change.

        Args:
            confidence_score: Confidence (0.0-1.0)
            change_type: Type of change
            affected_file_count: Number of affected files

        Returns:
            Formatted output string
        """
        try:
            ct = ChangeType(change_type)
            risk = self.manager.assess_risk(confidence_score, ct, affected_file_count)

            risk_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }

            return f"""
╔══════════════════════════════════════════════════════════════╗
║                     RISK ASSESSMENT                          ║
╚══════════════════════════════════════════════════════════════╝

INPUTS
  Confidence:              {confidence_score * 100:.1f}%
  Change Type:             {change_type}
  Affected Files:          {affected_file_count}

ASSESSMENT
  Base Risk:               {risk_icon.get(risk['base_risk_level'], '?')} {risk['base_risk_level'].upper()}
  Adjusted Risk:           {risk_icon.get(risk['adjusted_risk_level'], '?')} {risk['adjusted_risk_level'].upper()}

FACTORS
  Severity Multiplier:     {risk['severity_multiplier']}x
  Scope Multiplier:        {risk['scope_multiplier']}x
  Severity Factors:        {', '.join(risk['severity_factors']) if risk['severity_factors'] else 'none'}
  Scope Factors:           {', '.join(risk['scope_factors']) if risk['scope_factors'] else 'none'}

RECOMMENDATION
  Approval Required:       {'YES' if risk['adjusted_risk_level'] in ['high', 'critical'] else 'NO'}
"""
        except Exception as e:
            return f"✗ Error assessing risk: {str(e)}"

    # Audit History Commands

    def audit_history(
        self, project_id: int, limit: int = 20, offset: int = 0
    ) -> str:
        """Show audit history for a project.

        Args:
            project_id: Project ID
            limit: Number of entries to show
            offset: Pagination offset

        Returns:
            Formatted output string
        """
        try:
            history = self.manager.get_audit_history(project_id, limit, offset)
            if not history:
                return f"✓ No audit history for project {project_id}"

            output = f"\n{'AUDIT TRAIL':^70}\n"
            output += "=" * 70 + "\n"

            for entry in history:
                status_icon = "✓" if entry.success else "✗"
                risk_colors = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }
                risk_icon = risk_colors.get(entry.risk_level, "?")

                output += f"""
{status_icon} Entry #{entry.id}
  Timestamp:    {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
  Type:         {entry.change_type}
  Risk:         {risk_icon} {entry.risk_level.upper()}
  Confidence:   {entry.confidence_score * 100:.1f}%
  Agent:        {entry.agent_id or 'system'}
  Description:  {entry.description[:60]}...
  Status:       {'SUCCESS' if entry.success else f'FAILED: {entry.error_message}'}
"""

            return output
        except Exception as e:
            return f"✗ Error retrieving audit history: {str(e)}"

    # Summary Commands

    def status(self, project_id: int) -> str:
        """Show overall safety status for a project.

        Args:
            project_id: Project ID

        Returns:
            Formatted output string
        """
        try:
            summary = self.manager.get_summary(project_id)

            output = f"""
╔══════════════════════════════════════════════════════════════╗
║                   SAFETY STATUS DASHBOARD                    ║
╚══════════════════════════════════════════════════════════════╝

PROJECT {project_id}

POLICY
  Name:                    {summary['policy']['name']}
  Auto-approve threshold:  {summary['policy']['auto_approve_threshold'] * 100:.0f}%
  Auto-reject threshold:   {summary['policy']['auto_reject_threshold'] * 100:.0f}%

PENDING APPROVALS
  Count:                   {summary['pending_approvals']}
"""

            if summary['pending_approvals'] > 0:
                output += "\n  Recent requests:\n"
                for req in summary['approval_requests'][:5]:
                    output += f"    • {req['change_type']}: {req['risk_level'].upper()} risk, "
                    output += f"{req['confidence_score'] * 100:.0f}% confidence\n"

            output += f"""
RECENT CHANGES
  Total recorded:          {summary['recent_changes']}

STATISTICS
  Total entries shown:     {len(summary['approval_requests'])}
"""

            return output
        except Exception as e:
            return f"✗ Error getting status: {str(e)}"

    # Evaluation Commands

    def evaluate(
        self,
        project_id: int,
        change_type: str,
        confidence_score: float,
        affected_files_str: str,
        description: str,
        agent_id: Optional[str] = None,
    ) -> str:
        """Evaluate a proposed change.

        Args:
            project_id: Project ID
            change_type: Type of change
            confidence_score: Confidence (0.0-1.0)
            affected_files_str: Comma-separated file list
            description: Change description
            agent_id: Optional agent ID

        Returns:
            Formatted output string
        """
        try:
            affected_files = [f.strip() for f in affected_files_str.split(",")]
            ct = ChangeType(change_type)

            decision = self.manager.evaluate_change(
                project_id=project_id,
                change_type=ct,
                confidence_score=confidence_score,
                affected_files=affected_files,
                change_description=description,
                agent_id=agent_id,
            )

            decision_icons = {
                "auto_approve": "✅",
                "auto_reject": "❌",
                "require_approval": "⏳",
            }
            decision_icon = decision_icons.get(decision["decision"], "?")

            return f"""
╔══════════════════════════════════════════════════════════════╗
║                  CHANGE EVALUATION RESULT                    ║
╚══════════════════════════════════════════════════════════════╝

PROPOSED CHANGE
  Type:                    {change_type}
  Description:             {description}
  Confidence:              {confidence_score * 100:.1f}%
  Affected Files:          {len(affected_files)} ({', '.join(affected_files[:2])}...)
  Agent:                   {agent_id or 'N/A'}

DECISION
  {decision_icon} {decision['decision'].upper()}

RISK ASSESSMENT
  Risk Level:              {decision['risk_level']}
  Policy Applied:          {decision['policy_id']}
  Reason:                  {decision['reason']}

RECOMMENDATION
  {decision['reason']}
"""
        except Exception as e:
            return f"✗ Error evaluating change: {str(e)}"

    # Snapshot Management Commands

    def cleanup_snapshots(self, project_id: int) -> str:
        """Clean up expired snapshots.

        Args:
            project_id: Project ID

        Returns:
            Output string
        """
        try:
            deleted = self.manager.cleanup_expired_snapshots(project_id)
            return f"✓ Cleaned up {deleted} expired snapshots for project {project_id}"
        except Exception as e:
            return f"✗ Error cleaning up snapshots: {str(e)}"

    def cleanup_approvals(
        self, project_id: int, days: int = 30
    ) -> str:
        """Clean up old approval requests.

        Args:
            project_id: Project ID
            days: Retention period

        Returns:
            Output string
        """
        try:
            deleted = self.manager.cleanup_old_approvals(project_id, days)
            return f"✓ Deleted {deleted} approval requests older than {days} days"
        except Exception as e:
            return f"✗ Error cleaning up approvals: {str(e)}"

    # Help and Documentation

    def help(self) -> str:
        """Show help message.

        Returns:
            Help text
        """
        return """
╔══════════════════════════════════════════════════════════════╗
║                  SAFETY MANAGEMENT CLI HELP                  ║
╚══════════════════════════════════════════════════════════════╝

POLICY MANAGEMENT
  policy show <project_id>
    Display safety policy for a project

  policy create <project_id> <name> [--description TEXT]
    Create a new safety policy

APPROVAL MANAGEMENT
  approval list <project_id>
    List pending approval requests

  approval approve <request_id> <approved_by> [--reason TEXT]
    Approve a pending request

  approval reject <request_id> <reason>
    Reject a pending request

CHANGE EVALUATION
  evaluate <project_id> <change_type> <confidence> <files> <description>
    Evaluate a proposed change

  assess-risk <confidence> <change_type> <file_count>
    Assess risk of a change

AUDIT & HISTORY
  audit <project_id> [--limit 20] [--offset 0]
    Show audit history

  status <project_id>
    Show safety status dashboard

MAINTENANCE
  cleanup-snapshots <project_id>
    Delete expired code snapshots

  cleanup-approvals <project_id> [--days 30]
    Delete old approval requests

GENERAL
  help
    Show this message

CHANGE TYPES
  AUTH_CHANGE, DATABASE_CHANGE, DELETE_FILE, DEPLOY,
  CONFIG_CHANGE, SECURITY_CHANGE, INFRASTRUCTURE_CHANGE,
  DATA_LOSS_RISK, EXTERNAL_API_CHANGE, MODIFY_CRITICAL

EXAMPLES
  safety policy show 1
  safety approval list 1
  safety evaluate 1 AUTH_CHANGE 0.92 src/auth.py,tests/auth.py "Implement OAuth2"
  safety assess-risk 0.75 AUTH_CHANGE 2
  safety approval approve 5 user@org.com --reason "Code review complete"
"""
