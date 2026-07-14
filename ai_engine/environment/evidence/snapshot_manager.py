"""
Evidence Snapshot Manager implementation.
"""
import os
import time
import uuid
import logging
from typing import Dict, Any, List

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from ai_engine.core.exam_context import ExamContext, TrackedObject
from ai_engine.environment.evidence.manager import EvidenceSnapshotManagerInterface
from ai_engine.environment.evidence.models import EvidenceConfig, EvidenceSnapshot, SnapshotMetadata
from ai_engine.environment.evidence.exceptions import EvidenceManagerError, SnapshotCreationError, SnapshotStorageError, ImageProcessingError

logger = logging.getLogger(__name__)

class EvidenceSnapshotManager(EvidenceSnapshotManagerInterface):
    """
    Manages capturing evidence snapshots of tracked objects at meaningful lifecycle events.
    """
    def __init__(self, config: EvidenceConfig) -> None:
        super().__init__(config)
        self._initialized = False
        # track_id -> dict of state
        self._track_states: Dict[int, Dict[str, Any]] = {}
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing EvidenceSnapshotManager...")
            
        if not CV2_AVAILABLE:
            logger.warning("OpenCV is not available. Snapshots will not be processed correctly.")
            
        # Ensure snapshot directory exists
        os.makedirs(self._config.snapshot_directory, exist_ok=True)
        
        self._initialized = True
        self._track_states.clear()
        
        if self._config.enable_logging:
            logger.debug("EvidenceSnapshotManager initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise EvidenceManagerError("Cannot start uninitialized EvidenceSnapshotManager.")
        if self._config.enable_logging:
            logger.debug("EvidenceSnapshotManager started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("EvidenceSnapshotManager stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up EvidenceSnapshotManager...")
        self._initialized = False
        self._track_states.clear()
        if self._config.enable_logging:
            logger.debug("EvidenceSnapshotManager cleaned up.")

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            raise EvidenceManagerError("EvidenceSnapshotManager is not initialized.")
            
        start_time = time.perf_counter()
        
        # We need both the frame and the tracked objects
        frame = context.current_frame
        tracked_objects = context.object_info.tracked_objects
        
        new_snapshots: List[EvidenceSnapshot] = []
        
        # Track active IDs in this frame to help cleanup later
        current_frame_track_ids = set()
        
        for track in tracked_objects:
            t_id = track.tracking_id
            current_frame_track_ids.add(t_id)
            
            # Initialize state for new tracks
            if t_id not in self._track_states:
                self._track_states[t_id] = {
                    "has_confirmed": False,
                    "max_conf": 0.0,
                    "max_area": 0.0,
                    "snapshot_count": 0
                }
                
            state = self._track_states[t_id]
            
            # Skip if we hit max snapshots
            if state["snapshot_count"] >= self._config.max_snapshots_per_object:
                continue
                
            # Determine area
            area = track.bbox.width * track.bbox.height
            
            reason = None
            
            # Event 1: Track Confirmed
            if track.current_state == "TRACKED" and not state["has_confirmed"]:
                reason = "Track Confirmed"
                state["has_confirmed"] = True
            
            # Event 4: Track Removed
            elif track.current_state == "REMOVED":
                reason = "Track Removed"
            
            # Event 2: Highest Confidence Observation
            elif track.confidence > state["max_conf"]:
                # Only capture if it's a meaningful increase, e.g. > 5% to prevent spam, 
                # but for strict compliance we'll just capture if strictly greater.
                # However we want to ensure we don't spam snapshots if it increases by 0.001
                if track.confidence - state["max_conf"] > 0.05 or state["max_conf"] == 0.0:
                    reason = "Highest Confidence Observation"
            
            # Event 3: Largest Visible Bounding Box
            elif area > state["max_area"]:
                # Only capture if area increased significantly (> 10%)
                if area > state["max_area"] * 1.10 or state["max_area"] == 0.0:
                    reason = "Largest Visible Bounding Box"
                    
            if reason:
                # We have a reason to snapshot.
                try:
                    snapshot = self._capture_snapshot(track, frame, reason)
                    if snapshot:
                        new_snapshots.append(snapshot)
                        state["snapshot_count"] += 1
                        
                        # Update max states if we captured successfully
                        if track.confidence > state["max_conf"]:
                            state["max_conf"] = track.confidence
                        if area > state["max_area"]:
                            state["max_area"] = area
                            
                except Exception as e:
                    if self._config.enable_logging:
                        logger.error(f"Failed to capture snapshot for track {t_id}: {e}")
                        
        # Ensure we attach to context without modifying existing lists if possible
        if not hasattr(context.object_info, "evidence"):
            setattr(context.object_info, "evidence", [])
            
        evidence_list = getattr(context.object_info, "evidence")
        evidence_list.extend(new_snapshots)
        
        # Note: If track is marked REMOVED and we've processed it, we can safely delete its state
        # next frame. We will clean up states of tracks that are no longer in tracked_objects.
        active_ids = {t.tracking_id for t in tracked_objects}
        keys_to_remove = [tid for tid in self._track_states if tid not in active_ids]
        for tid in keys_to_remove:
            del self._track_states[tid]
            
        if self._config.enable_logging and new_snapshots:
            proc_time_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Captured {len(new_snapshots)} snapshots in {proc_time_ms:.2f}ms")

    def _capture_snapshot(self, track: TrackedObject, frame: Any, reason: str) -> EvidenceSnapshot:
        """Captures a frame, draws bounding box, and saves to disk."""
        if not CV2_AVAILABLE:
            raise ImageProcessingError("OpenCV is not available.")
            
        if frame is None or getattr(frame, "original_frame", None) is None:
            raise ImageProcessingError("No valid original_frame available in ExamContext.")
            
        try:
            # Copy frame to avoid modifying original
            img = frame.original_frame.copy()
            
            # Draw bbox
            x = int(track.bbox.x)
            y = int(track.bbox.y)
            w = int(track.bbox.width)
            h = int(track.bbox.height)
            
            cv2.rectangle(img, (x, y), (x + w, y + h), self._config.bounding_box_color, self._config.line_thickness)
            
            # Draw labels
            label = f"{track.object_type.name} ID:{track.tracking_id} Conf:{track.confidence:.2f}"
            
            # Timestamp (human readable)
            ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(track.last_detection_timestamp))
            
            cv2.putText(img, label, (x, max(10, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, self._config.font_scale, self._config.bounding_box_color, self._config.line_thickness)
            cv2.putText(img, ts_str, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, self._config.font_scale, self._config.bounding_box_color, self._config.line_thickness)
            
            # Generate file path
            snapshot_id = str(uuid.uuid4())
            ext = ".png" if self._config.png_support else ".jpg"
            filename = f"{snapshot_id}{ext}"
            file_path = os.path.join(self._config.snapshot_directory, filename)
            
            # Save image
            success = False
            if ext == ".jpg":
                success = cv2.imwrite(file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), self._config.jpeg_quality])
            else:
                success = cv2.imwrite(file_path, img)
                
            if not success:
                raise SnapshotStorageError(f"cv2.imwrite failed to save image at {file_path}")
                
            # Create snapshot object
            metadata = SnapshotMetadata(
                tracking_duration=track.visible_duration,
                reason=reason
            )
            
            snapshot = EvidenceSnapshot(
                snapshot_id=snapshot_id,
                track_id=track.tracking_id,
                object_type=track.object_type,
                timestamp=time.time(),
                frame_id=track.frame_id,
                bbox=track.bbox,
                confidence=track.confidence,
                snapshot_path=file_path,
                snapshot_reason=reason,
                metadata=metadata
            )
            
            return snapshot
            
        except Exception as e:
            if isinstance(e, SnapshotStorageError):
                raise
            raise SnapshotCreationError(f"Failed during image drawing/saving: {e}") from e
