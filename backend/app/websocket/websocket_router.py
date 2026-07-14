from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/{exam_session_id}")
async def websocket_endpoint(websocket: WebSocket, exam_session_id: int):
    """
    WebSocket endpoint for live tracking of a specific exam session.
    Expects clients to optionally send 'ping' text messages to maintain the heartbeat loop.
    """
    await manager.connect(websocket, exam_session_id)
    try:
        # Start the blocking heartbeat receive loop
        await manager.heartbeat_loop(websocket, exam_session_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, exam_session_id)
    except Exception as e:
        logger.error(f"WebSocket error for exam {exam_session_id}: {e}")
        manager.disconnect(websocket, exam_session_id)
