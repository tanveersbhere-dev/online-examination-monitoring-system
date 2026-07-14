from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ai_engine.core.exam_context import ExamContext
    from ai_engine.camera.frame import Frame

class CameraProvider(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initializes the camera provider components."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts the camera acquisition thread/process."""
        pass

    @abstractmethod
    def process(self, context: "ExamContext") -> None:
        """Enriches the exam context with camera status/metrics."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the camera acquisition."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleans up internal resources."""
        pass

    @abstractmethod
    def get_frame(self, timeout: Optional[float] = None) -> Optional["Frame"]:
        """Retrieves the next frame from the camera queue."""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Returns True if the camera provider is running."""
        pass

    @property
    @abstractmethod
    def status(self) -> str:
        """Returns the current camera status string."""
        pass

    @property
    @abstractmethod
    def dropped_count(self) -> int:
        """Returns the total number of frames dropped."""
        pass

    @property
    @abstractmethod
    def fps(self) -> float:
        """Returns the rolling average frame acquisition rate (FPS)."""
        pass
