"""
Multi-Camera Manager
====================
Phase 1 Infrastructure Component.

Responsibilities:
- Register and track active camera streams (Camera 1 = laptop_webcam, Camera 2 = mobile_camera).
- Store latest frame JPEG buffer and metadata per camera.
- Manage fan-out frame relay to monitoring dashboard subscribers.
- Handle clean camera connect/disconnect lifecycle independently.
- Provide LAN network configuration discovery for mobile phone pairing.

Guarantees:
- Camera 2 connections/disconnections CANNOT crash or block Camera 1.
- No AI or violation processing is performed here (Phase 1 is transport-only).
- Preserves session_id and camera_id on every frame.
"""
import time
import socket
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, List
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("playground.camera_manager")


def get_lan_ip() -> str:
    """Detect the local LAN IP address of this machine for phone connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # 8.8.8.8:53 doesn't send packets, but prompts OS to select interface routing IP
        s.connect(("8.8.8.8", 53))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@dataclass
class CameraStreamInfo:
    """Metadata container for a registered camera source."""
    camera_id: str
    name: str
    camera_type: str  # "laptop_webcam" | "mobile_camera"
    session_id: Optional[str] = None
    is_connected: bool = False
    connected_at: Optional[float] = None
    disconnected_at: Optional[float] = None
    last_frame_timestamp: float = 0.0
    frame_count: int = 0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    latest_jpeg_bytes: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "camera_type": self.camera_type,
            "session_id": self.session_id,
            "is_connected": self.is_connected,
            "connected_at": self.connected_at,
            "disconnected_at": self.disconnected_at,
            "last_frame_timestamp": self.last_frame_timestamp,
            "frame_count": self.frame_count,
            "fps": round(self.fps, 2),
            "width": self.width,
            "height": self.height,
        }


class MultiCameraManager:
    """
    Central coordinator for multi-camera streams in an examination session.
    """

    def __init__(self) -> None:
        self._cameras: Dict[str, CameraStreamInfo] = {
            "camera_1": CameraStreamInfo(
                camera_id="camera_1",
                name="Camera 1 — Laptop Webcam",
                camera_type="laptop_webcam",
            ),
            "camera_2": CameraStreamInfo(
                camera_id="camera_2",
                name="Camera 2 — Mobile Camera",
                camera_type="mobile_camera",
            ),
        }
        # Relay queues for dashboard subscribers: camera_id -> set of asyncio.Queue
        self._feed_subscribers: Dict[str, Set[asyncio.Queue]] = {
            "camera_1": set(),
            "camera_2": set(),
        }
        self._fps_trackers: Dict[str, Dict[str, Any]] = {
            "camera_1": {"count": 0, "last_t": time.time()},
            "camera_2": {"count": 0, "last_t": time.time()},
        }
        self._lan_ip = get_lan_ip()

        # Phase 2: Asynchronous AI frame sampling for Camera 2
        # Target: ~5 FPS (interval >= 0.20s). Live preview relay remains 100% untouched.
        self._cam2_ai_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._cam2_last_ai_sample_time: float = 0.0
        self._cam2_ai_min_interval: float = 0.20  # ~5 FPS max
        self._cam2_ai_task: Optional[asyncio.Task] = None
        self._ai_pipeline_processor = None  # Injected callable or pipeline handler
        # Dedicated bounded thread pool (1 worker) for Camera 2 AI inference.
        # Offloads synchronous blocking inference (e.g. YOLO, context builder)
        # off the asyncio event loop to ensure preview relay runs smoothly at ~15 FPS.
        self._cam2_executor: Optional[ThreadPoolExecutor] = None

    def set_ai_pipeline_processor(self, processor) -> None:
        """Inject the pipeline processor callback: func(camera_id, jpeg_bytes, session_id)."""
        self._ai_pipeline_processor = processor

    def start_background_workers(self) -> None:
        """Start async background tasks for AI processing if an event loop is running."""
        try:
            loop = asyncio.get_running_loop()
            if self._cam2_executor is None:
                self._cam2_executor = ThreadPoolExecutor(
                    max_workers=1,
                    thread_name_prefix="cam2_ai_worker",
                )
            if self._cam2_ai_task is None or self._cam2_ai_task.done():
                self._cam2_ai_task = loop.create_task(self._cam2_ai_worker())
                logger.info("[MultiCameraManager] Camera 2 background AI worker started.")
        except RuntimeError:
            pass  # No running event loop yet; will start when loop is active

    def stop_background_workers(self) -> None:
        """Cancel background AI tasks and shut down worker thread pool."""
        if self._cam2_ai_task and not self._cam2_ai_task.done():
            self._cam2_ai_task.cancel()
            self._cam2_ai_task = None
        if self._cam2_executor is not None:
            self._cam2_executor.shutdown(wait=False, cancel_futures=True)
            self._cam2_executor = None
        logger.info("[MultiCameraManager] Camera 2 background AI worker stopped.")

    async def _cam2_ai_worker(self) -> None:
        """Background worker consuming sampled Camera 2 frames for AI analysis."""
        logger.info("[MultiCameraManager] Camera 2 AI worker loop active.")
        loop = asyncio.get_running_loop()
        while True:
            try:
                item = await self._cam2_ai_queue.get()
                if item is None:
                    break
                cam_id, jpeg_bytes, session_id = item
                if self._ai_pipeline_processor is not None:
                    try:
                        # Offload synchronous blocking AI inference to dedicated background thread.
                        # The asyncio event loop is NEVER blocked, keeping live preview streaming at full FPS.
                        if self._cam2_executor is not None:
                            await loop.run_in_executor(
                                self._cam2_executor,
                                self._ai_pipeline_processor,
                                cam_id,
                                jpeg_bytes,
                                session_id,
                            )
                        else:
                            await asyncio.to_thread(
                                self._ai_pipeline_processor,
                                cam_id,
                                jpeg_bytes,
                                session_id,
                            )
                    except Exception as e:
                        logger.error(f"[MultiCameraManager] Error in Camera 2 AI inference: {e}", exc_info=True)
                self._cam2_ai_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[MultiCameraManager] Error in AI worker: {e}")

    @property
    def lan_ip(self) -> str:
        return self._lan_ip

    def refresh_lan_ip(self) -> str:
        self._lan_ip = get_lan_ip()
        return self._lan_ip

    def get_camera_info(self, camera_id: str) -> Optional[CameraStreamInfo]:
        return self._cameras.get(camera_id)

    def register_connection(self, camera_id: str, session_id: Optional[str] = None) -> CameraStreamInfo:
        """Called when a camera establishes a WebSocket connection."""
        if camera_id not in self._cameras:
            self._cameras[camera_id] = CameraStreamInfo(
                camera_id=camera_id,
                name=f"Camera ({camera_id})",
                camera_type="mobile_camera" if "2" in camera_id or "mobile" in camera_id else "external",
            )
        info = self._cameras[camera_id]
        info.is_connected = True
        info.connected_at = time.time()
        info.disconnected_at = None
        if session_id:
            info.session_id = session_id
        logger.info(f"[MultiCameraManager] Camera '{camera_id}' connected for session '{info.session_id}'")
        return info

    def register_disconnection(self, camera_id: str) -> None:
        """Called when a camera disconnects."""
        if camera_id in self._cameras:
            info = self._cameras[camera_id]
            info.is_connected = False
            info.disconnected_at = time.time()
            info.fps = 0.0
            logger.info(f"[MultiCameraManager] Camera '{camera_id}' disconnected")

            # Notify dashboard feed subscribers of disconnection
            subscribers = list(self._feed_subscribers.get(camera_id, set()))
            for q in subscribers:
                try:
                    q.put_nowait({"type": "status", "camera_id": camera_id, "is_connected": False})
                except Exception:
                    pass

            # Clear audio worker state for disconnected camera
            try:
                from ai_engine.audio_detection.audio_worker import audio_detection_worker
                audio_detection_worker.clear_camera_state(camera_id)
            except Exception:
                pass

    def push_frame(
        self,
        camera_id: str,
        jpeg_bytes: bytes,
        session_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        width: int = 0,
        height: int = 0,
    ) -> None:
        """
        Record a received frame and broadcast to dashboard subscribers.
        Zero AI processing — Phase 1 transport only.
        """
        now = timestamp or time.time()
        if camera_id not in self._cameras:
            self.register_connection(camera_id, session_id)

        info = self._cameras[camera_id]
        info.is_connected = True
        if session_id and not info.session_id:
            info.session_id = session_id
        info.last_frame_timestamp = now
        info.frame_count += 1
        info.latest_jpeg_bytes = jpeg_bytes
        if width > 0:
            info.width = width
        if height > 0:
            info.height = height

        # Compute rolling FPS
        tracker = self._fps_trackers[camera_id]
        tracker["count"] += 1
        elapsed = now - tracker["last_t"]
        if elapsed >= 1.0:
            info.fps = tracker["count"] / elapsed
            tracker["count"] = 0
            tracker["last_t"] = now

        # Relay to dashboard viewer subscribers (Live preview relay remains 100% untouched)
        subscribers = list(self._feed_subscribers.get(camera_id, set()))
        for q in subscribers:
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(jpeg_bytes)
            except Exception:
                pass

        # Push frame non-blockingly to dedicated audio detection worker (Camera 2)
        if camera_id == "camera_2":
            try:
                from ai_engine.audio_detection.audio_worker import audio_detection_worker
                audio_detection_worker.push_frame(
                    camera_id="camera_2",
                    jpeg_bytes=jpeg_bytes,
                    timestamp=now,
                )
            except Exception:
                pass

        # Phase 2: Sample Camera 2 frames for asynchronous AI inference at ~2-3 FPS
        if camera_id == "camera_2" and self._ai_pipeline_processor is not None:
            if (now - self._cam2_last_ai_sample_time) >= self._cam2_ai_min_interval:
                self._cam2_last_ai_sample_time = now
                if self._cam2_ai_queue.full():
                    try:
                        self._cam2_ai_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                try:
                    self._cam2_ai_queue.put_nowait((camera_id, jpeg_bytes, info.session_id or session_id))
                except Exception:
                    pass

    def subscribe_feed(self, camera_id: str) -> asyncio.Queue:
        """Subscribe a monitoring UI WebSocket to real-time JPEG frames."""
        if camera_id not in self._feed_subscribers:
            self._feed_subscribers[camera_id] = set()
        q: asyncio.Queue = asyncio.Queue(maxsize=2)
        self._feed_subscribers[camera_id].add(q)
        return q

    def unsubscribe_feed(self, camera_id: str, q: asyncio.Queue) -> None:
        """Unsubscribe from real-time JPEG frames."""
        if camera_id in self._feed_subscribers:
            self._feed_subscribers[camera_id].discard(q)

    def get_status(self, session_id: Optional[str] = None, frontend_port: int = 5173) -> Dict[str, Any]:
        """Return system-wide multi-camera status and LAN pairing configuration."""
        active_sid = session_id
        if not active_sid:
            active_sid = self._cameras["camera_1"].session_id or self._cameras["camera_2"].session_id or "local_session"

        mobile_url = f"https://{self._lan_ip}:{frontend_port}/mobile?session_id={active_sid}"
        return {
            "success": True,
            "session_id": active_sid,
            "lan_ip": self._lan_ip,
            "mobile_url": mobile_url,
            "cameras": {
                cid: cinfo.to_dict() for cid, cinfo in self._cameras.items()
            },
        }


# Global singleton instance
multi_camera_manager = MultiCameraManager()

