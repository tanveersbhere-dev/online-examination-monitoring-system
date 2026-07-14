"""Abstract Processor Interface for Environment History."""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.environment.history.models import HistoryConfig

class EnvironmentHistoryProcessorInterface(Detector):
    """
    Abstract base class for Environment History Engine implementations.
    """

    def __init__(self, config: HistoryConfig) -> None:
        self._config: HistoryConfig = config

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
    def config(self) -> HistoryConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
