"""
Object Filtering Processor implementation.
"""
import time
import logging
from typing import List

from ai_engine.core.exam_context import ExamContext, DetectedObject, FilteredObject, FilteringStatistics
from ai_engine.environment.object_filtering.processor import ObjectFilteringProcessorInterface
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig
from ai_engine.environment.object_filtering.exceptions import ObjectFilteringError, InvalidDetectionError

logger = logging.getLogger(__name__)

class FilteringProcessor(ObjectFilteringProcessorInterface):
    """
    Validates, filters, and suppresses duplicate raw detections.
    """
    
    def __init__(self, config: ObjectFilteringConfig) -> None:
        super().__init__(config)
        self._initialized = False
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing FilteringProcessor...")
        self._initialized = True
        if self._config.enable_logging:
            logger.debug("FilteringProcessor initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise ObjectFilteringError("Cannot start uninitialized FilteringProcessor.")
        if self._config.enable_logging:
            logger.debug("FilteringProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("FilteringProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up FilteringProcessor...")
        self._initialized = False
        if self._config.enable_logging:
            logger.debug("FilteringProcessor cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads raw detections, filters them, and outputs filtered_detections.
        """
        if not self._initialized:
            raise ObjectFilteringError("Processor is not initialized.")
            
        start_time = time.perf_counter()
        
        object_info = context.object_info
        raw_detections = object_info.current_detections
        
        stats = FilteringStatistics()
        stats.total_received = len(raw_detections)
        
        valid_detections: List[DetectedObject] = []
        
        # 1. Validation & Basic Filtering
        for det in raw_detections:
            if not self._is_valid_bbox(det.bbox):
                stats.invalid_box_removed += 1
                stats.total_rejected += 1
                continue
                
            if det.object_type not in self._config.supported_classes:
                stats.unsupported_class_removed += 1
                stats.total_rejected += 1
                continue
                
            if det.confidence < self._config.min_confidence:
                stats.low_confidence_removed += 1
                stats.total_rejected += 1
                continue
                
            valid_detections.append(det)
            
        # 2. Duplicate Suppression (NMS based on IoU if enabled)
        if self._config.duplicate_filtering_enabled:
            valid_detections = self._apply_nms(valid_detections, stats)
            
        # 3. Truncate to Max Objects based on confidence
        valid_detections.sort(key=lambda x: x.confidence, reverse=True)
        if len(valid_detections) > self._config.max_objects:
            removed = len(valid_detections) - self._config.max_objects
            # Attribute truncated objects to total rejected (could add a specific stat if needed)
            stats.total_rejected += removed
            valid_detections = valid_detections[:self._config.max_objects]
            
        # 4. Map to FilteredObject
        filtered_objects = []
        current_time = time.time()
        for det in valid_detections:
            filtered_objects.append(
                FilteredObject(
                    object_type=det.object_type,
                    confidence=det.confidence,
                    bbox=det.bbox,
                    detection_timestamp=current_time,
                    frame_id=object_info.frame_id
                )
            )
            
        stats.total_accepted = len(filtered_objects)
        
        end_time = time.perf_counter()
        proc_time_ms = (end_time - start_time) * 1000.0
        
        # 5. Update Context
        object_info.filtered_detections = filtered_objects
        object_info.filtering_statistics = stats
        object_info.filtering_processing_time_ms = proc_time_ms
        context.object_info = object_info
        
        if self._config.enable_logging:
            logger.debug(f"Filtered {len(filtered_objects)} objects out of {stats.total_received} received in {proc_time_ms:.2f}ms")

    def _is_valid_bbox(self, bbox) -> bool:
        """Validates bounding box dimensions and coordinates."""
        if bbox is None:
            return False
        if bbox.width <= 0 or bbox.height <= 0:
            return False
        if bbox.x < 0 or bbox.y < 0:
            return False
        # Prevent absurdly large boxes (e.g. larger than 8K resolution in general, though normally checked against frame)
        if bbox.width > 10000 or bbox.height > 10000:
            return False
        return True

    def _apply_nms(self, detections: List[DetectedObject], stats: FilteringStatistics) -> List[DetectedObject]:
        """Applies Non-Maximum Suppression per class."""
        if not detections:
            return []
            
        # Group by class
        by_class = {}
        for det in detections:
            by_class.setdefault(det.object_type, []).append(det)
            
        kept_detections = []
        for obj_type, group in by_class.items():
            # Sort by confidence
            group.sort(key=lambda x: x.confidence, reverse=True)
            
            kept = []
            for current in group:
                overlap = False
                for k in kept:
                    if self._calculate_iou(current.bbox, k.bbox) > self._config.iou_threshold:
                        overlap = True
                        break
                if not overlap:
                    kept.append(current)
                else:
                    stats.duplicates_removed += 1
                    stats.total_rejected += 1
                    
            kept_detections.extend(kept)
            
        return kept_detections

    def _calculate_iou(self, boxA, boxB) -> float:
        """Calculates Intersection over Union between two BoundingBoxes."""
        # box: x, y, width, height
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
