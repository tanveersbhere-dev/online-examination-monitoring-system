"""
Model configuration and landmark constants for Eye Aspect Ratio (EAR) Feature.
"""
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# MediaPipe Landmark Indices for the Eyes
# ---------------------------------------------------------------------------
# The official MediaPipe face mesh eye landmark indices
# We use 6 landmarks for each eye to compute EAR:
# P1 (outer), P2 (top-outer), P3 (top-inner), P4 (inner), P5 (bottom-inner), P6 (bottom-outer)
# EAR = (||P2 - P6|| + ||P3 - P5||) / (2.0 * ||P1 - P4||)

# Left Eye (Image Right)
LEFT_EYE_P1 = 362  # inner corner (relative to center of face) -> wait, 362 is inner, 263 is outer. Let's use standard.
# Let's define the points sequentially around the eye
LEFT_EYE_INDICES = [
    362,  # P1 - inner corner
    385,  # P2 - top inner
    387,  # P3 - top outer
    263,  # P4 - outer corner
    373,  # P5 - bottom outer
    380   # P6 - bottom inner
]

# Right Eye (Image Left)
RIGHT_EYE_INDICES = [
    33,   # P1 - outer corner
    160,  # P2 - top outer
    158,  # P3 - top inner
    133,  # P4 - inner corner
    153,  # P5 - bottom inner
    144   # P6 - bottom outer
]

REQUIRED_EYE_INDICES = LEFT_EYE_INDICES + RIGHT_EYE_INDICES

@dataclass
class EARConfig:
    """
    Configuration for the Eye Aspect Ratio Processor.
    
    Attributes:
        enable_logging: Emit per-frame diagnostics at DEBUG level.
    """
    enable_logging: bool = True
