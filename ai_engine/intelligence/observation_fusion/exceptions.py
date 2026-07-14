"""Exceptions for Observation Fusion."""
from ai_engine.core.exceptions import AIEngineError

class ObservationFusionError(AIEngineError):
    """Base exception for observation fusion errors."""
    pass

class MissingObservationError(ObservationFusionError):
    """Raised when an enabled subsystem's data is completely missing."""
    pass

class InvalidObservationError(ObservationFusionError):
    """Raised when an observation has malformed or unexpected data structures."""
    pass
