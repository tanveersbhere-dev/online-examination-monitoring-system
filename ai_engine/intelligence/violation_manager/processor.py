"""Abstract interface for Violation Manager."""
from abc import abstractmethod
from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig

class ViolationManagerProcessorInterface(Detector):
    """
    Abstract base class for Violation Manager implementations.
    """

    def __init__(self, config: ViolationManagerConfig) -> None:
        self._config: ViolationManagerConfig = config

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
    def config(self) -> ViolationManagerConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
