"""
Exceptions for the Object Detection Feature module.
"""
from ai_engine.core.exceptions import AIEngineError

class ObjectDetectionError(AIEngineError):
    """Base exception for all Object Detection errors."""
    pass

class ModelLoadError(ObjectDetectionError):
    """Raised when the object detection model fails to load."""
    pass

class InferenceError(ObjectDetectionError):
    """Raised when an error occurs during model inference."""
    pass

class InvalidFrameError(ObjectDetectionError):
    """Raised when the input frame is invalid or missing."""
    pass
