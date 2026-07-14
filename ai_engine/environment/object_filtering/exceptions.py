"""
Exceptions for the Object Filtering Feature module.
"""
from ai_engine.core.exceptions import AIEngineError

class ObjectFilteringError(AIEngineError):
    """Base exception for all Object Filtering errors."""
    pass

class InvalidDetectionError(ObjectFilteringError):
    """Raised when an incoming detection is malformed."""
    pass

class FilteringConfigurationError(ObjectFilteringError):
    """Raised when the filtering configuration is invalid."""
    pass
