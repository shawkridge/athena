"""
WebSocket and REST routes for real-time notifications.
"""

import logging
import json
from typing import Set, Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from datetime import datetime, timezone

from models.notifications import (
    NotificationCreate,
    NotificationUpdate,
    AlertRuleCreate,
    AlertRuleUpdate,
    NotificationPreferences,
    NotificationStatus,
    AlertLevel,
    WebSocketNotification,
)
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# REST API Router
notification_router = APIRouter(prefix="/notifications", tags=["notifications"])

# Global service instance
notification_service: Optional[NotificationService] = None


def set_notification_service(service: NotificationService) -> None:
    """Set the notification service instance."""
    global notification_service
    notification_service = service


# ============================================================================
# WebSocket Management
# ============================================================================

class NotificationConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        project_id: Optional[int] = None,
    ) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            project_id: Optional project ID for filtering
        """
        await websocket.accept()

        if project_id is None:
            project_id = 0  # Global notifications

        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()

        self.active_connections[project_id].add(websocket)
        total = len(self.active_connections[project_id])
        logger.info(
            f"Client connected for notifications "
            f"(project: {project_id}, total: {total})"
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        project_id: Optional[int] = None,
    ) -> None:
        """Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection
            project_id: Optional project ID
        """
        if project_id is None:
            project_id = 0

        removed = False
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].discard(websocket)
                removed = True

            remaining = len(self.active_connections[project_id])
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        else:
            remaining = 0

        if removed:
            logger.info(f"Client disconnected from notifications (project: {project_id}, remaining: {remaining})")
        else:
            logger.debug(f"Disconnect called for unknown connection (project: {project_id})")

    async def broadcast(
        self,
        message: WebSocketNotification,
        project_id: Optional[int] = None,
    ) -> None:
        """Broadcast a notification to all connected clients.

        Args:
            message: Notification message
            project_id: Optional project ID for filtering
        """
        # Send to global listeners
        if 0 in self.active_connections:
            await self._send_to_connections(
                list(self.active_connections[0]),
                message,
            )

        # Send to project-specific listeners
        if project_id and project_id in self.active_connections:
            await self._send_to_connections(
                list(self.active_connections[project_id]),
                message,
            )

    async def _send_to_connections(
        self,
        connections: list[WebSocket],
        message: WebSocketNotification,
    ) -> None:
        """Send message to a list of connections.

        Args:
            connections: List of WebSocket connections
            message: Message to send
        """
        disconnected = []
        message_data = json.dumps(message.dict_for_json())

        for websocket in connections:
            try:
                await websocket.send_text(message_data)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            for ws_set in self.active_connections.values():
                ws_set.discard(websocket)


manager = NotificationConnectionManager()


# ============================================================================
# WebSocket Endpoints
# ============================================================================

# DISABLED: WebSocket connection leak - connections not properly cleaned up
# TODO: Fix disconnect() handler to properly remove stale connections
# @notification_router.websocket("/ws/alerts/{project_id}")
async def _websocket_notifications_endpoint_disabled(
    websocket: WebSocket,
    project_id: int,
) -> None:
    """WebSocket endpoint for real-time notifications.

    Args:
        websocket: WebSocket connection
        project_id: Project ID for filtering notifications
    """
    try:
        await manager.connect(websocket, project_id)
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection: {e}")
        try:
            await websocket.close(code=1011, reason=f"Connection failed: {str(e)}")
        except:
            pass
        return

    try:
        while True:
            try:
                # Receive client messages (for control commands)
                data = await websocket.receive_text()

                if data == "ping":
                    # Respond to keep-alive ping
                    await websocket.send_text('{"type":"pong"}')
                elif data == "mark_all_read":
                    # Mark all notifications as read
                    if notification_service:
                        try:
                            notifications, _ = await notification_service.get_notifications(
                                project_id=project_id,
                                status=NotificationStatus.SENT,
                                limit=1000,
                            )
                            for notif in notifications:
                                await notification_service.mark_as_read(notif.id)
                        except Exception as e:
                            logger.error(f"Error processing mark_all_read: {e}")
                            await websocket.send_text(f'{{"type":"error","message":"{str(e)}"}}')
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket message error: {e}", exc_info=True)
                try:
                    await websocket.send_text(f'{{"type":"error","message":"{str(e)}"}}')
                except:
                    break

    except WebSocketDisconnect:
        logger.debug(f"Client disconnected from alerts (project: {project_id})")
        await manager.disconnect(websocket, project_id)
    except Exception as e:
        logger.error(f"WebSocket error for project {project_id}: {e}", exc_info=True)
        await manager.disconnect(websocket, project_id)


# DISABLED: WebSocket connection leak - connections not properly cleaned up
# @notification_router.websocket("/ws/alerts")
async def _websocket_global_notifications_endpoint_disabled(websocket: WebSocket) -> None:
    """WebSocket endpoint for global real-time notifications.

    Args:
        websocket: WebSocket connection
    """
    try:
        await manager.connect(websocket, None)
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection (global): {e}")
        try:
            await websocket.close(code=1011, reason=f"Connection failed: {str(e)}")
        except:
            pass
        return

    try:
        while True:
            try:
                data = await websocket.receive_text()

                if data == "ping":
                    await websocket.send_text('{"type":"pong"}')
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket message error (global): {e}", exc_info=True)
                try:
                    await websocket.send_text(f'{{"type":"error","message":"{str(e)}"}}')
                except:
                    break

    except WebSocketDisconnect:
        logger.debug("Client disconnected from global alerts")
        await manager.disconnect(websocket, None)
    except Exception as e:
        logger.error(f"WebSocket error (global): {e}", exc_info=True)
        await manager.disconnect(websocket, None)


# ============================================================================
# REST API Endpoints
# ============================================================================

@notification_router.post("/create")
async def create_notification(
    notification: NotificationCreate,
    project_id: Optional[int] = Query(None),
) -> Dict[str, Any]:
    """Create and send a notification.

    Args:
        notification: Notification to create
        project_id: Optional project ID

    Returns:
        Created notification
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    notif = await notification_service.create_notification(notification, project_id)

    # Broadcast to connected clients
    ws_notif = WebSocketNotification(notification=notif)
    await manager.broadcast(ws_notif, project_id)

    return {
        "id": notif.id,
        "type": notif.alert_type.value,
        "title": notif.title,
        "message": notif.message,
        "level": notif.level.value,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
    }


