"""
Model configuration for the Object Tracking Feature.
"""
from dataclasses import dataclass

@dataclass
class ObjectTrackingConfig:
    """
    Configuration for the Object Tracker.
    
    Attributes:
        tracking_confidence: Minimum confidence threshold for initializing or updating tracks.
        max_lost_frames: Maximum number of frames a track can be lost before it is removed.
        min_confirmed_frames: Number of consecutive frames needed to confirm a new track.
        tracking_timeout: Time in seconds before a lost track is forcefully removed.
        matching_threshold: The IoU threshold for matching a detection to an existing track.
        enable_logging: Emit diagnostics at DEBUG level.
    """
    tracking_confidence: float = 0.4
    max_lost_frames: int = 30
    min_confirmed_frames: int = 3
    tracking_timeout: float = 5.0
    matching_threshold: float = 0.8
    enable_logging: bool = True
