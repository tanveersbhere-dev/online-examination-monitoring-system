"""
Temporal Blink Processor implementation.
"""
import time
import logging
from typing import List, Tuple
from collections import deque

from ai_engine.core.exam_context import ExamContext
from ai_engine.features.blink_detection.processor import BlinkDetectionProcessor
from ai_engine.features.blink_detection.models import BlinkDetectionConfig
from ai_engine.features.blink_detection.result import BlinkState, BlinkStatistics
from ai_engine.features.blink_detection.exceptions import BlinkDetectionError, InvalidEARDataError

logger = logging.getLogger(__name__)


class TemporalBlinkProcessor(BlinkDetectionProcessor):
    """
    Detects blinks using temporal EAR values.
    """
    
    def __init__(self, config: BlinkDetectionConfig) -> None:
        super().__init__(config)
        self._initialized = False
        self._reset_state()

    def _reset_state(self) -> None:
        """Resets the internal temporal state."""
        self._consecutive_closed_frames = 0
        self._eye_state = BlinkState.OPEN
        self._blink_start_timestamp = 0.0
        self._total_blinks = 0
        
        # Deque for tracking blink timestamps to calculate frequency
        self._blink_history: deque = deque()

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing TemporalBlinkProcessor...")
        self._reset_state()
        self._initialized = True
        if self._config.enable_logging:
            logger.debug("TemporalBlinkProcessor initialized successfully.")

    def start(self) -> None:
        if not self._initialized:
            raise BlinkDetectionError("Cannot start uninitialized processor.")
        self._reset_state()
        if self._config.enable_logging:
            logger.debug("TemporalBlinkProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("TemporalBlinkProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up TemporalBlinkProcessor...")
        self._initialized = False
        self._reset_state()
        if self._config.enable_logging:
            logger.debug("TemporalBlinkProcessor cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads EAR from eye_info and updates blink metrics in eye_info.
        """
        if not self._initialized:
            raise BlinkDetectionError("Processor is not initialized.")

        try:
            start_time = time.perf_counter()
            
            # Read from ExamContext.eye_info (Deepcopy is done by the property, so we are working with a copy)
            eye_info = context.eye_info
            
            # Use average EAR for robust blink detection
            ear = eye_info.average_ear
            current_timestamp = eye_info.processing_timestamp
            
            if current_timestamp <= 0.0:
                current_timestamp = time.time()
                
            if ear == 0.0 and eye_info.ear_confidence == 0.0:
                # If EAR is exactly 0 and no confidence, it might mean no face was detected.
                # Do not increment blinks, reset frames.
                self._consecutive_closed_frames = 0
                self._eye_state = BlinkState.OPEN
                self._update_context(context, eye_info, False, 0.0, 0.0, start_time)
                return
                
            if ear < 0.0:
                raise InvalidEARDataError(f"Invalid EAR value: {ear}")

            blink_detected = False
            blink_end_timestamp = 0.0
            blink_duration = 0.0

            # State Machine: OPEN <-> CLOSED
            if ear < self._config.ear_threshold:
                self._consecutive_closed_frames += 1
                
                # Check if we should transition to CLOSED state
                if self._eye_state == BlinkState.OPEN and self._consecutive_closed_frames >= self._config.min_consecutive_frames:
                    self._eye_state = BlinkState.CLOSED
                    self._blink_start_timestamp = current_timestamp
                    if self._config.enable_logging:
                        logger.debug("Eye state changed to CLOSED.")
            else:
                # Eye is OPEN
                if self._eye_state == BlinkState.CLOSED:
                    # Eye just opened, calculate duration
                    duration_s = current_timestamp - self._blink_start_timestamp
                    duration_ms = duration_s * 1000.0
                    
                    if self._config.min_blink_duration_ms <= duration_ms <= self._config.max_blink_duration_ms:
                        # Valid blink
                        blink_detected = True
                        blink_end_timestamp = current_timestamp
                        blink_duration = duration_ms
                        self._total_blinks += 1
                        self._blink_history.append(current_timestamp)
                        if self._config.enable_logging:
                            logger.debug(f"Valid blink detected. Duration: {duration_ms:.2f}ms")
                    else:
                        if self._config.enable_logging:
                            logger.debug(f"Invalid blink duration: {duration_ms:.2f}ms")
                            
                    self._eye_state = BlinkState.OPEN
                
                # Reset consecutive frames
                self._consecutive_closed_frames = 0

            # Update rolling frequency
            self._prune_history(current_timestamp)
            rolling_freq = self._calculate_frequency()

            # Write back to context
            self._update_context(context, eye_info, blink_detected, blink_end_timestamp, blink_duration, start_time)
            
            # Also update legacy blink count and freq for backward compatibility if needed, 
            # though instruction says populate specific fields.
            
        except BlinkDetectionError:
            raise
        except Exception as e:
            if self._config.enable_logging:
                logger.error(f"Unexpected error in TemporalBlinkProcessor: {e}")
            raise BlinkDetectionError(f"Unexpected error processing blink: {e}") from e

    def _update_context(self, context: ExamContext, eye_info, blink_detected: bool, blink_end_timestamp: float, blink_duration: float, start_time: float) -> None:
        """Helper to write metrics back to the ExamContext."""
        end_time = time.perf_counter()
        
        eye_info.blink_detected = blink_detected
        if blink_detected:
            eye_info.blink_end_timestamp = blink_end_timestamp
            eye_info.blink_duration = blink_duration
            
        eye_info.blink_start_timestamp = self._blink_start_timestamp if self._eye_state == BlinkState.CLOSED else 0.0
        eye_info.blink_frequency = self._calculate_frequency()
        eye_info.consecutive_closed_frames = self._consecutive_closed_frames
        eye_info.eye_state = self._eye_state
        eye_info.blink_count = self._total_blinks
        
        # We don't overwrite the original processing timestamp, we just update the time taken
        eye_info.processing_time_ms += (end_time - start_time) * 1000.0
        
        context.eye_info = eye_info

    def _prune_history(self, current_timestamp: float) -> None:
        """Remove timestamps older than the frequency window."""
        cutoff_time = current_timestamp - self._config.frequency_window_seconds
        while self._blink_history and self._blink_history[0] < cutoff_time:
            self._blink_history.popleft()

    def _calculate_frequency(self) -> float:
        """Calculate blinks per minute."""
        count = len(self._blink_history)
        if self._config.frequency_window_seconds == 0:
            return 0.0
        return (count / self._config.frequency_window_seconds) * 60.0
