"""MediaPipe iris-relative eye-gaze extraction.

Gaze is measured from each iris centre relative to its own eye corners and
lid aperture.  The values are normalized to eye geometry, so face size and
camera resolution do not directly determine the result.  The calibrated
attention rule interprets these measurements; this extractor never creates a
violation by itself.
"""
from __future__ import annotations

import logging
import math
import time
from typing import List, Optional, Tuple

from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext
from ai_engine.features.eye_gaze.extractor import EyeGazeExtractorInterface
from ai_engine.features.eye_gaze.exceptions import EyeGazeStateError, EyeTrackingError, InvalidIrisLandmarksError
from ai_engine.features.eye_gaze.models import (
    LEFT_EYE_LEFT_CORNER_INDEX, LEFT_EYE_LOWER_LID_INDEX, LEFT_EYE_RIGHT_CORNER_INDEX,
    LEFT_EYE_UPPER_LID_INDEX, LEFT_IRIS_CENTER_INDEX, RIGHT_EYE_LEFT_CORNER_INDEX,
    RIGHT_EYE_LOWER_LID_INDEX, RIGHT_EYE_RIGHT_CORNER_INDEX, RIGHT_EYE_UPPER_LID_INDEX,
    RIGHT_IRIS_CENTER_INDEX, EyeGazeConfig,
)
from ai_engine.features.eye_gaze.result import EyeCenter, EyeGaze, EyeGazeResult, IrisCenter

logger = logging.getLogger("ai_engine.features.eye_gaze")
Point = Tuple[float, float, float]


def _normalized_eye_gaze(left_corner: Point, right_corner: Point, upper_lid: Point, lower_lid: Point, iris: Point) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float]]]:
    """Return iris displacement normalized by visible eye width/height.

    ``x`` and ``y`` are approximately in [-1, 1] for an iris near the eyelid
    limits.  A malformed/tightly closed eye returns ``None`` instead of a
    guessed direction.
    """
    min_x, max_x = sorted((left_corner[0], right_corner[0]))
    min_y, max_y = sorted((upper_lid[1], lower_lid[1]))
    width = max_x - min_x
    height = max_y - min_y
    if width < 0.008 or height < 0.003:
        return None
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    gaze_x = (iris[0] - center_x) / (width / 2.0)
    gaze_y = (iris[1] - center_y) / (height / 2.0)
    # Iris far beyond the physical aperture is a landmark failure, not gaze.
    if abs(gaze_x) > 1.35 or abs(gaze_y) > 1.35:
        return None
    return (gaze_x, gaze_y, 1.0), (center_x, center_y)


