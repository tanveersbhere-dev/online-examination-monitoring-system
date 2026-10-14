"""
Face Embedding Service
======================
Standalone identity embedding extraction service for student registration.
Uses InsightFace (buffalo_l) to extract 512-dimensional normalized embeddings.
"""
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class FaceEmbeddingError(Exception):
    """Exception raised when face embedding generation fails."""
    pass


class FaceEmbeddingService:
    """
    Singleton service extracting 512-dim facial identity embeddings.
    """
    _instance = None
    _model = None

    @classmethod
    def get_instance(cls) -> "FaceEmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, model_name: str = "buffalo_l") -> None:
        self.model_name = model_name
        self._init_model()

    def _init_model(self) -> None:
        if self._model is not None:
            return
        try:
            import insightface
            self._model = insightface.app.FaceAnalysis(
                name=self.model_name,
                allowed_modules=["detection", "recognition"]
            )
            self._model.prepare(ctx_id=-1)  # CPU execution
            logger.info(f"[FaceEmbeddingService] Loaded InsightFace model '{self.model_name}' on CPU.")
        except ImportError:
            logger.warning("[FaceEmbeddingService] insightface library not installed.")
            self._model = None
        except Exception as e:
            logger.error(f"[FaceEmbeddingService] Failed to load InsightFace model: {e}")
            self._model = None

    def extract_embedding(self, image: np.ndarray) -> Optional[List[float]]:
        """
        Extracts 512-dim normalized embedding from a BGR OpenCV image.
        Returns None if no face is detected.
        """
        if self._model is None:
            self._init_model()
            if self._model is None:
                raise FaceEmbeddingError("InsightFace model is not initialized.")

        try:
            faces = self._model.get(image)
            if not faces:
                return None

            primary_face = max(faces, key=lambda f: getattr(f, "det_score", 0.0))

            if getattr(primary_face, "normed_embedding", None) is not None:
                return primary_face.normed_embedding.tolist()
            elif getattr(primary_face, "embedding", None) is not None:
                emb = primary_face.embedding
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                return emb.tolist()
            return None
        except Exception as e:
            logger.error(f"[FaceEmbeddingService] Error extracting face embedding: {e}")
            raise FaceEmbeddingError(f"Error extracting face embedding: {e}") from e

    @staticmethod
    def compute_similarity(emb1: List[float], emb2: List[float]) -> float:
        """Calculates cosine similarity between two 512-dim normalized vectors."""
        vec1 = np.array(emb1, dtype=np.float32)
        vec2 = np.array(emb2, dtype=np.float32)
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))
