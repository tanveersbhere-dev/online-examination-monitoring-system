"""
Strongly typed result objects for the Blink Detection Feature module.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class BlinkState:
    """
    State of the eye.
    """
    OPEN = "OPEN"
    CLOSED = "CLOSED"

@dataclass
class BlinkStatistics:
    """
    Blink statistics over time.
    
    Attributes:
        total_blinks: Total count of blinks detected in the session.
        rolling_frequency: Blinks per minute over the configured sliding window.
    """
    total_blinks: int
    rolling_frequency: float

@dataclass
class BlinkDetectionResult:
    """
    Result of temporal blink processing for a single frame.
    
    Attributes:
        blink_detected: True if a complete valid blink was just detected on this frame.
        eye_state: Current state of the eye (OPEN or CLOSED).
        consecutive_closed_frames: Number of consecutive frames the eye has been closed.
        blink_start_timestamp: Timestamp when the current blink started (if currently blinking).
        blink_end_timestamp: Timestamp when the blink ended.
        blink_duration: Duration of the last completed blink in milliseconds.
        statistics: Overall blink statistics.
        processing_timestamp: Unix epoch time when inference completed.
        processing_time_ms: Processing time in milliseconds.
    """
    blink_detected: bool
    eye_state: str
    consecutive_closed_frames: int
    blink_start_timestamp: float
    blink_end_timestamp: float
    blink_duration: float
    statistics: BlinkStatistics
    processing_timestamp: float
    processing_time_ms: float
