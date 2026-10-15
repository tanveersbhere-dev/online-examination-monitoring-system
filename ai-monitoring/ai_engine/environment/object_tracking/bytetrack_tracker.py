"""
ByteTrack style Object Tracker implementation.
"""
import time
import logging
from typing import List, Dict, Optional

from ai_engine.core.exam_context import ExamContext, TrackedObject, TrackingStatistics
from ai_engine.core.enums import DetectedObjectType
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
        self._tracks_by_camera: Dict[str, Dict[int, TrackedObject]] = {}
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing ByteTrackTracker...")
        self._initialized = True
        self._next_id = 1
        self._tracks.clear()
        self._tracks_by_camera.clear()
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
        self._tracks_by_camera.clear()
        if self._config.enable_logging:
            logger.debug("ByteTrackTracker cleaned up.")

    def clear_camera(self, camera_id: str) -> None:
        """Purges active tracks for a specific camera (e.g. on camera disconnect)."""
        if camera_id in self._tracks_by_camera:
            self._tracks_by_camera[camera_id].clear()
            self._tracks = {tid: t for ctracks in self._tracks_by_camera.values() for tid, t in ctracks.items()}

    def process(self, context: ExamContext) -> None:
        """
        Reads filtered detections, updates tracks, and sets tracked_objects.
        Tracks are strictly partitioned by camera_id so Camera 1 frames never expire or remove Camera 2 tracks.
        """
        if not self._initialized:
            raise ObjectTrackingError("Tracker is not initialized.")
            
        start_time = time.perf_counter()
        
        curr_frame = getattr(context, "current_frame", None)
        cam_id = str(getattr(curr_frame, "camera_id", "camera_1") or "camera_1")
        if cam_id not in self._tracks_by_camera:
            self._tracks_by_camera[cam_id] = {}
        camera_tracks = self._tracks_by_camera[cam_id]

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
            
            # Allow camera-specific track initiation threshold (Camera 2 far objects: 0.22)
            effective_tracking_conf = getattr(self._config, "cam2_tracking_confidence", 0.22) if cam_id == "camera_2" else self._config.tracking_confidence

            for det in detections:
                if det.confidence >= effective_tracking_conf:
                    high_dets.append(det)
                else:
                    low_dets.append(det)
                    
            unmatched_tracks = set(t_id for t_id, t in camera_tracks.items() if t.current_state != 'REMOVED')
            matched_tracks = set()
            unmatched_high_dets = []
            
            # Step 1: Match high confidence detections
            for det in high_dets:
                best_iou = 0.0
                best_track_id = None
                
                for t_id in list(unmatched_tracks):
                    track = camera_tracks[t_id]
                    # Direct match or confusable class group match
                    confusable_group = {DetectedObjectType.BOOK, DetectedObjectType.LAPTOP, DetectedObjectType.NOTEBOOK, DetectedObjectType.PAPER, DetectedObjectType.UNAUTHORIZED_MATERIAL}
                    is_confusable = (track.object_type in confusable_group and det.object_type in confusable_group)
                    if track.object_type != det.object_type and not is_confusable:
                        continue
                        
                    iou = self._calculate_iou(det.bbox, track.bbox)
                    if iou > self._config.matching_threshold and iou > best_iou:
                        best_iou = iou
                        best_track_id = t_id
                
                # Spatial proximity fallback for recently lost/moved objects of same type
                if best_track_id is None:
                    best_dist = float('inf')
                    for t_id in list(unmatched_tracks):
                        track = camera_tracks[t_id]
                        confusable_group = {DetectedObjectType.BOOK, DetectedObjectType.LAPTOP, DetectedObjectType.NOTEBOOK, DetectedObjectType.PAPER, DetectedObjectType.UNAUTHORIZED_MATERIAL}
                        is_confusable = (track.object_type in confusable_group and det.object_type in confusable_group)
                        if track.object_type != det.object_type and not is_confusable:
                            continue
                        dist = self._calculate_spatial_dist(det.bbox, track.bbox)
                        max_dim = max(det.bbox.width, det.bbox.height, track.bbox.width, track.bbox.height, 100.0)
                        if dist < max_dim * 2.5 and dist < best_dist:
                            best_dist = dist
                            best_track_id = t_id
                        
                if best_track_id is not None:
                    # Update track
                    track = camera_tracks[best_track_id]
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
                    track.object_type = det.object_type
                    
                    matched_tracks.add(best_track_id)
                    unmatched_tracks.remove(best_track_id)
                else:
                    unmatched_high_dets.append(det)
                    
            # Step 2: Match remaining unmatched tracks with low confidence detections
            for det in low_dets:
                best_iou = 0.0
                best_track_id = None
                
                for t_id in list(unmatched_tracks):
                    track = camera_tracks[t_id]
                    # Only try to match low dets to tracks that are currently active (not newly lost)
                    if track.current_state != 'TRACKED':
                        continue
                    confusable_group = {DetectedObjectType.BOOK, DetectedObjectType.LAPTOP, DetectedObjectType.NOTEBOOK, DetectedObjectType.PAPER, DetectedObjectType.UNAUTHORIZED_MATERIAL}
                    is_confusable = (track.object_type in confusable_group and det.object_type in confusable_group)
                    if track.object_type != det.object_type and not is_confusable:
                        continue
                        
                    iou = self._calculate_iou(det.bbox, track.bbox)
                    # Use a potentially lower matching threshold for low dets if needed, or same
                    if iou > self._config.matching_threshold * 0.8 and iou > best_iou:
                        best_iou = iou
                        best_track_id = t_id
                        
                if best_track_id is not None:
                    # Update track
                    track = camera_tracks[best_track_id]
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
                track = camera_tracks[t_id]
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
                camera_tracks[self._next_id] = new_track
                self._next_id += 1
                stats.new_tracks += 1
                
            # Clean out REMOVED tracks from camera memory to prevent bloat
            self._tracks_by_camera[cam_id] = {tid: t for tid, t in camera_tracks.items() if t.current_state != 'REMOVED'}
            self._tracks = {tid: t for ctracks in self._tracks_by_camera.values() for tid, t in ctracks.items()}
            
            # Formulate final output for this camera
            active_objects = []
            for t in self._tracks_by_camera[cam_id].values():
                if t.current_state in ['NEW', 'TRACKED', 'LOST']:
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

    def _calculate_spatial_dist(self, boxA, boxB) -> float:
        cA_x = getattr(boxA, 'x', 0) + getattr(boxA, 'width', 0) / 2.0
        cA_y = getattr(boxA, 'y', 0) + getattr(boxA, 'height', 0) / 2.0
        cB_x = getattr(boxB, 'x', 0) + getattr(boxB, 'width', 0) / 2.0
        cB_y = getattr(boxB, 'y', 0) + getattr(boxB, 'height', 0) / 2.0
        return ((cA_x - cB_x) ** 2 + (cA_y - cB_y) ** 2) ** 0.5
