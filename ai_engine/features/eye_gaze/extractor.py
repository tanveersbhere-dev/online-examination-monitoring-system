"""
Abstract eye gaze extractor interface.

Defines the contract that every concrete eye gaze extraction backend must
satisfy. Extends the engine-level ``Detector`` interface with gaze-specific
methods.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.camera.frame import Frame
from ai_engine.features.eye_gaze.result import EyeGazeResult
from ai_engine.features.eye_gaze.models import EyeGazeConfig


class EyeGazeExtractorInterface(Detector):
    """
    Abstract base class for all eye gaze extraction implementations.

    Input contract
    --------------
    process() reads ONLY:
      • ``context.current_frame``
      • ``context.face_mesh_info``

    Output contract
    ---------------
    process() writes ONLY:
      • ``context.eye_info``
    """

    def __init__(self, config: EyeGazeConfig) -> None:
        self._config: EyeGazeConfig = config

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
        frame: Frame,
        all_face_landmarks: list
    ) -> EyeGazeResult:
        """
        Runs eye gaze extraction on a single frame.

        Args:
            frame: The current frame.
            all_face_landmarks: List of landmarks for all detected faces.

        Returns:
            An ``EyeGazeResult`` containing gaze data for every face.
        """
        pass

    @property
    def config(self) -> EyeGazeConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
