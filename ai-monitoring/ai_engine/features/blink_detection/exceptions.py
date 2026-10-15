"""
Exceptions for the Blink Detection Feature module.
"""
from ai_engine.core.exceptions import AIEngineError

class BlinkDetectionError(AIEngineError):
    """Base exception for all Blink Detection processor errors."""
    pass

class InvalidEARDataError(BlinkDetectionError):
    """Raised when EAR data is missing or invalid."""
    pass

class TemporalProcessingError(BlinkDetectionError):
    """Raised when there is an issue with the temporal history buffer."""
    pass
