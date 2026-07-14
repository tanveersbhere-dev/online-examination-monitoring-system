"""
Face Presence Feature Module.

Responsible ONLY for monitoring whether the candidate remains continuously visible during the examination.
"""
from ai_engine.features.face_presence.exceptions import FacePresenceError, InvalidFaceStateError, PresenceMonitoringError
from ai_engine.features.face_presence.models import FacePresenceConfig
from ai_engine.features.face_presence.result import FacePresenceResult, PresenceState, PresenceStatistics
from ai_engine.features.face_presence.processor import FacePresenceProcessor
from ai_engine.features.face_presence.temporal_processor import TemporalFacePresenceProcessor

__all__ = [
    "FacePresenceError",
    "InvalidFaceStateError",
    "PresenceMonitoringError",
    "FacePresenceConfig",
    "FacePresenceResult",
    "PresenceState",
    "PresenceStatistics",
    "FacePresenceProcessor",
    "TemporalFacePresenceProcessor"
]
