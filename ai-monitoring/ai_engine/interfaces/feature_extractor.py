from abc import ABC, abstractmethod
from ai_engine.core.exam_context import ExamContext

class FeatureExtractor(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initializes feature extraction models and pipelines."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the feature extractor."""
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """Extracts numerical features from face mesh/gaze/pose/audio in the context."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the feature extractor."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleans up internal resources."""
        pass
