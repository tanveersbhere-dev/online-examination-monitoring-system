"""
YOLO-based Object Detector implementation.
"""
import time
import logging
from typing import Dict

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import ExamContext, DetectedObject, BoundingBox
from ai_engine.environment.object_detection.detector import ObjectDetectorInterface
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_detection.exceptions import ObjectDetectionError, ModelLoadError, InferenceError, InvalidFrameError

logger = logging.getLogger(__name__)

class YOLODetector(ObjectDetectorInterface):
    """
    Ultralytics YOLO implementation for object detection.
    """
    
    # Map COCO class IDs (commonly used in YOLO) to our enum
    COCO_CLASS_MAP: Dict[int, DetectedObjectType] = {
        0: DetectedObjectType.PERSON,
        67: DetectedObjectType.CELL_PHONE,
        73: DetectedObjectType.LAPTOP,
        63: DetectedObjectType.LAPTOP,  # Sometimes 63 is laptop depending on model
        72: DetectedObjectType.MONITOR, # tv/monitor
        66: DetectedObjectType.KEYBOARD,
        64: DetectedObjectType.MOUSE,
        74: DetectedObjectType.MOUSE,   # sometimes mouse is 74
        76: DetectedObjectType.KEYBOARD,# sometimes keyboard is 76
        77: DetectedObjectType.CELL_PHONE, # mobile phone
        # Note: COCO doesn't explicitly have smartwatch, headphones, earbuds, book, notebook, paper.
        # This mapping is standard COCO. Custom YOLO models might have different indices.
        # We map what we can, everything else maps to UNKNOWN.
        73: DetectedObjectType.BOOK, # 73 is sometimes book
    }

    def __init__(self, config: ObjectDetectionConfig) -> None:
        super().__init__(config)
        self._initialized = False
        self._model = None
        
    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug(f"Initializing YOLODetector with model: {self._config.model_path}")
            
        try:
            import ultralytics
            # We enforce offline loading by passing the path directly and preventing downloads if possible.
            # In testing environments without weights, this might fail unless mocked.
            self._model = ultralytics.YOLO(self._config.model_path)
            # Send to CPU
            self._model.to(self._config.device)
            self._initialized = True
            
            if self._config.enable_logging:
                logger.debug("YOLO model loaded successfully.")
                
        except ImportError:
            logger.warning("ultralytics module not found. Inference will raise errors if not mocked.")
            self._model = None
            self._initialized = True # Mark true so we can test the fallback
        except Exception as e:
            raise ModelLoadError(f"Failed to load YOLO model: {e}") from e

    def start(self) -> None:
        if not self._initialized:
            raise ObjectDetectionError("Cannot start uninitialized detector.")
        if self._config.enable_logging:
            logger.debug("YOLODetector started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("YOLODetector stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up YOLODetector...")
        self._initialized = False
        self._model = None
        if self._config.enable_logging:
            logger.debug("YOLODetector cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads current_frame and updates object_info with detections.
        """
        if not self._initialized:
            raise ObjectDetectionError("Detector is not initialized.")
            
        frame = context.current_frame
        if frame is None or frame.original_frame is None:
            raise InvalidFrameError("Current frame is empty or invalid.")
            
        if self._model is None:
             raise InferenceError("YOLO model is not loaded. Cannot perform inference.")

        start_time = time.perf_counter()
        
        try:
            # Predict
            results = self._model.predict(
                source=frame.original_frame,
                conf=self._config.confidence_threshold,
                iou=self._config.iou_threshold,
                device=self._config.device,
                max_det=self._config.max_detections,
                verbose=False
            )
            
            detected_objects = []
            
            if results and len(results) > 0:
                result = results[0]
                
                # Extract boxes, confs, classes
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confs = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy()
                    
                    for i in range(len(boxes)):
                        conf = float(confs[i])
                        cls_id = int(class_ids[i])
                        
                        # Map to enum
                        obj_type = self._map_class_id(cls_id)
                        
                        # Filter by enabled classes
                        if obj_type in self._config.enabled_classes:
                            x1, y1, x2, y2 = boxes[i]
                            bbox = BoundingBox(
                                x=float(x1),
                                y=float(y1),
                                width=float(x2 - x1),
                                height=float(y2 - y1)
                            )
                            
                            detected_objects.append(
                                DetectedObject(
                                    object_type=obj_type,
                                    confidence=conf,
                                    bbox=bbox
                                )
                            )
            
            end_time = time.perf_counter()
            proc_time_ms = (end_time - start_time) * 1000.0
            
            # Update context
            object_info = context.object_info
            object_info.current_detections = detected_objects
            object_info.total_object_count = len(detected_objects)
            object_info.timestamp = time.time()
            object_info.frame_id = frame.frame_id
            object_info.processing_time_ms = proc_time_ms
            
            context.object_info = object_info
            
            if self._config.enable_logging:
                 logger.debug(f"Detected {len(detected_objects)} objects in {proc_time_ms:.2f}ms")
                 
        except Exception as e:
            if self._config.enable_logging:
                logger.error(f"Error during YOLO inference: {e}")
            raise InferenceError(f"Error performing object detection inference: {e}") from e

    def _map_class_id(self, class_id: int) -> DetectedObjectType:
        """Maps an integer class ID to DetectedObjectType Enum."""
        # For standard COCO:
        if class_id == 0:
            return DetectedObjectType.PERSON
        elif class_id == 67:
            return DetectedObjectType.CELL_PHONE
        elif class_id == 73:
            return DetectedObjectType.LAPTOP
        elif class_id == 66:
            return DetectedObjectType.KEYBOARD
        elif class_id == 64:
            return DetectedObjectType.MOUSE
        elif class_id == 72:
            return DetectedObjectType.MONITOR
        
        # If it's something else not mapped explicitly
        return DetectedObjectType.UNKNOWN
