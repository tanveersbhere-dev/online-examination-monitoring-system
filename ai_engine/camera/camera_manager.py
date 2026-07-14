import time
import logging
import threading
from dataclasses import dataclass
from typing import Optional, Union

@dataclass
class CameraHealth:
    camera_connected: bool
    camera_running: bool
    fps: float
    queue_size: int
    dropped_frames: int
    uptime: float
    last_frame_timestamp: float

try:
    import cv2
except ImportError:
    cv2 = None

from ai_engine.camera.frame import Frame
from ai_engine.camera.frame_queue import FrameQueue
from ai_engine.camera.webcam import Webcam
from ai_engine.core.exam_context import ExamContext, CameraState
from ai_engine.core.exceptions import CameraError
from ai_engine.interfaces.camera_provider import CameraProvider
from ai_engine.utils.fps import FPSTracker

logger = logging.getLogger("ai_engine.camera")

class CameraManager(CameraProvider):
    def __init__(
        self,
        camera_id: Union[int, str] = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        buffer_size: int = 10,
        reconnect_interval: float = 2.0,
        max_reconnect_attempts: int = 5,
        exam_context: Optional[ExamContext] = None
    ) -> None:
        self._camera_id = camera_id
        self._width = width
        self._height = height
        self._fps = fps
        self._buffer_size = buffer_size
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_attempts = max_reconnect_attempts
        self._exam_context = exam_context

        self._webcam: Optional[Webcam] = None
        self._frame_queue: Optional[FrameQueue] = None
        self._fps_tracker = FPSTracker()
        
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._status = "OFFLINE"
        self._dropped_frames = 0
        self._start_time = 0.0
        self._last_frame_timestamp = 0.0
        self._lock = threading.Lock()

    def initialize(self) -> None:
        """Initializes the webcam and frame queue."""
        logger.info("Initializing Camera Manager...")
        self._frame_queue = FrameQueue(max_size=self._buffer_size)
        self._webcam = Webcam(
            camera_id=self._camera_id,
            width=self._width,
            height=self._height,
            fps=self._fps
        )
        self._dropped_frames = 0
        self._fps_tracker.reset()
        self._update_status("INITIALIZED")

    def start(self) -> None:
        """Opens camera connection and starts background capture thread."""
        if self._webcam is None:
            raise CameraError("Camera Manager is not initialized. Call initialize() first.")
        
        logger.info("Starting Camera Manager capture thread...")
        
        # Try to open the camera first
        opened = False
        try:
            opened = self._webcam.open()
        except Exception as e:
            logger.error(f"Error opening webcam: {e}")

        if opened:
            self._update_status("CONNECTED")
            logger.info(f"Camera opened successfully: {self._camera_id}")
        else:
            self._update_status("RECONNECTING")
            logger.warning(f"Could not open camera {self._camera_id} immediately. Thread will handle reconnection.")

        self._start_time = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, name="CameraCaptureThread", daemon=True)
        self._thread.start()

    def process(self, context: ExamContext) -> None:
        """Enriches the exam context with the latest camera frame and state."""
        if not self._running:
            return
            
        with self._lock:
            status = self._status
            fps_val = self._fps_tracker.get_fps()
            dropped = self._dropped_frames

        # Update context
        with context.lock():
            c_state = context.camera_state
            c_state.is_connected = (status == "CONNECTED" or status == "ACTIVE")
            c_state.fps = fps_val
            c_state.dropped_frames = dropped
            c_state.status = status
            context.camera_state = c_state

    def stop(self) -> None:
        """Stops the capture thread and releases the webcam."""
        logger.info("Stopping Camera Manager...")
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        
        if self._webcam is not None:
            self._webcam.close()
            
        self._update_status("STOPPED")

    def cleanup(self) -> None:
        """Cleans up the frame queue and references."""
        logger.info("Cleaning up Camera Manager resources...")
        if self._frame_queue is not None:
            self._frame_queue.clear()
            self._frame_queue = None
        self._webcam = None
        self._update_status("OFFLINE")

    def get_frame(self, timeout: Optional[float] = None) -> Optional[Frame]:
        """Gets a frame from the queue."""
        if self._frame_queue is None:
            return None
        return self._frame_queue.get(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def dropped_count(self) -> int:
        with self._lock:
            return self._dropped_frames

    @property
    def fps(self) -> float:
        return self._fps_tracker.get_fps()

    def health(self) -> CameraHealth:
        """Returns a typed CameraHealth object with current diagnostics."""
        with self._lock:
            connected = (self._status == "CONNECTED" or self._status == "ACTIVE")
            running = self._running
            fps_val = self._fps_tracker.get_fps()
            dropped = self._dropped_frames
            uptime = (time.time() - self._start_time) if self._running else 0.0
            last_ts = self._last_frame_timestamp
            q_size = self._frame_queue.size if self._frame_queue is not None else 0

        return CameraHealth(
            camera_connected=connected,
            camera_running=running,
            fps=fps_val,
            queue_size=q_size,
            dropped_frames=dropped,
            uptime=uptime,
            last_frame_timestamp=last_ts
        )

    def _update_status(self, new_status: str) -> None:
        with self._lock:
            self._status = new_status
        if self._exam_context:
            with self._exam_context.lock():
                c_state = self._exam_context.camera_state
                c_state.status = new_status
                c_state.is_connected = (new_status == "CONNECTED" or new_status == "ACTIVE")
                self._exam_context.camera_state = c_state

    def _capture_loop(self) -> None:
        reconnect_attempts = 0
        last_frame_time = time.time()

        while self._running:
            # Check webcam connection
            if self._webcam is None:
                time.sleep(0.1)
                continue

            if not self._webcam.is_opened():
                self._update_status("RECONNECTING")
                logger.warning(f"Camera connection lost. Reconnection attempt {reconnect_attempts + 1}/{self._max_reconnect_attempts}...")
                
                opened = False
                try:
                    opened = self._webcam.open()
                except Exception as e:
                    logger.error(f"Reconnection attempt error: {e}")

                if opened:
                    logger.info("Camera reconnected successfully.")
                    reconnect_attempts = 0
                    self._update_status("CONNECTED")
                else:
                    reconnect_attempts += 1
                    if reconnect_attempts >= self._max_reconnect_attempts:
                        logger.critical("Maximum camera reconnection attempts reached. Shutting down capture.")
                        self._update_status("OFFLINE")
                        self._running = False
                        break
                    time.sleep(self._reconnect_interval)
                    continue

            # Read frame
            read_result = self._webcam.read()
            if read_result is None:
                # If we haven't received frames for too long, treat as disconnected
                if time.time() - last_frame_time > 5.0:
                    logger.error("Webcam read timeout. Releasing and forcing reconnect...")
                    self._webcam.close()
                time.sleep(0.01)
                continue

            timestamp, original_frame = read_result
            last_frame_time = timestamp
            with self._lock:
                self._last_frame_timestamp = timestamp

            # Process frame properties
            try:
                height, width, channels = original_frame.shape
                
                # Convert to RGB (required for Frame object rgb_frame)
                if cv2 is not None:
                    rgb_frame = cv2.cvtColor(original_frame, cv2.COLOR_BGR2RGB)
                else:
                    rgb_frame = original_frame
            except Exception as e:
                logger.error(f"Failed to process captured frame shape/color: {e}")
                continue

            self._fps_tracker.update()
            current_fps = self._fps_tracker.get_fps()

            # Create Frame dataclass
            frame = Frame(
                frame_id=int(time.time() * 1000),  # Unique identifier based on timestamp millisecond
                timestamp=timestamp,
                original_frame=original_frame,
                rgb_frame=rgb_frame,
                width=width,
                height=height,
                channels=channels,
                fps=current_fps,
                camera_id=self._camera_id
            )

            # Insert into frame queue
            if self._frame_queue is not None:
                dropped = self._frame_queue.put(frame)
                if dropped:
                    with self._lock:
                        self._dropped_frames += 1

            # Enrich context with current frame and camera state
            if self._exam_context is not None:
                with self._exam_context.lock():
                    self._exam_context.current_frame = frame
                    c_state = self._exam_context.camera_state
                    c_state.is_connected = True
                    c_state.fps = current_fps
                    c_state.width = width
                    c_state.height = height
                    c_state.frame_count += 1
                    c_state.dropped_frames = self._dropped_frames
                    c_state.status = "ACTIVE"
                    self._exam_context.camera_state = c_state

            # Control frame rate acquisition slightly to avoid thrashing cpu if camera delivers frames too fast
            sleep_time = max(0.001, (1.0 / self._fps) - (time.time() - timestamp))
            time.sleep(sleep_time)
