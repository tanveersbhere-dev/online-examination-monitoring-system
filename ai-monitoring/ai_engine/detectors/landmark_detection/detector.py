"""
Abstract face landmark detector interface.

Defines the contract that every concrete landmark extraction backend must
satisfy.  Extends the engine-level ``Detector`` interface with landmark-specific
methods so implementations (MediaPipe, FAN, Dlib, etc.) remain swappable
without modifying any other module.

Lifecycle
---------
initialize() → start() → process() [repeated] → stop() → cleanup()

Scope
-----
This interface is ONLY for facial landmark extraction.  It must never perform:
  • Face detection         (delegated to AI Module 1)
  • Head pose estimation   (AI Module 3)
  • Gaze estimation        (AI Module 4)
  • Blink or mouth analysis
  • Object detection / tracking
  • Decision making / violation generation
"""
from abc import abstractmethod

from ai_engine.interfaces.detector import Detector
from ai_engine.core.exam_context import ExamContext
from ai_engine.camera.frame import Frame
from ai_engine.detectors.landmark_detection.result import FaceMeshResult
from ai_engine.detectors.landmark_detection.models import LandmarkDetectionConfig


class LandmarkDetectorInterface(Detector):
    """
    Abstract base class for all face landmark extraction implementations.

    Each concrete subclass (e.g. ``MediaPipeLandmarkDetector``) must implement
    every abstract method.  Callers must never depend on a concrete type;
    always accept ``LandmarkDetectorInterface``.

    Input contract
    --------------
    process() reads ONLY:
      • ``context.current_frame``
      • ``context.face_info``  (to check whether detection is active)

    Output contract
    ---------------
    process() writes ONLY:
      • ``context.face_mesh_info``

    No other section of ExamContext is touched.
    """

    def __init__(self, config: LandmarkDetectionConfig) -> None:
        """
        Args:
            config: Configuration injected at construction time.
                    Must not be ``None``.
        """
        self._config: LandmarkDetectionConfig = config

    # ------------------------------------------------------------------ #
    #  Engine-level lifecycle (from interfaces.Detector)                  #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def initialize(self) -> None:
        """
        Loads the landmark model and prepares all internal resources.

        Must be idempotent — safe to call more than once.

        Raises:
            MediaPipeInitializationError: If the model cannot be loaded.
            LandmarkDetectorModelNotFoundError: If the model file is absent.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Marks the detector as active.  Called exactly once after initialize().

        Raises:
            LandmarkDetectorStateError: If initialize() has not been called.
        """
        pass

    @abstractmethod
    def process(self, context: ExamContext) -> None:
        """
        Reads ``context.current_frame`` and ``context.face_info``, runs
        landmark extraction, and writes the result to ``context.face_mesh_info``.

        If no frame is available, or if ``face_info.face_detected`` is False,
        the method returns without modifying the context.

        Args:
            context: The shared, thread-safe ExamContext instance.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Pauses landmark extraction.  The detector may be re-started."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Releases all model and resource handles acquired during initialize().

        After cleanup() the detector must be re-initialized before use.
        """
        pass

    # ------------------------------------------------------------------ #
    #  Landmark-specific abstract method                                  #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def extract(self, frame: Frame, num_faces: int) -> FaceMeshResult:
        """
        Runs landmark extraction on a single frame without mutating any
        shared state.

        This is the pure-functional core of the detector.  ``process()``
        is the orchestration wrapper that reads from and writes to the
        ExamContext.

        Args:
            frame:     The frame to run inference on.
            num_faces: Maximum number of faces to extract landmarks for.

        Returns:
            A ``FaceMeshResult`` containing landmarks for every detected face.

        Raises:
            LandmarkDetectorStateError: If called before initialize().
            LandmarkExtractionError:    On any inference failure.
        """
        pass

    # ------------------------------------------------------------------ #
    #  Read-only properties                                               #
    # ------------------------------------------------------------------ #

    @property
    def config(self) -> LandmarkDetectionConfig:
        """Returns the injected configuration (read-only)."""
        return self._config

    @property
    def is_initialized(self) -> bool:
        """True once ``initialize()`` has completed successfully."""
        return getattr(self, "_initialized", False)
