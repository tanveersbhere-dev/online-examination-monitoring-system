"""
ByteTrack style Object Tracker implementation.
"""
import time
import logging
from typing import List, Dict, Optional

from ai_engine.core.exam_context import ExamContext, TrackedObject, TrackingStatistics
from ai_engine.environment.object_tracking.tracker import ObjectTrackerInterface
from ai_engine.environment.object_tracking.models import ObjectTrackingConfig
from ai_engine.environment.object_tracking.exceptions import ObjectTrackingError, TrackingFailureError

logger = logging.getLogger(__name__)

class ByteTrackTracker(ObjectTrackerInterface):
    """
    Implements a multi-object tracker imitating ByteTrack logic (IoU-based matching over active tracks)
    using the abstract interfaces. Does not rely on external lap or filterpy packages to remain
    compatible with purely offline, mockable test environments.
    """
    
    def __init__(self, config: ObjectTrackingConfig) -> None:
        super().__init__(config)
        self._initialized = False
        self._next_id = 1
        self._tracks: Dict[int, TrackedObject] = {}
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing ByteTrackTracker...")
        self._initialized = True
        self._next_id = 1
        self._tracks.clear()
        if self._config.enable_logging:
            logger.debug("ByteTrackTracker initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise ObjectTrackingError("Cannot start uninitialized ByteTrackTracker.")
        if self._config.enable_logging:
            logger.debug("ByteTrackTracker started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("ByteTrackTracker stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up ByteTrackTracker...")
        self._initialized = False
        self._tracks.clear()
        if self._config.enable_logging:
            logger.debug("ByteTrackTracker cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads filtered detections, updates tracks, and sets tracked_objects.
        """
        if not self._initialized:
            raise ObjectTrackingError("Tracker is not initialized.")
            
        start_time = time.perf_counter()
        
        object_info = context.object_info
        detections = object_info.filtered_detections
        current_time = time.time()
        frame_id = object_info.frame_id
        
        stats = TrackingStatistics()
        stats.active_tracks = 0
        
        try:
            # ByteTrack Two-Step Association
            high_dets = []
            low_dets = []
            
            for det in detections:
                if det.confidence >= self._config.tracking_confidence:
                    high_dets.append(det)
                else:
                    low_dets.append(det)
                    
            unmatched_tracks = set(t_id for t_id, t in self._tracks.items() if t.current_state != 'REMOVED')
            matched_tracks = set()
            unmatched_high_dets = []
            
            # Step 1: Match high confidence detections
            for det in high_dets:
                best_iou = 0.0
                best_track_id = None
                
                for t_id in list(unmatched_tracks):
                    track = self._tracks[t_id]
                    if track.object_type != det.object_type:
                        continue
                        
                    iou = self._calculate_iou(det.bbox, track.bbox)
                    if iou > self._config.matching_threshold and iou > best_iou:
                        best_iou = iou
                        best_track_id = t_id
                        
                if best_track_id is not None:
                    # Update track
                    track = self._tracks[best_track_id]
                    if track.current_state == 'LOST':
                        stats.recovered_tracks += 1
                    track.current_state = 'TRACKED'
                    track.bbox = det.bbox
                    track.confidence = det.confidence
                    track.last_detection_timestamp = current_time
                    track.visible_duration = current_time - track.first_detection_timestamp
                    track.consecutive_frames += 1
                    track.lost_frames = 0
                    track.frame_id = frame_id
                    
                    matched_tracks.add(best_track_id)
                    unmatched_tracks.remove(best_track_id)
                else:
                    unmatched_high_dets.append(det)
                    
            # Step 2: Match remaining unmatched tracks with low confidence detections
            for det in low_dets:
                best_iou = 0.0
                best_track_id = None
                
                for t_id in list(unmatched_tracks):
                    track = self._tracks[t_id]
                    # Only try to match low dets to tracks that are currently active (not newly lost)
                    if track.current_state != 'TRACKED':
                        continue
                    if track.object_type != det.object_type:
                        continue
                        
                    iou = self._calculate_iou(det.bbox, track.bbox)
                    # Use a potentially lower matching threshold for low dets if needed, or same
                    if iou > self._config.matching_threshold * 0.8 and iou > best_iou:
                        best_iou = iou
                        best_track_id = t_id
                        
                if best_track_id is not None:
                    # Update track
                    track = self._tracks[best_track_id]
                    track.bbox = det.bbox
                    track.confidence = det.confidence
                    track.last_detection_timestamp = current_time
                    track.visible_duration = current_time - track.first_detection_timestamp
                    track.consecutive_frames += 1
                    track.lost_frames = 0
                    track.frame_id = frame_id
                    
                    matched_tracks.add(best_track_id)
                    unmatched_tracks.remove(best_track_id)
                    
            # Step 3: Handle unmatched tracks (mark LOST or REMOVED)
            for t_id in unmatched_tracks:
                track = self._tracks[t_id]
                track.lost_frames += 1
                track.consecutive_frames = 0
                
                if track.lost_frames >= self._config.max_lost_frames or \
                   (current_time - track.last_detection_timestamp) >= self._config.tracking_timeout:
                    track.current_state = 'REMOVED'
                    stats.removed_tracks += 1
                else:
                    if track.current_state != 'LOST':
                        track.current_state = 'LOST'
                        stats.lost_tracks += 1
                        
            # Step 4: Handle unmatched high confidence detections (mark NEW)
            # Unmatched low confidence detections are ignored.
            for det in unmatched_high_dets:
                new_track = TrackedObject(
                    tracking_id=self._next_id,
                    object_type=det.object_type,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    current_state='NEW',
                    first_detection_timestamp=current_time,
                    last_detection_timestamp=current_time,
                    visible_duration=0.0,
                    consecutive_frames=1,
                    lost_frames=0,
                    motion_status='STATIONARY', # basic default
                    frame_id=frame_id
                )
                self._tracks[self._next_id] = new_track
                self._next_id += 1
                stats.new_tracks += 1
                
            # Clean out REMOVED tracks from internal memory to prevent bloat
            self._tracks = {tid: t for tid, t in self._tracks.items() if t.current_state != 'REMOVED'}
            
            # Formulate final output
            active_objects = []
            for t in self._tracks.values():
                if t.current_state in ['NEW', 'TRACKED', 'LOST']:
                    # Only confirm if consecutive frames >= min_confirmed_frames (for 'TRACKED')
                    # But we'll output NEW as well, allowing downstream to decide if it trusts NEW
                    active_objects.append(t)
                    
            stats.active_tracks = len(active_objects)
            
            end_time = time.perf_counter()
            proc_time_ms = (end_time - start_time) * 1000.0
            
            # Update Context
            object_info.tracked_objects = active_objects
            object_info.tracking_statistics = stats
            object_info.tracking_processing_time_ms = proc_time_ms
            context.object_info = object_info
            
            if self._config.enable_logging:
                logger.debug(f"Tracking updated: {stats.active_tracks} active, {stats.new_tracks} new, {stats.lost_tracks} lost in {proc_time_ms:.2f}ms")
                
        except Exception as e:
            raise TrackingFailureError(f"Failed to process tracking: {e}") from e

    def _calculate_iou(self, boxA, boxB) -> float:
        xA = max(boxA.x, boxB.x)
        yA = max(boxA.y, boxB.y)
        xB = min(boxA.x + boxA.width, boxB.x + boxB.width)
        yB = min(boxA.y + boxA.height, boxB.y + boxB.height)

        interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
        if interArea == 0.0:
            return 0.0

        boxAArea = boxA.width * boxA.height
        boxBArea = boxB.width * boxB.height

        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou
