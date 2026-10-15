from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

from ai_engine.audio_detection.temporal_filter import (
    DetectionState,
    FrameDetection,
    TemporalAudioDeviceFilter,
)

logger = logging.getLogger(__name__)


class AudioDeviceDetector:
    """
    Dedicated full-frame YOLO26n audio-device detector with camera-scoped
    temporal stabilization. Detects wireless earbuds, wired earphones,
    and headphones on full camera frames without requiring ear or face crops.
    """

    def __init__(
        self,
        weights_path: Optional[Path] = None,
        conf_threshold: float = 0.5,
        imgsz: int = 640,
        device: str = "cpu",
        confirm_seconds: float = 0.25,
        dropout_grace_seconds: float = 1.50,
        display_alpha: float = 0.12,
    ) -> None:
        self.weights_path = (
            weights_path
            if weights_path is not None
            else Path(__file__).resolve().parent / "weights" / "best.pt"
        )
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz
        self.device = device
        self.confirm_seconds = confirm_seconds
        self.dropout_grace_seconds = dropout_grace_seconds
        self.display_alpha = display_alpha

        self._model = None
        self._is_available = False
        self.active_model_name = "YOLO26n-Audio"

        # Camera-scoped temporal filters to ensure independent temporal state per camera
        self._camera_filters: Dict[str, TemporalAudioDeviceFilter] = {}

    @property
    def is_available(self) -> bool:
        return self._is_available

    def _get_filter_for_camera(self, camera_id: str) -> TemporalAudioDeviceFilter:
        """Retrieve or create an independent temporal filter for the given camera."""
        if camera_id not in self._camera_filters:
            self._camera_filters[camera_id] = TemporalAudioDeviceFilter(
                confirm_seconds=self.confirm_seconds,
                dropout_grace_seconds=self.dropout_grace_seconds,
                display_alpha=self.display_alpha,
            )
        return self._camera_filters[camera_id]

    def initialize(self) -> None:
        """Load YOLO model weights and verify availability."""
        if not self.weights_path.is_file():
            self._is_available = False
            raise FileNotFoundError(
                f"Audio device detector model file not found at: {self.weights_path}"
            )

        try:
            from ultralytics import YOLO

            logger.info(f"[AudioDeviceDetector] Loading YOLO weights from {self.weights_path}...")
            self._model = YOLO(str(self.weights_path))
            self.active_model_name = f"YOLO-Audio ({self.weights_path.name})"
            self._is_available = True
            logger.info(
                f"[AudioDeviceDetector] Model successfully initialized. "
                f"Classes: {self._model.names}, conf={self.conf_threshold}, imgsz={self.imgsz}"
            )
        except Exception as e:
            self._is_available = False
            logger.error(f"[AudioDeviceDetector] Initialization failed: {e}", exc_info=True)
            raise

    def start(self) -> None:
        """Session start lifecycle: reset camera-scoped temporal filters."""
        for cam_filter in self._camera_filters.values():
            cam_filter.reset()
        logger.debug("[AudioDeviceDetector] Started; camera filters reset.")

    def stop(self) -> None:
        """Session stop lifecycle."""
        for cam_filter in self._camera_filters.values():
            cam_filter.reset()
        logger.debug("[AudioDeviceDetector] Stopped.")

    def process(self, context) -> None:
        """
        Process a single frame from context.current_frame.
        Executes dedicated full-frame YOLO audio detection with camera-scoped
        temporal filtering, exactly matching the standalone detector architecture.
        Mutates context.audio_device_info with detection results.
        Never swallows internal inference errors into false negative detections.
        """
        if not self._is_available or self._model is None:
            raise RuntimeError("AudioDeviceDetector is not initialized or model unavailable.")

        current_frame = getattr(context, "current_frame", None)
        if current_frame is None:
            return

        frame_data = getattr(current_frame, "original_frame", None)
        if frame_data is None:
            frame_data = getattr(current_frame, "data", None)
        if frame_data is None or not isinstance(frame_data, np.ndarray) or frame_data.size == 0:
            return

        camera_id = str(getattr(current_frame, "camera_id", "camera_1") or "camera_1")
        now = getattr(current_frame, "timestamp", None)
        if now is None or now <= 0.0:
            now = time.perf_counter()

        audio_info = getattr(context, "audio_device_info", None)
        if audio_info is None:
            return

        h, w = frame_data.shape[:2]
        frame_detections: list[FrameDetection] = []

        # Pass 1: Full-frame inference (detects over-ear headphones and large audio devices)
        results_full = self._model.predict(
            frame_data,
            conf=self.conf_threshold,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )
        if results_full and len(results_full) > 0 and results_full[0].boxes is not None:
            for box in results_full[0].boxes:
                cls_id = int(box.cls[0].item())
                cls_name = self._model.names.get(cls_id, str(cls_id))
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

        # Pass 2: Upper-body / Head region inference (resolves small in-ear earphones and wireless earbuds)
        y1, y2 = 0, int(h * 0.90)
        x1, x2 = int(w * 0.15), int(w * 0.85)
        if (y2 - y1) > 40 and (x2 - x1) > 40:
            crop_img = frame_data[y1:y2, x1:x2]
            results_crop = self._model.predict(
                crop_img,
                conf=self.conf_threshold,
                imgsz=800,
                device=self.device,
                verbose=False,
            )
            if results_crop and len(results_crop) > 0 and results_crop[0].boxes is not None:
                for box in results_crop[0].boxes:
                    cls_id = int(box.cls[0].item())
                    cls_name = self._model.names.get(cls_id, str(cls_id))
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

        # Apply camera-scoped temporal filter
        cam_filter = self._get_filter_for_camera(camera_id)
        cam_filter.update(frame_detections, current_time=now)

        # Extract stabilized state
        detected = cam_filter.is_audio_device_detected
        confidence = round(cam_filter.display_confidence, 4)
        is_confirmed = (cam_filter.state == DetectionState.CONFIRMED)

        # Extract bounding box (preserve during active, candidate, and dropout grace)
        bbox = None
        raw_bbox = cam_filter.active_bbox if cam_filter.active_bbox is not None else getattr(cam_filter, "last_bbox", None)
        if (detected or cam_filter.state == DetectionState.CANDIDATE) and raw_bbox is not None:
            x1_b, y1_b, x2_b, y2_b = raw_bbox
            bx = int(round(x1_b))
            by = int(round(y1_b))
            bw = int(round(max(0.0, x2_b - x1_b)))
            bh = int(round(max(0.0, y2_b - y1_b)))
            bbox = [bx, by, bw, bh]

        # Mutate context.audio_device_info
        audio_info.detected = detected
        audio_info.confidence = confidence
        audio_info.is_confirmed = is_confirmed
        audio_info.device_type = "COMM_EARPHONES"
        audio_info.bbox = bbox
        audio_info.timestamp = now
        context.audio_device_info = audio_info

        # Also bridge snapshot to AudioDetectionWorker for external queries
        try:
            from ai_engine.audio_detection.audio_worker import audio_detection_worker
            audio_detection_worker.update_snapshot_from_detector(
                camera_id=camera_id,
                detected=detected,
                confidence=confidence,
                is_confirmed=is_confirmed,
                bbox=bbox,
                frame_timestamp=now,
            )
        except Exception:
            pass

