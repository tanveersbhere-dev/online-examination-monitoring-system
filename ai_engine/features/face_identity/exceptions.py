"""
Exceptions for the Face Identity Feature module.
"""
from ai_engine.core.exceptions import AIEngineError

class FaceIdentityError(AIEngineError):
    """Base exception for all Face Identity processor errors."""
    pass

class EmbeddingGenerationError(FaceIdentityError):
    """Raised when an embedding cannot be generated from a valid face image."""
    pass

class IdentityVerificationError(FaceIdentityError):
    """Raised when there is an issue during the verification/comparison process."""
    pass
