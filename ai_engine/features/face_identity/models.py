"""
Model configuration for the Face Identity Verification Feature.
"""
from dataclasses import dataclass

@dataclass
class FaceIdentityConfig:
    """
    Configuration for the Embedding Identity Processor.
    
    Attributes:
        similarity_threshold: Threshold for cosine similarity [0.0, 1.0]. Above is match, below is mismatch.
        embedding_model_name: The name of the offline CPU model to use (e.g., buffalo_l or simple resnet).
        verification_interval_frames: How often to verify the identity (e.g., every 15 frames) to save CPU.
        min_face_confidence: Minimum detection confidence required to generate an embedding.
        enable_logging: Emit diagnostics at DEBUG level.
    """
    similarity_threshold: float = 0.60
    embedding_model_name: str = "buffalo_l"
    verification_interval_frames: int = 15
    min_face_confidence: float = 0.8
    enable_logging: bool = True
