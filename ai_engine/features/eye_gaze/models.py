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

RIGHT_EYE_LEFT_CORNER_INDEX = 362
RIGHT_EYE_RIGHT_CORNER_INDEX = 263


@dataclass
class EyeGazeConfig:
    """
    Configuration for the Eye Gaze Extractor.
    
    Attributes:
        confidence_threshold: Minimum presence score required for the iris landmarks.
        enable_logging: Emit per-frame diagnostics at DEBUG level.
    """
    confidence_threshold: float = 0.5
    enable_logging: bool = True
