"""
Service for managing notifications and alert rules.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import json
import aiohttp

from models.notifications import (
    Notification,
    NotificationCreate,
    NotificationUpdate,
    AlertRule,
    AlertRuleCreate,
    AlertRuleUpdate,
    NotificationPreferences,
    AlertLevel,
    AlertType,
    NotificationStatus,
    NotificationChannel,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications and sending alerts."""

    def __init__(self, db_loader=None):
        """Initialize notification service.

        Args:
            db_loader: Database loader for persistence
        """
        self.db = db_loader
        self.notifications: Dict[int, Notification] = {}
        self.alert_rules: Dict[int, AlertRule] = {}
        self.preferences: Dict[str, NotificationPreferences] = {}
        self._notification_id_counter = 1
        self._rule_id_counter = 1

    async def create_notification(
        self,
        notification: NotificationCreate,
        project_id: Optional[int] = None,
    ) -> Notification:
        """Create a new notification.

        Args:
            notification: Notification to create
            project_id: Project ID for filtering

        Returns:
            Created notification
        """
        now = datetime.now(timezone.utc)
        notif = Notification(
            id=self._notification_id_counter,
            alert_type=notification.alert_type,
            title=notification.title,
            message=notification.message,
            level=notification.level,
            status=NotificationStatus.SENT,
            channels=notification.channels,
            metadata=notification.metadata,
            created_at=now,
            project_id=project_id or notification.project_id,
        )
        self._notification_id_counter += 1
        self.notifications[notif.id] = notif

        # Check if notification should be delivered to webhook/email
        await self._deliver_notification(notif)

        return notif

    async def _deliver_notification(self, notification: Notification) -> None:
        """Deliver notification to configured channels.

        Args:
            notification: Notification to deliver
        """
        prefs = self.preferences.get(
            f"project_{notification.project_id}",
            NotificationPreferences(),
        )

        # Check quiet hours
        if self._is_in_quiet_hours(prefs):
            logger.debug(f"Notification {notification.id} held during quiet hours")
            return

        # Deliver to each channel
        for channel in notification.channels:
            try:
                if channel == NotificationChannel.EMAIL and prefs.enable_email:
                    await self._send_email(notification, prefs)
                elif channel == NotificationChannel.WEBHOOK and prefs.enable_webhook:
                    await self._send_webhook(notification, prefs)
                elif channel == NotificationChannel.SLACK and prefs.enable_slack:
                    await self._send_slack(notification, prefs)
            except Exception as e:
                logger.error(f"Error delivering notification via {channel}: {e}")

    async def _send_email(
        self,
        notification: Notification,
        prefs: NotificationPreferences,
    ) -> None:
        """Send email notification.

        Args:
            notification: Notification to send
            prefs: User preferences
        """
        if not prefs.email_address:
            return

        # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
        logger.info(
            f"Would send email to {prefs.email_address}: {notification.title}"
        )

    async def _send_webhook(
        self,
        notification: Notification,
        prefs: NotificationPreferences,
    ) -> None:
        """Send webhook notification.

        Args:
            notification: Notification to send
            prefs: User preferences
        """
        if not prefs.webhook_url:
            return

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "alert_type": notification.alert_type.value,
                    "title": notification.title,
                    "message": notification.message,
                    "level": notification.level.value,
                    "timestamp": notification.created_at.isoformat(),
                    "metadata": notification.metadata,
                }
                async with session.post(
                    prefs.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status >= 400:
                        logger.warning(
                            f"Webhook delivery failed: {resp.status}"
                        )
        except Exception as e:
            logger.error(f"Webhook delivery error: {e}")

    async def _send_slack(
        self,
        notification: Notification,
        prefs: NotificationPreferences,
    ) -> None:
        """Send Slack notification.

        Args:
            notification: Notification to send
            prefs: User preferences
        """
        if not prefs.slack_webhook:
            return

        try:
            # Determine color based on severity
            color_map = {
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#ff9800",
                AlertLevel.CRITICAL: "#f44336",
            }

            payload = {
                "channel": prefs.slack_channel,
                "attachments": [
                    {
                        "color": color_map.get(notification.level, "#808080"),
                        "title": notification.title,
                        "text": notification.message,
                        "fields": [
                            {
                                "title": "Type",
                                "value": notification.alert_type.value,
                                "short": True,
                            },
                            {
                                "title": "Level",
                                "value": notification.level.value.upper(),
                                "short": True,
                            },
                        ],
                        "ts": int(notification.created_at.timestamp()),
                    }
                ],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    prefs.slack_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status >= 400:
                        logger.warning(
                            f"Slack delivery failed: {resp.status}"
                        )
        except Exception as e:
            logger.error(f"Slack delivery error: {e}")

    def _is_in_quiet_hours(self, prefs: NotificationPreferences) -> bool:
        """Check if current time is in quiet hours.

        Args:
            prefs: User preferences

        Returns:
            True if in quiet hours, False otherwise
        """
        if not prefs.quiet_hours_enabled:
            return False

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end

        # Handle wraparound (e.g., 22:00 to 08:00)
        if start < end:
            return start <= current_time < end
        else:
            return current_time >= start or current_time < end

    async def get_notifications(
        self,
        project_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        status: Optional[NotificationStatus] = None,
        level: Optional[AlertLevel] = None,
    ) -> tuple[List[Notification], int]:
        """Get notifications with filtering.

        Args:
            project_id: Project to filter by
            limit: Maximum number to return
            offset: Number to skip
            status: Filter by status
            level: Filter by level

        Returns:
            Tuple of (notifications, total count)
        """
        results = []
        for notif in self.notifications.values():
            if project_id and notif.project_id != project_id:
                continue
            if status and notif.status != status:
                continue
            if level and notif.level != level:
                continue
            results.append(notif)

        # Sort by created_at descending
        results.sort(key=lambda n: n.created_at or datetime.now(), reverse=True)

        total = len(results)
        return results[offset : offset + limit], total

    async def mark_as_read(self, notification_id: int) -> Optional[Notification]:
        """Mark notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            Updated notification
        """
        if notification_id in self.notifications:
            notif = self.notifications[notification_id]
            notif.status = NotificationStatus.READ
            notif.read_at = datetime.now(timezone.utc)
            return notif
        return None

    async def archive_notification(self, notification_id: int) -> Optional[Notification]:
        """Archive a notification.

        Args:
            notification_id: Notification ID

        Returns:
            Updated notification
        """
        if notification_id in self.notifications:
            notif = self.notifications[notification_id]
            notif.status = NotificationStatus.ARCHIVED
            notif.archived_at = datetime.now(timezone.utc)
            return notif
        return None

    async def create_alert_rule(
        self,
        rule: AlertRuleCreate,
        project_id: Optional[int] = None,
    ) -> AlertRule:
        """Create an alert rule.

        Args:
            rule: Rule to create
            project_id: Project ID

        Returns:
            Created rule
        """
        now = datetime.now(timezone.utc)
        alert_rule = AlertRule(
            id=self._rule_id_counter,
            name=rule.name,
            alert_type=rule.alert_type,
            condition=rule.condition,
            severity=rule.severity,
            enabled=rule.enabled,
            channels=rule.channels,
            project_id=project_id or rule.project_id,
            created_at=now,
            updated_at=now,
        )
        self._rule_id_counter += 1
        self.alert_rules[alert_rule.id] = alert_rule
        return alert_rule

    async def get_alert_rules(
        self,
        project_id: Optional[int] = None,
        enabled_only: bool = False,
    ) -> List[AlertRule]:
        """Get alert rules.

        Args:
            project_id: Project to filter by
            enabled_only: Only return enabled rules

        Returns:
            List of alert rules
        """
        rules = []
        for rule in self.alert_rules.values():
            if project_id and rule.project_id != project_id:
                continue
            if enabled_only and not rule.enabled:
                continue
            rules.append(rule)
        return rules

    async def update_alert_rule(
        self,
        rule_id: int,
        update: AlertRuleUpdate,
    ) -> Optional[AlertRule]:
        """Update an alert rule.

        Args:
            rule_id: Rule ID
            update: Update data

        Returns:
            Updated rule
        """
        if rule_id not in self.alert_rules:
            return None

        rule = self.alert_rules[rule_id]
        if update.name is not None:
            rule.name = update.name
        if update.condition is not None:
            rule.condition = update.condition
        if update.severity is not None:
            rule.severity = update.severity
        if update.enabled is not None:
            rule.enabled = update.enabled
        if update.channels is not None:
            rule.channels = update.channels

        rule.updated_at = datetime.now(timezone.utc)
        return rule

    async def delete_alert_rule(self, rule_id: int) -> bool:
        """Delete an alert rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if deleted
        """
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            return True
        return False

    async def get_preferences(
        self,
        project_id: Optional[int] = None,
    ) -> NotificationPreferences:
        """Get notification preferences.

        Args:
            project_id: Project ID

        Returns:
            Preferences
        """
        key = f"project_{project_id}" if project_id else "default"
        if key not in self.preferences:
            self.preferences[key] = NotificationPreferences(
                project_id=project_id
            )
        return self.preferences[key]

    async def update_preferences(
        self,
        prefs: NotificationPreferences,
        project_id: Optional[int] = None,
    ) -> NotificationPreferences:
        """Update notification preferences.

        Args:
            prefs: Updated preferences
            project_id: Project ID

        Returns:
            Updated preferences
        """
        key = f"project_{project_id}" if project_id else "default"
        prefs.project_id = project_id
        prefs.updated_at = datetime.now(timezone.utc)
        self.preferences[key] = prefs
        return prefs

    async def get_stats(
        self,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get notification statistics.

        Args:
            project_id: Project to filter by

        Returns:
            Statistics dictionary
        """
        notifications, total = await self.get_notifications(project_id=project_id)

        unread = sum(
            1 for n in notifications
            if n.status == NotificationStatus.SENT and n.project_id == project_id
        )
        critical = sum(
            1 for n in notifications
            if n.level == AlertLevel.CRITICAL and n.project_id == project_id
        )

        return {
            "total": total,
            "unread": unread,
            "critical": critical,
            "by_level": {
                "info": sum(
                    1 for n in notifications if n.level == AlertLevel.INFO
                ),
                "warning": sum(
                    1 for n in notifications if n.level == AlertLevel.WARNING
                ),
                "critical": critical,
            },
            "by_type": {
                alert_type.value: sum(
                    1 for n in notifications
                    if n.alert_type == alert_type
                )
                for alert_type in AlertType
            },
        }
