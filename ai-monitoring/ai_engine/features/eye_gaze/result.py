"""
Strongly typed result objects for the Eye Gaze Feature Extraction module.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class EyeCenter:
    """
    2D coordinate for the center of the eye in normalized space [0, 1].
    """
    x: float
    y: float


@dataclass
class IrisCenter:
    """
    2D coordinate for the center of the iris in normalized space [0, 1].
    """
    x: float
    y: float


@dataclass
class EyeGaze:
    """
    Represents the estimated eye gaze for a single face.
    
    Attributes:
        left_gaze_vector: The 3D gaze vector for the left eye (dx, dy, dz).
        right_gaze_vector: The 3D gaze vector for the right eye (dx, dy, dz).
        combined_gaze_vector: The combined 3D gaze vector.
        left_iris_center: Normalised 2D coordinates of the left iris.
        right_iris_center: Normalised 2D coordinates of the right iris.
        left_eye_center: Normalised 2D coordinates of the left eye.
        right_eye_center: Normalised 2D coordinates of the right eye.
        confidence: Confidence score of the gaze estimation [0, 1].
        face_index: Zero-based index of the face.
    """
    left_gaze_vector: Tuple[float, float, float]
    right_gaze_vector: Tuple[float, float, float]
    combined_gaze_vector: Tuple[float, float, float]
    left_iris_center: Optional[IrisCenter]
    right_iris_center: Optional[IrisCenter]
    left_eye_center: Optional[EyeCenter]
    right_eye_center: Optional[EyeCenter]
    confidence: float
    face_index: int
    raw_gaze_vector: Optional[Tuple[float, float, float]] = None
    filtered_gaze_vector: Optional[Tuple[float, float, float]] = None


@dataclass
class EyeGazeResult:
    """
    Aggregated output of one eye gaze estimation pass on a single frame.
    
    Attributes:
        gazes: Per-face EyeGaze objects, ordered by face index.
        frame_id: Identifier of the source frame.
        processing_timestamp: Unix epoch time (seconds) when inference completed.
        processing_time_ms: Wall-clock inference duration in milliseconds.
    """
    gazes: List[EyeGaze]
    frame_id: Optional[int]
    processing_timestamp: float
    processing_time_ms: float
    
    @property
    def primary_gaze(self) -> Optional[EyeGaze]:
        """Returns the gaze for the primary face (index 0), if available."""
        return self.gazes[0] if self.gazes else None
