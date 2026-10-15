"""Exceptions for Environment History Engine."""
from ai_engine.core.exceptions import AIEngineError

class EnvironmentHistoryError(AIEngineError):
    """Base exception for environment history errors."""
    pass

class HistoryOverflowError(EnvironmentHistoryError):
    """Raised when the history exceeds the configured memory limits."""
    pass

class HistoryProcessingError(EnvironmentHistoryError):
    """Raised when an error occurs during history summary generation or track parsing."""
    pass

class InvalidHistoryStateError(EnvironmentHistoryError):
    """Raised when the history engine is in an invalid state."""
    pass
