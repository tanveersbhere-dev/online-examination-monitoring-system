"""
Model configuration and landmark constants for Eye Gaze Feature Extraction.
"""
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# MediaPipe Landmark Indices
# Subject's Left and Right eyes respectively.
# ---------------------------------------------------------------------------

LEFT_IRIS_CENTER_INDEX = 468
RIGHT_IRIS_CENTER_INDEX = 473

LEFT_EYE_LEFT_CORNER_INDEX = 33
LEFT_EYE_RIGHT_CORNER_INDEX = 133
LEFT_EYE_UPPER_LID_INDEX = 159
LEFT_EYE_LOWER_LID_INDEX = 145

RIGHT_EYE_LEFT_CORNER_INDEX = 362
RIGHT_EYE_RIGHT_CORNER_INDEX = 263
RIGHT_EYE_UPPER_LID_INDEX = 386
RIGHT_EYE_LOWER_LID_INDEX = 374


@dataclass
class EyeGazeConfig:
    """
    Configuration for the Eye Gaze Extractor.
    
    Attributes:
        confidence_threshold: Minimum presence score required for the iris landmarks.
        enable_logging: Emit per-frame diagnostics at DEBUG level.
        one_euro_min_cutoff: Minimum cutoff frequency (Hz) for One-Euro filter.
            Lower values reduce jitter during stationary gaze / fixations.
        one_euro_beta: Speed coefficient for One-Euro filter.
            Higher values reduce lag during fast saccades and intentional looking away.
        one_euro_d_cutoff: Cutoff frequency (Hz) for derivative filtering in One-Euro filter.
        enable_smoothing: Whether One-Euro temporal filtering is enabled.
    """
    confidence_threshold: float = 0.5
    enable_logging: bool = True
    one_euro_min_cutoff: float = 1.0
    one_euro_beta: float = 0.015
    one_euro_d_cutoff: float = 1.0
    enable_smoothing: bool = True