@notification_router.get("/list")
async def get_notifications(
    project_id: Optional[int] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    status: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Get notifications with filtering.

    Args:
        project_id: Project to filter by
        limit: Maximum number to return
        offset: Number to skip
        status: Filter by status
        level: Filter by level

    Returns:
        Notifications and metadata
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        status_filter = NotificationStatus(status) if status else None
        level_filter = AlertLevel(level) if level else None

        notifications, total = await notification_service.get_notifications(
            project_id=project_id,
            limit=limit,
            offset=offset,
            status=status_filter,
            level=level_filter,
        )

        unread = sum(1 for n in notifications if n.status == NotificationStatus.SENT)
        critical = sum(1 for n in notifications if n.level == AlertLevel.CRITICAL)

        return {
            "notifications": [
                {
                    "id": n.id,
                    "type": n.alert_type.value,
                    "title": n.title,
                    "message": n.message,
                    "level": n.level.value,
                    "status": n.status.value,
                    "channels": [ch.value for ch in n.channels],
                    "metadata": n.metadata,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                    "read_at": n.read_at.isoformat() if n.read_at else None,
                }
                for n in notifications
            ],
            "total": total,
            "unread_count": unread,
            "critical_count": critical,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid filter value: {e}")


@notification_router.put("/{notification_id}/read")
async def mark_notification_read(notification_id: int) -> Dict[str, Any]:
    """Mark a notification as read.

    Args:
        notification_id: Notification ID

    Returns:
        Updated notification
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    notif = await notification_service.mark_as_read(notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {
        "id": notif.id,
        "status": notif.status.value,
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
    }


@notification_router.put("/{notification_id}/archive")
async def archive_notification(notification_id: int) -> Dict[str, Any]:
    """Archive a notification.

    Args:
        notification_id: Notification ID

    Returns:
        Updated notification
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    notif = await notification_service.archive_notification(notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {
        "id": notif.id,
        "status": notif.status.value,
        "archived_at": notif.archived_at.isoformat() if notif.archived_at else None,
    }


@notification_router.get("/stats")
async def get_notification_stats(
    project_id: Optional[int] = Query(None),
) -> Dict[str, Any]:
    """Get notification statistics.

    Args:
        project_id: Project to filter by

    Returns:
        Statistics
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await notification_service.get_stats(project_id)


# ============================================================================
# Alert Rules Endpoints
# ============================================================================

@notification_router.post("/rules")
async def create_alert_rule(
    rule: AlertRuleCreate,
    project_id: Optional[int] = Query(None),
) -> Dict[str, Any]:
    """Create an alert rule.

    Args:
        rule: Rule to create
        project_id: Optional project ID

    Returns:
        Created rule
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    alert_rule = await notification_service.create_alert_rule(rule, project_id)

    return {
        "id": alert_rule.id,
        "name": alert_rule.name,
        "type": alert_rule.alert_type.value,
        "condition": alert_rule.condition,
        "severity": alert_rule.severity.value,
        "enabled": alert_rule.enabled,
        "channels": [ch.value for ch in alert_rule.channels],
        "created_at": alert_rule.created_at.isoformat() if alert_rule.created_at else None,
    }


@notification_router.get("/rules")
async def get_alert_rules(
    project_id: Optional[int] = Query(None),
    enabled_only: bool = Query(False),
) -> Dict[str, Any]:
    """Get alert rules.

    Args:
        project_id: Project to filter by
        enabled_only: Only return enabled rules

    Returns:
        Alert rules
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    rules = await notification_service.get_alert_rules(project_id, enabled_only)

    return {
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.alert_type.value,
                "condition": r.condition,
                "severity": r.severity.value,
                "enabled": r.enabled,
                "channels": [ch.value for ch in r.channels],
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rules
        ],
        "total": len(rules),
    }


@notification_router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    update: AlertRuleUpdate,
) -> Dict[str, Any]:
    """Update an alert rule.

    Args:
        rule_id: Rule ID
        update: Update data

    Returns:
        Updated rule
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    rule = await notification_service.update_alert_rule(rule_id, update)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        "id": rule.id,
        "name": rule.name,
        "type": rule.alert_type.value,
        "condition": rule.condition,
        "severity": rule.severity.value,
        "enabled": rule.enabled,
        "channels": [ch.value for ch in rule.channels],
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


@notification_router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: int) -> Dict[str, Any]:
    """Delete an alert rule.

    Args:
        rule_id: Rule ID

    Returns:
        Success confirmation
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    success = await notification_service.delete_alert_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {"success": True, "rule_id": rule_id}


# ============================================================================
# Preferences Endpoints
# ============================================================================

@notification_router.get("/preferences")
async def get_preferences(
    project_id: Optional[int] = Query(None),
) -> Dict[str, Any]:
    """Get notification preferences.

    Args:
        project_id: Project ID

    Returns:
        Preferences
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    prefs = await notification_service.get_preferences(project_id)

    return {
        "enable_in_app": prefs.enable_in_app,
        "enable_email": prefs.enable_email,
        "enable_webhook": prefs.enable_webhook,
        "enable_slack": prefs.enable_slack,
        "alert_types": [at.value for at in prefs.alert_types],
        "min_level": prefs.min_level.value,
        "email_address": prefs.email_address,
        "email_digest": prefs.email_digest,
        "email_digest_time": prefs.email_digest_time,
        "webhook_url": prefs.webhook_url,
        "slack_webhook": prefs.slack_webhook,
        "slack_channel": prefs.slack_channel,
        "quiet_hours_enabled": prefs.quiet_hours_enabled,
        "quiet_hours_start": prefs.quiet_hours_start,
        "quiet_hours_end": prefs.quiet_hours_end,
    }


@notification_router.put("/preferences")
async def update_preferences(
    prefs: NotificationPreferences,
    project_id: Optional[int] = Query(None),
) -> Dict[str, Any]:
    """Update notification preferences.

    Args:
        prefs: Updated preferences
        project_id: Project ID

    Returns:
        Updated preferences
    """
    if not notification_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    updated = await notification_service.update_preferences(prefs, project_id)

    return {
        "success": True,
        "enable_in_app": updated.enable_in_app,
        "enable_email": updated.enable_email,
        "enable_webhook": updated.enable_webhook,
        "enable_slack": updated.enable_slack,
    }
