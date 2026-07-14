"""
Model configuration and generic 3D face model constants for Head Pose Estimation.
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


# ---------------------------------------------------------------------------
# Generic 3D Face Model
# These coordinates represent a generic 3D human face.
# Scale is arbitrary but roughly corresponds to mm.
# ---------------------------------------------------------------------------

# Indices of the MediaPipe Face Mesh landmarks used for pose estimation
# 1: Nose tip
# 152: Chin
# 33: Left eye left corner
# 263: Right eye right corner
# 61: Left mouth corner
# 291: Right mouth corner
MP_LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]

# The corresponding 3D coordinates in the generic model
GENERIC_3D_MODEL_POINTS = np.array([
    [0.0, 0.0, 0.0],          # Nose tip
    [0.0, -330.0, -65.0],     # Chin
    [-225.0, 170.0, -135.0],  # Left eye left corner
    [225.0, 170.0, -135.0],   # Right eye right corner
    [-150.0, -150.0, -125.0], # Left mouth corner
    [150.0, -150.0, -125.0]   # Right mouth corner
], dtype=np.float64)


@dataclass
class HeadPoseConfig:
    """
    Configuration for the Head Pose Estimator.
    
    Attributes:
        focal_length_multiplier: Multiplier for image width to approximate focal length.
        enable_logging: Emit per-frame inference diagnostics at DEBUG level.
    """
    focal_length_multiplier: float = 1.0
    enable_logging: bool = True
