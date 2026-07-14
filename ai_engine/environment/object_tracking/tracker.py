"""
Abstract Object Tracker Interface.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.environment.object_tracking.models import ObjectTrackingConfig

class ObjectTrackerInterface(Detector):
    """
    Abstract base class for Object Tracking implementations.

    Input contract
    --------------
    process() reads ONLY:
      • `context.object_info.filtered_detections`

    Output contract
    ---------------
    process() writes ONLY to:
      • `context.object_info.tracked_objects`
      • `context.object_info.tracking_statistics`
      • `context.object_info.tracking_processing_time_ms`
    """

    def __init__(self, config: ObjectTrackingConfig) -> None:
        self._config: ObjectTrackingConfig = config

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass

    @property
    def config(self) -> ObjectTrackingConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
