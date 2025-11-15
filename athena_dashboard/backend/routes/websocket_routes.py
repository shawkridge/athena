"""WebSocket routes for real-time research streaming."""

import logging
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from services import StreamingService, StreamingUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

# Global streaming service instance
streaming_service: StreamingService = None

# Track connected clients
class ConnectionManager:
    """Manages WebSocket connections for a task."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, Set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            task_id: Task identifier
            websocket: WebSocket connection
        """
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)
        logger.info(f"Client connected to task {task_id} ({len(self.active_connections[task_id])} total)")

    async def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection.

        Args:
            task_id: Task identifier
            websocket: WebSocket connection
        """
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"Client disconnected from task {task_id}")

    async def broadcast(self, task_id: str, update: StreamingUpdate) -> None:
        """Broadcast an update to all connected clients for a task.

        Args:
            task_id: Task identifier
            update: Streaming update to broadcast
        """
        if task_id not in self.active_connections:
            return

        disconnected = []
        for websocket in self.active_connections[task_id]:
            try:
                await websocket.send_text(update.to_json())
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.append(websocket)

        # Remove disconnected clients
        for websocket in disconnected:
            await self.disconnect(task_id, websocket)


manager = ConnectionManager()


def initialize_websocket_routes(service: StreamingService) -> APIRouter:
    """Initialize WebSocket routes with streaming service.

    Args:
        service: StreamingService instance

    Returns:
        APIRouter with WebSocket endpoints
    """
    global streaming_service
    streaming_service = service
    return router


@router.websocket("/ws/research/{task_id}")
async def websocket_research_endpoint(websocket: WebSocket, task_id: str) -> None:
    """WebSocket endpoint for research result streaming.

    Args:
        websocket: WebSocket connection
        task_id: Task identifier
    """
    await manager.connect(task_id, websocket)

    try:
        # Start streaming if not already active
        if streaming_service:
            await streaming_service.start_streaming(
                task_id,
                on_update=lambda update: manager.broadcast(task_id, update),
            )

        # Keep connection alive, listen for client messages
        while True:
            # Receive client messages (for control commands if needed)
            data = await websocket.receive_text()

            # Handle control commands
            if data == "stop":
                logger.info(f"Received stop command for task {task_id}")
                await streaming_service.stop_streaming(task_id)
                break
            elif data == "pause":
                logger.info(f"Received pause command for task {task_id}")
                # TODO: Implement pause/resume if needed
            elif data == "resume":
                logger.info(f"Received resume command for task {task_id}")
                # TODO: Implement pause/resume if needed

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
        await manager.disconnect(task_id, websocket)

        # Stop streaming if no more clients connected
        if task_id not in manager.active_connections and streaming_service:
            await streaming_service.stop_streaming(task_id)

    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        await manager.disconnect(task_id, websocket)


@router.websocket("/ws/progress/{task_id}")
async def websocket_progress_endpoint(websocket: WebSocket, task_id: str) -> None:
    """WebSocket endpoint for agent progress streaming.

    Args:
        websocket: WebSocket connection
        task_id: Task identifier
    """
    await manager.connect(task_id, websocket)

    try:
        # Start streaming if not already active
        if streaming_service:
            await streaming_service.start_streaming(
                task_id,
                on_update=lambda update: manager.broadcast(task_id, update),
            )

        # Keep connection alive
        while True:
            data = await websocket.receive_text()

            if data == "stop":
                logger.info(f"Received stop command for task {task_id}")
                await streaming_service.stop_streaming(task_id)
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
        await manager.disconnect(task_id, websocket)

        if task_id not in manager.active_connections and streaming_service:
            await streaming_service.stop_streaming(task_id)

    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        await manager.disconnect(task_id, websocket)
