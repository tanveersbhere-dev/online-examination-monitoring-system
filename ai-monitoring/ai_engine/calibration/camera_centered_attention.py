"""
Camera-Centered Attention Processor for AI Monitoring Engine.
"""

import math
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

from ai_engine.intelligence.rule_engine.models import CameraCenteredAttentionConfig

logger = logging.getLogger("ai_engine.calibration.camera_centered")


@dataclass
class CameraCenteredAttentionResult:
    state: str
    confidence: float
    reason: str
    combined_score: float
    eye_score: float
    head_support: float
    unified_ray_h_deg: float
    unified_ray_v_deg: float
    compensating_gaze: bool
    landmark_quality: float


class CameraCenteredAttentionProcessor:
    def __init__(self, config: Optional[CameraCenteredAttentionConfig] = None) -> None:
        self.config = config or CameraCenteredAttentionConfig()

    def process(
        self,
        raw_yaw: float,
        raw_pitch: float,
        raw_roll: float,
        head_pose_success: bool,
        gaze_x: float,
        gaze_y: float,
        has_iris: bool,
        gaze_confidence: float,
        face_confidence: float,
        face_detected: bool,
        calib_bias_yaw: float = 0.0,
        calib_bias_pitch: float = 0.0,
        calib_bias_gx: float = 0.0,
        calib_bias_gy: float = 0.0,
    ) -> CameraCenteredAttentionResult:
        cfg = self.config

        if not face_detected:
            return CameraCenteredAttentionResult(
                state="UNCERTAIN", confidence=0.0, reason="FACE_NOT_DETECTED",
                combined_score=0.0, eye_score=0.0, head_support=0.0,
                unified_ray_h_deg=0.0, unified_ray_v_deg=0.0,
                compensating_gaze=False, landmark_quality=0.0,
            )

        landmark_quality = min(face_confidence, gaze_confidence) if (face_confidence > 0 and gaze_confidence > 0) else max(face_confidence, gaze_confidence)
        eyes_valid = has_iris and gaze_confidence >= cfg.min_landmark_confidence
        pose_valid = head_pose_success and face_confidence >= 0.40

        if not pose_valid and not eyes_valid:
            return CameraCenteredAttentionResult(
                state="UNCERTAIN", confidence=0.0, reason="LOW_QUALITY_OR_TRACKING_LOST",
                combined_score=0.0, eye_score=0.0, head_support=0.0,
                unified_ray_h_deg=0.0, unified_ray_v_deg=0.0,
                compensating_gaze=False, landmark_quality=round(landmark_quality, 4),
            )

        bounded_bias_yaw = max(-cfg.max_allowable_yaw_bias_deg, min(cfg.max_allowable_yaw_bias_deg, calib_bias_yaw))
        bounded_bias_pitch = max(-cfg.max_allowable_pitch_bias_deg, min(cfg.max_allowable_pitch_bias_deg, calib_bias_pitch))
        bounded_bias_gx = max(-cfg.max_allowable_gaze_bias_x, min(cfg.max_allowable_gaze_bias_x, calib_bias_gx))
        bounded_bias_gy = max(-cfg.max_allowable_gaze_bias_y, min(cfg.max_allowable_gaze_bias_y, calib_bias_gy))

        adj_yaw = raw_yaw - bounded_bias_yaw
        adj_pitch = raw_pitch - bounded_bias_pitch
        adj_gx = gaze_x - bounded_bias_gx
        adj_gy = gaze_y - bounded_bias_gy

        abs_yaw = abs(adj_yaw)
        is_extreme_side_turn = abs_yaw >= 35.0
        pitch_down_mag = -adj_pitch if adj_pitch < 0.0 else (adj_pitch if adj_pitch >= 30.0 and adj_gy > 0.15 else 0.0)
        is_extreme_pitch = pitch_down_mag >= 30.0

        if is_extreme_side_turn or is_extreme_pitch:
            if is_extreme_side_turn:
                direction_state = "RIGHT" if adj_yaw > 0 else "LEFT"
                extreme_excess = (abs_yaw - cfg.horizontal_screen_limit_deg) / cfg.horizontal_excess_range_deg
            else:
                direction_state = "DOWN"
                extreme_excess = (pitch_down_mag - cfg.downward_screen_limit_deg) / cfg.downward_excess_range_deg

            head_score = max(0.0, min(1.0, extreme_excess))
            effective_quality = face_confidence if not eyes_valid else landmark_quality
            conf = effective_quality * (0.60 + 0.40 * head_score)
            return CameraCenteredAttentionResult(
                state=direction_state, confidence=round(conf, 4),
                reason=f"CAMERA_CENTERED_EXTREME_HEAD_{direction_state}",
                combined_score=round(head_score, 4), eye_score=0.0,
                head_support=round(head_score, 4), unified_ray_h_deg=round(adj_yaw, 2),
                unified_ray_v_deg=round(adj_pitch, 2), compensating_gaze=False,
                landmark_quality=round(effective_quality, 4),
            )

        compensating_h = False
        if eyes_valid and pose_valid:
            if abs_yaw >= 10.0 and (adj_yaw * adj_gx < -0.01):
                effective_h_deg = adj_yaw + adj_gx * cfg.eye_to_angle_x
                if abs(effective_h_deg) <= cfg.horizontal_screen_limit_deg:
                    compensating_h = True

        pitch_v = -adj_pitch if adj_pitch < 0.0 else (adj_pitch if adj_pitch > 15.0 and adj_gy > 0.15 else 0.0)
        gaze_v = max(adj_gy, -adj_gy if adj_pitch < -8.0 else 0.0)
        if eyes_valid and pose_valid:
            phi_h = adj_yaw + adj_gx * cfg.eye_to_angle_x
            phi_v = pitch_v + gaze_v * cfg.eye_to_angle_y
        elif eyes_valid and not pose_valid:
            phi_h = adj_gx * cfg.eye_to_angle_x
            phi_v = max(adj_gy, 0.0) * cfg.eye_to_angle_y
        elif pose_valid and not eyes_valid:
            phi_h = adj_yaw
            phi_v = pitch_v
        else:
            phi_h = 0.0
            phi_v = 0.0

        h_excess = 0.0
        h_dir = "CENTER"
        if phi_h > cfg.horizontal_screen_limit_deg:
            h_excess = phi_h - cfg.horizontal_screen_limit_deg
            h_dir = "RIGHT"
        elif phi_h < -cfg.horizontal_screen_limit_deg:
            h_excess = -phi_h - cfg.horizontal_screen_limit_deg
            h_dir = "LEFT"

        v_excess = 0.0
        v_dir = "CENTER"
        if phi_v > cfg.downward_screen_limit_deg:
            v_excess = phi_v - cfg.downward_screen_limit_deg
            v_dir = "DOWN"

        score_h = max(0.0, min(1.0, h_excess / cfg.horizontal_excess_range_deg))
        score_v = max(0.0, min(1.0, v_excess / cfg.downward_excess_range_deg))

        if compensating_h and h_excess > 0:
            score_h = 0.0
            h_dir = "CENTER"

        eye_excess_h = max(0.0, abs(adj_gx) - 0.22) if eyes_valid else 0.0
        eye_score = max(0.0, min(1.0, eye_excess_h / 0.15)) if eyes_valid else 0.0
        head_excess_h = max(0.0, abs_yaw - cfg.horizontal_screen_limit_deg) if pose_valid else 0.0
        head_support = max(0.0, min(1.0, head_excess_h / cfg.horizontal_excess_range_deg)) if pose_valid else 0.0

        combined_score = max(score_h, score_v)
        threshold = cfg.off_screen_confidence_threshold

        if combined_score >= threshold:
            if score_h >= score_v:
                state = h_dir
                reason = f"CAMERA_CENTERED_LOOKING_{h_dir}"
                conf = landmark_quality * (0.60 + 0.40 * combined_score) * 0.90
            else:
                state = v_dir
                reason = f"CAMERA_CENTERED_LOOKING_{v_dir}"
                conf = landmark_quality * (0.60 + 0.40 * combined_score)
        elif combined_score <= 0.15:
            state = "CENTER"
            reason = "WITHIN_AUTHORIZED_CAMERA_SCREEN_FRUSTUM"
            conf = landmark_quality
        else:
            state = "CENTER"
            reason = "TRANSITIONAL_SCREEN_ATTENTION"
            conf = landmark_quality * (1.0 - combined_score)


        return CameraCenteredAttentionResult(
            state=state, confidence=round(conf, 4), reason=reason,
            combined_score=round(combined_score, 4), eye_score=round(eye_score, 4),
            head_support=round(head_support, 4), unified_ray_h_deg=round(phi_h, 2),
            unified_ray_v_deg=round(phi_v, 2), compensating_gaze=compensating_h,
            landmark_quality=round(landmark_quality, 4),
        )
