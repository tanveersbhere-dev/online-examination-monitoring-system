"""
Object Detection Feature Module (Environment Intelligence Stage 1).

Responsible ONLY for detecting objects from the current camera frame.
"""
from ai_engine.environment.object_detection.exceptions import ObjectDetectionError, ModelLoadError, InferenceError, InvalidFrameError
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_detection.result import ObjectDetectionResult
from ai_engine.environment.object_detection.detector import ObjectDetectorInterface
from ai_engine.environment.object_detection.yolo_detector import YOLODetector

__all__ = [
    "ObjectDetectionError",
    "ModelLoadError",
    "InferenceError",
    "InvalidFrameError",
    "ObjectDetectionConfig",
    "ObjectDetectionResult",
    "ObjectDetectorInterface",
    "YOLODetector"
]
