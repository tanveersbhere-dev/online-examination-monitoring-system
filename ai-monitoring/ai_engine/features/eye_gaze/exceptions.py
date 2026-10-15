"""
Custom exceptions for the Eye Gaze Feature Extraction module.
"""

class EyeGazeError(Exception):
    """Base exception for all Eye Gaze Extraction errors."""
    pass


class EyeTrackingError(EyeGazeError):
    """
    Raised when eye tracking or gaze extraction fails on a specific frame.
    """
    pass


class InvalidIrisLandmarksError(EyeGazeError):
    """
    Raised when the required iris landmarks are missing or invalid.
    """
    pass


class EyeGazeStateError(EyeGazeError):
    """
    Raised when a lifecycle method is called in an invalid order.
    """
    pass
