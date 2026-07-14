import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app
from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent, WSEventType
from datetime import datetime

def test_websocket_connection_and_heartbeat():
    client = TestClient(app)
    # The TestClient provides a context manager for websockets
    with client.websocket_connect("/ws/monitoring/999") as websocket:
        # Check that connection was established
        assert 999 in manager.active_connections
        assert len(manager.active_connections[999]) == 1
        
        # Test heartbeat
        websocket.send_text("ping")
        response = websocket.receive_json()
        assert response["event"] == "HEARTBEAT"
        assert response["payload"]["status"] == "alive"

def test_websocket_broadcast():
    client = TestClient(app)
    with client.websocket_connect("/ws/monitoring/101") as websocket1:
        with client.websocket_connect("/ws/monitoring/101") as websocket2:
            
            assert len(manager.active_connections[101]) == 2
            
            # Send broadcast event synchronously using asyncio.run
            event = WSEvent(
                event=WSEventType.RISK_UPDATED,
                timestamp=datetime.utcnow(),
                exam_session_id=101,
                payload={"new_score": 85.0}
            )
            
            # Create a new event loop purely for the broadcast trigger
            asyncio.run(manager.broadcast(event))
            
            # Both websockets should receive it
            resp1 = websocket1.receive_json()
            resp2 = websocket2.receive_json()
            
            assert resp1["event"] == "RISK_UPDATED"
            assert resp1["payload"]["new_score"] == 85.0
            
            assert resp2["event"] == "RISK_UPDATED"
            assert resp2["payload"]["new_score"] == 85.0

def test_websocket_disconnect():
    client = TestClient(app)
    
    with client.websocket_connect("/ws/monitoring/102") as websocket:
        assert 102 in manager.active_connections
        
    # Once context manager closes, the socket disconnects
    assert 102 not in manager.active_connections
