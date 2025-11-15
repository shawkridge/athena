"""
Tests for real-time notification API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from models.notifications import (
    NotificationCreate,
    AlertRuleCreate,
    AlertLevel,
    AlertType,
    NotificationChannel,
)


@pytest.fixture
def notification_client():
    """Fixture for API test client."""
    from athena_dashboard.backend.app import app
    return TestClient(app)


class TestNotificationCreation:
    """Tests for creating notifications."""

    def test_create_notification(self, notification_client):
        """Test creating a notification."""
        payload = {
            "alert_type": "performance",
            "title": "High CPU Usage",
            "message": "CPU usage exceeded 80%",
            "level": "warning",
            "channels": ["in_app"],
            "metadata": {"cpu_usage": 85.5},
        }
        response = notification_client.post("/api/notifications/create", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "High CPU Usage"
        assert data["level"] == "warning"
        assert data["type"] == "performance"

    def test_create_critical_notification(self, notification_client):
        """Test creating a critical notification."""
        payload = {
            "alert_type": "system",
            "title": "System Error",
            "message": "Database connection failed",
            "level": "critical",
            "channels": ["in_app", "email"],
        }
        response = notification_client.post("/api/notifications/create", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["level"] == "critical"

    def test_create_notification_with_project(self, notification_client):
        """Test creating a notification for a specific project."""
        payload = {
            "alert_type": "performance",
            "title": "Memory Alert",
            "message": "Memory usage high",
            "level": "warning",
            "channels": ["in_app"],
        }
        response = notification_client.post(
            "/api/notifications/create?project_id=1",
            json=payload,
        )
        assert response.status_code == 200


class TestNotificationRetrieval:
    """Tests for retrieving notifications."""

    def test_get_notifications(self, notification_client):
        """Test getting notifications."""
        # Create a notification first
        payload = {
            "alert_type": "performance",
            "title": "Test Alert",
            "message": "This is a test",
            "level": "info",
            "channels": ["in_app"],
        }
        notification_client.post("/api/notifications/create", json=payload)

        # Get notifications
        response = notification_client.get("/api/notifications/list")
        assert response.status_code == 200

        data = response.json()
        assert "notifications" in data
        assert "total" in data
        assert "unread_count" in data
        assert "critical_count" in data

    def test_get_notifications_with_limit(self, notification_client):
        """Test getting notifications with limit."""
        response = notification_client.get("/api/notifications/list?limit=5&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data["notifications"]) <= 5

    def test_get_notifications_filter_by_level(self, notification_client):
        """Test filtering notifications by level."""
        response = notification_client.get(
            "/api/notifications/list?level=critical"
        )
        assert response.status_code == 200

        data = response.json()
        for notif in data["notifications"]:
            assert notif["level"] == "critical"

    def test_get_notifications_filter_by_status(self, notification_client):
        """Test filtering notifications by status."""
        response = notification_client.get(
            "/api/notifications/list?status=sent"
        )
        assert response.status_code == 200

        data = response.json()
        for notif in data["notifications"]:
            assert notif["status"] == "sent"


class TestNotificationActions:
    """Tests for notification actions."""

    def test_mark_notification_as_read(self, notification_client):
        """Test marking a notification as read."""
        # Create a notification
        payload = {
            "alert_type": "performance",
            "title": "Test",
            "message": "Test message",
            "level": "info",
            "channels": ["in_app"],
        }
        create_response = notification_client.post(
            "/api/notifications/create",
            json=payload,
        )
        notif_id = create_response.json()["id"]

        # Mark as read
        response = notification_client.put(
            f"/api/notifications/{notif_id}/read"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "read"
        assert "read_at" in data

    def test_archive_notification(self, notification_client):
        """Test archiving a notification."""
        # Create a notification
        payload = {
            "alert_type": "performance",
            "title": "Test",
            "message": "Test message",
            "level": "info",
            "channels": ["in_app"],
        }
        create_response = notification_client.post(
            "/api/notifications/create",
            json=payload,
        )
        notif_id = create_response.json()["id"]

        # Archive
        response = notification_client.put(
            f"/api/notifications/{notif_id}/archive"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "archived"

    def test_mark_nonexistent_notification_fails(self, notification_client):
        """Test marking a nonexistent notification fails."""
        response = notification_client.put(
            "/api/notifications/99999/read"
        )
        assert response.status_code == 404


class TestNotificationStats:
    """Tests for notification statistics."""

    def test_get_notification_stats(self, notification_client):
        """Test getting notification statistics."""
        response = notification_client.get("/api/notifications/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "unread" in data
        assert "critical" in data
        assert "by_level" in data
        assert "by_type" in data

    def test_stats_has_all_levels(self, notification_client):
        """Test stats includes all severity levels."""
        response = notification_client.get("/api/notifications/stats")
        assert response.status_code == 200

        data = response.json()
        assert "info" in data["by_level"]
        assert "warning" in data["by_level"]
        assert "critical" in data["by_level"]

    def test_stats_has_all_types(self, notification_client):
        """Test stats includes all alert types."""
        response = notification_client.get("/api/notifications/stats")
        assert response.status_code == 200

        data = response.json()
        assert "performance" in data["by_type"]
        assert "system" in data["by_type"]
        assert "error" in data["by_type"]


class TestAlertRules:
    """Tests for alert rule management."""

    def test_create_alert_rule(self, notification_client):
        """Test creating an alert rule."""
        payload = {
            "name": "High CPU Alert",
            "alert_type": "cpu",
            "condition": "cpu_usage > 80",
            "severity": "warning",
            "enabled": True,
            "channels": ["in_app"],
        }
        response = notification_client.post(
            "/api/notifications/rules",
            json=payload,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "High CPU Alert"
        assert data["severity"] == "warning"
        assert data["enabled"] is True

    def test_get_alert_rules(self, notification_client):
        """Test getting alert rules."""
        # Create a rule first
        payload = {
            "name": "Test Rule",
            "alert_type": "memory",
            "condition": "memory_usage > 85",
            "severity": "critical",
            "enabled": True,
            "channels": ["in_app"],
        }
        notification_client.post("/api/notifications/rules", json=payload)

        # Get rules
        response = notification_client.get("/api/notifications/rules")
        assert response.status_code == 200

        data = response.json()
        assert "rules" in data
        assert "total" in data
        assert len(data["rules"]) >= 1

    def test_get_enabled_rules_only(self, notification_client):
        """Test getting only enabled rules."""
        response = notification_client.get(
            "/api/notifications/rules?enabled_only=true"
        )
        assert response.status_code == 200

        data = response.json()
        for rule in data["rules"]:
            assert rule["enabled"] is True

    def test_update_alert_rule(self, notification_client):
        """Test updating an alert rule."""
        # Create a rule
        payload = {
            "name": "Original Name",
            "alert_type": "disk",
            "condition": "disk_usage > 90",
            "severity": "warning",
            "enabled": True,
            "channels": ["in_app"],
        }
        create_response = notification_client.post(
            "/api/notifications/rules",
            json=payload,
        )
        rule_id = create_response.json()["id"]

        # Update rule
        update_payload = {
            "name": "Updated Name",
            "enabled": False,
        }
        response = notification_client.put(
            f"/api/notifications/rules/{rule_id}",
            json=update_payload,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["enabled"] is False

    def test_delete_alert_rule(self, notification_client):
        """Test deleting an alert rule."""
        # Create a rule
        payload = {
            "name": "Rule to Delete",
            "alert_type": "database",
            "condition": "query_time > 1000",
            "severity": "warning",
            "enabled": True,
            "channels": ["in_app"],
        }
        create_response = notification_client.post(
            "/api/notifications/rules",
            json=payload,
        )
        rule_id = create_response.json()["id"]

        # Delete rule
        response = notification_client.delete(
            f"/api/notifications/rules/{rule_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestNotificationPreferences:
    """Tests for notification preferences."""

    def test_get_preferences(self, notification_client):
        """Test getting notification preferences."""
        response = notification_client.get("/api/notifications/preferences")
        assert response.status_code == 200

        data = response.json()
        assert "enable_in_app" in data
        assert "enable_email" in data
        assert "enable_webhook" in data
        assert "enable_slack" in data
        assert "alert_types" in data
        assert "min_level" in data

    def test_update_preferences(self, notification_client):
        """Test updating notification preferences."""
        payload = {
            "enable_in_app": True,
            "enable_email": True,
            "enable_webhook": False,
            "enable_slack": False,
            "email_address": "test@example.com",
            "min_level": "warning",
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        }
        response = notification_client.put(
            "/api/notifications/preferences",
            json=payload,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

    def test_update_preferences_with_project(self, notification_client):
        """Test updating preferences for a specific project."""
        payload = {
            "enable_in_app": True,
            "enable_email": False,
            "enable_webhook": True,
            "enable_slack": False,
            "alert_types": ["performance", "system"],
        }
        response = notification_client.put(
            "/api/notifications/preferences?project_id=1",
            json=payload,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestNotificationIntegration:
    """Integration tests for notification system."""

    def test_notification_workflow(self, notification_client):
        """Test complete notification workflow."""
        # Create alert rule
        rule_payload = {
            "name": "Test Rule",
            "alert_type": "performance",
            "condition": "cpu > 80",
            "severity": "warning",
            "enabled": True,
            "channels": ["in_app"],
        }
        rule_response = notification_client.post(
            "/api/notifications/rules",
            json=rule_payload,
        )
        assert rule_response.status_code == 200

        # Create notification
        notif_payload = {
            "alert_type": "performance",
            "title": "High CPU",
            "message": "CPU usage at 85%",
            "level": "warning",
            "channels": ["in_app"],
        }
        notif_response = notification_client.post(
            "/api/notifications/create",
            json=notif_payload,
        )
        assert notif_response.status_code == 200
        notif_id = notif_response.json()["id"]

        # Get notifications
        list_response = notification_client.get("/api/notifications/list")
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["unread_count"] > 0

        # Mark as read
        read_response = notification_client.put(
            f"/api/notifications/{notif_id}/read"
        )
        assert read_response.status_code == 200

    def test_multiple_notification_levels(self, notification_client):
        """Test handling multiple notification severity levels."""
        levels = ["info", "warning", "critical"]
        for level in levels:
            payload = {
                "alert_type": "system",
                "title": f"{level.capitalize()} Alert",
                "message": f"This is a {level} alert",
                "level": level,
                "channels": ["in_app"],
            }
            response = notification_client.post(
                "/api/notifications/create",
                json=payload,
            )
            assert response.status_code == 200

        # Get stats and verify all levels are present
        stats_response = notification_client.get("/api/notifications/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()

        for level in levels:
            assert stats["by_level"][level] >= 1
