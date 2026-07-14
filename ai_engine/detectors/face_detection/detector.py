"""
Abstract face detector interface.

Defines the contract that every concrete face detection backend must satisfy.
Extends the engine-level Detector interface with face-detection-specific
methods so implementations remain swappable without modifying calling code.
"""
from abc import abstractmethod
from typing import Optional

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.camera.frame import Frame
from ai_engine.detectors.face_detection.result import FaceDetectionResult
from ai_engine.detectors.face_detection.models import FaceDetectionConfig


class FaceDetectorInterface(Detector):
    """
    Abstract base class for all face detector implementations.

    Lifecycle
    ---------
    initialize() → start() → process() [repeated] → stop() → cleanup()

    Responsibilities
    ----------------
    • Detect human faces in a provided frame.
    • Return a strongly typed FaceDetectionResult.
    • Update ExamContext.face_info after each inference.
    • Log initialization, inference time, face count, and confidence.

    Out-of-scope
    ------------
    • Must NOT perform face mesh, head pose, gaze, or mouth analysis.
    • Must NOT perform object detection or person tracking.
    • Must NOT publish events or generate violations.
    • Must NOT invoke the Decision Engine.
    """

    def __init__(self, config: FaceDetectionConfig) -> None:
        """
        Args:
            config: Configuration parameters injected at construction time
                    (dependency injection pattern).
        """
        self._config = config

    # ------------------------------------------------------------------ #
    #  Core interface methods (abstract — must be implemented by subclass) #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def initialize(self) -> None:
        """
        Loads the detection model and prepares internal resources.

        Raises:
            FaceDetectorInitializationError: If the model cannot be loaded.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """Marks the detector as active. Called once after initialize()."""
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """
        Reads the current frame from context, runs inference, and updates
        context.face_info with the detection results.

        Args:
            context: Shared exam session context. Must not be None.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops active detection; the detector may be re-started."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Releases all model and resource handles acquired in initialize()."""
        pass

    # ------------------------------------------------------------------ #
    #  Face-detection-specific abstract methods                           #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def detect(self, frame: Frame) -> FaceDetectionResult:
        """
        Runs face detection inference on a single frame without mutating
        any shared state.

        Args:
            frame: The frame to run inference on.

        Returns:
            A FaceDetectionResult with all faces found in the frame.

        Raises:
            FaceDetectorInferenceError: On inference failure.
        """
        pass

    # ------------------------------------------------------------------ #
    #  Optional property accessors                                        #
    # ------------------------------------------------------------------ #

    @property
    def config(self) -> FaceDetectionConfig:
        """Returns the current detector configuration (read-only)."""
        return self._config

    @property
    def is_initialized(self) -> bool:
        """True once initialize() has completed successfully."""
        return getattr(self, "_initialized", False)
