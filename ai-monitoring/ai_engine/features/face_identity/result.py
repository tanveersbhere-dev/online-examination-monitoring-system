"""
Strongly typed result objects for the Face Identity Feature module.
"""
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FaceEmbedding:
    """
    Represents a face embedding vector.
    
    Attributes:
        vector: The actual embedding array (list of floats).
        confidence: The confidence of the face detection when captured.
        extraction_time_ms: Time taken to extract this embedding.
    """
    vector: List[float]
    confidence: float
    extraction_time_ms: float

@dataclass
class IdentityVerification:
    """
    Represents the result of comparing two embeddings.
    
    Attributes:
        is_consistent: True if the similarity exceeds the threshold.
        similarity_score: Cosine similarity score [0.0, 1.0].
        confidence: Confidence in the verification (can be derived from score margin).
    """
    is_consistent: bool
    similarity_score: float
    confidence: float

@dataclass
class FaceIdentityResult:
    """
    Result of the identity verification process for a frame.
    
    Attributes:
        reference_embedding: The baseline embedding, if available.
        current_embedding: The newly captured embedding, if generated.
        verification: The verification outcome if a comparison was made.
        processing_timestamp: Unix epoch time when processing completed.
        processing_time_ms: Total time taken in this module.
        frame_id: The ID of the frame processed.
    """
    reference_embedding: Optional[FaceEmbedding]
    current_embedding: Optional[FaceEmbedding]
    verification: Optional[IdentityVerification]
    processing_timestamp: float
    processing_time_ms: float
    frame_id: Optional[int]
