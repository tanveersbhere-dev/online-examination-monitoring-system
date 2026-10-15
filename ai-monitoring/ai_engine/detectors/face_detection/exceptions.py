"""
Custom exceptions for the Face Detection module.

These are isolated from the core engine exceptions so the face detection
subsystem can be swapped out independently.
"""


class FaceDetectorError(Exception):
    """Base exception for all Face Detection errors."""
    pass


class FaceDetectorInitializationError(FaceDetectorError):
    """Raised when the face detector fails to initialize its model or resources."""
    pass


class FaceDetectorInferenceError(FaceDetectorError):
    """Raised when the face detector encounters an error during frame inference."""
    pass


class FaceDetectorModelNotFoundError(FaceDetectorInitializationError):
    """Raised when the required model file cannot be found or downloaded."""
    pass
