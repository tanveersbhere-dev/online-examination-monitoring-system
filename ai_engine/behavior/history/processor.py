"""
Abstract Behavior History Processor interface.
"""
from abc import abstractmethod
from typing import Any

from ai_engine.core.exam_context import ExamContext
from ai_engine.behavior.history.models import BehaviorHistoryConfig

class BehaviorHistoryProcessor:
    """
    Abstract base class for Behavior History Engine implementations.

    Input contract
    --------------
    process() reads ONLY standard metrics from ExamContext features.
    
    Output contract
    ---------------
    process() writes ONLY to `ExamContext.behavior_history`
    """

    def __init__(self, config: BehaviorHistoryConfig) -> None:
        self._config: BehaviorHistoryConfig = config

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
    def config(self) -> BehaviorHistoryConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
