"""
Strongly typed result objects for the Face Detection module.

These dataclasses are the sole output contract of the face detector. They
decouple calling code from the underlying MediaPipe representation and make
unit testing straightforward.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class DetectedFace:
    """
    Represents a single detected face within a frame.

    Attributes:
        bbox: Bounding box as (x, y, width, height) in pixel coordinates where
            (x, y) is the top-left corner of the box.
        confidence: Detection confidence score in [0.0, 1.0].
        keypoints: Optional list of facial keypoints as (x, y) normalized
            coordinates. MediaPipe blaze face detection provides 6 keypoints:
            right_eye, left_eye, nose_tip, mouth_center, right_ear_tragion,
            left_ear_tragion.
    """
    bbox: Tuple[float, float, float, float]    # x, y, w, h (pixels)
    confidence: float
    keypoints: List[Tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )


@dataclass
class FaceDetectionResult:
    """
    Aggregated result of one face-detection inference pass on a single frame.

    Attributes:
        faces: Ordered list of detected faces, sorted by confidence descending.
        face_count: Total number of faces detected (len(faces)).
        frame_id: Identifier of the source frame.
        detection_timestamp: Unix epoch timestamp (seconds) at the moment the
            inference completed.
        inference_time_ms: Wall-clock time taken by the inference call in
            milliseconds.
        frame_width: Width of the source frame in pixels.
        frame_height: Height of the source frame in pixels.
    """
    faces: List[DetectedFace]
    face_count: int
    frame_id: Optional[int]
    detection_timestamp: float
    inference_time_ms: float
    frame_width: int
    frame_height: int

    def __post_init__(self) -> None:
        # Ensure face_count is consistent with the faces list
        if self.face_count != len(self.faces):
            self.face_count = len(self.faces)

    @property
    def primary_face(self) -> Optional[DetectedFace]:
        """Returns the highest-confidence face, or None if no faces detected."""
        return self.faces[0] if self.faces else None

    @property
    def is_face_detected(self) -> bool:
        """True when at least one face was detected."""
        return self.face_count > 0

    @property
    def all_bboxes(self) -> List[Tuple[float, float, float, float]]:
        """Returns the bounding boxes of all detected faces."""
        return [f.bbox for f in self.faces]

    @property
    def all_confidences(self) -> List[float]:
        """Returns the confidence scores of all detected faces."""
        return [f.confidence for f in self.faces]
