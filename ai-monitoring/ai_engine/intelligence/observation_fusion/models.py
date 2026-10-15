"""Models for Observation Fusion."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ObservationFusionConfig:
    """Configuration for what sub-systems to enforce."""
    enable_face: bool = True
    enable_environment: bool = True
    enable_audio: bool = False
    enable_logging: bool = True

@dataclass
class FaceObservation:
    """Normalized Face intelligence data."""
    face_present: bool = False
    face_count: int = 1
    presence_state: str = "PRESENT"
    face_confidence: float = 0.0
    identity_consistent: bool = True
    identity_confidence: float = 0.0
    gaze_state: str = "UNKNOWN" # E.g., CENTER, LEFT, RIGHT
    gaze_confidence: float = 0.0
    head_pose_state: str = "UNKNOWN" # E.g., FORWARD, UP, DOWN, LEFT, RIGHT
    is_talking: bool = False
    blink_state: str = "UNKNOWN"
    # Provide a simple flat structure for the behavior summaries if needed
    behavioral_summary: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EnvironmentObservation:
    """Normalized Environment intelligence data."""
    active_objects: int = 0
    total_persons: int = 0
    phone_present: bool = False
    book_present: bool = False
    earphone_present: bool = False
    earbuds_present: bool = False
    neckband_present: bool = False
    register_present: bool = False
    laptop_present: bool = False
    smartwatch_present: bool = False
    # Summarized bounding box or tracking metadata
    tracked_entities_summary: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AudioObservation:
    """Normalized Audio intelligence data."""
    is_speaking: bool = False
    decibel_level: float = 0.0
    noise_level: float = 0.0

@dataclass
class ObservationConfidenceSummary:
    """Summarized confidence across the active modalities."""
    face_confidence: float = 0.0
    environment_confidence: float = 0.0
    audio_confidence: float = 0.0
    overall_confidence: float = 0.0

@dataclass
class UnifiedObservation:
    """The root unified observation structure."""
    timestamp: float = 0.0
    face: Optional[FaceObservation] = None
    environment: Optional[EnvironmentObservation] = None
    audio: Optional[AudioObservation] = None
    confidence_summary: ObservationConfidenceSummary = field(default_factory=ObservationConfidenceSummary)
    identity_protection: Optional[Any] = None
    calibration: Optional[Dict[str, Any]] = None
