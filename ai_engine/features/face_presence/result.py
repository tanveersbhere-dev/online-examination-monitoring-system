"""
Strongly typed result objects for the Face Presence Feature module.
"""
from dataclasses import dataclass

@dataclass
class PresenceState:
    """
    State of face presence.
    """
    PRESENT = "PRESENT"
    MISSING = "MISSING"

@dataclass
class PresenceStatistics:
    """
    Statistics regarding face presence.
    
    Attributes:
        longest_absence: Longest duration (in ms) the face was continuously missing.
        present_duration: Total duration (in ms) the face was present.
        absent_duration: Total duration (in ms) the face was missing.
    """
    longest_absence: float
    present_duration: float
    absent_duration: float

@dataclass
class FacePresenceResult:
    """
    Result of temporal presence processing for a single frame.
    
    Attributes:
        presence_state: Current presence state (PRESENT or MISSING).
        presence_confidence: Confidence score of the presence.
        consecutive_missing_frames: Number of consecutive missing frames.
        consecutive_present_frames: Number of consecutive present frames.
        partial_visibility_flag: True if face is partially visible (intersecting edge).
        occlusion_flag: True if face is occluded (low confidence despite detection).
        statistics: Overall presence statistics.
        processing_timestamp: Unix epoch time when inference completed.
        processing_time_ms: Processing time in milliseconds.
    """
    presence_state: str
    presence_confidence: float
    consecutive_missing_frames: int
    consecutive_present_frames: int
    partial_visibility_flag: bool
    occlusion_flag: bool
    statistics: PresenceStatistics
    processing_timestamp: float
    processing_time_ms: float
