"""
Temporal Face Presence Processor implementation.
"""
import time
import logging
from typing import Tuple

from ai_engine.core.exam_context import ExamContext
from ai_engine.features.face_presence.processor import FacePresenceProcessor
from ai_engine.features.face_presence.models import FacePresenceConfig
from ai_engine.features.face_presence.result import PresenceState
from ai_engine.features.face_presence.exceptions import FacePresenceError

logger = logging.getLogger(__name__)


class TemporalFacePresenceProcessor(FacePresenceProcessor):
    """
    Monitors face presence using temporal sequence of face detections.
    """
    
    def __init__(self, config: FacePresenceConfig) -> None:
        super().__init__(config)
        self._initialized = False
        self._reset_state()

    def _reset_state(self) -> None:
        """Resets the internal temporal state."""
        self._presence_state = PresenceState.PRESENT
        self._consecutive_missing_frames = 0
        self._consecutive_present_frames = 0
        
        self._current_absence_start_time = 0.0
        
        # Statistics
        self._present_duration = 0.0
        self._absent_duration = 0.0
        self._longest_absence = 0.0
        
        self._last_processed_timestamp = 0.0

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing TemporalFacePresenceProcessor...")
        self._reset_state()
        self._initialized = True
        if self._config.enable_logging:
            logger.debug("TemporalFacePresenceProcessor initialized successfully.")

    def start(self) -> None:
        if not self._initialized:
            raise FacePresenceError("Cannot start uninitialized processor.")
        self._reset_state()
        if self._config.enable_logging:
            logger.debug("TemporalFacePresenceProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("TemporalFacePresenceProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up TemporalFacePresenceProcessor...")
        self._initialized = False
        self._reset_state()
        if self._config.enable_logging:
            logger.debug("TemporalFacePresenceProcessor cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads face_info and updates presence metrics.
        """
        if not self._initialized:
            raise FacePresenceError("Processor is not initialized.")

        try:
            start_time = time.perf_counter()
            
            face_info = context.face_info
            
            current_timestamp = face_info.detection_timestamp
            if current_timestamp <= 0.0:
                 current_timestamp = time.time()
            
            if self._last_processed_timestamp > 0.0:
                time_delta = current_timestamp - self._last_processed_timestamp
            else:
                time_delta = 0.0
                
            self._last_processed_timestamp = current_timestamp
            
            face_count = face_info.face_count
            confidence = face_info.confidence
            bbox = face_info.bbox
            
            # Determine immediate presence
            # Must have at least 1 face and confidence above threshold
            # If no face is detected, bbox is usually (0,0,0,0) and confidence 0
            is_currently_present = (face_count > 0 and confidence >= self._config.min_face_confidence)
            
            # Additional flags
            partial_visibility_flag = False
            occlusion_flag = False
            
            if is_currently_present:
                # Check for partial visibility (bbox intersects with edges [0, 1] for normalized)
                # We assume bbox is normalized (x, y, w, h). If it's pixel, this logic relies on normalization or edge margin.
                # Since we don't have image dimensions, we check if it's close to 0 or 1.
                x, y, w, h = bbox
                margin = self._config.edge_margin
                if (x <= margin or y <= margin or 
                    x + w >= 1.0 - margin or y + h >= 1.0 - margin):
                    # But if w or h is 0, it might be invalid
                    if w > 0 and h > 0:
                        partial_visibility_flag = True
                
                # If confidence is lower than a very safe margin (e.g., < 0.7) but still present, might be occluded
                if self._config.min_face_confidence <= confidence < 0.7:
                     occlusion_flag = True
            else:
                 if face_count > 0 and confidence > 0.1:
                     # Face detected but very low confidence -> likely occluded
                     occlusion_flag = True
            
            # State Machine Update
            if is_currently_present:
                self._consecutive_missing_frames = 0
                self._consecutive_present_frames += 1
                
                if self._presence_state == PresenceState.MISSING:
                    # Check if we should transition back to PRESENT
                    if self._consecutive_present_frames >= self._config.presence_stability_window_frames:
                        self._presence_state = PresenceState.PRESENT
                        # Calculate final absence duration for this gap
                        absence_duration = current_timestamp - self._current_absence_start_time
                        if absence_duration > self._longest_absence:
                             self._longest_absence = absence_duration
                        self._current_absence_start_time = 0.0
                        if self._config.enable_logging:
                            logger.debug("Presence restored.")
                
            else:
                self._consecutive_present_frames = 0
                self._consecutive_missing_frames += 1
                
                if self._presence_state == PresenceState.PRESENT:
                    # Check if we should transition to MISSING
                    # Transition based on either frame count or time duration
                    
                    # We start tracking absence duration at the first missing frame
                    if self._current_absence_start_time == 0.0:
                        self._current_absence_start_time = current_timestamp
                        
                    current_absence_duration = (current_timestamp - self._current_absence_start_time) * 1000.0
                    
                    if (self._consecutive_missing_frames >= self._config.max_missing_frames or 
                        current_absence_duration >= self._config.max_absence_duration_ms):
                        
                        self._presence_state = PresenceState.MISSING
                        if self._config.enable_logging:
                            logger.debug("Presence lost (MISSING).")
            
            # Update Statistics
            if self._presence_state == PresenceState.PRESENT:
                 self._present_duration += time_delta
            else:
                 self._absent_duration += time_delta
                 # Update longest absence continuously while missing
                 if self._current_absence_start_time > 0.0:
                     current_absence_s = current_timestamp - self._current_absence_start_time
                     if current_absence_s > self._longest_absence:
                          self._longest_absence = current_absence_s

            # Write back to Context
            end_time = time.perf_counter()
            processing_time = (end_time - start_time) * 1000.0
            
            face_info.presence_state = self._presence_state
            face_info.presence_confidence = confidence if is_currently_present else 0.0
            face_info.present_duration = self._present_duration
            face_info.absent_duration = self._absent_duration
            face_info.longest_absence = self._longest_absence
            face_info.consecutive_missing_frames = self._consecutive_missing_frames
            face_info.consecutive_present_frames = self._consecutive_present_frames
            face_info.partial_visibility_flag = partial_visibility_flag
            face_info.occlusion_flag = occlusion_flag
            face_info.processing_timestamp = time.time()
            face_info.processing_time_ms = processing_time
            
            context.face_info = face_info
            
        except FacePresenceError:
            raise
        except Exception as e:
            if self._config.enable_logging:
                logger.error(f"Unexpected error in TemporalFacePresenceProcessor: {e}")
            raise FacePresenceError(f"Unexpected error processing face presence: {e}") from e
