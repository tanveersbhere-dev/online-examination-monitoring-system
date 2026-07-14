"""
Abstract Object Detector Interface.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.environment.object_detection.models import ObjectDetectionConfig

class ObjectDetectorInterface(Detector):
    """
    Abstract base class for Object Detection implementations.

    Input contract
    --------------
    process() reads ONLY:
      • `context.current_frame`

    Output contract
    ---------------
    process() writes ONLY to:
      • `context.object_info`
    """

    def __init__(self, config: ObjectDetectionConfig) -> None:
        self._config: ObjectDetectionConfig = config

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
    def config(self) -> ObjectDetectionConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
