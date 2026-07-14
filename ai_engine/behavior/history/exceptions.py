"""
Exceptions for the Behavior History module.
"""
from ai_engine.core.exceptions import AIEngineError

class BehaviorHistoryError(AIEngineError):
    """Base exception for all Behavior History errors."""
    pass

class RollingWindowError(BehaviorHistoryError):
    """Raised when an operation on the rolling window fails."""
    pass

class HistoryOverflowError(BehaviorHistoryError):
    """Raised when the history buffer exceeds its maximum capacity."""
    pass
