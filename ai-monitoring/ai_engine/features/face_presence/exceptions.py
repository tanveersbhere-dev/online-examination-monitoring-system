"""
Exceptions for the Face Presence Feature module.
"""
from ai_engine.core.exceptions import AIEngineError

class FacePresenceError(AIEngineError):
    """Base exception for all Face Presence processor errors."""
    pass

class InvalidFaceStateError(FacePresenceError):
    """Raised when face state data is missing or invalid."""
    pass

class PresenceMonitoringError(FacePresenceError):
    """Raised when there is an issue with the temporal monitoring buffer."""
    pass
