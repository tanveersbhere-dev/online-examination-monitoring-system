"""
Model configuration and landmark constants for Mouth Aspect Ratio (MAR) Feature.
"""
from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# MediaPipe Landmark Indices for the Mouth
# ---------------------------------------------------------------------------

# Inner lip horizontal corners
MOUTH_LEFT_CORNER_INDEX = 78
MOUTH_RIGHT_CORNER_INDEX = 308

# Inner lip vertical pairs (upper, lower)
# We use three vertical pairs across the lips for a robust MAR calculation.
MOUTH_UPPER_INNER_INDICES = [82, 13, 81]
MOUTH_LOWER_INNER_INDICES = [87, 14, 178]

# All required indices for simple validation
REQUIRED_MOUTH_INDICES = [
    MOUTH_LEFT_CORNER_INDEX, MOUTH_RIGHT_CORNER_INDEX
] + MOUTH_UPPER_INNER_INDICES + MOUTH_LOWER_INNER_INDICES


@dataclass
class MARConfig:
    """
    Configuration for the Mouth Aspect Ratio Processor.
    
    Attributes:
        enable_logging: Emit per-frame diagnostics at DEBUG level.
    """
    enable_logging: bool = True