class OneEuroFilter1D:
    """
    1-Euro Filter for 1D signal smoothing (Casiez et al., CHI 2012).
    Adaptive low-pass filter: high smoothing at low velocity (eliminates jitter during fixation),
    low smoothing at high velocity (eliminates lag during rapid saccades).
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self._x_prev: Optional[float] = None
        self._dx_prev: float = 0.0
        self._t_prev: Optional[float] = None

    def reset(self) -> None:
        """Reset internal filter state on session start or tracking loss."""
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    @staticmethod
    def _smoothing_factor(te: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * te
        return r / (r + 1.0)

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        t = timestamp if timestamp is not None else time.perf_counter()
        if self._t_prev is None or self._x_prev is None:
            self._x_prev = float(x)
            self._dx_prev = 0.0
            self._t_prev = t
            return float(x)

        te = t - self._t_prev
        # If timestamp is non-monotonic or huge gap (> 1.0s tracking loss), reset cleanly
        if te <= 0.0 or te > 1.0:
            self._x_prev = float(x)
            self._dx_prev = 0.0
            self._t_prev = t
            return float(x)

        # 1. Derivative (velocity) estimation with low-pass filtering
        dx = (x - self._x_prev) / te
        alpha_d = self._smoothing_factor(te, self.d_cutoff)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self._dx_prev

        # 2. Dynamic cutoff frequency based on velocity magnitude
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        alpha = self._smoothing_factor(te, cutoff)

        # 3. Filter the signal
        x_hat = alpha * x + (1.0 - alpha) * self._x_prev

        # Update state
        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t

        return x_hat


class OneEuroFilter2D:
    """Dual-channel One-Euro filter for 2D (gx, gy) coordinate vectors."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0) -> None:
        self.x_filter = OneEuroFilter1D(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
        self.y_filter = OneEuroFilter1D(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)

    def reset(self) -> None:
        self.x_filter.reset()
        self.y_filter.reset()

    def filter(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        t = timestamp if timestamp is not None else time.perf_counter()
        filtered_x = self.x_filter.filter(x, t)
        filtered_y = self.y_filter.filter(y, t)
        return filtered_x, filtered_y


class MediaPipeEyeGazeExtractor(EyeGazeExtractorInterface):
    """Produces normalized two-eye gaze measurements with One-Euro temporal filtering."""

    def __init__(self, config: Optional[EyeGazeConfig] = None) -> None:
        super().__init__(config=config or EyeGazeConfig())
        self._initialized = False
        self._running = False
        cfg = self._config
        self._filter = OneEuroFilter2D(
            min_cutoff=getattr(cfg, "one_euro_min_cutoff", 1.0),
            beta=getattr(cfg, "one_euro_beta", 0.007),
            d_cutoff=getattr(cfg, "one_euro_d_cutoff", 1.0),
        )
        self._last_valid_raw_gx: Optional[float] = None
        self._last_valid_raw_gy: Optional[float] = None

    def initialize(self) -> None:
        self._filter.reset()
        self._last_valid_raw_gx = None
        self._last_valid_raw_gy = None
        self._initialized = True

    def start(self) -> None:
        if not self._initialized:
            raise EyeGazeStateError("Call initialize() before start().")
        self._filter.reset()
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._filter.reset()

    def cleanup(self) -> None:
        self._running = False
        self._filter.reset()
        self._initialized = False

    def process(self, context: ExamContext) -> None:
        if not self._running or context.current_frame is None:
            return
        frame = context.current_frame
        mesh = context.face_mesh_info
        if mesh.face_count == 0 or not mesh.all_face_landmarks:
            self._filter.reset()
            self._last_valid_raw_gx = None
            self._last_valid_raw_gy = None
            self._write_empty_to_context(context, frame)
            return
        try:
            self._write_to_context(context, self.extract(frame, mesh.all_face_landmarks))
        except EyeTrackingError as exc:
            logger.error("Eye gaze extraction failed on frame %s: %s", frame.frame_id, exc)
            self._filter.reset()
            self._write_empty_to_context(context, frame)

    def extract(self, frame: Frame, all_face_landmarks: List[List[Point]]) -> EyeGazeResult:
        if not self._initialized:
            raise EyeGazeStateError("Extractor is not initialized.")
        started = time.perf_counter()
        frame_time = getattr(frame, "timestamp", None) or time.time()
        required = max(LEFT_IRIS_CENTER_INDEX, RIGHT_IRIS_CENTER_INDEX, LEFT_EYE_LOWER_LID_INDEX, RIGHT_EYE_LOWER_LID_INDEX)
        gazes: List[EyeGaze] = []

        for face_index, landmarks in enumerate(all_face_landmarks):
            if len(landmarks) <= required:
                continue
            try:
                left = _normalized_eye_gaze(
                    landmarks[LEFT_EYE_LEFT_CORNER_INDEX], landmarks[LEFT_EYE_RIGHT_CORNER_INDEX],
                    landmarks[LEFT_EYE_UPPER_LID_INDEX], landmarks[LEFT_EYE_LOWER_LID_INDEX],
                    landmarks[LEFT_IRIS_CENTER_INDEX],
                )
                right = _normalized_eye_gaze(
                    landmarks[RIGHT_EYE_LEFT_CORNER_INDEX], landmarks[RIGHT_EYE_RIGHT_CORNER_INDEX],
                    landmarks[RIGHT_EYE_UPPER_LID_INDEX], landmarks[RIGHT_EYE_LOWER_LID_INDEX],
                    landmarks[RIGHT_IRIS_CENTER_INDEX],
                )
            except IndexError as exc:
                raise InvalidIrisLandmarksError(f"Missing eye landmarks: {exc}") from exc

            valid = [item for item in (left, right) if item is not None]
            if not valid:
                self._filter.reset()
                continue

            # Two-eye disparity and outlier mitigation
            if len(valid) == 2:
                left_gx, left_gy = left[0][0], left[0][1]
                right_gx, right_gy = right[0][0], right[0][1]

                # Check for asymmetric single-eye landmark spike (e.g. reflection / iris jump)
                h_disparity = abs(left_gx - right_gx)
                if h_disparity > 0.50 and self._last_valid_raw_gx is not None:
                    left_dev = abs(left_gx - self._last_valid_raw_gx)
                    right_dev = abs(right_gx - self._last_valid_raw_gx)
                    if left_dev > right_dev + 0.35:
                        # Left eye spiked abnormally -> weight right eye
                        raw_gx = 0.20 * left_gx + 0.80 * right_gx
                        raw_gy = 0.20 * left_gy + 0.80 * right_gy
                        confidence = 0.75
                    elif right_dev > left_dev + 0.35:
                        # Right eye spiked abnormally -> weight left eye
                        raw_gx = 0.80 * left_gx + 0.20 * right_gx
                        raw_gy = 0.80 * left_gy + 0.20 * right_gy
                        confidence = 0.75
                    else:
                        raw_gx = (left_gx + right_gx) / 2.0
                        raw_gy = (left_gy + right_gy) / 2.0
                        confidence = 0.85
                else:
                    raw_gx = (left_gx + right_gx) / 2.0
                    raw_gy = (left_gy + right_gy) / 2.0
                    confidence = 1.0
            else:
                raw_gx = valid[0][0][0]
                raw_gy = valid[0][0][1]
                confidence = 0.65

            self._last_valid_raw_gx = raw_gx
            self._last_valid_raw_gy = raw_gy

            # Apply One-Euro filter on (gx, gy)
            if getattr(self._config, "enable_smoothing", True):
                filtered_gx, filtered_gy = self._filter.filter(raw_gx, raw_gy, frame_time)
            else:
                filtered_gx, filtered_gy = raw_gx, raw_gy

            raw_vector = (raw_gx, raw_gy, 1.0)
            filtered_vector = (filtered_gx, filtered_gy, 1.0)

            left_vec, left_center = left if left is not None else ((0.0, 0.0, 0.0), (0.0, 0.0))
            right_vec, right_center = right if right is not None else ((0.0, 0.0, 0.0), (0.0, 0.0))

            gazes.append(EyeGaze(
                left_gaze_vector=left_vec,
                right_gaze_vector=right_vec,
                combined_gaze_vector=filtered_vector,  # Filtered signal for production decisions
                left_iris_center=IrisCenter(x=landmarks[LEFT_IRIS_CENTER_INDEX][0], y=landmarks[LEFT_IRIS_CENTER_INDEX][1]) if left else None,
                right_iris_center=IrisCenter(x=landmarks[RIGHT_IRIS_CENTER_INDEX][0], y=landmarks[RIGHT_IRIS_CENTER_INDEX][1]) if right else None,
                left_eye_center=EyeCenter(x=left_center[0], y=left_center[1]) if left else None,
                right_eye_center=EyeCenter(x=right_center[0], y=right_center[1]) if right else None,
                confidence=confidence,
                face_index=face_index,
                raw_gaze_vector=raw_vector,
                filtered_gaze_vector=filtered_vector,
            ))

        return EyeGazeResult(
            gazes=gazes,
            frame_id=frame.frame_id,
            processing_timestamp=time.time(),
            processing_time_ms=(time.perf_counter() - started) * 1000.0,
        )

    def _write_to_context(self, context: ExamContext, result: EyeGazeResult) -> None:
        with context.lock():
            eye = context.eye_info
            primary = result.primary_gaze
            if primary:
                eye.gaze_left = primary.left_gaze_vector
                eye.gaze_right = primary.right_gaze_vector
                eye.combined_gaze = primary.combined_gaze_vector  # Filtered production signal
                # Retain raw and filtered vectors for diagnostics
                eye.raw_gaze = getattr(primary, "raw_gaze_vector", primary.combined_gaze_vector)
                eye.filtered_gaze = getattr(primary, "filtered_gaze_vector", primary.combined_gaze_vector)
                eye.left_iris_center = (primary.left_iris_center.x, primary.left_iris_center.y) if primary.left_iris_center else None
                eye.right_iris_center = (primary.right_iris_center.x, primary.right_iris_center.y) if primary.right_iris_center else None
                eye.left_eye_center = (primary.left_eye_center.x, primary.left_eye_center.y) if primary.left_eye_center else None
                eye.right_eye_center = (primary.right_eye_center.x, primary.right_eye_center.y) if primary.right_eye_center else None
                eye.gaze_confidence = primary.confidence
            else:
                eye.gaze_left = eye.gaze_right = eye.combined_gaze = (0.0, 0.0, 0.0)
                eye.raw_gaze = eye.filtered_gaze = (0.0, 0.0, 0.0)
                eye.left_iris_center = eye.right_iris_center = None
                eye.left_eye_center = eye.right_eye_center = None
                eye.gaze_confidence = 0.0
            eye.processing_timestamp = result.processing_timestamp
            eye.processing_time_ms = result.processing_time_ms
            eye.frame_id = result.frame_id
            context.eye_info = eye

    def _write_empty_to_context(self, context: ExamContext, frame: Frame) -> None:
        self._write_to_context(context, EyeGazeResult(gazes=[], frame_id=frame.frame_id, processing_timestamp=time.time(), processing_time_ms=0.0))