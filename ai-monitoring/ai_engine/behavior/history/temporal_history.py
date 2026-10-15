"""
Temporal History Processor implementation.
"""
import time
import logging
from typing import Dict

from ai_engine.core.exam_context import ExamContext, BehaviorHistory
from ai_engine.behavior.history.processor import BehaviorHistoryProcessor
from ai_engine.behavior.history.models import BehaviorHistoryConfig
from ai_engine.behavior.history.rolling_window import RollingWindow
from ai_engine.behavior.history.exceptions import BehaviorHistoryError

logger = logging.getLogger(__name__)

class TemporalHistoryProcessor(BehaviorHistoryProcessor):
    """
    Extracts metrics from features and maintains temporal history and statistics.
    """
    
    def __init__(self, config: BehaviorHistoryConfig) -> None:
        super().__init__(config)
        self._initialized = False
        # feature_name -> {window_size -> RollingWindow}
        self._windows: Dict[str, Dict[int, RollingWindow]] = {}
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing TemporalHistoryProcessor...")
            
        self._init_windows()
        self._initialized = True
        
        if self._config.enable_logging:
            logger.debug("TemporalHistoryProcessor initialized.")

    def _init_windows(self) -> None:
        self._windows.clear()
        features = [
            "head_pose_pitch", "head_pose_yaw", "head_pose_roll",
            "eye_gaze_horizontal", "eye_gaze_vertical",
            "mouth_mar", "eye_ear", "blink_detected",
            "presence_state", "identity_consistent"
        ]
        
        for feature in features:
            self._windows[feature] = {}
            for size in self._config.window_sizes_seconds:
                self._windows[feature][size] = RollingWindow(
                    window_size_seconds=float(size),
                    max_capacity=self._config.max_history_capacity
                )

    def start(self) -> None:
        if not self._initialized:
            raise BehaviorHistoryError("Cannot start uninitialized processor.")
        self._init_windows()
        if self._config.enable_logging:
            logger.debug("TemporalHistoryProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("TemporalHistoryProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up TemporalHistoryProcessor...")
        self._initialized = False
        self._windows.clear()
        if self._config.enable_logging:
            logger.debug("TemporalHistoryProcessor cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads all AI features and updates their rolling windows.
        """
        if not self._initialized:
            raise BehaviorHistoryError("Processor is not initialized.")

        try:
            start_time = time.perf_counter()
            current_timestamp = time.time()
            
            # Read inputs safely using context properties
            head_pose = context.head_pose_info
            gaze = context.eye_info
            mouth = context.mouth_info
            face = context.face_info
            
            # Extract discrete variables
            metrics = {
                "head_pose_pitch": head_pose.pitch,
                "head_pose_yaw": head_pose.yaw,
                "head_pose_roll": head_pose.roll,
                "eye_gaze_horizontal": gaze.horizontal_ratio if getattr(gaze, "horizontal_ratio", None) is not None else 0.0,
                "eye_gaze_vertical": gaze.vertical_ratio if getattr(gaze, "vertical_ratio", None) is not None else 0.0,
                "mouth_mar": getattr(mouth, "mar", 0.0),
                "eye_ear": getattr(gaze, "ear", 0.0),
                "blink_detected": getattr(gaze, "blink_detected", False),
                "presence_state": getattr(face, "presence_state", "PRESENT") == "PRESENT",
                "identity_consistent": getattr(face, "identity_consistent", True)
            }
            
            # Update windows
            behavior_history = context.behavior_history
            behavior_history.summaries.clear()
            
            for feature, value in metrics.items():
                if feature not in self._windows:
                    continue
                    
                behavior_history.summaries[feature] = {}
                for size, window in self._windows[feature].items():
                    window.append(current_timestamp, value)
                    summary = window.calculate_statistics(current_timestamp)
                    behavior_history.summaries[feature][size] = summary

            behavior_history.last_updated = current_timestamp
            
            # Save back to context
            context.behavior_history = behavior_history
            
            end_time = time.perf_counter()
            if self._config.enable_logging and (end_time - start_time) > 0.05:
                # Log if slow
                logger.debug(f"Behavior history update took {(end_time - start_time)*1000:.2f}ms")

        except HistoryOverflowError:
            raise
        except Exception as e:
            if self._config.enable_logging:
                logger.error(f"Unexpected error in TemporalHistoryProcessor: {e}")
            raise BehaviorHistoryError(f"Error processing temporal history: {e}") from e
