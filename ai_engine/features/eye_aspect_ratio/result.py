"""
Strongly typed result objects for the Eye Aspect Ratio (EAR) Feature module.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class EyeAspectRatio:
    """
    Eye Aspect Ratio metrics for a single face.
    """
    left_ear: float
    right_ear: float
    average_ear: float

@dataclass
class EyeGeometry:
    """
    Geometric measurements for a single face's eyes.
    
    Attributes:
        ear: The EyeAspectRatio metrics.
        left_eye_width: Horizontal width of the left eye (normalized).
        left_eye_height: Vertical height of the left eye (normalized).
        right_eye_width: Horizontal width of the right eye (normalized).
        right_eye_height: Vertical height of the right eye (normalized).
        confidence: Confidence score of the extraction [0, 1].
        face_index: Zero-based index of the face.
    """
    ear: EyeAspectRatio
    left_eye_width: float
    left_eye_height: float
    right_eye_width: float
    right_eye_height: float
    confidence: float
    face_index: int

@dataclass
class EARResult:
    """
    Aggregated output of one EAR computation pass on a single frame.
    
    Attributes:
        geometries: Per-face EyeGeometry objects, ordered by face index.
        frame_id: Identifier of the source frame.
        processing_timestamp: Unix epoch time (seconds) when inference completed.
        processing_time_ms: Wall-clock inference duration in milliseconds.
    """
    geometries: List[EyeGeometry]
    frame_id: Optional[int]
    processing_timestamp: float
    processing_time_ms: float
    
    @property
    def primary_geometry(self) -> Optional[EyeGeometry]:
        """Returns the eye geometry for the primary face (index 0), if available."""
        return self.geometries[0] if self.geometries else None
