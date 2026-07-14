"""
Embedding Identity Processor implementation.
"""
import time
import math
import logging
from typing import List, Optional

import numpy as np

from ai_engine.core.exam_context import ExamContext
from ai_engine.features.face_identity.processor import FaceIdentityProcessor
from ai_engine.features.face_identity.models import FaceIdentityConfig
from ai_engine.features.face_identity.result import FaceEmbedding, IdentityVerification
from ai_engine.features.face_identity.exceptions import FaceIdentityError, EmbeddingGenerationError

logger = logging.getLogger(__name__)

class EmbeddingIdentityProcessor(FaceIdentityProcessor):
    """
    Verifies face identity using an offline embedding model (e.g., InsightFace).
    """
    
    def __init__(self, config: FaceIdentityConfig) -> None:
        super().__init__(config)
        self._initialized = False
        self._reference_embedding: Optional[List[float]] = None
        self._frames_since_last_check = 0
        self._last_tracking_id: Optional[str] = None
        self._model = None
        
    def set_reference_embedding(self, embedding: List[float]) -> None:
        """Injects a pre-registered database embedding for continuous verification."""
        self._reference_embedding = embedding
        if self._config.enable_logging:
            logger.debug("Reference embedding successfully injected from database.")
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug(f"Initializing EmbeddingIdentityProcessor with model: {self._config.embedding_model_name}")
        
        # Lazy load insightface to not crash if only testing or if unavailable
        try:
            import insightface
            # Initialize offline model (e.g., buffalo_l). 
            # We only need recognition ('rec') for embeddings, but we assume face is already cropped
            # or we pass the whole image and bbox.
            # Using FaceAnalysis to handle the pipeline.
            self._model = insightface.app.FaceAnalysis(name=self._config.embedding_model_name, allowed_modules=['recognition'])
            # Since we require offline CPU only, ctx_id=0 for cpu
            self._model.prepare(ctx_id=-1)
        except ImportError:
            logger.warning("insightface module not found. The processor will raise errors during extraction if not mocked.")
            self._model = None
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # We don't raise here, we raise when extraction is actually attempted if model is None
        
        self._initialized = True
        if self._config.enable_logging:
            logger.debug("EmbeddingIdentityProcessor initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise FaceIdentityError("Cannot start uninitialized processor.")
        self._reference_embedding = None
        self._frames_since_last_check = 0
        if self._config.enable_logging:
            logger.debug("EmbeddingIdentityProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("EmbeddingIdentityProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up EmbeddingIdentityProcessor...")
        self._initialized = False
        self._reference_embedding = None
        self._last_tracking_id = None
        self._model = None
        if self._config.enable_logging:
            logger.debug("EmbeddingIdentityProcessor cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads face_info and current_frame to determine identity consistency.
        """
        if not self._initialized:
            raise FaceIdentityError("Processor is not initialized.")

        try:
            start_time = time.perf_counter()
            face_info = context.face_info
            
            # Reset verification timestamp logic per frame to not carry over old timestamps incorrectly
            verification_timestamp = face_info.verification_timestamp
            identity_consistent = face_info.identity_consistent
            similarity_score = face_info.similarity_score
            identity_confidence = face_info.identity_confidence
            current_emb = face_info.current_embedding
            
            # Check if tracking ID changed or face reappeared
            current_tracking_id = getattr(face_info, "tracking_id", None)
            if current_tracking_id != self._last_tracking_id:
                if self._config.enable_logging:
                    logger.debug("Tracking ID changed or face reappeared. Forcing immediate identity verification.")
                self._frames_since_last_check = self._config.verification_interval_frames
                self._last_tracking_id = current_tracking_id
            
            # Check if we need to process this frame
            should_process = False
            if face_info.face_count > 0 and face_info.confidence >= self._config.min_face_confidence:
                if self._reference_embedding is None:
                    # We always process the first valid face to get the reference
                    should_process = True
                else:
                    self._frames_since_last_check += 1
                    if self._frames_since_last_check >= self._config.verification_interval_frames:
                        should_process = True
                        self._frames_since_last_check = 0
            
            if should_process:
                # Need frame image
                frame = context.current_frame
                if frame is None or frame.original_frame is None:
                     if self._config.enable_logging:
                         logger.debug("Valid face detected but no camera frame available. Skipping extraction.")
                else:
                    # Extract embedding
                    image = frame.original_frame
                    bbox = face_info.bbox
                    
                    emb_start = time.perf_counter()
                    new_embedding_vector = self._extract_embedding(image, bbox)
                    emb_time = (time.perf_counter() - emb_start) * 1000.0
                    
                    if new_embedding_vector:
                        current_emb = new_embedding_vector
                        
                        if self._reference_embedding is None:
                            self._reference_embedding = current_emb
                            if self._config.enable_logging:
                                logger.debug("Reference embedding captured.")
                        
                        # Compare
                        similarity_score = self._cosine_similarity(self._reference_embedding, current_emb)
                        identity_consistent = similarity_score >= self._config.similarity_threshold
                        
                        # Scale confidence based on margin above/below threshold
                        # Simple mapping for now
                        margin = similarity_score - self._config.similarity_threshold
                        identity_confidence = min(max(0.5 + margin, 0.0), 1.0)
                        
                        verification_timestamp = time.time()
                        
                        if self._config.enable_logging:
                            logger.debug(f"Identity verification complete. Score: {similarity_score:.3f}, Consistent: {identity_consistent}")
                    
            # Write back
            end_time = time.perf_counter()
            proc_time_ms = (end_time - start_time) * 1000.0
            
            face_info.reference_embedding = self._reference_embedding
            face_info.current_embedding = current_emb
            face_info.similarity_score = similarity_score
            face_info.identity_consistent = identity_consistent
            face_info.identity_confidence = identity_confidence
            face_info.verification_timestamp = verification_timestamp
            face_info.identity_processing_time_ms += proc_time_ms
            
            context.face_info = face_info
            
        except FaceIdentityError:
            raise
        except Exception as e:
            if self._config.enable_logging:
                logger.error(f"Unexpected error in EmbeddingIdentityProcessor: {e}")
            raise FaceIdentityError(f"Unexpected error verifying identity: {e}") from e

    def _extract_embedding(self, image: np.ndarray, bbox: tuple) -> Optional[List[float]]:
        """
        Extracts face embedding using the initialized model.
        Returns None if extraction fails.
        """
        if self._model is None:
            # Fallback or raise error if insightface is missing
            # In testing, we can inject a mock embedding by replacing this method
            raise EmbeddingGenerationError("Embedding model is not loaded. Cannot generate embeddings.")
            
        try:
            # For insightface FaceAnalysis, we pass the image.
            # Usually it detects the face. To be efficient, we might crop using bbox first,
            # but standard insightface expects full image and handles detection itself.
            # Since we want to verify the specific detected face, we can constrain it.
            
            # Simple implementation: run get() and pick the face that best overlaps with bbox
            faces = self._model.get(image)
            if not faces:
                return None
                
            # If multiple faces, take the largest one or highest confidence
            # Assuming face_info is already the primary face
            primary_face = max(faces, key=lambda f: f.det_score)
            
            if primary_face.normed_embedding is not None:
                return primary_face.normed_embedding.tolist()
            elif primary_face.embedding is not None:
                # normalize if needed
                emb = primary_face.embedding
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                return emb.tolist()
                
            return None
            
        except Exception as e:
            raise EmbeddingGenerationError(f"Error extracting embedding: {e}") from e

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculates cosine similarity between two vectors."""
        vec1 = np.array(v1)
        vec2 = np.array(v2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(dot_product / (norm1 * norm2))
