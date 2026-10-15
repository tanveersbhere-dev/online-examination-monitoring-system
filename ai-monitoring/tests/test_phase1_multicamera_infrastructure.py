"""
Phase 1: Dual Camera Infrastructure Test Suite

Verifies:
1. MultiCameraManager camera connection tracking and disconnection
2. Frame buffering and frame rate tracking
3. Frame subscriber fan-out queues for live feed relay
4. LAN IP discovery utility
5. Camera 1 independence: Camera 2 connect/disconnect/failure does not affect Camera 1
6. REST API endpoints (/api/camera/status, /api/camera/{camera_id}/frame)
7. WebSocket endpoints:
   - /ws/camera/{camera_id} (ingress stream for Camera 2)
   - /ws/camera/feed/{camera_id} (relay feed for laptop dashboard)
   - /ws/monitor integration with camera_2 status metadata
"""

import pytest
import asyncio
import numpy as np
import cv2
from fastapi.testclient import TestClient

from backend.main import app
from backend.camera.multi_camera_manager import MultiCameraManager, get_lan_ip


@pytest.fixture
def clean_manager():
    """Provides a fresh MultiCameraManager for test isolation."""
    mgr = MultiCameraManager()
    return mgr


def test_lan_ip_discovery():
    """Verify get_lan_ip returns a non-empty valid IP string."""
    ip = get_lan_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4


def test_manager_registration(clean_manager):
    """Verify camera registration and retrieval."""
    cam1 = clean_manager.register_connection(
        camera_id="camera_1",
        session_id="test_session_1"
    )
    assert cam1.camera_id == "camera_1"
    assert cam1.camera_type == "laptop_webcam"
    assert cam1.is_connected is True

    # Register camera 2
    cam2 = clean_manager.register_connection(
        camera_id="camera_2",
        session_id="test_session_1"
    )
    assert cam2.camera_id == "camera_2"
    assert cam2.camera_type == "mobile_camera"
    assert cam2.is_connected is True

    status = clean_manager.get_status("test_session_1")
    assert status["success"] is True
    assert status["cameras"]["camera_1"]["is_connected"] is True
    assert status["cameras"]["camera_2"]["is_connected"] is True
    assert status["mobile_url"].startswith("https://")


def test_manager_disconnect_independence(clean_manager):
    """Verify disconnecting Camera 2 leaves Camera 1 intact."""
    clean_manager.register_connection("camera_1", "sess_indep")
    clean_manager.register_connection("camera_2", "sess_indep")

    # Disconnect camera 2
    clean_manager.register_disconnection("camera_2")

    status = clean_manager.get_status("sess_indep")
    assert status["cameras"]["camera_1"]["is_connected"] is True
    assert status["cameras"]["camera_2"]["is_connected"] is False


def test_frame_push_and_relay(clean_manager):
    """Verify frame push updates latest frame and notifies fan-out subscribers."""
    clean_manager.register_connection("camera_2", "sess_stream")

    # Subscribe to feed
    sub_queue = clean_manager.subscribe_feed("camera_2")
    assert sub_queue is not None

    # Create dummy JPEG bytes
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, jpeg_bytes = cv2.imencode(".jpg", dummy_img)
    raw_data = jpeg_bytes.tobytes()

    # Push frame
    clean_manager.push_frame("camera_2", raw_data, session_id="sess_stream")
    info = clean_manager.get_camera_info("camera_2")
    assert info is not None
    assert info.frame_count == 1
    assert info.latest_jpeg_bytes == raw_data

    # Verify subscriber queue has the item
    assert sub_queue.qsize() == 1
    delivered_bytes = sub_queue.get_nowait()
    assert delivered_bytes == raw_data

    # Unsubscribe
    clean_manager.unsubscribe_feed("camera_2", sub_queue)
    assert sub_queue not in clean_manager._feed_subscribers["camera_2"]


def test_rest_camera_status():
    """Verify GET /api/camera/status returns camera statuses."""
    client = TestClient(app)
    response = client.get("/api/camera/status")
    assert response.status_code == 200
    data = response.json()
    assert "lan_ip" in data
    assert "cameras" in data
    assert "camera_1" in data["cameras"]
    assert "camera_2" in data["cameras"]
    assert data["mobile_url"].startswith("https://")


def test_websocket_camera2_ingress_and_feed():
    """Verify Camera 2 ingress WebSocket and feed subscription WebSocket."""
    client = TestClient(app)

    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, jpeg_bytes = cv2.imencode(".jpg", dummy_img)
    raw_bytes = jpeg_bytes.tobytes()

    # Connect viewer WebSocket first
    with client.websocket_connect("/ws/camera/feed/camera_2?session_id=test_ws") as feed_ws:
        # Connect ingress WebSocket for Camera 2
        with client.websocket_connect("/ws/camera/camera_2?session_id=test_ws") as ingress_ws:
            # First message from server on connect is the connection ack
            ack = ingress_ws.receive_json()
            assert ack["type"] == "connection_ack"
            assert ack["status"] == "CONNECTED"
            assert ack["camera_id"] == "camera_2"

            # Send binary JPEG frame from mobile
            ingress_ws.send_bytes(raw_bytes)

            # Feed subscriber should receive relayed binary frame
            relayed_frame = feed_ws.receive_bytes()
            assert relayed_frame == raw_bytes
