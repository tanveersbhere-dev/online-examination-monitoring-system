import asyncio
import logging
from typing import Dict, List, Set
from fastapi import WebSocket

from app.websocket.websocket_events import WSEvent, WSEventType
from app.services.exceptions import ConnectionManagerError

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Stateful Singleton managing active WebSocket connections per exam_session_id.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            # Map exam_session_id -> Set of WebSockets
            cls._instance.active_connections = {}
        return cls._instance

    async def connect(self, websocket: WebSocket, exam_session_id: int):
        await websocket.accept()
        if exam_session_id not in self.active_connections:
            self.active_connections[exam_session_id] = set()
        self.active_connections[exam_session_id].add(websocket)
        logger.info(f"WebSocket connected for exam {exam_session_id}. Total: {len(self.active_connections[exam_session_id])}")

    def disconnect(self, websocket: WebSocket, exam_session_id: int):
        if exam_session_id in self.active_connections:
            self.active_connections[exam_session_id].discard(websocket)
            logger.info(f"WebSocket disconnected for exam {exam_session_id}. Remaining: {len(self.active_connections[exam_session_id])}")
            if not self.active_connections[exam_session_id]:
                del self.active_connections[exam_session_id]

    async def broadcast(self, event: WSEvent):
        """Broadcast an event to all clients tracking this exam_session_id."""
        exam_id = event.exam_session_id
        if exam_id in self.active_connections:
            websockets = self.active_connections[exam_id].copy()
            for ws in websockets:
                try:
                    await ws.send_json(event.model_dump(mode="json"))
                except Exception as e:
                    logger.warning(f"Failed to send WS message. Removing dead client. Error: {e}")
                    self.disconnect(ws, exam_id)

    async def broadcast_all(self, event: WSEvent):
        """Broadcast an event globally across all exam sessions."""
        for exam_id, websockets in list(self.active_connections.items()):
            for ws in websockets.copy():
                try:
                    await ws.send_json(event.model_dump(mode="json"))
                except Exception as e:
                    logger.warning(f"Failed to send WS message. Removing dead client. Error: {e}")
                    self.disconnect(ws, exam_id)

    async def heartbeat_loop(self, websocket: WebSocket, exam_session_id: int):
        """Simple ping/pong to keep connection alive."""
        from datetime import datetime
        try:
            while True:
                # Wait for a ping or message from client to act as heartbeat
                data = await websocket.receive_text()
                if data == "ping":
                    pong_event = WSEvent(
                        event=WSEventType.HEARTBEAT,
                        timestamp=datetime.utcnow(),
                        exam_session_id=exam_session_id,
                        payload={"status": "alive"}
                    )
                    await websocket.send_json(pong_event.model_dump(mode="json"))
        except Exception:
            self.disconnect(websocket, exam_session_id)

manager = ConnectionManager()
