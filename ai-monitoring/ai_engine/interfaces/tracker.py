from abc import ABC, abstractmethod
from ai_engine.core.exam_context import ExamContext

class Tracker(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initializes tracker models and parameters."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the tracker."""
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """Tracks entities across frames using detection results in ExamContext."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the tracker."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Releases tracker resources."""
        pass
