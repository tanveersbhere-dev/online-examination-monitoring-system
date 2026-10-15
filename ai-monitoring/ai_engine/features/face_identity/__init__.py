"""
Face Identity Consistency Verification Feature Module.

Responsible ONLY for verifying that the same candidate remains present throughout the examination.
"""
from ai_engine.features.face_identity.exceptions import FaceIdentityError, EmbeddingGenerationError, IdentityVerificationError
from ai_engine.features.face_identity.models import FaceIdentityConfig
from ai_engine.features.face_identity.result import FaceIdentityResult, FaceEmbedding, IdentityVerification
from ai_engine.features.face_identity.processor import FaceIdentityProcessor
from ai_engine.features.face_identity.embedding_processor import EmbeddingIdentityProcessor

__all__ = [
    "FaceIdentityError",
    "EmbeddingGenerationError",
    "IdentityVerificationError",
    "FaceIdentityConfig",
    "FaceIdentityResult",
    "FaceEmbedding",
    "IdentityVerification",
    "FaceIdentityProcessor",
    "EmbeddingIdentityProcessor"
]
