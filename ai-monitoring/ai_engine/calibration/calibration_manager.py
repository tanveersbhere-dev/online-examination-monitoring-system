"""
Calibration Manager and Session Drift Adapter for the Adaptive Calibration Engine.
Manages automatic passive session calibration, dynamic screen tolerances, and strict anti-drift protection.
"""
import time
import math
import logging
from typing import Dict, Any, Optional, Tuple

from ai_engine.calibration.baseline_profile import (
    CandidateBaseline, HeadPoseBaseline, GazeBaseline, CalibrationQualityScore
)
from ai_engine.core.exam_context import ExamContext, BoundingBox

logger = logging.getLogger("ai_engine.calibration.manager")

class CalibrationManager:
    """
    Manages session calibration lifecycle, calculates candidate runtime deviations,
    applies slow posture drift adaptation (EMA) ONLY during confirmed safe ON_SCREEN states,
    and triggers recalibration resets.
    """
    def __init__(self, ema_alpha: float = 0.005) -> None:
        self.status: str = "INITIALIZING"  # INITIALIZING | WARMING_UP | AUTO_CALIBRATING | CALIBRATED | READY | FAILED | RECALIBRATION_REQUIRED
        self.stage: str = "INITIALIZING"
        self.baseline: Optional[CandidateBaseline] = None
        self.quality_score: Optional[CalibrationQualityScore] = None
        self.ema_alpha: float = ema_alpha  # Exponential Moving Average factor for slow drift
        self.last_reset_reason: Optional[str] = None
        self.last_rejection_reason: Optional[str] = None
        self.consecutive_tracking_losses: int = 0
        self.progress_pct: int = 0
        self.valid_samples: int = 0
        self.target_samples: int = 20

    def start_calibration(self) -> None:
        self.status = "AUTO_CALIBRATING"
        self.stage = "AUTO_CALIBRATING"
        self.baseline = None
        self.quality_score = None
        self.last_reset_reason = None
        self.last_rejection_reason = None
        self.consecutive_tracking_losses = 0
        self.progress_pct = 0
        self.valid_samples = 0
        logger.info("[CalibrationManager] Automatic session calibration started.")

    def update_auto_progress(
        self,
        stage: str,
        progress_pct: int,
        valid_samples: int,
        target_samples: int,
        last_rejection_reason: Optional[str] = None
    ) -> None:
        self.stage = stage
        if stage in ("INITIALIZING", "WARMING_UP", "AUTO_CALIBRATING"):
            self.status = stage
        self.progress_pct = progress_pct
        self.valid_samples = valid_samples
        self.target_samples = target_samples
        self.last_rejection_reason = last_rejection_reason

    def complete_calibration(self, baseline: CandidateBaseline) -> None:
        self.baseline = baseline
        self.quality_score = baseline.quality
        self.valid_samples = baseline.samples_collected
        self.progress_pct = 100
        if baseline.quality and (baseline.quality.rating == "POOR" or baseline.quality.overall_score < 40.0):
            self.status = "FAILED"
            self.stage = "FAILED"
            self.last_reset_reason = "Calibration quality score POOR"
            return
        self.status = "CALIBRATED"
        self.stage = "READY"
        logger.info(f"[CalibrationManager] Status -> READY/CALIBRATED (Quality={baseline.quality.rating if baseline.quality else 'N/A'}, Score={baseline.quality.overall_score if baseline.quality else 0}%, Samples={baseline.samples_collected})")

    def fail_calibration(self, reason: str) -> None:
        self.status = "FAILED"
        self.stage = "FAILED"
        self.last_reset_reason = reason
        logger.warning(f"[CalibrationManager] Calibration failed: {reason}")

    def request_recalibration(self, reason: str) -> None:
        self.status = "RECALIBRATION_REQUIRED"
        self.stage = "RECALIBRATION_REQUIRED"
        self.last_reset_reason = reason
        self.progress_pct = 0
        self.valid_samples = 0
        logger.info(f"[CalibrationManager] Recalibration requested: {reason}")

    def evaluate_runtime_frame(self, context: ExamContext) -> Dict[str, Any]:
        """
        Calculates deltas/deviations relative to CandidateBaseline during exam monitoring.
        Applies slow posture drift adaptation (EMA) strictly when safe (anti-drift protected).
        """
        is_ready = self.status in ("CALIBRATED", "READY") and self.baseline is not None

        fi = getattr(context, "face_info", None)
        hp = getattr(context, "head_pose_info", None)
        ei = getattr(context, "eye_info", None)

        face_detected = getattr(fi, "face_detected", False) if fi else False

        # Tracking refresh condition: Refresh tracking ONLY if face remains continuously absent triggers (> 10s)
        face_absent = (
            not face_detected
            or getattr(fi, "presence_state", "PRESENT") in ("MISSING", "ABSENT")
            or not getattr(fi, "face_present", True)
        )
        if face_absent:
            if getattr(self, "_calibrated_absence_start_time", 0.0) <= 0.0:
                self._calibrated_absence_start_time = time.time()
            current_absence = time.time() - self._calibrated_absence_start_time
            if current_absence > 10.0 and is_ready:
                self._calibrated_absence_start_time = 0.0
                self.request_recalibration("Extended continuous face loss (> 10s)")
        else:
            self._calibrated_absence_start_time = 0.0

        # 1. Compute Head Pose (and circular angular delta if baseline exists)
        def _angular_delta(curr: float, base: float) -> float:
            return ((curr - base + 180.0) % 360.0) - 180.0

        curr_yaw = getattr(hp, "yaw", 0.0) if hp else 0.0
        curr_pitch = getattr(hp, "pitch", 0.0) if hp else 0.0
        curr_roll = getattr(hp, "roll", 0.0) if hp else 0.0

        base_hp = self.baseline.head_pose if (is_ready and self.baseline) else None
        delta_yaw = _angular_delta(curr_yaw, base_hp.average_yaw) if base_hp else curr_yaw
        delta_pitch = _angular_delta(curr_pitch, base_hp.average_pitch) if base_hp else curr_pitch
        delta_roll = _angular_delta(curr_roll, base_hp.average_roll) if base_hp else curr_roll

        abs_delta_yaw = abs(delta_yaw)
        abs_delta_pitch = abs(delta_pitch)

        # 2. Compute Gaze Deviations (linear normalized coordinates)
        cg = getattr(ei, "combined_gaze", (0.0, 0.0, 0.0)) if ei else (0.0, 0.0, 0.0)
        rg = getattr(ei, "raw_gaze", cg) if ei else cg
        g_x = cg[0] if isinstance(cg, (tuple, list)) and len(cg) > 0 else 0.0
        g_y = cg[1] if isinstance(cg, (tuple, list)) and len(cg) > 1 else 0.0
        raw_gx = rg[0] if isinstance(rg, (tuple, list)) and len(rg) > 0 else g_x
        raw_gy = rg[1] if isinstance(rg, (tuple, list)) and len(rg) > 1 else g_y

        base_gaze = self.baseline.gaze if (is_ready and self.baseline) else None
        delta_gaze_x = (g_x - base_gaze.center_x) if base_gaze else g_x
        delta_gaze_y = (g_y - base_gaze.center_y) if base_gaze else g_y
        gaze_confidence = float(getattr(ei, "gaze_confidence", 0.0)) if ei else 0.0
        has_iris_landmarks = bool(getattr(ei, "left_iris_center", None) or getattr(ei, "right_iris_center", None)) if ei else False
        face_conf = float(getattr(fi, "confidence", 0.0)) if fi else 0.0

        if gaze_confidence > 0.0:
            has_iris = has_iris_landmarks
            landmark_quality = min(face_conf, gaze_confidence)
        else:
            has_iris = has_iris_landmarks
            landmark_quality = face_conf

        # 3. Compute Face Distance / Size Deviation
        bbox = getattr(fi, "bbox", None) if fi else None
        f_w = float(bbox.width) if isinstance(bbox, BoundingBox) else (float(bbox[2]) if hasattr(bbox, "__len__") and len(bbox) >= 3 else 0.0)
        curr_dist = float(640.0 / max(f_w, 1.0)) if f_w > 0 else (self.baseline.face.average_distance if self.baseline else 1.0)
        delta_distance = (curr_dist - self.baseline.face.average_distance) if (self.baseline and self.baseline.face) else 0.0

        if not is_ready or self.baseline is None:
            return {
                "status": self.status,
                "stage": self.stage,
                "progress_pct": self.progress_pct,
                "valid_samples": self.valid_samples,
                "target_samples": self.target_samples,
                "last_rejection_reason": getattr(self, "last_rejection_reason", None),
                "has_baseline": False,
                "face_detected": face_detected,
                "quality_rating": self.stage,
                "quality_score": self.progress_pct,
                "gaze_decision": {
                    "state": "UNCERTAIN",
                    "confidence": 0.0,
                    "reason": f"GAZE_{self.stage}",
                    "combined_score": 0.0,
                    "eye_score": 0.0,
                    "head_support": 0.0,
                },
                "head_pose_deviation": {
                    "delta_yaw": round(delta_yaw, 2),
                    "delta_pitch": round(delta_pitch, 2),
                    "delta_roll": round(delta_roll, 2),
                    "abs_delta_yaw": round(abs_delta_yaw, 2),
                    "abs_delta_pitch": round(abs_delta_pitch, 2),
                },
                "gaze_deviation": {
                    "delta_gaze_x": round(delta_gaze_x, 4),
                    "delta_gaze_y": round(delta_gaze_y, 4),
                },
                "gaze_measurement": {
                    "x": round(g_x, 4),
                    "y": round(g_y, 4),
                    "raw_x": round(raw_gx, 4),
                    "raw_y": round(raw_gy, 4),
                    "filtered_x": round(g_x, 4),
                    "filtered_y": round(g_y, 4),
                    "confidence": round(gaze_confidence, 4),
                    "iris_visible": has_iris,
                    "valid": bool(has_iris and gaze_confidence >= 0.65),
                },
                "landmark_quality": round(landmark_quality, 4),
                "face_distance_deviation": round(delta_distance, 3),
                "baseline_averages": {
                    "yaw": 0.0, "pitch": 0.0, "roll": 0.0,
                    "gaze_x": 0.0, "gaze_y": 0.0,
                    "std_yaw": 1.0, "std_pitch": 1.0,
                    "std_gaze_x": 0.10, "std_gaze_y": 0.10,
                },
            }

        if not face_detected or hp is None or not getattr(hp, "success", False):
            return {
                "status": self.status,
                "stage": self.stage,
                "progress_pct": 100,
                "valid_samples": self.valid_samples,
                "target_samples": self.target_samples,
                "has_baseline": True,
                "face_detected": False,
                "quality_score": self.quality_score.overall_score if self.quality_score else 0.0,
                "quality_rating": self.quality_score.rating if self.quality_score else "UNKNOWN",
                "gaze_decision": {
                    "state": "UNCERTAIN",
                    "confidence": 0.0,
                    "reason": "FACE_NOT_DETECTED",
                    "combined_score": 0.0,
                    "eye_score": 0.0,
                    "head_support": 0.0,
                },
                "head_pose_deviation": {"delta_yaw": 0.0, "delta_pitch": 0.0, "delta_roll": 0.0, "abs_delta_yaw": 0.0, "abs_delta_pitch": 0.0},
                "gaze_deviation": {"delta_gaze_x": 0.0, "delta_gaze_y": 0.0},
                "gaze_measurement": {"x": 0.0, "y": 0.0, "confidence": 0.0, "iris_visible": False, "valid": False},
                "landmark_quality": 0.0,
                "face_distance_deviation": 0.0,
                "baseline_averages": {
                    "yaw": round(base_hp.average_yaw, 2) if base_hp else 0.0,
                    "pitch": round(base_hp.average_pitch, 2) if base_hp else 0.0,
                    "roll": round(base_hp.average_roll, 2) if base_hp else 0.0,
                    "gaze_x": round(base_gaze.center_x, 4) if base_gaze else 0.0,
                    "gaze_y": round(base_gaze.center_y, 4) if base_gaze else 0.0,
                    "std_yaw": round(base_hp.std_yaw, 2) if base_hp else 1.0,
                    "std_pitch": round(base_hp.std_pitch, 2) if base_hp else 1.0,
                    "std_gaze_x": round(getattr(base_gaze, "std_x", 0.10), 4) if base_gaze else 0.10,
                    "std_gaze_y": round(getattr(base_gaze, "std_y", 0.10), 4) if base_gaze else 0.10,
                },
            }

        # 1. Compute Head Pose Deviations using circular angular delta
        def _angular_delta(curr: float, base: float) -> float:
            return ((curr - base + 180.0) % 360.0) - 180.0

        curr_yaw = getattr(hp, "yaw", 0.0)
        curr_pitch = getattr(hp, "pitch", 0.0)
        curr_roll = getattr(hp, "roll", 0.0)

        base_hp = self.baseline.head_pose
        delta_yaw = _angular_delta(curr_yaw, base_hp.average_yaw)
        delta_pitch = _angular_delta(curr_pitch, base_hp.average_pitch)
        delta_roll = _angular_delta(curr_roll, base_hp.average_roll)

        abs_delta_yaw = abs(delta_yaw)
        abs_delta_pitch = abs(delta_pitch)

        # 2. Compute Gaze Deviations (linear normalized coordinates)
        cg = getattr(ei, "combined_gaze", (0.0, 0.0, 0.0)) if ei else (0.0, 0.0, 0.0)
        g_x = cg[0] if isinstance(cg, (tuple, list)) and len(cg) > 0 else 0.0
        g_y = cg[1] if isinstance(cg, (tuple, list)) and len(cg) > 1 else 0.0

        base_gaze = self.baseline.gaze
        delta_gaze_x = g_x - base_gaze.center_x
        delta_gaze_y = g_y - base_gaze.center_y
        gaze_confidence = float(getattr(ei, "gaze_confidence", 0.0)) if ei else 0.0
        has_iris_landmarks = bool(getattr(ei, "left_iris_center", None) or getattr(ei, "right_iris_center", None)) if ei else False
        face_conf = float(getattr(fi, "confidence", 0.0))

        if gaze_confidence > 0.0:
            has_iris = has_iris_landmarks
            landmark_quality = min(face_conf, gaze_confidence)
        else:
            has_iris = True
            landmark_quality = face_conf

        # 3. Compute Face Distance / Size Deviation
        bbox = getattr(fi, "bbox", None) if fi else None
        f_w = float(bbox.width) if isinstance(bbox, BoundingBox) else (float(bbox[2]) if hasattr(bbox, "__len__") and len(bbox) >= 3 else 0.0)
        curr_dist = float(640.0 / max(f_w, 1.0)) if f_w > 0 else self.baseline.face.average_distance
        delta_distance = curr_dist - self.baseline.face.average_distance

        # 4. CAMERA-CENTERED ATTENTION DECISION (Authoritative Source of Truth)
        # Evaluates raw perception signals directly against Camera Optical Axis (0, 0, 1)
        # and applies bounded anatomical baseline bias (|bias_yaw| <= 3.0°, |bias_pitch| <= 4.0°, |bias_gaze| <= 0.04)
        attention_processor = getattr(self, "_attention_processor", None)
        if attention_processor is None:
            from ai_engine.calibration.camera_centered_attention import CameraCenteredAttentionProcessor
            attention_processor = CameraCenteredAttentionProcessor()
            self._attention_processor = attention_processor

        # Anatomical resting bias from calibration baseline
        bias_yaw = float(base_hp.average_yaw) if base_hp else 0.0
        bias_pitch = float(base_hp.average_pitch) if base_hp else 0.0
        bias_gx = float(base_gaze.center_x) if base_gaze else 0.0
        bias_gy = float(base_gaze.center_y) if base_gaze else 0.0

        att_res = attention_processor.process(
            raw_yaw=curr_yaw,
            raw_pitch=curr_pitch,
            raw_roll=curr_roll,
            head_pose_success=getattr(hp, "success", False) if hp else False,
            gaze_x=g_x,
            gaze_y=g_y,
            has_iris=has_iris,
            gaze_confidence=gaze_confidence,
            face_confidence=face_conf,
            face_detected=face_detected,
            calib_bias_yaw=bias_yaw,
            calib_bias_pitch=bias_pitch,
            calib_bias_gx=bias_gx,
            calib_bias_gy=bias_gy,
        )

        # 5. STRICTLY BOUNDED MICRO-DRIFT ADAPTATION (Mode A Only)
        # Mode B Posture Repositioning has been PERMANENTLY REMOVED.
        # Calibration never shifts or redefines the screen center.
        # Micro-drift adaptation only updates tiny anatomical bias when confirmed safely within central cone.
        now = time.time()
        is_in_micro_drift_zone = (
            att_res.state == "CENTER"
            and abs(curr_yaw) <= 8.0
            and -6.0 <= curr_pitch <= 14.0
            and abs(g_x) <= 0.12
            and -0.08 <= g_y <= 0.12
            and landmark_quality >= 0.70
            and has_iris
        )

        if is_in_micro_drift_zone and base_hp and base_gaze:
            # Ultra-slow EMA adjusting only bounded resting anatomical offset (alpha <= 0.0005)
            alpha = min(self.ema_alpha, 0.0005)
            new_yaw = (1.0 - alpha) * base_hp.average_yaw + alpha * curr_yaw
            new_pitch = (1.0 - alpha) * base_hp.average_pitch + alpha * curr_pitch
            new_roll = (1.0 - alpha) * base_hp.average_roll + alpha * curr_roll
            new_gx = (1.0 - alpha) * base_gaze.center_x + alpha * g_x
            new_gy = (1.0 - alpha) * base_gaze.center_y + alpha * g_y

            # Enforce hard anatomical clamps (|yaw| <= 3.0°, |pitch| <= 4.0°, |gx, gy| <= 0.04)
            base_hp.average_yaw = max(-3.0, min(3.0, new_yaw))
            base_hp.average_pitch = max(-4.0, min(4.0, new_pitch))
            base_hp.average_roll = max(-5.0, min(5.0, new_roll))
            base_gaze.center_x = max(-0.04, min(0.04, new_gx))
            base_gaze.center_y = max(-0.04, min(0.04, new_gy))
            self.baseline.last_updated_timestamp = now

        # Stubbed legacy repositioning fields to prevent errors in any external observers
        self._reposition_start_time = 0.0
        self._reposition_yaw_samples = []
        self._reposition_pitch_samples = []
        self._reposition_gx_samples = []
        self._reposition_gy_samples = []

        # Standard dynamic screen tolerances for backward compatibility
        std_gx = getattr(base_gaze, "std_x", 0.04)
        std_gy = getattr(base_gaze, "std_y", 0.04)
        std_y = getattr(base_hp, "std_yaw", 1.0)
        std_p = getattr(base_hp, "std_pitch", 1.0)

        dynamic_tolerances = {
            "horizontal_gaze_tolerance": round(max(0.18, min(0.28, 1.4 * std_gx + 0.16)), 3),
            "horizontal_gaze_tolerance_right": round(max(0.18, min(0.28, 1.4 * std_gx + 0.16)), 3),
            "vertical_gaze_tolerance_up": round(max(0.08, min(0.14, 0.5 * std_gy + 0.07)), 3),
            "vertical_gaze_tolerance_down": round(max(0.16, min(0.26, 0.9 * std_gy + 0.12)), 3),
            "head_yaw_support_deg": round(max(18.0, min(26.0, 2.0 * std_y + 16.0)), 1),
            "head_yaw_support_deg_right": round(max(18.0, min(26.0, 2.0 * std_y + 16.0)), 1),
            "head_pitch_support_deg": round(max(14.0, min(22.0, 2.0 * std_p + 12.0)), 1),
            "head_pitch_up_support_deg": round(max(8.0, min(14.0, 1.0 * std_p + 7.0)), 1),
            "head_pitch_down_support_deg": round(max(16.0, min(26.0, 1.5 * std_p + 14.0)), 1),
        }

        # Format backward-compatible gaze decision dict
        gaze_decision_dict = {
            "state": "ON_SCREEN" if att_res.state == "CENTER" else att_res.state,
            "direction": att_res.state,
            "confidence": att_res.confidence,
            "reason": att_res.reason,
            "combined_score": att_res.combined_score,
            "eye_score": att_res.eye_score,
            "head_support": att_res.head_support,
            "unified_ray_h_deg": att_res.unified_ray_h_deg,
            "unified_ray_v_deg": att_res.unified_ray_v_deg,
            "compensating_gaze": att_res.compensating_gaze,
        }

        return {
            "status": self.status,
            "stage": self.stage,
            "progress_pct": 100,
            "valid_samples": self.valid_samples,
            "target_samples": self.target_samples,
            "has_baseline": True,
            "face_detected": True,
            "quality_rating": self.quality_score.rating if self.quality_score else "EXCELLENT",
            "quality_score": self.quality_score.overall_score if self.quality_score else 100.0,
            "gaze_decision": gaze_decision_dict,
            "head_pose_deviation": {
                "delta_yaw": round(delta_yaw, 2),
                "delta_pitch": round(delta_pitch, 2),
                "delta_roll": round(delta_roll, 2),
                "abs_delta_yaw": round(abs_delta_yaw, 2),
                "abs_delta_pitch": round(abs_delta_pitch, 2),
            },
            "gaze_deviation": {
                "delta_gaze_x": round(delta_gaze_x, 4),
                "delta_gaze_y": round(delta_gaze_y, 4),
            },
            "gaze_measurement": {
                "x": round(g_x, 4),
                "y": round(g_y, 4),
                "raw_x": round(raw_gx, 4),
                "raw_y": round(raw_gy, 4),
                "filtered_x": round(g_x, 4),
                "filtered_y": round(g_y, 4),
                "confidence": round(gaze_confidence, 4),
                "iris_visible": has_iris,
                "valid": bool(has_iris and gaze_confidence >= 0.40),
            },
            "landmark_quality": round(landmark_quality, 4),
            "face_distance_deviation": round(delta_distance, 3),
            "baseline_averages": {
                "yaw": round(base_hp.average_yaw, 2),
                "pitch": round(base_hp.average_pitch, 2),
                "roll": round(base_hp.average_roll, 2),
                "gaze_x": round(base_gaze.center_x, 4),
                "gaze_y": round(base_gaze.center_y, 4),
                "std_yaw": round(base_hp.std_yaw, 2),
                "std_pitch": round(base_hp.std_pitch, 2),
                "std_gaze_x": round(std_gx, 4),
                "std_gaze_y": round(std_gy, 4),
            },
            "dynamic_tolerances": dynamic_tolerances,
        }
