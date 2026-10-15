"""
Object Tracking Feature Module (Environment Intelligence Stage 3).

Responsible ONLY for maintaining object identities across consecutive frames.
"""
from ai_engine.environment.object_tracking.exceptions import ObjectTrackingError, TrackerInitializationError, TrackingFailureError, InvalidTrackingStateError
from ai_engine.environment.object_tracking.models import ObjectTrackingConfig
from ai_engine.environment.object_tracking.result import ObjectTrackingResult
from ai_engine.environment.object_tracking.tracker import ObjectTrackerInterface
from ai_engine.environment.object_tracking.bytetrack_tracker import ByteTrackTracker

__all__ = [
    "ObjectTrackingError",
    "TrackerInitializationError",
    "TrackingFailureError",
    "InvalidTrackingStateError",
    "ObjectTrackingConfig",
    "ObjectTrackingResult",
    "ObjectTrackerInterface",
    "ByteTrackTracker"
]
