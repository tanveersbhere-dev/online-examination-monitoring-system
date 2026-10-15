from abc import ABC, abstractmethod
from ai_engine.core.exam_context import ExamContext

class EvidenceManager(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initializes evidence folders and file writers."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the evidence manager."""
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """Captures images, audio snippets, or logs corresponding to violations in the context."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops evidence recording threads."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Flushes buffered evidence to disk."""
        pass
