"""
Calibration Metrics Accumulator for the Adaptive Calibration Engine.
"""
import math
import numpy as np
from typing import List, Dict, Any, Optional
from ai_engine.calibration.baseline_profile import (
    CandidateBaseline, HeadPoseBaseline, GazeBaseline, FaceBaseline,
    LightingBaseline, TrackingBaseline, BlinkBaseline, CalibrationQualityScore
)

class CalibrationMetricsAccumulator:
    """
    Accumulates frame observations during the calibration window and computes CandidateBaseline.
    """
    def __init__(self) -> None:
        self.yaws: List[float] = []
        self.pitches: List[float] = []
        self.rolls: List[float] = []
        self.gaze_xs: List[float] = []
        self.gaze_ys: List[float] = []
        self.face_widths: List[float] = []
        self.face_heights: List[float] = []
        self.face_center_xs: List[float] = []
        self.face_center_ys: List[float] = []
        self.confidences: List[float] = []
        self.brightnesses: List[float] = []
        self.contrasts: List[float] = []
        self.ears: List[float] = []
        self.blink_count: int = 0
        self.face_detected_frames: int = 0
        self.total_frames: int = 0
        self.severe_event_detected: bool = False
        self.severe_event_reason: Optional[str] = None

    def add_frame(
        self,
        face_detected: bool,
        face_confidence: float = 0.0,
        bbox: Optional[List[float]] = None,
        yaw: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
        gaze_vector: Optional[List[float]] = None,
        ear: float = 0.0,
        blink_detected: bool = False,
        bgr_frame: Optional[np.ndarray] = None,
        severe_event: bool = False,
        severe_reason: Optional[str] = None
    ) -> None:
        self.total_frames += 1

        if severe_event:
            self.severe_event_detected = True
            self.severe_event_reason = severe_reason

        if not face_detected or bbox is None:
            return

        if hasattr(bbox, "x"):
            x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height
        elif hasattr(bbox, "__len__") and len(bbox) >= 4:
            x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        else:
            return

        self.face_detected_frames += 1
        self.confidences.append(face_confidence)
        self.face_widths.append(w)
        self.face_heights.append(h)
        self.face_center_xs.append(x + w / 2.0)
        self.face_center_ys.append(y + h / 2.0)

        self.yaws.append(yaw)
        self.pitches.append(pitch)
        self.rolls.append(roll)

        if gaze_vector and len(gaze_vector) >= 2:
            self.gaze_xs.append(gaze_vector[0])
            self.gaze_ys.append(gaze_vector[1])

        if ear > 0.0:
            self.ears.append(ear)
        if blink_detected:
            self.blink_count += 1

        if bgr_frame is not None and bgr_frame.size > 0:
            try:
                gray = bgr_frame if len(bgr_frame.shape) == 2 else bgr_frame[:, :, 0]
                self.brightnesses.append(float(np.mean(gray)))
                self.contrasts.append(float(np.std(gray)))
            except Exception:
                pass

    def compute_baseline(self, timestamp: float) -> CandidateBaseline:
        samples = self.face_detected_frames
        if samples == 0:
            # Fallback empty profile
            quality = CalibrationQualityScore(
                overall_score=0.0,
                rating="POOR",
                guidance_messages=["No face detected during calibration phase."]
            )
            return CandidateBaseline(quality=quality, calibration_timestamp=timestamp, last_updated_timestamp=timestamp)

        # Head Pose (Median & Dispersion with Safe Physical Clamping)
        mean_yaw = float(np.median(self.yaws)) if self.yaws else 0.0
        mean_pitch = float(np.median(self.pitches)) if self.pitches else 0.0
        mean_roll = float(np.median(self.rolls)) if self.rolls else 0.0

        # Physical safety clamp: enforce valid camera-centered viewing cone
        mean_yaw = float(max(-14.0, min(14.0, mean_yaw)))
        mean_pitch = float(max(-16.0, min(6.0, mean_pitch)))  # Upward pitch baseline strictly clamped <= +6.0°
        mean_roll = float(max(-15.0, min(15.0, mean_roll)))

        std_yaw = float(1.4826 * np.median(np.abs(np.asarray(self.yaws) - mean_yaw))) if len(self.yaws) > 1 else 1.0
        std_pitch = float(1.4826 * np.median(np.abs(np.asarray(self.pitches) - mean_pitch))) if len(self.pitches) > 1 else 1.0
        std_roll = float(1.4826 * np.median(np.abs(np.asarray(self.rolls) - mean_roll))) if len(self.rolls) > 1 else 1.0

        head_pose = HeadPoseBaseline(
            average_pitch=mean_pitch,
            average_yaw=mean_yaw,
            average_roll=mean_roll,
            std_pitch=max(std_pitch, 0.5),
            std_yaw=max(std_yaw, 0.5),
            std_roll=max(std_roll, 0.5)
        )

        # Gaze (Median & Dispersion with Safe Physical Clamping)
        g_center_x = float(np.median(self.gaze_xs)) if self.gaze_xs else 0.0
        g_center_y = float(np.median(self.gaze_ys)) if self.gaze_ys else 0.0

        # Physical safety clamp: enforce valid on-screen iris cone
        g_center_x = float(max(-0.20, min(0.20, g_center_x)))
        g_center_y = float(max(-0.12, min(0.20, g_center_y)))  # Upward gaze baseline strictly clamped >= -0.12

        g_var_x = float((1.4826 * np.median(np.abs(np.asarray(self.gaze_xs) - g_center_x))) ** 2) if len(self.gaze_xs) > 1 else 0.01
        g_var_y = float((1.4826 * np.median(np.abs(np.asarray(self.gaze_ys) - g_center_y))) ** 2) if len(self.gaze_ys) > 1 else 0.01
        std_gx = float(math.sqrt(max(g_var_x, 0.001)))
        std_gy = float(math.sqrt(max(g_var_y, 0.001)))

        gaze = GazeBaseline(
            center_x=g_center_x,
            center_y=g_center_y,
            horizontal_variance=max(g_var_x, 0.001),
            vertical_variance=max(g_var_y, 0.001),
            std_x=std_gx,
            std_y=std_gy
        )

        # Face
        f_w = float(np.mean(self.face_widths)) if self.face_widths else 100.0
        f_h = float(np.mean(self.face_heights)) if self.face_heights else 100.0
        f_cx = float(np.mean(self.face_center_xs)) if self.face_center_xs else 320.0
        f_cy = float(np.mean(self.face_center_ys)) if self.face_center_ys else 240.0
        dist = float(640.0 / max(f_w, 1.0))  # Relative distance inverse to face width

        face = FaceBaseline(
            average_width=f_w,
            average_height=f_h,
            average_center_x=f_cx,
            average_center_y=f_cy,
            average_distance=dist
        )

        # Lighting
        bright = float(np.mean(self.brightnesses)) if self.brightnesses else 120.0
        cont = float(np.mean(self.contrasts)) if self.contrasts else 45.0
        lighting = LightingBaseline(brightness=bright, contrast=cont)

        # Tracking & Confidence
        avg_conf = float(np.mean(self.confidences)) if self.confidences else 0.90
        detection_ratio = float(self.face_detected_frames) / max(self.total_frames, 1)
        tracking = TrackingBaseline(average_confidence=avg_conf, stability=detection_ratio)

        # Blink
        dur_sec = max((self.total_frames * 0.1), 1.0)
        blinks_per_min = (self.blink_count / dur_sec) * 60.0
        avg_ear = float(np.mean(self.ears)) if self.ears else 0.28
        blink = BlinkBaseline(average_blinks_per_minute=blinks_per_min, average_ear_open=avg_ear)

        # Quality Computation
        quality = self._compute_quality(
            bright=bright,
            cont=cont,
            detection_ratio=detection_ratio,
            avg_conf=avg_conf,
            std_yaw=std_yaw,
            std_pitch=std_pitch,
            face_width=f_w
        )

        return CandidateBaseline(
            head_pose=head_pose,
            gaze=gaze,
            face=face,
            lighting=lighting,
            tracking=tracking,
            blink=blink,
            quality=quality,
            samples_collected=samples,
            stage="READY",
            progress_pct=100,
            calibration_timestamp=timestamp,
            last_updated_timestamp=timestamp
        )

    def _compute_quality(
        self,
        bright: float,
        cont: float,
        detection_ratio: float,
        avg_conf: float,
        std_yaw: float,
        std_pitch: float,
        face_width: float
    ) -> CalibrationQualityScore:
        guidance = []

        # 1. Lighting score (ideal brightness 80..180, contrast > 25)
        if bright < 60:
            lighting_q = 40.0
            guidance.append("Lighting is too dark. Please move to a brighter environment.")
        elif bright > 210:
            lighting_q = 50.0
            guidance.append("Lighting is overexposed. Avoid direct glare into camera.")
        else:
            lighting_q = 100.0

        if cont < 20:
            lighting_q = min(lighting_q, 50.0)
            guidance.append("Low image contrast. Adjust light source.")

        # 2. Face Visibility
        if detection_ratio < 0.70:
            vis_q = 40.0
            guidance.append("Face detection intermittent. Center face and keep clear of obstructions.")
        else:
            vis_q = 100.0

        if face_width < 60:
            vis_q = min(vis_q, 50.0)
            guidance.append("Face is too far away. Move closer to the webcam.")

        # 3. Motion Stability
        if std_yaw > 10.0 or std_pitch > 8.0:
            motion_q = 50.0
            guidance.append("Excessive head movement during calibration. Keep head still.")
        else:
            motion_q = 100.0

        # 4. Tracking Stability & Confidence
        track_q = min(detection_ratio * 100.0, 100.0)
        conf_q = min(avg_conf * 100.0, 100.0)

        overall = (lighting_q * 0.2) + (vis_q * 0.25) + (motion_q * 0.25) + (track_q * 0.15) + (conf_q * 0.15)

        if overall >= 85.0:
            rating = "EXCELLENT"
        elif overall >= 70.0:
            rating = "GOOD"
        elif overall >= 50.0:
            rating = "FAIR"
        else:
            rating = "POOR"

        return CalibrationQualityScore(
            overall_score=round(overall, 1),
            rating=rating,
            lighting_quality=round(lighting_q, 1),
            face_visibility_quality=round(vis_q, 1),
            tracking_stability_quality=round(track_q, 1),
            detection_confidence_quality=round(conf_q, 1),
            motion_stability_quality=round(motion_q, 1),
            guidance_messages=guidance
        )
