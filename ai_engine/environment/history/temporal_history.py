"""Environment History Engine implementation."""
import time
import logging
from typing import Dict, List, Set, Any

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import ExamContext
from ai_engine.environment.history.processor import EnvironmentHistoryProcessorInterface
from ai_engine.environment.history.models import (
    HistoryConfig, 
    EnvironmentHistory, 
    TrackedObjectHistory, 
    EnvironmentStatistics
)
from ai_engine.environment.history.rolling_window import RollingWindowTimeSeries
from ai_engine.environment.history.exceptions import EnvironmentHistoryError, HistoryOverflowError, HistoryProcessingError

logger = logging.getLogger(__name__)

class TemporalHistoryEngine(EnvironmentHistoryProcessorInterface):
    """
    Maintains historical information about tracked examination-related objects.
    """
    
    def __init__(self, config: HistoryConfig) -> None:
        super().__init__(config)
        self._initialized = False
        self._object_histories: Dict[int, TrackedObjectHistory] = {}
        self._stats = EnvironmentStatistics()
        
        # Max window size required
        max_window = max(self._config.history_window_sizes) if self._config.history_window_sizes else 30
        self._person_count_series = RollingWindowTimeSeries(max_window + 1.0)
        self._objects_per_frame_series = RollingWindowTimeSeries(max_window + 1.0)
        
        self._last_cleanup_time = 0.0
        self._last_summary_time = 0.0
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing TemporalHistoryEngine...")
        self._initialized = True
        self._object_histories.clear()
        self._person_count_series = RollingWindowTimeSeries(
            max(self._config.history_window_sizes) if self._config.history_window_sizes else 30
        )
        self._objects_per_frame_series = RollingWindowTimeSeries(
            max(self._config.history_window_sizes) if self._config.history_window_sizes else 30
        )
        if self._config.enable_logging:
            logger.debug("TemporalHistoryEngine initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise EnvironmentHistoryError("Cannot start uninitialized engine.")
        if self._config.enable_logging:
            logger.debug("TemporalHistoryEngine started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("TemporalHistoryEngine stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up TemporalHistoryEngine...")
        self._initialized = False
        self._object_histories.clear()
        if self._config.enable_logging:
            logger.debug("TemporalHistoryEngine cleaned up.")

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            raise EnvironmentHistoryError("Engine is not initialized.")
            
        try:
            start_time = time.perf_counter()
            current_time = time.time()
            
            # Extract inputs securely
            tracked_objects = getattr(context.object_info, "tracked_objects", [])
            evidence_snapshots = getattr(context.object_info, "evidence", [])
            
            # Update individual object histories
            active_ids = self._update_object_histories(tracked_objects, evidence_snapshots, current_time)
            
            # Handle periodic cleanup to prevent overflow
            if current_time - self._last_cleanup_time > self._config.cleanup_interval_seconds:
                self._cleanup_stale_histories(current_time)
                self._last_cleanup_time = current_time
                
            # Perform bounds checking
            if len(self._object_histories) > self._config.max_history_size:
                raise HistoryOverflowError(f"Exceeded max history size of {self._config.max_history_size}")
                
            # Update rolling windows
            person_count = sum(1 for t in tracked_objects if t.object_type == DetectedObjectType.PERSON)
            self._person_count_series.add(current_time, person_count)
            self._objects_per_frame_series.add(current_time, len(tracked_objects))
            
            # Update summaries periodically
            if current_time - self._last_summary_time > self._config.summary_interval_seconds:
                self._generate_summary(active_ids, current_time)
                self._last_summary_time = current_time
                
            self._stats.processing_timestamp = current_time
            
            # Assign to context dynamically (do not modify frozen module structure)
            final_history = EnvironmentHistory(
                object_histories=self._object_histories.copy(),
                statistics=self._stats
            )
            setattr(context, "environment_history", final_history)
            
            if self._config.enable_logging:
                proc_time_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"History processed in {proc_time_ms:.2f}ms. Total tracked histories: {len(self._object_histories)}")
                
        except Exception as e:
            if isinstance(e, HistoryOverflowError):
                raise
            raise HistoryProcessingError(f"Failed to process history: {e}") from e

    def _update_object_histories(self, tracked_objects: List[Any], evidence_snapshots: List[Any], current_time: float) -> Set[int]:
        active_ids = set()
        
        # Pre-map evidence to track IDs
        evidence_map = {}
        for ev in evidence_snapshots:
            if ev.track_id not in evidence_map:
                evidence_map[ev.track_id] = []
            evidence_map[ev.track_id].append(ev.snapshot_id)
            
        for track in tracked_objects:
            t_id = track.tracking_id
            active_ids.add(t_id)
            
            # Creation
            if t_id not in self._object_histories:
                self._object_histories[t_id] = TrackedObjectHistory(
                    track_id=t_id,
                    object_type=track.object_type,
                    first_seen_timestamp=current_time
                )
                
            hist = self._object_histories[t_id]
            
            # Updates
            hist.last_seen_timestamp = current_time
            hist.current_state = track.current_state
            
            if track.current_state in ["NEW", "TRACKED"]:
                hist.consecutive_visible_frames += 1
                hist.consecutive_missing_frames = 0
                hist.appearance_count += 1
                hist.total_visible_duration = current_time - hist.first_seen_timestamp
                
                # Running averages (approximation for memory efficiency)
                if hist.appearance_count == 1:
                    hist.average_detection_confidence = track.confidence
                    hist.average_bbox_area = track.bbox.width * track.bbox.height
                else:
                    alpha = 1.0 / hist.appearance_count
                    hist.average_detection_confidence = (1 - alpha) * hist.average_detection_confidence + alpha * track.confidence
                    area = track.bbox.width * track.bbox.height
                    hist.average_bbox_area = (1 - alpha) * hist.average_bbox_area + alpha * area
                    
                # Max/Min
                hist.max_detection_confidence = max(hist.max_detection_confidence, track.confidence)
                hist.min_detection_confidence = min(hist.min_detection_confidence, track.confidence)
                
                area = track.bbox.width * track.bbox.height
                hist.max_bbox_area = max(hist.max_bbox_area, area)
                
            elif track.current_state == "LOST":
                hist.consecutive_missing_frames += 1
                hist.consecutive_visible_frames = 0
                
            # Attach new evidence if any
            if t_id in evidence_map:
                for s_id in evidence_map[t_id]:
                    if s_id not in hist.snapshot_references:
                        hist.snapshot_references.append(s_id)
                        
        return active_ids

    def _cleanup_stale_histories(self, current_time: float) -> None:
        stale_ids = []
        for t_id, hist in self._object_histories.items():
            if hist.current_state == "REMOVED":
                # Expire if it has been removed and unseen for a long time
                if current_time - hist.last_seen_timestamp > self._config.history_expiration_seconds:
                    stale_ids.append(t_id)
                    
        for t_id in stale_ids:
            del self._object_histories[t_id]
            
        if self._config.enable_logging and stale_ids:
            logger.debug(f"Cleaned up {len(stale_ids)} stale object histories.")

    def _generate_summary(self, active_ids: Set[int], current_time: float) -> None:
        self._stats.total_object_count = len(self._object_histories)
        self._stats.active_object_count = len(active_ids)
        self._stats.historical_object_count = self._stats.total_object_count - self._stats.active_object_count
        
        # Calculate max person count per configured window
        for w_size in self._config.history_window_sizes:
            self._stats.person_count_history[w_size] = self._person_count_series.get_max_in_window(current_time, w_size)
            
        # Overall averages over the max window
        max_w = max(self._config.history_window_sizes) if self._config.history_window_sizes else 30
        self._stats.average_objects_per_frame = self._objects_per_frame_series.get_average_in_window(current_time, max_w)
        
        # Sum specific presence durations from active history
        phone_dur = 0.0
        book_dur = 0.0
        earphone_dur = 0.0
        smartwatch_dur = 0.0
        
        for hist in self._object_histories.values():
            if hist.object_type == DetectedObjectType.CELL_PHONE:
                phone_dur += hist.total_visible_duration
            elif hist.object_type == DetectedObjectType.BOOK:
                book_dur += hist.total_visible_duration
            elif hist.object_type == DetectedObjectType.EARPHONE:
                earphone_dur += hist.total_visible_duration
            elif hist.object_type == DetectedObjectType.SMARTWATCH:
                smartwatch_dur += hist.total_visible_duration
                
        self._stats.phone_presence_duration = phone_dur
        self._stats.book_presence_duration = book_dur
        self._stats.earphone_presence_duration = earphone_dur
        self._stats.smartwatch_presence_duration = smartwatch_dur
