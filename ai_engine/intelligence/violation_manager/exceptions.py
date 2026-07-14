"""Exceptions for Violation Manager."""
from ai_engine.core.exceptions import AIEngineError

class ViolationManagerError(AIEngineError):
    """Base exception for violation manager errors."""
    pass

class ViolationCreationError(ViolationManagerError):
    """Raised when failing to create a violation."""
    pass

class ViolationMergeError(ViolationManagerError):
    """Raised when a violation merge operation fails."""
    pass

class ViolationStateError(ViolationManagerError):
    """Raised when an invalid lifecycle state transition is attempted."""
    pass
