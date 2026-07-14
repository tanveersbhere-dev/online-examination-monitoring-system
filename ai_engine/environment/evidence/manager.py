"""
Abstract Evidence Snapshot Manager Interface.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.environment.evidence.models import EvidenceConfig

class EvidenceSnapshotManagerInterface(Detector):
    """
    Abstract base class for Evidence Snapshot Management implementations.

    Input contract
    --------------
    process() reads ONLY:
      • `context.current_frame`
      • `context.object_info.tracked_objects`

    Output contract
    ---------------
    process() updates ONLY:
      • `context.object_info.evidence`
    """

    def __init__(self, config: EvidenceConfig) -> None:
        self._config: EvidenceConfig = config

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
    def config(self) -> EvidenceConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
