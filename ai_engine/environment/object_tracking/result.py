"""
Strongly typed result objects for the Object Tracking module.
"""
from dataclasses import dataclass, field
from typing import List

from ai_engine.core.exam_context import TrackedObject, TrackingStatistics

@dataclass
class ObjectTrackingResult:
    """
    Result of the object tracking process for a single frame.
    
    Attributes:
        tracked_objects: The list of currently active or lost tracks.
        statistics: Metrics on what tracks were created/lost/removed.
        processing_time_ms: Time taken to track.
    """
    tracked_objects: List[TrackedObject] = field(default_factory=list)
    statistics: TrackingStatistics = field(default_factory=TrackingStatistics)
    processing_time_ms: float = 0.0
