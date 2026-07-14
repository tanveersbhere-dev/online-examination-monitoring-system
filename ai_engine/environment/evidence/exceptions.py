"""
Exceptions for Evidence Snapshot Manager.
"""
from ai_engine.core.exceptions import AIEngineError

class EvidenceManagerError(AIEngineError):
    """Base exception for Evidence Manager errors."""
    pass

class SnapshotCreationError(EvidenceManagerError):
    """Raised when failing to create an image snapshot."""
    pass

class SnapshotStorageError(EvidenceManagerError):
    """Raised when failing to save an image snapshot to disk."""
    pass

class ImageProcessingError(EvidenceManagerError):
    """Raised when OpenCV drawing or processing fails."""
    pass
