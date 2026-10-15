"""Abstract interface for Risk Scoring Engine."""
from abc import abstractmethod
from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.risk_scoring.models import RiskScoringConfig

class RiskScoringProcessorInterface(Detector):
    """
    Abstract base class for Risk Scoring implementations.
    """

    def __init__(self, config: RiskScoringConfig) -> None:
        self._config: RiskScoringConfig = config

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
    def config(self) -> RiskScoringConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
