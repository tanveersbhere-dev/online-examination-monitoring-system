"""Data models for Rule Engine."""
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class CameraCenteredAttentionConfig:
    """
    Authoritative configuration for Camera-Centered Attention Tracking.
    """
    horizontal_screen_limit_deg: float = 24.2
    upward_screen_limit_deg: float = 10.0
    downward_screen_limit_deg: float = 26.0
    horizontal_excess_range_deg: float = 12.0
    upward_excess_range_deg: float = 10.0
    downward_excess_range_deg: float = 14.0
    eye_to_angle_x: float = 35.0
    eye_to_angle_y: float = 25.0
    max_allowable_yaw_bias_deg: float = 4.0
    max_allowable_pitch_bias_deg: float = 6.0
    max_allowable_gaze_bias_x: float = 0.04
    max_allowable_gaze_bias_y: float = 0.04
    calib_max_abs_yaw_deg: float = 14.0
    calib_max_pitch_up_deg: float = 12.0
    calib_max_pitch_down_deg: float = 20.0
    calib_max_abs_gaze_x: float = 0.18
    calib_max_abs_gaze_y: float = 0.18
    compensating_gaze_threshold: float = 0.35
    weight_eye: float = 0.65
    weight_head: float = 0.35
    min_landmark_confidence: float = 0.40
    off_screen_confidence_threshold: float = 0.45


@dataclass
class AttentionToleranceConfig:
    """Calibrated iris-relative screen attention tolerances."""
    horizontal_gaze_tolerance: float = 0.231
    horizontal_gaze_tolerance_right: float = 0.231
    vertical_gaze_tolerance_up: float = 0.045
    vertical_gaze_tolerance_down: float = 0.160
    head_yaw_support_deg: float = 22.0
    head_yaw_support_deg_right: float = 22.0
    head_pitch_support_deg: float = 14.0
    min_landmark_confidence: float = 0.60
    min_combined_off_screen_confidence: float = 0.35
    # Opening/recovery time are owned by ViolationManager's existing
    # attention_confirmation_seconds and attention_grace_seconds.
@dataclass
class RuleEngineConfig:
    """Configuration for Rule Engine."""
    # Mapping of rule_id to enable status
    enabled_rules: Dict[str, bool] = field(default_factory=lambda: {
        "ATT_LOOKING_AWAY": True,
        "ATT_DOWNWARD_GAZE": True,
        "ID_MISMATCH": False,
        "ID_FACE_MISSING": True,
        "ID_MULTIPLE_FACES": True,
        "UNAUTH_PHONE": True,
        "UNAUTH_BOOK": True,
        "ENV_BOOK_DETECTED": True,
        "UNAUTH_NOTEBOOK": True,
        "UNAUTH_REGISTER": True,
        "UNAUTH_PAPER": True,
        "UNAUTH_LAPTOP": True,
        "COMM_EARPHONES": True,
        "COMM_HEADPHONES": True,
        "COMM_MULTIPLE_PERSONS": True,
        "ENV_CAM_OCCLUDED": True,
        "ENV_CAM_COVERED": True,
        "IDENTITY_LOW_INTEGRITY": False,
        "IDENTITY_INSTABILITY": False,
        "CONFIRMED_PRESENTATION_ATTACK": True,
        "IDENTITY_REPEATED_MISMATCH": False,
        "INSUFFICIENT_IDENTITY_EVIDENCE": True
    })
    
    # Custom thresholds (e.g., maximum duration allowed for looking away)
    thresholds: Dict[str, float] = field(default_factory=lambda: {
        "looking_away_duration": 3.0,
        "downward_gaze_duration": 5.0,
        "face_missing_duration": 2.0
    })

    # Screen viewing attention tolerance configuration. These direct camera
    # angles may be tuned without requiring a per-session baseline.
    attention_tolerance: AttentionToleranceConfig = field(default_factory=AttentionToleranceConfig)
    require_calibrated_attention: bool = True
    
    # Optional evaluation intervals to skip frames if needed (e.g. run rules every N seconds)
    evaluation_interval_seconds: float = 0.0
    enable_logging: bool = True

@dataclass
class RuleEvaluation:
    """The result of evaluating a single rule."""
    rule_id: str
    rule_name: str
    category: str
    triggered: bool
    confidence: float
    supporting_observations: str
    evaluation_timestamp: float
    evaluation_duration: float

@dataclass
class RuleStatistics:
    """Summary statistics for a rule engine run."""
    total_rules_evaluated: int = 0
    total_rules_triggered: int = 0
    triggered_by_category: Dict[str, int] = field(default_factory=dict)
    processing_time_ms: float = 0.0
