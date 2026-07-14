"""
Blink Detection Feature Module.

Responsible ONLY for detecting eye blinks using the temporal sequence of EAR values.
"""
from ai_engine.features.blink_detection.exceptions import BlinkDetectionError, InvalidEARDataError, TemporalProcessingError
from ai_engine.features.blink_detection.models import BlinkDetectionConfig
from ai_engine.features.blink_detection.result import BlinkDetectionResult, BlinkState, BlinkStatistics
from ai_engine.features.blink_detection.processor import BlinkDetectionProcessor
from ai_engine.features.blink_detection.temporal_processor import TemporalBlinkProcessor

__all__ = [
    "BlinkDetectionError",
    "InvalidEARDataError",
    "TemporalProcessingError",
    "BlinkDetectionConfig",
    "BlinkDetectionResult",
    "BlinkState",
    "BlinkStatistics",
    "BlinkDetectionProcessor",
    "TemporalBlinkProcessor"
]
