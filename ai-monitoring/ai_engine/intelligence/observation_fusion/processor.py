"""Abstract interface for Observation Fusion."""
from abc import abstractmethod
from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.observation_fusion.models import ObservationFusionConfig

class ObservationFusionProcessorInterface(Detector):
    """
    Abstract base class for Observation Fusion Engine.
    """

    def __init__(self, config: ObservationFusionConfig) -> None:
        self._config: ObservationFusionConfig = config

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
    def config(self) -> ObservationFusionConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
