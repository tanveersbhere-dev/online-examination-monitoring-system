"""
Model configuration and constants for the Face Detection module.

Defines model identifiers, download URLs, and configuration dataclasses
used to configure face detection implementations.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Official MediaPipe Face Detection blaze model — Tasks API format
# Source: https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.task
BLAZE_FACE_SHORT_RANGE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_detector/blaze_face_short_range/float16/latest/"
    "blaze_face_short_range.tflite"
)
BLAZE_FACE_SHORT_RANGE_MODEL_FILENAME = "blaze_face_short_range.tflite"

# Default model cache directory (relative to project root)
DEFAULT_MODEL_CACHE_DIR = Path("ai_engine") / "detectors" / "face_detection" / "model_cache"


@dataclass
class FaceDetectionConfig:
    """
    Configuration parameters for a face detection implementation.

    Attributes:
        min_detection_confidence: Minimum confidence score [0.0, 1.0] to accept
            a detection. Detections below this threshold are discarded.
        min_suppression_threshold: Non-maximum suppression threshold used to
            remove duplicate overlapping boxes.
        max_num_faces: Maximum number of faces to detect per frame.
        model_path: Optional explicit path to the model file. When None the
            detector will attempt to locate or download the default model.
        model_cache_dir: Directory used to cache downloaded model files.
        enable_logging: Whether to emit per-frame inference logs.
    """
    min_detection_confidence: float = 0.5
    min_suppression_threshold: float = 0.3
    max_num_faces: int = 5
    model_path: Optional[Path] = None
    model_cache_dir: Path = field(default_factory=lambda: DEFAULT_MODEL_CACHE_DIR)
    enable_logging: bool = True
