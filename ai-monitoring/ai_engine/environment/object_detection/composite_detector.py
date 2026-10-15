"""
Composite Object Detector implementation.
Orchestrates multiple specialized object detectors (e.g. General YOLOv8n + Wearable Audio Detector)
and merges their normalized detections into ExamContext.
"""
import logging
from typing import List, Dict, Any, Optional

from ai_engine.core.exam_context import ExamContext
from ai_engine.environment.object_detection.detector import ObjectDetectorInterface
from ai_engine.environment.object_detection.models import ObjectDetectionConfig

logger = logging.getLogger(__name__)


class CompositeObjectDetector(ObjectDetectorInterface):
    """
    Composite Detector that manages and executes multiple detector implementations
    (e.g., General YOLOv8n detector + Wearable Audio Detector).
    """

    def __init__(self, detectors: Optional[List[ObjectDetectorInterface]] = None, config: Optional[ObjectDetectionConfig] = None) -> None:
        cfg = config or ObjectDetectionConfig()
        super().__init__(cfg)
        self._detectors: List[ObjectDetectorInterface] = detectors or []
        self._initialized = False

    def add_detector(self, detector: ObjectDetectorInterface) -> None:
        """Appends a sub-detector to the composite chain."""
        self._detectors.append(detector)

    def initialize(self) -> None:
        """Initializes all registered sub-detectors."""
        for det in self._detectors:
            try:
                det.initialize()
            except Exception as e:
                logger.error(f"[CompositeObjectDetector] Failed initializing sub-detector {type(det).__name__}: {e}")
                raise
        self._initialized = True

    def start(self) -> None:
        for det in self._detectors:
            det.start()

    def process(self, context: ExamContext) -> None:
        """
        Sequentially runs all active sub-detectors.
        Sub-detectors append their normalized detections to context.object_info.current_detections.
        """
        if not self._initialized:
            return

        # Reset current_detections for the fresh frame
        object_info = context.object_info
        object_info.current_detections = []
        object_info.total_object_count = 0
        object_info.processing_time_ms = 0.0
        context.object_info = object_info

        for det in self._detectors:
            try:
                det.process(context)
            except Exception as e:
                logger.error(f"[CompositeObjectDetector] Error during sub-detector {type(det).__name__} execution: {e}")

    def stop(self) -> None:
        for det in self._detectors:
            det.stop()

    def cleanup(self) -> None:
        for det in self._detectors:
            det.cleanup()

    @property
    def sub_detectors(self) -> List[ObjectDetectorInterface]:
        return self._detectors

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns diagnostic status of all registered sub-detectors."""
        summary = {}
        for det in self._detectors:
            name = type(det).__name__
            status = getattr(det, "status", "READY" if getattr(det, "_initialized", False) else "NOT_INITIALIZED")
            available = getattr(det, "is_available", True)
            summary[name] = {
                "status": status,
                "available": available
            }
        return summary
