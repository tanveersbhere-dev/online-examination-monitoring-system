from abc import ABC, abstractmethod
from ai_engine.core.exam_context import ExamContext

class EventPublisher(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initializes publishing connectors or queues."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the publisher thread/service."""
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """Collects violations and publishes events externally."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the publisher."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Closes publisher connections and logs."""
        pass
