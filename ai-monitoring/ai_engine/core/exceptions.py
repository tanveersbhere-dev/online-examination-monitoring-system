class AIEngineError(Exception):
    """Base exception for all AI Engine errors."""
    pass

class ConfigurationError(AIEngineError):
    """Raised when there is a configuration error."""
    pass

class CameraError(AIEngineError):
    """Raised when camera initialization, connection, or acquisition fails."""
    pass

class EventBusError(AIEngineError):
    """Raised when event publishing, subscription, or thread processing fails."""
    pass

class ExamContextError(AIEngineError):
    """Raised when thread-safe modifications or context operations fail."""
    pass
