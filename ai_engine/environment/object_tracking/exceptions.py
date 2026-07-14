"""
Exceptions for the Object Tracking Feature module.
"""
from ai_engine.core.exceptions import AIEngineError

class ObjectTrackingError(AIEngineError):
    """Base exception for all Object Tracking errors."""
    pass

class TrackerInitializationError(ObjectTrackingError):
    """Raised when the tracker fails to initialize."""
    pass

class TrackingFailureError(ObjectTrackingError):
    """Raised when an error occurs during the tracking process."""
    pass

class InvalidTrackingStateError(ObjectTrackingError):
    """Raised when a track enters an invalid state transition."""
    pass
