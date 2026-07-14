"""
Abstract head pose estimator interface.

Defines the contract that every concrete head pose estimation backend must
satisfy. Extends the engine-level ``Detector`` interface with head-pose-specific
methods.

Lifecycle
---------
initialize() → start() → process() [repeated] → stop() → cleanup()

Scope
-----
This interface is ONLY for estimating head pose (pitch, yaw, roll) using
already extracted landmarks. It must never perform:
  • Face detection
  • Face landmark extraction
  • Gaze estimation
  • Blink or mouth analysis
  • Object detection / tracking
  • Decision making / violation generation
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.camera.frame import Frame
from ai_engine.detectors.landmark_detection.result import FaceLandmarks
from ai_engine.estimators.head_pose.result import HeadPoseResult
from ai_engine.estimators.head_pose.models import HeadPoseConfig


class HeadPoseEstimatorInterface(Detector):
    """
    Abstract base class for all head pose estimation implementations.

    Input contract
    --------------
    process() reads ONLY:
      • ``context.current_frame``
      • ``context.face_mesh_info``

    Output contract
    ---------------
    process() writes ONLY:
      • ``context.head_pose_info``
    """

    def __init__(self, config: HeadPoseConfig) -> None:
        """
        Args:
            config: Configuration injected at construction time.
        """
        self._config: HeadPoseConfig = config

    @abstractmethod
    def initialize(self) -> None:
        """
        Prepares internal resources (e.g., standard 3D model, camera matrix).
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Marks the estimator as active.
        """
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """
        Reads from ``context``, runs pose estimation, and writes the result
        to ``context.head_pose_info``.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Pauses estimation."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Releases resources."""
        pass

    @abstractmethod
    def estimate(
        self,
        frame: Frame,
        all_face_landmarks: list
    ) -> HeadPoseResult:
        """
        Runs head pose estimation on a single frame.

        Args:
            frame: The current frame.
            all_face_landmarks: List of landmarks for all detected faces.

        Returns:
            A ``HeadPoseResult`` containing poses for every face.
        """
        pass

    @property
    def config(self) -> HeadPoseConfig:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
