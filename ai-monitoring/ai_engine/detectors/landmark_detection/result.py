"""
Strongly typed result objects for the Face Landmark Detection module.

No dictionaries, raw tuples, or anonymous structures are used.  All data is
carried as named dataclass fields so that downstream modules can access values
by name and IDEs can provide full auto-completion.

Class hierarchy
---------------
Landmark          — single 3-D normalised point with optional visibility/presence.
FaceLandmarks     — 468 Landmark objects for one detected face.
FaceMeshResult    — aggregated output of one inference pass over one frame.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Landmark:
    """
    A single normalised facial landmark point.

    Coordinates are in the range [0.0, 1.0] relative to image width and
    height.  The z-coordinate is relative to the image width and represents
    depth — a more negative value means closer to the camera.

    Attributes:
        x:          Normalised x coordinate in [0, 1].
        y:          Normalised y coordinate in [0, 1].
        z:          Normalised depth coordinate (relative to image width).
        visibility: Score in [0, 1] indicating whether the landmark is
                    visible, or ``None`` if the model does not produce this.
        presence:   Score in [0, 1] indicating whether the landmark is
                    present on-screen, or ``None`` if unavailable.
        index:      Zero-based index of this landmark within the face mesh
                    (0 – 467 for canonical face mesh).
    """
    x: float
    y: float
    z: float
    visibility: Optional[float] = None
    presence: Optional[float] = None
    index: int = 0


@dataclass
class FaceLandmarks:
    """
    All landmarks extracted from a single detected face.

    Attributes:
        landmarks:      Ordered list of Landmark objects.  The position of
                        each landmark within this list corresponds to its
                        MediaPipe face-mesh index (0 – 467 canonical).
        landmark_count: Number of landmarks in this face (``len(landmarks)``).
        face_index:     Zero-based index of this face within the frame.
        detection_confidence: Detection confidence reported by the underlying
                        model, or ``None`` if unavailable.
    """
    landmarks: List[Landmark]
    landmark_count: int
    face_index: int
    detection_confidence: Optional[float] = None

    def __post_init__(self) -> None:
        # Keep landmark_count consistent with actual list length
        if self.landmark_count != len(self.landmarks):
            self.landmark_count = len(self.landmarks)

    def get(self, index: int) -> Optional[Landmark]:
        """Returns the landmark at *index*, or ``None`` if out of bounds."""
        if 0 <= index < len(self.landmarks):
            return self.landmarks[index]
        return None


@dataclass
class FaceMeshResult:
    """
    Aggregated output of one face landmark inference pass on a single frame.

    Attributes:
        face_landmarks:     Per-face FaceLandmarks objects, ordered by face
                            index.  Empty when no faces are detected.
        face_count:         Number of faces for which landmarks were
                            successfully extracted.
        frame_id:           Identifier of the source frame.
        processing_timestamp: Unix epoch time (seconds) when inference
                            completed.
        processing_time_ms: Wall-clock inference duration in milliseconds.
        frame_width:        Width of the source frame in pixels.
        frame_height:       Height of the source frame in pixels.
    """
    face_landmarks: List[FaceLandmarks]
    face_count: int
    frame_id: Optional[int]
    processing_timestamp: float
    processing_time_ms: float
    frame_width: int
    frame_height: int

    def __post_init__(self) -> None:
        if self.face_count != len(self.face_landmarks):
            self.face_count = len(self.face_landmarks)

    # ------------------------------------------------------------------ #
    #  Convenience accessors                                               #
    # ------------------------------------------------------------------ #

    @property
    def is_face_detected(self) -> bool:
        """True when landmarks were extracted for at least one face."""
        return self.face_count > 0

    @property
    def primary_landmarks(self) -> Optional[FaceLandmarks]:
        """Returns the first face's landmarks, or ``None`` if none found."""
        return self.face_landmarks[0] if self.face_landmarks else None

    def get_face(self, face_index: int) -> Optional[FaceLandmarks]:
        """Returns landmarks for face at *face_index*, or ``None``."""
        if 0 <= face_index < len(self.face_landmarks):
            return self.face_landmarks[face_index]
        return None
