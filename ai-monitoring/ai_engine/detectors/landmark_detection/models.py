"""
Model configuration and constants for the Face Landmark Detection module.

Provides the official MediaPipe Face Landmarker model URL, cache conventions,
and the injectable LandmarkDetectionConfig dataclass.

All default values are conservative production-ready choices; override them
via dependency injection rather than modifying this file.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# MediaPipe Face Landmarker model — Tasks API v0.10+
# Source: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
# ---------------------------------------------------------------------------
FACE_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/"
    "face_landmarker.task"
)
FACE_LANDMARKER_MODEL_FILENAME = "face_landmarker.task"

# Number of landmarks returned by MediaPipe FaceLandmarker per face
MEDIAPIPE_FACE_LANDMARK_COUNT = 478   # 468 canonical + 10 iris keypoints (v2 model)
CANONICAL_FACE_LANDMARK_COUNT = 468   # canonical face mesh landmark count

# Default model cache directory (relative to project root)
DEFAULT_LANDMARK_MODEL_CACHE_DIR = (
    Path("ai_engine") / "detectors" / "landmark_detection" / "model_cache"
)


@dataclass
class LandmarkDetectionConfig:
    """
    Configuration for a face landmark detection implementation.

    All fields have production-safe defaults.  Override via dependency
    injection — never hardcode values in implementation classes.

    Attributes:
        num_faces:
            Maximum number of faces for which landmarks are extracted per
            frame.  Setting this to 1 is optimal for single-student exams.
        min_face_detection_confidence:
            Minimum detection confidence [0, 1] for the internal face
            detector used by FaceLandmarker.
        min_face_presence_confidence:
            Minimum presence confidence [0, 1] for landmark tracking
            between frames.
        min_tracking_confidence:
            Minimum confidence [0, 1] for the face-tracking mode (only
            used in VIDEO / LIVE_STREAM running modes; ignored in IMAGE).
        output_face_blendshapes:
            Whether to also request blendshape scores from the model.
            Disabled by default — only landmark positions are needed here.
        model_path:
            Explicit path to a pre-downloaded ``*.task`` model file.
            When ``None`` the implementation resolves the path automatically,
            downloading to ``model_cache_dir`` if required.
        model_cache_dir:
            Directory used to cache the downloaded model file.
        enable_logging:
            Emit per-frame inference diagnostics at DEBUG level.
    """
    num_faces: int = 1
    min_face_detection_confidence: float = 0.5
    min_face_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    output_face_blendshapes: bool = False
    model_path: Optional[Path] = None
    model_cache_dir: Path = field(
        default_factory=lambda: DEFAULT_LANDMARK_MODEL_CACHE_DIR
    )
    enable_logging: bool = True
