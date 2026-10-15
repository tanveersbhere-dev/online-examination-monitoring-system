"""
Strongly typed result objects for the Head Pose Estimation module.

No dictionaries, raw tuples, or anonymous structures are used.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class HeadPose:
    """
    Represents the estimated head pose for a single face.
    
    Attributes:
        pitch: Up/down rotation angle in degrees.
        yaw: Left/right rotation angle in degrees.
        roll: Tilt rotation angle in degrees.
        rotation_vector: The raw rotation vector from solvePnP.
        translation_vector: The raw translation vector from solvePnP.
        success: True if the estimation was successful.
        face_index: Zero-based index of the face in the frame.
    """
    pitch: float
    yaw: float
    roll: float
    rotation_vector: Tuple[float, float, float]
    translation_vector: Tuple[float, float, float]
    success: bool
    face_index: int


@dataclass
class HeadPoseResult:
    """
    Aggregated output of one head pose estimation pass on a single frame.
    
    Attributes:
        poses: Per-face HeadPose objects, ordered by face index.
        camera_matrix: The 3x3 camera matrix used for estimation.
        distortion_coefficients: The distortion coefficients used.
        frame_id: Identifier of the source frame.
        processing_timestamp: Unix epoch time (seconds) when inference completed.
        processing_time_ms: Wall-clock inference duration in milliseconds.
    """
    poses: List[HeadPose]
    camera_matrix: List[List[float]]
    distortion_coefficients: List[float]
    frame_id: Optional[int]
    processing_timestamp: float
    processing_time_ms: float
    
    @property
    def primary_pose(self) -> Optional[HeadPose]:
        """Returns the pose for the primary face (index 0), if available."""
        return self.poses[0] if self.poses else None
