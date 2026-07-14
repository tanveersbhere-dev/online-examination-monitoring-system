"""
Abstract Mouth Aspect Ratio (MAR) Processor interface.

Defines the contract that every concrete MAR extraction backend must
satisfy. Extends the engine-level ``Detector`` interface with MAR-specific
methods.
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.camera.frame import Frame
from ai_engine.features.mouth_aspect_ratio.result import MARResult
from ai_engine.features.mouth_aspect_ratio.models import MARConfig


class MouthAspectRatioProcessor(Detector):
    """
    Abstract base class for all MAR feature extraction implementations.

    Input contract
    --------------
    process() reads ONLY:
      • ``context.face_mesh_info``

    Output contract
    ---------------
    process() writes ONLY:
      • ``context.mouth_info``
    """

    def __init__(self, config: MARConfig) -> None:
        self._config: MARConfig = config

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
        frame_id: int,
        all_face_landmarks: list
    ) -> MARResult:
        """
        Runs MAR extraction on a single frame's landmarks.

        Args:
            frame_id: The ID of the current frame.
            all_face_landmarks: List of landmarks for all detected faces.

        Returns:
            An ``MARResult`` containing geometries for every face.
        """
        pass

    @property
    def config(self) -> MARConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
