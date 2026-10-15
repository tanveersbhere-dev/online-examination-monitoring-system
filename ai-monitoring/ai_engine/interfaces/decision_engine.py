from abc import ABC, abstractmethod
from ai_engine.core.exam_context import ExamContext

class DecisionEngine(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initializes decision engine heuristics and models."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the decision engine monitoring process."""
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """Evaluates thresholds, updates risk scores, and flags violations in context."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the decision engine."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleans up decision engine state."""
        pass
