"""
Eye Aspect Ratio (EAR) Feature Module.

Responsible ONLY for calculating the Eye Aspect Ratio (EAR) from facial landmarks.
"""
from ai_engine.features.eye_aspect_ratio.exceptions import EARProcessorError, InvalidEyeLandmarksError
from ai_engine.features.eye_aspect_ratio.models import EARConfig
from ai_engine.features.eye_aspect_ratio.result import EARResult, EyeGeometry, EyeAspectRatio
from ai_engine.features.eye_aspect_ratio.processor import EyeAspectRatioProcessor
from ai_engine.features.eye_aspect_ratio.mediapipe_processor import MediaPipeEARProcessor

__all__ = [
    "EARProcessorError",
    "InvalidEyeLandmarksError",
    "EARConfig",
    "EARResult",
    "EyeGeometry",
    "EyeAspectRatio",
    "EyeAspectRatioProcessor",
    "MediaPipeEARProcessor"
]
