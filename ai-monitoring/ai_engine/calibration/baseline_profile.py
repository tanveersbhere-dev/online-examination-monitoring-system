"""
Baseline Profile Data Models for the Adaptive Calibration Engine.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class HeadPoseBaseline:
    average_pitch: float = 0.0
    average_yaw: float = 0.0
    average_roll: float = 0.0
    std_pitch: float = 1.0
    std_yaw: float = 1.0
    std_roll: float = 1.0

@dataclass
class GazeBaseline:
    center_x: float = 0.0
    center_y: float = 0.0
    horizontal_variance: float = 0.01
    vertical_variance: float = 0.01
    std_x: float = 0.10
    std_y: float = 0.10

@dataclass
class FaceBaseline:
    average_width: float = 0.0
    average_height: float = 0.0
    average_center_x: float = 0.5
    average_center_y: float = 0.5
    average_distance: float = 1.0  # Normalized relative distance

@dataclass
class LightingBaseline:
    brightness: float = 128.0
    contrast: float = 50.0

@dataclass
class TrackingBaseline:
    average_confidence: float = 0.90
    stability: float = 0.95  # [0.0, 1.0]

@dataclass
class BlinkBaseline:
    average_blinks_per_minute: float = 15.0
    average_ear_open: float = 0.28

@dataclass
class CalibrationQualityScore:
    overall_score: float = 100.0  # [0, 100]
    rating: str = "EXCELLENT"     # EXCELLENT | GOOD | FAIR | POOR
    lighting_quality: float = 100.0
    face_visibility_quality: float = 100.0
    tracking_stability_quality: float = 100.0
    detection_confidence_quality: float = 100.0
    motion_stability_quality: float = 100.0
    guidance_messages: List[str] = field(default_factory=list)

@dataclass
class CandidateBaseline:
    head_pose: HeadPoseBaseline = field(default_factory=HeadPoseBaseline)
    gaze: GazeBaseline = field(default_factory=GazeBaseline)
    face: FaceBaseline = field(default_factory=FaceBaseline)
    lighting: LightingBaseline = field(default_factory=LightingBaseline)
    tracking: TrackingBaseline = field(default_factory=TrackingBaseline)
    blink: BlinkBaseline = field(default_factory=BlinkBaseline)
    quality: CalibrationQualityScore = field(default_factory=CalibrationQualityScore)
    samples_collected: int = 0
    stage: str = "INITIALIZING"  # INITIALIZING | WARMING_UP | AUTO_CALIBRATING | READY | UNCERTAIN
    progress_pct: int = 0
    calibration_timestamp: float = 0.0
    last_updated_timestamp: float = 0.0
