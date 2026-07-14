"""
Abstract Object Filtering Processor Interface.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig

class ObjectFilteringProcessorInterface(Detector):
    """
    Abstract base class for Object Filtering implementations.

    Input contract
    --------------
    process() reads ONLY:
      • `context.object_info.current_detections`

    Output contract
    ---------------
    process() writes ONLY to:
      • `context.object_info.filtered_detections`
      • `context.object_info.filtering_statistics`
      • `context.object_info.filtering_processing_time_ms`
    """

    def __init__(self, config: ObjectFilteringConfig) -> None:
        self._config: ObjectFilteringConfig = config

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
    def config(self) -> ObjectFilteringConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
