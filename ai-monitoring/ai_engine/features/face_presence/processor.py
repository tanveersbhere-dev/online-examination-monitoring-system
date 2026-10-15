"""
Abstract Face Presence Processor interface.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.features.face_presence.models import FacePresenceConfig

class FacePresenceProcessor(Detector):
    """
    Abstract base class for Face Presence feature extraction implementations.

    Input contract
    --------------
    process() reads ONLY:
      • `context.face_info`
        - face_count
        - bbox
        - confidence
        - detection_timestamp

    Output contract
    ---------------
    process() writes ONLY to:
      • `context.face_info`
    """

    def __init__(self, config: FacePresenceConfig) -> None:
        self._config: FacePresenceConfig = config

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
    def config(self) -> FacePresenceConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
