"""
Model configuration for the Blink Detection Feature.
"""
from dataclasses import dataclass

@dataclass
class BlinkDetectionConfig:
    """
    Configuration for the Temporal Blink Detection Processor.
    
    Attributes:
        ear_threshold: The EAR value below which the eye is considered closed.
        min_consecutive_frames: Minimum consecutive frames the EAR must be below the threshold to start a blink.
        min_blink_duration_ms: Minimum duration of a blink in milliseconds to be valid.
        max_blink_duration_ms: Maximum duration of a blink in milliseconds to be valid (prevents continuous closure counting as blink).
        frequency_window_seconds: The sliding window size in seconds for calculating blink frequency.
        enable_logging: Emit per-frame diagnostics at DEBUG level.
    """
    ear_threshold: float = 0.20
    min_consecutive_frames: int = 2
    min_blink_duration_ms: float = 50.0
    max_blink_duration_ms: float = 500.0
    frequency_window_seconds: float = 60.0
    enable_logging: bool = True
