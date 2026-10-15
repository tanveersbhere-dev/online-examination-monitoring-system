"""
Custom exceptions for the Face Landmark Detection module.

These are fully isolated from both the core engine exceptions and the Face
Detection module exceptions, so the landmark subsystem can be replaced or
removed independently without cascading changes.
"""


class LandmarkDetectorError(Exception):
    """Base exception for all Face Landmark Detection errors."""
    pass


class MediaPipeInitializationError(LandmarkDetectorError):
    """
    Raised when the MediaPipe FaceLandmarker cannot be constructed.

    Typical causes:
    • MediaPipe library not installed.
    • Model file missing, corrupt, or incompatible.
    • Unsupported runtime options passed to create_from_options().
    """
    pass


class LandmarkExtractionError(LandmarkDetectorError):
    """
    Raised when landmark extraction fails on a specific frame.

    Typical causes:
    • Malformed or zero-size image array.
    • MediaPipe runtime crash during inference.
    • Unexpected result structure returned by the backend.
    """
    pass


class LandmarkDetectorModelNotFoundError(MediaPipeInitializationError):
    """
    Raised when the required model file cannot be located or downloaded.

    Extends MediaPipeInitializationError because model absence is always
    a fatal initialisation failure.
    """
    pass


class LandmarkDetectorStateError(LandmarkDetectorError):
    """
    Raised when a lifecycle method is called in an invalid order.

    Example: calling detect() before initialize(), or calling start()
    before initialize() completes successfully.
    """
    pass
