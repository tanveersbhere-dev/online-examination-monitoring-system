"""
Custom exceptions for the Mouth Aspect Ratio (MAR) Feature module.
"""

class MARProcessorError(Exception):
    """Base exception for all MAR Processor errors."""
    pass


class InvalidMouthLandmarksError(MARProcessorError):
    """
    Raised when the required mouth landmarks are missing or invalid.
    """
    pass


class MARProcessorStateError(MARProcessorError):
    """
    Raised when a lifecycle method is called in an invalid order.
    """
    pass
