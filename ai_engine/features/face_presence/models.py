"""
Model configuration for the Face Presence Monitor Feature.
"""
from dataclasses import dataclass

@dataclass
class FacePresenceConfig:
    """
    Configuration for the Temporal Face Presence Processor.
    
    Attributes:
        max_missing_frames: Max consecutive missing frames before state changes to MISSING.
        max_absence_duration_ms: Max duration in ms to tolerate absence before registering a confirmed absence.
        min_face_confidence: Minimum face detection confidence to be considered valid presence.
        presence_stability_window_frames: Minimum consecutive present frames required to transition back to PRESENT.
        edge_margin: Margin in normalized coordinates [0, 1] to consider a face partially visible/cut off.
        enable_logging: Emit per-frame diagnostics at DEBUG level.
    """
    max_missing_frames: int = 5
    max_absence_duration_ms: float = 2000.0
    min_face_confidence: float = 0.5
    presence_stability_window_frames: int = 3
    edge_margin: float = 0.05
    enable_logging: bool = True
