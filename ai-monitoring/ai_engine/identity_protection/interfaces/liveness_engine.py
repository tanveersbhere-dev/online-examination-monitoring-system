"""
Abstract interface for Liveness Detection Engines.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class LivenessResult:
    """
    Generic result returned by a Liveness Engine.
    """
    is_live: bool = True
    liveness_score: float = 1.0  # Range [0.0, 1.0]
    presentation_attack_type: str = "NONE"  # e.g., PRINTED_PHOTO, SCREEN_REPLAY, VIRTUAL_FEED, MASK
    confidence: float = 1.0
    reason: str = "Live human candidate verified"
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class LivenessEngineInterface(ABC):
    """
    Abstract Base Class for all anti-spoofing and liveness engines.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """Initializes engine models, resources, and configurations."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Cleans up model weights, GPU/CPU memory, and worker threads."""
        pass

    @abstractmethod
    def process(self, frame_bgr: Any, face_bbox: Optional[Any] = None) -> LivenessResult:
        """
        Processes a single frame and face bounding box to evaluate liveness.
        
        Args:
            frame_bgr: OpenCV image matrix (BGR format)
            face_bbox: Optional face bounding box (x, y, w, h)
            
        Returns:
            LivenessResult containing scores and attack classifications.
        """
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Returns engine health diagnostic information."""
        pass
