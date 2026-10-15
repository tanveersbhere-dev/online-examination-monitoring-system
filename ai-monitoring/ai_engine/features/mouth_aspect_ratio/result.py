"""
Strongly typed result objects for the Mouth Aspect Ratio (MAR) Feature module.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class MouthGeometry:
    """
    Geometric measurements for a single mouth.
    
    Attributes:
        mar: The computed Mouth Aspect Ratio.
        mouth_width: Horizontal distance between mouth corners (normalized [0, 1]).
        mouth_height: Average vertical distance between upper and lower lips (normalized).
        mouth_center: 2D coordinate for the center of the mouth (normalized).
        upper_lip_points: List of 2D coordinates for the upper lip.
        lower_lip_points: List of 2D coordinates for the lower lip.
        confidence: Confidence score of the extraction [0, 1].
        face_index: Zero-based index of the face.
    """
    mar: float
    mouth_width: float
    mouth_height: float
    mouth_center: Tuple[float, float]
    upper_lip_points: List[Tuple[float, float]]
    lower_lip_points: List[Tuple[float, float]]
    confidence: float
    face_index: int


@dataclass
class MARResult:
    """
    Aggregated output of one MAR computation pass on a single frame.
    
    Attributes:
        geometries: Per-face MouthGeometry objects, ordered by face index.
        frame_id: Identifier of the source frame.
        processing_timestamp: Unix epoch time (seconds) when inference completed.
        processing_time_ms: Wall-clock inference duration in milliseconds.
    """
    geometries: List[MouthGeometry]
    frame_id: Optional[int]
    processing_timestamp: float
    processing_time_ms: float
    
    @property
    def primary_geometry(self) -> Optional[MouthGeometry]:
        """Returns the mouth geometry for the primary face (index 0), if available."""
        return self.geometries[0] if self.geometries else None
