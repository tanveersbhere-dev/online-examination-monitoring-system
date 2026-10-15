"""
Abstract Eye Aspect Ratio (EAR) Processor interface.

Defines the contract that every concrete EAR extraction backend must satisfy.
"""
from abc import abstractmethod
from typing import Optional

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.features.eye_aspect_ratio.result import EARResult
from ai_engine.features.eye_aspect_ratio.models import EARConfig

class EyeAspectRatioProcessor(Detector):
    """
    Abstract base class for all EAR feature extraction implementations.

    Input contract
    --------------
    process() reads ONLY:
      • `context.face_mesh_info`

    Output contract
    ---------------
    process() writes ONLY:
      • `context.eye_info`
    """

    def __init__(self, config: EARConfig) -> None:
        self._config: EARConfig = config

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

    @abstractmethod
    def extract(
        self,
        frame_id: Optional[int],
        all_face_landmarks: list
    ) -> EARResult:
        """
        Runs EAR extraction on a single frame's landmarks.

        Args:
            frame_id: The ID of the current frame.
            all_face_landmarks: List of landmarks for all detected faces.

        Returns:
            An `EARResult` containing geometries for every face.
        """
        pass

    @property
    def config(self) -> EARConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
