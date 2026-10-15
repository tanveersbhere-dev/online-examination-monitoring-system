"""
Exceptions for the Eye Aspect Ratio (EAR) Feature module.
"""
from ai_engine.core.exceptions import AIEngineError

class EARProcessorError(AIEngineError):
    """Base exception for all EAR processor errors."""
    pass

class InvalidEyeLandmarksError(EARProcessorError):
    """Raised when required eye landmarks are missing or invalid."""
    pass
