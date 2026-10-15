from abc import ABC, abstractmethod
from ai_engine.core.exam_context import ExamContext

class Detector(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initializes detector models and resources."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the detector."""
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """Runs detection models on the current frame and updates the ExamContext."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the detector."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Releases detector models and resources."""
        pass
