"""Abstract interface for Rule Engine."""
from abc import abstractmethod
from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig

class RuleEngineProcessorInterface(Detector):
    """
    Abstract base class for Rule Engine implementations.
    """

    def __init__(self, config: RuleEngineConfig) -> None:
        self._config: RuleEngineConfig = config

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
    def config(self) -> RuleEngineConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
