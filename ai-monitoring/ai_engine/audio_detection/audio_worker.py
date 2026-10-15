from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from ai_engine.audio_detection.detector import AudioDeviceDetector
from ai_engine.audio_detection.temporal_filter import DetectionState

logger = logging.getLogger(__name__)


@dataclass
class AudioDetectionSnapshot:
    """Thread-safe snapshot of the latest audio-detection state for a specific camera."""
    camera_id: str
    detected: bool = False
    confidence: float = 0.0
    is_confirmed: bool = False
    bbox: Optional[list] = None  # [x, y, w, h]
    device_type: str = "COMM_EARPHONES"
    timestamp: float = 0.0           # System time when snapshot was produced by worker
    frame_timestamp: float = 0.0     # Capture timestamp of the frame that produced the detection
    last_ingress_time: float = 0.0   # Timestamp of the most recent frame pushed to this camera queue
    processed_count: int = 0


class AudioDetectionWorker:
    """
    Dedicated background worker for audio-device detection.
    
    Architecture:
    - Decoupled from the synchronous 19-stage pipeline.
    - Consumes incoming raw frames from Camera 1 and Camera 2 via bounded queues.
    - Drops stale frames when inference is busy to prevent latency buildup.
    - Thread-safe queue submission via event loop marshaling.
    - Maintains independent camera-scoped temporal filter states and freshness tracking.
    - Exposes a thread-safe snapshot bridge consumed by the main pipeline/orchestrator.
    """

    def __init__(
        self,
        detector: Optional[AudioDeviceDetector] = None,
        max_queue_size: int = 1,
        staleness_timeout_seconds: Optional[float] = None,
    ) -> None:
        self._detector = detector or AudioDeviceDetector()
        self._max_queue_size = max_queue_size

        # Ingress staleness timeout: if a camera stops pushing frames for longer than this,
        # its positive detection state expires and is no longer reported as active.
        # Defaults to max(2.0, dropout_grace_seconds + 0.5) to align with temporal filter grace.
        grace = getattr(self._detector, "dropout_grace_seconds", 1.50)
        self._staleness_timeout_seconds = (
            staleness_timeout_seconds if staleness_timeout_seconds is not None
            else max(2.0, grace + 0.5)
        )

        # Per-camera bounded frame queues: camera_id -> asyncio.Queue
        self._queues: Dict[str, asyncio.Queue] = {}

        # Thread-safe state snapshots: camera_id -> AudioDetectionSnapshot
        self._snapshots_lock = threading.Lock()
        self._snapshots: Dict[str, AudioDetectionSnapshot] = {
            "camera_1": AudioDetectionSnapshot(camera_id="camera_1"),
            "camera_2": AudioDetectionSnapshot(camera_id="camera_2"),
        }

        # Event loop reference & background task
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._is_healthy = False
        self._worker_task: Optional[asyncio.Task] = None
        self._inference_lock = threading.Lock()

    @property
    def detector(self) -> AudioDeviceDetector:
        return self._detector

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_healthy(self) -> bool:
        """True if the worker is started and its processing task is alive and healthy."""
        return self._running and self._is_healthy and (
            self._worker_task is not None and not self._worker_task.done()
        )

    def initialize(self) -> None:
        """Initialize the underlying YOLO audio detector."""
        self._detector.initialize()

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the async background worker task."""
        if not self._detector.is_available:
            self.initialize()
        self._detector.start()
        
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.warning("[AudioWorker] No running event loop found during start().")
                self._running = False
                self._is_healthy = False
                return

        self._loop = loop
        self._running = True
        self._is_healthy = True
        
        # Ensure queues exist on the worker's event loop
        if "camera_1" not in self._queues:
            self._queues["camera_1"] = asyncio.Queue(maxsize=self._max_queue_size)
        if "camera_2" not in self._queues:
            self._queues["camera_2"] = asyncio.Queue(maxsize=self._max_queue_size)

        if self._worker_task is None or self._worker_task.done():
            self._worker_task = self._loop.create_task(self._run_loop())
            logger.info("[AudioWorker] Dedicated background worker task started.")

    def stop(self) -> None:
        """Stop background worker and clear resources."""
        self._running = False
        self._is_healthy = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            self._worker_task = None
        self._detector.stop()
        logger.info("[AudioWorker] Dedicated background worker stopped.")

    def clear_camera_state(self, camera_id: str) -> None:
        """Explicitly reset detection state for a camera upon disconnect."""
        cam_id = "camera_1" if (not camera_id or camera_id == "playground_webcam") else camera_id
        with self._snapshots_lock:
            prev = self._snapshots.get(cam_id)
            p_count = prev.processed_count if prev else 0
            self._snapshots[cam_id] = AudioDetectionSnapshot(
                camera_id=cam_id,
                detected=False,
                confidence=0.0,
                is_confirmed=False,
                bbox=None,
                device_type="COMM_EARPHONES",
                timestamp=time.time(),
                frame_timestamp=0.0,
                last_ingress_time=0.0,
                processed_count=p_count,
            )
        # Also reset camera filter in detector
        try:
            cam_filter = self._detector._get_filter_for_camera(cam_id)
            cam_filter.reset()
        except Exception:
            pass
        logger.info(f"[AudioWorker] Cleared state for disconnected camera '{cam_id}'.")

    def push_frame(
        self,
        camera_id: str,
        jpeg_bytes: bytes,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Non-blocking frame push from WebSocket ingress.
        Thread-safe: marshals queue mutations to the owning event loop via call_soon_threadsafe
        if invoked from an external OS thread.
        Uses deliberate max-size-1 frame-drop policy (drops oldest frame on overflow).
        """
        if not self._running:
            return

        cam_id = "camera_1" if (not camera_id or camera_id == "playground_webcam") else camera_id
        now = timestamp or time.time()

        # Update last ingress freshness timestamp immediately under lock
        with self._snapshots_lock:
            snap = self._snapshots.get(cam_id)
            if snap is not None:
                snap.last_ingress_time = now

        loop = self._loop
        if loop is None or loop.is_closed():
            return

        # Helper to execute queue drop and put on the owning event loop
        def _enqueue():
            if not self._running:
                return
            q = self._queues.get(cam_id)
            if q is None:
                q = asyncio.Queue(maxsize=self._max_queue_size)
                self._queues[cam_id] = q

            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait((cam_id, jpeg_bytes, now))
            except asyncio.QueueFull:
                pass

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop is loop:
            # Already on the owning event loop
            _enqueue()
        else:
            # Called from a background thread — marshal onto the owning event loop
            loop.call_soon_threadsafe(_enqueue)

    async def _run_loop(self) -> None:
        """Main async consumption loop cycling across available camera queues."""
        logger.info("[AudioWorker] Ingress consumer loop active.")
        try:
            while self._running:
                processed_any = False
                for cam_id in ("camera_1", "camera_2"):
                    q = self._queues.get(cam_id)
                    if q is not None and not q.empty():
                        try:
                            item = q.get_nowait()
                            processed_any = True
                            c_id, jpeg_bytes, ts = item
                            # Run blocking CPU inference in a dedicated worker thread
                            await asyncio.to_thread(self._process_single_frame, c_id, jpeg_bytes, ts)
                            q.task_done()
                        except asyncio.QueueEmpty:
                            pass
                        except asyncio.CancelledError:
                            return
                        except Exception as e:
                            logger.error(f"[AudioWorker] Error processing frame for {cam_id}: {e}", exc_info=True)

                if not processed_any:
                    # Sleep briefly when queues are empty to yield to event loop
                    await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info("[AudioWorker] Run loop cancelled.")
        except Exception as e:
            self._is_healthy = False
            logger.critical(f"[AudioWorker] Fatal crash in run loop: {e}", exc_info=True)
            # Fail closed: clear running status so pipeline does not read frozen snapshots
            self._running = False
        finally:
            if not self._running:
                self._is_healthy = False

    def _process_single_frame(self, camera_id: str, jpeg_bytes: bytes, frame_time: float) -> None:
        """Synchronous frame decode and YOLO26n audio-inference execution."""
        try:
            # 1. Decode JPEG
            np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            bgr_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if bgr_image is None or bgr_image.size == 0:
                return

            # 2. Run inference & update camera-scoped temporal filter
            with self._inference_lock:
                if not self._detector.is_available or self._detector._model is None:
                    return

                h, w = bgr_image.shape[:2]
                from ai_engine.audio_detection.temporal_filter import FrameDetection
                frame_detections = []

                # Pass 1: Full-frame pass (detects over-ear headphones and general audio devices)
                results_full = self._detector._model.predict(
                    bgr_image,
                    conf=self._detector.conf_threshold,
                    imgsz=self._detector.imgsz,
                    device=self._detector.device,
                    verbose=False,
                )
                if results_full and len(results_full) > 0 and results_full[0].boxes is not None:
                    for box in results_full[0].boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = self._detector._model.names.get(cls_id, str(cls_id))
                        conf_val = float(box.conf[0].item())
                        xyxy = box.xyxy[0].tolist()
                        frame_detections.append(
                            FrameDetection(
                                cls_id=cls_id,
                                cls_name=cls_name,
                                confidence=conf_val,
                                bbox=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                            )
                        )

                # Pass 2: Focused upper-body/head region pass (resolves ~20px in-ear earbuds/earphones)
                # When sitting at a desk, candidate head & ears reside in upper 90% and center 70% of frame
                y1, y2 = 0, int(h * 0.90)
                x1, x2 = int(w * 0.15), int(w * 0.85)
                if (y2 - y1) > 40 and (x2 - x1) > 40:
                    crop_img = bgr_image[y1:y2, x1:x2]
                    results_crop = self._detector._model.predict(
                        crop_img,
                        conf=self._detector.conf_threshold,
                        imgsz=800,
                        device=self._detector.device,
                        verbose=False,
                    )
                    if results_crop and len(results_crop) > 0 and results_crop[0].boxes is not None:
                        for box in results_crop[0].boxes:
                            cls_id = int(box.cls[0].item())
                            cls_name = self._detector._model.names.get(cls_id, str(cls_id))
                            conf_val = float(box.conf[0].item())
                            b = [float(v) for v in box.xyxy[0].tolist()]
                            # Map coordinates back to full camera frame
                            fb = (b[0] + x1, b[1] + y1, b[2] + x1, b[3] + y1)
                            frame_detections.append(
                                FrameDetection(
                                    cls_id=cls_id,
                                    cls_name=cls_name,
                                    confidence=conf_val,
                                    bbox=fb,
                                )
                            )

                # Update camera-specific temporal filter
                cam_filter = self._detector._get_filter_for_camera(camera_id)
                cam_filter.update(frame_detections, current_time=frame_time)

                # 3. Create updated snapshot
                detected = cam_filter.is_audio_device_detected
                confidence = round(cam_filter.display_confidence, 4)
                is_confirmed = (cam_filter.state == DetectionState.CONFIRMED)
                
                # Retain bounding box during active detection, candidate, or dropout grace
                bbox = None
                raw_bbox = cam_filter.active_bbox if cam_filter.active_bbox is not None else getattr(cam_filter, "last_bbox", None)
                if (detected or cam_filter.state == DetectionState.CANDIDATE) and raw_bbox is not None:
                    x1, y1, x2, y2 = raw_bbox
                    x = int(round(x1))
                    y = int(round(y1))
                    w = int(round(max(0.0, x2 - x1)))
                    h = int(round(max(0.0, y2 - y1)))
                    bbox = [x, y, w, h]

                with self._snapshots_lock:
                    prev = self._snapshots.get(camera_id)
                    p_count = (prev.processed_count + 1) if prev else 1
                    ingress_time = prev.last_ingress_time if prev else frame_time
                    self._snapshots[camera_id] = AudioDetectionSnapshot(
                        camera_id=camera_id,
                        detected=detected,
                        confidence=confidence,
                        is_confirmed=is_confirmed,
                        bbox=bbox,
                        device_type="COMM_EARPHONES",
                        timestamp=time.time(),
                        frame_timestamp=frame_time,
                        last_ingress_time=ingress_time,
                        processed_count=p_count,
                    )

        except Exception as e:
            logger.error(f"[AudioWorker] Inference failure on camera '{camera_id}': {e}", exc_info=True)

    def update_snapshot_from_detector(
        self,
        camera_id: str,
        detected: bool,
        confidence: float,
        is_confirmed: bool,
        bbox: Optional[list],
        frame_timestamp: float,
    ) -> None:
        """Thread-safe update of the latest snapshot directly from the detector pipeline."""
        cam_id = "camera_1" if (not camera_id or camera_id == "playground_webcam") else camera_id
        now = time.time()
        with self._snapshots_lock:
            prev = self._snapshots.get(cam_id)
            p_count = (prev.processed_count + 1) if prev else 1
            self._snapshots[cam_id] = AudioDetectionSnapshot(
                camera_id=cam_id,
                detected=detected,
                confidence=confidence,
                is_confirmed=is_confirmed,
                bbox=bbox,
                device_type="COMM_EARPHONES",
                timestamp=now,
                frame_timestamp=frame_timestamp,
                last_ingress_time=now,
                processed_count=p_count,
            )

    def get_snapshot(self, camera_id: str) -> AudioDetectionSnapshot:
        """
        Thread-safe read of the latest audio-detection state for a specific camera.
        Called by the orchestrator or API during pipeline execution.
        """
        cam_id = "camera_1" if (not camera_id or camera_id == "playground_webcam") else camera_id
        
        now = time.time()
        with self._snapshots_lock:
            snap = self._snapshots.get(cam_id)
            if snap is None:
                snap = AudioDetectionSnapshot(camera_id=cam_id)
                self._snapshots[cam_id] = snap
                return snap

            # Staleness check: If camera stopped receiving frames beyond timeout, expire positive state
            if snap.detected and snap.last_ingress_time > 0:
                elapsed_since_ingress = now - snap.last_ingress_time
                if elapsed_since_ingress > self._staleness_timeout_seconds:
                    logger.debug(
                        f"[AudioWorker] Snapshot expired for camera '{cam_id}' due to frame staleness "
                        f"({elapsed_since_ingress:.2f}s > {self._staleness_timeout_seconds:.2f}s)."
                    )
                    return AudioDetectionSnapshot(
                        camera_id=cam_id,
                        detected=False,
                        confidence=0.0,
                        is_confirmed=False,
                        bbox=None,
                        device_type=snap.device_type,
                        timestamp=now,
                        frame_timestamp=snap.frame_timestamp,
                        last_ingress_time=snap.last_ingress_time,
                        processed_count=snap.processed_count,
                    )

            return snap


# Global singleton instance
audio_detection_worker = AudioDetectionWorker()

