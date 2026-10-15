"""
Calibration Engine Processor implementation for AI Monitoring Engine.
Handles automatic, passive, session-specific gaze baseline learning.
"""
import time
import logging
from typing import Optional, Dict, Any, Tuple

from ai_engine.core.exam_context import ExamContext, BoundingBox
from ai_engine.calibration.baseline_profile import CandidateBaseline
from ai_engine.calibration.calibration_metrics import CalibrationMetricsAccumulator

logger = logging.getLogger("ai_engine.calibration.engine")

class CalibrationEngineProcessor:
    """
    Executes automatic session calibration passively in the background.
    Transitions: INITIALIZING -> WARMING_UP (~1.5s) -> AUTO_CALIBRATING (~5-10s) -> READY.
    Accumulates baseline candidate measurements while verifying severe safety rules and stability.
    """
    def __init__(
        self,
        calibration_duration_seconds: float = 5.0,
        warmup_duration_seconds: float = 0.5,
        target_samples: int = 18,
        min_stable_samples_for_early_exit: int = 12
    ) -> None:
        self._initialized: bool = False
        self.calibration_duration_seconds: float = calibration_duration_seconds
        self.warmup_duration_seconds: float = warmup_duration_seconds
        self.target_samples: int = target_samples
        self.min_stable_samples_for_early_exit: int = min_stable_samples_for_early_exit
        self.accumulator: Optional[CalibrationMetricsAccumulator] = None
        self.start_time: float = 0.0
        self.is_completed: bool = False
        self.aborted_reason: Optional[str] = None
        self.last_rejection_reason: Optional[str] = None
        self.stage: str = "INITIALIZING"
        self._last_accepted_yaw: Optional[float] = None
        self._last_accepted_pitch: Optional[float] = None

    def initialize(self) -> None:
        self.accumulator = CalibrationMetricsAccumulator()
        self.start_time = time.time()
        self.is_completed = False
        self.aborted_reason = None
        self.last_rejection_reason = None
        self.stage = "WARMING_UP"
        self._last_accepted_yaw = None
        self._last_accepted_pitch = None
        self._initialized = True
        logger.info("CalibrationEngineProcessor initialized for automatic passive calibration.")

    def start(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.accumulator = CalibrationMetricsAccumulator()
        self.start_time = time.time()
        self.is_completed = False
        self.aborted_reason = None
        self.last_rejection_reason = None
        self.stage = "WARMING_UP"
        self._last_accepted_yaw = None
        self._last_accepted_pitch = None

    def stop(self) -> None:
        pass

    def cleanup(self) -> None:
        self._initialized = False

    @property
    def valid_samples(self) -> int:
        return self.accumulator.face_detected_frames if self.accumulator else 0

    @property
    def progress_percentage(self) -> int:
        if self.is_completed:
            return 100
        if not self.accumulator or self.target_samples <= 0:
            return 0
        return min(100, int((self.accumulator.face_detected_frames / float(self.target_samples)) * 100))

    def _is_valid_initial_calibration_frame(
        self,
        face_detected: bool,
        conf: float,
        face_width: float,
        pose_success: bool,
        yaw: float,
        pitch: float,
        roll: float,
        has_iris: bool,
        gaze_confidence: float,
        g_x: float,
        g_y: float,
        blink: bool,
        ear: float,
        bbox_norm: Optional[Tuple[float, float, float, float]] = None,
        bgr_frame: Optional[Any] = None,
    ) -> bool:
        """
        Camera & Tracking Verification Gate (3-5s pre-exam quality check).
        Verifies face centering, iris tracking, head pose, and lighting stability.
        Does NOT learn a gaze baseline.
        """
        # 1. Face presence & quality
        if not face_detected:
            self.last_rejection_reason = "Face not detected"
            return False
        effective_fw = face_width * 640.0 if (0.0 < face_width <= 1.0) else face_width
        if conf < 0.45 or effective_fw < 35.0:
            self.last_rejection_reason = "Face quality or size too low"
            return False

        # Face centering in camera frame (supports arbitrary camera resolutions e.g. 1280x720, 1920x1080)
        if bbox_norm and len(bbox_norm) >= 4:
            bx, by, bw, bh = bbox_norm[0], bbox_norm[1], bbox_norm[2], bbox_norm[3]
            cx, cy = bx + bw / 2.0, by + bh / 2.0
            if cx > 1.0 or cy > 1.0:
                frame_w = 640.0
                frame_h = 480.0
                if bgr_frame is not None and hasattr(bgr_frame, "shape") and len(bgr_frame.shape) >= 2:
                    frame_h = float(bgr_frame.shape[0])
                    frame_w = float(bgr_frame.shape[1])
                cx /= frame_w
                cy /= frame_h
            if cx < 0.10 or cx > 0.90 or cy < 0.05 or cy > 0.95:
                self.last_rejection_reason = "Face not centered in frame"
                return False

        # 2. Head pose: must succeed and candidate sit facing camera
        if not pose_success:
            self.last_rejection_reason = "Head pose tracking failed"
            return False

        roll_deviation = min(abs(roll), abs(abs(roll) - 180.0))
        if abs(yaw) > 30.0:
            self.last_rejection_reason = "Head turned away horizontally"
            return False
        if abs(yaw) > 18.0 and abs(g_x) < 0.05:
            self.last_rejection_reason = "Head turned away horizontally"
            return False
        if pitch < -12.0:
            self.last_rejection_reason = "Head tilted upward away from screen"
            return False
        if pitch > 22.0:
            self.last_rejection_reason = "Head tilted downward away from screen"
            return False
        if roll_deviation > 25.0:
            self.last_rejection_reason = "Head tilted sideways"
            return False

        # 3. Eye gaze: iris must be visible and gaze reasonably toward camera/screen
        if not has_iris:
            self.last_rejection_reason = "Eyes/iris not visible"
            return False
        if gaze_confidence < 0.35:
            self.last_rejection_reason = "Gaze tracking confidence low"
            return False
        if abs(g_x) > 0.22:
            self.last_rejection_reason = "Gaze directed away horizontally"
            return False
        if g_y < -0.14:
            self.last_rejection_reason = "Gaze directed upward off-screen"
            return False
        if g_y > 0.22:
            self.last_rejection_reason = "Gaze directed downward off-screen"
            return False

        # 4. Blink / eye closure
        if blink or ear < 0.14:
            self.last_rejection_reason = "Blinking or eyes closed"
            return False

        # 5. Lighting verification (if real camera frame available)
        if bgr_frame is not None and hasattr(bgr_frame, "mean"):
            import numpy as np
            mean_brightness = float(np.mean(bgr_frame))
            if 0.0 < mean_brightness < 15.0 or mean_brightness > 245.0:
                self.last_rejection_reason = "Lighting too dark or overexposed"
                return False

        self.last_rejection_reason = None
        return True

    def process(self, context: ExamContext) -> None:
        if not self._initialized or self.accumulator is None:
            return

        current_time = time.time()
        elapsed = current_time - self.start_time

        # Check severe safety abort conditions during verification
        fi = getattr(context, "face_info", None)
        face_count = getattr(fi, "face_count", 0) if fi else 0
        if face_count > 1:
            self.aborted_reason = "Multiple faces detected during verification."
            self.last_rejection_reason = self.aborted_reason
            logger.warning(f"Verification aborted: {self.aborted_reason}")
            return

        oi = getattr(context, "object_info", None)
        tracked = getattr(oi, "tracked_objects", []) or getattr(oi, "filtered_detections", []) if oi else []
        for obj in tracked:
            otype = getattr(obj.object_type, "name", str(obj.object_type))
            if otype in ["CELL_PHONE", "BOOK", "TABLET"]:
                conf = float(getattr(obj, "confidence", 1.0))
                if conf >= 0.65:
                    self.aborted_reason = f"Prohibited object '{otype}' detected during verification."
                    self.last_rejection_reason = self.aborted_reason
                    logger.warning(f"Verification aborted: {self.aborted_reason}")
                    return

        # Track consecutive face absence during verification
        if not fi or not getattr(fi, "face_detected", False) or getattr(fi, "presence_state", "PRESENT") == "MISSING":
            self._consecutive_missing_calibration_frames = getattr(self, "_consecutive_missing_calibration_frames", 0) + 1
            if self._consecutive_missing_calibration_frames > 45:
                self.aborted_reason = "Face missing for more than 3 seconds during camera verification."
                self.last_rejection_reason = self.aborted_reason
                logger.warning(f"Verification aborted: {self.aborted_reason}")
                return
            else:
                self.last_rejection_reason = "Face not detected"
        else:
            self._consecutive_missing_calibration_frames = 0

        self.aborted_reason = None

        # Update stage based on elapsed time or early warmup frames
        if elapsed < self.warmup_duration_seconds and getattr(self, "_warmup_frame_count", 0) < 3:
            self._warmup_frame_count = getattr(self, "_warmup_frame_count", 0) + 1
            self.stage = "WARMING_UP"
            return
        elif not self.is_completed:
            self.stage = "AUTO_CALIBRATING"

        # Extract features for sample validation
        face_detected = getattr(fi, "face_detected", False) if fi else False
        conf = getattr(fi, "confidence", 0.0) if fi else 0.0
        bbox = getattr(fi, "bbox", None) if fi else None
        hp = getattr(context, "head_pose_info", None)
        yaw = getattr(hp, "yaw", 0.0) if hp else 0.0
        pitch = getattr(hp, "pitch", 0.0) if hp else 0.0
        roll = getattr(hp, "roll", 0.0) if hp else 0.0
        ei = getattr(context, "eye_info", None)
        cg = getattr(ei, "combined_gaze", (0.0, 0.0, 0.0)) if ei else (0.0, 0.0, 0.0)
        ear = getattr(ei, "average_ear", 0.0) if ei else 0.0
        blink = getattr(ei, "blink_detected", False) if ei else False
        gaze_confidence = float(getattr(ei, "gaze_confidence", 0.0)) if ei else 0.0
        pose_success = bool(getattr(hp, "success", False)) if hp else False
        face_width = float(bbox.width) if isinstance(bbox, BoundingBox) else (float(bbox[2]) if hasattr(bbox, "__len__") and len(bbox) >= 3 else 0.0)
        has_iris = bool(getattr(ei, "left_iris_center", None) or getattr(ei, "right_iris_center", None)) if ei else False

        g_x = cg[0] if isinstance(cg, (tuple, list)) and len(cg) > 0 else 0.0
        g_y = cg[1] if isinstance(cg, (tuple, list)) and len(cg) > 1 else 0.0

        frame_obj = getattr(context, "current_frame", None)
        bgr = getattr(frame_obj, "original_frame", None) if frame_obj else None

        bbox_norm = None
        if isinstance(bbox, BoundingBox):
            bbox_norm = (bbox.x, bbox.y, bbox.width, bbox.height)
        elif hasattr(bbox, "__len__") and len(bbox) >= 4:
            bbox_norm = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))

        # Verification quality gate
        if not self._is_valid_initial_calibration_frame(
            face_detected=face_detected,
            conf=conf,
            face_width=face_width,
            pose_success=pose_success,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            has_iris=has_iris,
            gaze_confidence=gaze_confidence,
            g_x=g_x,
            g_y=g_y,
            blink=blink,
            ear=ear,
            bbox_norm=bbox_norm,
            bgr_frame=bgr
        ):
            return

        # Check motion stability (reject sudden head jerks during verification)
        if self._last_accepted_yaw is not None and self._last_accepted_pitch is not None:
            if abs(yaw - self._last_accepted_yaw) > 20.0 or abs(pitch - self._last_accepted_pitch) > 20.0:
                self._last_accepted_yaw = 0.8 * self._last_accepted_yaw + 0.2 * yaw
                self._last_accepted_pitch = 0.8 * self._last_accepted_pitch + 0.2 * pitch
                self.last_rejection_reason = "Sudden head movement"
                return

        self.last_rejection_reason = None
        self._last_accepted_yaw = yaw
        self._last_accepted_pitch = pitch

        if isinstance(bbox, BoundingBox):
            bbox_list = [bbox.x, bbox.y, bbox.width, bbox.height]
        elif hasattr(bbox, "__iter__"):
            bbox_list = list(bbox)
        else:
            bbox_list = None

        self.accumulator.add_frame(
            face_detected=face_detected,
            face_confidence=conf,
            bbox=bbox_list,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            gaze_vector=list(cg) if cg else None,
            ear=ear,
            blink_detected=blink,
            bgr_frame=bgr,
        )

        collected = self.accumulator.face_detected_frames
        has_min_samples = collected >= self.min_stable_samples_for_early_exit

        is_early_stable = False
        if (
            has_min_samples
            and elapsed >= 1.2
            and self.aborted_reason is None
            and len(self.accumulator.yaws) >= self.min_stable_samples_for_early_exit
            and len(self.accumulator.pitches) >= self.min_stable_samples_for_early_exit
        ):
            import numpy as np
            window = self.min_stable_samples_for_early_exit
            y_std = float(np.std(self.accumulator.yaws[-window:]))
            p_std = float(np.std(self.accumulator.pitches[-window:]))
            if y_std <= 3.5 and p_std <= 3.5:
                is_early_stable = True

        if is_early_stable or \
           (collected >= self.target_samples) or \
           (elapsed >= self.calibration_duration_seconds and collected >= 8):
            self.is_completed = True
            self.stage = "READY"
            logger.info(f"Camera & tracking verification completed: {collected} valid frames verified in {elapsed:.1f}s.")

    def finalize_baseline(self) -> CandidateBaseline:
        """
        Camera & Tracking Verification complete.
        Returns a verification baseline with ZERO biases.
        CRITICAL: We do NOT learn or store the student's gaze as screen baseline.
        The system is calibration-free.
        """
        from ai_engine.calibration.baseline_profile import (
            CandidateBaseline, HeadPoseBaseline, GazeBaseline, CalibrationQualityScore
        )
        collected = self.accumulator.face_detected_frames if self.accumulator else 0
        baseline = CandidateBaseline(
            head_pose=HeadPoseBaseline(
                average_yaw=0.0,
                average_pitch=0.0,
                average_roll=0.0,
                std_yaw=1.0,
                std_pitch=1.0,
                std_roll=1.0
            ),
            gaze=GazeBaseline(
                center_x=0.0,
                center_y=0.0,
                std_x=0.04,
                std_y=0.04
            ),
            quality=CalibrationQualityScore(
                overall_score=100.0,
                rating="VERIFIED"
            ),
            stage="READY",
            progress_pct=100,
            samples_collected=collected
        )
        return baseline
