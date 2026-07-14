"""
Abstract Blink Detection Processor interface.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.features.blink_detection.models import BlinkDetectionConfig

class BlinkDetectionProcessor(Detector):
    """
    Abstract base class for all Blink Detection feature extraction implementations.

    Input contract
    --------------
    process() reads ONLY:
      • `context.eye_info.average_ear`
      • `context.eye_info.processing_timestamp`

    Output contract
    ---------------
    process() writes ONLY to:
      • `context.eye_info`
    """

    def __init__(self, config: BlinkDetectionConfig) -> None:
        self._config: BlinkDetectionConfig = config

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
    def config(self) -> BlinkDetectionConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
