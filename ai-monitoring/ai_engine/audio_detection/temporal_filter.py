from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple


class DetectionState:
    NO_DEVICE = "NO AUDIO DEVICE"
    CANDIDATE = "CANDIDATE DETECTED"
    CONFIRMED = "AUDIO DEVICE DETECTED"
    DROPOUT_GRACE = "AUDIO DEVICE DETECTED (HOLDING)"


@dataclass
class FrameDetection:
    cls_id: int
    cls_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2


class TemporalAudioDeviceFilter:
    """
    Separates frame-level raw YOLO detections from application-level state.
    
    Prevents single-frame missed detections from causing state flickering,
    and prevents isolated single-frame false alarms (e.g. bare ear flashes)
    from triggering confirmed application alerts.
    """
    def __init__(
        self,
        confirm_seconds: float = 0.25,
        dropout_grace_seconds: float = 1.50,
        display_alpha: float = 0.12,
    ) -> None:
        self.confirm_seconds = confirm_seconds
        self.dropout_grace_seconds = dropout_grace_seconds
        self.display_alpha = display_alpha

        self.state: str = DetectionState.NO_DEVICE
        self.candidate_start_time: Optional[float] = None
        self.last_detection_time: Optional[float] = None
        self.last_frame_time: float = time.perf_counter()

        self.confirmed_class: Optional[str] = None
        self.confirmed_count: int = 0
        self.display_confidence: float = 0.0

        # Current frame diagnostic attributes (strictly raw YOLO detections)
        self.raw_status: str = DetectionState.NO_DEVICE
        self.raw_count: int = 0
        self.active_class: Optional[str] = None
        self.active_conf: float = 0.0
        self.active_bbox: Optional[Tuple[float, float, float, float]] = None
        self.last_bbox: Optional[Tuple[float, float, float, float]] = None

    @property
    def smoothed_confidence(self) -> float:
        """Backwards compatibility alias for display_confidence."""
        return self.display_confidence

    @smoothed_confidence.setter
    def smoothed_confidence(self, val: float) -> None:
        self.display_confidence = val

    def update(
        self,
        detections: List[FrameDetection],
        current_time: Optional[float] = None,
    ) -> str:
        now = current_time if current_time is not None else time.perf_counter()
        self.last_frame_time = now

        self.raw_count = len(detections)
        self.raw_status = (
            f"AUDIO DEVICE DETECTED: {self.raw_count}"
            if self.raw_count > 0
            else "NO AUDIO DEVICE"
        )

        if self.raw_count > 0:
            top_det = max(detections, key=lambda d: d.confidence)
            self.active_class = top_det.cls_name
            self.active_conf = top_det.confidence
            self.active_bbox = top_det.bbox
            self.last_bbox = top_det.bbox
            self.last_detection_time = now

            # DISPLAY-ONLY SMOOTHING (never used for any state/detection decision)
            if self.display_confidence == 0.0:
                self.display_confidence = top_det.confidence
            else:
                self.display_confidence = (
                    self.display_alpha * top_det.confidence
                    + (1.0 - self.display_alpha) * self.display_confidence
                )

            if self.state in (DetectionState.CONFIRMED, DetectionState.DROPOUT_GRACE):
                self.state = DetectionState.CONFIRMED
                self.confirmed_class = top_det.cls_name
                self.confirmed_count = self.raw_count

            elif self.state == DetectionState.NO_DEVICE:
                self.candidate_start_time = now
                self.state = DetectionState.CANDIDATE
                self.confirmed_class = top_det.cls_name
                self.confirmed_count = self.raw_count

            elif self.state == DetectionState.CANDIDATE:
                elapsed = (
                    now - self.candidate_start_time
                    if self.candidate_start_time is not None
                    else 0.0
                )
                if elapsed >= self.confirm_seconds:
                    self.state = DetectionState.CONFIRMED
                    self.confirmed_class = top_det.cls_name
                    self.confirmed_count = self.raw_count

        else:
            self.active_class = None
            self.active_conf = 0.0
            self.active_bbox = None

            if self.state == DetectionState.CANDIDATE:
                # 1-frame or brief spike did not sustain long enough to confirm -> reset
                self.state = DetectionState.NO_DEVICE
                self.candidate_start_time = None
                self.display_confidence = 0.0
                self.last_bbox = None

            elif self.state in (DetectionState.CONFIRMED, DetectionState.DROPOUT_GRACE):
                time_since_detection = (
                    now - self.last_detection_time
                    if self.last_detection_time is not None
                    else 999.0
                )
                if time_since_detection < self.dropout_grace_seconds:
                    self.state = DetectionState.DROPOUT_GRACE
                    # PRESERVE self.display_confidence and self.last_bbox unchanged during dropout grace
                else:
                    self.state = DetectionState.NO_DEVICE
                    self.confirmed_class = None
                    self.confirmed_count = 0
                    self.display_confidence = 0.0
                    self.candidate_start_time = None
                    self.last_bbox = None

        return self.state

    @property
    def is_audio_device_detected(self) -> bool:
        return self.state in (DetectionState.CONFIRMED, DetectionState.DROPOUT_GRACE)

    def reset(self) -> None:
        """Reset internal filter state."""
        self.state = DetectionState.NO_DEVICE
        self.candidate_start_time = None
        self.last_detection_time = None
        self.last_frame_time = time.perf_counter()
        self.confirmed_class = None
        self.confirmed_count = 0
        self.display_confidence = 0.0
        self.raw_status = DetectionState.NO_DEVICE
        self.raw_count = 0
        self.active_class = None
        self.active_conf = 0.0
        self.active_bbox = None
        self.last_bbox = None

